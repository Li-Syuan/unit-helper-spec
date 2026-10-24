"""Shared chat/work coordinator. Local links are recoverable; execution is unchanged."""
import json
from .dialogue_routing import VERSION


class WorkspaceTurns:
    def __init__(self,session):
        self.s=session
        session.dialogue.routing_allowed=self.allowed
        session.dialogue.workspace_pending=set()

    def allowed(self,assistant_id):
        binding=self.s.dialogue.validate_assistant(assistant_id)
        if not isinstance(binding,dict):return True
        with self.s.dialogue.store.connect() as db:
            row=db.execute('SELECT * FROM routing_checks WHERE profile_id=?',(binding['profile_id'],)).fetchone()
        return bool(row and row['revision']==binding['revision'] and row['contract']==VERSION and row['passed'])

    def catalog(self):
        from .dialogue_contracts import ASSISTANTS
        rows=getattr(self.s.dialogue.provider,'catalog',lambda:ASSISTANTS)()
        return [dict(row,automatic=self.allowed(row['id'])) for row in rows]

    def jobs(self):
        self.s.assert_identity()
        with self.s.store.connection() as db:
            rows=db.execute("SELECT o.id,o.data,w.goal,w.state,w.task_id,w.updated_at FROM work_orders o JOIN workflows w ON w.id=json_extract(o.data,'$.workflow_id') WHERE json_extract(o.data,'$.kind')='agent-v1' ORDER BY w.updated_at DESC").fetchall()
        result=[]
        for row in rows:
            data=json.loads(row['data']);task=None
            if row['task_id']:
                try:task=self.s.store.task(row['task_id'])
                except ValueError:pass
            if task and task['state']=='deleted':continue
            result.append({'id':row['id'],'workflow_id':data['workflow_id'],'goal':row['goal'],
                'state':task['state'] if task else row['state'],'task_id':row['task_id'],
                'source_thread':data.get('source_thread'),'updated_at':row['updated_at']})
        return result

    def _target(self,state):
        if not state.get('active_job'):return None
        try:
            job=self.s.agents.state(state['active_job'])
            if job['source_thread']!=state['id']:raise ValueError('工作來源不一致。')
            return job
        except ValueError:return None

    def state(self,tid):
        self.s.assert_identity();state=self.s.dialogue.state(tid)
        state['work']=self._target(state)
        # Reconcile an interrupted local link only; never dispatch on reads/reopen.
        for route in state['routes']:
            if route['job_id']:continue
            import hashlib
            key='turn-'+hashlib.sha256((tid+':'+route['request_id']).encode()).hexdigest()
            try:job=self.s.agents.state(key)
            except ValueError:continue
            route['job_id']=key
        state['composing_work']=bool(state['work'] and not state['work'].get('task') and state['work']['state'] in {'draft','ready','planning'})
        return state

    def select(self,tid,job_id=None,skill_id=None):
        with self.s.engine._lock,self.s.dialogue.lock:
            self.s.engine._ensure_open();self.s.dialogue.state(tid)
            if job_id and self.s.agents.state(job_id)['source_thread']!=tid:raise ValueError('工作屬於其他對話。')
            if skill_id and not self.s.skills.get(skill_id)['enabled']:raise ValueError('Skill 已停用。')
            with self.s.dialogue.store.connect() as db:
                db.execute('INSERT OR IGNORE INTO workspace_views(thread_id) VALUES(?)',(tid,))
                db.execute('UPDATE workspace_views SET active_job=?,skill_id=? WHERE thread_id=?',(job_id,skill_id,tid))
        return self.state(tid)

    def send(self,tid,text,request_id,skill_id=None):
        with self.s.engine._lock,self.s.dialogue.lock:
            self.s.engine._ensure_open();state=self.state(tid)
            with self.s.dialogue.store.connect() as db:
                previous=db.execute('SELECT thread_id,text,status FROM requests WHERE request_id=?',(request_id,)).fetchone()
            if previous:
                if previous['thread_id']!=tid or previous['text']!=text:raise ValueError('請求識別已用於其他內容。')
                if previous['status']=='completed':return state
                raise ValueError('原請求尚未完成，請檢查原請求，不要重新送出。')
            if state['composing_work']:raise ValueError('請補充目前工作，或另開對話。')
            selection={}
            if skill_id:
                skill=self.s.skills.get(skill_id)
                if not skill['enabled']:raise ValueError('Skill 已停用。')
                selection={'skill_id':skill_id,'skill_revision':skill['revision']}
        result=self.s.dialogue.send(tid,text,request_id,routing_input=selection)
        route=next((r for r in result['routes'] if r['request_id']==request_id),None)
        if route and route['proposal'] and route['proposal']['kind']=='work':
            try:return self.propose(tid,request_id)
            except ValueError as exc:
                # A valid conversation remains complete even if work capability is absent.
                result=self.state(tid);result['work_notice']=str(exc);return result
        return self.state(tid)

    def propose(self,tid,request_id):
        s=self.s
        with s.engine._lock,s.dialogue.lock:
            s.engine._ensure_open();state=s.dialogue.state(tid)
            if state['busy'] or tid in s.dialogue.workspace_pending:raise ValueError('請等待目前請求結束。')
            with s.dialogue.store.connect() as db:
                row=db.execute('SELECT r.*,q.text,q.status,q.revision FROM dialogue_routes r JOIN requests q USING(request_id) WHERE r.request_id=? AND r.thread_id=?',(request_id,tid)).fetchone()
            if not row or row['status']!='completed' or not row['proposal']:raise ValueError('沒有已完成的工作建議。')
            proposal=json.loads(row['proposal']);selection=json.loads(row['selection'])
            if row['decision']=='chat':raise ValueError('此建議已選擇直接回答。')
            if proposal['kind'] not in {'work','clarify'}:raise ValueError('普通聊天不是工作建議。')
            if not row['job_id'] and state['revision']!=row['revision']+1:raise ValueError('已有較新的對話，請重新提出需求。')
            binding=s.dialogue.validate_assistant(state['assistant_id'])
            pid=binding['profile_id'] if isinstance(binding,dict) else 'demo'
            if row['job_id']:return self.state(tid)
            # Only this conversation's explicit request becomes a planning goal.
            goal=proposal['goal'] if proposal['kind']=='work' else row['text']
            job=s.agents.create(pid,goal,source_thread=tid,search=proposal['search'],source_request_id=request_id,**selection)
            self._watch(tid,s.workflows.planning.get(job['workflow_id']))
            with s.dialogue.store.connect() as db:
                db.execute('UPDATE dialogue_routes SET job_id=?,decision=\'work\' WHERE request_id=?',(job['id'],request_id))
                db.execute('INSERT OR IGNORE INTO workspace_views(thread_id) VALUES(?)',(tid,))
                db.execute('UPDATE workspace_views SET active_job=? WHERE thread_id=?',(job['id'],tid))
        return self.state(tid)

    def _watch(self,tid,future):
        if future and not future.done():
            self.s.dialogue.workspace_pending.add(tid)
            def done(_):
                with self.s.dialogue.lock:self.s.dialogue.workspace_pending.discard(tid)
            future.add_done_callback(done)

    def reply(self,tid,job_id,revision,text,answers=None):
        with self.s.engine._lock,self.s.dialogue.lock:
            state=self.state(tid)
            if state['active_job']!=job_id or not state['composing_work']:raise ValueError('目前沒有可補充的計畫。')
            job=self.s.agents.reply(job_id,revision,text,answers or {})
            self._watch(tid,self.s.workflows.planning.get(job['workflow_id']))
            with self.s.dialogue.store.connect() as db:
                db.execute("UPDATE thread_views SET draft=CASE WHEN draft=? THEN '' ELSE draft END,revision=revision+1 WHERE thread_id=?",(text,tid))
        return self.state(tid)

    def choose(self,tid,request_id,choice):
        if choice=='work':return self.propose(tid,request_id)
        if choice!='chat':raise ValueError('請選擇直接回答或建立工作計畫。')
        with self.s.dialogue.lock,self.s.dialogue.store.connect() as db:
            state=self.s.dialogue.state(tid)
            row=db.execute('SELECT r.*,q.revision FROM dialogue_routes r JOIN requests q USING(request_id) WHERE r.request_id=? AND r.thread_id=?',(request_id,tid)).fetchone()
            if not row or not row['proposal'] or json.loads(row['proposal'])['kind']!='clarify' or row['job_id'] or row['decision'] or state['busy'] or state['revision']!=row['revision']+1:raise ValueError('此選擇已失效。')
            db.execute("UPDATE dialogue_routes SET decision='chat' WHERE request_id=?",(request_id,))
        return dict(self.state(tid),suggested_draft='請直接回答上一個問題，不要建立工作計畫。')
