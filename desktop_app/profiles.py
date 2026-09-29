"""User-managed assistant metadata; credentials stay in Windows credential storage."""
import copy
import json
import os
from pathlib import Path
import threading
import uuid
from urllib.parse import urlsplit
from .gateways import CompanyAssistant, DemoAssistant, GatewayError

DEMO = {'profile_id':'demo','revision':1}
class CredentialVault:
    SERVICE='QAagent.Desktop.API'
    def __init__(self, backend=None):
        if backend is None:
            from keyring.backends.Windows import WinVaultKeyring
            backend=WinVaultKeyring()
        self.backend=backend
    def get(self, account):
        try: return self.backend.get_password(self.SERVICE,account)
        except Exception: raise GatewayError('無法讀取 Windows 認證管理員。') from None
    def set(self, account, key):
        if not isinstance(key,str) or not key.strip(): raise GatewayError('請填 API key。')
        try: self.backend.set_password(self.SERVICE,account,key)
        except Exception: raise GatewayError('無法保存 API key；沒有改存明文。') from None
    def remove(self, account):
        try:
            if self.get(account) is not None: self.backend.delete_password(self.SERVICE,account)
        except Exception: raise GatewayError('無法移除 Windows 認證。') from None

class Profiles:
    def __init__(self,path,legacy=None,vault=None):
        self.path=Path(path); self.vault=vault or CredentialVault(); self.lock=threading.RLock()
        self.legacy=copy.deepcopy(legacy or {})
        if self.path.exists():
            try:
                self.data=json.loads(self.path.read_text('utf-8-sig'))
                if self.data['version']!=1 or not isinstance(self.data['profiles'],list): raise ValueError()
                for p in self.data['profiles']:
                    if not all(k in p for k in ('id','revision','name','assistant_id','notes','enabled')): raise ValueError()
            except (ValueError,KeyError,TypeError): raise GatewayError('助理清單格式錯誤；保留原檔，請回報維護者。') from None
        else:
            a=self.legacy
            self.data={'version':1,'endpoint':a.get('base_url',''),'credential_id':uuid.uuid4().hex,
                'credential_source':'environment','api_key_env':a.get('api_key_env','UNITHELPER_API_KEY'),
                'wire_mode':'unconfigured','model':'','assistant_field':'','default':'demo','profiles':[]}
            if a.get('mode')=='company':
                self.data['profiles']=[{'id':uuid.uuid4().hex,'revision':1,'name':'既有公司助理','assistant_id':a.get('assistant_ref') or a.get('model',''),'notes':'沿用舊版已設定的請求格式','enabled':True,'legacy':True}]
                self.data['default']=self.data['profiles'][0]['id']
        self._validate_data()
        if not self.path.exists() and self.legacy.get('mode')=='company':
            self._write(self.data)
    def _validate_data(self):
        d=self.data
        if d.get('credential_source') not in ('environment','keyring'): raise GatewayError('金鑰來源設定不正確。')
        if d.get('wire_mode') not in ('unconfigured','model','body_field','assistants'): raise GatewayError('公司 API 映射設定不正確。')
        ids=[p['id'] for p in d['profiles']]
        if len(ids)!=len(set(ids)) or 'demo' in ids: raise GatewayError('助理識別重複。')
        for p in d['profiles']:
            if not isinstance(p['revision'],int) or p['revision']<1 or type(p['enabled']) is not bool: raise GatewayError('助理版本或狀態不正確。')
            for key in ('id','name','assistant_id','notes'):
                if not isinstance(p[key],str): raise GatewayError('助理欄位格式不正確。')
            if 'workflow' in p:
                cap=p['workflow']
                if (not isinstance(cap,dict) or type(cap.get('revision')) is not int or cap['revision']<1
                        or not isinstance(cap.get('roles'),list) or not cap['roles']
                        or any(not isinstance(r,str) or r not in {'planner','analysis','review','compose','rag'} for r in cap['roles'])
                        or type(cap.get('verified')) is not bool or type(cap.get('read_only')) is not bool
                        or not isinstance(cap.get('evidence'),str) or (cap['verified'] and not cap['evidence'].strip())):
                    raise GatewayError('助理協作能力設定格式不正確；保留原檔，請由公司維護者核對。')
    def _write(self,data):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.tmp')
        try:
            temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            os.replace(temp,self.path)
        finally:
            if temp.exists(): temp.unlink()
        self.data=data
    def items(self,enabled=False):
        with self.lock:
            rows=[{'id':'demo','revision':1,'name':'示範助理','assistant_id':'demo-local','notes':'本機流程示範，未呼叫 AI','enabled':True}]+copy.deepcopy(self.data['profiles'])
            return [p for p in rows if p['enabled']] if enabled else rows
    def default_binding(self):
        with self.lock:
            p=next((p for p in self.items(True) if p['id']==self.data['default']),self.items(True)[0])
            return {'profile_id':p['id'],'revision':p['revision']}
    def snapshot(self,profile_id):
        p=next((p for p in self.items() if p['id']==profile_id),None)
        if p is None: raise GatewayError('找不到助理。')
        return {'profile_id':p['id'],'revision':p['revision']}
    def validate(self,binding):
        with self.lock:
            if not isinstance(binding,dict): raise GatewayError('舊版對話沒有助理歸屬；請選擇內容轉交至新對話。')
            p=next((p for p in self.items() if p['id']==binding.get('profile_id')),None)
            if not p or not p['enabled']: raise GatewayError('助理已停用；請使用其他助理的新對話。')
            if p['revision']!=binding.get('revision'): raise GatewayError('助理連線版本已改變；請建立新對話，舊資料仍可閱讀。')
            return p
    def information(self,binding):
        if not isinstance(binding,dict): return None
        p=next((p for p in self.items() if p['id']==binding.get('profile_id')),None)
        if p and p['revision']==binding.get('revision'): return p
        return next((copy.deepcopy(p) for p in self.data.get('history',[]) if p['id']==binding.get('profile_id') and p['revision']==binding.get('revision')),None)

    def save(self,name,assistant_id,notes='',profile_id=None,enabled=True):
        if not name.strip() or not assistant_id.strip(): raise GatewayError('助理名稱與 assistant ID 必填。')
        if len(name)>80 or len(assistant_id)>256 or len(notes)>2000: raise GatewayError('助理欄位超過長度限制。')
        with self.lock:
            d=copy.deepcopy(self.data); p=next((p for p in d['profiles'] if p['id']==profile_id),None)
            if profile_id and p is None: raise GatewayError('找不到可編輯助理。')
            if p is None:
                p={'id':uuid.uuid4().hex,'revision':1,'enabled':bool(enabled)}; d['profiles'].append(p)
            elif p['assistant_id']!=assistant_id.strip():
                d.setdefault('history',[]).append(dict(p,endpoint=d['endpoint']))
                p['revision']+=1; p.pop('legacy',None)
                if 'workflow' in p:p['workflow']['verified']=False
            p.update(name=name.strip(),assistant_id=assistant_id.strip(),notes=notes.strip(),enabled=bool(enabled))
            self._write(d); return p['id']
    def set_default(self,profile_id):
        self.validate(self.snapshot(profile_id))
        with self.lock:
            d=copy.deepcopy(self.data); d['default']=profile_id; self._write(d)
    def set_endpoint(self,endpoint):
        endpoint=endpoint.strip()
        if endpoint:
            try:
                p=urlsplit(endpoint)
                if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment or p.hostname.lower().rstrip('.') in ('openai.com','api.openai.com'): raise ValueError()
            except ValueError: raise GatewayError('請填公司 HTTPS endpoint；網址不可含帳密。') from None
        with self.lock:
            d=copy.deepcopy(self.data)
            if endpoint!=d['endpoint']:
                d['endpoint']=endpoint
                # Credentials are destination-specific. Do not forward an old key to a new endpoint.
                d['credential_id']=uuid.uuid4().hex; d['credential_source']='keyring'
                for p in d['profiles']:
                    d.setdefault('history',[]).append(dict(p,endpoint=self.data['endpoint']))
                    p['revision']+=1; p.pop('legacy',None)
                    if 'workflow' in p:p['workflow']['verified']=False
            self._write(d)
    def save_key(self,key):
        with self.lock:
            d=copy.deepcopy(self.data); d['credential_source']='keyring'
            account=uuid.uuid4().hex
            self.vault.set(account,key); d['credential_id']=account
            old_account=self.data['credential_id'] if self.data['credential_source']=='keyring' else None
            try: self._write(d)
            except Exception:
                self.vault.remove(account); raise
            if old_account and old_account!=account:
                try: self.vault.remove(old_account)
                except GatewayError: pass  # New key is usable; never expose native error text.
    def remove_key(self):
        with self.lock:
            d=copy.deepcopy(self.data)
            if d['credential_source']=='keyring': self.vault.remove(d['credential_id'])
            d['credential_source']='keyring'; self._write(d)
    def key(self):
        with self.lock:
            if self.data['credential_source']=='keyring': value=self.vault.get(self.data['credential_id'])
            else: value=os.environ.get(self.data['api_key_env'],'')
        if not value: raise GatewayError('尚未設定共用 API key。')
        return value
    def key_status(self):
        try: self.key(); return '已設定（'+('Windows 認證管理員' if self.data['credential_source']=='keyring' else '舊環境變數')+'）'
        except GatewayError: return '尚未設定或無法讀取'
    def set_wire_mode(self, mode, model='', assistant_field=''):
        """Explicit transport selection; changes revoke old bindings/capabilities."""
        if mode not in ('unconfigured','model','body_field','assistants'):
            raise GatewayError('公司 API 映射設定不正確。')
        if not isinstance(model,str) or not isinstance(assistant_field,str):
            raise GatewayError('公司 API 映射欄位不正確。')
        if mode=='body_field' and (not model.strip() or not assistant_field.strip()):
            raise GatewayError('請提供公司核准的 model 與助理欄位名稱。')
        with self.lock:
            d=copy.deepcopy(self.data)
            values=(mode,model.strip() if mode=='body_field' else '',assistant_field.strip() if mode=='body_field' else '')
            old=(d['wire_mode'],d.get('model',''),d.get('assistant_field',''))
            if values!=old:
                for p in d['profiles']:
                    d.setdefault('history',[]).append(dict(p,endpoint=d['endpoint']))
                    p['revision']+=1;p.pop('legacy',None)
                    if 'workflow' in p:p['workflow']['verified']=False
                d['wire_mode'],d['model'],d['assistant_field']=values
            self._write(d)

    def _assistants_client(self, d, p, key, binding):
        from .assistants_gateway import AssistantsGateway
        config={'base_url':d['endpoint'],'assistant_id':p['assistant_id']}
        for field in ('ca_bundle','timeout_seconds','run_timeout_seconds'):
            if field in self.legacy:config[field]=self.legacy[field]
        return AssistantsGateway(config,key,self.path.parent/'assistant-sessions.sqlite3',binding)

    def respond(self,messages,purpose,binding,context=None):
        with self.lock:
            p=self.validate(binding)
            if p['id']=='demo': return DemoAssistant().respond(messages,purpose)
            d=copy.deepcopy(self.data); legacy=copy.deepcopy(self.legacy)
            if d['wire_mode']=='assistants':
                config=None
            elif p.get('legacy'):
                config=legacy
                config['base_url']=d['endpoint']
            else:
                if d['wire_mode']=='unconfigured': raise GatewayError('待確認公司 API 格式；請由公司提供遮蔽值的成功呼叫範例。')
                config={'base_url':d['endpoint'],'timeout_seconds':30,'max_context_chars':50000}
                if d['wire_mode']=='model': config['model']=p['assistant_id']
                else: config.update(model=d['model'],assistant_ref=p['assistant_id'],assistant_ref_field=d['assistant_field'])
                for field in ('ca_bundle','header_env','verified_side_effect_free'):
                    if field in legacy: config[field]=legacy[field]
            key=self.key()
        client=self._assistants_client(d,p,key,binding) if config is None else CompanyAssistant(config,api_key=key)
        try:
            if config is None:return client.respond(messages,purpose,context=context)
            return client.respond(messages,purpose)
        finally: client.close()

    def inspect_request(self,binding,context,remote=False):
        """Explicit status check, never sends a new message or creates a run."""
        with self.lock:
            p=self.validate(binding);d=copy.deepcopy(self.data)
            if p['id']=='demo' or d['wire_mode']!='assistants':
                return {'state':'unsupported','recoverable':False,'remote_checked':False}
            from .assistant_sessions import AssistantSessions
            from .assistants_gateway import session_context
            key,rid,_,_=session_context(binding,'chat',context)
            request=AssistantSessions(self.path.parent/'assistant-sessions.sqlite3').get_request(key,rid)
            if not request:return {'state':'not_found','recoverable':False,'remote_checked':False}
            if not remote or request['state']=='completed':
                return {'state':request['state'],'recoverable':bool(request.get('run_id')) and request['state'] not in
                        ('failed','cancelled','cancel_requested','tools_blocked'),
                        'remote_checked':False,'remote_terminal':request.get('remote_terminal',False)}
            api_key=self.key()
        client=self._assistants_client(d,p,api_key,binding)
        try:return client.inspect_request(context=context,remote=True)
        finally:client.close()

    def inspect_assistant(self,binding):
        with self.lock:
            p=self.validate(binding);d=copy.deepcopy(self.data)
            if p['id']=='demo' or d['wire_mode']!='assistants':
                raise GatewayError('請先設定公司 Assistants 協定及公司助理 ID。')
            key=self.key()
        client=self._assistants_client(d,p,key,binding)
        try:return client.inspect_assistant()
        finally:client.close()

    def workflow_catalog(self):
        """Only explicitly verified read-only capabilities may be orchestrated."""
        return [p for p in self.items(True) if p.get('workflow',{}).get('verified') is True
                and p['workflow'].get('roles') and p['workflow'].get('read_only') is True]

    def forget_conversations_tx(self,db,ids):
        """Remove additional local response copies with the existing deletion transaction.

        Remote threads and independent workflow receipts are intentionally retained.
        """
        path=self.path.parent/'assistant-sessions.sqlite3'
        if not path.exists():return
        from .assistants_gateway import session_context
        keys=set()
        for cid in ids:
            row=db.execute('SELECT binding FROM conversations WHERE id=?',(cid,)).fetchone()
            if row and row['binding']:
                binding=json.loads(row['binding'])
                keys.add(session_context(binding,'chat',{'conversation_id':'engine:'+cid})[0])
            for task in db.execute('SELECT id,payload FROM tasks WHERE conversation_id=?',(cid,)):
                binding=json.loads(task['payload']).get('_binding')
                if binding:
                    keys.add(session_context(binding,'chat',{'conversation_id':'engine:'+cid})[0])
                    keys.add(session_context(binding,'chat',{'conversation_id':'task:'+task['id']})[0])
        db.execute('ATTACH DATABASE ? AS assistant_cache',(str(path),))
        for key in keys:
            db.execute('DELETE FROM assistant_cache.requests WHERE session_id=?',(key,))
            db.execute('DELETE FROM assistant_cache.sessions WHERE id=?',(key,))

    def workflow_binding(self,profile_id):
        p=next((p for p in self.workflow_catalog() if p['id']==profile_id),None)
        if p is None: raise GatewayError('此助理尚未完成自動協作能力驗證。')
        return dict(self.snapshot(profile_id),capability_revision=p['workflow']['revision'])

    def validate_workflow(self,binding,role):
        p=self.validate(binding)
        capability=p.get('workflow',{})
        if (capability.get('verified') is not True or capability.get('read_only') is not True
                or capability.get('revision')!=binding.get('capability_revision')
                or role not in capability.get('roles',[])):
            raise GatewayError('助理的協作能力未驗證、已改變或不支援此角色。請重新確認計畫。')
        return p

    def set_workflow_capability(self,profile_id,roles,verified=False,evidence=''):
        """Company setup hook, not proof of verification: evidence must reference actual local tests."""
        if not isinstance(roles,list) or not roles or any(r not in {'planner','analysis','review','compose','rag'} for r in roles):
            raise GatewayError('請設定支援的協作角色。')
        if type(verified) is not bool or not isinstance(evidence,str) or len(evidence)>300:
            raise GatewayError('能力驗證紀錄格式無效。')
        if verified and not evidence.strip(): raise GatewayError('啟用協作前需先完成公司能力與隔離測試，並提供本機證據識別。')
        with self.lock:
            d=copy.deepcopy(self.data);p=next((p for p in d['profiles'] if p['id']==profile_id),None)
            if p is None: raise GatewayError('找不到助理。')
            p['workflow']={'revision':p.get('workflow',{}).get('revision',0)+1,'roles':sorted(set(roles)),
                           'verified':verified,'read_only':True,'evidence':evidence.strip()}
            self._write(d)

    def workflow_call(self,messages,role,binding,context):
        """Company Assistants sessions are isolated by run, step and binding version."""
        self.validate_workflow(binding,role)
        if not isinstance(context,dict) or not all(context.get(k) for k in ('run_id','step_id')):
            raise GatewayError('協作呼叫缺少隔離識別。')
        return self.respond(messages,'workflow_plan' if role=='planner' else 'workflow_step',binding,context=context)
