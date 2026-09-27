import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from desktop_app.core import Store, Engine
from desktop_app.gateways import DemoQueries
from desktop_app.trial import TrialProfiles
from desktop_app.workflows import WorkflowService, json_object


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.db'
        self.store=Store(self.path);self.profiles=TrialProfiles();self.queries=DemoQueries()
        self.calls=[];self.query_calls=[];self.gate=threading.Event();self.gate.set()
        self.fail_role=None;self.needs_attention=False;self.plan_response=None
        self.profiles.workflow_call=self.call
        self.engine=Engine(self.store,self.query,None,query_validator=self.queries.validate,query_catalog=self.queries.catalog)
        self.service=WorkflowService(self.engine,self.profiles)
        self.cid=self.store.create_conversation('合成測試',self.profiles.default_binding())

    def tearDown(self):
        self.gate.set();self.engine.close(wait=True);self.tmp.cleanup()

    def query(self,q,p):
        self.query_calls.append((q,copy.deepcopy(p)));return self.queries.run(q,p)

    def call(self,messages,role,binding,context):
        self.calls.append((copy.deepcopy(messages),role,copy.deepcopy(binding),copy.deepcopy(context)))
        self.gate.wait(5)
        if role==self.fail_role:raise RuntimeError('PRIVATE_FAKE_SECRET')
        if role=='planner':
            return json.dumps(self.plan_response or {'message':'建議四個步驟','questions':[],
                'steps':[dict({k:v for k,v in s.items() if k!='binding'},**({'profile_id':s['binding']['profile_id']} if 'binding' in s else {})) for s in self.steps()]},ensure_ascii=False)
        text=messages[-1]['content'];payload=json.loads(text.split('核准工作與輸入：')[1])
        facts={}
        for source in payload['sources'].values():facts.update(source.get('numeric_totals',source.get('facts',{})))
        result={'text':role+' 合成成果','facts':facts}
        if role=='review':result['verdict']='needs_attention' if self.needs_attention else 'pass'
        return json.dumps(result)

    def steps(self):
        result=[{'id':'s1','title':'查數據','kind':'query','query_id':'DEMO03','parameters':{'category':'A'},'date_mode':'previous_day','inputs':[]}]
        for sid,role,inputs in [('s2','analysis',['s1']),('s3','review',['s1','s2']),('s4','compose',['s1','s2','s3'])]:
            result.append({'id':sid,'title':role,'kind':'assistant','role':role,'binding':self.profiles.workflow_binding('groq-'+role),'instruction':'依原始資料完成工作','inputs':inputs})
        return result

    def ready(self):
        r=self.service.create(self.cid,'查昨天 A 類數量並分析覆核製作日報',self.profiles.workflow_binding('groq-planner'))
        return self.service.update(r['id'],r['revision'],self.steps())

    def approve(self,r):
        self.assertTrue(self.service.preview(r['id'],r['revision'])['ready'])
        return self.service.confirm(r['id'],r['revision'],True)

    def wait(self,tid):
        deadline=time.monotonic()+8
        while self.store.task(tid)['state'] in {'queued','running'} and time.monotonic()<deadline:time.sleep(.01)
        task=self.store.task(tid);self.assertNotIn(task['state'],{'queued','running'})
        while self.engine.has_inflight() and time.monotonic()<deadline:time.sleep(.01)
        return task

    def wait_plan(self,wid):
        deadline=time.monotonic()+8
        while self.engine.has_inflight() and time.monotonic()<deadline:time.sleep(.01)
        return self.service.get(wid)

    def test_discussion_questions_then_plan_without_dispatch(self):
        self.plan_response={'message':'請選類別','questions':[{'id':'q1','text':'類別？','type':'single','options':['A','B']}],'steps':[]}
        r=self.service.create(self.cid,'幫我產生報表',self.profiles.workflow_binding('groq-planner'))
        r=self.service.discuss(r['id'],r['revision'],'請先問我缺少的資料');r=self.wait_plan(r['id'])
        self.assertEqual(r['state'],'draft');self.assertEqual(len(r['questions']),1)
        self.assertFalse(self.service.preview(r['id'],r['revision'])['ready'])
        self.plan_response=None
        r=self.service.discuss(r['id'],r['revision'],'A 類，昨天，分析覆核日報');r=self.wait_plan(r['id'])
        self.assertEqual(r['state'],'ready');self.assertEqual(len(r['steps']),4)
        self.assertEqual([c[1] for c in self.calls],['planner','planner'])
        self.assertEqual(self.query_calls,[]);self.assertEqual(self.store.tasks(),[]);self.assertEqual(self.store.messages(self.cid),[])

    def test_approve_runs_real_sequence_once_with_isolated_inputs(self):
        r=self.ready();tid=self.approve(r);task=self.wait(tid)
        self.assertEqual(task['state'],'succeeded',task['error'])
        self.assertEqual(self.service.confirm(r['id'],r['revision'],True),tid)
        self.assertEqual(len(self.query_calls),1);self.assertEqual([c[1] for c in self.calls],['analysis','review','compose'])
        self.assertEqual(len({c[3]['step_id'] for c in self.calls}),3)
        self.assertEqual({c[3]['run_id'] for c in self.calls},{tid})
        self.assertEqual(self.store.messages(self.cid),[])
        self.assertNotIn('rows',self.calls[0][0][0]['content'])
        self.assertEqual(len(self.service.get_task_steps(tid)),4)

    def test_preview_consent_expiry_and_revision(self):
        r=self.ready()
        with self.assertRaises(ValueError):self.service.confirm(r['id'],r['revision'],True)
        self.service.preview(r['id'],r['revision'])
        with self.assertRaises(ValueError):self.service.confirm(r['id'],r['revision'],False)
        with patch('desktop_app.workflows.time.monotonic',return_value=time.monotonic()+601):
            with self.assertRaises(ValueError):self.service.confirm(r['id'],r['revision'],True)
        self.service.preview(r['id'],r['revision']);n=self.service.update(r['id'],r['revision'],self.steps())
        with self.assertRaises(ValueError):self.service.confirm(n['id'],n['revision'],True)
        self.assertEqual(self.query_calls,[])

    def test_invalid_steps_and_capability(self):
        for mutate in [lambda s:s[0].update(kind='shell'),lambda s:s[1].update(inputs=['s4']),
                       lambda s:s[1].update(binding={'profile_id':'unknown','revision':1}),
                       lambda s:s[0].update(sql='SELECT *'),lambda s:s[0].update(query_id='UNKNOWN')]:
            steps=self.steps();mutate(steps)
            with self.assertRaises(ValueError):self.service.validate_steps(steps)
        with self.assertRaises(ValueError):self.service.validate_steps(self.steps()*2)
        self.assertFalse(self.query_calls)

    def test_cancel_planner_late_reply_and_delete_fence(self):
        self.gate.clear();r=self.service.create(self.cid,'合成工作',self.profiles.workflow_binding('groq-planner'))
        self.service.discuss(r['id'],1,'規劃');time.sleep(.03);self.service.cancel(r['id'])
        with self.assertRaises(ValueError):self.engine.preview_conversation_deletion([self.cid])
        self.gate.set();r=self.wait_plan(r['id']);self.assertEqual(r['state'],'cancelled');self.assertEqual(r['steps'],[])
        p=self.engine.preview_conversation_deletion([self.cid]);self.engine.delete_conversations(p['token'])
        self.assertEqual(self.service.list(self.cid),[])

    def test_cancel_worker_late_result_and_delete_fence(self):
        r=self.ready();self.gate.clear();tid=self.approve(r)
        deadline=time.monotonic()+4
        while not self.calls and time.monotonic()<deadline:time.sleep(.01)
        self.service.cancel(r['id'])
        with self.assertRaises(ValueError):self.engine.preview_conversation_deletion([self.cid])
        self.gate.set();self.wait(tid)
        self.assertEqual(self.store.task(tid)['state'],'cancelled')
        self.assertEqual([c[1] for c in self.calls],['analysis'])
        self.assertEqual(self.service.get_task_steps(tid)[1]['state'],'cancelled')

    def test_review_failure_retains_query_and_no_compose(self):
        self.needs_attention=True;r=self.ready();tid=self.approve(r);task=self.wait(tid)
        self.assertEqual(task['state'],'failed');steps=self.service.get_task_steps(tid)
        self.assertIn('query_result',steps[0]['output']);self.assertEqual(steps[2]['state'],'failed')
        self.assertEqual(steps[3]['state'],'blocked');self.assertEqual(len(self.calls),2)

    def test_retry_reuses_only_successful_prefix_and_no_hidden_retry(self):
        self.fail_role='review';r=self.ready();tid=self.approve(r);task=self.wait(tid)
        self.assertEqual(task['state'],'failed');self.assertNotIn('PRIVATE_FAKE_SECRET',task['error'])
        self.assertEqual(len(self.calls),2);self.fail_role=None
        retry=self.service.retry(tid,'one');self.assertEqual(self.wait(retry)['state'],'succeeded')
        self.assertEqual(len(self.query_calls),1);self.assertEqual([c[1] for c in self.calls],['analysis','review','review','compose'])
        self.assertEqual(self.service.retry(tid,'one'),retry)

    def test_schedule_needs_success_and_consent_then_tick_dedup(self):
        r=self.ready()
        with self.assertRaises(ValueError):self.service.schedule(r['id'],r['revision'],'日報','daily','08:00',consent=True)
        tid=self.approve(r);self.wait(tid)
        with self.assertRaises(ValueError):self.service.schedule(r['id'],r['revision'],'日報','daily','08:00')
        sid=self.service.schedule(r['id'],r['revision'],'日報','daily','08:00',consent=True)
        self.assertEqual(self.service.schedule(r['id'],r['revision'],'日報','daily','08:00',consent=True),sid)
        old=self.store.schedule(sid)['next_fire'];manual=self.engine.run_schedule_now(sid,'manual');self.wait(manual)
        self.assertIsNone(self.engine.run_schedule_now(sid,'manual'));self.assertEqual(self.store.schedule(sid)['next_fire'],old)
        now=datetime.fromisoformat(old);self.engine.tick(now)
        runs=self.store.schedule_runs(sid);scheduled=next(x['task_id'] for x in runs if x['scheduled_at']==old)
        self.wait(scheduled);self.engine.tick(now)
        self.assertEqual(len(self.store.schedule_runs(sid)),2);self.assertEqual(len(self.store.notifications()),2)
        self.assertEqual(self.query_calls[-1][1]['to_date'],now.astimezone(timezone(timedelta(hours=8))).date().isoformat())

    def test_failure_pauses_schedule_and_binding_revision_prevents_call(self):
        r=self.ready();self.wait(self.approve(r));sid=self.service.schedule(r['id'],r['revision'],'日報','daily','08:00',consent=True)
        self.needs_attention=True;tid=self.engine.run_schedule_now(sid,'fail');self.wait(tid)
        self.assertFalse(self.store.schedule(sid)['enabled'])
        self.profiles.data['profiles'][2]['revision']+=1
        before=len(self.calls)
        with self.assertRaises(ValueError):self.engine.set_schedule_enabled(sid,True)
        self.assertIsNone(self.engine.run_schedule_now(sid,'invalid'));self.assertEqual(len(self.calls),before)

    def test_source_delete_keeps_independent_results_and_schedule(self):
        r=self.ready();tid=self.approve(r);self.wait(tid)
        sid=self.service.schedule(r['id'],r['revision'],'日報','daily','08:00',consent=True)
        preview=self.engine.preview_conversation_deletion([self.cid]);self.engine.delete_conversations(preview['token'])
        self.assertIsNone(self.service.get(r['id'])['conversation_id']);self.assertEqual(self.store.task(tid)['state'],'succeeded')
        self.assertTrue(self.store.schedule(sid)['enabled'])
        self.wait(self.engine.run_schedule_now(sid,'after-delete'))

    def test_reopen_preserves_no_dispatch(self):
        r=self.ready();tid=self.approve(r);self.wait(tid);before=len(self.calls)
        self.engine.close(wait=True)
        self.engine=Engine(self.store,self.query,None,query_validator=self.queries.validate,query_catalog=self.queries.catalog)
        self.service=WorkflowService(self.engine,self.profiles)
        self.assertEqual(self.service.snapshot(r['id'])['task']['state'],'succeeded');self.assertEqual(len(self.calls),before)

    def test_schema4_migration_backup_and_atomic_failure(self):
        self.engine.close(wait=True)
        with self.store.connection() as db:db.execute('PRAGMA user_version=4')
        with patch('desktop_app.workflows.initialize_workflow_schema',side_effect=ValueError('injected')):
            with self.assertRaises(ValueError):Store(self.path)
        with self.store.connection() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
        migrated=Store(self.path)
        with migrated.connection() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],5)
        self.assertTrue(list(self.path.parent.glob('*.pre-v5-*.bak')))
        self.assertEqual(migrated.conversation(self.cid)['title'],'合成測試')

    def test_invalid_plan_clears_old_ready_steps_and_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):json_object('{"x":1,"x":2}')
        r=self.ready();self.plan_response={'message':'bad','questions':[],'steps':[{'kind':'shell'}]}
        r=self.service.discuss(r['id'],r['revision'],'換個工作');r=self.wait_plan(r['id'])
        self.assertEqual(r['steps'],[]);self.assertFalse(self.service.preview(r['id'],r['revision'])['ready'])
        self.assertEqual(self.query_calls,[])

    def test_numeric_corruption_stops_next_step(self):
        def bad(messages,role,binding,context):return '{"text":"錯誤合計","facts":{"quantity":"999999"}}'
        self.profiles.workflow_call=bad;r=self.ready();task=self.wait(self.approve(r))
        self.assertEqual(task['state'],'failed');self.assertIn('數值',task['error'])
        self.assertEqual(self.service.get_task_steps(task['id'])[2]['state'],'blocked')

    def test_confirmation_transaction_failure_does_not_dispatch(self):
        r=self.ready();self.service.preview(r['id'],r['revision'])
        with self.store.connection() as db:
            db.execute("CREATE TRIGGER fail_workflow BEFORE UPDATE ON workflows WHEN NEW.state='approved' BEGIN SELECT RAISE(ABORT,'injected'); END")
        with self.assertRaises(Exception):self.service.confirm(r['id'],r['revision'],True)
        self.assertFalse(self.store.tasks());self.assertFalse(self.query_calls)
        with self.store.connection() as db:self.assertEqual(db.execute('SELECT count(*) FROM workflow_versions').fetchone()[0],0)

    def test_schedule_cancel_drain_prevents_overlap(self):
        r=self.ready();self.wait(self.approve(r));sid=self.service.schedule(r['id'],r['revision'],'日報','daily','08:00',consent=True)
        self.gate.clear();before=len(self.calls);tid=self.engine.run_schedule_now(sid,'hold')
        deadline=time.monotonic()+4
        while len(self.calls)==before and time.monotonic()<deadline:time.sleep(.01)
        self.engine.cancel_task(tid)
        self.assertIsNone(self.engine.run_schedule_now(sid,'overlap'))
        self.gate.set();self.wait(tid)
        self.assertFalse(self.store.schedule(sid)['enabled'])
        self.assertTrue(any(x['state']=='skipped_overlap' for x in self.store.schedule_runs(sid)))

    def test_restart_interrupted_workflow_pauses_only_active_schedule(self):
        r=self.ready();self.wait(self.approve(r));sid=self.service.schedule(r['id'],r['revision'],'日報','daily','08:00',consent=True)
        self.engine.close(wait=True)
        with self.store.connection() as db:
            task,_=self.service._insert_task(db,self.service._spec(r['id'],r['revision']),'crash',sid)
            db.execute("UPDATE tasks SET state='running' WHERE id=?",(task,))
        self.engine=Engine(self.store,self.query,None,query_validator=self.queries.validate,query_catalog=self.queries.catalog)
        self.service=WorkflowService(self.engine,self.profiles)
        self.assertEqual(self.store.task(task)['state'],'failed');self.assertFalse(self.store.schedule(sid)['enabled'])
        before=len(self.calls);self.assertEqual(len(self.calls),before)

    def test_invalid_output_empty_or_unapproved_tool_stops(self):
        r=self.ready();self.profiles.workflow_call=lambda *args,**kwargs:'{"tool":"shell","command":"echo forbidden"}'
        t=self.wait(self.approve(r));self.assertEqual(t['state'],'failed')
        self.assertEqual(self.service.get_task_steps(t['id'])[2]['state'],'blocked')

    def test_no_numeric_query_works_and_stale_deletion_fails(self):
        steps=self.steps()[1:]
        steps[0]['inputs']=[];steps[1]['inputs']=['s2'];steps[2]['inputs']=['s2','s3']
        r=self.service.create(self.cid,'整理合成文字',self.profiles.workflow_binding('groq-planner'))
        r=self.service.update(r['id'],1,steps)
        deletion=self.engine.preview_conversation_deletion([self.cid]);r=self.service.update(r['id'],r['revision'],steps)
        with self.assertRaises(ValueError):self.engine.delete_conversations(deletion['token'])
        self.assertEqual(self.wait(self.approve(r))['state'],'succeeded');self.assertEqual(self.query_calls,[])

    def test_scheduled_retry_becomes_latest_and_cannot_fork_twice(self):
        r=self.ready();self.wait(self.approve(r));sid=self.service.schedule(r['id'],r['revision'],'日報','daily','08:00',consent=True)
        self.fail_role='review';bad=self.engine.run_schedule_now(sid,'fail');self.wait(bad)
        self.fail_role=None;retry=self.service.retry(bad,'click-one');self.wait(retry)
        self.assertEqual(self.service.snapshot(r['id'])['task']['id'],retry)
        calls=len(self.calls)
        self.assertEqual(self.service.retry(bad,'click-two'),retry)
        self.assertEqual(len(self.calls),calls)
        self.assertFalse(self.store.schedule(sid)['enabled'])

    def test_cross_midnight_retry_keeps_original_query_date(self):
        first=datetime(2026,9,20,2,tzinfo=timezone.utc)
        steps=[self.steps()[0],dict(self.steps()[0],id='s2')]
        original=self.engine.query_runner;query_number=[0]
        def fail_second(q,p):
            query_number[0]+=1
            if query_number[0]==2:raise ValueError('synthetic failure')
            return original(q,p)
        self.engine.query_runner=fail_second
        with patch('desktop_app.core.utcnow',return_value=first),patch('desktop_app.workflows.utcnow',return_value=first):
            r=self.service.create(self.cid,'兩筆合成查詢',self.profiles.workflow_binding('groq-planner'))
            r=self.service.update(r['id'],1,steps);bad=self.approve(r);self.wait(bad)
        first_date=self.query_calls[0][1]['from_date']
        with patch('desktop_app.core.utcnow',return_value=first+timedelta(days=1)),patch('desktop_app.workflows.utcnow',return_value=first+timedelta(days=1)):
            retry=self.service.retry(bad,'tomorrow');self.assertEqual(self.wait(retry)['state'],'succeeded')
        self.assertEqual(len(self.query_calls),2);self.assertEqual(self.query_calls[-1][1]['from_date'],first_date)


if __name__=='__main__':unittest.main()
