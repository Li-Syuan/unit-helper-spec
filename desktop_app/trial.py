"""Explicit external AI trial. Never loads company configuration or credentials."""
from pathlib import Path
import ssl
import threading

from .gateways import DemoAssistant, GatewayError, PURPOSES, validated_messages
from .profiles import Profiles

ENDPOINT = 'https://api.groq.com/openai/v1'
MODEL = 'openai/gpt-oss-20b'
ENV_PATH = Path(__file__).resolve().parent.parent / '.env'
PROFILE_ID = 'groq-trial'


def read_key(path=None):
    """Read one literal value, without shell expansion or changing os.environ."""
    try:
        with Path(path or ENV_PATH).open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError()
        text = raw.decode('utf-8-sig')
    except (OSError, UnicodeError, ValueError):
        raise GatewayError('無法讀取專案 .env；請確認為 UTF-8 文字且小於 64 KB。') from None
    values = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, separator, value = line.partition('=')
        if name.strip() != 'GROQ_API_KEY':
            continue
        if not separator:
            raise GatewayError('.env 的 GROQ_API_KEY 格式不正確。')
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values.append(value)
    if len(values) != 1 or not values[0] or len(values[0]) > 4096 or any(
            not (33 <= ord(c) <= 126) or c in "\"'`$" for c in values[0]):
        raise GatewayError('請在專案 .env 填一筆 GROQ_API_KEY；不能空白、重複或使用變數展開。')
    # Use the approved parser without interpolation or os.environ mutation.
    from dotenv import dotenv_values
    from io import StringIO
    parsed=dotenv_values(stream=StringIO(text),interpolate=False).get('GROQ_API_KEY')
    if parsed != values[0]:
        raise GatewayError('.env 的 GROQ_API_KEY 需為單一明確字面值。')
    return parsed


class GroqAssistant:
    def __init__(self, client=None, env_path=None):
        if client is None:
            import httpx
            from openai import OpenAI
            client = OpenAI(api_key=read_key(env_path), base_url=ENDPOINT,
                            max_retries=0, timeout=30,
                            http_client=httpx.Client(follow_redirects=False, timeout=30,
                                                     verify=ssl.create_default_context()))
        self.client = client

    def respond(self, messages, purpose='chat'):
        return self._complete(messages,purpose)

    def _complete(self, messages, purpose='chat', response_format=None):
        import openai
        if purpose not in PURPOSES:
            raise GatewayError('不支援的助理操作。')
        workflow=purpose in {'workflow_plan','workflow_step'}
        clean = validated_messages(messages, 24000 if workflow else 6000)
        try:
            options={} if response_format is None else {'response_format':response_format}
            response = self.client.chat.completions.create(
                model=MODEL, messages=[{'role':'system', 'content':PURPOSES[purpose]}, *clean],
                stream=False, max_completion_tokens=4096 if workflow else 2048, reasoning_effort='low',
                extra_body={'include_reasoning':False}, **options)
            choice = response.choices[0]
            message = choice.message
            if getattr(message, 'tool_calls', None) or getattr(message, 'function_call', None):
                raise GatewayError('試用助理回傳工具要求；本程式不會執行。')
            if choice.finish_reason != 'stop':
                raise GatewayError('試用回覆未完整完成；請縮短需求後再試，沒有當作成功。')
            if not isinstance(message.content, str) or not message.content.strip():
                raise GatewayError('Groq 回覆為空白或格式錯誤。')
            return message.content
        except openai.APITimeoutError:
            raise GatewayError('Groq 回應逾時；請稍後再試。') from None
        except openai.APIStatusError as exc:
            if exc.status_code in (401, 403):
                reason = 'Groq 認證失敗；請確認 .env 的 API key 與帳戶權限。'
            elif exc.status_code == 429:
                reason = 'Groq 流量或額度限制；請稍後再試。本程式不會自動重試或切換付費方案。'
            else:
                reason = 'Groq 服務拒絕請求；請查看帳戶或模型可用狀態。'
            raise GatewayError(reason) from None
        except openai.APIConnectionError:
            raise GatewayError('無法連線 Groq；請檢查網路、代理與可信憑證。') from None
        except (openai.APIError, AttributeError, IndexError, TypeError, ValueError) as exc:
            if isinstance(exc, GatewayError):
                raise
            raise GatewayError('Groq 回覆格式不正確；未使用示範答案替代。') from None

    def close(self):
        self.client.close()


class TrialProfiles(Profiles):
    """Reuse binding validation, with an immutable trial-only catalog."""
    def __init__(self, env_path=None):
        self.lock = threading.RLock()
        self.env_path = env_path
        self.data = {'default':PROFILE_ID, 'wire_mode':'model', 'endpoint':ENDPOINT,
                     'profiles':[{'id':PROFILE_ID, 'revision':1, 'name':'Groq 試用助理',
                     'assistant_id':MODEL, 'enabled':True,
                     'notes':'外部 AI：可整理與改寫測試文字。請勿傳送公司機密或個資。'}]}
        for role,label in [('planner','主代理／規劃'),('analysis','分析子代理'),('review','覆核子代理'),('compose','日報子代理')]:
            self.data['profiles'].append({'id':'groq-'+role,'revision':1,'name':label+'（Groq）','assistant_id':MODEL,
                'enabled':True,'notes':'同一 Groq 模型的隔離角色，非公司 assistant ID；僅供合成資料測試。',
                'workflow':{'revision':1,'roles':[role],'verified':True,'read_only':True,'evidence':'trial-stateless-no-tools'}})

    def key(self):
        return read_key(self.env_path)

    def key_status(self):
        try:
            self.key()
            return '已填寫 .env（尚不代表連線成功）'
        except GatewayError:
            return '未填寫或 .env 格式不正確'

    def _readonly(self, *args, **kwargs):
        raise GatewayError('此入口固定使用 Groq 試用連線；公司設定請使用 start-app.bat。')

    _write = save = set_default = set_endpoint = save_key = remove_key = _readonly

    def respond(self, messages, purpose, binding):
        profile = self.validate(binding)
        if profile['id'] == 'demo':
            return DemoAssistant().respond(messages, purpose)
        client = GroqAssistant(env_path=self.env_path)
        try:
            return client.respond(messages, purpose)
        finally:
            client.close()
