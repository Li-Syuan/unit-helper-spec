import copy
import io
import json
import re
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from desktop_app.config import DEFAULT
from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge
from desktop_app.dialogue_store import DialogueStore
from desktop_app.dialogue_service import DialogueService
from desktop_app.activation import Activation, deployment
from desktop_app.cli import Workbench, execute_line
from tests.test_dialogue_recovery import SyntheticProfiles
from desktop_app.dialogue_provider import ProfileDialogueProvider
from test_support.assistants_mock import AssistantsMock


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.s=WebSession(directory=self.root,config=copy.deepcopy(DEFAULT),start_scheduler=False)
        self.c=self.s.continuity;self.d=self.s.dialogue
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def note(self,aid='demo-general',source=None):
        data={'assistant_id':aid,'title':'報告偏好','text':'用繁體中文；未知事項明示。','category':'preference','source_thread_id':source}
        return self.c.memory_confirm(self.c.memory_preview(data)['token'])
    def test_local_title_manual_override_and_folders_preserve_conversation(self):
        t=self.d.start();tid=t['id'];self.d.send(tid,'請幫我整理每天八點財經日報。請列出台股、美股新聞','topic')
        self.assertEqual(self.d.history()[0]['title'],'整理每天八點財經日報')
        before=self.d.state(tid);self.c.view_save(tid,'未送出草稿',51,before['view_revision'])
        before=self.d.state(tid)
        with patch.object(self.d.provider,'respond_context',side_effect=AssertionError('must not call model')):
            folder=self.c.folder_create('每日報告')
            self.c.folder_move(tid,folder['id'])
            self.c.folder_update(folder['id'],1,collapsed=True,name='市場報告')
            with self.assertRaises(ValueError):self.c.folder_update(folder['id'],1,delete=True)
            with self.assertRaises(ValueError):self.c.folder_create('市場報告')
            with self.assertRaises(ValueError):self.c.folder_create('a\nb')
            with self.assertRaises(ValueError):self.c.folder_move(tid,'missing')
            self.c.metadata(tid,title='我的研究',pinned=True)
            self.assertEqual(self.d.history()[0]['title_source'],'manual')
            self.c.metadata(tid,title='')
            self.assertEqual(self.d.history()[0]['title_source'],'auto')
            self.assertEqual(self.d.history()[0]['title'],'整理每天八點財經日報')
            after=self.d.state(tid)
            for key in ('assistant_id','revision','messages','request','memory_snapshot','draft_text','view_revision','scroll'):
                self.assertEqual(before[key],after[key],key)
            fresh=DialogueService(DialogueStore(self.d.store.path),self.d.provider)
            self.assertEqual(fresh.history()[0]['folder_id'],folder['id']);fresh.close()
            self.assertTrue(self.c.folders()[0]['collapsed'])
            self.c.folder_update(folder['id'],2,delete=True)
            self.assertIsNone(self.d.history()[0]['folder_id']);self.assertEqual(self.c.folders(),[])
            self.assertEqual(self.d.state(tid)['messages'],before['messages'])
            self.assertEqual(self.s.store.tasks(),[])
        self.d.send(tid,'現在改聊其他主題','topic2')
        self.assertEqual(self.d.history()[0]['title'],'整理每天八點財經日報')

    def test_folder_bridge_authorization_preferences_failure_and_cli(self):
        bridge=WebBridge(self.s);w=Workbench(self.s);w.start();out=io.StringIO()
        execute_line(w,'/folder-create CLI資料夾',io.StringIO(),out)
        folder=self.c.folders()[0]
        execute_line(w,'/folder-move '+folder['id'],io.StringIO(),out)
        self.assertEqual(self.d.history()[0]['folder_id'],folder['id'])
        self.assertTrue(bridge.call('dialogue_recent_preference',{'collapsed':True})['data']['saved'])
        self.assertTrue(WebBridge(self.s).call('dialogue_recent_preference')['data']['collapsed'])
        with patch('desktop_app.web_bridge.update_preferences',side_effect=OSError('private error')):
            result=bridge.call('dialogue_recent_preference',{'collapsed':False})
            self.assertFalse(result['data']['saved']);self.assertNotIn('private',json.dumps(result))
        with patch.object(self.s,'assert_identity',side_effect=ValueError('expired')):
            for name,payload in [('dialogue_folder_create',{'name':'拒絕'}),('dialogue_folders',{}),('dialogue_recent_preference',{})]:
                self.assertFalse(bridge.call(name,payload)['ok'])
        self.d.confirm_delete(self.d.preview_delete('threads',[w.thread['id']])['token'])
        self.assertEqual(len(self.c.folders()),1)
        with self.assertRaises(ValueError):self.c.folder_move(w.thread['id'],folder['id'])

    def test_v3_folder_migration_backup_and_rollback_preserve_notes_and_drafts(self):
        path=self.root/'v3.sqlite3'
        with sqlite3.connect(path) as db:
            DialogueStore._upgrade(db);DialogueStore._continuity_upgrade(db)
            db.execute("INSERT INTO threads VALUES('old','chat','demo-general','{}',1,'now')")
            db.execute("INSERT INTO thread_views(thread_id,title,draft,memories,updated_at) VALUES('old','原名稱','舊草稿','[{\"text\":\"固定筆記\"}]','now')")
            db.execute("INSERT INTO memories VALUES('note',1,'demo-general','偏好','不編造','rule',1,'old','now')")
            db.execute("INSERT INTO task_drafts VALUES('draft','old',1,'demo-general','{}',0,'now')")
        original=DialogueStore._folders_upgrade
        def fail(db):original(db);raise RuntimeError('rollback folders')
        with patch.object(DialogueStore,'_folders_upgrade',side_effect=fail):
            with self.assertRaises(RuntimeError):DialogueStore(path)
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)
            self.assertNotIn('folder_id',[r[1] for r in db.execute('PRAGMA table_info(thread_views)')])
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='dialogue_folders'").fetchone())
        store=DialogueStore(path);state=DialogueService(store).state('old')
        self.assertEqual(state['draft_text'],'舊草稿');self.assertEqual(state['title'],'原名稱')
        self.assertEqual(state['memory_snapshot'],[{'text':'固定筆記'}]);self.assertFalse(state['saved'][0]['enabled'])
        with store.connect() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],5)
            self.assertEqual(db.execute('SELECT text FROM memories').fetchone()[0],'不編造')
        backups=list(self.root.glob('v3.sqlite3.pre-v5-*.bak'));self.assertEqual(len(backups),2)
        for backup in backups:
            with sqlite3.connect(backup) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)

    def test_memory_preview_revision_scope_snapshot_and_delete(self):
        source=self.d.start();note=self.note(source=source['id'])
        preview=self.c.start_preview('chat','demo-general');self.assertEqual(self.d.state(source['id'])['memory_snapshot'],[])
        new=self.c.start_confirm(preview['token'],True);self.assertEqual(new['memory_snapshot'][0]['text'],note['text'])
        self.assertEqual(self.c.snapshot('demo-data'),[])
        with self.assertRaises(ValueError):self.c.snapshot('demo-data',[note['id']])
        p=self.c.manage_preview(note['id'],note['revision'],'disable');self.c.manage_confirm(p['token'])
        self.assertEqual(self.c.snapshot('demo-general'),[]);self.assertTrue(self.d.state(new['id'])['memory_snapshot'])
        old=self.c.start_preview('chat','demo-general');note=self.c.get(note['id'])
        self.c.manage_confirm(self.c.manage_preview(note['id'],note['revision'],'enable')['token'])
        with self.assertRaises(ValueError):self.c.start_confirm(old['token'],True)
        self.d.confirm_delete(self.d.preview_delete('threads',[source['id']])['token'])
        note=self.c.get(note['id']);self.assertTrue(note['source_deleted'])
        data={k:note[k] for k in ('title','text','category','assistant_id','source_thread_id')};data['text']='來源刪除後仍可編輯'
        note=self.c.memory_confirm(self.c.memory_preview(data,note['id'],note['revision'])['token'])
        self.assertEqual(note['text'],data['text'])
        self.c.manage_confirm(self.c.manage_preview(note['id'],note['revision'],'delete')['token'])
        self.assertEqual(self.c.memories(),[]);self.assertTrue(self.d.state(new['id'])['memory_snapshot'])
        for n in range(7):
            d=dict(data,title=str(n),text='長'*2000,source_thread_id=None)
            self.c.memory_confirm(self.c.memory_preview(d)['token'])
        p=self.c.start_preview('chat','demo-general');self.assertTrue(p['memory_error'])
        with self.assertRaises(ValueError):self.c.start_confirm(p['token'],True)
        p=self.c.start_preview('chat','demo-general');self.assertEqual(self.c.start_confirm(p['token'],False)['memory_snapshot'],[])
    def test_draft_cas_send_clear_rename_pin_reopen_and_delete(self):
        t=self.d.start();tid=t['id'];self.c.view_save(tid,'草稿',71,0)
        with self.assertRaises(ValueError):self.c.view_save(tid,'晚到',0,0)
        self.c.metadata(tid,title='持續工作',pinned=True)
        fresh=DialogueService(DialogueStore(self.d.store.path),self.d.provider)
        self.assertEqual(fresh.state(tid)['draft_text'],'草稿');self.assertEqual(fresh.state(tid)['scroll'],71)
        self.assertEqual(fresh.history()[0]['title'],'持續工作');fresh.close()
        self.d.send(tid,'草稿','draft-send');self.assertEqual(self.d.state(tid)['draft_text'],'')
        with self.assertRaises(ValueError):self.c.view_save(tid,'晚到',0,1)
        p=self.d.preview_delete('threads',[tid]);self.assertEqual(p['counts']['thread_views'],1)
        self.c.view_save(tid,'新草稿',0,2)
        with self.assertRaises(ValueError):self.d.confirm_delete(p['token'])
        self.d.confirm_delete(self.d.preview_delete('threads',[tid])['token'])
        with self.assertRaises(ValueError):self.c.view_save(tid,'復活',0,3)
    def test_host_close_flush_after_expiry_preserves_cas_and_drains_request(self):
        t=self.d.start();tid=t['id'];entered=threading.Event();release=threading.Event()
        def reply(*args,**kwargs):
            entered.set();release.wait(3);return {'message':'晚到回覆'}
        errors=[]
        def send():
            try:self.d.send(tid,'已送內容','close-pending')
            except Exception as exc:errors.append(type(exc).__name__)
        with patch.object(self.d.provider,'respond_context',side_effect=reply):
            worker=threading.Thread(target=send);worker.start();self.assertTrue(entered.wait(2))
            with patch.object(self.s,'assert_identity',side_effect=ValueError('登入已到期')):
                bridge=WebBridge(self.s)
                self.assertFalse(bridge.call('dialogue_view_save',{'id':tid,'text':'新草稿','scroll':12,'revision':0})['ok'])
                self.assertNotIn('save_view_for_close',bridge._handlers())
                result=self.c.save_view_for_close({'id':tid,'text':'新草稿','scroll':12,'revision':0})
                self.assertEqual(result['revision'],1)
                with self.assertRaises(ValueError):self.c.save_view_for_close({'id':tid,'text':'過期草稿','scroll':0,'revision':0})
                closer=threading.Thread(target=self.s.close);closer.start()
                self.assertTrue(self.d._pending[tid]['cancelled'].wait(2))
                release.set();worker.join(3);closer.join(3)
                self.assertFalse(worker.is_alive());self.assertFalse(closer.is_alive())
        with self.d.store.connect() as db:
            self.assertEqual(db.execute('SELECT draft FROM thread_views WHERE thread_id=?',(tid,)).fetchone()[0],'新草稿')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM messages').fetchone()[0],0)
        self.assertTrue(errors)

    def test_two_threads_ten_turns_real_sdk_mock_reopen_fixed_memory(self):
        mock=AssistantsMock(reply='合成回覆');provider=ProfileDialogueProvider(SyntheticProfiles(self.root/'profiles.json',mock.handle))
        self.d.provider=provider
        aid='company:fixture:1';a=self.d.start(assistant_id=aid,memory_snapshot=[{'text':'記憶甲'}]);b=self.d.start(assistant_id=aid)
        for n in range(10):
            for t in (a,b):self.d.send(t['id'],'合成第'+str(n)+'輪',t['id']+str(n))
            if n==4:
                self.d.close();self.d=DialogueService(DialogueStore(self.d.store.path),provider);self.s.dialogue=self.d;self.c.dialogue=self.d;self.c.lock=self.d.lock
        self.assertEqual(len(mock.threads),2);self.assertEqual(len(mock.runs),20)
        payloads=[r[2] for r in mock.requests if r[0]=='POST' and r[1].endswith('/messages')]
        self.assertEqual(sum('記憶甲' in p['content'] for p in payloads),1)
        self.assertEqual(len(self.d.state(a['id'])['messages']),20)
        self.assertTrue(all(r[2]['tool_choice']=='none' for r in mock.requests if r[0]=='POST' and r[1].endswith('/runs')))
    def test_continuation_preview_no_dispatch_and_summary_cancel_unknown(self):
        t=self.d.start();self.d.send(t['id'],'本週完成介面','first');old=self.d.state(t['id'])
        with self.assertRaises(ValueError):self.c.summarize(t['id'],'非來源','demo-general',True)
        r=self.c.summarize(t['id'],'本週完成介面','demo-general',True)
        p=self.c.continuation_preview(t['id'],'demo-general',r['text']);before=len(self.d.history())
        self.assertEqual(len(self.d.history()),before)
        new=self.c.continuation_confirm(p['token']);self.assertEqual(new['messages'],[]);self.assertEqual(new['source_thread_id'],t['id'])
        self.assertTrue(new['draft_text']);self.assertEqual(self.d.state(t['id'])['messages'],old['messages'])
        with self.assertRaises(ValueError):self.c.continuation_confirm(p['token'])
        self.d.confirm_delete(self.d.preview_delete('threads',[t['id']])['token']);self.assertTrue(self.d.state(new['id'])['source_deleted'])
        pid=self.company();aid='company:'+pid+':1';t=self.d.start(assistant_id=aid)
        with patch.object(self.s.profiles,'respond',return_value='來源'):self.d.send(t['id'],'原始內容','synthetic')
        with patch.object(self.s.profiles,'respond',side_effect=RuntimeError('private body')) as send:
            with self.assertRaises(RuntimeError):self.c.summarize(t['id'],'原始內容',aid,True)
            with self.assertRaises(ValueError):self.c.summarize(t['id'],'原始內容',aid,True)
            self.assertEqual(send.call_count,1)
        # A separately requested summary has a true pending guard and fences late output.
        other=self.d.start(assistant_id=aid)
        with patch.object(self.s.profiles,'respond',return_value='來源'):self.d.send(other['id'],'可取消來源','cancel-source')
        entered=threading.Event();release=threading.Event();errors=[]
        def slow(*a,**k):entered.set();release.wait(5);return '晚到摘要'
        def worker():
            try:self.c.summarize(other['id'],'可取消來源',aid,True)
            except Exception as exc:errors.append(exc)
        with patch.object(self.s.profiles,'respond',side_effect=slow):
            thread=threading.Thread(target=worker);thread.start();self.assertTrue(entered.wait(3))
            try:
                self.d.stop(other['id'])
                with self.assertRaises(ValueError):self.d.preview_delete('threads',[other['id']])
                self.assertFalse(WebBridge(self.s).call('activation_save',{'assistant_id':'asst_fixture','api_key':'synthetic'})['ok'])
            finally:release.set();thread.join(5)
        self.assertTrue(errors);self.assertFalse(self.d.has_inflight());self.assertEqual(len(self.d.state(other['id'])['messages']),2)
    def company(self):
        self.s.profiles.set_endpoint('https://fixture.example.test/v1');self.s.profiles.set_wire_mode('assistants')
        return self.s.profiles.save('合成助理','asst_fixture')
    def test_activation_two_round_assertions_no_metadata_no_secret_and_version(self):
        pid=self.company();seen=[]
        def reply(messages,purpose,binding,context):
            seen.append((copy.deepcopy(messages),context))
            self.assertEqual(context['search_authorized'],False)
            return 'OK' if len(messages)==1 else re.search(r'QA-[0-9a-f]+',messages[0]['content'])[0]
        with patch.object(self.s.profiles,'respond',side_effect=reply),patch.object(self.s.profiles,'inspect_assistant',side_effect=AssertionError('metadata forbidden')):
            r=self.s.activation.test(pid,True);self.assertTrue(r['passed'])
        self.assertEqual(len(seen),2);self.assertEqual(seen[0][1]['conversation_id'],seen[1][1]['conversation_id'])
        self.assertEqual(self.s.activation.status()['chat_profiles'][0]['chat_status'],'passed')
        self.assertIsNone(self.s.skills.proof(pid,1))
        with patch.object(self.s.profiles,'respond',return_value='沒有代號'):self.assertFalse(self.s.activation.test(pid,True)['passed'])
        vault={}
        with patch.object(self.s.profiles.vault,'set',side_effect=lambda k,v:vault.update({k:v})),patch.object(self.s.profiles.vault,'get',side_effect=vault.get),patch.object(self.s.profiles.vault,'remove',side_effect=lambda k:vault.pop(k,None)):
            saved=self.s.activation.save('asst_fixture','SYNTHETIC-SECRET-ONLY');self.assertTrue(saved['saved'])
        self.assertNotIn('SYNTHETIC-SECRET-ONLY',self.s.profiles.path.read_text('utf-8'))
        self.assertEqual(self.s.activation.status()['chat_profiles'][0]['chat_status'],'not_tested')
        self.assertEqual(self.s.profiles.items(True)[1]['credential_mode'],'individual')
        with patch.object(self.s.profiles.vault,'set',side_effect=ValueError('synthetic vault unavailable')):
            with self.assertRaises(ValueError):self.s.activation.save('asst_fixture','never-persist')
        self.assertNotIn('never-persist',self.s.profiles.path.read_text('utf-8'))
    def test_deployment_validation_no_override_or_external_defaults(self):
        self.assertTrue(self.s.activation.status()['available']);self.assertFalse(self.s.activation.status()['configured'])
        vault={}
        with patch.object(self.s.profiles.vault,'set',side_effect=lambda k,v:vault.update({k:v})),patch.object(self.s.profiles.vault,'get',side_effect=vault.get),patch.object(self.s.profiles.vault,'remove',side_effect=lambda k:vault.pop(k,None)),patch.object(self.s.profiles,'respond',side_effect=AssertionError('save must not send')):
            for endpoint in ('','http://fixture.example.test','https://user:password@fixture.example.test'):
                with self.assertRaises(ValueError):self.s.activation.save('asst_fixture','synthetic-only',endpoint)
                self.assertFalse(self.s.profiles.data['endpoint'])
            self.s.activation.save('asst_fixture','synthetic-only','https://fixture.example.test/v1')
            self.assertTrue(self.s.activation.status()['configured']);self.assertEqual(self.s.profiles.data['wire_mode'],'assistants')
            binding=self.s.profiles.snapshot(self.s.profiles.data['default'])
            with self.assertRaises(ValueError):self.s.activation.save('asst_fixture','other-key','https://new.example.test/v1')
            self.s.profiles.validate(binding)
            self.s.activation.save('asst_fixture','other-key','https://new.example.test/v1',True)
            with self.assertRaises(ValueError):self.s.profiles.validate(binding)
            self.assertNotIn('synthetic-only',vault.values())
        isolated=WebSession(directory=self.root/'disabled',config=copy.deepcopy(DEFAULT),start_scheduler=False,activation_enabled=False)
        try:
            self.assertFalse(isolated.activation.status()['available'])
            with self.assertRaises(ValueError):isolated.activation.save('asst_x','synthetic','https://x.test')
        finally:isolated.close()
        path=self.root/'deployment.json';path.write_text(json.dumps({'version':1,'protocol':'assistants','endpoint':'https://fixture.example.test/v1','ca_bundle':None}))
        self.assertEqual(deployment(path)['protocol'],'assistants')
        with patch('desktop_app.activation.deployment',return_value=deployment(path)):
            a=Activation(self.s);self.assertTrue(a.status()['configured']);self.assertFalse(a.status()['needed'])
            self.assertEqual(self.s.profiles.data['endpoint'],'https://new.example.test/v1')
        self.company()
        with patch('desktop_app.activation.deployment',return_value={'endpoint':'https://different.example.test/v1','ca_bundle':None}):
            a=Activation(self.s);self.assertTrue(a.status()['configured']);self.assertEqual(self.s.profiles.data['endpoint'],'https://fixture.example.test/v1')
        path.write_text(json.dumps({'version':1,'protocol':'assistants','endpoint':'https://x.test','ca_bundle':None,'api_key':'forbidden'}))
        with self.assertRaises(ValueError):deployment(path)
    def test_v2_migration_backup_and_atomic_rollback(self):
        path=self.root/'old.sqlite3';DialogueStore(path)
        with sqlite3.connect(path) as db:
            for t in ('workspace_views','dialogue_routes','routing_checks','thread_views','dialogue_folders','memories','continuation_requests','activation_checks'):db.execute('DROP TABLE '+t)
            db.execute('PRAGMA user_version=2');db.execute("INSERT INTO threads VALUES('old','chat','demo-general','{}',1,'now')")
        original=DialogueStore._continuity_upgrade
        def fail(db):original(db);raise RuntimeError('synthetic rollback')
        with patch.object(DialogueStore,'_continuity_upgrade',side_effect=fail):
            with self.assertRaises(RuntimeError):DialogueStore(path)
        with sqlite3.connect(path) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
        store=DialogueStore(path)
        self.assertEqual(DialogueService(store).state('old')['memory_snapshot'],[])
        for backup in self.root.glob('old.sqlite3.pre-v5-*.bak'):
            with sqlite3.connect(backup) as db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
    def test_skill_opt_in_memory_and_cli_confirmation_no_dispatch(self):
        note=self.note();from desktop_app.skills import TEMPLATE
        d=copy.deepcopy(TEMPLATE);d.update(fields=[],search=False,default_profile_id='demo')
        k=self.s.skills;r=k.save_confirm(k.save_preview(d)['token'])
        f=k.start(r['id'],r['revision'],'demo',{},'整理');self.assertNotIn(note['text'],f['skill']['instructions'])
        f=k.start(r['id'],r['revision'],'demo',{},'整理',[note['id']]);self.assertIn(note['text'],f['skill']['instructions'])
        self.assertEqual(self.s.store.tasks(),[])
        w=Workbench(self.s);out=io.StringIO()
        with self.assertRaises(ValueError):execute_line(w,'/new-memory demo-general',io.StringIO('確認執行\n'),out)
        self.assertIsNone(w.thread)
        with self.assertRaises(ValueError):execute_line(w,'/activate asst_x',io.StringIO('key'),out)
        self.assertFalse(self.s.engine.has_inflight())
