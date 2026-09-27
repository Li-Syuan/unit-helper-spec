"""Explicitly approved, trial-only daily reports; no company adapter changes."""
import copy
import re
import time
from datetime import timedelta
from decimal import Decimal, InvalidOperation, localcontext

from .core import Engine, TAIPEI, _NOT_DISPATCHED, dumps, stamp, uid, utcnow
from .gateways import DemoQueries

REPORT_BINDING = {'profile_id': 'groq-trial', 'revision': 1}
REPORT_FAILURE = '查詢結果已保留；Groq 日報未完成，請檢查連線或額度後手動重試。'


def report_input(result):
    """Only exact local aggregates leave the machine; never forward detail rows."""
    if result.get('truncated'):
        raise ValueError('查詢結果已截斷，不能產生完整日報；原始結果已保留。')
    rows, columns = result.get('rows'), result.get('columns')
    if not isinstance(rows, list) or not isinstance(columns, list):
        raise ValueError('查詢結果格式無效；原始結果已保留。')
    names = [column.get('name') for column in columns if isinstance(column, dict)]
    if len(names) != len(columns) or len(set(names)) != len(names) or any(not isinstance(n, str) for n in names):
        raise ValueError('查詢欄位格式無效；原始結果已保留。')
    numeric = {column['name']: Decimal(0) for column in columns if column.get('type') in ('integer', 'decimal', 'number')}
    for row in rows:
        if isinstance(row, dict) and set(row) == set(names):
            values = row
        elif isinstance(row, list) and len(row) == len(names):
            values = dict(zip(names, row))
        else:
            raise ValueError('查詢欄列不一致；原始結果已保留。')
        for name in numeric:
            value = values[name]
            try:
                if isinstance(value, bool) or not isinstance(value, (str, int)):
                    raise InvalidOperation
                number = Decimal(str(value))
                if not number.is_finite():
                    raise InvalidOperation
                # Exact addition without the default Decimal precision rounding.
                with localcontext() as context:
                    context.prec = max(50, len(str(numeric[name])) + len(str(number)) + 10)
                    numeric[name] += number
            except (InvalidOperation, ValueError):
                raise ValueError('查詢數值格式無效；原始結果已保留。') from None
    payload = {'source': result.get('source_label'), 'query': result.get('query_ref'),
               'parameters': result.get('parameters'), 'fetched_at_utc': result.get('fetched_at_utc'),
               'truncated': False, 'row_count': len(rows),
               'numeric_totals': {name: format(value, 'f') for name, value in numeric.items()}}
    text = ('請用繁體中文整理合成資料日報，列出資料範圍、筆數、程式計算的合計與待確認事項。'
            '這是合計資料，不含逐筆明細；不得推論異常、趨勢、原因、負責人或期限。\n' + dumps(payload))
    if len(text) > 6000:
        raise ValueError('合計資料超過日報上限；未傳送或截斷資料，原始結果已保留。')
    return text


class ReportEngine(Engine):
    """Used only by the isolated Groq entrypoint. Approval is a local capability."""

    def __init__(self, *args, **kwargs):
        self._report_previews = {}
        super().__init__(*args, **kwargs)
        # The inherited recovery fails interrupted work without retrying it.
        with self.store.connection() as db:
            for row in db.execute("SELECT * FROM tasks WHERE state='failed' AND schedule_id IS NOT NULL"):
                task = self.store.decode(row)
                if task['payload'].get('_report'):
                    self._notify_result(db, task, 'failed', task.get('result'))

    def _report_binding(self, binding):
        if not isinstance(binding, dict) or binding != REPORT_BINDING or type(binding.get('revision')) is not int:
            raise ValueError('日報只能使用目前 Groq 試用助理版本。')
        if self.assistant_router is None or self.binding_validator is None:
            raise ValueError('日報助理尚未設定。')
        self.binding_validator(binding)

    def _report_schedule(self, schedule):
        metadata = schedule['parameters'].get('_report')
        if not isinstance(metadata, dict) or set(metadata) != {'version', 'binding'} or type(metadata['version']) is not int or metadata['version'] != 1:
            raise ValueError('日報設定已失效，請重新預覽及確認。')
        self._report_binding(metadata['binding'])
        if not isinstance(schedule['query_id'], str) or schedule['query_id'] not in {item['id'] for item in DemoQueries().catalog()}:
            raise ValueError('日報只允許三項本機合成查詢。')
        if schedule['parameters'].get('_date_mode') != 'previous_day' or schedule.get('frequency', 'daily') != 'daily':
            raise ValueError('試用日報僅支援每日查詢前一日資料。')
        if not self.schedule_date_mapping(schedule['query_id']):
            raise ValueError('日報模板未宣告日期範圍。')
        return metadata

    def preview_report(self, spec, binding):
        with self._lock:
            self._ensure_open()
            self._report_previews = {key: value for key, value in self._report_previews.items()
                                     if value['schedule_id'] or value['expires'] > time.monotonic()}
            self._report_binding(binding)
            if not isinstance(spec, dict) or set(spec) != {'query_id', 'parameters', 'time_hhmm', 'name'}:
                raise ValueError('請先補齊日報查詢、条件、時間及名稱。')
            name, at = spec['name'], spec['time_hhmm']
            if not isinstance(name, str) or not name.strip() or len(name) > 120:
                raise ValueError('日報名稱需為 1～120 字。')
            if not isinstance(at, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', at):
                raise ValueError('日報時間需為 HH:MM（台北時間）。')
            if not isinstance(spec['parameters'], dict) or any(str(key).startswith('_') for key in spec['parameters']):
                raise ValueError('日報參數格式無效。')
            schedule = dict(copy.deepcopy(spec), frequency='daily')
            schedule['parameters'].update(_date_mode='previous_day', _report={'version': 1, 'binding': copy.deepcopy(binding)})
            effective = self._schedule_parameters(schedule, utcnow())
            token = uid()
            preview = dict(copy.deepcopy(spec), parameters=effective, token=token,
                           binding=copy.deepcopy(binding), expires_at=stamp(utcnow() + timedelta(minutes=10)))
            self._report_previews[token] = {'preview': copy.deepcopy(preview), 'schedule': schedule,
                                            'expires': time.monotonic() + 600, 'schedule_id': None}
            return preview

    def confirm_report(self, token):
        with self._lock:
            self._ensure_open()
            item = self._report_previews.get(token) if isinstance(token, str) else None
            if item is None:
                raise ValueError('日報確認已取消或失效，請重新預覽。')
            if item['schedule_id']:
                return item['schedule_id']
            if item['expires'] <= time.monotonic():
                self._report_previews.pop(token, None)
                raise ValueError('日報確認已過期，請重新預覽。')
            s = item['schedule']
            self._schedule_parameters(s, utcnow())
            record_id = uid()
            with self.store.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('''INSERT INTO schedules(id,name,query_id,parameters,frequency,time_hhmm,
                              weekday,notify_rule,enabled,next_fire,created_at)
                              VALUES(?,?,?,?,'daily',?,0,'nonempty_on_change',1,?,?)''',
                           (record_id, s['name'], s['query_id'], dumps(s['parameters']), s['time_hhmm'],
                            stamp(self._next_fire(s, utcnow())), stamp()))
            item['schedule_id'] = record_id
            return record_id

    def cancel_report(self, token):
        with self._lock:
            item = self._report_previews.get(token) if isinstance(token, str) else None
            if item and not item['schedule_id']:
                self._report_previews.pop(token, None)

    def _schedule_parameters(self, schedule, occurrence):
        if '_report' not in schedule['parameters']:
            return super()._schedule_parameters(schedule, occurrence)
        self._report_schedule(schedule)
        clean = dict(schedule, parameters=dict(schedule['parameters']))
        clean['parameters'].pop('_report')
        return super()._schedule_parameters(clean, occurrence)

    def set_schedule_date_mode(self, schedule_id, mode):
        if '_report' in self.store.schedule(schedule_id)['parameters'] and mode != 'previous_day':
            raise ValueError('已批准的日報固定查詢前一日；需要修改時請建立新日報。')
        return super().set_schedule_date_mode(schedule_id, mode)

    def _new_task(self, db, kind, payload, conversation_id=None, request_id=None, plan_id=None, schedule_id=None):
        if schedule_id:
            schedule = self.store.decode(db.execute('SELECT * FROM schedules WHERE id=?', (schedule_id,)).fetchone())
            if '_report' in schedule['parameters']:
                metadata = self._report_schedule(schedule)
                payload = dict(payload, _binding=copy.deepcopy(metadata['binding']), _report=copy.deepcopy(metadata))
        return super()._new_task(db, kind, payload, conversation_id, request_id, plan_id, schedule_id)

    def _claim_occurrence(self, db, schedule, key, occurrence):
        if '_report' in schedule['parameters']:
            existing = db.execute('SELECT 1 FROM occurrences WHERE schedule_id=? AND scheduled_at=?', (schedule['id'], key)).fetchone()
            if existing:
                return None
            pending = [task_id for future, task_id in self._future_tasks.items() if not future.done()]
            if any(db.execute('SELECT 1 FROM tasks WHERE id=? AND schedule_id=?', (task_id, schedule['id'])).fetchone() for task_id in pending):
                db.execute("INSERT INTO occurrences VALUES(?,?,?,'skipped_overlap',NULL)", (uid(), schedule['id'], key))
                return None
        return super()._claim_occurrence(db, schedule, key, occurrence)

    def _work(self, task_id):
        task = self.store.task(task_id)
        if not task['schedule_id'] or not task['payload'].get('_report'):
            return super()._work(task_id)
        with self._lock, self.store.connection() as db:
            if not db.execute("UPDATE tasks SET state='running' WHERE id=? AND state='queued'", (task_id,)).rowcount:
                return
            db.execute("UPDATE occurrences SET state='running' WHERE task_id=?", (task_id,))
        result = None
        try:
            self._report_schedule(self.store.schedule(task['schedule_id']))
            self._report_binding(task['payload'].get('_binding'))
            self._validate('query', task['payload'])
            with self._lock:
                if self._closed or self.store.task(task_id)['state'] != 'running':
                    return
            result = self.query_runner(task['payload']['query_id'], task['payload']['parameters'])
            if not isinstance(result, dict) or not isinstance(result.get('rows'), list):
                raise ValueError('Invalid query result')
            result = dict(result, summary_status='pending')
            with self._lock, self.store.connection() as db:
                if not db.execute("UPDATE tasks SET result=? WHERE id=? AND state='running'", (dumps(result), task_id)).rowcount:
                    return
            try:
                text = report_input(result)
            except ValueError as exc:
                result.update(summary_status='failed', summary_error=str(exc))
            else:
                if not result['rows']:
                    result.update(summary='本次合成查詢沒有資料（0 筆），未呼叫 AI；請核對日期與查詢條件。', summary_status='succeeded')
                else:
                    try:
                        summary = self._dispatch_assistant(task_id, [{'role': 'user', 'content': text}], 'summarize')
                        if summary is _NOT_DISPATCHED:
                            return
                        if not isinstance(summary, str) or not summary.strip():
                            raise ValueError('Empty report')
                        result.update(summary=summary, summary_status='succeeded')
                    except Exception:
                        result.update(summary_status='failed', summary_error=REPORT_FAILURE)
            if result['summary_status'] == 'failed':
                self._finish(task_id, 'failed', result=result, error=result['summary_error'])
            else:
                self._finish(task_id, 'succeeded', result=result)
        except Exception:
            self._finish(task_id, 'failed', result=result, error='日報查詢失敗；未自動重試。錯誤編號 REPORT_QUERY_FAILED。')

    def _notify_result(self, db, task, state, result):
        if not task['payload'].get('_report'):
            return super()._notify_result(db, task, state, result)
        name = db.execute('SELECT name FROM schedules WHERE id=?', (task['schedule_id'],)).fetchone()['name']
        outcome = '已完成，請查看日報。' if state == 'succeeded' and result and result.get('summary_status') == 'succeeded' else '未完成，請查看工作與保留的查詢結果。'
        if state == 'cancelled':
            outcome = '已取消；遠端請求可能仍在結束中。'
        db.execute('INSERT OR IGNORE INTO notifications VALUES(?,?,?,?,0,?)',
                   (uid(), 'task:' + task['id'] + ':result', task['id'], '日報「' + name + '」' + outcome, stamp()))

    def cancel_task(self, task_id):
        with self._lock:
            before = self.store.task(task_id)
            super().cancel_task(task_id)
            if before['state'] in {'queued', 'running'} and before['payload'].get('_report'):
                with self.store.connection() as db:
                    self._notify_result(db, before, 'cancelled', before.get('result'))

    def close(self, wait=False):
        super().close(wait=wait)
        with self._lock, self.store.connection() as db:
            for row in db.execute("SELECT * FROM tasks WHERE state='cancelled' AND schedule_id IS NOT NULL"):
                task = self.store.decode(row)
                if task['payload'].get('_report'):
                    self._notify_result(db, task, 'cancelled', task.get('result'))
