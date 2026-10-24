"""Unified workspace journeys; synthetic providers only, no live services."""
import copy
import json
import re
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from desktop_app.config import DEFAULT
from desktop_app.web_session import WebSession
from desktop_app.dialogue_store import DialogueStore
from desktop_app.dialogue_service import DialogueService
from desktop_app.dialogue_provider import ProfileDialogueProvider
from desktop_app.dialogue_routing import parse
from desktop_app.core import dumps,stamp
from tests.test_dialogue_recovery import SyntheticProfiles
from test_support.assistants_mock import AssistantsMock


def envelope(kind='chat',text='合成答案',goal='',search=False):
    return json.dumps(dict(version=1,kind=kind,text=text,goal=goal,search=search),ensure_ascii=False,indent=2)


class WorkspaceTurnTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.s=WebSession(directory=self.root,config=copy.deepcopy(DEFAULT),start_scheduler=False)
        self.d=self.s.dialogue;self.w=self.s.workspace
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def wait(self):
        deadline=time.monotonic()+8
        while self.s.engine.has_inflight() and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(self.s.engine.has_inflight())
    def profile(self):
        p=self.s.profiles;p.set_endpoint('https://synthetic.example.test/v1');p.set_wire_mode('assistants')
        return p.save('合成助理','asst_synthetic')

    def test_single_turn_plan_confirmation_reopen_dedup_and_independent_deletion(self):
        t=self.d.start('auto');tid=t['id']
        r=self.w.send(tid,'請整理本週已完成的文字工作報告','work-1');self.wait()
        r=self.w.state(tid);job=r['work'];self.assertTrue(r['composing_work']);self.assertFalse(self.s.store.tasks())
        again=self.w.propose(tid,'work-1');self.assertEqual(again['work']['id'],job['id']);self.assertEqual(len(self.s.agents.list()),1)
        self.assertEqual(self.w.send(tid,'請整理本週已完成的文字工作報告','work-1')['work']['id'],job['id'])
        with self.assertRaises(ValueError):self.w.send(tid,'不同內容','work-1')
        self.s.agents.preview(job['id'],job['revision']);self.s.agents.confirm(job['id'],job['revision'],True);self.wait()
        r=self.w.state(tid);self.assertEqual(r['work']['task']['state'],'succeeded');self.assertFalse(r['composing_work'])
        before=len(self.s.store.tasks());self.s.close()
        self.s=WebSession(directory=self.root,config=copy.deepcopy(DEFAULT),start_scheduler=False);self.w=self.s.workspace;self.d=self.s.dialogue
        self.assertEqual(self.w.state(tid)['work']['id'],job['id']);self.assertEqual(len(self.s.store.tasks()),before)
        p=self.d.preview_delete('threads',[tid]);self.d.confirm_delete(p['token'])
        self.assertTrue(self.s.agents.state(job['id'])['source_deleted']);self.assertEqual(len(self.s.store.tasks()),before)

    def test_ambiguity_cancel_stale_source_and_no_provider_authority(self):
        for raw in [envelope()+"x",envelope('chat',goal='execute'),envelope('work',goal='x').replace('"search": false','"search": 1'),dumps({'version':1,'kind':'work','text':'x','goal':'x','search':False,'approved':True})]:
            with self.assertRaises(ValueError):parse(raw)
        for raw in [envelope(kind=[]),envelope(text='  '),envelope().replace('"version": 1','"version": 1,"version": 1')]:
            with self.assertRaises(ValueError):parse(raw)
        t=self.d.start('auto');r=self.w.send(t['id'],'幫我處理一下','clarify')
        self.assertIsNone(r['work']);self.assertFalse(self.s.store.tasks())
        self.w.choose(t['id'],'clarify','chat')
        with self.assertRaises(ValueError):self.w.choose(t['id'],'clarify','work')
        self.assertFalse(self.s.agents.list())
        t=self.d.start('auto');self.w.send(t['id'],'幫我處理一下','old');self.w.send(t['id'],'你好','new')
        with self.assertRaises(ValueError):self.w.choose(t['id'],'old','work')
        with self.assertRaises(ValueError):self.w.choose(t['id'],'old','chat')

    def test_raw_json_history_ten_turns_two_threads_real_sdk_mock_and_reopen(self):
        raw=envelope(text='字元及格式保留\n合成回覆');mock=AssistantsMock(reply=raw)
        provider=ProfileDialogueProvider(SyntheticProfiles(self.root/'profiles.json',mock.handle))
        path=self.root/'wire.sqlite3';d=DialogueService(DialogueStore(path),provider);d.routing_allowed=lambda _:True
        a=d.start('auto','company:fixture:1',memory_snapshot=[{'text':'合成固定記憶'}]);b=d.start('auto','company:fixture:1')
        try:
            for n in range(10):
                for t in (a,b):d.send(t['id'],'第'+str(n)+'輪',t['id']+str(n))
                if n==4:d.close();d=DialogueService(DialogueStore(path),provider);d.routing_allowed=lambda _:True
            self.assertEqual(len(mock.runs),20);self.assertEqual(len(mock.threads),2)
            self.assertEqual(d.state(a['id'])['messages'][1]['text'],'字元及格式保留\n合成回覆')
            with d.store.connect() as db:self.assertEqual(db.execute('SELECT wire FROM dialogue_routes LIMIT 1').fetchone()[0],raw)
            posts=[r for r in mock.requests if r[0]=='POST' and r[1].endswith('/runs')]
            self.assertTrue(all(r[2]['tool_choice']=='none' for r in posts))
            self.assertEqual(sum('合成固定記憶' in r[2].get('content','') for r in mock.requests if r[0]=='POST'),1)
        finally:d.close()

    def test_unknown_send_and_late_cancel_never_create_jobs(self):
        t=self.d.start('auto');tid=t['id'];entered=threading.Event();release=threading.Event();errors=[]
        def responder(*a):
            entered.set();release.wait(3);raw=envelope('work',goal='合成工作');return dict(text='合成答案',answers={},route=parse(raw),wire=raw)
        def run():
            try:self.w.send(tid,'請整理文字','pending')
            except ValueError as ex:errors.append(ex)
        with patch.object(self.d.provider,'respond_context',side_effect=responder):
            worker=threading.Thread(target=run);worker.start();self.assertTrue(entered.wait(2));self.d.stop(tid)
            with self.assertRaises(ValueError):self.d.preview_delete('threads',[tid])
            release.set();worker.join(3)
        self.assertTrue(errors);self.assertFalse(self.s.agents.list());self.assertFalse(self.s.store.tasks())
        with patch.object(self.d.provider,'respond_context',side_effect=AssertionError('must not retry')):
            with self.assertRaises(ValueError):self.w.send(tid,'請整理文字','pending')

    def test_local_link_failure_reconciles_without_second_plan_or_dispatch(self):
        t=self.d.start('auto');tid=t['id'];entered=threading.Event();release=threading.Event()
        original=self.s.agents.planning
        def blocked(*args,**kwargs):
            entered.set();release.wait(3);return original(*args,**kwargs)
        with self.d.store.connect() as db:
            db.execute("CREATE TRIGGER fail_link BEFORE UPDATE OF job_id ON dialogue_routes BEGIN SELECT RAISE(ABORT,'synthetic write failure'); END")
        with patch.object(self.s.agents,'planning',side_effect=blocked):
            try:
                with self.assertRaises(sqlite3.IntegrityError):self.w.send(tid,'請整理文字工作報告','stable')
                self.assertTrue(entered.wait(2))
                with self.assertRaises(ValueError):self.d.preview_delete('threads',[tid])
            finally:release.set();self.wait()
        job=self.s.agents.list()[0]
        with self.d.store.connect() as db:db.execute('DROP TRIGGER fail_link')
        with patch.object(self.s.workflows,'discuss',side_effect=AssertionError('repeat planning')):
            r=self.w.state(tid);self.assertEqual(r['routes'][0]['job_id'],job['id'])
            r=self.w.propose(tid,'stable');self.assertEqual(r['work']['id'],job['id'])
        self.assertEqual(len(self.s.agents.list()),1);self.assertFalse(self.s.store.tasks())

    def test_schema4_backup_and_failed_upgrade_roll_back(self):
        path=self.root/'old.sqlite3'
        with sqlite3.connect(path) as db:
            DialogueStore._upgrade(db);DialogueStore._continuity_upgrade(db);DialogueStore._folders_upgrade(db)
            db.execute("INSERT INTO threads VALUES('old','chat','demo-general','{}',1,'now')")
        original=DialogueStore._workspace_upgrade
        def fail(db):original(db);raise RuntimeError('synthetic rollback')
        with patch.object(DialogueStore,'_workspace_upgrade',side_effect=fail):
            with self.assertRaises(RuntimeError):DialogueStore(path)
        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='dialogue_routes'").fetchone())
        store=DialogueStore(path);self.assertEqual(DialogueService(store).state('old')['mode'],'chat')
        backups=list(self.root.glob('old.sqlite3.pre-v5-*.bak'));self.assertEqual(len(backups),2)
        for p in backups:
            with sqlite3.connect(p) as db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def activation_reply(self,messages,purpose,binding,context=None):
        self.calls.append((purpose,context));pid=binding['profile_id'];sid=context.get('step_id','')
        if context.get('operation')=='activation':
            marker=re.search(r'QA-[a-f0-9]+',dumps(messages)).group()
            second=context['request_id'].endswith(':1')
            return envelope('work' if second else 'chat',marker if second else 'OK',marker if second else '')
        if sid=='planner':return dumps({'message':'合成','questions':[],'steps':[{'id':'compose','title':'整理','kind':'assistant','role':'compose','profile_id':pid,'instruction':'指定文字','inputs':[]}]})
        if sid=='compose':return dumps({'text':'合成','facts':{'sample':'6.60'}})
        if sid=='assess':return dumps({'decision':'needs_input','step_id':'','reason':'缺少來源'})
        return dumps({'action':'ask' if sid=='decision_3' else 'compose','profile_id':'' if sid=='decision_3' else pid,'role':'' if sid=='decision_3' else 'compose','instruction':'合成案例','inputs':['qa_action_1'] if sid=='decision_2' else [],'reason':'合成'})

    def test_activation_eight_calls_separate_proofs_no_search_and_version_guard(self):
        pid=self.profile();self.calls=[]
        with self.assertRaises(ValueError):self.s.activation.run(pid,False)
        with patch.object(self.s.profiles,'respond',side_effect=self.activation_reply):r=self.s.activation.run(pid,True)
        self.assertEqual(len(self.calls),8);self.assertEqual(len(r['stages']),3);self.assertTrue(all(x['passed'] for x in r['stages']))
        self.assertTrue(all(not c.get('search_authorized') for _,c in self.calls));aid=r['assistant_id'];self.assertTrue(self.w.allowed(aid))
        self.assertFalse(self.s.store.tasks());self.assertFalse(self.s.store.schedules())
        from tests.test_search_tools import SEARCH_TOOL
        self.s.profiles.set_search_policy(self.s.profiles.snapshot(pid),{'tools':[SEARCH_TOOL]})
        current=self.s.profiles.snapshot(pid);self.assertFalse(self.w.allowed(f"company:{pid}:{current['revision']}"))

    def test_partial_activation_chat_only_and_cancel_stops_later_requests(self):
        pid=self.profile();self.calls=[]
        def plain(messages,purpose,binding,context=None):
            if context.get('operation')=='activation':return 'OK' if context['request_id'].endswith(':0') else re.search(r'QA-[a-f0-9]+',dumps(messages)).group()
            return 'bad format'
        with patch.object(self.s.profiles,'respond',side_effect=plain):r=self.s.activation.run(pid,True)
        self.assertTrue(r['stages'][0]['passed']);self.assertFalse(r['stages'][0]['routing_passed']);self.assertFalse(r['stages'][1]['passed'])
        self.assertEqual(self.s.activation.status()['chat_profiles'][0]['chat_status'],'passed');self.assertFalse(self.w.allowed(r['assistant_id']))
        def cancel(messages,purpose,binding,context=None):
            value=self.activation_reply(messages,purpose,binding,context);self.s.activation.cancel(pid);return value
        with patch.object(self.s.profiles,'respond',side_effect=cancel):r=self.s.activation.run(pid,True)
        self.assertEqual(len(self.calls),1);self.assertTrue(r['cancelled']);self.assertFalse(r['stages'][0]['passed'])
