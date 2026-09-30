import copy
import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from desktop_app.profiles import Profiles, CredentialVault
from desktop_app.core import Store, Engine
from desktop_app.gateways import GatewayError

class MemoryVault:
    def __init__(self): self.values={}
    def set(self,name,key): self.values[name]=key
    def get(self,name): return self.values.get(name)
    def remove(self,name): self.values.pop(name,None)

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)
        self.vault=MemoryVault();self.p=Profiles(self.path/'assistants.json',vault=self.vault)
    def tearDown(self): self.tmp.cleanup()
    def test_management_revision_disable_default_persistence(self):
        pid=self.p.save('數據','id-one','說明');b=self.p.snapshot(pid)
        self.p.set_default(pid);self.assertEqual(self.p.default_binding(),b)
        self.p.save('新名稱','id-one','新備註',pid);self.assertEqual(self.p.snapshot(pid),b)
        self.p.save('新名稱','id-two','',pid)
        with self.assertRaisesRegex(GatewayError,'版本'):self.p.validate(b)
        self.p.save('新名稱','id-two','',pid,False)
        with self.assertRaisesRegex(GatewayError,'停用'):self.p.validate(self.p.snapshot(pid))
        reopened=Profiles(self.p.path,vault=self.vault)
        self.assertEqual(reopened.items()[1]['notes'],'')
        self.assertEqual(reopened.default_binding()['profile_id'],'demo')
        latest=reopened.snapshot(pid)
        with self.assertRaises(GatewayError):reopened.remove(pid,latest['revision']-1)
        reopened.remove(pid,latest['revision'])
        with self.assertRaises(GatewayError):reopened.validate(latest)
        self.assertTrue(any(p['id']==pid and p['revision']==latest['revision'] for p in reopened.data['history']))
    def test_key_destination_isolation_and_never_persist_secret(self):
        self.p.set_endpoint('https://company.invalid/v1');self.p.save_key('secret-test')
        self.assertEqual(self.p.key(),'secret-test')
        self.assertNotIn('secret-test',self.p.path.read_text('utf-8'))
        self.p.set_endpoint('https://other.invalid/v1')
        with self.assertRaises(GatewayError):self.p.key()
        self.p.save_key('replacement');self.p.remove_key()
        with self.assertRaises(GatewayError):self.p.key()
    def test_environment_not_imported_and_explicit_keyring_takes_over(self):
        self.p.data['api_key_env']='QA_TEST_LEGACY'
        with patch.dict(os.environ,{'QA_TEST_LEGACY':'legacy'}):
            self.assertEqual(self.p.key(),'legacy');self.assertEqual(self.vault.values,{})
            self.p.save_key('stored');self.assertEqual(self.p.key(),'stored')
            self.p.remove_key()
            with self.assertRaises(GatewayError): self.p.key()
            self.assertEqual(os.environ['QA_TEST_LEGACY'],'legacy')
    def test_unconfigured_api_does_not_guess_or_dispatch(self):
        pid=self.p.save('數據','company-id')
        with patch('desktop_app.profiles.CompanyAssistant') as adapter:
            with self.assertRaisesRegex(GatewayError,'API 格式'):
                self.p.respond([{'role':'user','content':'hello'}],'chat',self.p.snapshot(pid))
            adapter.assert_not_called()
    def test_confirmed_mapping_and_per_request_destination(self):
        self.p.set_endpoint('https://company.invalid/v1');self.p.save_key('secret')
        one=self.p.save('一','one');two=self.p.save('二','two');self.p.data['wire_mode']='model'
        with patch('desktop_app.profiles.CompanyAssistant') as adapter:
            adapter.return_value.respond.return_value='ok'
            self.p.respond([{'role':'user','content':'one only'}],'chat',self.p.snapshot(one))
            self.p.respond([{'role':'user','content':'two only'}],'chat',self.p.snapshot(two))
            self.assertEqual([c.args[0]['model'] for c in adapter.call_args_list],['one','two'])
            self.assertEqual(adapter.return_value.close.call_count,2)
    def test_legacy_profile_identity_persisted_before_any_user_edit(self):
        path=self.path/'legacy.json'
        legacy={'mode':'company','base_url':'https://company.invalid/v1','model':'old-model','api_key_env':'TEST'}
        first=Profiles(path,legacy,vault=self.vault);binding=first.default_binding()
        second=Profiles(path,legacy,vault=self.vault)
        self.assertEqual(binding,second.default_binding())
        self.assertEqual(second.validate(binding)['assistant_id'],'old-model')
        self.assertEqual(first.data['credential_id'],second.data['credential_id'])

    def test_keyring_error_redacted_no_fallback(self):
        class Broken:
            def get_password(self,*a):raise RuntimeError('private-token')
            def set_password(self,*a):raise RuntimeError('private-token')
        v=CredentialVault(Broken())
        for fn,args in [(v.get,('id',)),(v.set,('id','secret'))]:
            with self.assertRaises(GatewayError) as e:fn(*args)
            self.assertNotIn('private-token',str(e.exception))

class WindowsCredentialTests(unittest.TestCase):
    def test_real_windows_credential_roundtrip_isolated(self):
        vault=CredentialVault();account='test-'+uuid.uuid4().hex
        try:
            vault.set(account,'synthetic-one');self.assertEqual(vault.get(account),'synthetic-one')
            vault.set(account,'synthetic-two');self.assertEqual(vault.get(account),'synthetic-two')
            vault.remove(account);self.assertIsNone(vault.get(account))
        finally:vault.remove(account)

class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.p=Profiles(self.root/'profiles.json',vault=MemoryVault());self.store=Store(self.root/'db.sqlite')
        self.calls=[];self.gate=threading.Event();self.gate.set()
        def router(messages,purpose,binding):
            self.calls.append((messages,copy.deepcopy(binding)));self.gate.wait(3);return 'done'
        self.engine=Engine(self.store,lambda *a:None,lambda *a:'not used',assistant_router=router,binding_validator=self.p.validate)
    def tearDown(self):
        self.gate.set();self.engine.close(wait=True);self.tmp.cleanup()
    def wait(self,tid):
        for _ in range(500):
            t=self.store.task(tid)
            if t['state'] in ('succeeded','failed','cancelled'):return t
            time.sleep(.005)
        self.fail('timeout')
    def test_conversations_pin_target_and_context(self):
        p1=self.p.save('one','one');p2=self.p.save('two','two')
        c1=self.store.create_conversation('one',self.p.snapshot(p1));c2=self.store.create_conversation('two',self.p.snapshot(p2))
        self.gate.clear()
        t1=self.engine.run_chat(c1,'private-one');t2=self.engine.run_chat(c2,'private-two')
        self.gate.set();self.assertEqual(self.wait(t1)['state'],'succeeded');self.wait(t2)
        mapping={binding['profile_id']:messages for messages,binding in self.calls}
        self.assertEqual(mapping[p1],[{'role':'user','content':'private-one'}])
        self.assertEqual(mapping[p2],[{'role':'user','content':'private-two'}])
    def test_plan_zero_dispatch_until_approved_and_changed_target_refused(self):
        pid=self.p.save('one','one');cid=self.store.create_conversation('one',self.p.snapshot(pid))
        plan=self.engine.create_plan('chat',{'text':'data','conversation_id':cid},cid)
        self.assertEqual(self.calls,[]);self.assertEqual(self.store.tasks(),[])
        self.p.save('one','changed','',pid)
        with self.assertRaisesRegex(GatewayError,'版本'):self.engine.confirm_plan(plan,1,'approve')
        self.assertEqual(self.store.tasks(),[])
    def test_no_auto_summary_and_legacy_readonly(self):
        cid=self.store.create_conversation('legacy')
        with self.store.connection() as db:db.execute('UPDATE conversations SET binding=NULL WHERE id=?',(cid,))
        with self.assertRaisesRegex(GatewayError,'舊版'):self.engine.run_chat(cid,'data')
        with self.assertRaises(ValueError):self.engine.run_query_summarize('q',{})
        self.assertEqual(self.calls,[])
    def test_v1_backup_and_transactional_migration_preserves_history(self):
        path=self.root/'old.sqlite'
        with sqlite3.connect(path) as db:
            db.executescript("CREATE TABLE conversations(id TEXT PRIMARY KEY,title TEXT,created_at TEXT); INSERT INTO conversations VALUES('old','歷史','time'); PRAGMA user_version=1;")
        migrated=Store(path);self.assertIsNone(migrated.conversation('old')['binding'])
        backups=list(self.root.glob('old.sqlite.pre-v6-*.bak'));self.assertEqual(len(backups),1)
        with sqlite3.connect(backups[0]) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT title FROM conversations').fetchone()[0],'歷史')
        Store(path);self.assertEqual(len(list(self.root.glob('old.sqlite.pre-v6-*.bak'))),1)
