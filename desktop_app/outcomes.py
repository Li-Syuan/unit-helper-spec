"""Local read models and quality feedback; never dispatch model or query work."""
import copy
import json
from decimal import Decimal, localcontext

from .core import stamp, TERMINAL
from .report_engine import report_input
from .query_schema import find_template, date_mapping


def initialize_outcome_schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS outcome_feedback(
        task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
        rating TEXT NOT NULL CHECK(rating IN ('usable','revise','unhelpful')),
        note TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')


class OutcomeService:
    def __init__(self, workflows):
        self.workflows = workflows
        self.store = workflows.store

    def read(self, tid):
        task = self.store.task(tid)
        if task['kind'] != 'workflow':
            raise ValueError('只支援多助理流程成果。')
        steps = self.workflows.get_task_steps(tid)
        report = (task.get('result') or {}).get('report') or ''
        partial = '\n\n'.join(s['step_id'] + ' · ' + s['output']['text'] for s in steps
                              if isinstance(s.get('output'), dict) and s['output'].get('text'))
        text = report or partial
        reviews = [s['output']['transfer']['verdict'] for s in steps
                   if isinstance(s.get('output'), dict)
                   and isinstance(s['output'].get('transfer'), dict)
                   and 'verdict' in s['output']['transfer']]
        review = ('覆核需要處理' if 'needs_attention' in reviews else
                  '流程覆核通過' if reviews and all(v == 'pass' for v in reviews) else '尚無覆核結果')
        return dict(task=task, steps=steps, text=text, partial=task['state'] != 'succeeded',
                    review=review, can_rate=task['state'] in TERMINAL and bool(text))

    def feedback(self, tid):
        self.read(tid)
        with self.store.connection() as db:
            row = db.execute('SELECT * FROM outcome_feedback WHERE task_id=?', (tid,)).fetchone()
            return dict(row) if row else None

    def save_feedback(self, tid, rating, note=''):
        if rating not in {'usable', 'revise', 'unhelpful'}:
            raise ValueError('請選擇有效評價。')
        if not isinstance(note, str) or len(note) > 2000:
            raise ValueError('備註最多 2,000 字。')
        with self.workflows.engine._lock:
            if not self.read(tid)['can_rate']:
                raise ValueError('工作結束且有成果後才能評價。')
            now = stamp()
            with self.store.connection() as db:
                db.execute('''INSERT INTO outcome_feedback VALUES(?,?,?,?,?)
                    ON CONFLICT(task_id) DO UPDATE SET rating=excluded.rating,
                    note=excluded.note,updated_at=excluded.updated_at''', (tid, rating, note, now, now))

    def clear_feedback(self, tid):
        with self.workflows.engine._lock, self.store.connection() as db:
            db.execute('DELETE FROM outcome_feedback WHERE task_id=?', (tid,))

    def _signature(self, task):
        spec = copy.deepcopy(task['payload']['workflow'])
        spec.pop('occurrence', None)
        for step in spec['steps']:
            if step['kind'] == 'query' and step.get('date_mode') == 'previous_day':
                mapping = date_mapping(find_template(self.workflows.engine.query_catalog(), step['query_id']))
                if not mapping:
                    raise ValueError('日期映射已不存在，無法比較。')
                for key in mapping.values():
                    step['parameters'].pop(key, None)
        return spec

    def compare(self, tid):
        current = self.read(tid)
        task = current['task']
        result = dict(baseline_id=None, reason='', groups=[])
        if task['state'] != 'succeeded':
            result['reason'] = '本次工作尚未成功，暫不比較。'
            return result
        try:
            signature = self._signature(task)
            with self.store.connection() as db:
                candidates = db.execute("SELECT * FROM tasks WHERE kind='workflow' AND state='succeeded' AND id<>? AND finished_at<=? AND created_at<? ORDER BY finished_at DESC,created_at DESC,id DESC",
                    (tid, task['finished_at'], task['created_at'])).fetchall()
            baseline = None
            for row in candidates:
                previous = self.store.task(row['id'])
                if previous.get('schedule_id') != task.get('schedule_id'):
                    continue
                if self._signature(previous) == signature:
                    baseline = self.read(previous['id'])
                    break
            if baseline is None:
                result['reason'] = '沒有同流程版本、綁定及條件的成功基準。'
                return result
            result['baseline_id'] = baseline['task']['id']
            old = {s['step_id']: s for s in baseline['steps']}
            for step in current['steps']:
                output = step.get('output') or {}
                if 'query_result' not in output:
                    continue
                group = dict(step_id=step['step_id'], rows=[], reason='')
                result['groups'].append(group)
                try:
                    a = old[step['step_id']]['output']['query_result']
                    b = output['query_result']
                    if a['columns'] != b['columns'] or a.get('source_label') != b.get('source_label') or a.get('query_ref') != b.get('query_ref'):
                        raise ValueError('欄位或來源不一致，無法比較。')
                    x, y = [json.loads(report_input(v).split('\n', 1)[1]) for v in (a, b)]
                    group.update(previous=x, current=y, same_period=x['parameters'] == y['parameters'])
                    if not x['row_count'] or not y['row_count']:
                        raise ValueError('其中一次為空資料，不將空資料推定為零。')
                    for key in [None, *x['numeric_totals']]:
                        before, after = ((str(x['row_count']), str(y['row_count'])) if key is None
                                         else (x['numeric_totals'][key], y['numeric_totals'][key]))
                        with localcontext() as ctx:
                            ctx.prec = max(50, len(before) + len(after) + 10)
                            delta = format(Decimal(after) - Decimal(before), 'f')
                        group['rows'].append(('筆數' if key is None else key, before, after, delta))
                except ValueError as exc:
                    group['reason'] = str(exc)
                except (KeyError, TypeError):
                    group['reason'] = '資料空白、截斷、欄位或數值無法驗證，無法比較。'
            if not result['groups']:
                result['reason'] = '這次流程沒有可比較的查詢數值。'
        except (ValueError, KeyError, TypeError):
            result['reason'] = '流程定義或日期映射已變更，無法比較。'
        return result
