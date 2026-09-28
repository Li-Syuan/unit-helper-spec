import copy
import json
import sqlite3
import unittest
from unittest.mock import patch
from desktop_app.core import Store
from desktop_app.outcomes import OutcomeService
from tests import test_workflows as fixtures


class OutcomeTests(unittest.TestCase):
    setUp=fixtures.WorkflowTests.setUp
    tearDown=fixtures.WorkflowTests.tearDown
    query=fixtures.WorkflowTests.query
    call=fixtures.WorkflowTests.call
    steps=fixtures.WorkflowTests.steps
    ready=fixtures.WorkflowTests.ready
    approve=fixtures.WorkflowTests.approve
    wait=fixtures.WorkflowTests.wait

    def run_pair(self):
        record=self.ready();first=self.approve(record);self.wait(first)
        sid=self.service.schedule(record['id'],record['revision'],'日報','daily','08:00',consent=True)
        a=self.engine.run_schedule_now(sid,'a');self.wait(a)
        b=self.engine.run_schedule_now(sid,'b');self.wait(b)
        return OutcomeService(self.service),a,b

    def test_compare_exact_and_same_period_without_dispatch(self):
        service,a,b=self.run_pair();calls=len(self.calls)
        compared=service.compare(b)
        self.assertEqual(compared['baseline_id'],a)
        self.assertTrue(compared['groups'][0]['same_period'])
        self.assertTrue(all(row[3] in ('0','0.0','0.00') for row in compared['groups'][0]['rows']))
        self.assertEqual(len(self.calls),calls)

    def test_feedback_upsert_clear_and_no_dispatch(self):
        service,a,b=self.run_pair();calls=len(self.calls)
        service.save_feedback(b,'usable','精確');service.save_feedback(b,'revise','待修改')
        self.assertEqual(service.feedback(b)['rating'],'revise')
        with self.store.connection() as db:self.assertEqual(db.execute('SELECT count(*) FROM outcome_feedback').fetchone()[0],1)
        service.clear_feedback(b);self.assertIsNone(service.feedback(b));self.assertEqual(len(self.calls),calls)

    def test_invalid_feedback_and_running_rejected(self):
        service,a,b=self.run_pair()
        for rating,note in [('bad',''),('usable','x'*2001)]:
            with self.assertRaises(ValueError):service.save_feedback(b,rating,note)
        with self.store.connection() as db:db.execute("UPDATE tasks SET state='running' WHERE id=?",(b,))
        with self.assertRaises(ValueError):service.save_feedback(b,'usable')

    def test_revision_and_schedule_isolation(self):
        service,a,b=self.run_pair()
        task=self.store.task(b);task['payload']['workflow']['revision']+=1
        with self.store.connection() as db:db.execute('UPDATE tasks SET payload=? WHERE id=?',(json.dumps(task['payload']),b))
        self.assertIsNone(service.compare(b)['baseline_id'])
        task['payload']['workflow']['revision']-=1
        with self.store.connection() as db:db.execute('UPDATE tasks SET payload=?,schedule_id=NULL WHERE id=?',(json.dumps(task['payload']),b))
        self.assertNotEqual(service.compare(b)['baseline_id'],a)

    def test_bad_query_snapshot_not_compared(self):
        service,a,b=self.run_pair()
        for change in ('empty','truncated','null','columns'):
            row=self.service.get_task_steps(b)[0];original=copy.deepcopy(row['output']);value=copy.deepcopy(original)
            result=value['query_result']
            if change=='empty':result['rows']=[]
            elif change=='truncated':result['truncated']=True
            elif change=='columns':result['columns'][0]['label']='changed'
            else:
                result['rows']=[{c['name']:None for c in result['columns']}]
            with self.store.connection() as db:db.execute('UPDATE workflow_steps SET output=? WHERE task_id=? AND step_id=?',(json.dumps(value),b,row['step_id']))
            self.assertTrue(service.compare(b)['groups'][0]['reason'])
            with self.store.connection() as db:db.execute('UPDATE workflow_steps SET output=? WHERE task_id=? AND step_id=?',(json.dumps(original),b,row['step_id']))

    def test_partial_and_source_deletion_preserves_feedback(self):
        self.needs_attention=True;r=self.ready();tid=self.approve(r);self.wait(tid)
        service=OutcomeService(self.service);outcome=service.read(tid)
        self.assertTrue(outcome['partial']);self.assertTrue(outcome['can_rate']);self.assertEqual(outcome['review'],'覆核需要處理')
        service.save_feedback(tid,'revise')
        preview=self.engine.preview_conversation_deletion([self.cid]);self.engine.delete_conversations(preview['token'])
        self.assertEqual(service.feedback(tid)['rating'],'revise')

    def test_schema_five_backup_and_transaction_rollback(self):
        with self.store.connection() as db:
            db.execute('DROP TABLE outcome_feedback');db.execute('PRAGMA user_version=5')
        def fail(db):
            db.execute('CREATE TABLE failed_marker(x)');raise RuntimeError('migration failed')
        with patch('desktop_app.outcomes.initialize_outcome_schema',side_effect=fail):
            with self.assertRaises(RuntimeError):Store(self.path)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],5)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='failed_marker'").fetchone())
        Store(self.path)
        backups=list(self.path.parent.glob('*.pre-v6-*.bak'));self.assertTrue(backups)
        with sqlite3.connect(backups[0]) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],5)

    def test_failed_save_keeps_previous_feedback(self):
        service,a,b=self.run_pair();service.save_feedback(b,'usable','original')
        with patch.object(service,'read',side_effect=RuntimeError('unavailable')):
            with self.assertRaises(RuntimeError):service.save_feedback(b,'revise')
        self.assertEqual(service.feedback(b)['note'],'original')

    def test_high_precision_and_date_modes(self):
        service,a,b=self.run_pair()
        for tid,value,date in [(a,'123456789012345678901234567890.123456789','2026-09-20'),
                               (b,'123456789012345678901234567890.123456790','2026-09-21')]:
            row=self.service.get_task_steps(tid)[0];output=row['output']
            output['query_result'].update(columns=[{'name':'amount','type':'decimal'}],rows=[[value]],parameters={'from_date':date})
            task=self.store.task(tid);task['payload']['workflow']['steps'][0]['parameters']['from_date']=date
            with self.store.connection() as db:
                db.execute('UPDATE workflow_steps SET output=? WHERE task_id=? AND step_id=?',(json.dumps(output),tid,row['step_id']))
                db.execute('UPDATE tasks SET payload=? WHERE id=?',(json.dumps(task['payload']),tid))
        comp=service.compare(b);self.assertEqual(comp['baseline_id'],a)
        self.assertFalse(comp['groups'][0]['same_period'])
        self.assertEqual(comp['groups'][0]['rows'][1][3],'0.000000001')
        for tid in (a,b):
            task=self.store.task(tid);task['payload']['workflow']['steps'][0]['date_mode']='literal'
            with self.store.connection() as db:db.execute('UPDATE tasks SET payload=? WHERE id=?',(json.dumps(task['payload']),tid))
        self.assertIsNone(service.compare(b)['baseline_id'])

    def test_changed_binding_and_nondate_parameter_not_compared(self):
        service,a,b=self.run_pair();original=self.store.task(b)['payload']
        for mode in ('binding','category'):
            payload=copy.deepcopy(original)
            if mode=='binding':payload['workflow']['planner']['revision']+=1
            else:payload['workflow']['steps'][0]['parameters']['category']='B'
            with self.store.connection() as db:db.execute('UPDATE tasks SET payload=? WHERE id=?',(json.dumps(payload),b))
            self.assertIsNone(service.compare(b)['baseline_id'])

    def test_feedback_cascades_with_task_deletion(self):
        service,a,b=self.run_pair();service.save_feedback(b,'usable')
        with self.store.connection() as db:
            db.execute('DELETE FROM workflow_steps WHERE task_id=?',(b,))
            db.execute('DELETE FROM occurrences WHERE task_id=?',(b,))
            db.execute('DELETE FROM tasks WHERE id=?',(b,))
            self.assertEqual(db.execute('SELECT count(*) FROM outcome_feedback WHERE task_id=?',(b,)).fetchone()[0],0)

    def test_schedule_retry_keeps_comparison_scope(self):
        service,a,b=self.run_pair();sid=self.store.task(b)['schedule_id']
        self.fail_role='review';failed=self.engine.run_schedule_now(sid,'failed');self.wait(failed)
        self.fail_role=None;retry=self.service.retry(failed,'retry');self.wait(retry)
        self.assertIsNone(self.store.task(retry)['schedule_id'])
        self.assertEqual(service.compare(retry)['baseline_id'],b)
