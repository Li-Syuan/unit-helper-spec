import copy
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_app.config import DEFAULT
from desktop_app.core import Store
from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge
from desktop_app.work_orders import validate_answers

ANSWERS={'scope':'台股＋美股＋重大總經新聞','sources':'公開可靠新聞','time_hhmm':'08:00'}
TOOL={'name':'internet_search','parameters':{'type':'object','properties':{'query':{'type':'string'}},'required':['query'],'additionalProperties':False}}


class WorkOrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=WebSession(directory=self.tmp.name,config=copy.deepcopy(DEFAULT),start_scheduler=False)
        self.o=self.s.orders;self.api=WebBridge(self.s)

    def tearDown(self):self.s.close();self.tmp.cleanup()

    def company(self):
        p=self.s.profiles;p.set_endpoint('https://synthetic.example.test/v1');p.set_wire_mode('assistants')
        pid=p.save('合成搜尋助理','asst_synthetic')
        p.set_search_policy(p.snapshot(pid),{'tools':[TOOL]})
        return pid

    def ready(self,pid='demo'):
        r=self.o.create(pid,'每天八點做日報')
        return self.o.edit(r['id'],r['revision'],ANSWERS)

    def wait(self):
        deadline=time.monotonic()+8
        while self.s.engine.has_inflight() and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(self.s.engine.has_inflight())

    def trial(self,r):
        p=self.o.preview(r['id'],r['revision']);result=self.o.trial(r['id'],p['token']);self.wait()
        return self.o.state(r['id']),p

    def test_demo_questions_edit_and_trial_are_isolated_and_idempotent(self):
        with patch('httpx.Client.send',side_effect=AssertionError('network')):
            r=self.o.create('demo','每天08:00，台股美股新聞')
            r=self.o.discuss(r['id'],r['revision'],r['goal'])
            self.assertEqual([q['id'] for q in r['questions']],['sources'])
            self.assertFalse(self.s.store.tasks());self.assertFalse(self.s.store.schedules())
            r=self.o.edit(r['id'],r['revision'],ANSWERS)
            result,p=self.trial(r)
            self.assertEqual(self.o.trial(r['id'],p['token'])['task_id'],result['task_id'])
            self.assertEqual(len(self.s.store.tasks()),1)
            self.assertIn('離線示範',result['task']['result']['text'])
            with self.assertRaises(ValueError):self.o.schedule_preview(r['id'],r['revision'])

    def test_company_two_confirmations_binding_and_atomic_schedule(self):
        pid=self.company();r=self.ready(pid)
        with patch.object(self.s.engine,'assistant_router',return_value='合成回覆，無真實新聞') as respond:
            result,p=self.trial(r)
        self.assertEqual(result['task']['state'],'succeeded')
        self.assertFalse(self.s.store.schedules())
        preview=self.o.schedule_preview(r['id'],r['revision'])
        for reviewed,consent in ((False,True),(True,False),(1,True)):
            with self.assertRaises(ValueError):self.o.enable(r['id'],preview['token'],reviewed,consent)
        with patch.object(self.o,'_write',side_effect=sqlite3.OperationalError('injected')):
            with self.assertRaises(sqlite3.OperationalError):self.o.enable(r['id'],preview['token'],True,True)
        self.assertFalse(self.s.store.schedules())
        enabled=self.o.enable(r['id'],preview['token'],True,True)
        self.assertEqual(self.o.enable(r['id'],preview['token'],True,True)['schedule_id'],enabled['schedule_id'])
        self.assertEqual(len(self.s.store.schedules()),1)
        self.assertFalse(self.o.pause(r['id'])['schedule']['enabled'])
        self.assertEqual(respond.call_count,1)

    def test_revision_expiry_policy_and_unknown_fields_rejected(self):
        r=self.ready();p=self.o.preview(r['id'],r['revision'])
        self.o.edit(r['id'],r['revision'],dict(ANSWERS,time_hhmm='09:00'))
        with self.assertRaises(ValueError):self.o.trial(r['id'],p['token'])
        r=self.o.state(r['id']);p=self.o.preview(r['id'],r['revision'])
        self.o.tokens[p['token']]['expires']=0
        with self.assertRaises(ValueError):self.o.trial(r['id'],p['token'])
        for bad in ({'command':'whoami'},dict(ANSWERS,time_hhmm='24:00'),{'scope':True}):
            with self.assertRaises(ValueError):validate_answers(bad)
        pid=self.company();r=self.ready(pid);p=self.o.preview(r['id'],r['revision'])
        self.s.profiles.set_search_policy(self.s.profiles.snapshot(pid),None)
        with self.assertRaises(ValueError):self.o.trial(r['id'],p['token'])
        self.assertFalse(self.s.store.tasks())

    def test_planning_structured_contract_tool_disable_and_failure_keeps_input(self):
        r=self.o.create(self.company(),'請整理日報')
        with patch.object(self.s.profiles,'respond',return_value=json.dumps({'message':'請核對','answers':ANSWERS})) as call:
            r=self.o.discuss(r['id'],r['revision'],'每日08:00，公開新聞，台股美股總經')
        self.assertEqual(call.call_args.args[1],'workflow_plan')
        self.assertFalse(call.call_args.kwargs['context']['search_authorized'])
        self.assertEqual(r['state'],'ready');self.assertFalse(self.s.store.tasks())
        with patch.object(self.s.profiles,'respond',return_value='{"message":"run","answers":{},"execute":true}'):
            failed=self.o.discuss(r['id'],r['revision'],'其他要求')
        self.assertEqual(failed['state'],'failed');self.assertEqual(failed['answers'],ANSWERS)
        self.assertIn('其他要求',failed['discussion'][-1]['content'])
        with self.assertRaises(ValueError):self.o.discuss(failed['id'],failed['revision'],'retry')

    def test_cancel_late_proposal_and_pending_profile_mutation_guard(self):
        r=self.o.create(self.company(),'日報');gate=threading.Event();entered=threading.Event()
        def reply(*a,**kw):
            entered.set();gate.wait(5)
            return json.dumps({'message':'late','answers':ANSWERS})
        with patch.object(self.s.profiles,'respond',side_effect=reply):
            t=threading.Thread(target=lambda:self.o.discuss(r['id'],r['revision'],'08:00'))
            t.start()
            try:
                self.assertTrue(entered.wait(3));self.assertTrue(self.s.engine.has_inflight())
                result=self.api.call('profile_roles',{'id':r['binding']['profile_id'],'roles':['planner']})
                self.assertFalse(result['ok'])
                cancelled=self.o.cancel(r['id'])
            finally:gate.set();t.join(6)
        self.assertEqual(self.o.state(r['id'])['answers'],{})
        self.assertEqual(self.o.state(r['id'])['revision'],cancelled['revision'])

    def test_trial_insert_and_link_roll_back_together_and_reopen_no_replay(self):
        r=self.ready();p=self.o.preview(r['id'],r['revision'])
        with patch.object(self.o,'_write',side_effect=sqlite3.OperationalError('injected')):
            with self.assertRaises(sqlite3.OperationalError):self.o.trial(r['id'],p['token'])
        self.assertFalse(self.s.store.tasks())
        result,_=self.trial(r)
        self.s.close();self.s=WebSession(directory=self.tmp.name,start_scheduler=False);self.o=self.s.orders
        self.assertEqual(self.o.state(r['id'])['task_id'],result['task_id'])
        self.assertEqual(len(self.s.store.tasks()),1)

    def test_recovery_uses_same_planning_receipt_and_does_not_retry_unknown(self):
        r=self.o.create(self.company(),'日報')
        with patch.object(self.s.profiles,'respond',side_effect=TimeoutError('PRIVATE')):
            r=self.o.discuss(r['id'],r['revision'],'明天08:00')
        rid=r['planning_request']
        with patch.object(self.s.profiles,'inspect_request',return_value={'state':'unknown','recoverable':False}):
            with self.assertRaises(ValueError):self.o.recover(r['id'])
        with patch.object(self.s.profiles,'inspect_request',return_value={'state':'completed','recoverable':True}),patch.object(self.s.profiles,'respond',return_value=json.dumps({'message':'已取回','answers':ANSWERS})) as call:
            result=self.o.recover(r['id'])
        self.assertTrue(call.call_args.kwargs['context']['resume'])
        self.assertEqual(call.call_args.kwargs['context']['request_id'],rid)
        self.assertEqual(result['state'],'ready');self.assertFalse(self.s.store.tasks())

    def test_schema6_backup_and_failed_migration_transaction(self):
        path=Path(self.tmp.name)/'migration.sqlite3';s=Store(path);cid=s.create_conversation('preserved')
        with s.connection() as db:db.execute('DROP TABLE work_orders');db.execute('PRAGMA user_version=6')
        def failure(db):
            db.execute('CREATE TABLE work_orders(id TEXT)');raise sqlite3.OperationalError('injected')
        with patch('desktop_app.work_orders.initialize_order_schema',side_effect=failure):
            with self.assertRaises(sqlite3.OperationalError):Store(path)
        with s.connection() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],6)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='work_orders'").fetchone())
        migrated=Store(path)
        self.assertEqual(migrated.conversation(cid)['title'],'preserved')
        with migrated.connection() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],7)
        for backup in path.parent.glob('migration.sqlite3.pre-v7-*.bak'):
            with sqlite3.connect(backup) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],6)
