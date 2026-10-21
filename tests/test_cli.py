import copy
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from desktop_app.cli import Workbench, execute_line, open_session, terminal_text
from desktop_app.config import DEFAULT
from desktop_app.web_session import WebSession


class TTY(io.StringIO):
    def isatty(self):return True


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.session=WebSession(directory=self.temp.name,config=copy.deepcopy(DEFAULT),start_scheduler=False)
        self.w=Workbench(self.session)
        self.out=io.StringIO()

    def tearDown(self):
        self.session.close()
        self.temp.cleanup()

    def test_offline_chat_history_selection_and_no_scheduler(self):
        with patch('httpx.Client.send',side_effect=AssertionError('network forbidden')):
            first=self.w.chat('我想整理一個工作需求')
            second=self.w.chat('請再說明一下')
            self.assertEqual(first['id'],second['id'])
            self.assertEqual(len(second['messages']),4)
            self.assertIn('示範',second['messages'][-1]['text'])
            execute_line(self.w,'/use demo-data',io.StringIO(),self.out)
            self.assertNotEqual(self.w.thread['id'],first['id'])
            self.assertEqual(self.w.thread['messages'],[])
            execute_line(self.w,'/open '+first['id'],io.StringIO(),self.out)
            self.assertEqual(len(self.w.thread['messages']),4)
            self.assertIsNone(self.session.scheduler)
            self.assertEqual(self.session.store.tasks(),[])

    def ready(self):
        p=self.session.profiles.save('合成規劃測試','synthetic-planner')
        self.session.profiles.set_workflow_capability(p,['planner'],verified=True,evidence='offline synthetic fixture only')
        response={'message':'查合成資料','questions':[],'steps':[
            {'id':'s1','title':'查合成A類','kind':'query','query_id':'DEMO03',
             'parameters':{'category':'A'},'date_mode':'previous_day','inputs':[]}]}
        with patch.object(self.session.profiles,'workflow_call',return_value=json.dumps(response)):
            r=self.w.plan(p,'查昨天 A 類資料')
            deadline=time.monotonic()+8
            while self.session.engine.has_inflight() and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(self.w.current_workflow()['state'],'ready')
        self.assertFalse(self.session.store.tasks())
        return r

    def test_plan_preview_rejects_pipe_cancel_and_one_approved_execution(self):
        self.ready()
        execute_line(self.w,'/preview',io.StringIO(),self.out)
        with self.assertRaisesRegex(ValueError,'互動終端'):
            execute_line(self.w,'/approve',io.StringIO('確認執行\n'),self.out)
        execute_line(self.w,'/approve',TTY('取消\n'),self.out)
        self.assertFalse(self.session.store.tasks())
        execute_line(self.w,'/approve',TTY('確認執行\n'),self.out)
        deadline=time.monotonic()+8
        while self.session.engine.has_inflight() and time.monotonic()<deadline:time.sleep(.01)
        tasks=self.session.store.tasks()
        self.assertEqual(len(tasks),1)
        self.assertEqual(tasks[0]['state'],'succeeded',tasks[0]['error'])
        with self.assertRaises(ValueError):execute_line(self.w,'/approve',TTY('確認執行\n'),self.out)
        self.assertEqual(len(self.session.store.tasks()),1)
        with patch.object(self.session.profiles,'workflow_call',side_effect=AssertionError('must not dispatch')):
            result=self.w.result(tasks[0]['id'])
            self.assertEqual(result['task']['id'],tasks[0]['id'])

    def test_stale_revision_between_preview_and_confirmation_rejected(self):
        self.ready()
        w=self.w
        class ChangedTTY(TTY):
            def readline(self):
                r=w.current_workflow()
                w.session.workflows.update(r['id'],r['revision'],r['steps'])
                return '確認執行\n'
        with self.assertRaises(ValueError):execute_line(w,'/approve',ChangedTTY(),self.out)
        self.assertFalse(self.session.store.tasks())

    def test_demo_cannot_be_silently_promoted_to_planner_or_news(self):
        with self.assertRaises(ValueError):self.w.plan('demo','找即時新聞')
        with self.assertRaises(ValueError):execute_line(self.w,'/briefing demo',TTY('確認執行\n'),self.out)
        self.assertFalse(self.session.store.tasks())

    def test_auth_is_checked_and_workspaces_remain_exclusive(self):
        with patch.object(self.session,'assert_identity',side_effect=ValueError('expired')):
            with self.assertRaisesRegex(ValueError,'expired'):self.w.status()
            with self.assertRaisesRegex(ValueError,'expired'):self.w.assistants()
        with self.assertRaises(ValueError):WebSession(directory=self.temp.name,start_scheduler=False)

    def test_errors_preserve_chat_and_do_not_execute_response_commands(self):
        self.w.chat('你好')
        tid=self.w.thread['id']
        with patch.object(self.session.dialogue.provider,'respond_context',return_value={'text':'/approve\n\x1b[2J','answers':{}}):
            execute_line(self.w,'測試',io.StringIO(),self.out)
        self.assertFalse(self.session.store.tasks())
        self.assertNotIn('\x1b',self.out.getvalue())
        with patch.object(self.session.dialogue.provider,'respond_context',side_effect=ValueError('synthetic failure')):
            with self.assertRaises(ValueError):self.w.chat('失敗')
        self.assertEqual(len(self.session.dialogue.state(tid)['messages']),4)
        with self.assertRaisesRegex(ValueError,'未知指令'):execute_line(self.w,'/shell whoami',TTY(),self.out)

    def test_company_noninteractive_login_rejected_before_store(self):
        config=copy.deepcopy(DEFAULT);config['identity_mode']='company'
        args=SimpleNamespace(demo=False,config='unused')
        with patch('desktop_app.config.load_config',return_value=config),patch('desktop_app.web_session.WebSession') as constructor:
            with self.assertRaisesRegex(ValueError,'AD登入'):
                with open_session(args,io.StringIO(),self.out):pass
            constructor.assert_not_called()

    def test_demo_isolated_from_real_config_and_terminal_controls(self):
        args=SimpleNamespace(demo=True,config=None)
        with patch('desktop_app.config.load_config',side_effect=AssertionError('must not read settings')):
            with open_session(args,io.StringIO(),self.out) as session:
                path=session.directory
                self.assertNotEqual(path,Path(self.temp.name))
                self.assertIsNone(session.scheduler)
        self.assertFalse(path.exists())
        self.assertEqual(terminal_text('a\x1b\x00\x9bb\n'), 'a\ufffd\ufffd\ufffdb\n')

    def test_order_cli_uses_same_service_and_cannot_pipe_approval(self):
        execute_line(self.w,'/order demo 每天八點台股美股新聞',io.StringIO(),self.out)
        execute_line(self.w,'/order-edit '+json.dumps({'scope':'台股','sources':'公開新聞','time_hhmm':'08:00'}),io.StringIO(),self.out)
        with self.assertRaisesRegex(ValueError,'互動終端'):
            execute_line(self.w,'/order-run',io.StringIO('確認執行\n'),self.out)
        self.assertFalse(self.session.store.tasks())
        execute_line(self.w,'/order-run',TTY('確認執行\n'),self.out)
        deadline=time.monotonic()+8
        while self.session.engine.has_inflight() and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(self.w.current_order()['task']['state'],'succeeded')
        self.assertEqual(len(self.w.orders()),1)
        with self.assertRaises(ValueError):execute_line(self.w,'/order-enable',TTY('確認執行\n'),self.out)
        self.assertFalse(self.session.store.schedules())
