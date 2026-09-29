import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from desktop_app.profiles import Profiles


class AssistantsProfilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Profiles(Path(self.tmp.name)/'profiles.json', vault=Mock())
        self.p.set_endpoint('https://fixture.example.test/v1')
        self.pid = self.p.save('測試助理', 'asst_synthetic')

    def tearDown(self):
        self.tmp.cleanup()

    def test_mapping_invalidates_bindings_and_capabilities_once(self):
        self.p.set_workflow_capability(self.pid, ['analysis'], True, 'synthetic evidence')
        before = self.p.snapshot(self.pid)
        self.p.set_wire_mode('assistants')
        self.assertEqual(self.p.snapshot(self.pid)['revision'], before['revision']+1)
        self.assertEqual(self.p.workflow_catalog(), [])
        with self.assertRaises(ValueError):
            self.p.validate(before)
        after = self.p.snapshot(self.pid)
        self.p.set_wire_mode('assistants')
        self.assertEqual(self.p.snapshot(self.pid), after)
        reloaded = Profiles(self.p.path, vault=Mock())
        self.assertEqual(reloaded.data['wire_mode'], 'assistants')

    def test_context_forwarding_workflow_and_regular(self):
        self.p.set_wire_mode('assistants')
        self.p.key = Mock(return_value='synthetic-key')
        client = Mock()
        self.p._assistants_client = Mock(return_value=client)
        messages = [{'role':'user', 'content':'synthetic'}]
        context = {'conversation_id':'c', 'request_id':'r'}
        self.p.respond(messages, 'chat', self.p.snapshot(self.pid), context=context)
        client.respond.assert_called_with(messages, 'chat', context=context)
        self.p.set_workflow_capability(self.pid, ['analysis'], True, 'fixture')
        ctx = {'run_id':'run', 'step_id':'analysis'}
        self.p.workflow_call(messages, 'analysis', self.p.workflow_binding(self.pid), ctx)
        client.respond.assert_called_with(messages, 'workflow_step', context=ctx)

    def test_local_inspect_requires_no_key_or_network(self):
        self.p.set_wire_mode('assistants')
        self.p.key = Mock(side_effect=AssertionError('should not read key'))
        self.assertEqual(self.p.inspect_request(self.p.snapshot(self.pid), {'run_id':'r','step_id':'s'})['state'], 'not_found')


if __name__ == '__main__':
    unittest.main()
