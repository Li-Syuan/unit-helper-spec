"""Local, bounded diagnostic evidence; never an authority or a remote retry engine."""
import contextvars
import copy
import functools
import hashlib
import inspect
import json
import os
import re
import sqlite3
import tempfile
import threading
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .assistant_errors import AssistantFailure, LABELS, STAGES
from .core import stamp

CHECKS = {'chat': ('聊天', 2), 'routing': ('需求辨識', 2), 'work': ('工作格式', 3),
          'autonomous': ('自主決策', 3), 'search': ('搜尋', 4)}
STATUSES = {'running', 'passed', 'failed', 'cancelled', 'incomplete'}
CODES = set(LABELS) | {'CONTEXT_ASSERTION', 'FORMAT_ASSERTION', 'CANCELLED', 'INCOMPLETE', 'NO_DETAIL'}
PHASES = STAGES | {'chat_assertion', 'routing_assertion', 'work_assertion', 'autonomous_assertion', 'search_assertion'}
HINTS = {
    'AUTHENTICATION': '核對這位助理使用的金鑰；不要將金鑰貼入工作單。',
    'FORBIDDEN': '請服務管理者確認此金鑰對這位助理的權限。',
    'NOT_FOUND': '核對端點、Assistant ID 與遠端資源；尚不能確定哪一項不存在。',
    'RATE_LIMIT': '確認服務額度與頻率限制；沒有自動重送。',
    'TRANSPORT': '請部署者檢查網路、代理及信任鏈；目前不能確定是 CA 問題。',
    'TIMEOUT': '先檢查原請求是否已在遠端執行，勿直接重新派發。',
    'LOCAL_SETUP': '先修正本機連線或金鑰設定，再明確啟動測試。',
    'FORMAT': '對照已核准的服務契約與回覆解析位置。',
    'FORMAT_ASSERTION': '比對合成測試的 JSON 格式、必要欄位及工具收據；不放寬斷言。',
    'CONTEXT_ASSERTION': '確認同一 thread 的兩輪回覆及訊息選取；不要改成每輪新建 thread。',
    'CANCELLED': '檢查已取消；待真實請求收尾後，再確認遠端狀態。',
    'INCOMPLETE': '檢查中斷或紀錄不完整；不能推定成功或尚未送出。',
}
_current = contextvars.ContextVar('qa_diagnostic_check', default=None)


def failure_details(session, exc, phase, cancelled=False):
    from .support import record
    code = 'CANCELLED' if cancelled else (exc.code if isinstance(exc, AssistantFailure) else
            ('FORMAT_ASSERTION' if isinstance(exc, (ValueError, TypeError, KeyError)) else 'UNKNOWN'))
    return {'code': code, 'stage': exc.stage if isinstance(exc, AssistantFailure) else phase,
            'http_status': exc.http_status if isinstance(exc, AssistantFailure) else None,
            'incident': record(session.directory, 'ui', exc)['id']}


def measured(kind):
    """All existing probe entry points share the same record and unresolved-request guard."""
    def decorate(fn):
        signature = inspect.signature(fn)
        @functools.wraps(fn)
        def invoke(owner, *args, **kwargs):
            expected = kwargs.pop('expected_revision', None)
            bound = signature.bind(owner, *args, **kwargs);bound.apply_defaults()
            values = bound.arguments
            s = getattr(owner, 's', None) or owner.session
            diag = getattr(s, 'diagnostics', None)
            if diag is None or values.get('consent') is not True or values['pid'] == 'demo':
                return fn(owner, *args, **kwargs)
            checks = (['search'] if values.get('search') else ['work']) if kind == 'work' else [kind]
            if kind == 'chat' and values.get('routing'):checks.append('routing')
            return diag.measure(values['pid'], checks, lambda: fn(owner, *args, **kwargs),
                                values.get('cancelled'), expected)
        return invoke
    return decorate


def diagnostic_respond(session, messages, purpose, binding, *, context):
    current = _current.get()
    if current is None:return session.profiles.respond(messages, purpose, binding, context=context)
    diag, handle = current
    # Validate the binding again after reserving the check and before every dispatch.
    if binding['revision'] != handle['revision']:raise ValueError('設定版本已變更，請重新查看診斷。')
    from .assistants_gateway import session_context
    key, rid, _, _ = session_context(binding, purpose, context)
    ref = {'key': key, 'rid': rid, 'received': False, 'unsent': False}
    handle['requests'].append(ref);diag.checkpoint(handle)
    try:
        result = session.profiles.respond(messages, purpose, binding, context=context)
        ref['received'] = True;diag.checkpoint(handle)
        return result
    except AssistantFailure as exc:
        ref['unsent'] = not exc.sent;diag.checkpoint(handle)
        raise


class ConnectionDiagnostics:
    MAX_BYTES = 1024 * 1024

    def __init__(self, session):
        self.s = session;self.path = session.directory / 'connection-diagnostics.json'
        self.lock = threading.RLock();self.active = {};self.warning = ''
        self.data = {'version': 1, 'profiles': {}, 'dialogue_errors': {}}
        try:
            if self.path.is_symlink():raise ValueError()
            if self.path.exists():
                if self.path.stat().st_size > self.MAX_BYTES:raise ValueError()
                self.data = self._clean(json.loads(self.path.read_text('utf-8')))
        except Exception:self.warning = '診斷摘要無法讀取；沒有可用紀錄，既有對話與能力證據不受影響。'

    @staticmethod
    def alias(pid):return '助理-' + hashlib.sha256(pid.encode('utf-8')).hexdigest()[:12]

    @staticmethod
    def _safe_row(row):
        if not isinstance(row, dict) or row.get('status') not in STATUSES:raise ValueError()
        time = row.get('time')
        if not isinstance(time, str) or len(time) > 40:raise ValueError()
        time = datetime.fromisoformat(time).isoformat()
        code = row.get('code') if row.get('code') in CODES else 'UNKNOWN'
        stage = row.get('stage') if row.get('stage') in PHASES else 'remote_request'
        incident = row.get('incident')
        status = row.get('http_status')
        refs = row.get('requests', [])
        if not isinstance(refs, list) or len(refs) > 8:raise ValueError()
        cleaned = []
        for ref in refs:
            if not isinstance(ref, dict) or not re.fullmatch('[a-f0-9]{64}', ref.get('key', '')):raise ValueError()
            if not re.fullmatch('[a-zA-Z0-9:_-]{1,160}', ref.get('rid', '')):raise ValueError()
            cleaned.append({'key': ref['key'], 'rid': ref['rid'], 'received': ref.get('received') is True, 'unsent': ref.get('unsent') is True})
        return {'status': row['status'], 'time': time, 'code': code, 'stage': stage,
                'http_status': status if type(status) is int and 400 <= status <= 599 else None,
                'incident': incident if isinstance(incident, str) and re.fullmatch('[a-f0-9]{32}', incident) else None,
                'requests': cleaned}

    @classmethod
    def _clean(cls, data):
        if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('profiles'), dict) or len(data['profiles']) > 128:raise ValueError()
        result = {'version': 1, 'profiles': {}, 'dialogue_errors': {}}
        for pid, versions in data['profiles'].items():
            if not re.fullmatch('助理-[a-f0-9]{12}', pid) or not isinstance(versions, dict) or len(versions) > 2:raise ValueError()
            result['profiles'][pid] = {}
            for revision, rows in versions.items():
                if not re.fullmatch('[1-9][0-9]{0,8}', revision) or not isinstance(rows, dict) or set(rows) - set(CHECKS):raise ValueError()
                result['profiles'][pid][revision] = {key: cls._safe_row(row) for key, row in rows.items()}
        errors = data.get('dialogue_errors', {})
        if not isinstance(errors, dict) or len(errors) > 128:raise ValueError()
        for key, row in errors.items():
            if not re.fullmatch('[a-f0-9]{64}', key):raise ValueError()
            result['dialogue_errors'][key] = cls._safe_row(row)
        return result

    def _save(self):
        temporary = None
        try:
            if self.path.is_symlink() or self.path.parent.is_symlink():raise ValueError()
            content = json.dumps(self._clean(self.data), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            if len(content) > self.MAX_BYTES:raise ValueError()
            with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix='.diagnostics-', delete=False) as f:
                temporary = Path(f.name);f.write(content);f.flush();os.fsync(f.fileno())
            os.replace(temporary, self.path);self.warning = '';return True
        except Exception:
            self.warning = '診斷摘要保存失敗；本次畫面仍可查看，重新開啟後可能沒有此紀錄。';return False
        finally:
            if temporary is not None:
                try:temporary.unlink(missing_ok=True)
                except OSError:pass

    def checkpoint(self, handle):
        with self.lock:
            versions = self.data['profiles'].setdefault(handle['alias'], {})
            rows = versions.setdefault(str(handle['revision']), {})
            for check, row in handle['rows'].items():rows[check] = dict(row, requests=copy.deepcopy(handle['requests']))
            for revision in sorted(versions, key=int)[:-2]:del versions[revision]
            while len(self.data['profiles']) > 128:del self.data['profiles'][next(iter(self.data['profiles']))]
            return self._save()

    def _unresolved(self, row):
        if row.get('status') in {'incomplete', 'running'} and not row.get('requests'):return True
        for ref in row.get('requests', []):
            if ref['received'] or ref['unsent']:continue
            path = self.s.directory / 'assistant-sessions.sqlite3'
            try:
                if not path.exists() or path.is_symlink():return True
                with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
                    rec = db.execute('SELECT data FROM requests WHERE session_id=? AND id=?', (ref['key'], ref['rid'])).fetchone()
                data = json.loads(rec[0]) if rec else {}
                if data.get('remote_terminal') is not True:return True
            except Exception:return True
        return False

    def _busy(self):
        return self.s.closed or self.s.engine.has_inflight() or self.s.dialogue.has_inflight() or self.s.company_probe.has_inflight()

    def dialogue_failure(self, tid, rid, exc, cancelled):
        """Best-effort sidecar incident correlation; never alter the original request outcome."""
        details = failure_details(self.s, exc, 'remote_request', cancelled)
        key = hashlib.sha256((tid + '\0' + rid).encode('utf-8')).hexdigest()
        with self.lock:
            errors = self.data['dialogue_errors']
            errors[key] = dict(details, status='cancelled' if cancelled else 'failed', time=stamp(), requests=[])
            while len(errors) > 128:del errors[next(iter(errors))]
            self._save()

    def _chat_unresolved(self, pid, revision):
        # Read local request evidence only. Missing receipt is never evidence of no dispatch.
        from .assistant_errors import decode_failure
        from .assistants_gateway import session_context
        with self.s.dialogue.store.connect() as db:
            rows = db.execute("SELECT r.*,t.id AS tid FROM requests r JOIN threads t ON t.id=r.thread_id WHERE t.assistant_id=? AND r.status!='completed'",
                              (f'company:{pid}:{revision}',)).fetchall()
        if not rows:return False
        binding = self.s.profiles.snapshot(pid)
        for row in rows:
            failure = decode_failure(row['error_code'])
            if failure is not None and not failure.sent:continue
            key, rid, _, _ = session_context(binding, 'chat', {'conversation_id': 'dialogue:' + row['tid'], 'request_id': row['request_id']})
            if self._unresolved({'requests': [{'key': key, 'rid': rid, 'received': False, 'unsent': False}]}):return True
        return False

    def measure(self, pid, checks, operation, cancelled, expected):
        self.s.assert_identity();binding = self.s.profiles.snapshot(pid)
        revision = binding['revision']
        if expected is not None and (type(expected) is not int or expected != revision):raise ValueError('設定版本已變更，請重新查看診斷。')
        if self._chat_unresolved(pid, revision):raise ValueError('原對話請求結果尚未釐清，請回原對話檢查，不另派發測試。')
        with self.lock:
            if pid in self.active or self._busy():raise ValueError('背景請求尚未結束，不能開始重測。')
            versions = self.data['profiles'].get(self.alias(pid), {})
            for row in versions.get(str(revision), {}).values():
                if self._unresolved(row):raise ValueError('原檢查送出結果尚未釐清；請先檢查原請求，不能盲目重測。')
            handle = {'alias': self.alias(pid), 'revision': revision, 'requests': [],
                      'rows': {check: {'status': 'running', 'time': stamp(), 'code': 'NO_DETAIL', 'stage': 'preflight'} for check in checks}}
            self.active[pid] = handle;self.checkpoint(handle)
        token = _current.set((self, handle))
        try:
            result = operation()
            failed = next((r for r in result.get('checks', []) if r.get('status') in {'failed', 'cancelled'}), {})
            stopped = bool(cancelled and cancelled())
            for check, row in handle['rows'].items():
                ok = result.get('routing_passed') if check == 'routing' else result.get('passed')
                detail = failed
                if not ok and not stopped and not detail:
                    detail = failure_details(self.s, ValueError('synthetic assertion failed'), check + '_assertion')
                row.update(status='cancelled' if stopped else ('passed' if ok is True else 'failed'), time=stamp(),
                           code='CANCELLED' if stopped else ('NO_DETAIL' if ok else detail.get('code', 'FORMAT_ASSERTION')),
                           stage=detail.get('stage', check + '_assertion'), http_status=detail.get('http_status'),
                           incident=detail.get('incident'))
            return result
        except Exception as exc:
            details = failure_details(self.s, exc, 'preflight', bool(cancelled and cancelled()))
            for row in handle['rows'].values():row.update(details, status='cancelled' if details['code'] == 'CANCELLED' else 'failed', time=stamp())
            raise
        finally:
            _current.reset(token)
            with self.lock:self.checkpoint(handle);self.active.pop(pid, None)

    def _target(self, profile_id=None, thread_id=None):
        if bool(profile_id) == bool(thread_id):raise ValueError('請指定一位助理或一段對話。')
        thread = None;revision = None
        if thread_id:
            thread = self.s.dialogue.state(thread_id)
            parts = thread['assistant_id'].split(':')
            if len(parts) != 3 or parts[0] != 'company' or not parts[2].isdigit():raise ValueError('示範對話沒有遠端連線診斷。')
            profile_id = parts[1];revision = int(parts[2])
        profile = next((r for r in self.s.profiles.items(True) if r['id'] == profile_id and r['id'] != 'demo'), None)
        if profile is None:raise ValueError('助理設定不存在。')
        return profile, thread, revision

    def status(self, profile_id=None, thread_id=None):
        self.s.assert_identity();profile, thread, source_revision = self._target(profile_id, thread_id)
        pid = profile['id'];revision = profile['revision'];busy = bool(self._busy())
        activation = next((r for r in self.s.activation.status()['chat_profiles'] if r['id'] == pid), {})
        roles = set(activation.get('skill_roles', []))
        proofs = {'chat': activation.get('chat_status') == 'passed', 'routing': activation.get('routing_status') == 'passed',
                  'work': {'planner', 'compose', 'assess'} <= roles, 'autonomous': 'autonomous' in roles, 'search': 'rag' in roles}
        with self.lock:
            versions = copy.deepcopy(self.data['profiles'].get(self.alias(pid), {}));active = pid in self.active;warning = self.warning
        current = versions.get(str(revision), {});rows = [];blocked = any(self._unresolved(r) for r in current.values()) or self._chat_unresolved(pid, revision)
        for check, (label, limit) in CHECKS.items():
            row = current.get(check);status = row['status'] if row else ('passed' if proofs[check] else 'not_tested')
            evidence_revision = revision if row or proofs[check] else None
            if row is None and not proofs[check] and any(check in r for r in versions.values()):
                previous, prior = next((v, r) for v, r in sorted(versions.items(), key=lambda x: int(x[0]), reverse=True) if check in r)
                row = prior[check];evidence_revision = int(previous);status = 'stale'
            row = row or {}
            if status == 'running' and not active:status = 'incomplete'
            if status == 'passed' and not proofs[check]:status = 'incomplete'
            code = row.get('code') or 'NO_DETAIL'
            allowed = not busy and not active and not blocked and profile.get('enabled', True)
            if check == 'search':allowed = allowed and bool(activation.get('search_approved'))
            if check == 'autonomous':allowed = allowed and proofs['work']
            if thread and (thread['read_only'] or source_revision != revision):allowed = False
            summary = ('合成斷言通過；實際內容品質仍需核對。' if status == 'passed' else
                       '設定已變更，舊結果不代表目前能力。' if status == 'stale' else
                       '檢查中斷；不能推定成功或未送出。' if status == 'incomplete' else
                       '沒有可用紀錄。' if not row else LABELS.get(code, '請依安全代碼與檢查階段定位；原因尚未完全確定。'))
            rows.append(dict(check=check, label=label, status=status, evidence_revision=evidence_revision, time=row.get('time'), code=code,
                             stage=row.get('stage'), http_status=row.get('http_status'), incident=row.get('incident'), summary=summary,
                             next_step='原請求尚未釐清，請先檢查原請求；不提供盲目重測。' if blocked else
                             ('此項已通過，無須重測；可使用已驗證功能。' if status == 'passed' else HINTS.get(code, '可明確啟動此項合成測試。')),
                             can_retest=bool(allowed), request_limit=limit))
        request = None
        if thread and thread.get('request'):
            raw = thread['request'];code = raw.get('error_code')
            key = hashlib.sha256((thread['id'] + '\0' + raw['id']).encode('utf-8')).hexdigest()
            with self.lock:detail = self.data['dialogue_errors'].get(key, {})
            if code not in CODES:code = detail.get('code', 'UNKNOWN')
            request = {key: raw.get(key) for key in ('state', 'remote_state', 'retry_unsent', 'recoverable')}
            request.update(busy=thread['busy'], read_only=thread['read_only'], code=code if code in CODES else 'UNKNOWN',
                           stage=raw.get('error_stage') if raw.get('error_stage') in PHASES else None,
                           http_status=raw.get('error_http_status'), incident=detail.get('incident'), time=detail.get('time'),
                           summary=HINTS.get(code, '請回到原對話，依已知收據檢查或取回結果；未知送出不自動重送。'))
        return {'profile_id': pid, 'revision': revision, 'name': profile['name'], 'assistant_id': activation.get('assistant_id'),
                'rows': rows, 'warnings': [warning] if warning else [], 'request': request, 'busy': busy or active,
                'report_available': True, 'search_approved': bool(activation.get('search_approved')), 'source_revision': source_revision}

    def retest(self, profile_id, revision, check, consent=False):
        if consent is not True or check not in CHECKS:raise ValueError('請選定檢查項目並明確同意合成請求。')
        state = self.status(profile_id=profile_id)
        if type(revision) is not int or state['revision'] != revision:raise ValueError('設定版本已變更，請重新查看診斷。')
        if not next(r for r in state['rows'] if r['check'] == check)['can_retest']:raise ValueError('此項目前不能重測，請先處理診斷列出的缺項或原請求。')
        if check in {'chat', 'routing'}:self.s.activation.test(profile_id, True, routing=check == 'routing', expected_revision=revision)
        elif check == 'autonomous':self.s.agents.autonomy_probe(profile_id, True, expected_revision=revision)
        else:self.s.agents.probe(profile_id, True, search=check == 'search', expected_revision=revision)
        return self.status(profile_id=profile_id)

    def report(self, **target):
        from . import __version__
        state = self.status(**target)
        # Explicit output fields: never serialize status, profiles, messages or an exception.
        lines = ['# QA agent 修復工作單', '', f'- 版本：{__version__}', f'- 匿名助理：{self.alias(state["profile_id"])}',
                 f'- 連線修訂：{state["revision"]}', '- 真實服務／來源品質／現場使用性：另行驗收', '',
                 '| 檢查 | 狀態 | 證據修訂 | 時間 | 安全代碼 | 階段 | HTTP | 錯誤編號 |', '|---|---|---|---|---|---|---|---|']
        for row in state['rows']:
            lines.append('| ' + ' | '.join(str(v) if v is not None else '沒有可用紀錄' for v in
                         (row['label'], row['status'], row['evidence_revision'], row['time'], row['code'], row['stage'], row['http_status'], row['incident'])) + ' |')
        if state['request']:
            r = state['request']
            lines += ['', '## 原對話請求', f'- 來源對話修訂：{state["source_revision"]}', f'- 安全代碼：{r["code"]}；階段：{r["stage"] or "沒有可用紀錄"}',
                      f'- 時間：{r["time"] or "沒有可用紀錄"}；錯誤編號：{r["incident"] or "沒有可用紀錄"}',
                      '- 恢復方式：回原對話檢查收據；已知結果才可取回。未知送出不能重新派發。']
        lines += ['', '## 建議處理順序', '', '1. 確認本機環境與鎖檔；不要重新安裝或放寬 TLS 來猜測原因。',
                  '2. 先處理聊天；格式或搜尋失敗不代表聊天不能使用。工具核准與實測分開。']
        for row in state['rows']:
            if row['status'] not in {'passed', 'not_tested'}:lines.append(f'- {row["label"]}：{row["next_step"]}')
        lines += ['3. 保留 request ID／收據／版本守護；診斷不是重送或執行授權。',
                  '4. 修改後只執行受影響測試；真實請求另由使用者同意，不能以合成通過替代。', '',
                  '## 定位與最小離線驗證', '',
                  '- desktop_app/activation.py：兩輪聊天與需求辨識。',
                  '- desktop_app/agent_jobs.py：工作格式、自主決策、搜尋收據斷言。',
                  '- desktop_app/assistants_gateway.py：Threads／Messages／Runs、核准搜尋及安全錯誤。',
                  '- desktop_app/dialogue_service.py：原請求檢查、恢復及確定未送出重試。',
                  '- desktop_app/connection_diagnostics.py：白名單摘要與工作單；不授予能力。', '', '```bat',
                  '.venv\\Scripts\\python.exe scripts/doctor.py',
                  '.venv\\Scripts\\python.exe scripts/test_runner.py --suite targeted --tests tests.test_connection_diagnostics',
                  '```', '', '依修改位置加選 tests.test_continuity、tests.test_agent_jobs、tests.test_assistants_gateway 或 tests.test_dialogue_recovery；不要無差別重跑 full。',
                  '', '沒有附上端點、Assistant ID、金鑰、對話、原始 HTTP 或絕對路徑。沒有自動上傳。']
        return {'markdown': '\n'.join(lines) + '\n'}

    def export(self, destination, **target):
        content = self.report(**target)['markdown'];path = Path(destination)
        # Native save dialogue chooses the destination; no model-supplied path and no silent overwrite.
        created = False
        try:
            with path.open('x', encoding='utf-8', newline='\n') as f:
                created = True;f.write(content)
        except Exception:
            if created:
                try:path.unlink()
                except OSError:pass
            raise
        return {'saved': True, 'path': str(path)}
