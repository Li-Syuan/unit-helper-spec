import copy
import io
import json
import tempfile
import threading
import time
import unittest
from datetime import timedelta
from unittest.mock import patch

from desktop_app.agent_jobs import DEFAULT_LIMITS, decision, limits
from desktop_app.config import DEFAULT
from desktop_app.core import dumps, stamp, utcnow
from desktop_app.skills import TEMPLATE
from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge


class AgentJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.s=WebSession(directory=self.tmp.name,config=copy.deepcopy(DEFAULT),start_scheduler=False)
        self.a=self.s.agents;self.w=self.s.workflows;self.calls=[];self.rounds=0
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def wait(self):
        until=time.monotonic()+10
        while self.s.engine.has_inflight() and time.monotonic()<until:time.sleep(.01)
        self.assertFalse(self.s.engine.has_inflight())
    def ready(self,**kw):
        kw.setdefault('autonomous',False)
        r=self.a.create(kw.pop('profile_id','demo'),'整理指定工作資料',**kw);self.wait()
        r=self.a.state(r['id']);self.assertEqual(r['state'],'ready',r['error']);return r
    def run_job(self,r):
        p=self.a.preview(r['id'],r['revision']);self.assertTrue(p['ready'],p['error'])
        self.a.confirm(r['id'],r['revision'],True);self.wait();return self.a.state(r['id'])
    def company(self):
        from tests.test_search_tools import SEARCH_TOOL
        p=self.s.profiles;p.set_endpoint('https://synthetic.example.test/v1');p.set_wire_mode('assistants')
        pid=p.save('合成工作助理','asst_synthetic');p.set_search_policy(p.snapshot(pid),{'tools':[SEARCH_TOOL]})
        b=p.snapshot(pid)
        with self.s.store.connection() as db:db.execute('INSERT INTO skill_capabilities VALUES(?,?,?,?,?)',(pid,b['revision'],'proof',dumps(['planner','compose','assess','rag']),stamp()))
        return pid
    def responder(self,messages,purpose,binding,context=None):
        self.calls.append((purpose,copy.deepcopy(binding),dict(context),messages))
        sid=context['step_id']
        if sid=='planner':
            steps=[{'id':'search','title':'搜尋','kind':'assistant','role':'rag','profile_id':binding['profile_id'],'instruction':'只查核准的來源與主題','inputs':[]},
                {'id':'compose','title':'整理','kind':'assistant','role':'compose','profile_id':binding['profile_id'],'instruction':'只整理指定成果','inputs':['search']}]
            return dumps({'message':'已規劃','questions':[],'steps':steps})
        if sid.startswith('qa_assess_'):
            return dumps({'decision':'supplement' if sid=='qa_assess_0' else 'complete','step_id':'search' if sid=='qa_assess_0' else '', 'reason':'在原範圍核對' if sid=='qa_assess_0' else '資料足夠'})
        return dumps({'text':'合成資料 https://example.test/source','facts':{}})

    def test_demo_text_approval_no_network_and_skill_save_is_explicit(self):
        with patch('httpx.Client.send',side_effect=AssertionError('network')):
            r=self.ready();self.assertEqual(self.s.orders.list(),[]);self.assertFalse(self.s.store.tasks());self.assertFalse(self.s.skills.list())
            with self.assertRaises(ValueError):self.a.confirm(r['id'],r['revision'],True)
            r=self.run_job(r);self.assertEqual(r['task']['state'],'succeeded',r['task']['error'])
            self.assertEqual(len(r['budget']['requests']),2)
            self.assertEqual(self.a.confirm(r['id'],r['revision'],True)['task']['id'],r['task']['id'])
            self.assertEqual(len(self.s.store.tasks()),1)
            self.assertIn('離線示範',r['task']['result']['report'])
            self.assertIn('draft',self.a.skill_draft(r['id']));self.assertFalse(self.s.skills.list())
            with self.assertRaises(ValueError):self.a.schedule(r['id'],r['revision'],'08:00',reviewed=True,consent=True)
            api=WebBridge(self.s);self.assertTrue(api.call('agent_state',{'id':r['id']})['ok'])

    def test_questions_options_edit_expiry_and_fixed_skill_revision(self):
        d=copy.deepcopy(TEMPLATE);d['fields']=[{'id':'q'+str(i),'text':f'問題{i}','type':'boolean','options':[]} for i in range(4)]
        skill=self.s.skills.save_confirm(self.s.skills.save_preview(d)['token'])
        r=self.a.create('demo','整理',skill_id=skill['id'],skill_revision=1,autonomous=False)
        self.assertEqual(len(r['questions']),3);self.assertFalse(self.s.engine.has_inflight())
        with self.assertRaises(ValueError):self.a.reply(r['id'],r['revision'],answer_values={'q0':'true'})
        r=self.a.reply(r['id'],r['revision'],answer_values={'q'+str(i):False for i in range(3)})
        self.assertEqual([q['id'] for q in r['questions']],['q3'])
        r=self.a.reply(r['id'],r['revision'],answer_values={'q3':True});self.wait();r=self.a.state(r['id'])
        self.assertEqual(r['state'],'ready',r['error'])
        self.a.preview(r['id'],r['revision']);changed=self.a.edit(r['id'],r['revision'],r['steps'],dict(DEFAULT_LIMITS,max_supplements=0))
        with self.assertRaises(ValueError):self.a.confirm(r['id'],r['revision'],True)
        self.a.preview(changed['id'],changed['revision']);self.w.previews[r['workflow_id']]=(changed['revision'],0)
        with self.assertRaises(ValueError):self.a.confirm(changed['id'],changed['revision'],True)
        bad=copy.deepcopy(changed['steps']);bad[0]['id']='qa_escape'
        with self.assertRaises(ValueError):self.a.edit(changed['id'],changed['revision'],bad)
        self.assertFalse(self.s.store.tasks())
        cid=self.w.get(r['workflow_id'])['conversation_id']
        deletion=self.s.engine.preview_conversation_deletion([cid])
        self.s.engine.delete_conversations(deletion['token'])
        with self.s.store.connection() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM work_orders WHERE id=?',(r['id'],)).fetchone())

    def test_selected_second_assistant_receives_only_named_sources_and_revision_is_fixed(self):
        pid=self.company();other=self.s.profiles.save('合成分析','asst_analysis')
        self.s.profiles.set_workflow_capability(other,['analysis'],True,'synthetic-unit-fixture')
        with patch.object(self.s.profiles,'respond',side_effect=self.responder):
            r=self.ready(profile_id=pid,search=True,team_ids=[other])
        steps=copy.deepcopy(r['steps'])
        steps.insert(1,{'id':'analysis','title':'分析指定搜尋','kind':'assistant','role':'analysis',
            'binding':self.s.profiles.workflow_binding(other),'instruction':'只分析指定來源','inputs':['search']})
        steps[-1]['inputs']=['analysis']
        r=self.a.edit(r['id'],r['revision'],steps)
        with patch.object(self.s.profiles,'respond',side_effect=self.responder):r=self.run_job(r)
        self.assertEqual(r['task']['state'],'succeeded',r['task']['error'])
        analysis=next(c for c in self.calls if c[2]['step_id']=='analysis')
        self.assertEqual(analysis[1]['profile_id'],other);self.assertFalse(analysis[2].get('search_authorized'))
        payload=json.loads(analysis[3][0]['content'].split('核准工作與輸入：',1)[1])
        self.assertEqual(set(payload['sources']),{'search'})
        self.s.profiles.save('合成分析','asst_changed',profile_id=other)
        with self.assertRaises(ValueError):self.a.schedule(r['id'],r['revision'],'08:00',reviewed=True,consent=True)

    def test_bounded_search_contexts_and_schedule_consent_fixed_snapshot(self):
        pid=self.company()
        with patch.object(self.s.profiles,'respond',side_effect=self.responder):
            r=self.ready(profile_id=pid,search=True)
            self.assertEqual(len(self.calls),1);self.assertFalse(self.calls[0][2]['search_authorized'])
            r=self.run_job(r);self.assertEqual(r['task']['state'],'succeeded',r['task']['error'])
        execution=self.calls[1:];self.assertEqual([c[2]['step_id'] for c in execution],['search','qa_assess_0','qa_supplement_1','qa_assess_1','compose'])
        self.assertEqual(len(r['budget']['requests']),5)
        self.assertTrue(all(c[1]['profile_id']==pid for c in execution))
        self.assertTrue(all(c[2]['search_authorized']==(c[2]['step_id'] in {'search','qa_supplement_1'}) for c in execution))
        self.assertTrue(all(0<c[2]['request_deadline_seconds']<=600 for c in execution))
        final=json.loads(execution[-1][3][0]['content'].split('核准工作與輸入：',1)[1]);self.assertIn('qa_supplement_1',final['sources'])
        with self.assertRaises(ValueError):self.a.schedule(r['id'],r['revision'],'08:00',consent=True)
        r=self.a.schedule(r['id'],r['revision'],'08:00',frequency='weekly',weekday=4,reviewed=True,consent=True)
        self.assertEqual(r['schedule']['weekday'],4)
        spec=self.w.schedule_spec(r['schedule'],utcnow()+timedelta(days=1))
        self.assertEqual(spec['agent']['limits'],DEFAULT_LIMITS);self.assertIn('occurrence',spec)

    def test_limit_stop_preserves_partial_and_rejects_out_of_scope_decision(self):
        for value in [{'max_supplements':3,'max_requests':12,'timeout_seconds':600},dict(DEFAULT_LIMITS,max_requests=True)]:
            with self.assertRaises(ValueError):limits(value)
        for obj in [{'decision':'supplement','step_id':'shell','reason':'x'}, {'decision':'complete','step_id':'','reason':'x','command':'run'}]:
            with self.assertRaises(ValueError):decision(obj,['search'])
        pid=self.company()
        with patch.object(self.s.profiles,'respond',side_effect=self.responder):
            r=self.ready(profile_id=pid,search=True,limits_value=dict(DEFAULT_LIMITS,max_supplements=0));r=self.run_job(r)
        self.assertEqual(r['task']['state'],'failed');self.assertIn('AGENT_SUPPLEMENT_LIMIT',r['task']['error'])
        self.assertTrue(any(s['output'] and s['output'].get('text') for s in r['steps_status']))
        self.assertNotIn('compose',[c[2]['step_id'] for c in self.calls])
        with self.assertRaises(ValueError):self.w.retry(r['task']['id'],'new')
        with self.assertRaises(ValueError):self.a.schedule(r['id'],r['revision'],'08:00',reviewed=True,consent=True)

    def test_budget_persists_before_dispatch_and_expired_resume_never_calls(self):
        pid=self.company()
        with patch.object(self.s.profiles,'respond',side_effect=self.responder):r=self.ready(profile_id=pid,search=True)
        self.a.preview(r['id'],r['revision'])
        with patch.object(self.s.engine,'_submit'):
            tid=self.a.confirm(r['id'],r['revision'],True)['task']['id']
        task=self.s.store.task(tid);payload=task['payload'];payload['agent_budget']={'started_at':stamp(utcnow()-timedelta(seconds=700)), 'deadline':stamp(utcnow()-timedelta(seconds=100)), 'requests':['search']}
        with self.s.store.connection() as db:db.execute('UPDATE tasks SET payload=? WHERE id=?',(dumps(payload),tid))
        before=len(self.calls)
        with patch.object(self.s.profiles,'respond',side_effect=self.responder):self.w.work(tid)
        task=self.s.store.task(tid);self.assertEqual(len(self.calls),before);self.assertIn('AGENT_TIME_LIMIT',task['error']);self.assertEqual(task['payload']['agent_budget'],payload['agent_budget'])

    def test_unknown_planner_not_reposted_and_cancelled_late_result_ignored(self):
        pid=self.company()
        with patch.object(self.s.profiles,'respond',side_effect=RuntimeError('unknown')) as network:
            r=self.a.create(pid,'搜尋指定來源',search=True,autonomous=False);self.wait();r=self.a.state(r['id'])
            with self.assertRaises(ValueError):self.a.reply(r['id'],r['revision'],'再試一次')
            self.assertEqual(network.call_count,1)
        gate=threading.Event();entered=threading.Event()
        def slow(*a,**k):entered.set();gate.wait(5);return self.responder(*a,**k)
        with patch.object(self.s.profiles,'respond',side_effect=slow):
            r=self.a.create(pid,'另一項搜尋',search=True,autonomous=False);self.assertTrue(entered.wait(3));self.a.cancel(r['id']);gate.set();self.wait()
        self.assertEqual(self.a.state(r['id'])['state'],'cancelled');self.assertFalse(self.s.store.tasks())

    def test_probe_explicit_max_three_no_tools_and_failure_revokes_role(self):
        pid=self.company();self.calls=[]
        def respond(messages,purpose,binding,context=None):
            self.calls.append(context)
            text=messages[0]['content']
            return text.split('請只回覆 ',1)[1] if '請只回覆 ' in text else text.split('僅回覆 ',1)[1]
        with self.assertRaises(ValueError):self.a.probe(pid)
        with patch.object(self.s.profiles,'respond',side_effect=respond):r=self.a.probe(pid,True)
        self.assertEqual(len(self.calls),3);self.assertTrue(all(not c['search_authorized'] for c in self.calls))
        self.assertEqual([c['status'] for c in r['checks']],['passed']*3)
        with patch.object(self.s.profiles,'respond',return_value='not JSON') as net:r=self.a.probe(pid,True)
        self.assertEqual(net.call_count,1);self.assertNotIn('assess',r['roles']);self.assertNotIn('planner',r['roles'])
        with self.assertRaises(ValueError):self.a.create(pid,'整理')

    def test_checkpoint_resume_reuses_receipts_and_budget_then_cleanup(self):
        from desktop_app.graph_runner import execute
        pid=self.company()
        with patch.object(self.s.profiles,'respond',side_effect=self.responder):r=self.ready(profile_id=pid,search=True)
        def interrupt(path,tid,steps,dispatch,receipts=None):
            dispatch(steps[0]);raise OSError('synthetic checkpoint failure')
        with patch.object(self.s.profiles,'respond',side_effect=self.responder),patch('desktop_app.graph_runner.execute',side_effect=interrupt):
            r=self.run_job(r)
        self.assertIn('WORKFLOW_RECOVERY_REQUIRED',r['task']['error']);before=r['budget']['deadline']
        with patch.object(self.s.profiles,'respond',side_effect=self.responder):
            self.a.recover(r['id']);self.wait();r=self.a.state(r['id'])
        self.assertEqual(r['task']['state'],'succeeded',r['task']['error']);self.assertEqual(r['budget']['deadline'],before)
        self.assertEqual([c[2]['step_id'] for c in self.calls].count('search'),1)
        self.assertEqual(len(r['budget']['requests']),5)
        task=r['task'];task_row=dict(task,payload=dumps(task['payload']))
        keys,_=self.s.cleanup._cache_targets([task_row],'tasks');self.assertEqual(len(keys),7)
        p=self.s.cleanup.preview('tasks',[task['id']]);self.s.cleanup.confirm(p['token'])
        self.assertIsNone(self.a.state(r['id'])['task'])
        p=self.s.cleanup.preview('workflows',[r['workflow_id']]);self.s.cleanup.confirm(p['token']);self.assertFalse(self.a.list())
        with self.s.store.connection() as db:self.assertEqual(db.execute("SELECT count(*) FROM work_orders WHERE json_extract(data,'$.kind')='agent-v1'").fetchone()[0],0)

    def test_request_budget_and_needs_input_never_finish_or_schedule(self):
        pid=self.company()
        for mode,code in [('budget','AGENT_REQUEST_LIMIT'),('input','AGENT_NEEDS_INPUT')]:
            def respond(*a,**kw):
                if mode=='input' and kw['context']['step_id']=='qa_assess_0':return dumps({'decision':'needs_input','step_id':'','reason':'資料期間不明'})
                return self.responder(*a,**kw)
            with patch.object(self.s.profiles,'respond',side_effect=respond):
                r=self.ready(profile_id=pid,search=True,limits_value=dict(DEFAULT_LIMITS,max_requests=3));r=self.run_job(r)
            self.assertEqual(r['task']['state'],'failed');self.assertIn(code,r['task']['error'])
            self.assertLessEqual(len(r['budget']['requests']),3)

    def test_cancel_running_late_output_and_reopen_never_replay(self):
        pid=self.company();gate=threading.Event();entered=threading.Event()
        with patch.object(self.s.profiles,'respond',side_effect=self.responder):r=self.ready(profile_id=pid,search=True)
        def slow(*a,**kw):entered.set();gate.wait(5);return self.responder(*a,**kw)
        with patch.object(self.s.profiles,'respond',side_effect=slow):
            self.a.preview(r['id'],r['revision']);self.a.confirm(r['id'],r['revision'],True)
            self.assertTrue(entered.wait(3))
            from desktop_app.authentication import AuthenticationError
            with patch.object(self.s,'assert_identity',side_effect=AuthenticationError('expired')):
                cancelled=WebBridge(self.s).call('agent_cancel',{'id':r['id']})
            self.assertEqual(cancelled['data'],{'cancelled':True,'identity_expired':True})
            gate.set();self.wait()
        r=self.a.state(r['id']);self.assertEqual(r['task']['state'],'cancelled')
        self.assertFalse(any(s['state']=='succeeded' for s in r['steps_status']))
        self.s.close()
        with patch('httpx.Client.send',side_effect=AssertionError('network')):
            self.s=WebSession(directory=self.tmp.name,config=copy.deepcopy(DEFAULT),start_scheduler=False);self.a=self.s.agents
            self.assertEqual(self.a.state(r['id'])['task']['state'],'cancelled');self.assertFalse(self.s.engine.has_inflight())

    def test_cli_uses_same_service_and_pipe_cannot_approve(self):
        from desktop_app.cli import Workbench,execute_line
        w=Workbench(self.s);out=io.StringIO()
        execute_line(w,'/job demo 整理測試文字',io.StringIO(),out);self.wait()
        execute_line(w,'/job-preview',io.StringIO(),out)
        with self.assertRaises(ValueError):execute_line(w,'/job-run',io.StringIO('確認執行\n'),out)
        self.assertFalse(self.s.store.tasks());self.assertIsNone(self.s.scheduler)
