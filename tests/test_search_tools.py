import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import httpx
from openai import OpenAI
from desktop_app.assistants_gateway import AssistantsGateway, session_context
from desktop_app.search_tools import policy, arguments
from desktop_app.gateways import GatewayError
from desktop_app.profiles import Profiles
from desktop_app.company_readiness import CompanyProbe
from test_support.search_mock import SearchMock, SEARCH_TOOL, call


class SearchToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.mock=SearchMock();self.clients=[]
        self.binding={'profile_id':'synthetic','revision':1}
        self.context={'conversation_id':'test','request_id':'test','search_authorized':True}
    def tearDown(self):
        for c in self.clients:c.close()
        self.tmp.cleanup()
    def gateway(self,approved=True):
        sdk=OpenAI(base_url='https://synthetic.example.test/v1',api_key='synthetic-test-only',max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(self.mock.handle),follow_redirects=False))
        config={'base_url':'https://synthetic.example.test/v1','assistant_id':'asst_search','poll_seconds':.01}
        if approved:config['search_policy']={'tools':[SEARCH_TOOL]}
        gateway=AssistantsGateway(config,'synthetic-test-only',Path(self.tmp.name)/'ledger.sqlite3',self.binding,client=sdk)
        self.clients.append(gateway);return gateway
    def run_search(self,gateway=None,context=None,purpose='chat'):
        return (gateway or self.gateway()).respond([{'role':'user','content':'合成需求'}],purpose,context or self.context)
    def test_approved_search_uses_fixed_endpoint_and_correlated_submission_and_cached_result(self):
        reserved=[]
        context=dict(self.context,reserve_tool_round=lambda signature:reserved.append(signature))
        g=self.gateway();text=self.run_search(g,context)
        self.assertIn('合成搜尋',text);self.assertEqual(len(self.mock.plugin_requests),1)
        url,args=self.mock.plugin_requests[0]
        self.assertEqual(httpx.URL(url).path,'/v1/pluginapi')
        self.assertEqual(dict(httpx.URL(url).params),{'tid':'thread_mock_1','aid':'asst_search','pid':'internet_search'})
        self.assertEqual(args,{'query':'合成新聞'})
        self.assertEqual(self.run_search(g,context),text);self.assertEqual(len(self.mock.plugin_requests),1)
        self.assertEqual(len(reserved),1)
        run=next(b for m,p,b in self.mock.requests if p.endswith('/runs') and m=='POST')
        self.assertEqual(run['tools'][0]['function']['name'],'internet_search')
        self.assertEqual(run['tool_choice'],'auto')
        submit=next(b for m,p,b in self.mock.requests if p.endswith('/submit_tool_outputs'))
        self.assertEqual(submit['tool_outputs'],[{'tool_call_id':'call_search','output':'synthetic source only'}])

    def test_total_job_budget_stops_before_search_and_model_continuation(self):
        def exhausted(signature):raise ValueError('AGENT_REQUEST_LIMIT')
        with self.assertRaisesRegex(GatewayError,'AGENT_REQUEST_LIMIT'):
            self.run_search(context=dict(self.context,reserve_tool_round=exhausted))
        self.assertFalse(self.mock.plugin_requests)
        self.assertFalse(any(p.endswith('/submit_tool_outputs') for m,p,b in self.mock.requests))
    def test_no_policy_cannot_dispatch_even_if_context_requests_it(self):
        self.mock.force_tools=True
        with self.assertRaises(GatewayError):self.run_search(self.gateway(False))
        self.assertFalse(self.mock.plugin_requests)
    def test_chat_and_planner_keep_tools_off(self):
        for index,(purpose,authorized) in enumerate((('chat',False),('workflow_plan',True))):
            context=dict(self.context,request_id=str(index),conversation_id=str(index),search_authorized=authorized)
            self.run_search(context=context,purpose=purpose)
        self.assertFalse(self.mock.plugin_requests)
        self.assertTrue(all(b['tool_choice']=='none' for m,p,b in self.mock.requests if p.endswith('/runs') and m=='POST'))
    def test_mixed_batch_is_rejected_before_first_call(self):
        self.mock.batches=[[call(),call('bad','python_exec')]]
        with self.assertRaises(GatewayError):self.run_search()
        self.assertFalse(self.mock.plugin_requests)
    def test_unknown_arguments_rejected(self):
        self.mock.batches=[[call(raw='{"query":"hello","url":"https://attacker.test"}')]]
        with self.assertRaises(GatewayError):self.run_search()
        self.assertFalse(self.mock.plugin_requests)
    def test_duplicate_json_keys_and_wrong_types_rejected(self):
        definition=policy({'tools':[SEARCH_TOOL]})['tools'][0]['parameters']
        for raw in ('{"query":"a","query":"b"}','{"query":null}','{"query":123}','{"query":NaN}','[]'):
            with self.subTest(raw=raw),self.assertRaises(GatewayError):arguments(raw,definition)
    def test_unsupported_schema_cannot_be_approved(self):
        for value in ({'type':'object','$ref':'https://example.test'}, {'type':'object','additionalProperties':True},
                      {'type':'object','properties':{'query':{'type':'string','pattern':'.*'}}}):
            with self.subTest(value=value),self.assertRaises(GatewayError):policy({'tools':[dict(SEARCH_TOOL,parameters=value)]})
    def test_four_call_batch_limit(self):
        self.mock.batches=[[call(str(i)) for i in range(5)]]
        with self.assertRaises(GatewayError):self.run_search()
        self.assertFalse(self.mock.plugin_requests)
    def test_two_batches_pair_multiple_outputs(self):
        self.mock.batches=[[call('a'),call('b')],[call('c')]]
        self.run_search()
        self.assertEqual(len(self.mock.plugin_requests),3)
        submitted=[b['tool_outputs'] for m,p,b in self.mock.requests if p.endswith('/submit_tool_outputs')]
        self.assertEqual([[v['tool_call_id'] for v in batch] for batch in submitted],[['a','b'],['c']])
    def test_description_survives_approval_and_run_override(self):
        tool=copy.deepcopy(SEARCH_TOOL);tool['description']='組織核准的唯讀新聞搜尋'
        tool['parameters']['properties']['query']['description']='搜尋關鍵字'
        self.mock.assistant_tools=[{'type':'function','function':tool}]
        g=self.gateway();metadata=g.inspect_assistant();g.search_policy=policy({'tools':metadata['search_candidates']})
        self.run_search(g)
        declared=next(b['tools'][0]['function'] for m,p,b in self.mock.requests if p.endswith('/runs') and m=='POST')
        self.assertEqual(declared['description'],tool['description'])
        self.assertEqual(declared['parameters']['properties']['query']['description'],'搜尋關鍵字')
    def test_completed_tools_resume_from_receipt_without_research(self):
        # Simulate a process stopping after durable tool results, before the submit intent.
        g=self.gateway();original=g.ledger.save;stopped=[False]
        def save(key,session,rid,request):
            original(key,session,rid,request)
            if (not stopped[0] and request['state']=='tools_ready' and
                    all(c['state']=='completed' for b in request['tool_batches'] for c in b['calls'])):
                stopped[0]=True;raise RuntimeError('synthetic process stop')
        g.ledger.save=save
        with self.assertRaises(RuntimeError):self.run_search(g)
        self.run_search(context=dict(self.context,resume=True))
        self.assertEqual(len(self.mock.plugin_requests),1)
        self.assertEqual(sum(p.endswith('/submit_tool_outputs') for m,p,b in self.mock.requests),1)
    def test_foreign_thread_stops_before_plugin(self):
        g=self.gateway();original=self.mock.dispatch
        def dispatch(method,path,body=None,query=None):
            status,value=original(method,path,body,query)
            if method=='POST' and path.endswith('/runs'):value=dict(value,thread_id='foreign')
            return status,value
        self.mock.dispatch=dispatch
        with self.assertRaises(GatewayError):self.run_search(g)
        self.assertFalse(self.mock.plugin_requests)
    def test_three_batch_limit(self):
        self.mock.batches=[[call(str(i))] for i in range(4)]
        with self.assertRaises(GatewayError):self.run_search()
        self.assertEqual(len(self.mock.plugin_requests),3)
    def test_reused_call_id_with_changed_arguments_rejected(self):
        self.mock.batches=[[call()],[call(raw='{"query":"changed"}')]]
        with self.assertRaises(GatewayError):self.run_search()
        self.assertEqual(len(self.mock.plugin_requests),1)
    def test_oversize_response_not_truncated_or_submitted(self):
        self.mock.plugin_reply='x'*131073
        with self.assertRaises(GatewayError):self.run_search()
        self.assertFalse(any(p.endswith('/submit_tool_outputs') for m,p,b in self.mock.requests))
    def test_empty_response_not_submitted(self):
        self.mock.plugin_reply=' '
        with self.assertRaises(GatewayError):self.run_search()
        self.assertFalse(any(p.endswith('/submit_tool_outputs') for m,p,b in self.mock.requests))
    def test_plugin_unknown_does_not_retry_after_restart(self):
        self.mock.lose_plugin=True;g=self.gateway()
        with self.assertRaises(GatewayError):self.run_search(g)
        self.mock.lose_plugin=False
        with self.assertRaises(GatewayError):self.run_search(context=dict(self.context,resume=True))
        self.assertEqual(len(self.mock.plugin_requests),1)
        self.assertFalse(g.inspect_request(context=self.context)['recoverable'])
    def test_submit_unknown_does_not_retry_after_restart(self):
        self.mock.lose_submit=True;g=self.gateway()
        with self.assertRaises(GatewayError):self.run_search(g)
        self.mock.lose_submit=False
        with self.assertRaises(GatewayError):self.run_search(context=dict(self.context,resume=True))
        self.assertEqual(len(self.mock.plugin_requests),1)
        self.assertEqual(sum(p.endswith('/submit_tool_outputs') for m,p,b in self.mock.requests),1)
        self.assertFalse(g.inspect_request(context=self.context)['recoverable'])
    def test_cancel_during_plugin_never_submits_result_or_succeeds(self):
        cancelled=[False];self.mock.after_plugin=lambda:cancelled.__setitem__(0,True)
        with self.assertRaises(GatewayError):self.run_search(context=dict(self.context,cancelled=lambda:cancelled[0]))
        self.assertFalse(any(p.endswith('/submit_tool_outputs') for m,p,b in self.mock.requests))
        self.assertEqual(len(self.mock.plugin_requests),1)
    def test_policy_changed_cannot_reuse_cached_request(self):
        self.run_search()
        with self.assertRaises(GatewayError):self.run_search(context=dict(self.context,search_authorized=False))
        self.assertEqual(len(self.mock.plugin_requests),1)
    def test_metadata_exposes_schema_without_search_or_verification(self):
        self.mock.assistant_tools.append({'type':'code_interpreter'})
        result=self.gateway().inspect_assistant()
        self.assertEqual(result['search'],'not_tested');self.assertEqual(result['search_candidates'][0]['name'],'internet_search')
        self.assertEqual(result['unsupported_tools'][0]['name'],'code_interpreter')
        self.assertEqual(len(self.mock.requests),1);self.assertFalse(self.mock.plugin_requests)


class SearchPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Profiles(Path(self.tmp.name)/'profiles.json',vault=Mock())
        self.p.set_endpoint('https://example.test/v1');self.p.set_wire_mode('assistants');self.pid=self.p.save('search','asst_search')
        self.p.inspect_assistant=Mock(return_value={'search_candidates':[SEARCH_TOOL],'search':'not_tested'})
        self.probe=CompanyProbe(self.p)
    def tearDown(self):self.tmp.cleanup()
    def test_consent_binds_revision_and_revokes_verified_role_without_dispatch(self):
        self.p.set_workflow_capability(self.pid,['rag'],True,'synthetic evidence')
        old=self.p.snapshot(self.pid);token=self.probe.inspect(self.pid)['policy_token']
        result=self.probe.approve(token,['internet_search'],True)
        self.assertEqual(result['company_search'],'not_tested');self.assertGreater(result['revision'],old['revision'])
        self.assertFalse(result['chat_search_enabled'])
        self.assertFalse(self.p.workflow_catalog())
        with self.assertRaises(GatewayError):self.p.validate(old)
        with self.assertRaises(ValueError):self.probe.approve(token,['internet_search'],True)
    def test_unknown_tool_or_no_consent_cannot_save(self):
        token=self.probe.inspect(self.pid)['policy_token'];before=copy.deepcopy(self.p.data)
        for names,consent in ((['python_exec'],True),(['internet_search'],False)):
            with self.assertRaises(ValueError):self.probe.approve(token,names,consent)
        self.assertEqual(before,self.p.data)
    def test_expired_or_revised_probe_cannot_save(self):
        token=self.probe.inspect(self.pid)['policy_token'];self.probe.approval['expires']=0
        with self.assertRaises(ValueError):self.probe.approve(token,['internet_search'],True)
        token=self.probe.inspect(self.pid)['policy_token'];self.p.save('changed','asst_other',profile_id=self.pid)
        with self.assertRaises(GatewayError):self.probe.approve(token,['internet_search'],True)
    def test_endpoint_id_and_protocol_changes_clear_permissions(self):
        for mode in ('id','endpoint','wire'):
            self.p.set_wire_mode('assistants')
            self.p.set_search_policy(self.p.snapshot(self.pid),{'tools':[SEARCH_TOOL]},chat_enabled=True)
            if mode=='id':self.p.save('other','asst_other',profile_id=self.pid)
            elif mode=='endpoint':self.p.set_endpoint('https://different.test/v1')
            else:self.p.set_wire_mode('model')
            self.assertNotIn('search_policy',self.p.validate(self.p.snapshot(self.pid)))
            self.assertFalse(self.p.validate(self.p.snapshot(self.pid))['chat_search_enabled'])

    def test_chat_consent_is_explicit_and_profiles_gate_only_ordinary_chat(self):
        token=self.probe.inspect(self.pid)['policy_token']
        with self.assertRaises(ValueError):self.probe.approve(token,['internet_search'],True,chat_enabled='true')
        self.probe.approve(token,['internet_search'],True,chat_enabled=True)
        self.p.key=Mock(return_value='synthetic');client=Mock();client.respond.return_value='reply'
        self.p._assistants_client=Mock(return_value=client)
        binding=self.p.snapshot(self.pid)
        for operation,purpose,expected in [('ordinary_chat','chat',True),('ordinary_chat','workflow_plan',False),
                                           ('task_draft','chat',False),('task_draft','workflow_step',False)]:
            context={'operation':operation,'search_authorized':not expected}
            self.p.respond([] ,purpose,binding,context=context)
            self.assertEqual(client.respond.call_args.kwargs['context']['search_authorized'],expected)
            self.assertEqual(context['search_authorized'],not expected)
        self.p.respond([],'chat',binding,context={'operation':'assistant_briefing','search_authorized':True})
        self.assertTrue(client.respond.call_args.kwargs['context']['search_authorized'])
        self.p.set_search_policy(binding,{'tools':[SEARCH_TOOL]})
        self.p.respond([],'chat',self.p.snapshot(self.pid),context={'operation':'ordinary_chat','search_authorized':True})
        self.assertFalse(client.respond.call_args.kwargs['context']['search_authorized'])
        self.p.set_search_policy(self.p.snapshot(self.pid),None,chat_enabled=True)
        self.assertFalse(self.p.validate(self.p.snapshot(self.pid))['chat_search_enabled'])
    def test_rag_only_workflow_authorization(self):
        self.p.set_workflow_capability(self.pid,['planner','analysis','review','compose','rag'],True,'synthetic')
        self.p.respond=Mock(return_value='synthetic')
        binding=self.p.workflow_binding(self.pid)
        for role in ('planner','analysis','review','compose','rag'):
            self.p.workflow_call([],role,binding,{'run_id':'r','step_id':role,'search_authorized':True})
            self.assertEqual(self.p.respond.call_args.kwargs['context'].get('search_authorized',False),role=='rag')
