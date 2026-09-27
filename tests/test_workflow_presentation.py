"""Real Tk, synthetic-only coverage for the read-only workflow progress views."""
import copy
import gc
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk

from desktop_app.config import DEFAULT
from desktop_app.ui import App
from desktop_app.workflow_presenter import detail_text, step_rows


class WorkflowPresentationTests(unittest.TestCase):
    def test_one_explicit_confirmation_runs_only_displayed_plan_once(self):
        a=self.app;a.workflow_mode.set('workflow');a.change_workflow_mode()
        a.input.insert('1.0','整理合成文字')
        with patch.object(a.profiles,'workflow_call',side_effect=self.answer) as call:
            a.send_chat()
            self.wait(lambda:a.workflows.get(a.workflow_id)['state']=='ready' and not a.engine.has_inflight())
            a.refresh_lists()
            self.assertEqual(a.store.tasks(),[]);self.assertEqual(call.call_count,1)
            self.assertFalse(a.workflow_consent.get())
            self.assertIn('指定輸入',a.workflow_consent_button.cget('text'))
            self.assertEqual(a.workflow_buttons['批准並試跑'].cget('text'),'確認執行')
            a.workflow_buttons['批准並試跑'].invoke()
            a.confirm_workflow_from_card()
            self.wait(lambda:not a.engine.has_inflight());a.refresh_lists()
            self.assertEqual(len(a.store.tasks()),1)
            self.assertEqual(a.store.tasks()[0]['state'],'succeeded')
            self.assertFalse(a.workflow_consent.get())

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=tk.Tk();self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.tmp.name))
        self.pid=self.app.profiles.save('品質分析助理','synthetic-id')
        self.app.profiles.set_workflow_capability(self.pid,['planner','analysis','compose'],verified=True,evidence='synthetic-test-only')
        self.app.refresh_workflow_catalog();self.root.update()

    def tearDown(self):
        self.root.update();self.app.close(force=True);self.app=None;self.root=None
        gc.collect();self.tmp.cleanup()

    def wait(self,predicate):
        end=time.monotonic()+5
        while time.monotonic()<end:
            self.root.update()
            if predicate():return
            time.sleep(.01)
        self.fail('workflow presentation timeout')

    def answer(self,messages,role,binding,context):
        if role=='planner':
            return json.dumps({'message':'請核對資料來源，批准後才執行。','questions':[], 'steps':[
                {'id':'s1','title':'分析資料','kind':'assistant','role':'analysis','profile_id':self.pid,'instruction':'分析原始需求','inputs':[]},
                {'id':'s2','title':'產生日報','kind':'assistant','role':'compose','profile_id':self.pid,'instruction':'整理前置成果','inputs':['s1']}]},ensure_ascii=False)
        return json.dumps({'text':'合成成果 '+role,'facts':{}},ensure_ascii=False)

    def prepare(self):
        a=self.app;a.workflow_mode.set('workflow');a.change_workflow_mode()
        a.input.insert('1.0','請分析虛構筆記，再整理日報')
        with patch.object(a.profiles,'workflow_call',side_effect=self.answer):
            a.send_chat();self.wait(lambda:a.workflows.get(a.workflow_id)['state']=='ready' and not a.engine.has_inflight())
        a.refresh_lists();self.root.update()

    def test_unapproved_rows_are_read_only_and_complete_text_remains_selectable(self):
        self.prepare();a=self.app;view=a.workflow_steps_view
        self.assertEqual(view.table.get_children(),('s1','s2'))
        self.assertEqual(view.table.item('s1','values')[0],'01')
        self.assertIn('品質分析助理',view.table.item('s1','values')[2])
        self.assertIn('待批准',view.table.item('s1','values')[3])
        self.assertEqual(a.workflow_notebook.select(),str(view))
        with patch.object(a.profiles,'workflow_call',side_effect=AssertionError('no dispatch')):
            view.table.selection_set('s2');view.selected()
            self.assertEqual(view.source.cget('text'),'來源：分析資料')
            window=a.show_workflow_step(view.rows['s2'],view.record)
            content=window.workflow_step_text.get('1.0','end-1c')
            self.assertIn('s1 · 分析資料',content);self.assertIn('整理前置成果',content)
            self.assertIn('尚無紀錄',content);window.destroy()
            a.workflow_notebook.select(a.workflow_text.master)
            a.workflow_text.tag_add('sel','1.0','1.5');selected=a.workflow_text.get('sel.first','sel.last')
            a.refresh_workflow_view();a.change_theme('light')
            self.assertEqual(a.workflow_notebook.select(),str(a.workflow_text.master))
            self.assertEqual(a.workflow_text.get('sel.first','sel.last'),selected)
        self.assertFalse(a.store.tasks());self.assertFalse(a.store.schedules())

    def test_actual_running_and_failed_steps_retained_and_retry_button_available(self):
        self.prepare();a=self.app;started=threading.Event();release=threading.Event()
        def call(*args):
            started.set();release.wait(4);raise ValueError('合成失敗')
        with patch.object(a.profiles,'workflow_call',side_effect=call):
            a.workflow_consent.set(True);a.confirm_workflow()
            try:
                self.wait(started.is_set);a.refresh_lists()
                view=a.workflow_steps_view
                self.assertIn('處理中',view.table.item('s1','values')[3])
                self.assertIn('等待執行',view.table.item('s2','values')[3])
                view.table.selection_set('s2');view.table.focus('s2');view.selected()
                a.change_theme('light');a.refresh_lists()
                self.assertEqual(view.table.selection(),('s2',))
                self.assertEqual(view.table.tag_configure('running')['foreground'],a.palette.ACCENT)
            finally:release.set()
            self.wait(lambda:a.workflows.snapshot(a.workflow_id)['task']['state']=='failed' and not a.engine.has_inflight())
        a.refresh_lists()
        self.assertIn('需要處理',view.table.item('s1','values')[3])
        self.assertIn('前置未完成',view.table.item('s2','values')[3])
        self.assertTrue(a.workflow_buttons['重試未完成步驟'].winfo_manager())
        self.assertIn('0 / 2',view.summary.cget('text'))
        window=a.show_workflow_step(view.rows['s1'],view.record)
        self.assertIn(view.rows['s1']['observed']['error'],window.workflow_step_text.get('1.0','end'));window.destroy()

    def test_result_window_uses_fixed_snapshot_and_opening_does_not_dispatch(self):
        self.prepare();a=self.app
        with patch.object(a.profiles,'workflow_call',side_effect=self.answer):
            a.workflow_consent.set(True);a.confirm_workflow()
            self.wait(lambda:a.workflows.snapshot(a.workflow_id)['task']['state']=='succeeded' and not a.engine.has_inflight())
        a.refresh_lists();tid=a.workflow_record['task']['id']
        with patch.object(a.profiles,'workflow_call',side_effect=AssertionError('no dispatch')):
            w=a.show_workflow_result(tid);view=w.workflow_steps_view;self.root.update()
            self.assertIn('2 / 2',view.summary.cget('text'))
            self.assertIn('合成成果 compose',detail_text(view.rows['s2'],view.record))
            self.assertEqual(view.rows['s2']['observed']['state'],'succeeded')
            a.workflow_mode.set('chat');a.change_workflow_mode();a.change_theme('light');self.root.update()
            self.assertEqual(view.table.tag_configure('succeeded')['foreground'],a.palette.SUCCESS)
            w.destroy()

    def test_unknown_and_cancelled_are_not_misreported_and_details_do_not_truncate(self):
        binding={'profile_id':self.pid,'revision':1}
        long_text='長篇工作成果\n'*2500
        record={'id':'fixture','state':'approved','task':{'id':'task','state':'failed'},'steps':[
            {'id':'one','title':'保留原文','kind':'assistant','binding':binding,'instruction':long_text,'inputs':[]}],
            'steps_status':[]}
        row=step_rows(record,self.app.workflow_target)[0]
        self.assertEqual(row['state'],'unknown');self.assertIn(long_text,detail_text(row,record))
        record.update(task=None,state='cancelled')
        self.assertEqual(step_rows(record,self.app.workflow_target)[0]['state'],'cancelled')

    def test_small_workspace_keeps_input_approval_and_step_controls_reachable(self):
        self.prepare();a=self.app
        self.root.deiconify();self.root.geometry('1050x700')
        for theme in ('dark','light'):
            a.change_theme(theme);self.root.update()
            for widget in (a.input,a.send_button,a.workflow_buttons['批准並試跑'],a.workflow_steps_view.detail_button):
                self.assertTrue(widget.winfo_viewable(),str(widget))
                self.assertGreater(widget.winfo_height(),4,str(widget))
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height(),str(widget))
            self.assertEqual(a.workflow_steps_view.table.cget('height'),3)


if __name__=='__main__':unittest.main()
