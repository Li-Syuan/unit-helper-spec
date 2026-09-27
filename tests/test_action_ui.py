"""Real Tk action routing and confirmation integration; no external service calls."""
import copy
import gc
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from desktop_app.config import DEFAULT
from desktop_app.ui import App
from desktop_app.intent_drafts import example_query


class ActionUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=tk.Tk();self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.tmp.name));self.root.update()
    def tearDown(self):
        self.app.close(force=True);self.app=None;self.root=None;gc.collect();self.tmp.cleanup()
    def wait(self,predicate):
        end=time.monotonic()+5
        while time.monotonic()<end:
            self.root.update()
            if predicate():return
            time.sleep(.01)
        self.fail('UI timeout')
    def test_example_routes_to_local_card_preserves_draft_until_accepted(self):
        a=self.app;a.use_entry('query')
        with patch('desktop_app.intent_drafts.extract_action',side_effect=AssertionError('no AI')):a.send_chat()
        self.assertEqual(a.store.tasks(),[]);self.assertEqual(a.store.messages(a.conversation),[])
        self.assertEqual(a.input.get('1.0','end-1c'),'查昨天 A 類數量合計')
        a.preview_action();self.assertFalse(a.action_confirm_button.instate(['disabled']))
        aid=a.action_id;a.confirm_action();self.wait(lambda:a.actions.snapshot(aid)['status']=='succeeded')
        a.refresh_lists();self.assertEqual(a.input.get('1.0','end-1c'),'')
        self.assertIsNone(a.actions.snapshot(aid)['task']['conversation_id'])
        self.assertEqual(a.store.messages(a.conversation),[])
        self.assertIn('完成',a.transcript.get('1.0','end'))
        a.action_result();self.assertEqual(a.book.select(),str(a.tabs['result']))
        a.return_to_action();self.assertEqual(a.action_id,aid)
        a.action_to_schedule();self.assertEqual(a.action_record['kind'],'schedule')
        a.action_vars['name'].set('合成每日');a.action_vars['time_hhmm'].set('08:00')
        a.preview_action();a.confirm_action();snap=a.actions.snapshot(a.action_id)
        self.assertTrue(snap['schedule']['enabled']);self.assertEqual(a.book.select(),str(a.tabs['chat']))
        a.pause_action_schedule();self.assertFalse(a.actions.snapshot(a.action_id)['schedule']['enabled'])
    def test_navigation_options_selection_and_existing_draft(self):
        a=self.app
        self.assertFalse(a.more_tools.winfo_manager());self.assertFalse(a.more_options.winfo_manager())
        for name in ('chat','todo','schedule','activity'):self.assertEqual(a.nav_buttons[name].winfo_manager(),'pack')
        self.assertFalse(a.cancel_button.winfo_manager());self.assertFalse(a.remove_upload_button.winfo_manager())
        cid=a.conversation;a.input.insert('1.0','保留文字');a.use_entry('text')
        self.assertNotEqual(a.conversation,cid);self.assertEqual(a.drafts[cid][0],'保留文字')
        self.assertIn('虛構',a.input.get('1.0','end'));self.assertEqual(a.store.tasks(),[])
    def test_unknown_and_company_queries_do_not_parse(self):
        a=self.app
        with patch('desktop_app.intent_drafts.extract_action',side_effect=AssertionError('no AI')):
            a.input.insert('1.0','查未知內容');a.send_chat()
            self.assertFalse(a.action_record['spec'].get('query_id'))
            a.preview_action();self.assertTrue(a.action_confirm_button.instate(['disabled']))
        a.cancel_action();self.assertEqual(a.input.get('1.0','end-1c'),'查未知內容')
    def test_manual_edit_and_cancel_reject_late_parse(self):
        a=self.app;record=a.start_action('query','查昨天數量');aid=record['id'];started=threading.Event();release=threading.Event()
        def parse(*args,**kwargs):started.set();release.wait(3);return dict(example_query(),questions=[])
        with patch('desktop_app.intent_drafts.extract_action',parse):
            a.parse_action(record);self.assertTrue(started.wait(1));a.cancel_action();release.set()
            self.wait(lambda:not a.pending_io)
        self.assertEqual(a.actions.get(aid)['state'],'cancelled');self.assertEqual(a.store.tasks(),[])
    def test_plan_stays_in_conversation_and_approves_once(self):
        a=self.app;a.input.insert('1.0','整理虛構筆記');a.plan_mode.set(True);a.send_chat()
        self.assertEqual(a.book.select(),str(a.tabs['chat']));self.assertEqual(a.action_record['kind'],'plan')
        self.assertEqual(a.store.tasks(),[]);a.preview_action();a.confirm_action();self.wait(lambda:bool(a.store.tasks()) and a.store.tasks()[0]['state']=='succeeded')
        self.assertEqual(len(a.store.tasks()),1)
    def test_timeline_refresh_preserves_selection_and_does_not_duplicate(self):
        a=self.app;a.input.insert('1.0','簡單對話');a.send_chat();self.wait(lambda:a.store.tasks()[0]['state']=='succeeded');a.show_chat()
        original=a.transcript.get('1.0','end');a.transcript.tag_add('sel','2.0','2.4');selected=a.transcript.get('sel.first','sel.last')
        for _ in range(3):a.refresh_lists()
        self.assertEqual(a.transcript.get('1.0','end'),original);self.assertEqual(a.transcript.get('sel.first','sel.last'),selected)
        a.start_action('query','查資料',example_query());a.preview_action();a.confirm_action();self.wait(lambda:a.actions.snapshot(a.action_id)['status']=='succeeded');a.refresh_lists()
        self.assertEqual(a.transcript.get('1.0','end').count('點此查看確認卡／結果'),1)

    def test_confirmation_controls_reachable_at_normal_small_and_maximized(self):
        a=self.app;self.root.deiconify()
        for geometry in ('1280x860','1050x700'):
            self.root.state('normal');self.root.geometry(geometry);self.root.update()
            a.start_action('query','查資料',example_query());self.root.update()
            for control in (a.send_button,a.action_confirm_button,a.action_cancel_button):
                self.assertTrue(control.winfo_ismapped(),(geometry,control.cget('text')))
                self.assertLessEqual(control.winfo_rooty()+control.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height()+2)
                self.assertLessEqual(control.winfo_rootx()+control.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width()+2)
        self.root.state('zoomed');self.root.update()
        self.assertTrue(a.action_confirm_button.winfo_ismapped());a.toggle_action_panel();self.root.update()
        self.assertTrue(a.action_confirm_button.winfo_ismapped());self.assertFalse(a.action_scroll.winfo_manager())

    def test_trial_auto_parse_is_background_and_stale_manual_edit_is_retained(self):
        a=self.app;a.close(force=True);self.root=tk.Tk();self.root.withdraw()
        self.app=a=App(self.root,directory=Path(self.tmp.name),groq_trial=True);self.root.update()
        started=threading.Event();release=threading.Event()
        def parse(*args,**kwargs):started.set();release.wait(3);return dict(example_query(),questions=[])
        with patch('desktop_app.intent_drafts.extract_action',parse):
            a.input.insert('1.0','查昨天的數量');a.send_chat();self.assertTrue(started.wait(1))
            self.assertEqual(a.store.tasks(),[])
            a.action_query_name.set(a.action_catalog[0]['name']);a.action_query_changed()
            expected=a.action_record['spec']['query_id']
            for key,value in example_query()['parameters'].items():a.action_param_vars[key].set(value)
            self.assertTrue(a.action_confirm_button.instate(['disabled']))
            release.set();self.wait(lambda:not a.pending_io)
            self.assertFalse(a.action_confirm_button.instate(['disabled']))
        self.assertEqual(a.actions.get(a.action_id)['spec']['query_id'],expected)
        self.assertEqual(a.store.messages(a.conversation),[])

    def test_report_requires_consent_and_edit_resets_it(self):
        a=self.app;a.close(force=True);self.root=tk.Tk();self.root.withdraw()
        self.app=a=App(self.root,directory=Path(self.tmp.name),groq_trial=True);self.root.update()
        proposal=dict(example_query(),time_hhmm='08:00',frequency='daily',weekday=0,date_mode='previous_day',questions=[])
        with patch('desktop_app.intent_drafts.extract_action',return_value=proposal):
            a.input.insert('1.0','每天八點查昨天 A 類數量合計並整理日報');a.send_chat();self.wait(lambda:not a.pending_io)
        self.assertTrue(a.action_confirm_button.instate(['disabled']))
        self.assertFalse(a.action_preview_button.winfo_manager());self.assertNotIn('frequency',a.action_vars)
        a.action_consent.set(True);a.action_consent_changed();self.assertFalse(a.action_confirm_button.instate(['disabled']))
        a.action_vars['time_hhmm'].set('09:00');self.assertFalse(a.action_consent.get());self.assertTrue(a.action_confirm_button.instate(['disabled']))
        a.action_consent.set(True);a.action_consent_changed();a.confirm_action()
        self.assertEqual(a.store.tasks(),[]);self.assertTrue(a.actions.snapshot(a.action_id)['schedule']['enabled'])
        self.assertEqual(a.book.select(),str(a.tabs['chat']))

    def test_catalog_dynamic_fields_and_unmapped_schedule_dates(self):
        a=self.app
        catalog=[{'id':'COMPANY_TEST','name':'動態核准查詢','parameters':{'count':{'type':'integer','label':'件數','default':1},'approved':{'type':'boolean','label':'核對','default':False},'group':{'type':'single_choice','label':'組別','options':['X','Y'],'default':'X'}}}]
        with patch.object(a.queries,'catalog',return_value=catalog):
            a.engine.query_catalog=lambda:catalog
            a.start_action('schedule','設定動態自動工作')
            a.action_query_name.set('動態核准查詢');a.action_query_changed()
            self.assertEqual(set(a.action_param_vars),{'count','approved','group'})
            self.assertEqual(a.action_vars['date_mode'].get(),'使用固定日期')
            a.action_param_vars['count'].set('7');a.action_param_vars['approved'].set('是')
            spec=a.actions.get(a.action_id)['spec'];self.assertEqual(spec['parameters']['count'],7);self.assertIs(spec['parameters']['approved'],True)
            self.assertNotIn('weekday',a.action_vars)
            a.action_vars['frequency'].set('每週');self.assertIn('weekday',a.action_vars)

    def test_copy_in_card_keeps_chat_and_activity_opens_pending_action(self):
        a=self.app;a.use_entry('query');a.send_chat();aid=a.action_id
        self.assertFalse(a.action_confirm_button.instate(['disabled']))
        a.refresh_lists();self.assertTrue(a.activity_tree.exists('action:'+aid))
        a.activity_tree.selection_set('action:'+aid);a.open_activity();self.assertEqual(a.action_id,aid)
        a.confirm_action();self.wait(lambda:a.actions.snapshot(aid)['status']=='succeeded');a.refresh_lists()
        a.copy_action_result();self.assertEqual(a.book.select(),str(a.tabs['chat']));self.assertTrue(a.root.clipboard_get())
        a.start_action('choose','討論自動工作');a.input.insert('1.0','討論自動工作');a.discuss_action()
        self.wait(lambda:any(t['conversation_id']==a.conversation and t['state']=='succeeded' for t in a.store.tasks()))
        self.assertEqual(len(a.store.messages(a.conversation)),2)

    def test_repeated_send_reuses_pending_card_and_missing_report_rule_is_explicit(self):
        a=self.app;a.input.insert('1.0','查昨天 A 類數量合計');a.send_chat();aid=a.action_id;a.send_chat()
        self.assertEqual(a.action_id,aid);self.assertEqual(len(a.actions.list(a.conversation)),1)
        a.close(force=True);self.root=tk.Tk();self.root.withdraw()
        self.app=a=App(self.root,directory=Path(self.tmp.name),groq_trial=True);self.root.update()
        spec=dict(example_query(),time_hhmm='08:00',name='合成日報',frequency='',weekday=0,date_mode='')
        a.start_action('report','整理日報',spec);a.action_consent.set(True);a.action_consent_changed()
        self.assertTrue(a.action_confirm_button.instate(['disabled']))
        a.adopt_report_rule();self.assertFalse(a.action_consent.get());a.action_consent.set(True);a.action_consent_changed()
        self.assertFalse(a.action_confirm_button.instate(['disabled']))

    def test_schedule_source_return_and_deleted_source_label(self):
        a=self.app;cid=a.conversation;spec=dict(example_query(),name='來源測試',time_hhmm='08:00',frequency='daily',weekday=0,date_mode='previous_day')
        a.start_action('schedule','定期查詢來源',spec);a.confirm_action();aid=a.action_id;sid=a.actions.snapshot(aid)['schedule']['id']
        a.new_chat();a.schedules.selection_set(sid);a.schedule_details()
        self.assertIn('來源對話：',a.schedule_info.get('1.0','end'));self.assertFalse(a.schedule_source_button.instate(['disabled']))
        a.open_schedule_source();self.assertEqual(a.conversation,cid);self.assertEqual(a.action_id,aid)
        a.new_chat();preview=a.engine.preview_conversation_deletion([cid]);a.engine.delete_conversations(preview['token'])
        a.schedules.selection_set(sid);a.schedule_details();self.assertIn('來源對話已刪除',a.schedule_info.get('1.0','end'));self.assertTrue(a.schedule_source_button.instate(['disabled']))

    def test_immediate_test_double_click_and_busy_are_one_run(self):
        a=self.app;spec=dict(example_query(),name='立即測試',time_hhmm='08:00',frequency='daily',weekday=0,date_mode='previous_day')
        a.start_action('schedule','定期查詢',spec);a.confirm_action();aid=a.action_id
        a.run_action_now();self.wait(lambda:a.actions.snapshot(aid)['status']=='succeeded')
        self.assertEqual(len(a.store.tasks()),1);a.run_action_now();self.assertEqual(len(a.store.tasks()),1)
        a.refresh_lists();self.assertTrue(a.action_run_button.instate(['disabled']))
        a.action_run_deadlines[aid]=time.monotonic()-1;a.refresh_lists();self.assertFalse(a.action_run_button.instate(['disabled']))
        a.run_action_now();self.wait(lambda:len(a.store.tasks())==2 and a.actions.snapshot(aid)['status']=='succeeded')

    def test_summary_does_not_route_embedded_query_words(self):
        a=self.app;a.purpose.set('整理重點');a.input.insert('1.0','虛構：已完成報告，明天檢查資料。');a.send_chat()
        self.wait(lambda:a.store.tasks() and a.store.tasks()[0]['state']=='succeeded')
        self.assertEqual(a.actions.list(a.conversation),[]);self.assertEqual(a.store.tasks()[0]['kind'],'summarize')

    def test_navigation_text_and_query_fields_remain_visible_at_current_dpi(self):
        from tkinter import ttk
        a=self.app;self.root.deiconify();a.display.size_window(self.root,1050,700,(1050,700));a.use_entry('query');a.send_chat();self.root.update()
        for theme in ('light','dark'):
            a.change_theme(theme);self.root.update()
            for key in ('chat','schedule','activity','settings','issue'):
                self.assertEqual(str(a.nav_buttons[key].cget('compound')),'left');self.assertTrue(a.nav_buttons[key].cget('text').strip())
            self.assertGreaterEqual(a.action_canvas.winfo_height(),a.display.px(190))
            self.assertGreaterEqual(a.transcript.winfo_height(),a.display.px(50))
            bottom=a.action_canvas.winfo_rooty()+a.action_canvas.winfo_height()
            def children(widget):
                for child in widget.winfo_children():yield child;yield from children(child)
            for widget in children(a.action_body):
                if isinstance(widget,ttk.Entry):self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),bottom)
            self.assertIn('不傳送資料給助理',a.action_boundary.cget('text'));self.assertIn('尚未執行',a.action_boundary.cget('text'))

    def test_report_consent_is_visible_without_scrolling_at_minimum_size(self):
        self.app.close(force=True);self.root=tk.Tk()
        self.app=a=App(self.root,directory=Path(self.tmp.name),groq_trial=True)
        a.display.size_window(self.root,1050,700,(1050,700))
        a.start_action('report','合成日報',dict(example_query(),name='合成日報',time_hhmm='08:00',frequency='daily',weekday=0,date_mode='previous_day'))
        for theme in ('light','dark'):
            a.change_theme(theme);self.root.update()
            box=a.action_consent_checkbox
            self.assertTrue(box.winfo_ismapped())
            self.assertLessEqual(box.winfo_rooty()+box.winfo_height(),a.action_confirm_button.winfo_rooty())
            self.assertLessEqual(a.action_confirm_button.winfo_rooty()+a.action_confirm_button.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
        self.assertEqual(a.store.tasks(),[]);self.assertEqual(a.store.schedules(),[])

    def test_failed_query_retry_only_prepares_new_confirmation(self):
        a=self.app;a.use_entry('query');a.send_chat();aid=a.action_id
        with patch.object(a.engine,'query_runner',side_effect=ValueError('synthetic failure')):
            a.confirm_action();self.wait(lambda:a.actions.snapshot(aid)['status']=='failed')
        a.refresh_lists();a.retry_query_action()
        self.assertNotEqual(a.action_id,aid);self.assertEqual(len(a.store.tasks()),1)
        a.confirm_action();self.wait(lambda:a.actions.snapshot(a.action_id)['status']=='succeeded')
        self.assertEqual(len(a.store.tasks()),2)

    def test_plan_approved_in_advanced_tools_shows_real_result(self):
        a=self.app;a.input.insert('1.0','整理合成文字');a.plan_mode.set(True);a.send_chat();aid=a.action_id
        plan=a.store.plans()[0];tid=a.engine.confirm_plan(plan['id'],plan['revision'],'advanced-approval')
        self.wait(lambda:a.store.task(tid)['state']=='succeeded');a.show_action(aid);self.root.update()
        self.assertEqual(a.actions.snapshot(aid)['status'],'succeeded')
        self.assertTrue(a.action_result_button.winfo_manager());self.assertFalse(a.action_confirm_button.winfo_manager())
