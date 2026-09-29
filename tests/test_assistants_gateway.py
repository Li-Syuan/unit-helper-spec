import tempfile
import unittest
import threading
from pathlib import Path
import httpx
from openai import OpenAI
from desktop_app.assistants_gateway import AssistantsGateway
from desktop_app.gateways import GatewayError
from test_support.assistants_mock import AssistantsMock


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
        with self.assertRaisesRegex(GatewayError,'沒有執行搜尋'):self.gateway().inspect_assistant()

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
        with self.assertRaisesRegex(GatewayError, '沒有可用文字'):
            self.gateway().respond(self.messages)
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
        with self.assertRaisesRegex(GatewayError,'不支援'):
            self.gateway(non_text).respond(self.messages)

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
