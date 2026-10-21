import copy
import io
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from desktop_app.config import DEFAULT
from desktop_app.core import Store
from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge
from desktop_app.skills import TEMPLATE, definition, answers, export_markdown, import_markdown, initialize_skill_schema
from desktop_app.cli import Workbench, execute_line

class SkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=WebSession(directory=self.tmp.name,config=copy.deepcopy(DEFAULT),start_scheduler=False)
        self.k=self.s.skills;self.w=self.s.workflows;self.api=WebBridge(self.s)
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def save(self,search=False):
        d=copy.deepcopy(TEMPLATE);d.update(search=search,fields=[],default_profile_id='demo')
        return self.k.save_confirm(self.k.save_preview(d)['token'])
    def wait(self):
        until=time.monotonic()+8
        while self.s.engine.has_inflight() and time.monotonic()<until:time.sleep(.01)
        self.assertFalse(self.s.engine.has_inflight())
    def plan(self,skill=None,pid='demo'):
        r=skill or self.save();f=self.k.start(r['id'],r['revision'],pid,{},'整理工作報告，不編造負責人與日期')
        self.k.discuss(f['id'],f['revision'],'請規劃',{});self.wait();return self.k.state(f['id'])
    def execute(self,flow):
        p=self.w.preview(flow['id'],flow['revision']);self.assertTrue(p['ready'],p.get('error'))
        tid=self.w.confirm(flow['id'],flow['revision'],True);self.wait();return self.s.store.task(tid)
    def company(self):
        p=self.s.profiles;p.set_endpoint('https://synthetic.example.test/v1');p.set_wire_mode('assistants')
        return p.save('合成助理','asst_synthetic')
    def test_definitions_options_import_and_export_remove_local_binding(self):
        d=copy.deepcopy(TEMPLATE);d['default_profile_id']='private-local-profile'
        md=export_markdown(d);self.assertNotIn('private-local-profile',md);self.assertNotIn('default_profile_id',md)
        imported=import_markdown(md);self.assertIsNone(imported['default_profile_id']);self.assertEqual(imported['instructions'],d['instructions'])
        self.assertEqual(import_markdown('普通方法')['instructions'],'普通方法')
        for text in ['```qa-skill-v2\n{}\n```',md.replace('"search": true','"search": true, "endpoint":"secret"')]:
            with self.assertRaises(ValueError):import_markdown(text)
        with self.assertRaises(ValueError):definition(dict(d,command='shell'))
        for values in [{'markets':['不存在'],'sources':'x'},{'markets':'台股','sources':'x'},{'unknown':'x'}]:
            with self.assertRaises(ValueError):answers(d['fields'],values)
        v,missing=answers([{'id':'yes','text':'是否','type':'boolean','options':[]}],{'yes':False})
        self.assertEqual(v,{'yes':False});self.assertFalse(missing)
    def test_save_preview_atomic_revision_and_one_shot(self):
        p=self.k.save_preview(copy.deepcopy(TEMPLATE));self.assertFalse(self.k.list());self.assertFalse(self.s.store.tasks())
        r=self.k.save_confirm(p['token'])
        with self.assertRaises(ValueError):self.k.save_confirm(p['token'])
        a=self.k.save_preview(self.k.copy(r['id']),r['id'],r['revision']);b=self.k.save_preview(self.k.copy(r['id']),r['id'],r['revision'])
        changed=self.k.save_confirm(a['token']);self.assertEqual(changed['revision'],2)
        with self.assertRaises(ValueError):self.k.save_confirm(b['token'])
        with self.s.store.connection() as db:self.assertEqual(db.execute('SELECT count(*) FROM skill_versions').fetchone()[0],2)
        with self.s.store.connection() as db:db.execute("CREATE TRIGGER refuse_skill BEFORE UPDATE ON skills BEGIN SELECT RAISE(ABORT,'synthetic'); END")
        preview=self.k.save_preview(self.k.copy(r['id']),r['id'],2)
        with self.assertRaises(sqlite3.IntegrityError):self.k.save_confirm(preview['token'])
        with self.s.store.connection() as db:self.assertEqual(db.execute('SELECT count(*) FROM skill_versions').fetchone()[0],2)
    def test_missing_fields_zero_dispatch_then_demo_plan_and_idempotent_execution(self):
        r=self.k.save_confirm(self.k.save_preview(copy.deepcopy(TEMPLATE))['token'])
        with patch('httpx.Client.send',side_effect=AssertionError('network')):
            f=self.k.start(r['id'],1,'demo',{},'每日情報');self.assertEqual(len(f['questions']),2)
            f=self.k.discuss(f['id'],f['revision'],'請規劃',{});self.assertFalse(self.s.engine.has_inflight());self.assertFalse(self.s.store.tasks())
            values={'markets':['台股'],'sources':'官方來源'}
            self.k.discuss(f['id'],f['revision'],'請規劃',values);self.wait();f=self.k.state(f['id'])
            self.assertEqual(f['state'],'ready');self.assertEqual(f['steps'][-1]['role'],'compose');self.assertFalse(self.s.store.tasks())
            task=self.execute(f);self.assertEqual(task['state'],'succeeded',task['error'])
            self.assertIn('離線示範',task['result']['report']);self.assertEqual(self.w.confirm(f['id'],f['revision'],True),task['id'])
            self.assertEqual(len(self.s.store.tasks()),1)
    def test_edit_dismiss_and_binding_changes_invalidate_approval(self):
        f=self.plan();self.w.preview(f['id'],f['revision']);self.k.dismiss(f['id'])
        with self.assertRaises(ValueError):self.w.confirm(f['id'],f['revision'],True)
        p=self.w.preview(f['id'],f['revision']);updated=self.w.update(f['id'],f['revision'],f['steps'])
        with self.assertRaises(ValueError):self.w.confirm(f['id'],p['revision'],True)
        bad=copy.deepcopy(updated['steps']);bad[0]['role']='analysis'
        with self.assertRaises(ValueError):self.w.update(f['id'],updated['revision'],bad)
        self.assertFalse(self.s.store.tasks())
    def test_immutable_snapshot_schedule_dates_disable_and_delete_history(self):
        r=self.save(search=True);f=self.plan(r);task=self.execute(f)
        with self.assertRaises(ValueError):self.k.schedule(f['id'],f['revision'],'08:00',False,True)
        with self.assertRaises(ValueError):self.w.schedule(f['id'],f['revision'],'x','daily','08:00',consent=True)
        sid=self.k.schedule(f['id'],f['revision'],'08:00',True,True)
        d=self.k.copy(r['id']);d['instructions']='不同修訂'
        newer=self.k.save_confirm(self.k.save_preview(d,r['id'],r['revision'])['token'])
        spec=self.w.schedule_spec(self.s.store.schedule(sid),datetime(2026,10,23,tzinfo=timezone.utc))
        self.assertEqual(spec['skill']['revision'],1);self.assertNotEqual(spec['skill']['instructions'],d['instructions']);self.assertIn('2026-10-23',spec['occurrence'])
        p=self.k.manage_preview(r['id'],newer['revision'],'disable');self.assertEqual(p['schedules'][0]['id'],sid)
        self.k.manage_confirm(p['token']);self.assertFalse(self.s.store.schedule(sid)['enabled'])
        with self.assertRaises(ValueError):self.s.engine.set_schedule_enabled(sid,True)
        self.k.manage_confirm(self.k.manage_preview(r['id'],newer['revision'],'delete')['token'])
        self.assertFalse(self.k.list());self.assertEqual(self.s.store.task(task['id'])['state'],'succeeded');self.assertEqual(self.k.state(f['id'])['skill']['revision'],1)
    def test_source_deletion_keeps_approved_skill_work(self):
        f=self.plan();task=self.execute(f)
        p=self.s.engine.preview_conversation_deletion([f['conversation_id']]);self.s.engine.delete_conversations(p['token'])
        self.assertIsNone(self.w.get(f['id'])['conversation_id']);self.assertEqual(self.k.state(f['id'])['task']['id'],task['id'])
    def test_probe_asserts_formats_no_legacy_unlock_and_revision_isolation(self):
        pid=self.company();planner={'message':'合成測試','questions':[],'steps':[{'id':'compose','title':'整理','kind':'assistant','role':'compose','instruction':'整理','inputs':[]}]}
        responses=[json.dumps(planner),json.dumps({'text':'合成測試','facts':{'sample':'6.60'}})]
        with patch.object(self.s.profiles,'respond',side_effect=responses) as call:
            result=self.k.probe(pid,consent=True)
            self.assertEqual(result['roles'],['planner','compose']);self.assertEqual(call.call_count,2)
            contexts=[c.kwargs['context'] for c in call.call_args_list];self.assertNotEqual(contexts[0]['step_id'],contexts[1]['step_id']);self.assertFalse(any(c['search_authorized'] for c in contexts))
        binding=self.k.binding(pid);self.assertNotIn(pid,[p['id'] for p in self.s.profiles.workflow_catalog()])
        with patch.object(self.s.profiles,'respond',return_value='not JSON'):
            self.assertEqual(self.k.probe(pid,consent=True)['roles'],[])
        with self.assertRaises(ValueError):self.k.wrapper.validate_workflow(binding,'planner')
    def test_company_single_id_plan_and_stages_isolated_and_bad_search_stops(self):
        pid=self.company();p=self.s.profiles
        with self.s.store.connection() as db:db.execute('INSERT INTO skill_capabilities VALUES(?,?,?,?,?)',(pid,p.snapshot(pid)['revision'],'test-proof','["planner","compose"]','synthetic'))
        r=self.save();f=self.k.start(r['id'],r['revision'],pid,{},'合成文字')
        response={'message':'規劃','questions':[],'steps':[{'id':'first','title':'整理','kind':'assistant','role':'compose','instruction':'整理原文','inputs':[]},{'id':'final','title':'結果','kind':'assistant','role':'compose','instruction':'整理前一步','inputs':['first']}]}
        with patch.object(p,'respond',side_effect=[json.dumps(response),json.dumps({'text':'第一段','facts':{}}),json.dumps({'text':'完成','facts':{}})]) as call:
            self.k.discuss(f['id'],f['revision'],'規劃',{});self.wait();f=self.k.state(f['id']);task=self.execute(f)
            self.assertEqual(task['state'],'succeeded',task['error']);self.assertEqual(call.call_count,3)
            ctx=[c.kwargs['context'] for c in call.call_args_list]
            self.assertEqual(len({(c['run_id'],c['step_id']) for c in ctx}),3)
            self.assertFalse(any(c['search_authorized'] for c in ctx))
        with self.assertRaises(ValueError):self.k.binding(pid,True)
    def test_cancel_late_planner_and_profile_mutation_guard(self):
        pid=self.company();p=self.s.profiles
        with self.s.store.connection() as db:db.execute('INSERT INTO skill_capabilities VALUES(?,?,?,?,?)',(pid,p.snapshot(pid)['revision'],'test-proof','["planner","compose"]','synthetic'))
        r=self.save();f=self.k.start(r['id'],1,pid,{},'合成文字');started=threading.Event();release=threading.Event()
        def respond(*a,**kw):started.set();release.wait(4);return '{"message":"晚到","questions":[],"steps":[]}'
        with patch.object(p,'respond',side_effect=respond):
            self.k.discuss(f['id'],f['revision'],'規劃',{});self.assertTrue(started.wait(2));self.assertTrue(self.s.engine.has_inflight())
            self.assertFalse(self.api.call('connection_save',{'endpoint':'https://another.example.test/v1'})['ok'])
            with patch.object(self.s,'assert_identity',side_effect=ValueError('expired')):
                receipt=self.api.call('skill_cancel',{'wid':f['id']})
                self.assertEqual(receipt,{'ok':True,'data':{'id':f['id'],'cancelled':True,'identity_expired':True}})
            release.set();self.wait()
        self.assertEqual(self.w.get(f['id'])['state'],'cancelled');self.assertFalse(self.s.store.tasks())
    def test_unknown_planning_post_requires_same_receipt_recovery(self):
        pid=self.company();p=self.s.profiles
        with self.s.store.connection() as db:db.execute('INSERT INTO skill_capabilities VALUES(?,?,?,?,?)',(pid,p.snapshot(pid)['revision'],'test-proof','["planner","compose"]','synthetic'))
        r=self.save();f=self.k.start(r['id'],1,pid,{},'文字報告')
        with patch.object(p,'respond',side_effect=RuntimeError('private-body-never-display')):
            self.k.discuss(f['id'],f['revision'],'規劃',{});self.wait()
        failed=self.k.state(f['id']);self.assertNotIn('private-body',failed['error'])
        with self.assertRaises(ValueError):self.k.discuss(f['id'],failed['revision'],'再試',{})
        with patch.object(p,'inspect_request',return_value={'state':'not_found','recoverable':False}):
            with self.assertRaises(ValueError):self.k.recover(f['id'])
        response={'message':'取回原計畫','questions':[],'steps':[{'id':'done','title':'整理','kind':'assistant','role':'compose','instruction':'整理文字','inputs':[]}]}
        with patch.object(p,'inspect_request',return_value={'state':'polling','recoverable':True}),patch.object(p,'respond',return_value=json.dumps(response)) as call:
            self.k.recover(f['id']);self.wait()
            self.assertEqual(call.call_args.kwargs['context']['run_id'],f['id']+':'+str(failed['revision']))
            self.assertTrue(call.call_args.kwargs['context']['resume'])
        self.assertEqual(self.k.state(f['id'])['state'],'ready');self.assertFalse(self.s.store.tasks())
    def test_search_probe_requires_actual_receipt_and_profile_revision_revokes(self):
        from desktop_app.assistant_sessions import AssistantSessions
        from desktop_app.assistants_gateway import session_context
        from test_support.search_mock import SEARCH_TOOL
        pid=self.company();p=self.s.profiles;p.set_search_policy(p.snapshot(pid),{'tools':[SEARCH_TOOL]})
        planner={'message':'格式','questions':[],'steps':[{'id':'compose','title':'整理','kind':'assistant','role':'compose','instruction':'整理','inputs':[]}]}
        with patch.object(p,'respond',side_effect=[json.dumps(planner)]+[json.dumps({'text':'https://www.python.org/','facts':{'sample':'6.60'}})]*2):
            rejected=self.k.probe(pid,True,True)
            self.assertNotIn('rag',rejected['roles']);self.assertEqual(rejected['checks'][-1]['status'],'failed')
        def response(messages,purpose,binding,context):
            if context['step_id']=='planner':return json.dumps(planner)
            if context['step_id']=='rag':
                key,rid,_,_=session_context(binding,purpose,context)
                AssistantSessions(p.path.parent/'assistant-sessions.sqlite3').save(key,{'thread_id':'synthetic'},rid,
                    {'state':'completed','tool_batches':[{'submit_state':'submitted','calls':[{'state':'completed'}]}]})
            return json.dumps({'text':'合成測試來源 https://www.python.org/','facts':{'sample':'6.60'}})
        with patch.object(p,'respond',side_effect=response) as call:
            result=self.k.probe(pid,True,True);self.assertEqual(result['roles'],['planner','compose','rag']);self.assertEqual(call.call_count,3)
        binding=self.k.binding(pid,True)
        p.set_search_policy(p.snapshot(pid),{'tools':[SEARCH_TOOL]})
        with self.assertRaises(ValueError):self.k.wrapper.validate_workflow(binding,'rag')
    def test_schema_1_through_7_backup_and_transaction_failure(self):
        for version in range(1,8):
            path=Path(self.tmp.name)/('migration'+str(version)+'.sqlite3');store=Store(path)
            with store.connection() as db:
                db.execute('DROP TABLE skill_flows');db.execute('DROP TABLE skill_versions');db.execute('DROP TABLE skills');db.execute('DROP TABLE skill_capabilities')
                if version==1:
                    db.execute('ALTER TABLE conversations DROP COLUMN binding');db.execute('ALTER TABLE conversations DROP COLUMN source')
                db.execute('PRAGMA user_version='+str(version))
            def fail(db):initialize_skill_schema(db);raise ValueError('injected')
            with patch('desktop_app.skills.initialize_skill_schema',side_effect=fail),self.assertRaises(ValueError):Store(path)
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],version)
                self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='skills'").fetchone())
            Store(path)
            with sqlite3.connect(path) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],8)
            for backup in path.parent.glob(path.name+'.pre-v8-*.bak'):
                with sqlite3.connect(backup) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],version)
    def test_cli_skill_selection_requires_interactive_save_and_no_scheduler(self):
        r=self.save();w=Workbench(self.s);out=io.StringIO()
        execute_line(w,'/skill '+r['id']+' demo',io.StringIO(),out)
        self.assertIsNotNone(w.workflow);self.assertFalse(self.s.store.tasks());self.assertIsNone(self.s.scheduler)
        execute_line(w,'/skill-draft demo 整理文字報告',io.StringIO(),out)
        self.assertFalse(self.s.store.tasks());self.assertIn('draft',out.getvalue())
        with self.assertRaises(ValueError):execute_line(w,'/skill-save '+json.dumps({'data':self.k.copy(r['id'])}),io.StringIO(),out)
        self.assertEqual(len(self.k.list()),1)
