"""Real Tk presentation checks; no company services or antivirus claims."""
import copy
import gc
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from unittest import TestCase
from desktop_app.config import DEFAULT
from desktop_app.ui import App


class WorkspaceTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=tk.Tk();self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.temp.name))
        self.root.deiconify();self.root.geometry('1050x700');self.root.update()

    def tearDown(self):
        self.root.update_idletasks();self.app.close(force=True);self.app=None;self.root=None;gc.collect();self.temp.cleanup()

    def wait_for(self,predicate):
        deadline=time.monotonic()+6
        while time.monotonic()<deadline:
            self.root.update()
            if predicate():return
            time.sleep(.02)
        self.fail('Workspace operation timed out')

    def test_quick_actions_do_not_dispatch_and_composer_grows(self):
        a=self.app
        a.quick_work('summarize');self.root.update()
        self.assertEqual(a.purpose.get(),'整理重點');self.assertEqual(a.store.tasks(),[])
        a.input.insert('end','\n資料'*20);self.root.update()
        self.assertEqual(int(a.input['height']),6)
        draft=a.input.get('1.0','end');a.quick_work('rewrite');self.assertEqual(a.input.get('1.0','end'),draft)
        a.input.delete('1.0','end');self.root.update();self.assertEqual(int(a.input['height']),3)
        a.quick_work('query');self.root.update();self.assertEqual(a.book.select(),str(a.tabs['query']))
        self.assertEqual(a.store.tasks(),[]);self.assertEqual(a.store.plans(),[])

    def test_transcript_refresh_preserves_cross_message_selection_and_scroll(self):
        a=self.app;cid=a.conversation
        tid=a.engine.run_chat(cid,'第一段\n'*80)
        self.wait_for(lambda:a.store.task(tid)['state']=='succeeded')
        a.show_chat();self.root.update()
        text=a.transcript.get('1.0','end');self.assertIn('第一段',text);self.assertIn('QA agent',text)
        a.transcript.tag_add('sel','2.0','end-2c');a.transcript.yview_moveto(.2);self.root.update()
        before=(a.transcript.get('sel.first','sel.last'),a.transcript.yview())
        a.show_chat();a.change_theme('light');self.root.update()
        self.assertEqual(a.transcript.get('sel.first','sel.last'),before[0])
        self.assertAlmostEqual(a.transcript.yview()[0],before[1][0],places=3)
        self.assertIn('QA agent',before[0])
        top=a.transcript.index('@0,0')
        a.toggle_page_hint();self.root.update()
        self.assertEqual(a.transcript.index('@0,0'),top)
        self.assertEqual(a.transcript.get('sel.first','sel.last'),before[0])
        a.toggle_page_hint();self.root.update()
        self.assertEqual(a.transcript.index('@0,0'),top)
        a.store.add_message(cid,'assistant','新增的長回覆\n'*100)
        a.show_chat();self.root.update()
        self.assertEqual(a.transcript.index('@0,0'),top)
        self.assertEqual(a.transcript.get('sel.first','sel.last'),before[0])

    def test_plan_task_states_and_detail_stay_bound_to_selection(self):
        a=self.app;cid=a.conversation
        pid=a.engine.create_plan('chat',{'text':'待批准範例','conversation_id':cid},cid)
        a.refresh_lists();self.assertIn('待批准',a.task_card_label['text']);self.assertEqual(a.store.tasks(),[])
        a.open_chat_detail();self.root.update();self.assertEqual(a.workspace_selection,('plan',pid))
        self.assertEqual(a.detail_mode,'window');self.assertTrue(a.detail_window.winfo_exists())
        self.assertIn('待批准',a.detail_widgets[1]['text'])
        a.new_chat();a.refresh_workspace()
        self.assertEqual(a.workspace_selection,('plan',pid))
        self.assertIn(a.store.conversation(cid)['title'],a.detail_widgets[2].get('1.0','end'))
        self.assertEqual(str(a.task_card_action['state']),'disabled')
        self.root.geometry('1450x860');self.root.update()
        self.assertEqual(a.detail_mode,'panel');self.assertEqual(a.detail_panel.winfo_width(),300)
        self.assertIsNone(a.detail_window)
        a.change_theme('light');self.root.geometry('1050x700');self.root.update()
        self.assertEqual(a.detail_mode,'window');self.assertEqual(a.workspace_selection,('plan',pid))
        a.close_detail();self.assertFalse(a.detail_requested)

    def test_running_cancel_failure_and_no_extra_dispatch(self):
        a=self.app;gate=threading.Event();calls=[]
        def respond(messages,purpose,binding):
            calls.append(messages);gate.wait(4);return '完成'
        a.engine.assistant_router=respond
        try:
            tid=a.engine.run_chat(a.conversation,'範例')
            self.wait_for(lambda:bool(calls));a.refresh_workspace()
            self.assertTrue(a.task_progress_running);self.assertIn('執行中',a.task_card_label['text'])
            a.refresh_page_hint();self.assertIn('正在執行',a.page_hint.cget('text'))
            a.toggle_page_hint();a.toggle_page_hint();self.root.update()
            self.assertEqual(a.store.task(tid)['state'],'running')
            a.open_chat_detail();a.change_theme('light');a.refresh_workspace()
            self.assertEqual(len(calls),1)
            a.engine.cancel_task(tid);a.refresh_workspace();self.assertFalse(a.task_progress_running)
            self.assertIn('已取消',a.task_card_label['text'])
        finally:gate.set()
        self.wait_for(lambda:not a.engine.has_inflight())
        def fail(*args):raise ValueError('合成失敗')
        a.engine.assistant_router=fail
        failed=a.engine.run_chat(a.conversation,'另一筆')
        self.wait_for(lambda:a.store.task(failed)['state']=='failed');a.refresh_workspace()
        self.assertIn('執行失敗',a.task_card_label['text']);self.assertFalse(a.task_progress_running)
        a.refresh_page_hint();self.assertIn('未完成',a.page_hint.cget('text'))
        a.open_chat_detail();self.assertIn('失敗',a.detail_widgets[2].get('1.0','end'))
        self.assertEqual(str(a.detail_widgets[3]['state']),'disabled')

    def test_optional_icons_theme_and_reading_width(self):
        a=self.app
        for size in ('1050x700','1280x860','1450x860'):
            self.root.geometry(size);self.root.update()
            self.assertLessEqual(a.chat_column.winfo_width(),820)
            self.assertEqual(a.send_button.winfo_ismapped(),1)
            self.assertLessEqual(a.send_button.winfo_rooty()+a.send_button.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
        image=a.nav_buttons['chat']['image'];a.change_theme('light');self.assertNotEqual(a.nav_buttons['chat']['image'],image)

    def test_detail_selection_survives_completion_and_source_remains(self):
        a=self.app;gate=threading.Event()
        def respond(*args):gate.wait(4);return '完成'
        a.engine.assistant_router=respond
        try:
            tid=a.engine.run_chat(a.conversation,'範例')
            self.wait_for(lambda:a.store.task(tid)['state']=='running')
            a.open_work_detail('task',tid);self.root.update()
            text=a.detail_widgets[2];pos=text.search('來源：','1.0')
            if not pos:pos=text.search('助理：','1.0')
            text.tag_add('sel',pos,pos+' lineend')
            chosen=text.get('sel.first','sel.last')
            gate.set();self.wait_for(lambda:a.store.task(tid)['state']=='succeeded')
            a.refresh_workspace();self.root.update()
            self.assertEqual(text.get('sel.first','sel.last'),chosen)
        finally:gate.set()

    def test_composer_reflows_without_edit_on_narrowing(self):
        a=self.app;self.root.geometry('1450x860');self.root.update()
        a.input.insert('1.0','長文字測試'*45);self.root.update()
        before=a.input.get('1.0','end');a.input.mark_set('insert','1.10')
        # Opening the side panel changes the real available reading width.
        pid=a.engine.create_plan('chat',{'text':'x','conversation_id':a.conversation},a.conversation)
        a.open_work_detail('plan',pid);self.root.update()
        lines=a.input.count('1.0','end','displaylines')[0]
        self.assertEqual(int(a.input['height']),max(3,min(6,lines)))
        self.assertEqual(a.input.get('1.0','end'),before);self.assertEqual(a.input.index('insert'),'1.10')
