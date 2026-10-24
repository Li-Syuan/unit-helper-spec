"""Explicit local content deletion; minimal task receipts retain idempotency."""
import hashlib
import json
import time
import uuid
from contextlib import ExitStack

LABELS = {'tasks':'工作與成果', 'schedules':'自動工作', 'plans':'待確認計畫',
          'workflows':'分工流程', 'issues':'問題回報', 'notifications':'通知', 'local_forms':'選項表單'}


class DataCleanup:
    def __init__(self, engine):
        self.engine=engine;self.store=engine.store;self.previews={}

    def catalog(self):
        result={}
        with self.engine._lock,self.store.connection() as db:
            for kind,label in LABELS.items():
                if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(kind,)).fetchone():continue
                rows=[]
                for r in db.execute(f'SELECT * FROM {kind} ORDER BY rowid DESC'):
                    r=dict(r)
                    if r.get('state')=='deleted':continue
                    rows.append({'id':r['id'],'title':r.get('name') or r.get('title') or r.get('goal') or r.get('kind') or label,
                                 'state':r.get('state') or ('已啟用' if r.get('enabled') else '已暫停') if kind=='schedules' else r.get('state',''),
                                 'created_at':r.get('created_at','')})
                result[kind]={'label':label,'items':rows}
        return result

    def _snapshot(self, db, kind, ids):
        if kind not in LABELS:raise ValueError('不支援此資料類別。')
        marks=','.join('?' for _ in ids)
        rows=[dict(r) for r in db.execute(f'SELECT * FROM {kind} WHERE id IN ({marks}) ORDER BY id',ids)]
        if len(rows)!=len(ids) or any(r.get('state')=='deleted' for r in rows):raise ValueError('選定資料已刪除，請重新整理。')
        data={'selected':rows}
        task_ids=set(ids) if kind=='tasks' else set()
        if kind=='schedules':
            if any(r['enabled'] for r in rows):raise ValueError('請先暫停選定的自動工作，再刪除。')
            data['runs']=[dict(r) for r in db.execute(f'SELECT * FROM occurrences WHERE schedule_id IN ({marks}) ORDER BY id',ids)]
            task_ids.update(r['id'] for r in db.execute(f'SELECT id FROM tasks WHERE schedule_id IN ({marks})',ids))
        if kind=='workflows':
            for row in rows:
                future=getattr(self.engine,'_workflows',None)
                if future and row['id'] in future.planning:raise ValueError('分工仍在規劃，請等待或取消收尾。')
                if row['schedule_id']:raise ValueError('此流程仍有自動工作，請先刪除其排程。')
                task_ids.update(r['id'] for r in db.execute("SELECT id FROM tasks WHERE json_extract(payload,'$.workflow.id')=?",(row['id'],)))
            data['versions']=[dict(r) for r in db.execute(f'SELECT * FROM workflow_versions WHERE workflow_id IN ({marks}) ORDER BY workflow_id,revision',ids)]
            data['agent_orders']=[dict(r) for r in db.execute(f"SELECT * FROM work_orders WHERE json_extract(data,'$.kind')='agent-v1' AND json_extract(data,'$.workflow_id') IN ({marks}) ORDER BY id",ids)]
        if kind=='plans':
            if any(r['state']=='executing' for r in rows):raise ValueError('計畫仍在執行。')
            task_ids.update(r['task_id'] for r in rows if r['task_id'])
        if task_ids:
            tm=','.join('?' for _ in task_ids);args=sorted(task_ids)
            data['tasks']=[dict(r) for r in db.execute(f'SELECT * FROM tasks WHERE id IN ({tm}) ORDER BY id',args)]
            if any(r['state'] in ('queued','running','executing') for r in data['tasks']) or any(
                tid in task_ids and not future.done() for future,tid in self.engine._future_tasks.items()
            ) or task_ids & self.engine._assistant_dispatching:
                raise ValueError('工作仍在執行或取消收尾中；未刪除任何資料。')
            if kind=='tasks':
                for table in ('workflow_steps','outcome_feedback','notifications','conversation_actions','plans','workflows','occurrences'):
                    data[table]=[dict(r) for r in db.execute(f'SELECT * FROM {table} WHERE task_id IN ({tm}) ORDER BY rowid',args)]
        if kind=='schedules':
            for table in ('schedule_sources','conversation_actions','workflows'):
                data[table]=[dict(r) for r in db.execute(f'SELECT * FROM {table} WHERE schedule_id IN ({marks}) ORDER BY rowid',ids)]
        if kind=='plans':
            data['actions']=[dict(r) for r in db.execute(f'SELECT * FROM conversation_actions WHERE plan_id IN ({marks}) ORDER BY rowid',ids)]
        if kind in ('tasks','workflows'):data['cache']=self._cache_snapshot(db,kind,rows)
        digest=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,
            default=lambda item: {'blob_hash':hashlib.sha256(item).hexdigest()} if isinstance(item,bytes) else str(type(item))).encode()).hexdigest()
        return rows,digest

    def preview(self,kind,ids):
        if not isinstance(ids,list) or not ids or len(ids)>500 or any(not isinstance(i,str) or not i for i in ids):
            raise ValueError('請選擇1至500筆資料。')
        ids=sorted(set(ids))
        with self.engine._lock,self.store.connection() as db:
            self.engine._ensure_open();db.execute('BEGIN')
            rows,digest=self._snapshot(db,kind,ids)
            now=time.monotonic();self.previews={k:v for k,v in self.previews.items() if v['expires']>now}
            token=uuid.uuid4().hex;self.previews[token]=dict(kind=kind,ids=ids,digest=digest,expires=now+600)
        note={'tasks':'刪除選定工作輸入、成果、分工輸出、評價及通知；保留獨立對話、流程定義與排程。保留最少防重識別，舊請求不會重新執行。',
              'schedules':'刪除排程與觸發紀錄；已完成成果保留，可另行刪除。',
              'workflows':'刪除流程定義及修訂；已完成成果保留，可另行刪除。',
              'plans':'刪除計畫，已完成工作保留。'}.get(kind,'永久刪除選定本機內容。')
        return dict(token=token,kind=kind,label=LABELS[kind],count=len(rows),
                    items=[{'id':r['id'],'title':r.get('title') or r.get('name') or r.get('goal') or r.get('kind') or LABELS[kind]} for r in rows],
                    notice=note+' 不刪除服務端資料、原始附件、匯出檔或備份；應用無法復原。')

    def confirm(self,token):
        with self.engine._lock:
            self.engine._ensure_open();saved=self.previews.get(token)
            if not saved or saved['expires']<=time.monotonic():raise ValueError('刪除預覽已失效，請重新確認。')
            kind,ids=saved['kind'],saved['ids'];marks=','.join('?' for _ in ids)
            with ExitStack() as locks,self.store.connection() as db:
                # Status retrieval also writes the local ledger after its GET. Hold
                # the same non-blocking session locks through the deletion commit.
                if kind in ('tasks','workflows'):
                    selected=[dict(r) for r in db.execute(f'SELECT * FROM {kind} WHERE id IN ({marks})',ids)]
                    self._lock_cache(selected,kind,locks)
                db.execute('BEGIN IMMEDIATE');rows,digest=self._snapshot(db,kind,ids)
                if digest!=saved['digest']:
                    self.previews.pop(token,None);raise ValueError('資料已變更，請重新預覽。')
                if kind=='tasks':
                    self._forget_task_cache(db,rows)
                    for table in ('workflow_steps','outcome_feedback','notifications','conversation_actions'):
                        db.execute(f'DELETE FROM {table} WHERE task_id IN ({marks})',ids)
                    db.execute(f"UPDATE plans SET payload='{{}}',state='cancelled',task_id=NULL WHERE task_id IN ({marks})",ids)
                    db.execute(f'UPDATE workflows SET task_id=NULL WHERE task_id IN ({marks})',ids)
                    db.execute(f"UPDATE occurrences SET state='deleted',task_id=NULL WHERE task_id IN ({marks})",ids)
                    # Keep request IDs and hashes only to prevent old confirmations from dispatching again.
                    db.execute(f"UPDATE tasks SET state='deleted',payload='{{}}',result=NULL,error=NULL,conversation_id=NULL,plan_id=NULL WHERE id IN ({marks})",ids)
                else:
                    if kind=='schedules':
                        db.execute(f'DELETE FROM occurrences WHERE schedule_id IN ({marks})',ids)
                        db.execute(f'DELETE FROM schedule_sources WHERE schedule_id IN ({marks})',ids)
                        db.execute(f'UPDATE workflows SET schedule_id=NULL WHERE schedule_id IN ({marks})',ids)
                        db.execute(f'DELETE FROM conversation_actions WHERE schedule_id IN ({marks})',ids)
                    elif kind=='workflows':
                        self._forget_planner_cache(db,rows)
                        db.execute(f'DELETE FROM workflow_versions WHERE workflow_id IN ({marks})',ids)
                        db.execute(f"DELETE FROM work_orders WHERE json_extract(data,'$.kind')='agent-v1' AND json_extract(data,'$.workflow_id') IN ({marks})",ids)
                    elif kind=='plans':
                        db.execute(f'DELETE FROM conversation_actions WHERE plan_id IN ({marks})',ids)
                        db.execute(f'UPDATE tasks SET plan_id=NULL WHERE plan_id IN ({marks})',ids)
                    db.execute(f'DELETE FROM {kind} WHERE id IN ({marks})',ids)
            self.previews.pop(token,None)
            workflows=getattr(self.engine,'_workflows',None)
            if kind=='workflows' and workflows:
                for wid in ids:workflows.previews.pop(wid,None)
            return dict(deleted=True,kind=kind,ids=ids)

    def _cache_targets(self,rows,kind):
        from .assistants_gateway import session_context
        keys=set();request_keys=[]
        for row in rows:
            if kind=='workflows':
                binding=json.loads(row['planner'])
                if not isinstance(row['revision'],int) or not 1<=row['revision']<=100000:
                    raise ValueError('流程修訂資料無效，未刪除。')
                for revision in range(1,row['revision']+1):
                    keys.add(session_context(binding,'workflow_step',{'run_id':row['id']+':'+str(revision),'step_id':'planner'})[0])
                continue
            payload=json.loads(row['payload']);binding=payload.get('_binding')
            if binding:
                keys.add(session_context(binding,'chat',{'conversation_id':'task:'+row['id']})[0])
                if row['conversation_id']:
                    request_keys.append((session_context(binding,'chat',{'conversation_id':'engine:'+row['conversation_id']})[0],row['id']))
            spec=payload.get('workflow',{})
            if 'agent' in spec:
                if spec['agent'].get('version')==2:
                    workflows=getattr(self.engine,'_workflows',None)
                    if not workflows:raise ValueError('無法核對自主工作收據，未刪除。')
                    steps=list(workflows._runtime_definitions({'payload':payload},workflows.get_task_steps(row['id'])).values())
                else:
                    from .agent_execution import expanded_steps
                    steps=expanded_steps(spec)
            else:steps=spec.get('steps',[])
            for step in steps:
                binding=step.get('binding')
                if binding:keys.add(session_context(binding,'workflow_step',{'run_id':row['id'],'step_id':step['id']})[0])
        return keys,request_keys

    def _lock_cache(self,rows,kind,locks):
        from .assistant_sessions import AssistantSessions
        path=self.store.path.with_name('assistant-sessions.sqlite3')
        if not path.exists():return
        keys,requests=self._cache_targets(rows,kind)
        ledger=AssistantSessions(path)
        for key in sorted(keys|{key for key,rid in requests}):locks.enter_context(ledger.session(key))

    @staticmethod
    def _attach(db,path,name):
        if path.exists() and name not in {r['name'] for r in db.execute('PRAGMA database_list')}:
            db.execute(f'ATTACH DATABASE ? AS {name}',(str(path),))
        return name in {r['name'] for r in db.execute('PRAGMA database_list')}

    def _cache_snapshot(self,db,kind,rows):
        keys,requests=self._cache_targets(rows,kind);data={}
        path=self.store.path.with_name('assistant-sessions.sqlite3')
        if self._attach(db,path,'cleanup_cache'):
            data['sessions']=[];data['requests']=[]
            for key in sorted(keys|{key for key,rid in requests}):
                data['sessions'].extend(dict(r) for r in db.execute('SELECT * FROM cleanup_cache.sessions WHERE id=?',(key,)))
            for key in sorted(keys):
                data['requests'].extend(dict(r) for r in db.execute('SELECT * FROM cleanup_cache.requests WHERE session_id=? ORDER BY id',(key,)))
            for key,rid in sorted(requests):
                data['requests'].extend(dict(r) for r in db.execute('SELECT * FROM cleanup_cache.requests WHERE session_id=? AND id=?',(key,rid)))
        if kind=='tasks' and self._attach(db,self.store.path.with_name('workflow-checkpoints.sqlite3'),'cleanup_graph'):
            for table in ('checkpoints','writes'):
                if db.execute("SELECT 1 FROM cleanup_graph.sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                    data[table]=[]
                    for row in rows:
                        data[table].extend(dict(r) for r in db.execute(f'SELECT * FROM cleanup_graph.{table} WHERE thread_id=? ORDER BY rowid',(row['id'],)))
        return data

    def _forget_planner_cache(self,db,rows):
        keys,_=self._cache_targets(rows,'workflows')
        if self._attach(db,self.store.path.with_name('assistant-sessions.sqlite3'),'cleanup_cache'):
            for key in keys:
                db.execute('DELETE FROM cleanup_cache.requests WHERE session_id=?',(key,))
                db.execute('DELETE FROM cleanup_cache.sessions WHERE id=?',(key,))

    def _forget_task_cache(self,db,rows):
        keys,request_keys=self._cache_targets(rows,'tasks')
        path=self.store.path.with_name('assistant-sessions.sqlite3')
        if path.exists():
            self._attach(db,path,'cleanup_cache')
            for key in keys:
                db.execute('DELETE FROM cleanup_cache.requests WHERE session_id=?',(key,))
                db.execute('DELETE FROM cleanup_cache.sessions WHERE id=?',(key,))
            for key,rid in request_keys:
                entry=db.execute('SELECT data FROM cleanup_cache.requests WHERE session_id=? AND id=?',(key,rid)).fetchone()
                if entry:
                    value=json.loads(entry['data']);value['result']='';value['tool_batches']=[]
                    # Completed history remains a valid prefix for the next turn.
                    # Failed/unknown writes retain their original non-retry fence.
                    db.execute('UPDATE cleanup_cache.requests SET data=? WHERE session_id=? AND id=?',(json.dumps(value),key,rid))
        # Checkpoints contain IDs only, but remove them in the same attached transaction.
        checkpoint=self.store.path.with_name('workflow-checkpoints.sqlite3')
        if checkpoint.exists():
            self._attach(db,checkpoint,'cleanup_graph')
            for table in ('checkpoints','writes'):
                if db.execute("SELECT 1 FROM cleanup_graph.sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                    db.executemany(f'DELETE FROM cleanup_graph.{table} WHERE thread_id=?',[(r['id'],) for r in rows])
