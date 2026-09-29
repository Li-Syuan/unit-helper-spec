"""Offline two-mode dialogue, validated suggestions and explicit inert-draft saves."""
import json
import threading
import time
import uuid
from datetime import datetime,timezone
from .dialogue_contracts import ASSISTANTS,TASK_TYPES,assistant,answers,draft
from .dialogue_provider import DemoDialogueProvider


def stamp():return datetime.now(timezone.utc).isoformat()
def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True)


class DialogueService:
    def __init__(self,store,provider=None):
        self.store=store;self.provider=provider or DemoDialogueProvider();self.lock=threading.RLock();self.previews={}
        self._condition=threading.Condition(self.lock);self._pending={};self._closed=False

    def _ensure_open(self):
        if self._closed:raise ValueError('程式正在關閉，未送出對話。')

    def has_inflight(self):
        with self.lock:return bool(self._pending)

    def stop(self,tid):
        """Fence the local result immediately; remote cancellation is best effort."""
        with self.lock:
            self.state(tid)
            entry=self._pending.get(tid)
            if entry:entry['cancelled'].set()
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

    def start(self,mode='chat',assistant_id='demo-general'):
        if mode not in {'chat','task'}:raise ValueError('對話模式不支援。')
        self.validate_assistant(assistant_id);tid=uuid.uuid4().hex
        with self.lock,self.store.connect() as db:
            self._ensure_open()
            db.execute('INSERT INTO threads VALUES(?,?,?,\'{}\',1,?)',(tid,mode,assistant_id,stamp()))
        return self.state(tid)

    def state(self,tid):
        with self.lock,self.store.connect() as db:
            row=db.execute('SELECT * FROM threads WHERE id=?',(tid,)).fetchone()
            if row is None:raise ValueError('對話不存在，請開始新對話。')
            thread=dict(row);thread['answers']=json.loads(thread['answers'])
            thread['messages']=[dict(r) for r in db.execute('SELECT role,text FROM messages WHERE thread_id=? ORDER BY id',(tid,))]
            thread['complete']=set(thread['answers'])=={'target','source','task_type','schedule'}
            thread['saved']=[dict(r) for r in db.execute('SELECT id,revision,enabled FROM task_drafts WHERE thread_id=?',(tid,))]
            thread['company']=thread['assistant_id'].startswith('company:')
            return thread

    def list_saved(self):
        with self.lock,self.store.connect() as db:
            return [dict(r,body=json.loads(r['body'])) for r in db.execute('SELECT * FROM task_drafts ORDER BY created_at DESC')]

    def history(self):
        with self.lock,self.store.connect() as db:
            return [dict(r) for r in db.execute("SELECT t.id,t.mode,t.assistant_id,t.created_at,"
                "(SELECT substr(text,1,80) FROM messages WHERE thread_id=t.id AND role='user' ORDER BY id LIMIT 1) AS title "
                "FROM threads t WHERE EXISTS(SELECT 1 FROM messages WHERE thread_id=t.id) ORDER BY t.created_at DESC")]

    def send(self,tid,text,request_id):
        if not isinstance(text,str) or not 1<=len(text.strip())<=4000:raise ValueError('請輸入1～4,000字。')
        if not isinstance(request_id,str) or not 1<=len(request_id)<=150:raise ValueError('送出識別無效。')
        with self.lock:
            self._ensure_open()
            state=self.state(tid)
            with self.store.connect() as db:
                previous=db.execute('SELECT * FROM turns WHERE request_id=?',(request_id,)).fetchone()
                if previous:
                    if previous['thread_id']!=tid or previous['text']!=text:raise ValueError('重複送出內容不一致。')
                    return self.state(tid)
            if tid in self._pending:raise ValueError('此對話仍有請求處理中；取消後也請等遠端請求結束。')
            if any(item['request_id']==request_id for item in self._pending.values()):
                raise ValueError('送出識別已用於另一筆處理中的對話。')
            history=[{'role':m['role'],'content':m['text']} for m in state['messages']]+[{'role':'user','content':text}]
            if sum(len(m['content']) for m in history)>50000:raise ValueError('本次對話超過50,000字，請開始新對話；原訊息仍保留。')
            event=threading.Event()
            self._pending[tid]={'request_id':request_id,'cancelled':event}
        try:
            if hasattr(self.provider,'respond_context'):
                reply=self.provider.respond_context(history,state['mode'],state['answers'],state['assistant_id'],
                    {'conversation_id':'dialogue:'+tid,'request_id':request_id,'cancelled':event.is_set})
            else:
                reply=self.provider.respond(history,state['mode'],state['answers'],state['assistant_id'])
            if not isinstance(reply,dict) or set(reply)!={'text','answers'} or not isinstance(reply['text'],str) or not 1<=len(reply['text'])<=10000:raise ValueError('助理回覆格式無效；原對話保留，沒有產生任務。')
            candidate=answers(reply['answers'])
            if state['mode']=='chat' and candidate:raise ValueError('一般聊天不能產生任務。')
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
                self.previews.pop(tid,None)
                return self.state(tid)
        finally:
            with self._condition:
                self._pending.pop(tid,None)
                self._condition.notify_all()

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
