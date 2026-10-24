"""Explicit, local notes and conversation continuation. No autonomous memory mining."""
import copy
import json
import math
import threading
import time
import uuid
from .dialogue_service import encode, stamp


def text(value, label, limit, empty=False):
    if not isinstance(value,str) or len(value)>limit or '\x00' in value or (not empty and not value.strip()):
        raise ValueError(f'{label}必須為{limit}字以內的文字。')
    return value


def owner(assistant_id):
    if not isinstance(assistant_id,str):raise ValueError('請選擇助理。')
    if assistant_id.startswith('company:'):
        parts=assistant_id.split(':')
        if len(parts)!=3 or not parts[2].isdigit():raise ValueError('助理識別無效。')
        return ':'.join(parts[:2])
    return assistant_id


class Continuity:
    def __init__(self,session):
        self.session=session;self.dialogue=session.dialogue;self.store=self.dialogue.store
        self.lock=self.dialogue.lock;self.tokens={}

    def ensure(self):
        self.session.assert_identity();self.dialogue._ensure_open()

    def token(self,kind,data):
        self.tokens={k:v for k,v in self.tokens.items() if v[2]>time.monotonic()}
        if len(self.tokens)>=200:self.tokens.pop(next(iter(self.tokens)))
        tid=uuid.uuid4().hex;self.tokens[tid]=(kind,copy.deepcopy(data),time.monotonic()+600);return tid

    def consume(self,tid,kind):
        row=self.tokens.pop(tid,None)
        if not row or row[0]!=kind or row[2]<=time.monotonic():raise ValueError('預覽已失效，請重新確認。')
        return row[1]

    def current_assistant(self,scope):
        catalog=self.dialogue.provider.catalog() if hasattr(self.dialogue.provider,'catalog') else {'assistants':[]}
        rows=catalog.get('assistants',[]) if isinstance(catalog,dict) else catalog
        # ProfileDialogueProvider.catalog returns a list.
        return next((r['id'] for r in rows if owner(r['id'])==scope),scope)

    def row(self,row):
        r=dict(row);r['enabled']=bool(r['enabled']);r['assistant_id']=self.current_assistant(r['assistant_id'])
        with self.store.connect() as db:r['source_deleted']=bool(r['source_thread_id'] and not db.execute('SELECT 1 FROM threads WHERE id=?',(r['source_thread_id'],)).fetchone())
        return r

    def get(self,mid):
        with self.store.connect() as db:r=db.execute('SELECT * FROM memories WHERE id=?',(mid,)).fetchone()
        if not r:raise ValueError('記憶已刪除。')
        return self.row(r)

    def memories(self,assistant_id=None):
        with self.lock:
            self.ensure()
            with self.store.connect() as db:
                rows=db.execute('SELECT * FROM memories'+(' WHERE assistant_id=?' if assistant_id else '')+' ORDER BY updated_at DESC',
                    (owner(assistant_id),) if assistant_id else ()).fetchall()
            return [self.row(r) for r in rows]

    def memory_preview(self,data,mid=None,revision=None):
        with self.lock:
            self.ensure()
            if not isinstance(data,dict) or set(data)-{'title','text','category','assistant_id','source_thread_id'}:raise ValueError('記憶欄位不符。')
            d={k:data.get(k) for k in ('title','text','category','assistant_id','source_thread_id')}
            text(d['title'],'標題',120);text(d['text'],'記憶',2000)
            if d['category'] not in {'preference','background','rule'}:raise ValueError('請選擇記憶種類。')
            self.dialogue.validate_assistant(d['assistant_id'])
            before=self.get(mid) if mid else None
            if before and (before['revision']!=revision or owner(before['assistant_id'])!=owner(d['assistant_id'])):raise ValueError('記憶已變更或目的助理不同。')
            if d['source_thread_id']:
                retained=before and before['source_deleted'] and before['source_thread_id']==d['source_thread_id']
                if not retained:
                    source=self.dialogue.state(d['source_thread_id'])
                    if owner(source['assistant_id'])!=owner(d['assistant_id']):raise ValueError('來源屬於另一位助理，不能直接共享。')
            p={'data':d,'id':mid,'before':before}
            return {'token':self.token('memory',p),'data':d}

    def memory_confirm(self,token):
        with self.lock:
            self.ensure();p=self.consume(token,'memory');d=p['data'];self.dialogue.validate_assistant(d['assistant_id'])
            if p['id'] and self.get(p['id'])!=p['before']:raise ValueError('記憶已變更，請重新預覽。')
            mid=p['id'] or uuid.uuid4().hex;rev=p['before']['revision']+1 if p['before'] else 1
            with self.store.connect() as db:
                db.execute('INSERT OR REPLACE INTO memories VALUES(?,?,?,?,?,?,?,?,?)',
                    (mid,rev,owner(d['assistant_id']),d['title'],d['text'],d['category'],int(p['before']['enabled']) if p['before'] else 1,d['source_thread_id'],stamp()))
            return self.get(mid)

    def manage_preview(self,mid,revision,action):
        with self.lock:
            self.ensure();r=self.get(mid)
            if action not in {'enable','disable','delete'} or r['revision']!=revision:raise ValueError('記憶操作或修訂無效。')
            return {'token':self.token('manage',{'record':r,'action':action}),'data':r}

    def manage_confirm(self,token):
        with self.lock:
            self.ensure();p=self.consume(token,'manage');r=p['record']
            if self.get(r['id'])!=r:raise ValueError('記憶已變更。')
            with self.store.connect() as db:
                if p['action']=='delete':db.execute('DELETE FROM memories WHERE id=?',(r['id'],))
                else:db.execute('UPDATE memories SET enabled=?,revision=revision+1,updated_at=? WHERE id=?',(int(p['action']=='enable'),stamp(),r['id']))
            return {'id':r['id'],'action':p['action'],'previous_snapshots_preserved':True}

    def snapshot(self,assistant_id,ids=None,*,enforce_limit=True):
        rows=[r for r in self.memories(assistant_id) if r['enabled']]
        if ids is not None:
            if not isinstance(ids,list) or any(not isinstance(i,str) for i in ids) or len(ids)!=len(set(ids)):raise ValueError('記憶選擇無效。')
            rows=[r for r in rows if r['id'] in ids]
            if len(rows)!=len(ids):raise ValueError('記憶已停用、刪除或屬於另一位助理。')
        result=[{k:r[k] for k in ('id','revision','title','text','category')} for r in rows]
        if enforce_limit and len(encode(result))>12000:raise ValueError('記憶總長超過12,000字，請先停用不需要的項目；沒有截斷。')
        return result

    def start_preview(self,mode,assistant_id):
        with self.lock:
            self.ensure();self.dialogue.validate_assistant(assistant_id)
            if mode not in {'chat','task','auto'}:raise ValueError('不支援的模式。')
            data={'mode':mode,'assistant_id':assistant_id,'memories':self.snapshot(assistant_id,enforce_limit=False) if mode in {'chat','auto'} else []}
            data['memory_error']='記憶總長超過12,000字；請停用不需要項目，或本次不使用記憶。' if len(encode(data['memories']))>12000 else ''
            return dict(data,token=self.token('start',data))

    def start_confirm(self,token,use_memory):
        with self.lock:
            self.ensure();p=self.consume(token,'start')
            if type(use_memory) is not bool:raise ValueError('請確認是否使用記憶。')
            if use_memory and self.snapshot(p['assistant_id'])!=p['memories']:raise ValueError('記憶已變更，請重新預覽。')
            return self.dialogue.start(p['mode'],p['assistant_id'],memory_snapshot=p['memories'] if use_memory else [])

    def view_save(self,tid,value,scroll,revision):
        with self.lock:
            self.ensure()
            if tid in self.dialogue._pending:raise ValueError('對話仍在處理，草稿稍後再保存。')
            return self._write_view(tid,value,scroll,revision)

    def save_view_for_close(self,value):
        """Host-only local flush of this session's captured draft, including after expiry.

        Not exposed to the bridge/CLI. No identity reads, provider calls or dispatch.
        The host fences new operations first, then cancels/drains via session.close.
        The dialogue lock and CAS still prevent stale writes or deleted-thread revival.
        """
        with self.lock:
            if self.dialogue._closed:raise ValueError('對話已關閉。')
            return self._write_view(value['id'],value['text'],value['scroll'],value['revision'])

    def _write_view(self,tid,value,scroll,revision):
        text(value,'草稿',4000,True)
        if type(scroll) not in (int,float) or not math.isfinite(scroll) or scroll<0:raise ValueError('閱讀位置無效。')
        if type(revision) is not int:raise ValueError('草稿版本無效。')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM threads WHERE id=?',(tid,)).fetchone():raise ValueError('對話不存在。')
            db.execute('INSERT OR IGNORE INTO thread_views(thread_id,updated_at) VALUES(?,?)',(tid,stamp()))
            current=db.execute('SELECT revision FROM thread_views WHERE thread_id=?',(tid,)).fetchone()[0]
            if current!=revision:raise ValueError('草稿已更新，請重新讀取；畫面內容請保留。')
            db.execute('UPDATE thread_views SET draft=?,scroll=?,revision=revision+1,updated_at=? WHERE thread_id=?',(value,scroll,stamp(),tid))
        return {'revision':revision+1}

    def metadata(self,tid,title=None,pinned=None):
        with self.lock:
            self.ensure();self.dialogue.state(tid)
            if title is not None:title=text(title,'對話名稱',120,True).strip()
            if pinned is not None and type(pinned) is not bool:raise ValueError('置頂選擇無效。')
            with self.store.connect() as db:
                db.execute('INSERT OR IGNORE INTO thread_views(thread_id,updated_at) VALUES(?,?)',(tid,stamp()))
                if title is not None:db.execute('UPDATE thread_views SET title=?,updated_at=? WHERE thread_id=?',(title,stamp(),tid))
                if pinned is not None:db.execute('UPDATE thread_views SET pinned=?,updated_at=? WHERE thread_id=?',(int(pinned),stamp(),tid))
            return self.dialogue.state(tid)

    def folders(self):
        with self.lock:
            self.ensure()
            with self.store.connect() as db:
                return [dict(r,collapsed=bool(r['collapsed'])) for r in db.execute('SELECT * FROM dialogue_folders ORDER BY name COLLATE NOCASE,id')]

    @staticmethod
    def folder_name(name):
        name=text(name,'資料夾名稱',60).strip()
        if any(ord(c)<32 for c in name):raise ValueError('資料夾名稱不能包含換行或控制字元。')
        return name

    def folder_create(self,name):
        import sqlite3
        with self.lock:
            self.ensure();name=self.folder_name(name);fid=uuid.uuid4().hex
            try:
                with self.store.connect() as db:db.execute('INSERT INTO dialogue_folders(id,name) VALUES(?,?)',(fid,name))
            except sqlite3.IntegrityError:raise ValueError('已有同名資料夾，請換個名稱。') from None
            return {'id':fid,'name':name,'collapsed':False,'revision':1}

    def folder_update(self,fid,revision,*,name=None,collapsed=None,delete=False):
        import sqlite3
        with self.lock:
            self.ensure()
            if type(revision) is not int:raise ValueError('資料夾版本無效。')
            if name is not None:name=self.folder_name(name)
            if collapsed is not None and type(collapsed) is not bool:raise ValueError('收合設定無效。')
            try:
                with self.store.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    row=db.execute('SELECT * FROM dialogue_folders WHERE id=?',(fid,)).fetchone()
                    if not row or row['revision']!=revision:raise ValueError('資料夾已變更或刪除，請重新讀取。')
                    if delete:
                        db.execute('DELETE FROM dialogue_folders WHERE id=?',(fid,))
                        return {'id':fid,'deleted':True,'conversations_preserved':True}
                    db.execute('UPDATE dialogue_folders SET name=?,collapsed=?,revision=revision+1 WHERE id=?',
                        (name if name is not None else row['name'],int(collapsed) if collapsed is not None else row['collapsed'],fid))
                    return dict(db.execute('SELECT * FROM dialogue_folders WHERE id=?',(fid,)).fetchone())
            except sqlite3.IntegrityError:raise ValueError('已有同名資料夾，請換個名稱。') from None

    def folder_move(self,tid,fid):
        with self.lock:
            self.ensure()
            if fid is not None and not isinstance(fid,str):raise ValueError('資料夾識別無效。')
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if not db.execute('SELECT 1 FROM threads WHERE id=?',(tid,)).fetchone():raise ValueError('對話已刪除。')
                if fid is not None and not db.execute('SELECT 1 FROM dialogue_folders WHERE id=?',(fid,)).fetchone():raise ValueError('資料夾已刪除。')
                db.execute('INSERT OR IGNORE INTO thread_views(thread_id,updated_at) VALUES(?,?)',(tid,stamp()))
                db.execute('UPDATE thread_views SET folder_id=? WHERE thread_id=?',(fid,tid))
            return {'thread_id':tid,'folder_id':fid}

    def continuation_preview(self,tid,assistant_id,value):
        with self.lock:
            self.ensure();old=self.dialogue.state(tid);self.dialogue.validate_assistant(assistant_id);text(value,'接續摘要',4000)
            if tid in self.dialogue._pending:raise ValueError('請等原請求結束再接續。')
            p={'id':tid,'revision':old['revision'],'assistant_id':assistant_id,'text':value}
            return {'token':self.token('continue',p),'text':value,'source_thread_id':tid}

    def continuation_confirm(self,token):
        with self.lock:
            self.ensure();p=self.consume(token,'continue');old=self.dialogue.state(p['id'])
            if old['revision']!=p['revision'] or p['id'] in self.dialogue._pending:raise ValueError('來源對話已變更，請重新確認。')
            mode='auto' if self.session.workspace.allowed(p['assistant_id']) else 'chat'
            return self.dialogue.start(mode,p['assistant_id'],source_thread_id=p['id'],draft_text=p['text'])

    def summarize(self,tid,value,assistant_id,consent):
        if consent is not True:raise ValueError('產生摘要會呼叫助理一次，請先確認。')
        with self.lock:
            self.ensure();old=self.dialogue.state(tid);text(value,'選取內容',12000)
            if value not in '\n\n'.join(m['text'] for m in old['messages']):raise ValueError('請從來源對話選取要整理的內容。')
            if tid in self.dialogue._pending:raise ValueError('原對話仍在處理。')
            binding=self.dialogue.validate_assistant(assistant_id);rid=uuid.uuid4().hex
            with self.store.connect() as db:
                pending=db.execute("SELECT 1 FROM continuation_requests WHERE thread_id=? AND state='unknown'",(tid,)).fetchone()
                if pending:raise ValueError('上次摘要請求結果不明，不重送；可手動整理後接續。')
                db.execute("INSERT OR REPLACE INTO continuation_requests VALUES(?,?,'unknown')",(tid,rid))
            event=threading.Event();self.dialogue._pending[tid]={'request_id':rid,'cancelled':event}
        try:
            if isinstance(binding,dict):
                def call(_):
                    return self.session.profiles.respond([{'role':'user','content':'只摘要以下已選內容，保留未知、限制及未完成問題；不要新增事實，不執行工具。限4000字。\n'+value}],
                        'workflow_plan',binding,context={'run_id':'continuation:'+rid,'step_id':'summary','cancelled':event.is_set})
                result=self.session.skills._remote(binding['profile_id'],call)
            else:result='【離線示範摘要】請自行核對與修改；不是真實 AI 分析。\n'+value
            with self.lock:
                self.ensure()
                with self.store.connect() as db:db.execute("UPDATE continuation_requests SET state='received' WHERE thread_id=? AND request_id=?",(tid,rid))
                if event.is_set():raise ValueError('摘要已取消，晚到回覆未套用。')
                self.dialogue.validate_assistant(assistant_id);text(result,'摘要',4000)
                return {'text':result,'notice':'請核對並修改；確認後只建立新對話草稿，不自動送出。'}
        finally:
            with self.dialogue._condition:
                self.dialogue._pending.pop(tid,None);self.dialogue._condition.notify_all()
