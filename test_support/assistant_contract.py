from pathlib import Path
import json
import os
import ssl
import unittest
from unittest.mock import patch

import httpx
from openai import OpenAI

from desktop_app.gateways import (
    CompanyAssistant, CompanyIdentity, DemoAssistant, DemoIdentity,
    DemoQueries, GatewayError, OracleQueries,
)


# Inherit this mixin before unittest.TestCase; override adapter() for a custom wire protocol.
class AssistantContractMixin:
    adapter_class = CompanyAssistant

    def setUp(self):
        self.env = patch.dict(os.environ, {"UNIT_HELPER_TEST_KEY": "secret-must-not-leak"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.config = {"base_url": "https://company.example/v1", "model": "company-assistant",
                       "api_key_env": "UNIT_HELPER_TEST_KEY", "timeout_seconds": 10}

    def adapter(self, handler):
        self.requests = []
        def recording(request):
            self.requests.append(request)
            return handler(request)
        client = OpenAI(base_url=self.config["base_url"], api_key="secret-must-not-leak", max_retries=0,
                        http_client=httpx.Client(transport=httpx.MockTransport(recording), follow_redirects=False))
        self.addCleanup(client.close)
        return self.adapter_class(self.config, client=client)

    @staticmethod
    def success(request):
        payload = json.loads((Path(__file__).parent / 'fixtures' / 'chat-response.json').read_text('utf-8'))
        return httpx.Response(200, json=payload)

    def test_sdk_request_and_conversation_isolation(self):
        adapter = self.adapter(self.success)
        self.assertEqual(adapter.respond([{"role": "user", "content": "第一組"}]), "合成回覆格式測試")
        adapter.respond([{"role": "user", "content": "第二組"}], "rewrite")
        payload = json.loads(self.requests[1].content)
        self.assertEqual(self.requests[0].url.path, "/v1/chat/completions")
        self.assertEqual(payload["model"], "company-assistant")
        self.assertFalse(payload["stream"])
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["messages"][1]["content"], "第二組")
        self.assertNotIn("第一組", self.requests[1].content.decode())
        self.assertNotIn("tools", payload)

    def test_sdk_401_redacts_error_body_and_never_retries(self):
        adapter = self.adapter(lambda request: httpx.Response(401, json={"error": {"message": "secret-must-not-leak"}}))
        with self.assertRaisesRegex(GatewayError, "認證失敗") as caught:
            adapter.respond([{"role": "user", "content": "test"}])
        self.assertNotIn("secret-must-not-leak", str(caught.exception))
        self.assertEqual(len(self.requests), 1)

    def test_sdk_timeout_never_retries(self):
        def timeout(request):
            raise httpx.ReadTimeout("secret-must-not-leak", request=request)
        adapter = self.adapter(timeout)
        with self.assertRaisesRegex(GatewayError, "逾時"):
            adapter.respond([{"role": "user", "content": "test"}])
        self.assertEqual(len(self.requests), 1)

    def test_company_client_options_headers_and_assistant_ref(self):
        self.config.update(header_env={"X-Company-Tenant": "UNIT_HELPER_TEST_TENANT"},
                           assistant_ref="dept-assistant", assistant_ref_field="assistant_id")
        with patch.dict(os.environ, {"UNIT_HELPER_TEST_TENANT": "unit-a"}), patch("openai.OpenAI") as constructor:
            adapter = self.adapter_class(self.config)
            kwargs = constructor.call_args.kwargs
            self.assertEqual(kwargs["base_url"], "https://company.example/v1")
            self.assertEqual(kwargs["max_retries"], 0)
            self.assertEqual(kwargs["timeout"], 10)
            self.assertEqual(kwargs["default_headers"], {"X-Company-Tenant": "unit-a"})
            self.assertFalse(kwargs["http_client"].follow_redirects)
            kwargs["http_client"].close()
            self.assertEqual(adapter.extra_body, {"assistant_id": "dept-assistant"})
        with patch.dict(os.environ, {"UNIT_HELPER_TEST_TENANT": "unit-a"}):
            adapter = self.adapter(self.success)
            adapter.respond([{"role": "user", "content": "test"}])
            self.assertEqual(json.loads(self.requests[0].content)["assistant_id"], "dept-assistant")

    def test_rate_limit_and_redirect_do_not_retry_or_follow(self):
        for status in [302, 429, 500]:
            with self.subTest(status=status):
                adapter = self.adapter(lambda request: httpx.Response(status, headers={"Location": "https://other.example"},
                                                                      json={"error": {"message": "secret-must-not-leak"}}))
                with self.assertRaises(GatewayError):
                    adapter.respond([{"role": "user", "content": "test"}])
                self.assertEqual(len(self.requests), 1)

    def test_tls_default_and_company_ca_bundle(self):
        with patch("openai.OpenAI"), patch("httpx.Client") as http_client:
            self.adapter_class(self.config)
            self.assertIs(http_client.call_args.kwargs["verify"], True)
        context = ssl.create_default_context()
        self.config["ca_bundle"] = "company-ca.pem"
        with patch("ssl.create_default_context", return_value=context) as factory, patch("openai.OpenAI"), patch("httpx.Client") as http_client:
            self.adapter_class(self.config)
            factory.assert_called_once_with(cafile="company-ca.pem")
            self.assertIs(http_client.call_args.kwargs["verify"], context)
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        for bundle in [False, "", "file-does-not-exist-unit-helper.pem"]:
            with self.subTest(bundle=bundle), self.assertRaisesRegex(GatewayError, "CA"):
                self.adapter_class(dict(self.config, ca_bundle=bundle), client=object())

    def test_sdk_empty_malformed_and_tool_response(self):
        for payload in [{}, {"choices": []}, {"choices": [{"message": {"content": ""}}]},
                        {"choices": [{"message": {"content": ["not text"]}}]},
                        {"choices": [{"message": {"content": "done", "tool_calls": [{"id": "x", "type": "function", "function": {"name": "query", "arguments": "{}"}}]}}]}]:
            with self.subTest(payload=payload):
                adapter = self.adapter(lambda request: httpx.Response(200, json=payload))
                with self.assertRaises(GatewayError):
                    adapter.respond([{"role": "user", "content": "test"}])

    def test_configuration_and_context_rejected_before_network(self):
        for settings in [{"base_url": ""}, {"base_url": "http://company.example/v1"},
                         {"base_url": "https://user:password@company.example"},
                         {"base_url": "https://api.openai.com/v1"}, {"model": ""},
                         {"timeout_seconds": 0}, {"api_key_env": "NONEXISTENT_UNIT_HELPER_KEY"}]:
            with self.subTest(settings=settings), self.assertRaises(GatewayError):
                self.adapter_class(dict(self.config, **settings), client=object())
        self.config["max_context_chars"] = 3
        adapter = self.adapter(self.success)
        with self.assertRaisesRegex(GatewayError, "上限"):
            adapter.respond([{"role": "user", "content": "1234"}])
        self.assertEqual(self.requests, [])

    def test_demo_does_not_claim_ai_work(self):
        messages = [{"role": "user", "content": "原文數字 01234"}]
        rewritten = DemoAssistant().respond(messages, "rewrite")
        self.assertIn("原文數字 01234", rewritten)
        self.assertIn("未呼叫 AI", rewritten)
        self.assertIn("尚未產生語意摘要", DemoAssistant().respond(messages, "summarize"))

