import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock,patch
from desktop_app.core import Store
from desktop_app.gateways import DemoQueries,GatewayError
from desktop_app.report_engine import ReportEngine,REPORT_BINDING
from desktop_app.conversation_actions import ActionService,initialize_action_schema
from desktop_app.intent_drafts import example_query,extract_action,intent_hint,can_parse_actions


class ActionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'test.db';self.store=Store(self.path)
        self.cid=self.store.create_conversation('測試',REPORT_BINDING);self.queries=DemoQueries()
        self.query_calls=[];self.ai_calls=[];self.gate=threading.Event();self.gate.set();self.valid=True
        def run(q,p):self.query_calls.append((q,p));self.gate.wait(4);return self.queries.run(q,p)
        def respond(m,p,b):self.ai_calls.append(m);return '合成摘要'
        def validate(b):
            if not self.valid:raise ValueError('binding changed')
        self.engine=ReportEngine(self.store,run,None,query_validator=self.queries.validate,query_catalog=self.queries.catalog,
            assistant_router=respond,binding_validator=validate)
        self.actions=ActionService(self.engine)

    def tearDown(self):
        self.gate.set();self.engine.close(wait=True);self.temp.cleanup()

    def create(self,kind='query'):
        spec=example_query()
        if kind!='query':spec.update(name='每日測試',frequency='daily',weekday=0,time_hhmm='08:00',date_mode='previous_day')
        return self.actions.create(self.cid,kind,'測試需求',spec)

    def confirm(self,a,consent=False):
        self.assertTrue(self.actions.preview(a['id'],a['revision'])['ready'])
        return self.actions.confirm(a['id'],a['revision'],consent)

    def wait(self,tid):
        until=time.monotonic()+5
        while self.store.task(tid)['state'] in {'queued','running'} and time.monotonic()<until:time.sleep(.01)
        self.assertIn(self.store.task(tid)['state'],{'succeeded','failed','cancelled'})
        return self.store.task(tid)

    def test_preview_query_confirmation_double_click_and_model_isolation(self):
        a=self.create();self.assertTrue(self.actions.preview(a['id'],1)['ready'])
        self.assertEqual(self.create()['id'],a['id'])
        self.assertEqual(self.store.tasks(),[]);self.assertEqual(self.query_calls,[])
        a=self.actions.confirm(a['id'],1);self.wait(a['task_id'])
        self.assertEqual(self.actions.confirm(a['id'],1)['task_id'],a['task_id'])
        self.assertEqual(len(self.query_calls),1);self.assertEqual(self.ai_calls,[])
        self.assertEqual(self.store.messages(self.cid),[])
        self.assertIsNone(self.store.task(a['task_id'])['conversation_id'])
        self.assertEqual(self.actions.snapshot(a['id'])['status'],'succeeded')

    def test_incomplete_unknown_and_modified_preview(self):
        a=self.actions.create(self.cid,'query','查資料',{})
        self.assertFalse(self.actions.preview(a['id'],1)['ready'])
        with self.assertRaises(ValueError):self.actions.confirm(a['id'],1)
        with self.assertRaises(ValueError):self.actions.update(a['id'],1,{'sql':'x'})
        a=self.actions.update(a['id'],1,example_query());self.assertTrue(self.actions.preview(a['id'],2)['ready'])
        updated=copy.deepcopy(a['spec']);updated['parameters']['category']='B'
        self.actions.update(a['id'],2,updated)
        with self.assertRaises(ValueError):self.actions.confirm(a['id'],2)
        with self.assertRaises(ValueError):self.actions.confirm(a['id'],3)

    def test_preview_expiry_and_binding(self):
        a=self.create()
        with patch('desktop_app.conversation_actions.time.monotonic',return_value=10):self.actions.preview(a['id'],1)
        with patch('desktop_app.conversation_actions.time.monotonic',return_value=611),self.assertRaises(ValueError):self.actions.confirm(a['id'],1)
        self.actions.preview(a['id'],1);self.valid=False
        with self.assertRaises(ValueError):self.actions.confirm(a['id'],1)
        self.assertFalse(self.store.tasks())

    def test_schedule_confirmation_atomic_pause_and_run_once(self):
        a=self.create('schedule');a=self.confirm(a);sid=a['schedule_id'];next_fire=self.store.schedule(sid)['next_fire']
        self.assertFalse(self.query_calls)
        tid=self.actions.run_now(a['id'],'one');self.wait(tid)
        self.assertIsNone(self.actions.run_now(a['id'],'one'))
        self.assertEqual(self.store.schedule(sid)['next_fire'],next_fire)
        self.assertFalse(self.ai_calls)
        self.engine.set_schedule_enabled(sid,False)
        self.assertFalse(self.actions.snapshot(a['id'])['schedule']['enabled'])

    def test_report_requires_consent_and_retains_fixed_binding(self):
        a=self.create('report');self.actions.preview(a['id'],1)
        with self.assertRaises(ValueError):self.actions.confirm(a['id'],1)
        a=self.actions.confirm(a['id'],1,True);self.wait(self.actions.run_now(a['id'],'once'))
        self.assertEqual(len(self.ai_calls),1)
        self.assertEqual(self.actions.snapshot(a['id'])['result']['summary_status'],'succeeded')

    def test_schedule_atomic_rollback(self):
        a=self.create('schedule');self.actions.preview(a['id'],1)
        with self.store.connection() as db:
            db.execute("CREATE TRIGGER reject_source BEFORE INSERT ON schedule_sources BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.actions.confirm(a['id'],1)
        self.assertFalse(self.store.schedules());self.assertEqual(self.actions.get(a['id'])['state'],'draft')

    def test_query_atomic_rollback_no_dispatch(self):
        a=self.create();self.actions.preview(a['id'],1)
        with self.store.connection() as db:
            db.execute("CREATE TRIGGER reject_link BEFORE UPDATE ON conversation_actions BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.actions.confirm(a['id'],1)
        self.assertFalse(self.store.tasks());self.assertFalse(self.query_calls)

    def test_reopen_preserves_link_and_never_dispatches(self):
        a=self.confirm(self.create());self.wait(a['task_id'])
        new=ActionService(self.engine)
        self.assertEqual(new.snapshot(a['id'])['task']['id'],a['task_id'])
        self.assertEqual(new.confirm(a['id'],1)['task_id'],a['task_id'])
        self.assertEqual(len(self.query_calls),1)

    def test_delete_links_keeps_independent_query_and_schedule(self):
        a=self.confirm(self.create());self.wait(a['task_id']);s=self.confirm(self.create('schedule'))
        preview=self.engine.preview_conversation_deletion([self.cid])
        self.assertEqual(preview['counts']['actions'],2)
        self.engine.delete_conversations(preview['token'])
        self.assertEqual(self.actions.list(self.cid),[])
        self.assertEqual(self.store.task(a['task_id'])['state'],'succeeded')
        self.assertTrue(self.store.schedule(s['schedule_id']))
        with self.store.connection() as db:self.assertIsNone(db.execute('SELECT conversation_id FROM schedule_sources').fetchone()[0])

    def test_cancelled_real_future_blocks_delete(self):
        self.gate.clear();a=self.confirm(self.create())
        until=time.monotonic()+2
        while not self.query_calls and time.monotonic()<until:time.sleep(.01)
        self.actions.cancel(a['id'])
        with self.assertRaises(ValueError):self.engine.preview_conversation_deletion([self.cid])
        self.gate.set();self.engine.close(wait=True)
        self.assertIsNone(self.store.task(a['task_id'])['result'])

    def test_parser_cancel_change_delete_and_late_return(self):
        a=self.create();self.actions.begin_parse(a['id'],1)
        with self.assertRaises(ValueError):self.engine.preview_conversation_deletion([self.cid])
        self.actions.cancel(a['id'])
        with self.assertRaises(ValueError):self.engine.preview_conversation_deletion([self.cid])
        self.actions.end_parse(a['id'])
        self.assertIsNone(self.actions.apply_parse(a['id'],1,example_query()))
        p=self.engine.preview_conversation_deletion([self.cid]);self.engine.delete_conversations(p['token'])
        self.assertIsNone(self.actions.apply_parse(a['id'],1,example_query()))

    def test_adopt_plan_uses_existing_gate_and_replay_id(self):
        pid=self.engine.create_plan('chat',{'text':'hello'},self.cid)
        a=self.actions.adopt_plan(self.cid,pid);self.assertEqual(a['id'],self.actions.adopt_plan(self.cid,pid)['id'])
        self.confirm(a);self.wait(self.store.plan(pid)['task_id'])
        self.actions.confirm(a['id'],1)
        self.assertEqual(len(self.ai_calls),1)

    def test_new_plan_revision_has_new_card_and_old_confirmation_expires(self):
        pid=self.engine.create_plan('chat',{'text':'old'},self.cid)
        old=self.actions.adopt_plan(self.cid,pid);self.actions.preview(old['id'],1)
        self.engine.edit_plan(pid,1,'chat',{'text':'new','conversation_id':self.cid})
        new=self.actions.adopt_plan(self.cid,pid)
        self.assertNotEqual(old['id'],new['id']);self.assertEqual(self.actions.snapshot(old['id'])['status'],'expired')
        with self.assertRaises(ValueError):self.actions.confirm(old['id'],1)
        with self.assertRaises(ValueError):self.actions.cancel(old['id'])
        self.assertEqual(self.store.plan(pid)['state'],'ready')
        self.confirm(new);self.wait(self.store.plan(pid)['task_id']);self.assertEqual(len(self.ai_calls),1)
        self.assertEqual(self.actions.snapshot(old['id'])['status'],'expired')

    def test_plan_atomic_rollback_no_dispatch(self):
        pid=self.engine.create_plan('chat',{'text':'test'},self.cid)
        a=self.actions.adopt_plan(self.cid,pid);self.actions.preview(a['id'],1)
        with self.store.connection() as db:
            db.execute("CREATE TRIGGER reject_link BEFORE UPDATE ON conversation_actions BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.actions.confirm(a['id'],1)
        self.assertFalse(self.store.tasks());self.assertFalse(self.ai_calls)
        self.assertEqual(self.store.plan(pid)['state'],'ready')
        with self.store.connection() as db:db.execute('DROP TRIGGER reject_link')
        self.confirm(a);self.wait(self.store.plan(pid)['task_id']);self.assertEqual(len(self.ai_calls),1)

    def test_schema3_upgrade_backup_and_rollback(self):
        self.engine.close(wait=True)
        with self.store.connection() as db:
            db.execute('DROP TABLE conversation_actions');db.execute('DROP TABLE schedule_sources');db.execute('PRAGMA user_version=3')
        def fail(db):initialize_action_schema(db);raise sqlite3.OperationalError('injected')
        with patch('desktop_app.core.initialize_action_schema',side_effect=fail),self.assertRaises(sqlite3.OperationalError):Store(self.path)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)
            self.assertFalse(db.execute("SELECT name FROM sqlite_master WHERE name='conversation_actions'").fetchall())
        migrated=Store(self.path)
        self.assertEqual(migrated.conversation(self.cid)['title'],'測試')
        with migrated.connection() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],7)
        backups=list(self.path.parent.glob('*.pre-v7-*.bak'));self.assertEqual(len(backups),2)
        with sqlite3.connect(backups[-1]) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)


class IntentTests(unittest.TestCase):
    def test_capability_and_intent(self):
        self.assertTrue(can_parse_actions(True,REPORT_BINDING))
        self.assertFalse(can_parse_actions(False,REPORT_BINDING));self.assertFalse(can_parse_actions(True,{'profile_id':'demo','revision':1}))
        for text,kind in [('查昨天數量','query'),('每天八點查庫存','schedule'),('每天八點日報','report'),('明天我要安排排程','choose'),('你好','None')]:
            self.assertEqual(str(intent_hint(text)),kind)
        for text in ('虛構：已完成報告，明天檢查資料。','請整理每天查資料的工作筆記','請改寫以下內容：每天查資料','今天已完成查資料'):
            self.assertIsNone(intent_hint(text))

    def test_schema_parse_and_malformed_result(self):
        data={'query_id':'DEMO03','from_date':'2026-09-26','to_date':'2026-09-27','category':'A',
              'time_hhmm':None,'frequency':None,'weekday':None,'date_mode':None,'questions':[]}
        client=Mock();client._complete.return_value=json.dumps(data)
        result=extract_action('查昨天數量',client=client)
        self.assertEqual(result['parameters']['category'],'A')
        self.assertNotIn('anyOf',json.dumps(client._complete.call_args.kwargs))
        for raw in ('{}','private-secret',json.dumps(dict(data,weekday=True)),json.dumps(dict(data,from_date='yesterday'))):
            client._complete.return_value=raw
            with self.assertRaises(GatewayError) as exc:extract_action('查數量',client=client)
            self.assertNotIn('private-secret',str(exc.exception))
