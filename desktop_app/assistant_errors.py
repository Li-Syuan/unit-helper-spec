"""Safe, allowlisted failure metadata. Never retain provider error bodies."""
from .gateways import GatewayError

STAGES = {'preflight', 'thread_create', 'message_create', 'run_create', 'run_poll',
          'messages_read', 'assistant_metadata', 'tool_call', 'tool_submit', 'remote_request'}
LABELS = {
    'LOCAL_SETUP': '本機連線設定尚未就緒，尚未送出',
    'AUTHENTICATION': '認證失敗，請核對此助理使用的 API key',
    'FORBIDDEN': '此金鑰沒有操作此助理的權限',
    'NOT_FOUND': '找不到指定助理或遠端資源，請核對端點與識別',
    'RATE_LIMIT': '服務限制請求頻率或額度',
    'TIMEOUT': '等待逾時，請檢查原請求狀態',
    'TRANSPORT': '網路連線失敗，請檢查原請求狀態',
    'FORMAT': '服務回覆格式不相容',
    'RUN_FAILED': '助理工作未完成',
    'UNKNOWN': '服務請求失敗',
}
REMOTE_CODES = {'server_error', 'rate_limit_exceeded', 'invalid_prompt',
                'max_completion_tokens', 'max_prompt_tokens'}


class AssistantFailure(GatewayError):
    def __init__(self, code, stage, *, sent=True, http_status=None, remote_code=None):
        self.code = code if code in LABELS else 'UNKNOWN'
        self.stage = stage if stage in STAGES else 'remote_request'
        # Only a locally verified preflight failure may assert no dispatch.
        self.sent = not (sent is False and self.stage == 'preflight' and self.code == 'LOCAL_SETUP')
        self.http_status = http_status if type(http_status) is int and 400 <= http_status <= 599 else None
        self.remote_code = remote_code if remote_code in REMOTE_CODES else None
        suffix = ('；可修正設定後明確重試。' if not self.sent else '；未自動重送或改用示範。')
        super().__init__(LABELS[self.code] + suffix)

    def metadata(self):
        return {'code': self.code, 'stage': self.stage, 'sent': self.sent,
                'http_status': self.http_status, 'remote_code': self.remote_code}


def classify(exc, stage):
    from openai import APIStatusError, APITimeoutError, APIConnectionError
    if isinstance(exc, AssistantFailure):
        return exc
    status = getattr(exc, 'status_code', None) if isinstance(exc, APIStatusError) else None
    code = {401: 'AUTHENTICATION', 403: 'FORBIDDEN', 404: 'NOT_FOUND', 429: 'RATE_LIMIT'}.get(status, 'UNKNOWN')
    if isinstance(exc, APITimeoutError):
        code = 'TIMEOUT'
    elif isinstance(exc, APIConnectionError):
        code = 'TRANSPORT'
    elif isinstance(exc, (AttributeError, TypeError, KeyError, ValueError)):
        code = 'FORMAT'
    return AssistantFailure(code, stage, http_status=status)


def decode_failure(value):
    """Old opaque errors remain conservative; only our exact metadata is accepted."""
    import json
    try:
        data = json.loads(value)
        if not isinstance(data, dict) or set(data) != {'code', 'stage', 'sent', 'http_status', 'remote_code'}:
            return None
        return AssistantFailure(data['code'], data['stage'], sent=data['sent'],
                                http_status=data['http_status'], remote_code=data['remote_code'])
    except (ValueError, TypeError, KeyError):
        return None
