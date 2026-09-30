"""Read-only setup inventory. A saved setting is never service acceptance."""
import copy
import os
import threading
import time
import secrets
from urllib.parse import urlsplit

ROLES={'planner':'規劃','analysis':'分析','review':'覆核','compose':'彙整'}


class CompanyProbe:
    """Track a single explicit metadata request without blocking the UI bridge."""
    def __init__(self,profiles):
        self.profiles=profiles;self.condition=threading.Condition();self.pending=False;self.closed=False
        self.approval=None

    def has_inflight(self):
        with self.condition:return self.pending

    def inspect(self,profile_id):
        with self.condition:
            if self.closed:raise ValueError('程式正在關閉。')
            if self.pending:raise ValueError('組織連線檢查仍在處理中，請勿重複點擊。')
            binding=self.profiles.snapshot(profile_id)
            self.pending=True
        try:
            result=self.profiles.inspect_assistant(binding)
            with self.condition:
                if self.closed:raise ValueError('程式已關閉，檢查結果不再顯示。')
                self.profiles.validate(binding)
                token=secrets.token_urlsafe(32)
                self.approval=dict(token=token,binding=binding,expires=time.monotonic()+600,
                    tools=copy.deepcopy(result.get('search_candidates',[])))
                result=dict(result,policy_token=token)
                return result
        finally:
            with self.condition:
                self.pending=False;self.condition.notify_all()

    def close(self,wait=True):
        with self.condition:
            self.closed=True
            while wait and self.pending:self.condition.wait()

    def approve(self,token,names,consent,chat_enabled=False):
        with self.condition:
            if type(chat_enabled) is not bool:raise ValueError('聊天搜尋授權格式無效。')
            saved=self.approval
            if (self.closed or self.pending or not saved or token!=saved['token'] or
                    time.monotonic()>saved['expires'] or consent is not True):
                raise ValueError('搜尋核准預覽失效或尚未同意；請重新檢查助理。')
            if (not isinstance(names,list) or not names or not all(isinstance(n,str) for n in names)
                    or len(names)!=len(set(names))):
                raise ValueError('請選擇已檢查的搜尋工具。')
            tools={t['name']:t for t in saved['tools']}
            if set(names)-set(tools):raise ValueError('包含未檢查的工具；未核准任何工具。')
            result=self.profiles.set_search_policy(saved['binding'],{'tools':[tools[n] for n in names]},chat_enabled=chat_enabled)
            self.approval=None
            return result


def inspect_company(profiles, *, trial=False):
    checks=[]
    def add(id,label,state,detail,action='none'):
        checks.append(dict(id=id,label=label,state=state,detail=detail,action=action))
    if trial:
        add('workspace','工作區','missing','目前是隔離的 Groq 試用；請用 start-app.bat 設定 AI 助理。')
        return dict(scope='local_only',ready_for_company_test=False,checks=checks,
                    next_step='關閉試用工作區後，以 start-app.bat 開啟工作區。',company_services='not_tested')
    with profiles.lock:
        data=copy.deepcopy(profiles.data)
        entries=[p for p in profiles.items(True) if p['id']!='demo']
        ca_configured=bool(profiles.legacy.get('ca_bundle'))
    try:
        url=urlsplit(data.get('endpoint',''))
        endpoint_ok=bool(url.scheme=='https' and url.hostname and not url.username and not url.password
            and not url.query and not url.fragment and url.hostname.lower().rstrip('.') not in {'openai.com','api.openai.com'})
    except (ValueError,TypeError):endpoint_ok=False
    add('endpoint','組織 Endpoint','ready' if endpoint_ok else 'missing',
        'HTTPS 網址格式已設定；尚未測試連線。' if endpoint_ok else '請保存組織核准的 HTTPS Assistants base URL。','settings')
    wire_ok=data.get('wire_mode')=='assistants'
    add('protocol','Threads／Runs 協定','ready' if wire_ok else 'missing',
        '已選 Assistants；Assistant ID 會放在 run 的 assistant_id。' if wire_ok else '組織提供的範例使用 assistants，請在連線協定中選取。','settings')
    source=data.get('credential_source')
    shared_reference=(source=='keyring' and bool(data.get('credential_id'))) or (source=='environment' and data.get('api_key_env') in os.environ)
    reference_ok=any(bool(p.get('credential_id')) if p.get('credential_mode','shared')=='individual' else shared_reference for p in entries)
    add('credential','API key 來源','not_tested' if reference_ok else 'missing',
        '至少一位助理已指定共用或個別金鑰來源；本檢查沒有讀取金鑰，是否存在及可讀仍需試跑。' if reference_ok else '尚無助理的金鑰來源設定；請保存共用或個別 API key。','settings')
    add('assistants','可選AI 助理','ready' if entries else 'missing',
        f'已設定 {len(entries)} 位啟用中的AI 助理；不代表已接通。' if entries else '請在助理團隊新增名稱及 Assistant ID。','team')
    for role,label in ROLES.items():
        candidates=[p for p in entries if role in p.get('workflow',{}).get('roles',[])]
        verified=[p for p in candidates if p['workflow'].get('verified') is True and p['workflow'].get('read_only') is True]
        add('role_'+role,label+'角色','ready' if verified else 'not_tested' if candidates else 'missing',
            '本機已有能力驗收紀錄；本次檢查未重新呼叫助理。' if verified else
            '已分配角色，但尚未完成組織能力試跑；不能只修改 verified 旗標。' if candidates else
            '尚未分配此角色；先在助理團隊設定用途，再完成角色試跑。','team')
    add('tls','TLS 與組織 CA','not_tested',
        '已指定組織 CA 檔案；本次未讀取或驗證。' if ca_configured else '使用系統信任庫；若組織憑證不受信任，需設定核准 CA，不能關閉 TLS。','settings')
    approved=sum(len(p.get('search_policy',{}).get('tools',[])) for p in entries)
    chats=sum(p.get('chat_search_enabled') is True and bool(p.get('search_policy',{}).get('tools')) for p in entries)
    add('tools','組織查資料／插件','not_tested',f'已核准 {approved} 項搜尋工具，其中 {chats} 位助理另獲一般聊天搜尋授權；已確認日報／搜尋步驟維持原授權。核准不代表搜尋已實測。','settings')
    add('drafts','建立任務與排程','ready','建立任務只存未啟用草稿；規劃工作試跑成功後才能另行授權排程。','plan')
    missing=next((c for c in checks[:4] if c['state']=='missing'),None)
    next_step=(missing['detail'] if missing else
        '先用合成文字確認單助理連線，再從「財經日報」預覽並試跑；多助理分工另需四個角色驗收。')
    return dict(scope='local_only',ready_for_company_test=bool(endpoint_ok and wire_ok and reference_ok and entries),
                checks=checks,next_step=next_step,company_services='not_tested')
