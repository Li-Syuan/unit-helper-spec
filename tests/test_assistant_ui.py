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
    def test_demo_response_does_not_read_company_credentials(self):
        a=self.a
        with patch('desktop_app.profiles.Profiles.key',side_effect=AssertionError('must not read key')):
            a.input.insert('end','整理這段合成文字');a.send_chat()
            task=a.store.tasks()[0]
            self.assertEqual(self.wait(task['id'])['state'],'succeeded')
        self.assertIn('示範',a.store.messages(a.conversation)[-1]['text'])

    def test_profile_editor_individual_shared_remove_and_search_label_without_dispatch(self):
        from tests.test_profiles import MemoryVault
        from tests.test_search_tools import SEARCH_TOOL
        a=self.a;a.profiles.vault=MemoryVault();a.profiles.save_key('shared-synthetic')
        a.profiles.set_wire_mode('assistants');pid=a.profiles.save('synthetic','asst_one')
        a.profiles.set_search_policy(a.profiles.snapshot(pid),{'tools':[SEARCH_TOOL]},chat_enabled=True)
        w=a.edit_profile(pid);self.root.update();controls=w.profile_credentials
        self.assertIn('一般聊天搜尋：已核准',controls['summary'].cget('text'))
        controls['value'].set('individual-synthetic');controls['save'].invoke();self.root.update()
        self.assertEqual(a.profiles.key(a.profiles.snapshot(pid)),'individual-synthetic')
        self.assertEqual(controls['value'].get(),'');self.assertIn('一般聊天搜尋：未核准',controls['summary'].cget('text'))
        with patch.object(a.profiles.vault,'remove',side_effect=RuntimeError('PRIVATE cleanup detail')):
            with patch('desktop_app.assistant_views.messagebox.showwarning') as warning:
                controls['remove'].invoke();self.root.update()
                warning.assert_called_once();self.assertIn('仍可能保留',warning.call_args.args[1])
                self.assertNotIn('PRIVATE',str(warning.call_args))
        with self.assertRaises(GatewayError):a.profiles.key(a.profiles.snapshot(pid))
        controls['shared'].invoke();self.root.update()
        self.assertEqual(a.profiles.key(a.profiles.snapshot(pid)),'shared-synthetic')
        self.assertEqual(str(controls['remove'].cget('state')),'disabled')
        a.change_theme('light');self.root.update();a.change_theme('dark');self.root.update()
        self.assertEqual(a.store.tasks(),[]);w.destroy()
    def test_switch_new_conversation_preserves_private_draft_and_attachment(self):
        a=self.a;old=a.conversation;a.input.insert('end','private draft')
        a.attachment={'name':'original.txt','text':'private attachment','kind':'txt'}
        pid=a.profiles.save('組織文字','real-id','文字用途');a.refresh_profiles()
        a.profile_picker.current(1);a.switch_assistant()
        self.assertNotEqual(a.conversation,old);self.assertEqual(a.store.messages(a.conversation),[])
        self.assertEqual(a.input.get('1.0','end-1c'),'');self.assertIsNone(a.attachment)
        self.assertEqual(a.store.conversation(a.conversation)['binding']['profile_id'],pid)
        self.assertIn('AI 助理',a.mode_label.cget('text'))
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
        def fail(*args):raise GatewayError('組織回覆失敗')
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
