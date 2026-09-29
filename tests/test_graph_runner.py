import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from desktop_app.graph_runner import execute
from desktop_app.core import Engine, dumps
from desktop_app.workflows import WorkflowService
from tests import test_workflows as fixtures


class GraphCheckpointTests(unittest.TestCase):
    def test_end_checkpoint_missing_store_receipt_stops_without_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'checkpoint.db';steps=[{'id':'a'},{'id':'b'}];calls=[]
            execute(path,'task',steps,lambda s:calls.append(s['id']))
            with self.assertRaisesRegex(ValueError,'不一致'):
                execute(path,'task',steps,lambda s:calls.append(s['id']),receipts={'b'})
            self.assertEqual(calls,['a','b'])

    def test_resume_failed_node_does_not_replay_committed_predecessor(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'checkpoint.db';calls=[];receipts=set()
            def run(step):
                sid=step['id']
                if sid in receipts:return
                calls.append(sid)
                if sid=='b' and calls.count('b')==1:raise ValueError('synthetic interruption')
                receipts.add(sid)
            steps=[{'id':'a'},{'id':'b'}]
            with self.assertRaises(ValueError):execute(path,'task',steps,run)
            execute(path,'task',steps,run)
            execute(path,'task',steps,run)
            self.assertEqual(calls,['a','b','b'])

    def test_completed_receipt_prevents_repeat_after_checkpoint_write_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'checkpoint.db';receipts=set();calls=[]
            def run(step):
                if step['id'] in receipts:return
                calls.append(step['id']);receipts.add(step['id'])
                raise ValueError('crash after committed output before checkpoint')
            with self.assertRaises(ValueError):execute(path,'task',[{'id':'a'}],run)
            execute(path,'task',[{'id':'a'}],run)
            self.assertEqual(calls,['a'])


class WorkflowRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.WorkflowTests();self.f.setUp()
    def tearDown(self):self.f.tearDown()

    def prepare_interrupted(self,started=False):
        f=self.f;r=f.ready();spec={'id':r['id'],'revision':r['revision'],'goal':r['goal'],'planner':r['planner'],'steps':r['steps']}
        with f.store.connection() as db:
            tid,_=f.service._insert_task(db,spec,'crash-test')
            if started:db.execute("UPDATE workflow_steps SET input='{}' WHERE task_id=? AND position=0",(tid,))
        f.engine.close(wait=True)
        with f.store.connection() as db:
            db.execute("UPDATE tasks SET state='running' WHERE id=?",(tid,))
            db.execute("UPDATE workflow_steps SET state='queued' WHERE task_id=?",(tid,))
        f.engine=Engine(f.store,f.query,None,query_validator=f.queries.validate,query_catalog=f.queries.catalog)
        f.service=WorkflowService(f.engine,f.profiles)
        return tid

    def test_restart_no_dispatch_and_explicit_resume_once(self):
        tid=self.prepare_interrupted();f=self.f
        self.assertTrue(f.service.recovery(tid)['eligible']);self.assertFalse(f.query_calls)
        f.service.resume(tid)
        self.assertEqual(f.wait(tid)['state'],'succeeded')
        with self.assertRaises(ValueError):f.service.resume(tid)
        self.assertEqual(len(f.query_calls),1)

    def test_checkpoint_failure_preserves_receipt_and_resume_skips_query(self):
        f=self.f
        def broken_checkpoint(path,tid,steps,dispatch,**kwargs):
            dispatch(steps[0])
            raise OSError('synthetic checkpoint failure')
        with patch('desktop_app.graph_runner.execute',side_effect=broken_checkpoint):
            tid=f.approve(f.ready())
            failed=f.wait(tid)
        self.assertEqual(failed['state'],'failed')
        self.assertIn('WORKFLOW_RECOVERY_REQUIRED',failed['error'])
        self.assertEqual(f.service.get_task_steps(tid)[0]['state'],'succeeded')
        self.assertTrue(f.service.recovery(tid)['eligible'])
        f.service.resume(tid)
        self.assertEqual(f.wait(tid)['state'],'succeeded')
        self.assertEqual(len(f.query_calls),1)
        self.assertEqual([call[1] for call in f.calls],['analysis','review','compose'])

    def test_uncertain_query_never_replayed(self):
        tid=self.prepare_interrupted(True)
        with self.assertRaises(ValueError):self.f.service.resume(tid)
        self.assertFalse(self.f.query_calls)

    def test_abandon_cannot_resume(self):
        tid=self.prepare_interrupted();self.f.service.abandon(tid)
        with self.assertRaises(ValueError):self.f.service.resume(tid)
        self.assertEqual(self.f.store.task(tid)['state'],'cancelled')

    def test_binding_change_blocks_recovery(self):
        tid=self.prepare_interrupted()
        with patch.object(self.f.profiles,'validate_workflow',side_effect=ValueError('changed')):
            with self.assertRaises(ValueError):self.f.service.resume(tid)
        self.assertFalse(self.f.query_calls)
