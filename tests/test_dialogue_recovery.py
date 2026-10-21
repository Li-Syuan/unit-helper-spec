"""Durable main-chat recovery and bounded local deletion; never company HTTP."""
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from openai import OpenAI
from desktop_app.assistants_gateway import AssistantsGateway
from desktop_app.dialogue_provider import ProfileDialogueProvider
from desktop_app.dialogue_service import DialogueService
from desktop_app.dialogue_store import DialogueStore
from test_support.assistants_mock import AssistantsMock
from desktop_app.assistant_errors import AssistantFailure


class SyntheticProfiles:
    def __init__(self,path,transport):
        self.path=path;self.transport=transport;self.data={'wire_mode':'assistants'}
    def validate(self,binding):
        if binding!={'profile_id':'fixture','revision':1}:raise ValueError('stale binding')
    def client(self,binding):
        sdk=OpenAI(api_key='synthetic-only',base_url='https://fixture.example.test/v1',max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(self.transport)))
        return AssistantsGateway({'base_url':'https://fixture.example.test/v1','assistant_id':'asst_fixture','poll_seconds':.01},
            'synthetic-only',self.path.parent/'assistant-sessions.sqlite3',binding,client=sdk)
    def respond(self,messages,purpose,binding,context=None):
        client=self.client(binding)
        try:return client.respond(messages,purpose,context)
        finally:client.close()
    def inspect_request(self,binding,context,remote=False):
        client=self.client(binding)
        try:return client.inspect_request(context=context,remote=remote)
        finally:client.close()
    def can_retry_unsent(self,binding,context):
        self.validate(binding)
        from desktop_app.assistants_gateway import session_context
        path=self.path.parent/'assistant-sessions.sqlite3'
        if not path.exists():return True
        key,rid,_,_=session_context(binding,'chat',context)
        with sqlite3.connect(path) as db:
            return db.execute('SELECT 1 FROM requests WHERE session_id=? AND id=?',(key,rid)).fetchone() is None


class DialogueRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'dialogue.sqlite3'
        self.service=DialogueService(DialogueStore(self.path));self.mock=AssistantsMock(reply='合成答案')
        self.fail=None
    def tearDown(self):self.service.close();self.tmp.cleanup()
    def company(self):
        def transport(request):
            if self.fail=='read' and request.method=='GET':raise httpx.ReadTimeout('synthetic',request=request)
            result=self.mock.handle(request)
            if self.fail=='write' and request.method=='POST' and request.url.path.endswith('/runs'):
                raise httpx.ReadTimeout('synthetic accepted write',request=request)
            return result
        provider=ProfileDialogueProvider(SyntheticProfiles(self.path.parent/'profiles.json',transport))
        self.service.provider=provider
        return provider
    def posts(self):return len([r for r in self.mock.requests if r[0]=='POST'])

    def test_proven_unsent_retries_same_request_once_and_survives_reopen(self):
        provider=self.company();tid=self.service.start(assistant_id='company:fixture:1')['id']
        self.service.send(tid,'第一輪','first')
        with patch.object(provider.profiles,'respond',side_effect=AssistantFailure('LOCAL_SETUP','preflight',sent=False)):
            with self.assertRaises(AssistantFailure):self.service.send(tid,'第二輪','second')
        self.service.close();self.service=DialogueService(DialogueStore(self.path),provider)
        state=self.service.state(tid)
        self.assertTrue(state['request']['retry_unsent']);self.assertEqual(len(state['messages']),2)
        inspected=self.service.inspect(tid)
        self.assertFalse(inspected['busy']);self.assertTrue(inspected['request']['retry_unsent'])
        with self.assertRaises(ValueError):self.service.retry_unsent(tid,'stale-request')
        before=self.posts();result=self.service.retry_unsent(tid,'second')
        self.assertEqual(len(result['messages']),4);self.assertEqual(self.posts()-before,2)
        self.assertEqual(self.service.retry_unsent(tid,'second'),result);self.assertEqual(self.posts()-before,2)
        self.service.send(tid,'第三輪','third')
        self.assertEqual(len(self.mock.threads),1)

    def test_unknown_or_cancelled_failure_never_promoted_by_missing_ledger(self):
        provider=self.company();tid=self.service.start(assistant_id='company:fixture:1')['id']
        for error in (ValueError('synthetic before dispatch'),AssistantFailure('TIMEOUT','run_create')):
            with patch.object(provider.profiles,'respond',side_effect=error):
                with self.assertRaises(Exception):self.service.send(tid,'不能推斷未送出',str(id(error)))
            self.assertFalse(self.service.state(tid)['request']['retry_unsent'])
            self.service.inspect(tid)
            with self.assertRaises(ValueError):self.service.retry_unsent(tid,str(id(error)))
            tid=self.service.fork(tid)['id']
        self.assertEqual(self.posts(),0)

    def test_unsent_proof_invalidated_by_receipt_or_changed_snapshot(self):
        provider=self.company();tid=self.service.start(assistant_id='company:fixture:1')['id']
        with patch.object(provider.profiles,'respond',side_effect=AssistantFailure('LOCAL_SETUP','preflight',sent=False)):
            with self.assertRaises(AssistantFailure):self.service.send(tid,'合成草稿','unsent')
        with patch.object(provider.profiles,'can_retry_unsent',return_value=False):
            with self.assertRaises(ValueError):self.service.retry_unsent(tid,'unsent')
        with self.service.store.connect() as db:db.execute("UPDATE requests SET history='[]'")
        with self.assertRaisesRegex(ValueError,'內容已改變'):self.service.retry_unsent(tid,'unsent')
        self.assertEqual(self.posts(),0)

    def test_second_turn_failure_reopens_recovers_only_reads_then_third_turn(self):
        for stage in ('poll','read_text'):
            with self.subTest(stage=stage):
                self.mock.statuses=['completed']
                provider=self.company();tid=self.service.start(assistant_id='company:fixture:1')['id']
                first=self.service.send(tid,'第一輪',stage+'one');self.fail='read'
                if stage=='poll':self.mock.statuses=['in_progress','completed']
                with self.assertRaises(Exception):self.service.send(tid,'第二輪',stage+'two')
                self.assertEqual(self.service.state(tid)['messages'],first['messages'])
                before=self.posts();self.fail=None
                self.service=DialogueService(DialogueStore(self.path),provider)
                status=self.service.state(tid)
                self.assertEqual(status['request']['pending_text'],'第二輪')
                self.assertEqual(status['request']['id'],stage+'two')
                with self.assertRaises(ValueError):self.service.send(tid,'第二輪','wrong-new-id')
                self.assertTrue(self.service.inspect(tid)['request']['recoverable'])
                result=self.service.recover(tid)
                self.assertEqual(len(result['messages']),4);self.assertFalse(result['busy'])
                self.assertEqual(self.posts(),before)
                self.assertEqual(self.service.recover(tid),result)
                third=self.service.send(tid,'第三輪',stage+'three')
                self.assertEqual(len(third['messages']),6)
                sent=[r[2]['content'] for r in self.mock.requests if r[0]=='POST' and r[1].endswith('/messages')]
                self.assertEqual(sent[-3:],['第一輪','第二輪','第三輪'])
        self.assertEqual(len(self.mock.threads),2)

    def test_unknown_write_never_retries_and_fork_preserves_history_and_draft(self):
        self.company();tid=self.service.start(assistant_id='company:fixture:1')['id']
        self.service.send(tid,'已完成','one');self.fail='write'
        with self.assertRaises(Exception):self.service.send(tid,'保留草稿','two')
        before=self.posts();self.fail=None
        self.assertFalse(self.service.inspect(tid)['request']['recoverable'])
        with self.assertRaises(ValueError):self.service.recover(tid)
        fresh=self.service.fork(tid)
        self.assertEqual(fresh['messages'],[]);self.assertEqual(fresh['draft_text'],'保留草稿')
        self.assertEqual(len(self.service.state(tid)['messages']),2);self.assertEqual(self.posts(),before)
        copied=self.service.fork(tid,include_history=True)
        self.assertEqual(copied['messages'],self.service.state(tid)['messages'])
        self.assertEqual(self.posts(),before)

    def test_completed_remote_cache_survives_local_failure_and_long_response(self):
        self.company();tid=self.service.start(assistant_id='company:fixture:1')['id']
        self.mock.reply='長'*12000
        original=self.service.validate_assistant
        calls=[]
        def reject_once(value):
            calls.append(value)
            if len(calls)==1:raise ValueError('synthetic local completion failure')
            return original(value)
        with patch.object(self.service,'validate_assistant',side_effect=reject_once):
            with self.assertRaises(ValueError):self.service.send(tid,'第一輪','one')
        before=len(self.mock.requests)
        self.assertTrue(self.service.inspect(tid)['request']['recoverable'])
        recovered=self.service.recover(tid)
        self.assertEqual(len(recovered['messages'][-1]['text']),12000)
        self.assertEqual(len(self.mock.requests),before)

    def test_cancelled_worker_blocks_delete_and_never_revives(self):
        entered=threading.Event();release=threading.Event();errors=[]
        class Slow:
            def respond_context(inner,*args):
                entered.set();release.wait(3);return {'text':'late','answers':{}}
            def inspect_context(inner,*args,**kwargs):return {'state':'completed','recoverable':True}
        self.service.provider=Slow();tid=self.service.start()['id']
        def send():
            try:self.service.send(tid,'保留文字','one')
            except Exception as exc:errors.append(exc)
        worker=threading.Thread(target=send);worker.start()
        try:
            self.assertTrue(entered.wait(2));self.service.stop(tid)
            with self.assertRaises(ValueError):self.service.preview_delete('threads',[tid])
            release.set();worker.join(3);self.assertEqual(len(errors),1)
            self.assertFalse(self.service.inspect(tid)['request']['recoverable'])
            with self.assertRaises(ValueError):self.service.recover(tid)
            self.assertEqual(self.service.state(tid)['messages'],[])
        finally:release.set();worker.join(3)

    def test_delete_snapshot_rollback_and_company_cache_only_local(self):
        self.company();tid=self.service.start(assistant_id='company:fixture:1')['id']
        self.service.send(tid,'私有合成訊息','one')
        other=self.service.start(assistant_id='company:fixture:1')['id'];self.service.send(other,'保留','other')
        preview=self.service.preview_delete('threads',[tid]);self.service.send(tid,'再一輪','two')
        with self.assertRaises(ValueError):self.service.confirm_delete(preview['token'])
        preview=self.service.preview_delete('threads',[tid]);before=len(self.mock.requests)
        with self.service.store.connect() as db:
            db.execute("CREATE TRIGGER abort_delete BEFORE DELETE ON requests BEGIN SELECT RAISE(ABORT,'synthetic'); END")
        with self.assertRaises(sqlite3.DatabaseError):self.service.confirm_delete(preview['token'])
        self.assertEqual(len(self.service.state(tid)['messages']),4)
        with self.service.store.connect() as db:db.execute('DROP TRIGGER abort_delete')
        self.service.confirm_delete(preview['token'])
        with self.assertRaises(ValueError):self.service.state(tid)
        with self.assertRaises(ValueError):self.service.confirm_delete(preview['token'])
        self.assertEqual(len(self.service.state(other)['messages']),2)
        with sqlite3.connect(self.path.parent/'assistant-sessions.sqlite3') as db:
            records=''.join(r[0] for r in db.execute('SELECT data FROM requests'))
            self.assertNotIn('私有合成訊息',records)
            self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],1)
        self.assertEqual(len(self.mock.requests),before)

    def test_task_draft_delete_cancel_and_stale_confirmation(self):
        thread=self.service.start('task');tid=thread['id']
        for index,text in enumerate(('需求','A','合成來源','摘要整理','每天08:00')):
            thread=self.service.send(tid,text,str(index))
        approval=self.service.preview(tid,thread['revision']);saved=self.service.confirm(tid,approval['token'])
        preview=self.service.preview_delete('task_drafts',[saved['id']])
        self.assertEqual(len(self.service.list_saved()),1)
        with patch('desktop_app.dialogue_service.time.monotonic',return_value=10**12):
            with self.assertRaises(ValueError):self.service.confirm_delete(preview['token'])
        self.service.confirm_delete(preview['token']);self.assertEqual(self.service.list_saved(),[])
        self.assertEqual(len(self.service.state(tid)['messages']),10)
        with self.assertRaises(ValueError):self.service.confirm(tid,approval['token'])

    def test_v1_backup_transaction_upgrade_and_enabled_constraint(self):
        self.service.close()
        with sqlite3.connect(self.path) as db:
            for table in ('thread_views','dialogue_folders','memories','continuation_requests','activation_checks'):db.execute('DROP TABLE '+table)
            db.execute('DROP TABLE requests');db.execute('PRAGMA user_version=1')
            db.execute("INSERT INTO threads VALUES('old','chat','demo-general','{}',1,'now')")
            db.execute("INSERT INTO messages(thread_id,role,text) VALUES('old','user','保留')")
        original=DialogueStore._upgrade
        def broken(db):original(db);raise RuntimeError('synthetic migration failure')
        with patch.object(DialogueStore,'_upgrade',side_effect=broken):
            with self.assertRaises(RuntimeError):DialogueStore(self.path)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],1)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='requests'").fetchone())
        self.service=DialogueService(DialogueStore(self.path))
        self.assertEqual(self.service.state('old')['messages'][0]['text'],'保留')
        backups=list(self.path.parent.glob('*.pre-v4-*.bak'));self.assertEqual(len(backups),2)
        for backup in backups:
            with sqlite3.connect(backup) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],1)
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        with self.service.store.connect() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO task_drafts VALUES('invalid','old',1,'demo-general','{}',1,'now')")
