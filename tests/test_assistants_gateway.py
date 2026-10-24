import tempfile
import unittest
import threading
from pathlib import Path
import httpx
from openai import OpenAI
from desktop_app.assistants_gateway import AssistantsGateway
from desktop_app.gateways import GatewayError
from test_support.assistants_mock import AssistantsMock
from desktop_app.assistant_errors import AssistantFailure


class AssistantsGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'sessions.sqlite3'
        self.mock = AssistantsMock(reply='合成答案')
        self.ctx = {'conversation_id': 'chat-one', 'request_id': 'turn-one'}
        self.binding = {'profile_id': 'one', 'revision': 1}
        self.messages = [{'role': 'user', 'content': '合成問題'}]
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        self.tmp.cleanup()

    def gateway(self, transport=None, binding=None, **kwargs):
        sdk = OpenAI(api_key='synthetic-key', base_url='https://fixture.example.test/v1', max_retries=0,
                     http_client=httpx.Client(transport=httpx.MockTransport(transport or self.mock.handle)))
        gateway = AssistantsGateway({'base_url': 'https://fixture.example.test/v1', 'assistant_id': 'asst_fixture',
                                     'poll_seconds': 0.01}, 'synthetic-key', self.path, binding or self.binding,
                                    client=sdk, **kwargs)
        self.clients.append(gateway)
        return gateway

    def test_real_sdk_request_and_multiturn_no_duplicate_history(self):
        gateway = self.gateway()
        self.assertEqual(gateway.respond(self.messages, context=self.ctx), '合成答案')
        count = len(self.mock.requests)
        self.assertTrue(gateway.inspect_request(context=self.ctx, remote=True)['recoverable'])
        self.assertEqual(len(self.mock.requests), count)
        self.assertEqual(gateway.respond(self.messages, context=self.ctx), '合成答案')
        self.assertEqual(len(self.mock.requests), count)
        history = self.messages + [{'role': 'assistant', 'content': '合成答案'}, {'role': 'user', 'content': '再問一次'}]
        self.assertEqual(self.gateway().respond(history, context=dict(self.ctx, request_id='turn-two')), '合成答案')
        self.assertEqual(len(self.mock.threads), 1)
        sent = [r[2] for r in self.mock.requests if r[0] == 'POST' and r[1].endswith('/messages')]
        self.assertEqual(sent, [{'role': 'user', 'content': '合成問題'}, {'role': 'user', 'content': '再問一次'}])
        run = next(r[2] for r in self.mock.requests if r[0] == 'POST' and r[1].endswith('/runs'))
        self.assertEqual(run['assistant_id'], 'asst_fixture')
        self.assertEqual(run['tool_choice'], 'none')

    def test_ten_turns_per_distinct_assistant_no_history_leak_or_replayed_post(self):
        for aid in ('asst_first','asst_second'):
            gateway=self.gateway(binding={'profile_id':aid,'revision':1});gateway.assistant_id=aid
            history=[]
            for turn in range(10):
                history.append({'role':'user','content':aid+' synthetic '+str(turn)})
                context={'conversation_id':'same-local-id','request_id':'turn-'+str(turn)}
                answer=gateway.respond(history,context=context)
                before=len(self.mock.requests)
                self.assertEqual(gateway.respond(history,context=context),answer)
                self.assertEqual(before,len(self.mock.requests))
                history.append({'role':'assistant','content':answer})
        self.assertEqual(len(self.mock.threads),2);self.assertEqual(len(self.mock.runs),20)
        for record in self.mock.runs.values():
            run=record['run'];messages=self.mock.threads[run['thread_id']]
            self.assertEqual(len(messages),20)
            for message in messages:
                if message['role']=='user':self.assertTrue(message['content'][0]['text']['value'].startswith(run['assistant_id']))

    def test_http_classification_and_metadata_failure_does_not_block_chat(self):
        for status,code in ((401,'AUTHENTICATION'),(403,'FORBIDDEN'),(404,'NOT_FOUND'),(429,'RATE_LIMIT')):
            def transport(request):
                if '/assistants/' in request.url.path:
                    return httpx.Response(status,json={'error':{'message':'DO-NOT-LEAK-private-body'}})
                return self.mock.handle(request)
            gateway=self.gateway(transport,binding={'profile_id':str(status),'revision':1})
            with self.assertRaises(AssistantFailure) as caught:gateway.inspect_assistant()
            self.assertEqual(caught.exception.code,code);self.assertEqual(caught.exception.stage,'assistant_metadata')
            self.assertEqual(caught.exception.http_status,status)
            self.assertNotIn('DO-NOT-LEAK',str(caught.exception))
            self.assertEqual(gateway.respond(self.messages,context=self.ctx),'合成答案')

    def test_total_timeout_config_and_failure_metadata_are_allowlisted(self):
        from desktop_app.config import validate_config
        from desktop_app.assistant_errors import decode_failure
        import json
        self.assertEqual(validate_config({})['assistant']['run_timeout_seconds'],600)
        self.assertEqual(validate_config({'assistant':{'run_timeout_seconds':900}})['assistant']['run_timeout_seconds'],900)
        for value in (True,0,1801,'600'):
            with self.assertRaises(ValueError):validate_config({'assistant':{'run_timeout_seconds':value}})
        failure=AssistantFailure('RUN_FAILED','run_poll',remote_code='private body')
        self.assertIsNone(decode_failure(json.dumps(failure.metadata())).remote_code)
        self.assertTrue(AssistantFailure('TIMEOUT','preflight',sent=False).sent)

    def test_live_check_requires_explicit_flag_and_uses_temporary_workspace(self):
        import runpy
        import copy
        from unittest.mock import patch
        from desktop_app.profiles import Profiles
        from tests.test_profiles import MemoryVault
        entry=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/check-assistants.py'))
        with patch('desktop_app.profiles.Profiles',side_effect=AssertionError('must not load settings')):
            self.assertEqual(entry['main']([]),0)
        p=Profiles(Path(self.tmp.name)/'source'/'assistants.json',vault=MemoryVault())
        p.set_endpoint('https://fixture.example.test/v1');p.set_wire_mode('assistants');p.save_key('synthetic')
        ids=[p.save('合成'+str(i),'asst_distinct_'+str(i)) for i in range(2)]
        original=p.path;before=original.read_bytes();original_data=copy.deepcopy(p.data)
        def client(data,profile,key,binding):
            sdk=OpenAI(api_key=key,base_url=data['endpoint'],max_retries=0,
                       http_client=httpx.Client(transport=httpx.MockTransport(self.mock.handle)))
            return AssistantsGateway({'base_url':data['endpoint'],'assistant_id':profile['assistant_id']},
                key,p.path.parent/'assistant-sessions.sqlite3',binding,client=sdk)
        with patch.object(p,'_assistants_client',side_effect=client):
            result=entry['exercise'](p,ids,Path(self.tmp.name)/'isolated')
        self.assertEqual(result['service'],'company_real_passed') # transport remains synthetic in this unit test
        self.assertEqual([r['completed_turns'] for r in result['profiles']],[10,10])
        self.assertEqual(len(self.mock.threads),2);self.assertEqual(original.read_bytes(),before)
        self.assertNotIn('asst_distinct_',__import__('json').dumps(result))
        self.assertEqual([v['assistant_id'] for v in original_data['profiles']],['asst_distinct_0','asst_distinct_1'])

    def test_assistant_inspection_is_one_get_not_permission_or_search(self):
        self.mock.assistant_tools=[{'type':'function','function':{'name':'synthetic_search','description':'synthetic only','parameters':{'type':'object'}}}]
        result=self.gateway().inspect_assistant()
        self.assertEqual(result['connection'],'passed')
        self.assertEqual(result['search'],'not_tested')
        self.assertTrue(result['requires_plugin_review'])
        self.assertEqual([(m,p) for m,p,b in self.mock.requests],[('GET','/assistants/asst_fixture')])
        self.assertFalse(self.mock.runs);self.assertFalse(self.mock.threads)

    def test_assistant_inspection_rejects_wrong_id_and_redacts_errors(self):
        def wrong(request):return httpx.Response(200,json={'id':'wrong','object':'assistant','created_at':0,'model':'synthetic','tools':[]})
        with self.assertRaisesRegex(GatewayError,'識別'):self.gateway(wrong).inspect_assistant()
        self.mock.fail_status=403
        with self.assertRaisesRegex(GatewayError,'權限'):self.gateway().inspect_assistant()

    def test_isolation_binding_conversation_and_ephemeral(self):
        self.gateway().respond(self.messages, context=self.ctx)
        self.gateway(binding={'profile_id': 'two', 'revision': 1}).respond(self.messages, context=self.ctx)
        self.gateway().respond(self.messages, context={'conversation_id': 'other', 'request_id': 'x'})
        gateway = self.gateway()
        gateway.respond(self.messages)
        gateway.respond(self.messages)
        self.assertEqual(len(self.mock.threads), 5)

    def test_requires_action_never_dispatches_plugin(self):
        self.mock.statuses = ['requires_action']
        gateway = self.gateway()
        with self.assertRaisesRegex(GatewayError, '未核准'):
            gateway.respond(self.messages, context=self.ctx)
        self.assertFalse(any('plugin' in r[1] or 'submit_tool' in r[1] for r in self.mock.requests))
        self.assertEqual(gateway.inspect_request(context=self.ctx)['state'], 'tools_blocked')
        with self.assertRaises(GatewayError):
            gateway.respond(self.messages, context=dict(self.ctx, resume=True))

    def test_run_correlated_paginated_reply(self):
        self.mock.paginate = True
        gateway = self.gateway()
        gateway.respond(self.messages, context=self.ctx)
        self.mock.reply = '第二次答案'
        history = self.messages + [{'role': 'assistant', 'content': '合成答案'}, {'role': 'user', 'content': '第二次'}]
        self.assertEqual(gateway.respond(history, context=dict(self.ctx, request_id='two')), '第二次答案')

    def test_unknown_write_outcome_no_retry_after_reopen(self):
        def transport(req):
            result = self.mock.handle(req)
            if req.method == 'POST' and req.url.path.endswith('/runs'):
                raise httpx.ReadTimeout('secret response lost', request=req)
            return result
        with self.assertRaises(GatewayError) as error:
            self.gateway(transport).respond(self.messages, context=self.ctx)
        self.assertNotIn('secret', str(error.exception))
        gateway = self.gateway()
        self.assertFalse(gateway.inspect_request(context=self.ctx)['recoverable'])
        count = len(self.mock.requests)
        with self.assertRaises(GatewayError):
            gateway.respond(self.messages, context=dict(self.ctx, resume=True))
        self.assertEqual(len(self.mock.requests), count)

    def test_known_run_resume_only_reads(self):
        self.mock.statuses = ['in_progress', 'completed']
        def transport(req):
            if req.method == 'GET' and '/runs/' in req.url.path:
                raise httpx.ConnectError('synthetic interruption', request=req)
            return self.mock.handle(req)
        with self.assertRaises(GatewayError):
            self.gateway(transport).respond(self.messages, context=self.ctx)
        gateway = self.gateway()
        self.assertTrue(gateway.inspect_request(context=self.ctx)['recoverable'])
        before = len([r for r in self.mock.requests if r[0] == 'POST'])
        self.assertEqual(gateway.respond(self.messages, context=dict(self.ctx, resume=True)), '合成答案')
        self.assertEqual(len([r for r in self.mock.requests if r[0] == 'POST']), before)

    def test_cancellation_late_completed_is_not_success(self):
        self.mock.statuses = ['in_progress', 'completed']
        def cancelled():
            return bool(self.mock.runs)
        gateway = self.gateway()
        with self.assertRaisesRegex(GatewayError, '取消'):
            gateway.respond(self.messages, context=dict(self.ctx, cancelled=cancelled))
        state = gateway.inspect_request(context=self.ctx)
        self.assertEqual(state['state'], 'cancelled')
        self.assertFalse(state['recoverable'])

    def test_authentication_blank_malformed_and_failed(self):
        self.mock.fail_status = 401
        with self.assertRaisesRegex(GatewayError, '認證失敗'):
            self.gateway().respond(self.messages)
        self.mock.fail_status = None
        self.mock.reply = ' '
        with self.assertRaises(AssistantFailure) as blank:
            self.gateway().respond(self.messages)
        self.assertEqual((blank.exception.code,blank.exception.stage),('FORMAT','messages_read'))
        self.mock.statuses = ['failed']
        with self.assertRaisesRegex(GatewayError, '未完成'):
            self.gateway().respond(self.messages)
        def malformed(req):
            return httpx.Response(200, json={'id': None})
        with self.assertRaises(GatewayError):
            self.gateway(malformed).respond(self.messages)

    def test_history_and_request_revision_refuse_remote_calls(self):
        gateway = self.gateway()
        gateway.respond(self.messages, context=self.ctx)
        count = len(self.mock.requests)
        with self.assertRaisesRegex(GatewayError, '內容已改變'):
            gateway.respond([{'role': 'user', 'content': 'changed'}], context=self.ctx)
        with self.assertRaisesRegex(GatewayError, '歷史'):
            gateway.respond(self.messages, context=dict(self.ctx, request_id='another'))
        self.assertEqual(count, len(self.mock.requests))

    def test_overall_deadline_does_not_repeat_remote_mutations(self):
        self.mock.statuses = ['in_progress']
        now = [0.0]
        def sleep(seconds):
            now[0] += 601
        gateway = self.gateway(clock=lambda: now[0], sleep=sleep)
        with self.assertRaisesRegex(GatewayError, '逾時'):
            gateway.respond(self.messages, context=self.ctx)
        self.assertEqual(len(self.mock.runs), 1)
        self.assertTrue(gateway.inspect_request(context=self.ctx)['recoverable'])
        # A workflow supplies its remaining total budget, which may be shorter.
        now[0]=0
        gateway=self.gateway(clock=lambda:now[0],sleep=lambda seconds:now.__setitem__(0,2))
        with self.assertRaises(GatewayError):
            gateway.respond(self.messages,context=dict(self.ctx,request_deadline_seconds=1,resume=True))
        self.assertEqual(len(self.mock.runs),1)

    def test_endpoint_and_ca_validation(self):
        for endpoint in ('http://company.test', 'https://user:pass@company.test', 'https://api.openai.com/v1'):
            with self.assertRaises(GatewayError):
                AssistantsGateway({'base_url': endpoint, 'assistant_id': 'a'}, 'test', self.path, self.binding)
        with self.assertRaisesRegex(GatewayError, 'CA'):
            AssistantsGateway({'base_url': 'https://company.test', 'assistant_id': 'a', 'ca_bundle': 'missing.pem'},
                              'test', self.path, self.binding)

    def test_unknown_message_outcome_and_failed_run_never_replay_history(self):
        def transport(req):
            response = self.mock.handle(req)
            if req.method == 'POST' and req.url.path.endswith('/messages'):
                raise httpx.ReadTimeout('accepted but response lost', request=req)
            return response
        with self.assertRaises(GatewayError):
            self.gateway(transport).respond(self.messages, context=self.ctx)
        before = len(self.mock.requests)
        with self.assertRaises(GatewayError):
            self.gateway().respond(self.messages, context=dict(self.ctx, request_id='new'))
        self.assertEqual(before, len(self.mock.requests))
        ctx = {'conversation_id':'failure','request_id':'one'}
        self.mock.statuses = ['failed']
        gateway = self.gateway()
        with self.assertRaises(GatewayError):
            gateway.respond(self.messages, context=ctx)
        before = len(self.mock.requests)
        with self.assertRaises(GatewayError):
            gateway.respond(self.messages, context=dict(ctx, request_id='two'))
        self.assertEqual(before, len(self.mock.requests))

    def test_remote_inspection_does_not_save_a_success_or_reexecute(self):
        self.mock.statuses = ['in_progress', 'completed']
        def transport(req):
            if req.method == 'GET' and '/runs/' in req.url.path:
                raise httpx.ConnectError('lost', request=req)
            return self.mock.handle(req)
        with self.assertRaises(GatewayError):
            self.gateway(transport).respond(self.messages, context=self.ctx)
        gateway = self.gateway()
        before = len([r for r in self.mock.requests if r[0]=='POST'])
        inspected = gateway.inspect_request(context=self.ctx, remote=True)
        self.assertTrue(inspected['remote_checked'])
        self.assertTrue(inspected['recoverable'])
        self.assertEqual(inspected['state'], 'polling')
        self.assertTrue(inspected['remote_terminal'])
        self.assertEqual(before, len([r for r in self.mock.requests if r[0]=='POST']))
        with self.assertRaises(GatewayError):
            gateway.respond(self.messages, context=dict(self.ctx, request_id='new'))

    def test_wrong_run_identity_and_non_text_content_are_rejected(self):
        def wrong_run(req):
            response = self.mock.handle(req)
            if req.method=='POST' and req.url.path.endswith('/runs'):
                data=response.json();data['thread_id']='other-thread'
                return httpx.Response(200,json=data)
            return response
        with self.assertRaisesRegex(GatewayError,'識別不一致'):
            self.gateway(wrong_run).respond(self.messages)
        def non_text(req):
            response=self.mock.handle(req)
            if req.method=='GET' and req.url.path.endswith('/messages'):
                data=response.json()
                data['data'][-1]['content']=[{'type':'image_file','image_file':{'file_id':'synthetic'}}]
                return httpx.Response(200,json=data)
            return response
        with self.assertRaises(AssistantFailure) as nontext:
            self.gateway(non_text).respond(self.messages)
        self.assertEqual((nontext.exception.code,nontext.exception.stage),('FORMAT','messages_read'))

    def test_active_session_refuses_double_dispatch_but_other_session_works(self):
        entered, release = threading.Event(), threading.Event()
        errors = []
        def held(req):
            if req.method=='POST' and req.url.path.endswith('/runs'):
                entered.set();release.wait(3)
            return self.mock.handle(req)
        first, second = self.gateway(held), self.gateway()
        def work():
            try:first.respond(self.messages,context=self.ctx)
            except Exception as exc:errors.append(exc)
        worker=threading.Thread(target=work)
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            with self.assertRaisesRegex(GatewayError,'處理中'):
                second.respond(self.messages,context=self.ctx)
            self.assertEqual(second.respond(self.messages,context={'conversation_id':'other','request_id':'x'}),'合成答案')
        finally:
            release.set();worker.join(3)
        self.assertFalse(errors)
        self.assertEqual(len(self.mock.runs),2)


if __name__ == '__main__':
    unittest.main()
