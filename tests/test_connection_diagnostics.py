"""Diagnostic journeys with isolated local data and synthetic responses only."""
import copy
import json
import re
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from desktop_app.assistant_errors import AssistantFailure
from desktop_app.config import DEFAULT
from desktop_app.connection_diagnostics import ConnectionDiagnostics
from desktop_app.core import stamp
from desktop_app.web_bridge import WebBridge
from desktop_app.web_session import WebSession


class ConnectionDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.root = Path(self.tmp.name)
        self.s = WebSession(directory=self.root, config=copy.deepcopy(DEFAULT), start_scheduler=False)
        p = self.s.profiles;p.set_endpoint('https://secret-endpoint.example.test/v1');p.set_wire_mode('assistants')
        self.pid = p.save('SECRET-NAME', 'asst_SECRET_ID')
        self.d = self.s.diagnostics;self.calls = []

    def tearDown(self):self.s.close();self.tmp.cleanup()

    def reply(self, messages, purpose, binding, context=None):
        self.calls.append(context)
        marker = re.search(r'QA-[a-f0-9]+', messages[0]['content'])
        return 'OK' if len(messages) == 1 else marker.group()

    def rows(self, pid=None):return {r['check']: r for r in self.d.status(profile_id=pid or self.pid)['rows']}

    def test_two_profiles_partial_capabilities_persist_and_no_network_on_export(self):
        other = self.s.profiles.save('SECOND-SECRET', 'asst_SECOND')
        with patch.object(self.s.profiles, 'respond', side_effect=self.reply):self.s.activation.test(self.pid, True)
        with patch.object(self.s.profiles, 'respond', return_value='invalid SECRET-BODY'):
            self.assertFalse(self.s.agents.probe(self.pid, True)['passed'])
        with patch.object(self.s.profiles, 'respond', side_effect=AssistantFailure('FORBIDDEN', 'run_create', http_status=403)):
            self.assertFalse(self.s.activation.test(other, True)['passed'])
        self.assertEqual(self.rows()['chat']['status'], 'passed')
        self.assertEqual(self.rows()['work']['code'], 'FORMAT_ASSERTION')
        self.assertTrue(self.rows()['work']['can_retest'])
        self.assertEqual(self.rows(other)['chat']['code'], 'FORBIDDEN')
        self.assertFalse(self.rows(other)['chat']['can_retest'])
        self.s.close();self.s = WebSession(directory=self.root, config=copy.deepcopy(DEFAULT), start_scheduler=False);self.d = self.s.diagnostics
        with (patch.object(self.s.profiles, 'respond', side_effect=AssertionError('no model')),
              patch('httpx.Client.send', side_effect=AssertionError('no HTTP'))):
            before = self.s.profiles.snapshot(self.pid)
            self.assertEqual(self.rows()['chat']['status'], 'passed')
            report = self.d.report(profile_id=self.pid)['markdown']
            destination = self.root / 'repair.md';self.d.export(destination, profile_id=self.pid)
            self.assertEqual(destination.read_text('utf-8'), report)
            self.assertEqual(self.s.profiles.snapshot(self.pid), before)
            from desktop_app.support import export_bundle
            target = self.root / 'support.zip';export_bundle(self.root, target)
            with zipfile.ZipFile(target) as z:shared = ''.join(z.read(n).decode('utf-8') for n in z.namelist())
            for secret in ('SECRET-NAME', 'asst_SECRET_ID', 'secret-endpoint', 'SECRET-BODY', str(self.root)):
                self.assertNotIn(secret, report + shared)
        self.assertEqual(len(self.calls), 2)

    def test_safe_failure_categories_context_and_explicit_retest(self):
        for code, status in [('AUTHENTICATION', 401), ('FORBIDDEN', 403), ('NOT_FOUND', 404), ('RATE_LIMIT', 429), ('TIMEOUT', None), ('TRANSPORT', None), ('FORMAT', None)]:
            with self.subTest(code=code):
                pid = self.s.profiles.save(code, 'asst_' + code)
                with patch.object(self.s.profiles, 'respond', side_effect=AssistantFailure(code, 'run_poll', http_status=status)):
                    self.s.activation.test(pid, True)
                row = self.rows(pid)['chat'];self.assertEqual(row['code'], code);self.assertEqual(row['http_status'], status)
                self.assertRegex(row['incident'], '^[a-f0-9]{32}$')
        with patch.object(self.s.profiles, 'respond', return_value='wrong'):
            self.s.activation.test(self.pid, True)
        self.assertEqual(self.rows()['chat']['code'], 'CONTEXT_ASSERTION')
        rev = self.s.profiles.snapshot(self.pid)['revision']
        with patch.object(self.s.profiles, 'respond', side_effect=self.reply):
            with self.assertRaises(ValueError):self.d.retest(self.pid, rev, 'chat', False)
            self.d.retest(self.pid, rev, 'chat', True)
        self.assertEqual(len(self.calls), 2);self.assertEqual(self.rows()['chat']['status'], 'passed')
        with self.assertRaises(ValueError):self.d.retest(self.pid, rev + 1, 'chat', True)

    def test_cancel_running_guard_and_incomplete_reopen(self):
        entered = threading.Event();release = threading.Event();cancel = threading.Event();errors = []
        def provider(*args, **kwargs):entered.set();release.wait(5);return 'OK'
        def check():
            try:self.s.activation.test(self.pid, True, cancelled=cancel.is_set)
            except Exception as exc:errors.append(exc)
        with patch.object(self.s.profiles, 'respond', side_effect=provider):
            thread = threading.Thread(target=check);thread.start()
            try:
                self.assertTrue(entered.wait(3));row = self.rows()['chat']
                self.assertEqual(row['status'], 'running');self.assertFalse(row['can_retest'])
                cancel.set()
                with self.assertRaises(ValueError):self.s.activation.test(self.pid, True)
            finally:release.set();thread.join(5)
        self.assertFalse(errors);self.assertEqual(self.rows()['chat']['status'], 'cancelled')
        data = json.loads(self.d.path.read_text('utf-8'));row = data['profiles'][self.d.alias(self.pid)]['1']['chat']
        row.update(status='running', requests=[])
        self.d.path.write_text(json.dumps(data), 'utf-8')
        self.d = ConnectionDiagnostics(self.s)
        self.assertEqual(self.rows()['chat']['status'], 'incomplete');self.assertFalse(self.rows()['chat']['can_retest'])
        with self.assertRaises(ValueError):self.d.measure(self.pid, ['chat'], lambda: {}, None, 1)

    def test_version_retention_corruption_save_and_export_failures(self):
        for n in range(4):
            with patch.object(self.s.profiles, 'respond', side_effect=self.reply):self.s.activation.test(self.pid, True)
            if n < 3:self.s.profiles.save('SECRET-NAME', 'asst_revision_' + str(n), profile_id=self.pid)
        versions = self.d.data['profiles'][self.d.alias(self.pid)]
        self.assertEqual(len(versions), 2)
        self.s.profiles.save('SECRET-NAME', 'asst_new', profile_id=self.pid)
        self.assertEqual(self.rows()['chat']['status'], 'stale')
        self.d.path.write_text('{broken', 'utf-8');self.d = ConnectionDiagnostics(self.s)
        self.assertTrue(self.d.status(profile_id=self.pid)['warnings']);self.assertEqual(self.rows()['chat']['status'], 'not_tested')
        self.s.diagnostics = self.d
        with (patch('desktop_app.connection_diagnostics.os.replace', side_effect=OSError('SECRET-DISK')),
              patch.object(self.s.profiles, 'respond', side_effect=self.reply)):
            self.s.activation.test(self.pid, True)
        self.assertTrue(self.d.status(profile_id=self.pid)['warnings']);self.assertEqual(self.rows()['chat']['status'], 'passed')
        before = self.d.report(profile_id=self.pid)['markdown']
        with self.assertRaises(OSError):self.d.export(self.root / 'missing' / 'report.md', profile_id=self.pid)
        self.assertEqual(self.d.report(profile_id=self.pid)['markdown'], before)
        destination = self.root / 'existing.md';destination.write_text('original', 'utf-8')
        with self.assertRaises(FileExistsError):self.d.export(destination, profile_id=self.pid)
        self.assertEqual(destination.read_text('utf-8'), 'original')

    def test_untrusted_persistent_details_are_whitelisted_not_authority(self):
        with patch.object(self.s.profiles, 'respond', side_effect=self.reply):self.s.activation.test(self.pid, True)
        data = json.loads(self.d.path.read_text('utf-8'));row = data['profiles'][self.d.alias(self.pid)]['1']['chat']
        row.update(code='SECRET-KEY', stage='https://secret.internal/', incident='EMPLOYEE-SECRET', body='PRIVATE-CONTENT')
        data['profiles'][self.d.alias(self.pid)]['1']['autonomous'] = dict(row, status='passed')
        self.d.path.write_text(json.dumps(data), 'utf-8');self.d = ConnectionDiagnostics(self.s)
        report = self.d.report(profile_id=self.pid)['markdown']
        for secret in ('SECRET-KEY', 'secret.internal', 'EMPLOYEE-SECRET', 'PRIVATE-CONTENT'):self.assertNotIn(secret, report)
        self.assertEqual(self.rows()['autonomous']['status'], 'incomplete')
        self.assertIsNone(self.s.skills.proof(self.pid, 1))

    def test_dialogue_failure_keeps_draft_and_read_only_diagnostics_never_resend(self):
        t = self.s.dialogue.start('chat', f'company:{self.pid}:1');tid = t['id']
        with patch.object(self.s.profiles, 'respond', return_value='existing answer'):self.s.dialogue.send(tid, 'first private text', 'first')
        with patch.object(self.s.profiles, 'respond', side_effect=AssistantFailure('TIMEOUT', 'run_poll')):
            with self.assertRaises(AssistantFailure):self.s.dialogue.send(tid, 'PRIVATE-DRAFT', 'failed')
        before = self.s.dialogue.state(tid)
        self.assertEqual(before['request']['pending_text'], 'PRIVATE-DRAFT')
        api = WebBridge(self.s)
        with patch.object(self.s.profiles, 'respond', side_effect=AssertionError('must not send')) as spy:
            state = api.call('diagnostics_status', {'thread_id': tid})['data']
            self.assertEqual(state['request']['code'], 'TIMEOUT');self.assertTrue(state['request']['incident'])
            self.assertFalse(any(r['can_retest'] for r in state['rows']))
            report = api.call('diagnostics_report', {'thread_id': tid})['data']['markdown']
            self.assertNotIn('PRIVATE-DRAFT', report);self.assertNotIn('first private text', report)
            self.assertFalse(api.call('diagnostics_retest', {'profile_id': self.pid, 'revision': 1, 'check': 'chat', 'consent': True})['ok'])
            self.assertFalse(api.call('diagnostics_report', {'thread_id': tid, 'path': 'arbitrary'})['ok']);spy.assert_not_called()
        self.assertEqual(self.s.dialogue.state(tid)['messages'], before['messages'])
        self.assertEqual(self.s.dialogue.state(tid)['request'], before['request'])
