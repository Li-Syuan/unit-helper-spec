"""Offline two-mode dialogue, validated suggestions and explicit inert-draft saves."""
import json
import threading
import time
import uuid
import hashlib
import re
from datetime import datetime,timezone
from .dialogue_contracts import ASSISTANTS,TASK_TYPES,assistant,answers,draft
from .dialogue_provider import DemoDialogueProvider
from .assistant_errors import AssistantFailure, decode_failure


def stamp():return datetime.now(timezone.utc).isoformat()
def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True)


def automatic_title(value):
    """Local first-topic label only; no model, summarization or hidden dispatch."""
    lines=[line.strip() for line in (value or '').splitlines() if line.strip()]
    if not lines:return '新對話'
    line=re.sub(r'^\s*(?:#{1,6}\s+|[-*]\s+|\d+[.)、]\s+)', '', lines[0])
    line=' '.join(line.split())
    topic=re.split(r'[。！？!?]',line,maxsplit=1)[0].strip()
    topic=re.sub(r'^(?:請幫我|麻煩幫我|幫我|請問)\s*','',topic).strip() or line
    return topic if len(topic)<=32 else topic[:31]+'…'


class DialogueService:
    def __init__(self,store,provider=None):
        self.store=store;self.provider=provider or DemoDialogueProvider();self.lock=threading.RLock();self.previews={}
        self._condition=threading.Condition(self.lock);self._pending={};self._closed=False;self.delete_previews={}

    def _ensure_open(self):
        if self._closed:raise ValueError('程式正在關閉，未送出對話。')
        if getattr(self,'authorization',None):self.authorization()

    def has_inflight(self):
        with self.lock:return bool(self._pending)

    def stop(self,tid):
        """Fence the local result immediately; remote cancellation is best effort."""
        with self.lock:
            self.state(tid)
            entry=self._pending.get(tid)
            if entry:
                entry['cancelled'].set()
                with self.store.connect() as db:
                    db.execute("UPDATE requests SET status='cancelled',recoverable=0,error_code='cancelled',updated_at=? WHERE request_id=? AND status!='completed'",(stamp(),entry['request_id']))
            return {'cancel_requested':bool(entry),'remote_stopped':False}

    def close(self,wait=True):
        with self._condition:
            self._closed=True
            for entry in self._pending.values():entry['cancelled'].set()
            if wait:
                while self._pending:self._condition.wait()

    def validate_assistant(self,value):
        validator=getattr(self.provider,'validate_assistant',assistant)
        return validator(value)

    def validate_draft(self,value,assistant_id):
        self.validate_assistant(assistant_id)
        result=answers(value)
        if set(result)!={'target','source','task_type','schedule'}:raise ValueError('請補齊追蹤對象、資訊來源、任務類型與執行時間。')
        return result

    def start(self,mode='chat',assistant_id='demo-general',*,memory_snapshot=None,source_thread_id=None,draft_text=''):
        if mode not in {'chat','task','auto'}:raise ValueError('對話模式不支援。')
        if mode=='auto' and not getattr(self,'routing_allowed',lambda aid:not aid.startswith('company:'))(assistant_id):
            raise ValueError('此助理尚未通過自動辨識契約；仍可使用一般聊天或手動交辦。')
        self.validate_assistant(assistant_id);tid=uuid.uuid4().hex
        with self.lock,self.store.connect() as db:
            self._ensure_open()
            db.execute('INSERT INTO threads VALUES(?,?,?,\'{}\',1,?)',(tid,mode,assistant_id,stamp()))
            db.execute('INSERT INTO thread_views(thread_id,draft,memories,source_thread_id,updated_at) VALUES(?,?,?,?,?)',
                (tid,draft_text,encode(memory_snapshot or []),source_thread_id,stamp()))
            db.execute('INSERT INTO workspace_views(thread_id) VALUES(?)',(tid,))
        return self.state(tid)

    def state(self,tid):
        with self.lock,self.store.connect() as db:
            row=db.execute('SELECT * FROM threads WHERE id=?',(tid,)).fetchone()
            if row is None:raise ValueError('對話不存在，請開始新對話。')
            thread=dict(row);thread['answers']=json.loads(thread['answers'])
            view=db.execute('SELECT * FROM thread_views WHERE thread_id=?',(tid,)).fetchone()
            thread.update(title=view['title'] if view else '',pinned=bool(view['pinned']) if view else False,
                draft_text=view['draft'] if view else '',scroll=view['scroll'] if view else 0,
                view_revision=view['revision'] if view else 0,memory_snapshot=json.loads(view['memories']) if view else [],
                source_thread_id=view['source_thread_id'] if view else None)
            thread['folder_id']=view['folder_id'] if view else None
            workspace=db.execute('SELECT * FROM workspace_views WHERE thread_id=?',(tid,)).fetchone()
            thread['active_job']=workspace['active_job'] if workspace else None
            thread['skill_id']=workspace['skill_id'] if workspace else None
            thread['routes']=[dict(r,proposal=json.loads(r['proposal']) if r['proposal'] else None) for r in db.execute(
                'SELECT request_id,proposal,job_id,decision FROM dialogue_routes WHERE thread_id=? ORDER BY rowid',(tid,))]
            thread['source_deleted']=bool(thread['source_thread_id'] and not db.execute('SELECT 1 FROM threads WHERE id=?',(thread['source_thread_id'],)).fetchone())
            try:getattr(self.provider,'validate_assistant',assistant)(thread['assistant_id']);thread['read_only']=False
            except ValueError:thread['read_only']=True
            thread['messages']=[dict(r) for r in db.execute('SELECT role,text FROM messages WHERE thread_id=? ORDER BY id',(tid,))]
            thread['complete']=set(thread['answers'])=={'target','source','task_type','schedule'}
            thread['saved']=[dict(r) for r in db.execute('SELECT id,revision,enabled FROM task_drafts WHERE thread_id=?',(tid,))]
            thread['company']=thread['assistant_id'].startswith('company:')
            request=db.execute('SELECT * FROM requests WHERE thread_id=? ORDER BY rowid DESC LIMIT 1',(tid,)).fetchone()
            thread['request']=None if request is None else {'id':request['request_id'],'state':request['status'],
                'pending_text':request['text'] if request['status']!='completed' else '',
                'recoverable':bool(request['recoverable']) and request['status'] not in ('cancelled','completed'),
                'remote_state':request['remote_state'],'error_code':request['error_code']}
            thread['busy']=tid in self._pending
            thread['tools_allowed']=bool(getattr(self.provider,'tools_allowed',lambda *a:False)(thread['mode'],thread['assistant_id']))
            if request is not None:
                failure=decode_failure(request['error_code'])
                unsent=(request['status']=='failed' and failure is not None and not failure.sent
                        and thread['revision']==request['revision'] and not thread['busy'])
                check=getattr(self.provider,'can_retry_unsent',None)
                retry=bool(unsent and check and check(thread['mode'],thread['assistant_id'],
                    {'conversation_id':'dialogue:'+tid,'request_id':request['request_id']}))
                thread['request'].update(retry_unsent=retry,error_stage=failure.stage if failure else None,
                    error_http_status=failure.http_status if failure else None,
                    error_provider_code=failure.remote_code if failure else None,
                    error_code=failure.code if failure else request['error_code'],
                    recovery_action='retry_unsent' if retry else ('recover' if thread['request']['recoverable'] else
                        ('inspect_or_fork' if request['status']!='completed' else 'none')))
            return thread

    def list_saved(self):
        with self.lock,self.store.connect() as db:
            return [dict(r,body=json.loads(r['body'])) for r in db.execute('SELECT * FROM task_drafts ORDER BY created_at DESC')]

    def history(self):
        with self.lock,self.store.connect() as db:
            self._ensure_open()
            rows=[dict(r) for r in db.execute("SELECT t.id,t.mode,t.assistant_id,t.created_at,COALESCE(v.pinned,0) AS pinned,v.folder_id,COALESCE(v.title,'') AS manual_title,"
                "COALESCE((SELECT text FROM requests WHERE thread_id=t.id ORDER BY rowid LIMIT 1),"
                "(SELECT text FROM messages WHERE thread_id=t.id AND role='user' ORDER BY id LIMIT 1),v.draft,'') AS topic "
                "FROM threads t LEFT JOIN thread_views v ON v.thread_id=t.id WHERE EXISTS(SELECT 1 FROM messages WHERE thread_id=t.id) OR EXISTS(SELECT 1 FROM requests WHERE thread_id=t.id) OR v.draft!='' OR v.title!='' OR v.pinned=1 OR v.folder_id IS NOT NULL ORDER BY pinned DESC,COALESCE(v.updated_at,t.created_at) DESC")]
            for r in rows:
                manual=r.pop('manual_title');topic=r.pop('topic')
                r.update(title=manual or automatic_title(topic),title_source='manual' if manual else 'auto')
            return rows

    def _history(self,state,text):
        if state['mode']=='auto':
            from .dialogue_routing import PROMPT
            history=[{'role':'user','content':PROMPT}]
            with self.store.connect() as db:
                rows=db.execute('SELECT q.text,r.wire FROM dialogue_routes r JOIN requests q USING(request_id) WHERE r.thread_id=? AND q.status=\'completed\' ORDER BY q.rowid',(state['id'],)).fetchall()
            for row in rows:
                history.extend([{'role':'user','content':row['text']},{'role':'assistant','content':row['wire']}])
        else:history=[{'role':m['role'],'content':m['text']} for m in state['messages']]
        if state.get('memory_snapshot'):
            history.insert(0,{'role':'user','content':'以下是使用者確認的背景筆記，可能過時，不構成工具或執行授權。\n'+encode(state['memory_snapshot'])})
        return history+[{'role':'user','content':text}]

    def send(self,tid,text,request_id,*,routing_input=None):
        if not isinstance(text,str) or not 1<=len(text.strip())<=4000:raise ValueError('請輸入1～4,000字。')
        if not isinstance(request_id,str) or not 1<=len(request_id)<=150:raise ValueError('送出識別無效。')
        with self.lock:
            self._ensure_open()
            state=self.state(tid)
            if state['mode']=='auto' and not getattr(self,'routing_allowed',lambda aid:True)(state['assistant_id']):raise ValueError('自動辨識能力已失效；請重新檢查助理，或建立一般聊天。')
            if tid in self._pending:raise ValueError('此對話仍有請求處理中；取消後也請等遠端請求結束。')
            with self.store.connect() as db:
                previous=db.execute('SELECT * FROM turns WHERE request_id=?',(request_id,)).fetchone()
                if previous:
                    if previous['thread_id']!=tid or previous['text']!=text:raise ValueError('重複送出內容不一致。')
                    return self.state(tid)
                if db.execute('SELECT 1 FROM requests WHERE request_id=?',(request_id,)).fetchone():
                    raise ValueError('此請求已有紀錄，請檢查或恢復原請求，不要再次送出。')
                if db.execute("SELECT 1 FROM requests WHERE thread_id=? AND status!='completed'",(tid,)).fetchone():
                    raise ValueError('上一筆請求尚未完成；請檢查原請求，或另開對話保留草稿。')
            if any(item['request_id']==request_id for item in self._pending.values()):
                raise ValueError('送出識別已用於另一筆處理中的對話。')
            history=self._history(state,text)
            if sum(len(m['content']) for m in history)>50000:raise ValueError('本次對話超過50,000字，請開始新對話；原訊息仍保留。')
            event=threading.Event()
            with self.store.connect() as db:
                db.execute('INSERT INTO requests(request_id,thread_id,text,status,revision,answers,history,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                    (request_id,tid,text,'pending',state['revision'],encode(state['answers']),encode(history),stamp(),stamp()))
                if state['mode']=='auto':db.execute('INSERT INTO dialogue_routes(request_id,thread_id,contract,selection) VALUES(?,?,1,?)',(request_id,tid,encode(routing_input or {})))
            self._pending[tid]={'request_id':request_id,'cancelled':event}
        return self._perform(tid,text,request_id,state,history,event,False)

    def _perform(self,tid,text,request_id,state,history,event,resume):
        try:
            if hasattr(self.provider,'respond_context'):
                reply=self.provider.respond_context(history,state['mode'],state['answers'],state['assistant_id'],
                    {'conversation_id':'dialogue:'+tid,'request_id':request_id,'cancelled':event.is_set,'resume':resume})
            else:
                reply=self.provider.respond(history,state['mode'],state['answers'],state['assistant_id'])
            expected={'text','answers','route','wire'} if state['mode']=='auto' else {'text','answers'}
            if not isinstance(reply,dict) or set(reply)!=expected or not isinstance(reply['text'],str) or not 1<=len(reply['text'])<=200000:raise ValueError('助理回覆格式無效；原對話保留，沒有產生任務。')
            if state['mode']=='auto':
                from .dialogue_routing import parse
                if parse(reply['wire'])!=reply['route'] or reply['route']['text']!=reply['text']:raise ValueError('辨識回覆不一致。')
            candidate=answers(reply['answers'])
            if state['mode'] in {'chat','auto'} and candidate:raise ValueError('一般聊天不能產生任務。')
            with self.lock:
                self._ensure_open()
                if event.is_set():raise ValueError('對話已取消；晚到回覆沒有保存或建立任務。')
                self.validate_assistant(state['assistant_id'])
                if self.state(tid)['revision']!=state['revision']:raise ValueError('對話條件已改變；晚到回覆未保存。')
                # No provider output can persist a task. Only confirm() below can do so.
                with self.store.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    db.execute('INSERT INTO messages(thread_id,role,text) VALUES(?,\'user\',?)',(tid,text))
                    db.execute('INSERT INTO messages(thread_id,role,text) VALUES(?,\'assistant\',?)',(tid,reply['text']))
                    db.execute('UPDATE threads SET answers=?,revision=revision+1 WHERE id=?',(encode(candidate),tid))
                    db.execute('INSERT INTO turns VALUES(?,?,?)',(request_id,tid,text))
                    if state['mode']=='auto':db.execute('UPDATE dialogue_routes SET wire=?,proposal=? WHERE request_id=?',(reply['wire'],encode(reply['route']),request_id))
                    db.execute("UPDATE requests SET status='completed',recoverable=0,error_code='',remote_state='completed',updated_at=? WHERE request_id=?",(stamp(),request_id))
                    db.execute("UPDATE thread_views SET draft=CASE WHEN draft=? THEN '' ELSE draft END,revision=revision+1,updated_at=? WHERE thread_id=?",(text,stamp(),tid))
                self.previews.pop(tid,None)
                return dict(self.state(tid),busy=False)
        except Exception as exc:
            failure=encode(exc.metadata()) if isinstance(exc,AssistantFailure) else 'request_failed'
            with self.lock,self.store.connect() as db:
                db.execute("UPDATE requests SET status=?,recoverable=0,error_code=?,updated_at=? WHERE request_id=? AND status!='completed'",
                    ('cancelled' if event.is_set() else 'failed','cancelled' if event.is_set() else failure,stamp(),request_id))
            raise
        finally:
            with self._condition:
                if self._pending.get(tid,{}).get('cancelled') is event:self._pending.pop(tid,None)
                self._condition.notify_all()

    def _latest_request(self,tid):
        with self.store.connect() as db:
            row=db.execute('SELECT * FROM requests WHERE thread_id=? ORDER BY rowid DESC LIMIT 1',(tid,)).fetchone()
        if row is None:raise ValueError('沒有可檢查的請求。')
        return dict(row)

    def inspect(self,tid):
        """Explicit retrieval only. Unknown remote writes are never re-issued."""
        with self.lock:
            self._ensure_open();state=self.state(tid)
            if tid in self._pending:raise ValueError('此對話仍有請求處理中。')
            request=self._latest_request(tid)
            if request['status']=='completed':return state
            event=threading.Event();self._pending[tid]={'request_id':request['request_id'],'cancelled':event}
        try:
            if hasattr(self.provider,'inspect_context'):
                result=self.provider.inspect_context(state['mode'],state['assistant_id'],
                    {'conversation_id':'dialogue:'+tid,'request_id':request['request_id']},remote=True)
            else:result={'state':'unsupported','recoverable':False,'remote_checked':False}
            allowed={'not_found','unsupported','completed','polling','failed','cancelled','cancel_requested',
                     'tools_blocked','tool_outcome_unknown','tool_submit_unknown','thread_outcome_unknown',
                     'message_outcome_unknown','run_outcome_unknown','prepared','interrupted'}
            remote_state=result.get('state') if result.get('state') in allowed else 'unknown'
            with self.lock,self.store.connect() as db:
                self._ensure_open()
                if event.is_set():raise ValueError('檢查已取消，未恢復回覆。')
                db.execute('UPDATE requests SET remote_state=?,recoverable=?,updated_at=? WHERE request_id=?',
                    (remote_state,int(result.get('recoverable') is True and request['status']!='cancelled'),stamp(),request['request_id']))
        finally:
            with self._condition:
                if self._pending.get(tid,{}).get('cancelled') is event:self._pending.pop(tid,None)
                self._condition.notify_all()
        result_state=self.state(tid)
        result_state['remote_checked']=result.get('remote_checked') is True
        return result_state

    def recover(self,tid):
        with self.lock:
            self._ensure_open();state=self.state(tid)
            if tid in self._pending:raise ValueError('此對話仍有請求處理中。')
            request=self._latest_request(tid)
            if request['status']=='completed':return state
            if request['status']=='cancelled':raise ValueError('已取消的請求不能恢復，請另開對話。')
            if not request['recoverable']:raise ValueError('請先檢查原請求；未知寫入不能重送。')
            if state['revision']!=request['revision']:raise ValueError('對話條件已變更，請另開對話。')
            self.validate_assistant(state['assistant_id'])
            state['answers']=json.loads(request['answers']);event=threading.Event()
            with self.store.connect() as db:
                db.execute("UPDATE requests SET status='pending',updated_at=? WHERE request_id=?",(stamp(),request['request_id']))
            self._pending[tid]={'request_id':request['request_id'],'cancelled':event}
        return self._perform(tid,request['text'],request['request_id'],state,json.loads(request['history']),event,True)

    def retry_unsent(self,tid,request_id):
        """Explicit retry of proven local preflight failure, never inferred from absence."""
        with self.lock:
            self._ensure_open();state=self.state(tid)
            if tid in self._pending:raise ValueError('此對話仍有請求處理中。')
            request=self._latest_request(tid)
            if request_id!=request['request_id']:raise ValueError('原請求已改變，請重新查看對話。')
            if request['status']=='completed':return state
            if not state['request']['retry_unsent']:
                raise ValueError('不能確認此請求尚未送出；請檢查原請求或另開對話。')
            history=self._history(state,request['text'])
            if (history!=json.loads(request['history']) or state['answers']!=json.loads(request['answers'])):
                raise ValueError('對話內容已改變，未重新送出。')
            self.validate_assistant(state['assistant_id'])
            event=threading.Event()
            with self.store.connect() as db:
                db.execute("UPDATE requests SET status='pending',error_code='',updated_at=? WHERE request_id=?",(stamp(),request['request_id']))
            self._pending[tid]={'request_id':request['request_id'],'cancelled':event}
        return self._perform(tid,request['text'],request['request_id'],state,history,event,False)

    def fork(self,tid,include_history=False,assistant_id=None):
        """New remote context; copying history requires an explicit UI confirmation."""
        if type(include_history) is not bool:raise ValueError('轉交歷史選項無效。')
        with self.lock:
            self._ensure_open();old=self.state(tid)
            if tid in self._pending:raise ValueError('請等背景請求結束後再另開對話。')
            target=assistant_id or old['assistant_id']
            mode=old['mode']
            if mode=='auto' and (include_history or not getattr(self,'routing_allowed',lambda aid:True)(target)):mode='chat'
            new=self.start(mode,target,source_thread_id=tid,draft_text=(old['request'] or {}).get('pending_text','') or old['draft_text'])
            if include_history:
                with self.store.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    for message in old['messages']:
                        db.execute('INSERT INTO messages(thread_id,role,text) VALUES(?,?,?)',(new['id'],message['role'],message['text']))
                    db.execute('UPDATE threads SET answers=? WHERE id=?',(encode(old['answers']),new['id']))
            new=self.state(new['id']);new['draft_text']=(old['request'] or {}).get('pending_text','')
            new['source_thread_id']=tid;new['history_copied']=include_history
            return new

    def _deletion_snapshot(self,db,kind,ids):
        tables={};items=[];threads=[]
        for item_id in ids:
            table='threads' if kind=='threads' else 'task_drafts'
            row=db.execute('SELECT * FROM '+table+' WHERE id=?',(item_id,)).fetchone()
            if row is None:raise ValueError('選定資料已刪除，請重新選擇。')
            row=dict(row);tid=item_id if kind=='threads' else row['thread_id']
            if tid in self._pending or tid in getattr(self,'workspace_pending',set()):raise ValueError('選定對話仍有請求處理中，整批未刪除。')
            tables.setdefault(table,[]).append(row)
            if kind=='threads':
                for child in ('messages','turns','task_drafts','requests','thread_views','continuation_requests','dialogue_routes','workspace_views'):
                    rows=[dict(r) for r in db.execute('SELECT * FROM '+child+' WHERE thread_id=? ORDER BY rowid',(tid,))]
                    tables.setdefault(child,[]).extend(rows)
                title=next((r['text'][:80] for r in tables['messages'] if r['thread_id']==tid and r['role']=='user'),None)
                title=title or next((r['text'][:80] for r in tables['requests'] if r['thread_id']==tid),'空白對話')
                requests=[r['request_id'] for table in ('turns','requests') for r in tables[table] if r['thread_id']==tid]
                threads.append(dict(row,request_ids=sorted(set(requests))))
            else:title=json.loads(row['body']).get('target','未啟用任務草稿')
            items.append({'id':item_id,'title':title})
        ledger_keys=[]
        if kind=='threads' and hasattr(self.provider,'deletion_ledger'):
            path,ledger_keys=self.provider.deletion_ledger(threads)
            if path.exists() and ledger_keys:
                db.execute('ATTACH DATABASE ? AS dialogue_ledger',(str(path),))
                tables['remote_cache']=[]
                for key in ledger_keys:
                    tables['remote_cache'].extend(dict(r) for r in db.execute('SELECT id,data FROM dialogue_ledger.sessions WHERE id=?',(key,)))
                    tables['remote_cache'].extend(dict(r) for r in db.execute('SELECT session_id,id,data FROM dialogue_ledger.requests WHERE session_id=? ORDER BY id',(key,)))
            else:ledger_keys=[]
        digest=hashlib.sha256(encode(tables).encode('utf-8')).hexdigest()
        return {'digest':digest,'counts':{k:len(v) for k,v in tables.items()},'items':items,'ledger_keys':ledger_keys}

    def preview_delete(self,kind,ids):
        if kind not in ('threads','task_drafts'):raise ValueError('刪除類型無效。')
        if not isinstance(ids,list) or not 1<=len(ids)<=1000 or any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('請選擇有效且不重複的資料。')
        ids=sorted(ids)
        with self.lock,self.store.connect() as db:
            self._ensure_open();snapshot=self._deletion_snapshot(db,kind,ids);token=uuid.uuid4().hex
            self.delete_previews={k:v for k,v in self.delete_previews.items() if v['expires']>time.monotonic()}
            self.delete_previews[token]={'kind':kind,'ids':ids,'digest':snapshot['digest'],'expires':time.monotonic()+600}
            return {'token':token,'kind':kind,'counts':snapshot['counts'],'items':snapshot['items'],
                    'permanent':True,'remote_deleted':False,'independent_work_preserved':True}

    def confirm_delete(self,token):
        with self.lock,self.store.connect() as db:
            self._ensure_open();preview=self.delete_previews.get(token)
            if not preview or preview['expires']<=time.monotonic():raise ValueError('刪除預覽已失效，請重新確認。')
            db.execute('BEGIN IMMEDIATE')
            snapshot=self._deletion_snapshot(db,preview['kind'],preview['ids'])
            if snapshot['digest']!=preview['digest']:raise ValueError('資料已變更，請重新預覽後刪除。')
            affected_threads=preview['ids'] if preview['kind']=='threads' else [
                db.execute('SELECT thread_id FROM task_drafts WHERE id=?',(item_id,)).fetchone()[0]
                for item_id in preview['ids']]
            if preview['kind']=='threads':
                for tid in preview['ids']:
                    for child in ('messages','turns','task_drafts','requests'):
                        db.execute('DELETE FROM '+child+' WHERE thread_id=?',(tid,))
                    db.execute('DELETE FROM threads WHERE id=?',(tid,))
                for key in snapshot['ledger_keys']:
                    db.execute('DELETE FROM dialogue_ledger.requests WHERE session_id=?',(key,))
                    db.execute('DELETE FROM dialogue_ledger.sessions WHERE id=?',(key,))
            else:
                for item_id in preview['ids']:db.execute('DELETE FROM task_drafts WHERE id=?',(item_id,))
            db.commit()
            self.delete_previews.pop(token,None)
            for tid in affected_threads:self.previews.pop(tid,None)
            return {'deleted':len(preview['ids']),'kind':preview['kind'],'remote_deleted':False}

    def edit(self,tid,revision,value):
        with self.lock:
            self._ensure_open()
            if tid in self._pending:raise ValueError('對話仍在處理中，請稍後再修改草稿。')
            state=self.state(tid)
            if state['mode']!='task' or state['revision']!=revision:raise ValueError('草稿已變更，請重新查看。')
            value=self.validate_draft(value,state['assistant_id'])
            with self.store.connect() as db:db.execute('UPDATE threads SET answers=?,revision=revision+1 WHERE id=?',(encode(value),tid))
            self.previews.pop(tid,None)
            return self.state(tid)

    def preview(self,tid,revision):
        with self.lock:
            self._ensure_open()
            if tid in self._pending:raise ValueError('對話仍在處理中，請稍後再預覽。')
            state=self.state(tid)
            if state['mode']!='task' or state['revision']!=revision:raise ValueError('草稿已變更，請重新預覽。')
            value=self.validate_draft(state['answers'],state['assistant_id']);token=uuid.uuid4().hex
            self.previews[tid]={'token':token,'revision':revision,'expires':time.monotonic()+600,'draft':value}
            return dict(self.previews[tid],assistant_id=state['assistant_id'],enabled=False)

    def confirm(self,tid,token):
        with self.lock:
            self._ensure_open()
            if tid in self._pending:raise ValueError('對話仍在處理中，請稍後再確認。')
            state=self.state(tid);preview=self.previews.get(tid)
            if not preview or preview['token']!=token or preview['expires']<=time.monotonic() or preview['revision']!=state['revision']:raise ValueError('預覽已失效，請重新核對後確認。')
            value=self.validate_draft(state['answers'],state['assistant_id'])
            if value!=preview['draft']:raise ValueError('草稿已改變。')
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                old=db.execute('SELECT id FROM task_drafts WHERE thread_id=? AND revision=?',(tid,state['revision'])).fetchone()
                if old:return {'id':old['id'],'enabled':False}
                task_id=uuid.uuid4().hex
                db.execute('INSERT INTO task_drafts VALUES(?,?,?,?,?,0,?)',(task_id,tid,state['revision'],state['assistant_id'],encode(value),stamp()))
            return {'id':task_id,'enabled':False}

    def cancel(self,tid):
        with self.lock:
            self.state(tid);self.previews.pop(tid,None)
            return {'cancelled':True,'saved':False}
