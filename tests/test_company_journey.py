"""Real SDK + real LangGraph + synthetic company HTTP. Never company acceptance."""
import json
import tempfile
import time
import unittest
from unittest.mock import Mock
import httpx
from openai import OpenAI
from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge
from desktop_app.assistants_gateway import AssistantsGateway
from test_support.assistants_mock import AssistantsMock


class CompanyJourneyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=WebSession(directory=self.tmp.name)
        self.p=self.s.profiles;self.p.set_endpoint('https://fixture.example.test/v1');self.p.set_wire_mode('assistants')
        self.ids={role:self.p.save(role,'asst_'+role) for role in ('planner','analysis','review','compose')}
        for role,pid in self.ids.items():self.p.set_workflow_capability(pid,[role],True,'synthetic test only')
        self.p.key=Mock(return_value='synthetic-test-key')
        self.mock=AssistantsMock();self.reply='【協定模擬】合成文字'
        def factory(d,p,key,binding):
            sdk=OpenAI(base_url='https://fixture.example.test/v1',api_key=key,max_retries=0,
                       http_client=httpx.Client(transport=httpx.MockTransport(self.mock.handle)))
            self.mock.reply=self.reply
            if getattr(self,'workflow_reply',False):
                role=p['name']
                if role=='planner':
                    steps=[]
                    for i,role_name in enumerate(('analysis','review','compose')):
                        steps.append({'id':'s'+str(i),'title':role_name,'kind':'assistant','role':role_name,
                                      'profile_id':self.ids[role_name],'instruction':'整理合成筆記',
                                      'inputs':['s'+str(i-1)] if i else []})
                    self.mock.reply=json.dumps({'message':'建議三步','questions':[],'steps':steps})
                else:
                    value={'text':'合成成果 '+role,'facts':{}}
                    if role=='review':value['verdict']='pass'
                    self.mock.reply=json.dumps(value)
            return AssistantsGateway({'base_url':d['endpoint'],'assistant_id':p['assistant_id']},key,
                self.s.directory/'assistant-sessions.sqlite3',binding,client=sdk)
        self.p._assistants_client=factory;self.api=WebBridge(self.s)
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def call(self,name,**kw):
        result=self.api.call(name,kw);self.assertTrue(result['ok'],result);return result['data']
    def wait(self):
        end=time.monotonic()+8
        while self.s.engine.has_inflight() and time.monotonic()<end:time.sleep(.01)
        self.assertFalse(self.s.engine.has_inflight())
    def selection(self,role='analysis'):
        p=self.p.snapshot(self.ids[role]);return f"company:{p['profile_id']}:{p['revision']}"

    def test_main_chat_true_provider_multiturn_and_switch(self):
        tid=self.call('dialogue_start',assistant_id=self.selection())['id']
        self.call('dialogue_send',id=tid,text='合成一',request_id='turn1')
        state=self.call('dialogue_send',id=tid,text='追問',request_id='turn2')
        self.assertTrue(state['company']);self.assertEqual(len(state['messages']),4)
        self.assertEqual(len(self.mock.threads),1)
        self.assertEqual(sum(m=='POST' and p.endswith('/messages') for m,p,b in self.mock.requests),2)
        other=self.call('dialogue_start',assistant_id=self.selection('compose'))
        self.call('dialogue_send',id=other['id'],text='獨立問題',request_id='turn3')
        self.assertEqual(len(self.mock.threads),2)

    def test_task_suggestions_isolated_and_only_confirm_saves(self):
        tid=self.call('dialogue_start',mode='task',assistant_id=self.selection())['id']
        self.reply=json.dumps({'text':'請補來源','answers':{'target':'合成目標'}})
        self.call('dialogue_send',id=tid,text='建立草稿',request_id='t1')
        values={'target':'合成目標','source':'人工文字','task_type':'摘要整理',
                'schedule':{'frequency':'daily','time_hhmm':'08:00','weekday':None,'date':None}}
        self.reply=json.dumps({'text':'草稿完成','answers':values})
        state=self.call('dialogue_send',id=tid,text='每天08:00',request_id='t2')
        self.assertEqual(len(self.mock.threads),2)
        self.assertEqual(self.s.dialogue.list_saved(),[])
        p=self.call('dialogue_preview',id=tid,revision=state['revision'])
        saved=self.call('dialogue_confirm',id=tid,token=p['token']);self.assertFalse(saved['enabled'])
        self.assertFalse(self.s.store.tasks());self.assertFalse(self.s.store.schedules())

    def test_plan_confirm_and_graph_multiple_real_sdk_ids(self):
        self.workflow_reply=True
        cid=self.s.store.create_conversation('合成旅程',self.p.snapshot(self.ids['planner']))
        service=self.s.workflows;r=service.create(cid,'整理合成筆記',self.p.workflow_binding(self.ids['planner']))
        service.discuss(r['id'],r['revision'],'請分析覆核後彙整');self.wait()
        r=service.get(r['id']);self.assertEqual(r['state'],'ready')
        self.assertFalse(self.s.store.tasks());self.assertEqual(len(self.mock.runs),1)
        self.assertTrue(service.preview(r['id'],r['revision'])['ready'])
        tid=service.confirm(r['id'],r['revision'],True);self.wait()
        task=self.s.store.task(tid);self.assertEqual(task['state'],'succeeded',task['error'])
        self.assertEqual(len(self.mock.runs),4)
        self.assertEqual(len(self.mock.threads),4)
        self.assertEqual({v['run']['assistant_id'] for v in self.mock.runs.values()}, {'asst_'+r for r in self.ids})
        self.assertEqual(service.confirm(r['id'],r['revision'],True),tid)
        self.assertEqual(len(self.mock.runs),4)

    def test_engine_chat_deletion_removes_extra_local_cache(self):
        from desktop_app.assistant_sessions import AssistantSessions
        cid=self.s.store.create_conversation('待刪除',self.p.snapshot(self.ids['analysis']))
        tid=self.s.engine.run_chat(cid,'合成文字')
        self.wait();self.assertEqual(self.s.store.task(tid)['state'],'succeeded')
        ledger=AssistantSessions(self.s.directory/'assistant-sessions.sqlite3')
        with ledger.connect() as db:self.assertGreater(db.execute('SELECT count(*) FROM requests').fetchone()[0],0)
        preview=self.s.engine.preview_conversation_deletion([cid])
        self.s.engine.delete_conversations(preview['token'])
        with ledger.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM requests').fetchone()[0],0)
