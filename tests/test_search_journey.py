"""Actual services, SDK and graph; synthetic HTTP only, not company acceptance."""
import json
from tests import test_company_journey as journey
from desktop_app.assistants_gateway import AssistantsGateway
from test_support.search_mock import SearchMock
import httpx
from openai import OpenAI


class SearchJourneyTests(journey.CompanyJourneyTests):
    # Re-run the existing four journeys with an assistant declaring a search tool.
    def setUp(self):
        super().setUp();self.mock=SearchMock()
        def factory(d,p,key,binding):
            sdk=OpenAI(base_url=d['endpoint'],api_key=key,max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(self.mock.handle)))
            self.mock.reply=self.reply
            if getattr(self,'workflow_reply',False):
                role=p['name']
                if role=='planner':
                    roles=('rag','analysis','review','compose') if getattr(self,'with_search',False) else ('analysis','review','compose')
                    steps=[{'id':'s'+str(i),'title':r,'kind':'assistant','role':r,'profile_id':self.ids[r],
                        'instruction':'核對合成來源','inputs':['s'+str(i-1)] if i else []} for i,r in enumerate(roles)]
                    self.mock.reply=json.dumps({'message':'合成分工','questions':[],'steps':steps})
                else:
                    result={'text':'合成成果 '+role,'facts':{}}
                    if role=='review':result['verdict']='pass'
                    self.mock.reply=json.dumps(result)
            return AssistantsGateway({'base_url':d['endpoint'],'assistant_id':p['assistant_id'],
                'search_policy':p.get('search_policy')},key,self.s.directory/'assistant-sessions.sqlite3',binding,client=sdk)
        self.p._assistants_client=factory

    def approve(self,pid):
        result=self.call('company_probe',profile_id=pid)
        self.assertEqual(result['search'],'not_tested')
        self.assertFalse(self.mock.plugin_requests)
        return self.call('search_policy_save',token=result['policy_token'],names=['internet_search'],consent=True)

    def test_briefing_search_is_zero_until_confirm_then_schedule_keeps_binding(self):
        pid=self.ids['analysis'];self.approve(pid)
        preview=self.call('briefing_preview',profile_id=pid,prompt='搜尋合成新聞',time_hhmm='08:00')
        self.assertEqual(preview['search_tools'],['internet_search']);self.assertFalse(self.mock.plugin_requests)
        state=self.call('state')
        self.assertEqual(next(p for p in state['profiles'] if p['id']==pid)['search_policy']['tools'][0]['name'],'internet_search')
        result=self.call('briefing_run',token=preview['token']);self.wait()
        task=self.s.store.task(result['task_id']);self.assertEqual(task['state'],'succeeded',task['error'])
        self.assertEqual(len(self.mock.plugin_requests),1)
        self.assertEqual(self.call('briefing_status',task_id=result['task_id'])['search_activity'],
            [{'name':'internet_search','state':'completed','submitted':True}])
        self.assertFalse(self.s.store.schedules())
        again=self.call('briefing_run',token=preview['token']);self.assertEqual(again,result)
        self.assertEqual(len(self.mock.plugin_requests),1)
        # Policy revision invalidates an existing preview and revokes the old binding.
        other=self.call('briefing_preview',profile_id=pid,prompt='搜尋合成新聞')
        self.call('search_policy_clear',profile_id=pid)
        self.assertFalse(self.api.call('briefing_run',{'token':other['token']})['ok'])
        self.assertEqual(len(self.mock.plugin_requests),1)

    def test_main_chat_with_approved_profile_still_cannot_search(self):
        pid=self.ids['analysis'];self.approve(pid);self.mock.force_tools=True
        tid=self.call('dialogue_start',assistant_id=self.selection())['id']
        result=self.api.call('dialogue_send',{'id':tid,'text':'請搜尋','request_id':'t1'})
        self.assertFalse(result['ok']);self.assertFalse(self.mock.plugin_requests)

    def test_policy_mutation_holds_dispatch_locks_and_reopen_preserves_removal(self):
        import threading
        pid=self.ids['analysis'];self.approve(pid)
        original=self.p.set_search_policy;acquired=[]
        def change(binding,value):
            def contender():
                for lock in (self.s.engine._lock,self.s.dialogue.lock,self.s.company_probe.condition):
                    held=lock.acquire(blocking=False);acquired.append(held)
                    if held:lock.release()
            worker=threading.Thread(target=contender);worker.start();worker.join(2)
            self.assertFalse(worker.is_alive());self.assertEqual(acquired,[False,False,False])
            return original(binding,value)
        self.p.set_search_policy=change
        self.call('search_policy_clear',profile_id=pid)
        self.assertNotIn('search_policy',next(p for p in self.call('state')['profiles'] if p['id']==pid))
        from desktop_app.profiles import Profiles
        loaded=Profiles(self.p.path,vault=self.p.vault)
        self.assertNotIn('search_policy',loaded.validate(loaded.snapshot(pid)))

    def test_planner_then_search_analysis_review_compose(self):
        self.workflow_reply=True;self.with_search=True
        pid=self.p.save('rag','asst_rag');self.ids['rag']=pid;self.approve(pid)
        self.p.set_workflow_capability(pid,['rag'],True,'synthetic acceptance only')
        cid=self.s.store.create_conversation('合成搜尋流程',self.p.snapshot(self.ids['planner']))
        service=self.s.workflows;r=service.create(cid,'搜尋並核對合成資料',self.p.workflow_binding(self.ids['planner']))
        service.discuss(r['id'],r['revision'],'搜尋分析覆核彙整');self.wait()
        r=service.get(r['id']);self.assertEqual(r['state'],'ready');self.assertFalse(self.mock.plugin_requests)
        preview=service.preview(r['id'],r['revision']);self.assertFalse(self.mock.plugin_requests)
        self.assertEqual(preview['search_tools'],[{'step_id':'s0','tools':['internet_search']}])
        tid=service.confirm(r['id'],r['revision'],True);self.wait()
        task=self.s.store.task(tid);self.assertEqual(task['state'],'succeeded',task['error'])
        self.assertEqual(len(self.mock.plugin_requests),1);self.assertEqual(len(self.mock.threads),5)
        runs=[b for m,p,b in self.mock.requests if m=='POST' and p.endswith('/runs')]
        self.assertEqual([b['assistant_id'] for b in runs if b['tool_choice']=='auto'],['asst_rag'])
        self.assertEqual(service.confirm(r['id'],r['revision'],True),tid)
        self.assertEqual(len(self.mock.plugin_requests),1)
