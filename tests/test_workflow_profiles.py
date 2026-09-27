import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from desktop_app.profiles import Profiles


class WorkflowProfilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Profiles(Path(self.tmp.name)/'profiles.json',vault=Mock())
        self.a=self.p.save('分析','company-analysis');self.b=self.p.save('覆核','company-review')

    def tearDown(self):self.tmp.cleanup()

    def test_unverified_catalog_and_roles(self):
        self.assertEqual(self.p.workflow_catalog(),[])
        with self.assertRaises(ValueError):self.p.workflow_binding(self.a)
        with self.assertRaises(ValueError):self.p.set_workflow_capability(self.a,['analysis'],True)
        self.p.set_workflow_capability(self.a,['analysis'],True,'synthetic-test-evidence')
        binding=self.p.workflow_binding(self.a);self.p.validate_workflow(binding,'analysis')
        with self.assertRaises(ValueError):self.p.validate_workflow(binding,'planner')
        self.p.set_workflow_capability(self.a,['analysis'],False)
        with self.assertRaises(ValueError):self.p.validate_workflow(binding,'analysis')

    def test_assistant_id_endpoint_disable_invalidate_capability(self):
        self.p.set_workflow_capability(self.a,['analysis'],True,'synthetic-evidence')
        binding=self.p.workflow_binding(self.a)
        self.p.save('新名稱','company-analysis','描述',self.a)
        self.assertEqual(self.p.workflow_binding(self.a),binding)
        self.p.save('新名稱','new-id','描述',self.a)
        self.assertEqual(self.p.workflow_catalog(),[])
        self.p.set_workflow_capability(self.a,['analysis'],True,'synthetic-evidence-2')
        self.p.set_endpoint('https://company.example.test/api')
        self.assertEqual(self.p.workflow_catalog(),[])

    def test_different_ids_and_roles_are_routed_stateless(self):
        self.p.set_workflow_capability(self.a,['analysis'],True,'fixture')
        self.p.set_workflow_capability(self.b,['review'],True,'fixture')
        self.p.respond=Mock(return_value='{"text":"synthetic","facts":{}}')
        messages=[{'role':'user','content':'synthetic only'}]
        for run in ('run-one','run-two'):
            for pid,role in ((self.a,'analysis'),(self.b,'review')):
                self.p.workflow_call(copy.deepcopy(messages),role,self.p.workflow_binding(pid),{'run_id':run,'step_id':role})
        calls=self.p.respond.call_args_list
        self.assertEqual([c.args[2]['profile_id'] for c in calls],[self.a,self.b,self.a,self.b])
        self.assertTrue(all(c.args[0]==messages and c.args[1]=='workflow_step' for c in calls))
        with self.assertRaises(ValueError):self.p.workflow_call(messages,'analysis',self.p.workflow_binding(self.a),{})


if __name__=='__main__':unittest.main()
