"""Deployment defaults and explicit two-turn activation. No metadata prerequisite."""
import json
import os
import ssl
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from .assistant_errors import AssistantFailure
from .dialogue_service import stamp


def deployment(path=None):
    path=Path(path or os.environ.get('UNITHELPER_DEPLOYMENT_FILE') or Path(__file__).resolve().parents[1]/'deployment.json')
    if not path.exists():return None
    try:
        if path.stat().st_size>16384:raise ValueError()
        data=json.loads(path.read_text('utf-8-sig'))
        if set(data)!={'version','protocol','endpoint','ca_bundle'} or data['version']!=1 or data['protocol']!='assistants':raise ValueError()
        u=urlsplit(data['endpoint'])
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment:raise ValueError()
        if data['ca_bundle'] is not None:
            if not isinstance(data['ca_bundle'],str) or not data['ca_bundle']:raise ValueError()
            ca=Path(data['ca_bundle']);ca=ca if ca.is_absolute() else path.parent/ca
            ssl.create_default_context(cafile=str(ca))
            data['ca_bundle']=str(ca.resolve())
        return data
    except Exception:raise ValueError('部署設定或 CA 無效，請聯絡部署者；沒有停用 TLS 或改送其他端點。') from None


class Activation:
    def __init__(self,session,*,load_defaults=True):
        self.s=session;self.error=''
        if load_defaults:
            try:
                d=deployment()
                if d:
                    current=session.profiles.data
                    # Optional deployment defaults seed an empty installation only.
                    # Explicitly saved user destinations survive reopening unchanged.
                    if not current['endpoint']:
                        session.profiles.set_endpoint(d['endpoint'])
                        if current['wire_mode']=='unconfigured':session.profiles.set_wire_mode('assistants')
                    if session.profiles.data['endpoint']==d['endpoint'] and d['ca_bundle']:
                        session.profiles.legacy['ca_bundle']=d['ca_bundle']
            except ValueError as exc:self.error=str(exc)

    def status(self):
        self.s.assert_identity();p=self.s.profiles;d=getattr(p,'data',{})
        available=bool(not self.error and self.s.activation_enabled and not self.s.trial and not self.s.demo_session)
        configured=bool(available and d.get('endpoint') and d.get('wire_mode')=='assistants')
        rows=[]
        for row in p.items(True):
            if row['id']=='demo':continue
            with self.s.dialogue.store.connect() as db:r=db.execute('SELECT * FROM activation_checks WHERE profile_id=?',(row['id'],)).fetchone()
            proof=self.s.skills.proof(row['id'],row['revision'])
            rows.append({'id':row['id'],'name':row['name'],'revision':row['revision'],
                'assistant_id':f"company:{row['id']}:{row['revision']}",
                'chat_status':'passed' if r and r['revision']==row['revision'] and r['passed'] else 'not_tested',
                'skill_roles':proof['roles'] if proof else [],'search_approved':bool(row.get('search_policy',{}).get('tools'))})
        return {'available':available,'configured':configured,'needed':available and not rows,'chat_profiles':rows,
            'endpoint':d.get('endpoint',''),'wire_mode':d.get('wire_mode','unconfigured'),
            'message':self.error or ('填入 endpoint、Assistant ID 與 API key 即可測試；預設使用系統信任憑證。' if available else '此隔離示範／試用入口不設定真實助理；請用一般桌面入口。')}

    def save(self,assistant_id,api_key,endpoint=None,confirm_endpoint_change=False):
        if not isinstance(assistant_id,str) or not 1<=len(assistant_id.strip())<=256 or any(ord(c)<32 for c in assistant_id):raise ValueError('請填有效 Assistant ID。')
        if not isinstance(api_key,str) or not api_key.strip() or len(api_key)>8192:raise ValueError('請填 API key。')
        s=self.s
        with s.engine._lock,s.dialogue.lock,s.company_probe.condition,s.profiles.lock:
            s.engine._ensure_open()
            if not self.status()['available']:raise ValueError(self.status()['message'])
            if s.engine.has_inflight() or s.dialogue.has_inflight() or s.company_probe.has_inflight():raise ValueError('請等待背景請求結束，再保存連線。')
            current=s.profiles.data['endpoint']
            endpoint=current if endpoint is None else endpoint
            if not isinstance(endpoint,str) or not endpoint.strip() or len(endpoint)>4096 or any(ord(c)<32 for c in endpoint):raise ValueError('請填有效 HTTPS endpoint。')
            endpoint=endpoint.strip()
            changed=bool(current and current!=endpoint) or s.profiles.data['wire_mode'] not in ('unconfigured','assistants')
            if changed and confirm_endpoint_change is not True:raise ValueError('變更端點或協定會撤銷舊憑證與能力，舊對話保留唯讀；請明確確認。')
            s.profiles.set_endpoint(endpoint)
            if s.profiles.data['wire_mode']!='assistants':s.profiles.set_wire_mode('assistants')
            existing=next((p for p in s.profiles.items() if p.get('assistant_id')==assistant_id.strip()),None)
            pid=s.profiles.save(existing['name'] if existing else '我的助理',assistant_id,existing.get('notes','') if existing else '',profile_id=existing['id'] if existing else None)
            s.profiles.save_profile_key(pid,api_key);s.profiles.set_default(pid)
            b=s.profiles.snapshot(pid)
            return {'profile_id':pid,'assistant_id':f"company:{pid}:{b['revision']}",'saved':True}

    def test(self,pid,consent):
        if consent is not True:raise ValueError('測試會傳送兩輪合成訊息，請先確認。')
        if not self.status()['configured']:raise ValueError(self.status()['message'])
        if pid=='demo':raise ValueError('示範模式不是真實啟用測試。')
        def perform(binding):
            marker='QA-'+uuid.uuid4().hex[:12];cid='activation:'+uuid.uuid4().hex
            history=[];checks=[];passed=False
            try:
                for n,prompt in enumerate((f'這是合成連線測試。請記住測試代號 {marker}，只回答 OK。不要使用工具。','請只回覆上一輪的測試代號，不要使用工具。')):
                    s=self.s;s.assert_identity();history.append({'role':'user','content':prompt})
                    result=s.profiles.respond(history,'chat',binding,context={'conversation_id':cid,'request_id':cid+':'+str(n),
                        'operation':'activation','search_authorized':False,'cancelled':lambda:s.engine._closed})
                    if not isinstance(result,str) or not result.strip() or (n==1 and result.strip()!=marker):raise ValueError('context_assertion_failed')
                    history.append({'role':'assistant','content':result});checks.append({'round':n+1,'status':'passed'})
                passed=True;message='聊天兩輪及上下文斷言通過；Skill 與搜尋需另外測試。'
            except Exception as exc:
                code=exc.code if isinstance(exc,AssistantFailure) else 'FORMAT_OR_LOCAL_SETUP'
                hints={'AUTHENTICATION':'檢查 API key。','FORBIDDEN':'確認此金鑰有該助理權限。','NOT_FOUND':'核對 Assistant ID 與部署端點。',
                    'TRANSPORT':'請部署者檢查網路及 CA。','TIMEOUT':'服務等待逾時；沒有自動重送。','RATE_LIMIT':'服務限制請求，請稍後明確測試。'}
                message=hints.get(code,'回覆格式、上下文或本機設定未通過；請查看安全錯誤編號。')
                from .support import record
                incident=record(self.s.directory,'activation',exc)
                checks.append({'round':len(checks)+1,'status':'failed','code':code,'incident':incident})
            self.s.assert_identity();self.s.profiles.validate(binding)
            if self.s.engine._closed:raise ValueError('工作區已關閉。')
            with self.s.dialogue.store.connect() as db:db.execute('INSERT OR REPLACE INTO activation_checks VALUES(?,?,?,?)',(pid,binding['revision'],int(passed),stamp()))
            return {'passed':passed,'checks':checks,'message':message,'assistant_id':f"company:{pid}:{binding['revision']}"}
        return self.s.skills._remote(pid,perform)
