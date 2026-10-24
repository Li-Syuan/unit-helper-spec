import copy
import io
import json
import tempfile
import threading
import time
import unittest
from datetime import timedelta
from unittest.mock import patch

from desktop_app.autonomous import DEFAULT_LIMITS,validate_decision
from desktop_app.config import DEFAULT
from desktop_app.core import dumps,stamp,utcnow
from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge


class AutonomousTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.s=WebSession(directory=self.tmp.name,config=copy.deepcopy(DEFAULT),start_scheduler=False)
        self.a=self.s.agents;self.w=self.s.workflows;self.calls=[]
    def tearDown(self):
        self.s.close();self.tmp.cleanup()
    def wait(self):
        until=time.monotonic()+10
        while self.s.engine.has_inflight() and time.monotonic()<until:time.sleep(.01)
        self.assertFalse(self.s.engine.has_inflight())
    def profile(self,autonomy=True):
        from tests.test_search_tools import SEARCH_TOOL
        p=self.s.profiles;p.set_endpoint('https://synthetic.example.test/v1');p.set_wire_mode('assistants')
        pid=p.save('合成主助理','asst_test');p.set_search_policy(p.snapshot(pid),{'tools':[SEARCH_TOOL]})
        b=p.snapshot(pid)
        roles=['planner','compose','assess','rag']+(['autonomous'] if autonomy else [])
        with self.s.store.connection() as db:db.execute('INSERT INTO skill_capabilities VALUES(?,?,?,?,?)',(pid,b['revision'],'proof',dumps(roles),stamp()))
        return pid
    def ready(self,pid='demo',**kwargs):
        r=self.a.create(pid,'核對今天台股與美股的合成資料',**kwargs);self.wait();r=self.a.state(r['id'])
        self.assertEqual(r['state'],'ready',r['error']);return r
    def execute(self,r):
        self.assertTrue(self.a.preview(r['id'],r['revision'])['ready'])
        r=self.a.confirm(r['id'],r['revision'],True);self.wait();return self.a.state(r['id'])
    def choice(self,action,pid,refs=(),instruction='整理來源',role=None):
        return {'action':action,'profile_id':pid if action!='ask' else '',
            'role':role or {'search':'rag','compose':'compose','delegate':'analysis','ask':''}[action],
            'instruction':instruction,'inputs':list(refs),'reason':'根據已取得來源決定下一步'}
    def responder(self,messages,purpose,binding,context=None):
        self.calls.append((copy.deepcopy(messages),purpose,copy.deepcopy(binding),dict(context)))
        sid=context['step_id'];pid=binding['profile_id']
        if sid=='planner':
            return dumps({'message':'合成建議','questions':[],'steps':[
                {'id':'search','title':'搜尋','kind':'assistant','role':'rag','profile_id':pid,'instruction':'今天核准來源','inputs':[]},
                {'id':'compose','title':'整理','kind':'assistant','role':'compose','profile_id':pid,'instruction':'整理來源','inputs':['search']}]})
        if sid.startswith('qa_decide_'):
            data=json.loads(messages[0]['content'].split('\n工作資料：',1)[1]);sources=data['sources']
            if not sources:return dumps(self.choice('search',pid,instruction='查今天台股'))
            if any('舊日期' in s['text'] for s in sources.values()) and len(sources)==1:
                return dumps(self.choice('search',pid,sources,'改用當日日期查台股'))
            return dumps(self.choice('compose',pid,sources))
        return dumps({'text':('舊日期，需重新核對 ' if sid=='qa_action_1' else '當日資料 ')+'https://example.test/news','facts':{}})
    def synthetic(self):
        return patch.object(self.s.profiles,'respond',side_effect=self.responder)

    def test_default_autonomy_demo_approval_and_cli_parity(self):
        with patch('httpx.Client.send',side_effect=AssertionError('network')):
            r=self.ready();self.assertTrue(r['autonomous']);self.assertEqual(r['limits'],DEFAULT_LIMITS)
            self.assertFalse(self.s.store.tasks())
            with self.assertRaises(ValueError):self.a.confirm(r['id'],r['revision'],True)
            p=self.a.preview(r['id'],r['revision']);self.assertIn('authority',p)
            r=self.execute(r);self.assertEqual(r['task']['state'],'succeeded',r['task']['error'])
            from desktop_app.workflow_presenter import step_rows
            self.assertEqual([v['id'] for v in step_rows(r,lambda b:b['profile_id'])],['qa_decide_1','qa_action_1'])
            self.assertEqual(len(r['budget']['requests']),2);self.assertEqual(len(r['budget']['actions']),1)
            self.assertEqual(self.a.confirm(r['id'],r['revision'],True)['task']['id'],r['task']['id'])
            self.assertIn('離線示範',r['task']['result']['report'])
            from desktop_app.cli import Workbench,execute_line
            w=Workbench(self.s);w.job=r['id'];out=io.StringIO()
            execute_line(w,'/job-preview',io.StringIO(),out)
            self.assertIn('autonomous',out.getvalue())
            with self.assertRaises(ValueError):self.a.schedule(r['id'],r['revision'],'08:00',reviewed=True,consent=True)

    def test_decisions_change_with_observation_not_preexpanded_plan(self):
        pid=self.profile()
        with self.synthetic(),patch('desktop_app.autonomous.search_receipt',return_value=True):
            r=self.ready(pid,search=True);self.assertEqual(len(self.calls),1)
            r=self.execute(r)
        self.assertEqual(r['task']['state'],'succeeded',r['task']['error'])
        decisions=[s['output']['decision'] for s in r['steps_status'] if s['step_id'].startswith('qa_decide_')]
        self.assertEqual([d['action'] for d in decisions],['search','search','compose'])
        self.assertNotEqual(decisions[0]['instruction'],decisions[1]['instruction'])
        self.assertEqual(len(r['budget']['requests']),6);self.assertEqual(len(r['budget']['actions']),3)
        self.assertTrue(all(not c[3].get('search_authorized') for c in self.calls if c[3]['step_id'].startswith('qa_decide_')))
        self.assertEqual(len({c[3]['step_id'] for c in self.calls}),7)
        self.assertTrue(all(c[1]=='workflow_plan' for c in self.calls if c[3]['step_id'].startswith('qa_decide_')))

    def test_team_selected_input_only_and_versions_before_each_action(self):
        pid=self.profile();other=self.s.profiles.save('合成分析','asst_other')
        self.s.profiles.set_workflow_capability(other,['analysis'],True,'synthetic-fixture')
        def answer(messages,purpose,binding,context=None):
            sid=context['step_id']
            if sid=='qa_decide_2':
                self.calls.append((messages,purpose,binding,context))
                return dumps(self.choice('delegate',other,['qa_action_1'],'分析第一份來源'))
            if sid=='qa_decide_3':
                self.calls.append((messages,purpose,binding,context))
                return dumps(self.choice('compose',pid,['qa_action_1','qa_action_2']))
            return self.responder(messages,purpose,binding,context)
        with patch.object(self.s.profiles,'respond',side_effect=answer),patch('desktop_app.autonomous.search_receipt',return_value=True):
            r=self.ready(pid,search=True,team_ids=[other]);r=self.execute(r)
        self.assertEqual(r['task']['state'],'succeeded',r['task']['error'])
        delegated=next(c for c in self.calls if c[3]['step_id']=='qa_action_2')
        self.assertEqual(delegated[2]['profile_id'],other)
        inputs=json.loads(delegated[0][0]['content'].split('核准工作與輸入：',1)[1])
        self.assertEqual(set(inputs['sources']),{'qa_action_1'});self.assertFalse(delegated[3].get('search_authorized'))
        self.s.profiles.save('changed','asst_new',profile_id=other)
        with self.assertRaises(ValueError):self.a.schedule(r['id'],r['revision'],'08:00',reviewed=True,consent=True)

    def test_untrusted_decisions_and_no_progress_stop_without_hidden_retry(self):
        pid=self.profile()
        with self.synthetic():r=self.ready(pid,search=True)
        spec={'planner':self.w.get(r['workflow_id'])['planner'],'agent':r['authority']}
        valid=self.choice('search',pid)
        for bad in [dict(valid,action='shell'),dict(valid,command='whoami'),dict(valid,profile_id='unknown'),dict(valid,inputs=['other_thread']),dict(valid,role='analysis')]:
            with self.assertRaises(ValueError):validate_decision(bad,spec,{})
        def answer(messages,purpose,binding,context=None):
            if context['step_id'].startswith('qa_decide_'):
                return dumps(self.choice('search',pid,instruction='同一條查詢'))
            return self.responder(messages,purpose,binding,context)
        with patch.object(self.s.profiles,'respond',side_effect=answer),patch('desktop_app.autonomous.search_receipt',return_value=True):r=self.execute(r)
        self.assertIn('AGENT_NO_PROGRESS',r['task']['error']);self.assertEqual(len(r['budget']['actions']),1)
        self.assertTrue(any(s['output'] for s in r['steps_status']))
        with self.assertRaises(ValueError):self.w.retry(r['task']['id'],'another-request')
        with self.synthetic():new=self.ready(pid,search=True,prior_task_id=r['task']['id'])
        self.assertEqual(new['prior_task_id'],r['task']['id']);self.assertFalse(new['memory_snapshot']);self.assertIsNone(new['task'])
        self.assertNotIn('舊日期',dumps(new['authority']))

    def test_budget_actions_time_and_tool_continuations_do_not_reset(self):
        pid=self.profile()
        for key,value,code in [('max_actions',1,'ACTION_LIMIT'),('max_requests',2,'REQUEST_LIMIT')]:
            with self.subTest(key=key),self.synthetic(),patch('desktop_app.autonomous.search_receipt',return_value=True):
                r=self.ready(pid,search=True,limits_value=dict(DEFAULT_LIMITS,**{key:value}));r=self.execute(r)
            self.assertIn('AGENT_'+code,r['task']['error']);self.assertEqual(len(r['budget']['actions']),1)
        with self.synthetic():r=self.ready(pid,search=True)
        self.a.preview(r['id'],r['revision'])
        with patch.object(self.s.engine,'_submit'):tid=self.a.confirm(r['id'],r['revision'],True)['task']['id']
        payload=self.s.store.task(tid)['payload'];payload['agent_budget']={'requests':[],'deadline':stamp(utcnow()-timedelta(seconds=1))}
        with self.s.store.connection() as db:db.execute('UPDATE tasks SET payload=? WHERE id=?',(dumps(payload),tid))
        with patch.object(self.s.profiles,'respond') as network:self.w.work(tid)
        network.assert_not_called();self.assertIn('AGENT_TIME_LIMIT',self.s.store.task(tid)['error'])
        def tool_rounds(messages,purpose,binding,context=None):
            if context['step_id']=='qa_action_1':
                context['reserve_tool_round']('batch1');context['reserve_tool_round']('batch1')
            return self.responder(messages,purpose,binding,context)
        with patch.object(self.s.profiles,'respond',side_effect=tool_rounds),patch('desktop_app.autonomous.search_receipt',return_value=True):
            r=self.execute(self.ready(pid,search=True))
        self.assertEqual(r['task']['state'],'succeeded',r['task']['error'])
        self.assertEqual(len(r['budget']['requests']),7)

    def test_missing_sources_ask_and_forged_citations_do_not_finish(self):
        pid=self.profile()
        for stage in ['ask','no_receipt','no_source','forged']:
            def answer(messages,purpose,binding,context=None):
                sid=context['step_id']
                if stage=='ask' and sid.startswith('qa_decide_'):return dumps(self.choice('ask',pid,instruction='請補充日期'))
                if stage=='no_source' and sid.startswith('qa_action_'):return dumps({'text':'沒有任何來源','facts':{}})
                if stage=='forged' and sid=='qa_action_3':return dumps({'text':'https://invented.example.test','facts':{}})
                return self.responder(messages,purpose,binding,context)
            with self.subTest(stage=stage),patch.object(self.s.profiles,'respond',side_effect=answer),patch('desktop_app.autonomous.search_receipt',return_value=stage!='no_receipt'):
                r=self.ready(pid,search=True);r=self.execute(r)
            self.assertEqual(r['task']['state'],'failed');self.assertIn('AGENT_NEEDS_INPUT',r['task']['error'])
            with self.assertRaises(ValueError):self.a.schedule(r['id'],r['revision'],'08:00',reviewed=True,consent=True)

    def test_cancel_and_expiry_block_late_results(self):
        pid=self.profile();gate=threading.Event();entered=threading.Event()
        def answer(messages,purpose,binding,context=None):
            if context['step_id']=='qa_decide_1':entered.set();gate.wait(5)
            return self.responder(messages,purpose,binding,context)
        with patch.object(self.s.profiles,'respond',side_effect=answer):
            r=self.ready(pid,search=True);self.a.preview(r['id'],r['revision']);self.a.confirm(r['id'],r['revision'],True)
            self.assertTrue(entered.wait(3));self.a.cancel(r['id']);gate.set();self.wait()
        r=self.a.state(r['id']);self.assertEqual(r['task']['state'],'cancelled')
        self.assertFalse(any(s['state']=='succeeded' for s in r['steps_status']))
        before=len(self.calls);self.s.close()
        self.s=WebSession(directory=self.tmp.name,config=copy.deepcopy(DEFAULT),start_scheduler=False)
        self.assertEqual(len(self.calls),before);self.assertEqual(self.s.store.task(r['task']['id'])['state'],'cancelled')
        self.a=self.s.agents;self.w=self.s.workflows
        from desktop_app.authentication import AuthenticationError
        def expiry(messages,purpose,binding,context=None):
            if context['step_id']=='qa_decide_1':
                self.s.engine.authorization=lambda:(_ for _ in ()).throw(AuthenticationError('登入已到期'))
            return self.responder(messages,purpose,binding,context)
        with patch.object(self.s.profiles,'respond',side_effect=expiry):
            r=self.ready(pid,search=True);self.a.preview(r['id'],r['revision']);r=self.a.confirm(r['id'],r['revision'],True);self.wait()
        task=self.s.store.task(r['task']['id']);self.assertEqual(task['state'],'failed')
        self.assertFalse(any(s['step_id'].startswith('qa_action_') for s in self.w.get_task_steps(task['id'])))

    def test_checkpoint_resume_reuses_decisions_and_action_receipts(self):
        import desktop_app.graph_runner as graph
        pid=self.profile();original=graph.execute_autonomous
        def interrupted(path,tid,spec,runner):
            real_act=runner.act
            def act(index):
                done=real_act(index)
                if index==0:raise OSError('simulated crash after receipt')
                return done
            runner.act=act
            return original(path,tid,spec,runner)
        with self.synthetic(),patch('desktop_app.autonomous.search_receipt',return_value=True):
            r=self.ready(pid,search=True)
            with patch.object(graph,'execute_autonomous',side_effect=interrupted):r=self.execute(r)
            self.assertIn('WORKFLOW_RECOVERY_REQUIRED',r['task']['error'])
            self.assertTrue(self.w.recovery(r['task']['id'])['eligible'])
            self.w.resume(r['task']['id']);self.wait();r=self.a.state(r['id'])
        self.assertEqual(r['task']['state'],'succeeded',r['task']['error'])
        ids=[c[3]['step_id'] for c in self.calls]
        self.assertEqual(ids.count('qa_action_1'),1);self.assertEqual(ids.count('qa_decide_1'),1)
        self.assertEqual(len(r['budget']['requests']),6)
        original_deadline=r['budget']['deadline']
        self.assertTrue(original_deadline)
        # Checkpoint loss/lag must not feed later results back into cached decisions.
        graph.remove(self.s.store.path.with_name('workflow-checkpoints.sqlite3'),r['task']['id'])
        with self.s.store.connection() as db:db.execute("UPDATE tasks SET state='queued' WHERE id=?",(r['task']['id'],))
        with patch.object(self.s.profiles,'respond',side_effect=AssertionError('cached work replayed')) as network:
            self.w.work(r['task']['id'])
        network.assert_not_called();self.assertEqual(self.s.store.task(r['task']['id'])['state'],'succeeded')
        deletion=self.s.cleanup.preview('tasks',[r['task']['id']]);self.s.cleanup.confirm(deletion['token'])
        with self.assertRaises(ValueError):self.s.store.task(r['task']['id'])
        # A known run may resume along its original decision ID; an unknown POST cannot.
        def fail_known(messages,purpose,binding,context=None):
            if context['step_id']=='qa_decide_1':raise RuntimeError('synthetic known-run timeout')
            return self.responder(messages,purpose,binding,context)
        with patch.object(self.s.profiles,'respond',side_effect=fail_known):second=self.execute(self.ready(pid,search=True))
        deadline=second['budget']['deadline']
        with patch.object(self.s.profiles,'inspect_request',return_value={'recoverable':True,'state':'polling'}),self.synthetic(),patch('desktop_app.autonomous.search_receipt',return_value=True):
            self.w.resume(second['task']['id']);self.wait();second=self.a.state(second['id'])
        self.assertEqual(second['task']['state'],'succeeded',second['task']['error'])
        self.assertEqual(second['budget']['deadline'],deadline);self.assertEqual(len(second['budget']['requests']),6)

    def test_probe_separate_explicit_and_failure_revokes_autonomy(self):
        pid=self.profile(autonomy=False)
        with self.assertRaises(ValueError):self.a.create(pid,'整理文字')
        with self.assertRaises(ValueError):self.a.autonomy_probe(pid)
        calls=[]
        def answer(messages,purpose,binding,context=None):
            calls.append((purpose,context));sid=context['step_id']
            return dumps(self.choice('ask' if sid=='decision_3' else 'compose',pid,['qa_action_1'] if sid=='decision_2' else []))
        with patch.object(self.s.profiles,'respond',side_effect=answer):result=self.a.autonomy_probe(pid,True)
        self.assertTrue(result['passed']);self.assertEqual(len(calls),3)
        self.assertTrue(all(p=='workflow_plan' and not c.get('search_authorized') for p,c in calls))
        self.assertTrue(next(x for x in self.a.catalog()['assistants'] if x['id']==pid)['autonomous_ready'])
        with patch.object(self.s.profiles,'respond',return_value='{"command":"shell"}') as network:result=self.a.autonomy_probe(pid,True)
        self.assertFalse(result['passed']);self.assertEqual(network.call_count,1)
        self.assertNotIn('autonomous',self.s.skills.proof(pid,self.s.profiles.snapshot(pid)['revision'])['roles'])

    def test_schedule_snapshot_date_old_mode_and_unknown_do_not_restart(self):
        pid=self.profile()
        with self.synthetic(),patch('desktop_app.autonomous.search_receipt',return_value=True):r=self.execute(self.ready(pid,search=True))
        with self.assertRaises(ValueError):self.a.schedule(r['id'],r['revision'],'08:00',consent=True)
        r=self.a.schedule(r['id'],r['revision'],'08:00',frequency='weekly',weekday=1,reviewed=True,consent=True)
        spec=self.w.schedule_spec(r['schedule'],utcnow()+timedelta(days=1))
        self.assertEqual(spec['agent']['version'],2);self.assertEqual(spec['agent']['limits'],DEFAULT_LIMITS);self.assertIn('occurrence',spec)
        with self.synthetic():old=self.ready(pid,search=True,autonomous=False)
        self.assertFalse(old['autonomous']);self.assertEqual(old['authority']['version'],1)
        with self.synthetic():bad=self.ready(pid,search=True)
        with patch.object(self.s.profiles,'respond',side_effect=RuntimeError('unknown post')):bad=self.execute(bad)
        with self.assertRaises(ValueError):self.a.create(pid,'重試',prior_task_id=bad['task']['id'])
        with patch.object(self.s.profiles,'inspect_request',return_value={'recoverable':False}):
            with self.assertRaises(ValueError):self.w.resume(bad['task']['id'])
