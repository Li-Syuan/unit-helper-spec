"""Persistent conversation links, separate from model messages and task ownership."""
import copy
import json
import re
import time
from datetime import timedelta


def initialize_action_schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS conversation_actions(
        id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL REFERENCES conversations(id),
        kind TEXT NOT NULL,request TEXT NOT NULL,spec TEXT NOT NULL,binding TEXT,
        revision INTEGER NOT NULL,state TEXT NOT NULL,task_id TEXT,schedule_id TEXT,plan_id TEXT,
        created_at TEXT NOT NULL,updated_at TEXT NOT NULL)''')
    db.execute('CREATE INDEX IF NOT EXISTS action_conversation ON conversation_actions(conversation_id)')
    db.execute('''CREATE TABLE IF NOT EXISTS schedule_sources(
        schedule_id TEXT PRIMARY KEY REFERENCES schedules(id),conversation_id TEXT)''')


class ActionService:
    KINDS={'query','schedule','report','choose','plan'}
    def __init__(self,engine):
        from . import core
        self.core=core;self.engine=engine;self.store=engine.store;self._previews={}
        if not hasattr(engine,'_action_parsing'):engine._action_parsing={}

    def _decode(self,row):
        value=self.store.decode(row)
        value['spec']=json.loads(value['spec'])
        return value

    def get(self,action_id):
        with self.store.connection() as db:
            return self._decode(db.execute('SELECT * FROM conversation_actions WHERE id=?',(action_id,)).fetchone())

    def list(self,cid):
        with self.store.connection() as db:
            return [self._decode(r) for r in db.execute('SELECT * FROM conversation_actions WHERE conversation_id=? ORDER BY rowid',(cid,))]

    def _shape(self,kind,spec):
        allowed={'query_id','parameters'}
        if kind in {'schedule','report'}:allowed|={'name','time_hhmm','frequency','weekday','date_mode','source_task_id'}
        if kind=='plan':allowed={'plan_id','plan_revision'}
        if kind=='choose':allowed=set()
        if kind not in self.KINDS or not isinstance(spec,dict) or set(spec)-allowed:
            raise ValueError('操作類型或欄位不支援。')
        if len(self.core.dumps(spec))>60000:raise ValueError('操作內容過長，請縮小範圍。')

    def create(self,cid,kind,request,spec=None):
        spec=copy.deepcopy(spec or {});self._shape(kind,spec)
        if kind=='plan':raise ValueError('既有計畫請使用連結入口。')
        if not isinstance(request,str) or not request.strip() or len(request)>50000:raise ValueError('請提供有效需求。')
        with self.engine._lock:
            self.engine._ensure_open();convo=self.store.conversation(cid)
            for record in self.list(cid):
                if record['state']=='draft' and record['kind']==kind and record['request']==request and record['spec']==spec:
                    return record
            record_id=self.core.uid()
            with self.store.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT INTO conversation_actions VALUES(?,?,?,?,?,?,1,\'draft\',NULL,NULL,NULL,?,?)',
                    (record_id,cid,kind,request,self.core.dumps(spec),self.core.dumps(convo['binding']),self.core.stamp(),self.core.stamp()))
            return self.get(record_id)

    def adopt_plan(self,cid,plan_id):
        with self.engine._lock:
            plan=self.store.plan(plan_id)
            if plan['conversation_id']!=cid:raise ValueError('計畫不屬於這個對話。')
            for record in self.list(cid):
                if record['plan_id']==plan_id and record['spec'].get('plan_revision')==plan['revision']:return record
            convo=self.store.conversation(cid);record_id=self.core.uid()
            with self.store.connection() as db:
                db.execute('INSERT INTO conversation_actions VALUES(?,?,?,?,?,?,1,\'draft\',NULL,NULL,?,?,?)',
                    (record_id,cid,'plan',plan['payload'].get('text','核對查詢計畫'),
                     self.core.dumps({'plan_id':plan_id,'plan_revision':plan['revision']}),self.core.dumps(convo['binding']),
                     plan_id,self.core.stamp(),self.core.stamp()))
            return self.get(record_id)

    def update(self,action_id,expected_revision,spec,kind=None):
        with self.engine._lock:
            self.engine._ensure_open();record=self.get(action_id)
            if record['state']!='draft' or record['revision']!=expected_revision:raise ValueError('操作已改變，請重新查看。')
            if record['kind']=='plan':raise ValueError('請使用既有計畫修改入口。')
            kind=kind or record['kind'];self._shape(kind,spec)
            if kind=='plan':raise ValueError('不能改送既有計畫。')
            with self.store.connection() as db:
                db.execute('UPDATE conversation_actions SET kind=?,spec=?,revision=revision+1,updated_at=? WHERE id=?',
                    (kind,self.core.dumps(spec),self.core.stamp(),action_id))
            self._previews.pop(action_id,None)
            return self.get(action_id)

    def _validated(self,record):
        from .query_schema import find_template,parameters
        c=self.core;kind=record['kind'];spec=copy.deepcopy(record['spec']);self._shape(kind,spec)
        convo=self.store.conversation(record['conversation_id'])
        if convo['binding']!=record['binding']:raise ValueError('助理連線已改變，請建立新操作。')
        if self.engine.binding_validator:self.engine.binding_validator(record['binding'])
        if kind=='choose':raise ValueError('請選擇要完成的工作。')
        if kind=='plan':
            plan=self.store.plan(record['plan_id'])
            if plan['revision']!=spec['plan_revision'] or plan['state']!='ready' or plan['expires_at']<=c.stamp():
                raise ValueError('計畫已改變或過期，請重新查看。')
            self.engine._validate(plan['kind'],plan['payload']);return spec
        query_id=spec.get('query_id');template=find_template(self.engine.query_catalog(),query_id)
        values=spec.get('parameters',{})
        if not isinstance(values,dict) or any(str(k).startswith('_') for k in values):raise ValueError('查詢參數格式無效。')
        if kind=='query':
            spec['parameters']=parameters(template,values)
            self.engine._validate('query',spec);return spec
        name=spec.get('name');at=spec.get('time_hhmm')
        if not isinstance(name,str) or not name.strip() or len(name)>120:raise ValueError('請填寫 1～120 字工作名稱。')
        if not isinstance(at,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',at):raise ValueError('請填寫台北時間 HH:MM。')
        if spec.get('frequency') not in {'daily','weekly'} or type(spec.get('weekday',0)) is not int or spec.get('weekday',0) not in range(7):
            raise ValueError('請選擇每日或每週與星期。')
        spec.setdefault('weekday',0)
        if spec.get('date_mode') not in {'literal','previous_day'}:raise ValueError('請選擇固定條件或每次前一日。')
        if spec.get('source_task_id'):
            source=self.store.task(spec['source_task_id'])
            if source['state']!='succeeded' or source['kind']!='query' or source['payload']['query_id']!=query_id:
                raise ValueError('來源查詢不是成功的同一模板。')
        schedule=dict(spec,parameters=dict(values,_date_mode=spec['date_mode']))
        if kind=='report':
            if not hasattr(self.engine,'_report_binding'):raise ValueError('這個工作區未開放日報整理。')
            schedule['parameters']['_report']={'version':1,'binding':record['binding']}
        effective=self.engine._schedule_parameters(schedule,c.utcnow())
        spec['parameters']=effective
        return spec

    def preview(self,action_id,revision):
        with self.engine._lock:
            self.engine._ensure_open()
            record=self.get(action_id)
            try:
                if record['revision']!=revision or record['state']!='draft':raise ValueError('操作已改變，請重新查看。')
                if action_id in self.engine._action_parsing:raise ValueError('正在整理條件，請稍候。')
                spec=self._validated(record)
                self._previews[action_id]={'revision':revision,'expires':time.monotonic()+600,'spec':spec}
                return dict(record,ready=True,error='',spec=spec)
            except ValueError as exc:
                self._previews.pop(action_id,None)
                return dict(record,ready=False,error=str(exc))

    def confirm(self,action_id,revision,consent=False):
        c=self.core
        with self.engine._lock:
            self.engine._ensure_open();record=self.get(action_id)
            if record['revision']!=revision:raise ValueError('操作已修改，請重新確認。')
            if record['state']=='submitted':return self.get(action_id)
            p=self._previews.get(action_id)
            if record['state']!='draft' or not p or p['revision']!=revision or p['expires']<=time.monotonic():
                raise ValueError('確認已取消或過期，請重新核對。')
            if action_id in self.engine._action_parsing:raise ValueError('解析尚未結束。')
            # Revalidate immutable input and binding. Rolling dates are resolved at execution.
            self._validated(record);spec=p['spec'];kind=record['kind'];task_id=None;sid=None;created=False
            if kind=='report' and consent is not True:raise ValueError('請確認每次彙總資料傳送授權。')
            with self.store.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                if kind=='plan':
                    task_id,created=self.engine._confirm_plan_tx(db,record['plan_id'],spec['plan_revision'],'action:'+action_id)
                elif kind=='query':
                    task_id,created=self.engine._new_task(db,'query',spec,request_id='action:'+action_id)
                elif kind in {'schedule','report'}:
                    sid=c.uid();schedule=dict(spec,parameters=dict(spec['parameters'],_date_mode=spec['date_mode']))
                    if kind=='report':schedule['parameters']['_report']={'version':1,'binding':record['binding']}
                    db.execute('''INSERT INTO schedules(id,name,query_id,parameters,frequency,time_hhmm,weekday,
                        notify_rule,enabled,next_fire,created_at) VALUES(?,?,?,?,?,?,?,'nonempty_on_change',1,?,?)''',
                        (sid,spec['name'],spec['query_id'],c.dumps(schedule['parameters']),spec['frequency'],spec['time_hhmm'],
                         spec['weekday'],c.stamp(self.engine._next_fire(schedule,c.utcnow())),c.stamp()))
                    db.execute('INSERT INTO schedule_sources VALUES(?,?)',(sid,record['conversation_id']))
                db.execute('UPDATE conversation_actions SET state=\'submitted\',task_id=?,schedule_id=?,updated_at=? WHERE id=?',
                    (task_id,sid,c.stamp(),action_id))
            if created:self.engine._submit(task_id)
            return self.get(action_id)

    def cancel(self,action_id):
        with self.engine._lock:
            record=self.get(action_id)
            if record['schedule_id']:raise ValueError('請暫停已啟用的自動工作。')
            if record['task_id'] and self.store.task(record['task_id'])['state'] not in {'queued','running'}:
                raise ValueError('這項工作已結束，不需要取消。')
            if record['plan_id']:
                plan=self.store.plan(record['plan_id'])
                if plan['revision']!=record['spec']['plan_revision']:
                    raise ValueError('這是舊修訂，不能取消目前計畫。')
                if plan['state'] in {'succeeded','failed','cancelled'}:
                    raise ValueError('這項計畫已結束，不需要取消。')
                self.engine.cancel_plan(record['plan_id'])
            elif record['task_id']:self.engine.cancel_task(record['task_id'])
            with self.store.connection() as db:
                db.execute('UPDATE conversation_actions SET state=\'cancelled\',revision=revision+1,updated_at=? WHERE id=?',
                           (self.core.stamp(),action_id))
            self._previews.pop(action_id,None)
            return self.get(action_id)

    def snapshot(self,action_id):
        record=self.get(action_id);task=None;schedule=None;plan=None;status=record['state'];error=''
        if record['plan_id']:
            plan=self.store.plan(record['plan_id']);status=plan['state']
            if plan['task_id'] and plan['revision']==record['spec']['plan_revision']:task=self.store.task(plan['task_id'])
            if status=='ready' and plan['expires_at']<=self.core.stamp():status='expired'
            if plan['revision']!=record['spec']['plan_revision']:status='expired'
        if record['task_id']:task=self.store.task(record['task_id'])
        if record['schedule_id']:
            schedule=self.store.schedule(record['schedule_id']);status='enabled' if schedule['enabled'] else 'disabled'
            runs=[r for r in self.store.schedule_runs(schedule['id']) if r['task_id']]
            if runs:task=self.store.task(runs[0]['task_id'])
        if task:
            status=task['state'];error=task['error'] or ''
        if action_id in self.engine._action_parsing:status='parsing'
        return dict(record,status=status,task=task,schedule=schedule,plan=plan,result=task['result'] if task else None,error=error)

    def run_now(self,action_id,request_id):
        with self.engine._lock:
            record=self.get(action_id)
            if not record['schedule_id']:raise ValueError('尚未建立自動工作。')
            if not request_id:raise ValueError('需要本次測試識別。')
            return self.engine.run_schedule_now(record['schedule_id'],request_id)

    def begin_parse(self,action_id,revision):
        with self.engine._lock:
            self.engine._ensure_open();record=self.get(action_id)
            if record['revision']!=revision or record['state']!='draft' or action_id in self.engine._action_parsing:
                raise ValueError('操作已改變或正在解析。')
            self.engine._action_parsing[action_id]=record['conversation_id'];self._previews.pop(action_id,None)

    def end_parse(self,action_id):
        with self.engine._lock:self.engine._action_parsing.pop(action_id,None)

    def apply_parse(self,action_id,revision,spec,kind=None):
        with self.engine._lock:
            if self.engine._closed:return None
            try:record=self.get(action_id)
            except ValueError:return None
            if record['state']!='draft' or record['revision']!=revision:return None
            return self.update(action_id,revision,spec,kind)
