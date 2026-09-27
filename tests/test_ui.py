"""Real Tk widget integration tests; no API, Oracle, AD or Excel claims."""
import gc
import os
import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from desktop_app.config import DEFAULT
from desktop_app.ui import App,ChoiceDialog

class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=tk.Tk()
        if not os.environ.get('UNITHELPER_VISIBLE_TESTS'): self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.tmp.name)); self.root.update()
    def tearDown(self):
        self.app.close(force=True)
        deadline=time.monotonic()+5
        while not self.app.lock.handle.closed and time.monotonic()<deadline: time.sleep(.01)
        self.app=None; self.root=None; gc.collect()
        self.tmp.cleanup()
    def wait_task(self):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            self.root.update(); tasks=self.app.store.tasks()
            if tasks and tasks[0]['state'] in ('succeeded','failed','cancelled'): return tasks[0]
            time.sleep(.01)
        self.fail('Task timeout')
    def test_chat_query_plan_edit_approve_pagination_clipboard(self):
        a=self.app; a.input.insert('end','測試原文'); a.send_chat(); t=self.wait_task()
        self.assertEqual(t['state'],'succeeded'); a.show_chat(); self.assertIn('測試原文',a.transcript.get('1.0','end'))
        a.query_plan.set(True); a.submit_query(); p=a.store.plans()[0]
        self.assertEqual(len(a.store.tasks()),1)
        a.edit_plan(); a.category.set('A'); a.submit_query(); p=a.store.plan(p['id']); self.assertEqual(p['revision'],2)
        a.approve_plan(); a.approve_plan(); t=self.wait_task(); self.assertEqual(len(a.store.tasks()),2)
        a.show_result(t['id']); self.assertIsNotNone(a.result); a.copy_table(False); self.assertIn('000001',a.root.clipboard_get())
        a.query_plan.set(False); a.category.set('all'); a.submit_query(); t=self.wait_task(); a.show_result(t['id']); a.change_page(1)
        self.assertEqual(a.page,1); a.table.selection_set('100'); a.copy_table(True); self.assertEqual(len(a.root.clipboard_get().splitlines()),2)
        a.copy_table(False); self.assertEqual(len(a.root.clipboard_get().splitlines()),151)
    def test_issue_draft_reopen_schedule_and_notifications(self):
        a=self.app; a.issue_title.set('標題'); a.issue_description.insert('end','描述'); a.save_issue(False); iid=a.issue_id
        a.issues.selection_set(iid); a.load_issue(); a.issue_title.set('新標題'); a.save_issue(True)
        self.assertEqual(a.store.issue(iid)['status'],'local_saved')
        a.submit_query(); t=self.wait_task(); sid=a.engine.create_schedule(t['id'],'測試','daily','09:00')
        self.assertFalse(a.store.schedule(sid)['enabled']); a.engine.run_schedule_now(sid,'one'); self.wait_task(); a.refresh_lists()
        self.assertTrue(a.store.notifications()); self.assertTrue(a.schedules.exists(sid))
    def test_widget_choice_submission_and_clipboard_failure(self):
        a=self.app; form=a.forms.create([{'id':'q','title':'確認？','type':'yes_no','options':[{'id':'yes','label':'是'},{'id':'no','label':'否'}]}]); answers=[]
        d=ChoiceDialog(a,form,answers.append)
        with self.assertRaises(ValueError): d.submit()
        d.variables['q'].set('no'); d.submit(); self.assertEqual(answers,[{'q':['no']}])
        with patch.object(a.root,'clipboard_append',side_effect=tk.TclError('busy')):
            with self.assertRaisesRegex(ValueError,'剪貼簿'): a.clipboard('hello')
    def test_company_error_does_not_use_demo_and_restart_history(self):
        a=self.app; a.setting_vars['mode'].set('company')
        with self.assertRaises(ValueError): a.apply_settings()
        self.assertEqual(a.config['assistant']['mode'],'demo')
        def fail_company(messages,purpose,binding):
            from desktop_app.gateways import GatewayError
            raise GatewayError('公司連線失敗')
        a.engine.assistant_router=fail_company; a.input.insert('end','你好'); a.send_chat(); t=self.wait_task()
        self.assertEqual(t['state'],'failed'); self.assertNotIn('示範',t['error'])

    def test_cross_workflow_plan_edit_rejected_and_exit_supported(self):
        a=self.app; a.query_plan.set(True); a.submit_query(); pid=a.store.plans()[0]['id']; a.edit_plan()
        a.plan_mode.set(True); a.input.insert('end','不同工作')
        with self.assertRaises(ValueError): a.send_chat()
        self.assertEqual(a.store.plan(pid)['kind'],'query')
        a.discard_edit(); a.send_chat(); self.assertEqual(len(a.store.plans()),2)

    def test_settings_blocked_while_cancelled_worker_drains(self):
        import threading
        entered=threading.Event(); release=threading.Event()
        def delayed(messages,purpose):
            entered.set(); release.wait(3); return 'late'
        a=self.app; a.engine.assistant_router=lambda messages,purpose,binding:delayed(messages,purpose); a.input.insert('end','資料'); a.send_chat()
        self.assertTrue(entered.wait(2)); a.cancel_latest()
        try:
            with self.assertRaises(ValueError): a.apply_settings()
        finally: release.set()

    def test_visible_widget_layout_and_restart(self):
        a=self.app; self.root.deiconify(); self.root.geometry('1230x830'); self.root.update()
        for key in a.tabs:
            a.book.select(a.tabs[key]); self.root.update()
            self.assertTrue(a.tabs[key].winfo_ismapped())
            self.assertGreater(a.tabs[key].winfo_height(),400)
        a.input.insert('end','重開保留的原文'); a.send_chat(); self.wait_task(); cid=a.conversation
        a.close(force=True)
        deadline=time.monotonic()+5
        while not a.lock.handle.closed and time.monotonic()<deadline: time.sleep(.01)
        self.app=None; self.root=None; del a; gc.collect()
        self.root=tk.Tk(); self.root.withdraw(); self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.tmp.name)); self.root.update()
        self.assertEqual(self.app.store.messages(cid)[0]['text'],'重開保留的原文')

    def test_settings_cannot_change_destination_of_ready_plan(self):
        a=self.app; a.query_plan.set(True); a.submit_query()
        with self.assertRaisesRegex(ValueError,'待批准'): a.apply_settings()

    def test_normal_close_waits_for_remote_then_releases_on_main_thread(self):
        import threading
        entered=threading.Event(); release=threading.Event()
        a=self.app
        def delayed(messages,purpose):
            entered.set(); release.wait(3); return 'late'
        a.engine.assistant_router=lambda messages,purpose,binding:delayed(messages,purpose); a.input.insert('end','測試'); a.send_chat(); self.assertTrue(entered.wait(2))
        with patch('desktop_app.ui.messagebox.askyesno',return_value=True): a.close()
        self.assertFalse(a.lock.handle.closed); release.set()
        deadline=time.monotonic()+5
        while not a.lock.handle.closed and time.monotonic()<deadline:
            self.root.update(); time.sleep(.01)
        self.assertTrue(a.lock.handle.closed)

    def test_navigation_and_minimum_size_keep_actions_visible(self):
        from tkinter import ttk
        a=self.app; self.root.deiconify(); self.root.geometry('1050x700'); self.root.update()
        for key,title,_ in a.routes:
            a.nav_buttons[key].invoke(); self.root.update()
            self.assertEqual(a.book.select(),str(a.tabs[key]))
            self.assertEqual(a.page_title.cget('text'),title)
            def children(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from children(child)
            page=a.tabs[key]; bottom=page.winfo_rooty()+page.winfo_height(); right=page.winfo_rootx()+page.winfo_width()
            for widget in children(page):
                if isinstance(widget,ttk.Button):
                    if widget is a.draft_retry or (key=='todo' and not widget.winfo_ismapped()):
                        continue  # Retry is conditional; narrow todo pages hide inactive columns.
                    if key=='chat' and not widget.winfo_ismapped() and (str(widget).startswith(str(a.action_panel))
                            or str(widget).startswith(str(a.more_options)) or str(widget).startswith(str(a.task_card))
                            or str(widget).startswith(str(a.work_toolbar))
                            or widget in (a.selection_todo,a.selection_handoff,a.cancel_button,a.remove_upload_button)):
                        continue  # Contextual controls are intentionally hidden; action journeys verify their visible state.
                    self.assertTrue(widget.winfo_ismapped(),(key,widget.cget('text')))
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),bottom+2,(key,widget.cget('text')))
                    self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),right+2,(key,widget.cget('text')))

    def test_welcome_shortcut_and_readable_plan_are_not_data_mutations(self):
        a=self.app
        self.assertEqual(a.store.messages(a.conversation),[])
        self.assertIn('今天，想先完成哪件事',a.transcript.get('1.0','end'))
        a.input.insert('end','需要確認的文字'); a.plan_mode.set(True)
        self.assertEqual(a.send_button.cget('text'),'建立計畫')
        a.send_shortcut(); self.assertEqual(a.store.tasks(),[])
        self.assertIn('需要確認的文字',a.plan_preview.get('1.0','end'))
        self.assertNotIn('conversation_id',a.plan_preview.get('1.0','end'))
        a.approve_plan(); self.wait_task()
        self.assertEqual(a.store.messages(a.conversation)[0]['text'],'需要確認的文字')

    def test_dynamic_custom_fields_plan_and_result(self):
        from tests.test_query_schema import catalog
        from desktop_app.query_schema import find_template, parameters
        a=self.app; templates=catalog()
        class Custom:
            def catalog(self): return templates
            def validate(self,q,p): parameters(find_template(templates,q),p)
            def run(self,q,p):
                self.validate(q,p)
                return {'rows':[[p.get('amount','1')]],'columns':[{'name':'value','label':'數值','type':'decimal'}],
                    'parameters':p,'source_label':'合成測試','row_count':1,'truncated':False,'fetched_at_utc':'2026-09-26T00:00:00+00:00'}
        a.queries=Custom(); a.engine.query_catalog=a.queries.catalog; a.engine.query_validator=a.queries.validate; a.engine.query_runner=a.queries.run
        a.reload_query_catalog(); self.assertEqual(len(a.query_vars),6)
        a.query_vars['count'].set('bad'); self.assertEqual(str(a.query_submit['state']),'disabled')
        a.query_vars['count'].set('12'); a.query_plan.set(True); a.submit_query()
        self.assertEqual(a.store.tasks(),[]); self.assertIn('精確金額',a.plan_preview.get('1.0','end'))
        a.edit_plan(); a.query_vars['active'].set('是'); a.submit_query(); a.approve_plan(); t=self.wait_task()
        self.assertIs(t['payload']['parameters']['active'],True)
        a.show_result(t['id']); self.assertIn('123456789012345678.0010',a.result_meta.get())
        sid=a.engine.create_schedule(t['id'],'固定條件','daily','09:00'); a.refresh_lists(); a.schedules.selection_set(sid); a.schedule_details()
        self.assertIn('精確金額',a.schedule_info.get('1.0','end'))
        self.root.deiconify(); self.root.geometry('1050x700'); a.book.select(a.tabs['query']); self.root.update()
        self.assertLessEqual(a.query_submit.winfo_rooty()+a.query_submit.winfo_height(),a.tabs['query'].winfo_rooty()+a.tabs['query'].winfo_height())
        a.query_id.set('DATES'); self.assertEqual(set(a.query_vars),{'begin','until'})
        a.query_id.set('missing'); self.assertEqual(str(a.query_submit['state']),'disabled')
        with self.assertRaises(ValueError): a.submit_query()

    def test_malformed_catalog_and_invalid_schedule_remain_readable(self):
        a=self.app; a.submit_query(); task=self.wait_task(); sid=a.engine.create_schedule(task['id'],'舊模板','daily','09:00')
        a.query_plan.set(True); a.submit_query()
        a.engine.query_catalog=lambda:a.queries.catalog()
        with patch.object(a.queries,'catalog',return_value=[None]):
            a.reload_query_catalog(); self.assertEqual(str(a.query_submit['state']),'disabled')
            a.preview_selected_plan(); self.assertIn('失效',a.plan_preview.get('1.0','end'))
            with self.assertRaises(ValueError): a.edit_plan()
            self.assertIsNone(a.editing_plan)
            a.engine.run_schedule_now(sid,'invalid'); a.refresh_lists(); a.schedules.selection_set(sid); a.schedule_details()
            self.assertIn('無法預覽',a.schedule_info.get('1.0','end')); self.assertTrue(a.runs.get_children())
            nid=a.store.notifications()[0]['id']; a.refresh_lists(); a.notices.selection_set(nid); a.read_notice()
            self.assertIn('失效',a.status.get())
        for bad_type in ([],{}):
            values=a.queries.catalog(); values[0]['parameters']['from_date']['type']=bad_type
            with patch.object(a.queries,'catalog',return_value=values):
                a.reload_query_catalog(); self.assertEqual(str(a.query_submit['state']),'disabled')
