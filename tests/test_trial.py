"""Offline trial contract and real Tk checks. Never reads the developer's .env."""
import gc
import json
from pathlib import Path
import ssl
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

import httpx
from openai import OpenAI

from desktop_app.gateways import GatewayError
from desktop_app.trial import ENDPOINT, MODEL, GroqAssistant, TrialProfiles, read_key
from desktop_app.ui import App


class TrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = Path(self.temp.name)/'.env'

    def tearDown(self):
        self.temp.cleanup()

    def test_env_literal_and_no_environment_side_effect(self):
        self.env.write_text('\ufeff# local only\nGROQ_API_KEY="test-key"\nENDPOINT=ignored\n', encoding='utf-8')
        with patch.dict('os.environ', {'GROQ_API_KEY':'other-key'}):
            self.assertEqual(read_key(self.env), 'test-key')
            self.assertEqual(__import__('os').environ['GROQ_API_KEY'], 'other-key')

    def test_bad_env_never_discloses_content(self):
        for content in ('', 'GROQ_API_KEY=', 'GROQ_API_KEY=secret-marker\nGROQ_API_KEY=other',
                        'GROQ_API_KEY=$(secret-marker)', 'GROQ_API_KEY="secret-marker',
                        'GROQ_API_KEY=secret marker', 'x'*65537):
            self.env.write_text(content, encoding='utf-8')
            with self.assertRaises(GatewayError) as error: read_key(self.env)
            self.assertNotIn('secret-marker', str(error.exception))
        self.env.unlink()
        with self.assertRaises(GatewayError): read_key(self.env)

    def adapter(self, handler):
        sdk = OpenAI(api_key='synthetic-key', base_url=ENDPOINT, max_retries=0,
                     http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        client = GroqAssistant(client=sdk)
        self.addCleanup(client.close)
        return client

    @staticmethod
    def response(content='合成測試回答', finish='stop', **fields):
        return httpx.Response(200, json={'id':'test', 'object':'chat.completion', 'created':1,
            'model':MODEL, 'choices':[{'index':0, 'finish_reason':finish,
            'message':{'role':'assistant', 'content':content, **fields}}]})

    def test_real_sdk_request_and_context_isolation(self):
        seen=[]
        def handler(request):
            self.assertEqual(str(request.url), ENDPOINT+'/chat/completions')
            seen.append(json.loads(request.content))
            return self.response()
        client=self.adapter(handler)
        self.assertEqual(client.respond([{'role':'user','content':'first'}]), '合成測試回答')
        client.respond([{'role':'user','content':'second'}], 'rewrite')
        for request in seen:
            self.assertEqual(request['model'], MODEL)
            self.assertFalse(request['stream'])
            self.assertFalse(request['include_reasoning'])
            self.assertEqual(request['max_completion_tokens'], 2048)
            self.assertNotIn('tools', request)
            self.assertNotIn('reasoning_format', request)
        self.assertNotIn('first', json.dumps(seen[1]))

    def test_tls_and_retry_configuration(self):
        with patch('desktop_app.trial.read_key',return_value='synthetic'), patch('httpx.Client') as http, patch('openai.OpenAI') as sdk:
            GroqAssistant()
        context=http.call_args.kwargs['verify']
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertFalse(http.call_args.kwargs['follow_redirects'])
        self.assertEqual(sdk.call_args.kwargs['max_retries'],0)
        self.assertEqual(sdk.call_args.kwargs['base_url'],ENDPOINT)

    def test_status_errors_redacted_and_no_retry(self):
        for code, label in ((401,'認證'),(403,'認證'),(429,'額度'),(500,'拒絕')):
            calls=[]
            def handler(request):
                calls.append(1)
                return httpx.Response(code,json={'error':{'message':'secret-provider-body'}})
            client=self.adapter(handler)
            with self.assertRaisesRegex(GatewayError,label) as error:
                client.respond([{'role':'user','content':'hello'}])
            self.assertNotIn('secret-provider-body',str(error.exception))
            self.assertEqual(len(calls),1)

    def test_timeout_and_connection_redacted(self):
        for cls,label in ((httpx.ReadTimeout,'逾時'),(httpx.ConnectError,'連線')):
            def handler(request): raise cls('secret-network-detail',request=request)
            with self.assertRaisesRegex(GatewayError,label) as error:
                self.adapter(handler).respond([{'role':'user','content':'hello'}])
            self.assertNotIn('secret-network-detail',str(error.exception))

    def test_empty_malformed_incomplete_and_tools_rejected(self):
        responses=[self.response(''),self.response(None),self.response(finish='length'),
            self.response(tool_calls=[{'id':'x','type':'function','function':{'name':'run','arguments':'{}'}}]),
            httpx.Response(200,json={'choices':[]}),httpx.Response(200,json={'unexpected':'value'})]
        for response in responses:
            with self.assertRaises(GatewayError):
                self.adapter(lambda request:response).respond([{'role':'user','content':'hello'}])

    def test_validation_prevents_network_and_silent_truncation(self):
        def handler(request): self.fail('Must not dispatch')
        client=self.adapter(handler)
        for messages in ([],[{'role':'system','content':'x'}],[{'role':'user','content':'x'*6001}]):
            with self.assertRaises(GatewayError): client.respond(messages)
        with self.assertRaises(GatewayError): client.respond([{'role':'user','content':'x'}],'unknown')

    def test_profiles_readonly_and_stale_binding(self):
        profiles=TrialProfiles(self.env)
        self.assertEqual(profiles.default_binding(), {'profile_id':'groq-trial','revision':1})
        for operation,args in ((profiles.save,('x','y')),(profiles.set_endpoint,('https://other.invalid',)),
                               (profiles.save_key,('secret',)),(profiles.set_default,('demo',)),(profiles.remove_key,())):
            with self.assertRaises(GatewayError): operation(*args)
        with self.assertRaises(GatewayError): profiles.validate({'profile_id':'groq-trial','revision':2})
        with self.assertRaises(GatewayError): profiles.validate({'profile_id':'company','revision':1})
        self.assertFalse(self.env.exists())

    def test_missing_key_fails_without_demo_fallback(self):
        profiles=TrialProfiles(self.env)
        with self.assertRaises(GatewayError):
            profiles.respond([{'role':'user','content':'hello'}],'chat',profiles.default_binding())


class TrialTkTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.base.joinpath('config.json').write_text('company-original',encoding='utf-8')
        self.base.joinpath('assistants.json').write_text('company-original',encoding='utf-8')
        self.root=tk.Tk(); self.root.withdraw()
        self.key_patch=patch('desktop_app.trial.read_key',return_value='synthetic-key')
        self.key_patch.start()
        self.network=patch('desktop_app.trial.GroqAssistant.respond',return_value='測試替身回答')
        self.respond=self.network.start()
        self.app=App(self.root,directory=self.base,groq_trial=True)
        self.root.deiconify();self.root.geometry('1050x700');self.root.update()

    def tearDown(self):
        self.app.close(force=True);self.app=None;self.root=None
        self.network.stop();self.key_patch.stop();gc.collect();self.temp.cleanup()

    def wait_for(self,predicate):
        until=time.monotonic()+8
        while time.monotonic()<until:
            self.root.update()
            if predicate(): return
            time.sleep(.02)
        self.fail('Trial operation timed out')

    def test_workspace_and_settings_isolated_without_network_on_start(self):
        a=self.app
        self.assertEqual(a.directory,self.base/'groq-trial')
        self.assertIn('Groq',self.root.title())
        self.assertIn('Groq',a.mode_label['text'])
        self.assertIn('外部',a.page_hint_content('settings'))
        self.assertEqual(a.store.conversation(a.conversation)['binding']['profile_id'],'groq-trial')
        self.assertFalse(hasattr(a,'endpoint_var'))
        self.respond.assert_not_called()
        self.assertEqual((self.base/'config.json').read_text(),'company-original')
        self.assertEqual((self.base/'assistants.json').read_text(),'company-original')
        for mode in ('light','dark'):
            a.change_theme(mode);self.root.update()
            self.assertTrue(a.send_button.winfo_viewable())
        with self.assertRaises(GatewayError): a.apply_settings()

    def test_plan_approval_and_single_dispatch(self):
        a=self.app
        a.input.insert('1.0','請整理這筆虛構文字')
        a.plan_mode.set(True);a.send_chat()
        self.assertEqual(a.store.tasks(),[]);self.respond.assert_not_called()
        plan=a.store.plans()[0]
        tid=a.engine.confirm_plan(plan['id'],plan['revision'],'trial-test')
        self.wait_for(lambda:a.store.task(tid)['state']=='succeeded')
        self.assertEqual(self.respond.call_count,1)
        self.assertIn('測試替身回答',str(a.store.task(tid)))
        self.assertEqual(a.engine.confirm_plan(plan['id'],plan['revision'],'trial-test'),tid)
        self.assertEqual(self.respond.call_count,1)

    def test_enter_sends_and_work_card_does_not(self):
        a=self.app
        a.quick_work('summarize');self.respond.assert_not_called()
        a.input.delete('1.0','end');a.input.insert('1.0','虛構：已完成報告，明天檢查資料。')
        a.input.focus_force();self.root.update();a.input.event_generate('<Return>')
        self.wait_for(lambda:bool(a.store.tasks()) and a.store.tasks()[0]['state']=='succeeded')
        self.assertEqual(self.respond.call_count,1)
