"""Local cleanup preserves independent work and remote-write idempotency."""
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from desktop_app.assistant_sessions import AssistantSessions
from desktop_app.assistants_gateway import session_context
from desktop_app.core import Engine, Store, dumps, stamp
from desktop_app.data_cleanup import DataCleanup


class DataCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'state.sqlite3')
        self.calls=[];self.engine=Engine(self.store,lambda q,p:self.calls.append(q),lambda m,p:'unused')
        self.cleanup=DataCleanup(self.engine);self.binding={'profile_id':'synthetic','revision':1}
        self.ledger=AssistantSessions(self.store.path.with_name('assistant-sessions.sqlite3'))
    def tearDown(self):self.engine.close(wait=True);self.tmp.cleanup()
    def task(self,kind='query',payload=None,cid=None,rid='one',schedule=None):
        payload=payload or {'query_id':'fixture','parameters':{}}
        with self.store.connection() as db:
            tid,_=self.engine._new_task(db,kind,payload,cid,rid,schedule_id=schedule)
            db.execute("UPDATE tasks SET state='succeeded',result=?,finished_at=? WHERE id=?",(dumps({'text':'private-result'}),stamp(),tid))
        return tid
    def cache(self,context,rid,state='completed'):
        key=session_context(self.binding,'chat',context)[0]
        self.ledger.save(key,{'thread_id':'thread_fixture','history':['prefix'],'active':rid},rid,
            {'state':state,'result':'secret-output','tool_batches':[{'result':'secret-tool'}],
             'digest':'synthetic','run_id':'run_fixture','remote_terminal':True})
        return key
    def schedule(self,sid='schedule'):
        with self.store.connection() as db:
            db.execute("INSERT INTO schedules(id,name,query_id,parameters,frequency,time_hhmm,weekday,notify_rule,enabled,created_at) VALUES(?,?,'fixture','{}','daily','08:00',0,'nonempty_on_change',0,?)",(sid,'合成排程',stamp()))
        return sid
    def workflow(self,wid='workflow',task=None,schedule=None):
        with self.store.connection() as db:
            db.execute("INSERT INTO workflows VALUES(?,NULL,'合成流程',2,'approved',?,'[]','[]','[]','',?,?,?,?)",
                (wid,dumps(self.binding),task,schedule,stamp(),stamp()))
            db.execute('INSERT INTO workflow_versions VALUES(?,2,?)',(wid,dumps({'goal':'private-goal'})))
        return wid

    def test_task_content_deleted_receipt_prevents_reexecution_other_data_retained(self):
        cid=self.store.create_conversation('保留對話');self.store.add_message(cid,'user','保留訊息')
        sid=self.schedule();tid=self.task(schedule=sid);other=self.task(rid='other')
        with self.store.connection() as db:
            db.execute("INSERT INTO workflow_steps VALUES(?,'s1',0,'succeeded','private-input','private-output','')",(tid,))
            db.execute("INSERT INTO outcome_feedback VALUES(?,'usable','private-note',?,?)",(tid,stamp(),stamp()))
            db.execute("INSERT INTO notifications VALUES('notice','n',?,'private-notification',0,?)",(tid,stamp()))
            db.execute("INSERT INTO occurrences VALUES('occ',?,'future','succeeded',?)",(sid,tid))
        preview=self.cleanup.preview('tasks',[tid]);self.cleanup.confirm(preview['token'])
        with self.store.connection() as db:
            self.assertEqual(self.engine._new_task(db,'query',{'query_id':'fixture','parameters':{}},request_id='one',schedule_id=sid),(tid,False))
        with self.assertRaises(ValueError):self.engine.run_query('fixture',{},request_id='one')
        self.assertEqual(self.calls,[])
        with self.assertRaises(ValueError):self.store.task(tid)
        with self.store.connection() as db:
            row=dict(db.execute('SELECT * FROM tasks WHERE id=?',(tid,)).fetchone())
            self.assertEqual(row['payload'],'{}');self.assertIsNone(row['result']);self.assertEqual(row['state'],'deleted')
            self.assertEqual(row['request_id'],'one');self.assertTrue(row['request_hash'])
            occurrence=dict(db.execute("SELECT * FROM occurrences WHERE id='occ'").fetchone())
            self.assertEqual(occurrence['state'],'deleted');self.assertIsNone(occurrence['task_id'])
            self.assertIsNone(self.engine._claim_occurrence(db,self.store.schedule(sid),'future',None))
            for table in ('workflow_steps','outcome_feedback','notifications'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table+' WHERE task_id=?',(tid,)).fetchone()[0],0)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(len(self.store.messages(cid)),1);self.assertEqual(self.store.schedule(sid)['id'],sid)
        self.assertEqual(self.store.task(other)['id'],other)
        self.assertNotIn(tid,[i['id'] for i in self.cleanup.catalog()['tasks']['items']])
        with self.assertRaises(ValueError):self.cleanup.confirm(preview['token'])

    def test_preview_expiry_changed_related_content_busy_future_and_atomic_rollback(self):
        tid=self.task();preview=self.cleanup.preview('tasks',[tid])
        with patch('desktop_app.data_cleanup.time.monotonic',return_value=10**12):
            with self.assertRaises(ValueError):self.cleanup.confirm(preview['token'])
        with self.store.connection() as db:db.execute("INSERT INTO notifications VALUES('n','n',?,'new',0,?)",(tid,stamp()))
        with self.assertRaises(ValueError):self.cleanup.confirm(preview['token'])
        preview=self.cleanup.preview('tasks',[tid]);pending=Future();self.engine._future_tasks[pending]=tid
        with self.store.connection() as db:db.execute("UPDATE tasks SET state='cancelled' WHERE id=?",(tid,))
        with self.assertRaises(ValueError):self.cleanup.confirm(preview['token'])
        pending.set_result(None);self.engine._future_tasks.pop(pending)
        preview=self.cleanup.preview('tasks',[tid]);key=self.cache({'conversation_id':'task:'+tid},tid)
        # The fixture cache was not part of this query task's payload, hence is independent.
        with self.store.connection() as db:
            db.execute("CREATE TRIGGER fail_cleanup BEFORE UPDATE ON tasks WHEN NEW.state='deleted' BEGIN SELECT RAISE(ABORT,'synthetic'); END")
        with self.assertRaises(sqlite3.DatabaseError):self.cleanup.confirm(preview['token'])
        self.assertEqual(self.store.task(tid)['state'],'cancelled');self.assertEqual(len(self.store.notifications()),1)
        self.assertIsNotNone(self.ledger.get_request(key,tid))
        with self.store.connection() as db:db.execute('DROP TRIGGER fail_cleanup')
        self.cleanup.confirm(preview['token'])

    def test_cache_checkpoint_scope_and_status_inspection_lock(self):
        from desktop_app.graph_runner import execute
        step={'id':'s1','binding':self.binding,'kind':'assistant'}
        tid=self.task('workflow',{'workflow':{'id':'flow','steps':[step]}},rid='workflow-run')
        key=self.cache({'run_id':tid,'step_id':'s1'},tid)
        other=self.cache({'run_id':'other','step_id':'s1'},'other')
        graph=self.store.path.with_name('workflow-checkpoints.sqlite3')
        execute(graph,tid,[step],lambda s:None);execute(graph,'other',[step],lambda s:None)
        preview=self.cleanup.preview('tasks',[tid])
        with self.ledger.session(key):
            with self.assertRaises(ValueError):self.cleanup.confirm(preview['token'])
        with self.store.connection() as db:
            db.execute("CREATE TRIGGER fail_cleanup BEFORE UPDATE ON tasks WHEN NEW.state='deleted' BEGIN SELECT RAISE(ABORT,'synthetic'); END")
        with self.assertRaises(sqlite3.DatabaseError):self.cleanup.confirm(preview['token'])
        self.assertIsNotNone(self.ledger.get_request(key,tid))
        with sqlite3.connect(graph) as db:self.assertGreater(db.execute('SELECT count(*) FROM checkpoints WHERE thread_id=?',(tid,)).fetchone()[0],0)
        with self.store.connection() as db:db.execute('DROP TRIGGER fail_cleanup')
        self.cleanup.confirm(preview['token'])
        self.assertIsNone(self.ledger.get_request(key,tid));self.assertIsNotNone(self.ledger.get_request(other,'other'))
        with sqlite3.connect(graph) as db:
            for table in ('checkpoints','writes'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table+' WHERE thread_id=?',(tid,)).fetchone()[0],0)
            self.assertGreater(db.execute("SELECT count(*) FROM checkpoints WHERE thread_id='other'").fetchone()[0],0)

    def test_shared_chat_cache_scrub_does_not_cancel_completed_prefix(self):
        cid=self.store.create_conversation('保留對話');tid=self.task('chat',{'text':'合成','_binding':self.binding},cid)
        key=self.cache({'conversation_id':'engine:'+cid},tid)
        preview=self.cleanup.preview('tasks',[tid]);self.cleanup.confirm(preview['token'])
        receipt=self.ledger.get_request(key,tid)
        self.assertEqual(receipt['state'],'completed');self.assertEqual(receipt['result'],'');self.assertEqual(receipt['tool_batches'],[])
        self.assertEqual(self.ledger.get_session(key)['history'],['prefix'])
        self.assertEqual(len(self.store.messages(cid)),1)

    def test_schedule_and_workflow_deletion_preserves_results_and_rejects_active(self):
        sid=self.schedule();tid=self.task(schedule=sid);wid=self.workflow(task=tid,schedule=sid)
        with self.store.connection() as db:
            db.execute('INSERT INTO schedule_sources VALUES(?,NULL)',(sid,))
            db.execute("INSERT INTO occurrences VALUES('occ',?,'future','succeeded',?)",(sid,tid))
            db.execute('UPDATE schedules SET enabled=1 WHERE id=?',(sid,))
        with self.assertRaises(ValueError):self.cleanup.preview('schedules',[sid])
        with self.assertRaises(ValueError):self.cleanup.preview('workflows',[wid])
        with self.store.connection() as db:db.execute('UPDATE schedules SET enabled=0 WHERE id=?',(sid,))
        preview=self.cleanup.preview('schedules',[sid]);self.cleanup.confirm(preview['token'])
        self.assertEqual(self.store.task(tid)['schedule_id'],sid)
        self.assertEqual(self.store.task(tid)['result'],{'text':'private-result'})
        key=self.cache({'run_id':wid+':2','step_id':'planner'},'planning')
        self.engine._workflows=SimpleNamespace(planning={wid:Future()},previews={wid:'unused'})
        with self.assertRaises(ValueError):self.cleanup.preview('workflows',[wid])
        self.engine._workflows.planning.clear()
        preview=self.cleanup.preview('workflows',[wid]);self.cleanup.confirm(preview['token'])
        self.assertIsNone(self.ledger.get_session(key));self.assertEqual(self.engine._workflows.previews,{})
        self.assertEqual(self.store.task(tid)['result'],{'text':'private-result'})
        with self.store.connection() as db:
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(db.execute('SELECT count(*) FROM workflow_versions').fetchone()[0],0)

    def test_plans_issues_forms_and_notifications_delete_without_dispatch(self):
        from desktop_app.choices import ChoiceForms
        plan=self.engine.create_plan('query',{'query_id':'fixture','parameters':{}})
        issue=self.store.save_issue('app','標題','說明','預期')
        forms=ChoiceForms(self.store.path);form=forms.create([{'id':'q','type':'yes_no','options':[{'id':'yes'},{'id':'no'}]}])
        with self.store.connection() as db:db.execute("INSERT INTO notifications VALUES('n','n',NULL,'合成',0,?)",(stamp(),))
        for kind,rid in [('plans',plan),('issues',issue),('local_forms',form['id']),('notifications','n')]:
            preview=self.cleanup.preview(kind,[rid]);self.cleanup.confirm(preview['token'])
        self.assertEqual(self.calls,[]);self.assertEqual(self.store.tasks(),[])
        with self.assertRaises(ValueError):self.engine.confirm_plan(plan,1,'old-approval')
