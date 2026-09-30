"""One existing company assistant, explicit trial then daily consent. No tool bypass."""
import copy
import hashlib
import re
import time
from .core import dumps,stamp,uid,utcnow,TAIPEI,_NOT_DISPATCHED
from .gateways import GatewayError

DEFAULT_PROMPT=('請搜尋並整理台股、美股與重大總經新聞的財經日報。優先使用最近24小時的可靠來源，'
    '列出重點、需要注意的事件、資料日期及可核對的來源連結。休市時標明最近交易日；'
    '區分事實與推測，不給個人化買賣建議。無法搜尋或資料不足時明確說明，不能編造新聞、行情或來源。')


class AssistantBriefings:
    def __init__(self,engine,profiles):
        self.engine=engine;self.store=engine.store;self.profiles=profiles;self.previews={}
        engine._briefings=self

    def validate(self,spec):
        if not isinstance(spec,dict) or set(spec)!={'binding','prompt','time_hhmm'}:
            raise ValueError('日報設定格式不正確。')
        if not isinstance(spec['prompt'],str) or not 1<=len(spec['prompt'].strip())<=5000:
            raise ValueError('請填寫1至5,000字的日報需求。')
        if not isinstance(spec['time_hhmm'],str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',spec['time_hhmm']):
            raise ValueError('請填寫台北時間 HH:MM。')
        p=self.profiles.validate(spec['binding'])
        if p['id']=='demo' or self.profiles.data.get('wire_mode')!='assistants':
            raise ValueError('財經日報需要已設定的組織 Assistants 助理；示範不能冒充即時新聞。')
        return p

    def preview(self,profile_id,prompt=DEFAULT_PROMPT,time_hhmm='08:00'):
        with self.engine._lock:
            self.engine._ensure_open()
            spec={'binding':self.profiles.snapshot(profile_id),'prompt':prompt,'time_hhmm':time_hhmm}
            p=self.validate(spec);token=uid()
            self.previews={k:v for k,v in self.previews.items() if v['expires']>time.monotonic()}
            self.previews[token]={'spec':copy.deepcopy(spec),'expires':time.monotonic()+600}
            return {'token':token,'assistant_name':p['name'],'prompt':prompt,'time_hhmm':time_hhmm,
                'search_tools':[t['name'] for t in p.get('search_policy',{}).get('tools',[])],
                'message':'尚未執行。現在試跑會把此需求及當次台北時間傳給所選AI 助理，不會啟用排程。'}

    def _insert(self,db,spec,request_id,when,schedule_id=None):
        old=db.execute('SELECT id FROM tasks WHERE request_id=?',(request_id,)).fetchone()
        if old:return old['id'],False
        payload={'spec':copy.deepcopy(spec),'_binding':spec['binding'],'requested_at':stamp(when)}
        tid=uid();digest=hashlib.sha256(dumps(payload).encode()).hexdigest()
        db.execute("INSERT INTO tasks(id,kind,state,payload,request_id,request_hash,schedule_id,created_at) VALUES(?,'assistant_briefing','queued',?,?,?,?,?)",
                   (tid,dumps(payload),request_id,digest,schedule_id,stamp()))
        return tid,True

    def run(self,token):
        with self.engine._lock:
            self.engine._ensure_open();preview=self.previews.get(token)
            if not preview or preview['expires']<=time.monotonic():raise ValueError('日報預覽已過期，請重新預覽。')
            self.validate(preview['spec'])
            with self.store.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                tid,created=self._insert(db,preview['spec'],'briefing-preview:'+token,utcnow())
            if created:self.engine._submit(tid)
            return {'task_id':tid}

    def status(self,tid):
        task=self.store.task(tid)
        if task['kind']!='assistant_briefing':raise ValueError('這不是助理日報。')
        # Local receipt only: never retrieve remote state just to paint a result.
        from .assistants_gateway import session_context
        from .assistant_sessions import AssistantSessions
        path=self.profiles.path.parent/'assistant-sessions.sqlite3'
        activity=[]
        if path.exists():
            key,rid,_,_=session_context(task['payload']['_binding'],'chat',{'conversation_id':'task:'+tid,'request_id':tid})
            receipt=AssistantSessions(path).get_request(key,rid) or {}
            activity=[{'name':c['name'],'state':c['state'],'submitted':b['submit_state']=='submitted'}
                for b in receipt.get('tool_batches',[]) for c in b['calls']]
        task=dict(task,search_activity=activity)
        if not task['schedule_id']:
            with self.store.connection() as db:
                row=db.execute("SELECT id FROM schedules WHERE query_id='ASSISTANT_BRIEFING' AND json_extract(parameters,'$.trial_task')=?",(tid,)).fetchone()
            task=dict(task,schedule_id=row['id'] if row else None)
        if task['schedule_id']:
            with self.store.connection() as db:
                s=db.execute('SELECT * FROM schedules WHERE id=?',(task['schedule_id'],)).fetchone()
            if s is None:task=dict(task,schedule_deleted=True)
            else:task=dict(task,schedule={'enabled':bool(s['enabled']),'time_hhmm':s['time_hhmm'],'next_fire':s['next_fire']})
        return task

    def work(self,tid):
        with self.engine._lock,self.store.connection() as db:
            if not db.execute("UPDATE tasks SET state='running' WHERE id=? AND state='queued'",(tid,)).rowcount:return
            db.execute("UPDATE occurrences SET state='running' WHERE task_id=?",(tid,))
        try:
            task=self.store.task(tid);spec=task['payload']['spec'];self.validate(spec)
            # Actual execution time, including manual tests and delayed catch-up.
            now=utcnow().astimezone(TAIPEI)
            text=('這是使用者已確認的財經日報需求。當次執行時間（Asia/Taipei）：'+now.isoformat()+
                  '\n如無即時搜尋能力，明確說明；不要使用示範或捏造來源。\n'+spec['prompt'])
            reply=self.engine._dispatch_assistant(tid,[{'role':'user','content':text}],'chat')
            if reply is _NOT_DISPATCHED:return
            if not isinstance(reply,str) or not reply.strip() or len(reply)>50000:
                raise GatewayError('助理沒有提供有效日報或內容超限；未截斷、未啟用排程。')
            self.engine._finish(tid,'succeeded',{'text':reply,'received_at':stamp(),
                'search':'not_tested','notice':'已取得助理回覆，請人工核對新聞日期與來源；不是已驗證的市場資料。'})
        except Exception as exc:
            error=str(exc) if isinstance(exc,GatewayError) else '日報未完成，請核對助理連線版本與設定。沒有自動重送。'
            self.engine._finish(tid,'failed',error=error)

    def schedule(self,tid,consent=False,reviewed=False):
        if consent is not True or reviewed is not True:raise ValueError('請先核對日報內容，再同意每日傳送此需求。')
        with self.engine._lock:
            self.engine._ensure_open();task=self.status(tid)
            if task['state']!='succeeded' or not (task.get('result') or {}).get('text'):
                raise ValueError('請先完成一次試跑並核對結果。')
            spec=task['payload']['spec'];self.validate(spec)
            if task['schedule_id']:return self._scheduled(task['schedule_id'])
            sid=uid();now=utcnow();params={'_assistant_briefing':copy.deepcopy(spec),'trial_task':tid}
            with self.store.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute("INSERT INTO schedules(id,name,query_id,parameters,frequency,time_hhmm,weekday,notify_rule,enabled,next_fire,created_at) VALUES(?,'財經日報','ASSISTANT_BRIEFING',?,'daily',?,0,'assistant_briefing',1,?,?)",
                    (sid,dumps(params),spec['time_hhmm'],stamp(self.engine._next_fire({'frequency':'daily','time_hhmm':spec['time_hhmm']},now)),stamp(now)))
            return self._scheduled(sid)

    def _scheduled(self,sid):
        s=self.store.schedule(sid)
        return {'schedule_id':sid,'time_hhmm':s['time_hhmm'],'next_fire':s['next_fire']}

    def claim(self,db,s,key,when):
        if db.execute('SELECT 1 FROM occurrences WHERE schedule_id=? AND scheduled_at=?',(s['id'],key)).fetchone():return None
        pending=[t for f,t in self.engine._future_tasks.items() if not f.done()]
        if db.execute("SELECT 1 FROM tasks WHERE schedule_id=? AND state IN ('queued','running')",(s['id'],)).fetchone() or any(
                db.execute('SELECT 1 FROM tasks WHERE id=? AND schedule_id=?',(t,s['id'])).fetchone() for t in pending):
            db.execute("INSERT INTO occurrences VALUES(?,?,?,'skipped_overlap',NULL)",(uid(),s['id'],key));return None
        spec=s['parameters']['_assistant_briefing']
        try:self.validate(spec)
        except ValueError:
            db.execute("INSERT INTO occurrences VALUES(?,?,?,'failed',NULL)",(uid(),s['id'],key))
            db.execute('UPDATE schedules SET enabled=0 WHERE id=?',(s['id'],))
            db.execute("INSERT OR IGNORE INTO notifications VALUES(?,?,NULL,?,0,?)",(uid(),'briefing-invalid:'+s['id']+':'+key,'財經日報助理設定已變更，已暫停，請重新試跑。',stamp()))
            return None
        tid,_=self._insert(db,spec,'briefing-schedule:'+s['id']+':'+key,when,s['id'])
        db.execute("INSERT INTO occurrences VALUES(?,?,?,'queued',?)",(uid(),s['id'],key,tid));return tid

    def notify(self,db,task,state):
        if state!='succeeded':db.execute('UPDATE schedules SET enabled=0 WHERE id=?',(task['schedule_id'],))
        message='財經日報已取得回覆，請查看並核對來源。' if state=='succeeded' else '財經日報未完成，已暫停自動工作，請查看原因。'
        db.execute('INSERT OR IGNORE INTO notifications VALUES(?,?,?,?,0,?)',(uid(),'task:'+task['id']+':result',task['id'],message,stamp()))
