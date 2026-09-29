import json
import tempfile
import unittest
import threading
from pathlib import Path
from unittest.mock import Mock
from desktop_app.profiles import Profiles
from desktop_app.company_readiness import inspect_company


class CompanyReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=Profiles(Path(self.tmp.name)/'assistants.json',vault=Mock())
        self.p.data['api_key_env']='QA_READINESS_UNSET_TEST_VARIABLE'
        self.p.key=Mock(side_effect=AssertionError('no secret reads'))
        self.p.respond=Mock(side_effect=AssertionError('no remote calls'))
    def tearDown(self):self.tmp.cleanup()
    def setup_company(self):
        self.p.set_endpoint('https://synthetic-private.example.test/v1')
        self.p.set_wire_mode('assistants')
        self.p.data['credential_source']='keyring'
        return self.p.save('PRIVATE-NAME','PRIVATE-ID','PRIVATE-NOTES')
    def test_empty_gives_concrete_next_step_without_writes_or_calls(self):
        before=json.dumps(self.p.data)
        result=inspect_company(self.p)
        self.assertFalse(result['ready_for_company_test'])
        self.assertEqual(result['checks'][0]['state'],'missing')
        self.assertEqual(before,json.dumps(self.p.data))
        self.assertFalse(self.p.path.exists())
        self.p.key.assert_not_called();self.p.respond.assert_not_called()
    def test_configured_is_only_ready_to_test_and_report_is_whitelisted(self):
        self.setup_company();result=inspect_company(self.p)
        self.assertTrue(result['ready_for_company_test'])
        self.assertEqual(result['company_services'],'not_tested')
        text=json.dumps(result)
        for secret in ('PRIVATE-NAME','PRIVATE-ID','PRIVATE-NOTES','synthetic-private',self.p.data['credential_id']):self.assertNotIn(secret,text)
        self.assertEqual(next(c for c in result['checks'] if c['id']=='credential')['state'],'not_tested')
        self.p.key.assert_not_called();self.p.respond.assert_not_called()
    def test_declared_roles_are_not_verified_and_disabled_not_counted(self):
        pid=self.setup_company();self.p.set_workflow_capability(pid,['planner'])
        result=inspect_company(self.p)
        self.assertEqual(next(c for c in result['checks'] if c['id']=='role_planner')['state'],'not_tested')
        self.p.save('name','PRIVATE-ID',profile_id=pid,enabled=False)
        self.assertFalse(inspect_company(self.p)['ready_for_company_test'])
    def test_changed_endpoint_revokes_role_readiness(self):
        pid=self.setup_company();self.p.set_workflow_capability(pid,['planner'],True,'synthetic-test-evidence-only')
        self.assertEqual(next(c for c in inspect_company(self.p)['checks'] if c['id']=='role_planner')['state'],'ready')
        self.p.set_endpoint('https://changed.example.test/v1')
        self.assertEqual(next(c for c in inspect_company(self.p)['checks'] if c['id']=='role_planner')['state'],'not_tested')
    def test_trial_does_not_read_company_profiles(self):
        result=inspect_company(None,trial=True)
        self.assertFalse(result['ready_for_company_test'])
        self.assertIn('start-app.bat',result['next_step'])

    def test_company_probe_serializes_requests_and_close_fences_result(self):
        from desktop_app.company_readiness import CompanyProbe
        pid=self.setup_company();entered=threading.Event();release=threading.Event();errors=[]
        def remote(binding):entered.set();release.wait(3);return {'connection':'passed'}
        self.p.inspect_assistant=remote;probe=CompanyProbe(self.p)
        def work():
            try:probe.inspect(pid)
            except ValueError as e:errors.append(str(e))
        worker=threading.Thread(target=work);worker.start();self.assertTrue(entered.wait(2))
        try:
            self.assertTrue(probe.has_inflight())
            with self.assertRaises(ValueError):probe.inspect(pid)
            probe.close(wait=False)
        finally:release.set();worker.join(3)
        self.assertFalse(probe.has_inflight());self.assertEqual(len(errors),1)

    def test_bridge_state_available_while_probe_waits_and_setting_changes_blocked(self):
        from desktop_app.web_session import WebSession
        from desktop_app.web_bridge import WebBridge
        with tempfile.TemporaryDirectory() as directory:
            s=WebSession(directory=directory);api=WebBridge(s)
            pid=s.profiles.save('synthetic','asst_synthetic');entered=threading.Event();release=threading.Event()
            def remote(binding):entered.set();release.wait(3);return {'connection':'passed','tools':[],'search':'not_tested'}
            s.profiles.inspect_assistant=remote;results=[]
            worker=threading.Thread(target=lambda:results.append(api.call('company_probe',{'profile_id':pid})))
            worker.start();self.assertTrue(entered.wait(2))
            try:
                self.assertTrue(api.call('state')['ok'])
                self.assertFalse(api.call('profile_default',{'id':pid})['ok'])
            finally:release.set();worker.join(3);s.close()
            self.assertTrue(results[0]['ok'])
