"""Company Assistants protocol: explicit sessions, bounded runs, no plugins.

The wire contract follows the supplied company Threads/Messages/Runs sample.
No company connection has been verified by this implementation's offline tests.
"""
import hashlib
import json
import ssl
import time
import uuid
from urllib.parse import urlsplit
from .assistant_sessions import AssistantSessions
from .gateways import GatewayError, PURPOSES, validated_messages


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def session_context(binding, purpose, context=None):
    context = dict(context or {})
    if context.get('run_id') or context.get('step_id'):
        fields = ('run_id', 'step_id')
        namespace = 'workflow'
    elif context.get('conversation_id'):
        fields = ('conversation_id',)
        namespace = 'conversation'
    else:
        fields = ('conversation_id',)
        namespace = 'isolated'
        context['conversation_id'] = uuid.uuid4().hex
    for field in fields:
        if not isinstance(context.get(field), str) or not context[field] or len(context[field]) > 512:
            raise GatewayError('公司對話缺少有效隔離識別。')
    request_id = context.get('request_id')
    if request_id is None:
        request_id = _digest([context['run_id'], context['step_id']]) if namespace == 'workflow' else uuid.uuid4().hex
    if not isinstance(request_id, str) or not request_id or len(request_id) > 512:
        raise GatewayError('公司請求識別不正確。')
    cancelled = context.get('cancelled', lambda: False)
    if not callable(cancelled):
        raise GatewayError('取消狀態檢查格式不正確。')
    key = _digest([binding, namespace, [context[f] for f in fields]])
    return key, request_id, cancelled, context.get('resume') is True


class AssistantsGateway:
    def __init__(self, config, api_key, ledger, binding, client=None, clock=None, sleep=None):
        from openai import OpenAI
        import httpx
        base = config.get('base_url', '')
        try:
            parsed = urlsplit(base)
            valid = (parsed.scheme == 'https' and parsed.hostname and not parsed.username and
                     not parsed.password and not parsed.query and not parsed.fragment and
                     parsed.hostname.lower().rstrip('.') not in {'openai.com', 'api.openai.com'})
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise GatewayError('請設定公司的 HTTPS Assistants 端點；網址不可含帳密。')
        self.assistant_id = config.get('assistant_id')
        if not isinstance(self.assistant_id, str) or not self.assistant_id.strip() or len(self.assistant_id) > 256:
            raise GatewayError('請設定公司 assistant ID。')
        if not isinstance(api_key, str) or not api_key.strip():
            raise GatewayError('尚未設定共用 API key。')
        self.timeout = config.get('timeout_seconds', 30)
        self.deadline_seconds = config.get('run_timeout_seconds', 600)
        self.poll_seconds = config.get('poll_seconds', 0.5)
        for value, low, high in ((self.timeout, 1, 120), (self.deadline_seconds, 1, 1800), (self.poll_seconds, 0.01, 10)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
                raise GatewayError('公司請求或輪詢時間設定不正確。')
        tls = ssl.create_default_context()
        if config.get('ca_bundle') is not None:
            try:
                tls.load_verify_locations(cafile=config['ca_bundle'])
            except (OSError, ssl.SSLError, TypeError):
                raise GatewayError('無法載入公司 CA；TLS 驗證不會停用。') from None
        self.client = client or OpenAI(base_url=base, api_key=api_key, max_retries=0,
            timeout=self.timeout, http_client=httpx.Client(verify=tls, timeout=self.timeout,
                                                          follow_redirects=False))
        self.ledger = ledger if isinstance(ledger, AssistantSessions) else AssistantSessions(ledger)
        self.binding = dict(binding)
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep

    def close(self):
        self.client.close()

    def _call(self, function, deadline, **kwargs):
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise GatewayError('公司工作等待逾時；未自動重送，請檢查遠端狀態。')
        return function(**kwargs, timeout=min(self.timeout, remaining))

    @staticmethod
    def _id(value):
        result = getattr(value, 'id', None)
        if not isinstance(result, str) or not result:
            raise GatewayError('公司服務缺少遠端識別；結果未明，不會自動重送。')
        return result

    def _cancel(self, key, session, rid, request, deadline):
        request['state'] = 'cancel_requested'
        self.ledger.save(key, session, rid, request)
        if request.get('run_id'):
            try:
                run = self._call(self.client.beta.threads.runs.cancel, deadline,
                                 thread_id=session['thread_id'], run_id=request['run_id'])
                if run.status in ('cancelled', 'completed', 'failed', 'expired', 'incomplete'):
                    request['remote_terminal'] = True
                    request['state'] = 'cancelled'
                    self.ledger.save(key, session, rid, request)
            except Exception:
                # Cancel is best effort; never claim the remote process stopped.
                pass
        raise GatewayError('已請求取消；遠端是否已停止請檢查狀態，晚到結果不會標為成功。')

    def respond(self, messages, purpose='chat', context=None):
        from openai import APIError, APIStatusError
        if purpose not in PURPOSES:
            raise GatewayError('不支援的助理操作。')
        clean = validated_messages(messages)
        if clean[-1]['role'] != 'user':
            raise GatewayError('公司對話最後一筆必須是使用者訊息。')
        key, rid, cancelled, resume = session_context(self.binding, purpose, context)
        digest = _digest([purpose, clean])
        hashes = [_digest(message) for message in clean]
        deadline = self.clock() + self.deadline_seconds
        with self.ledger.session(key):
            session = self.ledger.get_session(key) or {'thread_id': None, 'history': [], 'active': None}
            request = self.ledger.get_request(key, rid)
            if request:
                if request['digest'] != digest:
                    raise GatewayError('相同請求識別的內容已改變；未重新送出。')
                if request['state'] == 'completed':
                    return request['result']
                if request['state'] in ('cancel_requested', 'cancelled', 'failed', 'tools_blocked'):
                    raise GatewayError('此請求已停止或已取消，不能直接恢復或重新送出。')
                if not resume or not request.get('run_id'):
                    raise GatewayError('先前公司請求尚未釐清；請檢查遠端狀態，未重新送出。')
            else:
                previous = self.ledger.get_request(key, session['active']) if session['active'] else None
                if previous and previous['state'] != 'completed':
                    # A failed/cancelled run may still have accepted its input
                    # messages. Do not replay that history into the same thread.
                    raise GatewayError('此對話先前請求尚未完成；請恢復原請求或建立新對話，未重送歷史。')
                if session['history'] != hashes[:len(session['history'])]:
                    raise GatewayError('對話歷史與遠端記憶不一致；請建立新對話，未重送歷史。')
                if cancelled():
                    raise GatewayError('工作已取消；未傳送公司請求。')
                request = {'digest': digest, 'state': 'prepared', 'run_id': None,
                           'message_ids': [], 'remote_terminal': False}
                session['active'] = rid
                self.ledger.save(key, session, rid, request)
            try:
                if not request['run_id']:
                    if not session['thread_id']:
                        request['state'] = 'thread_outcome_unknown'
                        self.ledger.save(key, session, rid, request)
                        thread = self._call(self.client.beta.threads.create, deadline)
                        session['thread_id'] = self._id(thread)
                        self.ledger.save(key, session, rid, request)
                    for message in clean[len(session['history']):]:
                        if cancelled():
                            self._cancel(key, session, rid, request, deadline)
                        request['state'] = 'message_outcome_unknown'
                        self.ledger.save(key, session, rid, request)
                        remote = self._call(self.client.beta.threads.messages.create, deadline,
                                            thread_id=session['thread_id'], role=message['role'], content=message['content'])
                        request['message_ids'].append(self._id(remote))
                        self.ledger.save(key, session, rid, request)
                    if cancelled():
                        self._cancel(key, session, rid, request, deadline)
                    request['state'] = 'run_outcome_unknown'
                    self.ledger.save(key, session, rid, request)
                    run = self._call(self.client.beta.threads.runs.create, deadline,
                                     thread_id=session['thread_id'], assistant_id=self.assistant_id,
                                     additional_instructions=PURPOSES[purpose], tool_choice='none')
                    request.update(run_id=self._id(run), state='polling')
                    self.ledger.save(key, session, rid, request)
                else:
                    run = self._call(self.client.beta.threads.runs.retrieve, deadline,
                                     thread_id=session['thread_id'], run_id=request['run_id'])
                while True:
                    if cancelled():
                        self._cancel(key, session, rid, request, deadline)
                    if getattr(run, 'id', None) != request['run_id'] or getattr(run, 'thread_id', None) != session['thread_id']:
                        raise GatewayError('公司回覆工作識別不一致，已停止處理。')
                    status = getattr(run, 'status', None)
                    if status == 'completed':
                        break
                    if status == 'requires_action':
                        request['state'] = 'tools_blocked'
                        self.ledger.save(key, session, rid, request)
                        raise GatewayError('公司助理要求尚未核准的工具；未呼叫 pluginapi，請由維護者處理遠端工作。')
                    if status in ('cancelled', 'failed', 'expired', 'incomplete'):
                        request.update(state='cancelled' if status == 'cancelled' else 'failed', remote_terminal=True)
                        self.ledger.save(key, session, rid, request)
                        raise GatewayError('公司工作未完成（' + status + '）；未自動重試。')
                    if status not in ('queued', 'in_progress', 'cancelling'):
                        raise GatewayError('公司工作狀態不相容；請檢查遠端狀態。')
                    remaining = deadline - self.clock()
                    if remaining <= 0:
                        raise GatewayError('公司工作等待逾時；未自動重送，請檢查遠端狀態。')
                    self.sleep(min(self.poll_seconds, remaining))
                    run = self._call(self.client.beta.threads.runs.retrieve, deadline,
                                     thread_id=session['thread_id'], run_id=request['run_id'])
                result = self._read_text(session['thread_id'], request['run_id'], deadline)
                if cancelled():
                    self._cancel(key, session, rid, request, deadline)
                request.update(state='completed', result=result, remote_terminal=True)
                session['history'] = hashes + [_digest({'role': 'assistant', 'content': result})]
                self.ledger.save(key, session, rid, request)
                return result
            except APIStatusError as exc:
                label = '認證失敗' if exc.status_code in (401, 403) else 'HTTP ' + str(exc.status_code) + ' 錯誤'
                raise GatewayError('公司服務' + label + '；未自動重試或改用示範。') from None
            except APIError:
                raise GatewayError('公司請求失敗或逾時；結果可能未明，請檢查狀態，未自動重送。') from None
            except (AttributeError, TypeError, KeyError, ValueError) as exc:
                if isinstance(exc, GatewayError):
                    raise
                raise GatewayError('公司回傳格式不相容；未自動重送或改用示範。') from None

    def _read_text(self, thread_id, run_id, deadline):
        parts, seen, after = [], set(), None
        for _ in range(100):
            kwargs = {'thread_id': thread_id, 'order': 'asc', 'limit': 100}
            if after:
                kwargs['after'] = after
            page = self._call(self.client.beta.threads.messages.list, deadline, **kwargs)
            for message in page.data:
                if message.run_id != run_id or message.role != 'assistant':
                    continue
                for block in message.content:
                    if block.type != 'text' or not isinstance(block.text.value, str):
                        raise GatewayError('本次助理回覆包含不支援的內容格式，未當成成功文字。')
                    parts.append(block.text.value)
            if sum(map(len, parts)) > 200000:
                raise GatewayError('助理回覆超過顯示上限；未默默截斷。')
            if not page.has_more:
                text = '\n\n'.join(parts)
                if not text.strip():
                    raise GatewayError('本次工作沒有可用文字回覆，未使用其他工作的答案。')
                return text
            after = page.last_id
            if not isinstance(after, str) or not after or after in seen:
                raise GatewayError('公司訊息分頁格式不相容。')
            seen.add(after)
        raise GatewayError('公司訊息分頁超過上限；未默默截斷。')

    def inspect_request(self, purpose='chat', context=None, remote=False):
        key, rid, _, _ = session_context(self.binding, purpose, context)
        with self.ledger.session(key):
            session = self.ledger.get_session(key)
            request = self.ledger.get_request(key, rid)
            if not session or not request:
                return {'state': 'not_found', 'recoverable': False, 'remote_checked': False}
            checked = False
            if remote and request.get('run_id') and request['state'] != 'completed':
                try:
                    run = self._call(self.client.beta.threads.runs.retrieve, self.clock() + self.timeout,
                                     thread_id=session['thread_id'], run_id=request['run_id'])
                    if run.id != request['run_id'] or run.thread_id != session['thread_id']:
                        raise GatewayError('遠端工作識別不一致。')
                    checked = True
                    if run.status in ('completed', 'failed', 'expired', 'incomplete', 'cancelled'):
                        request['remote_terminal'] = True
                        if request['state'] in ('cancel_requested', 'cancelled'):
                            request['state'] = 'cancelled'
                        elif run.status != 'completed':
                            request['state'] = 'failed'
                    self.ledger.save(key, session, rid, request)
                except Exception:
                    raise GatewayError('無法確認遠端工作狀態；沒有重新執行。') from None
            return {'state': request['state'], 'recoverable': bool(request.get('run_id')) and
                    request['state'] not in ('failed', 'cancelled', 'cancel_requested', 'tools_blocked'),
                    'remote_checked': checked, 'remote_terminal': request.get('remote_terminal', False)}
