import copy
import gc
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from desktop_app.config import DEFAULT
from desktop_app.ui import App
from desktop_app.gateways import GatewayError

class AssistantUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=tk.Tk();self.root.withdraw()
        self.a=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.temp.name));self.root.update()
    def tearDown(self):
        self.a.close(force=True);self.a=None;self.root=None;gc.collect();self.temp.cleanup()
    def wait(self,tid):
        for _ in range(500):
            self.root.update();t=self.a.store.task(tid)
            if t['state'] in ('succeeded','failed','cancelled'):return t
            time.sleep(.01)
        self.fail('timeout')
    def test_tutorial_initialization_does_not_read_ambient_credentials(self):
        self.a.close(force=True);self.a=None;self.root=None;gc.collect()
        self.root=tk.Tk();self.root.withdraw()
        with patch('desktop_app.profiles.Profiles.key',side_effect=AssertionError('must not read key')):
            self.a=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.temp.name)/'practice',tutorial=True)
        self.assertIn('不讀取',self.a.key_label.cget('text'))
    def test_switch_new_conversation_preserves_private_draft_and_attachment(self):
        a=self.a;old=a.conversation;a.input.insert('end','private draft')
        a.attachment={'name':'original.txt','text':'private attachment','kind':'txt'}
        pid=a.profiles.save('公司文字','real-id','文字用途');a.refresh_profiles()
        a.profile_picker.current(1);a.switch_assistant()
        self.assertNotEqual(a.conversation,old);self.assertEqual(a.store.messages(a.conversation),[])
        self.assertEqual(a.input.get('1.0','end-1c'),'');self.assertIsNone(a.attachment)
        self.assertEqual(a.store.conversation(a.conversation)['binding']['profile_id'],pid)
        self.assertIn('公司助理',a.mode_label.cget('text'))
        a.history.selection_clear(0,'end');a.history.selection_set(a.conversation_ids.index(old));a.choose_chat()
        self.assertEqual(a.input.get('1.0','end-1c'),'private draft')
        self.assertEqual(a.attachment['text'],'private attachment')
    def test_edit_other_assistant_plan_does_not_transfer_private_attachment(self):
        a=self.a;first=a.conversation;a.plan_mode.set(True);a.input.insert('end','A plan');a.send_chat();plan=a.store.plans()[0]
        pid=a.profiles.save('B','id-b');a.refresh_profiles();a.profile_picker.current(1);a.switch_assistant();second=a.conversation
        a.input.insert('end','B draft');a.attachment={'name':'b.txt','kind':'txt','text':'B secret file'}
        self.assertNotIn('目前為示範模式',a.transcript.get('1.0','end'))
        a.plans.selection_set(plan['id']);a.edit_plan()
        self.assertEqual(a.conversation,first);self.assertIsNone(a.attachment);a.send_chat()
        self.assertEqual(a.store.plan(plan['id'])['payload']['text'],'A plan')
        a.history.selection_clear(0,'end');a.history.selection_set(a.conversation_ids.index(second));a.choose_chat()
        self.assertEqual(a.input.get('1.0','end-1c'),'B draft');self.assertEqual(a.attachment['text'],'B secret file')
        self.assertEqual(a.store.tasks(),[])
    def test_selected_rows_preview_only_double_confirm_and_precision(self):
        a=self.a;tid=a.engine.run_query('DEMO02',{'from_date':'2026-01-01','to_date':'2026-01-02','category':'all'})
        self.assertEqual(self.wait(tid)['state'],'succeeded');a.show_result(tid);a.change_page(1);a.table.selection_set('100')
        received=[];a.engine.assistant_router=lambda messages,purpose,binding:received.append(messages) or '摘要'
        a.open_result_handoff();dialog=a.handoff_window;self.root.update()
        self.assertEqual(received,[]);self.assertEqual(len(a.store.tasks()),1)
        dialog.transfer_submit();task=a.store.tasks()[0];self.assertEqual(self.wait(task['id'])['state'],'succeeded')
        source=a.store.conversation(a.conversation)['source'];self.assertEqual(source['rows'],[100]);self.assertEqual(source['task_id'],tid)
        original=a.store.task(tid)['result'];text=received[0][0]['content']
        self.assertIn(str(original['rows'][100][1]),text);self.assertIn(str(original['rows'][100][3]),text)
        self.assertNotIn(str(original['rows'][0][1]),text)
        with self.assertRaises(GatewayError):dialog.transfer_submit()
        self.assertEqual(len(received),1);self.assertEqual(a.store.task(tid)['result'],original)
    def test_transfer_failure_retains_query_and_source(self):
        a=self.a;tid=a.engine.run_query('DEMO01',{'from_date':'2026-01-01','to_date':'2026-01-02','category':'A'});self.wait(tid)
        before=copy.deepcopy(a.store.task(tid)['result']);a.show_result(tid)
        def fail(*args):raise GatewayError('公司回覆失敗')
        a.engine.assistant_router=fail;a.open_result_handoff();a.handoff_window.transfer_submit()
        transfer=a.store.tasks()[0];self.assertEqual(self.wait(transfer['id'])['state'],'failed')
        self.assertEqual(a.store.task(tid)['result'],before);self.assertEqual(a.store.conversation(a.conversation)['source']['task_id'],tid)
    def test_oversize_result_refused_without_truncation_or_task(self):
        a=self.a;tid=a.engine.run_query('DEMO01',{'from_date':'2026-01-01','to_date':'2026-01-02','category':'A'});self.wait(tid);a.show_result(tid)
        a.result['rows'][0][1]='x'*50001
        # Initial preview uses safe(); capture error instead of opening a native modal box.
        errors=[]
        original=a.safe
        def safe(fn):
            try:return fn()
            except GatewayError as e:errors.append(str(e))
        a.safe=safe;a.open_result_handoff();a.safe=original
        self.assertTrue(errors);self.assertEqual(str(a.handoff_window.transfer_confirm['state']),'disabled')
        self.assertEqual(len(a.store.tasks()),1);a.handoff_window.destroy()

