"""Real Tk workflow journeys with synthetic model replies, never external calls."""
import copy
import gc
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from desktop_app.config import DEFAULT
from desktop_app.ui import App


class WorkflowUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=tk.Tk();self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.tmp.name))
        self.pid=self.app.profiles.save('測試助理','synthetic-id')
        self.app.profiles.set_workflow_capability(self.pid,['planner','analysis','review','compose'],verified=True,evidence='synthetic-test-only')
        self.app.refresh_workflow_catalog();self.root.update()
    def tearDown(self):
        self.root.update()
        self.app.close(force=True);self.app=None;self.root=None;gc.collect();self.tmp.cleanup()
    def wait(self,predicate):
        end=time.monotonic()+5
        while time.monotonic()<end:
            self.root.update()
            if predicate():return
            time.sleep(.01)
        self.fail('workflow UI timeout')
    def mode(self):
        self.app.workflow_mode.set('workflow');self.app.change_workflow_mode()
    def answer(self,messages,role,binding,context):
        if role=='planner':return json.dumps({'message':'先分析再整理；請批准。','questions':[],
            'steps':[{'id':'s1','title':'分析','kind':'assistant','role':'analysis','profile_id':self.pid,'instruction':'整理使用者需求','inputs':[]},
                     {'id':'s2','title':'彙整','kind':'assistant','role':'compose','profile_id':self.pid,'instruction':'產生報告','inputs':['s1']}]},ensure_ascii=False)
        return json.dumps({'text':'合成 '+role+' 成果','facts':{}},ensure_ascii=False)
    def ready(self):
        self.wait(lambda:self.app.workflows.get(self.app.workflow_id)['state']=='ready' and not self.app.engine.has_inflight())
        self.app.refresh_lists()
    def test_conversation_plan_executes_only_after_consent_and_preserves_chat(self):
        a=self.app;self.mode();a.input.insert('1.0','請分析虛構筆記再整理報告')
        with patch.object(a.profiles,'workflow_call',side_effect=self.answer) as call:
            a.send_chat();self.ready()
            self.assertEqual(call.call_count,1);self.assertEqual(a.store.tasks(),[]);self.assertEqual(a.store.messages(a.conversation),[])
            self.assertIn('批准',a.workflow_text.get('1.0','end'))
            with self.assertRaises(ValueError):a.confirm_workflow()
            a.workflow_consent.set(True);a.confirm_workflow()
            self.wait(lambda:a.workflows.snapshot(a.workflow_id)['task']['state']=='succeeded')
            a.refresh_lists();self.assertEqual(call.call_count,3);self.assertEqual(len(a.store.tasks()),1)
            self.assertIn('合成 compose 成果',a.workflow_text.get('1.0','end'))
            self.assertTrue(a.workflow_buttons['設為自動工作'].winfo_manager())
            a.workflow_mode.set('chat');a.change_workflow_mode();self.assertTrue(a.transcript.winfo_manager())
    def test_mode_selection_does_not_dispatch_and_attachment_not_silently_sent(self):
        a=self.app;a.input.insert('1.0','草稿留著');original=a.input.get('1.0','end-1c')
        with patch.object(a.profiles,'workflow_call',side_effect=AssertionError('no call')):
            self.mode();a.refresh_lists();self.assertEqual(a.input.get('1.0','end-1c'),original)
            a.attachment={'name':'test.txt','kind':'text','text':'not approved'}
            with self.assertRaisesRegex(ValueError,'附件'):a.send_chat()
            self.assertEqual(a.workflows.list(a.conversation),[]);self.assertEqual(a.attachment['text'],'not approved')
            a.change_theme('light');self.assertEqual(a.input.get('1.0','end-1c'),original)
    def test_followup_discussion_questions_and_revision(self):
        a=self.app;self.mode();a.input.insert('1.0','幫我整理')
        question={'message':'請選用途','questions':[{'id':'q','text':'整理用途？','type':'single','options':['報告','信件']}],'steps':[]}
        with patch.object(a.profiles,'workflow_call',return_value=json.dumps(question,ensure_ascii=False)):
            a.send_chat();self.wait(lambda:a.workflows.get(a.workflow_id)['state']=='draft' and not a.engine.has_inflight());a.refresh_lists()
        self.assertTrue(a.workflow_buttons['批准並試跑'].instate(['disabled']))
        revision=a.workflow_record['revision'];a.input.insert('1.0','選報告，請先分析再彙整')
        with patch.object(a.profiles,'workflow_call',side_effect=self.answer):a.send_chat();self.ready()
        self.assertGreater(a.workflow_record['revision'],revision);self.assertEqual(a.store.tasks(),[])
        a.workflow_text.tag_add('sel','1.0','1.2');text=a.workflow_text.get('sel.first','sel.last')
        a.refresh_lists();a.change_theme('light');self.assertEqual(a.workflow_text.get('sel.first','sel.last'),text)
    def test_unverified_company_catalog_blocked_and_reopen_latest_local_plan(self):
        a=self.app;self.mode();a.input.insert('1.0','先討論')
        with patch.object(a.profiles,'workflow_call',side_effect=self.answer):a.send_chat();self.ready()
        wid=a.workflow_id;a.workflow_selected.clear();a.refresh_workflow_view();self.assertEqual(a.workflow_id,wid)
        a.new_workflow();self.assertIsNone(a.workflow_id)
        a.profiles.set_workflow_capability(self.pid,['planner'],verified=False);a.refresh_workflow_catalog()
        a.input.insert('1.0','另一個工作')
        with self.assertRaisesRegex(ValueError,'規劃助理'):a.send_chat()
        self.assertEqual(a.store.tasks(),[])

    def test_mode_restores_per_conversation_without_dispatch(self):
        from desktop_app.preferences import load_preferences
        a=self.app;cid=a.conversation;self.mode();a.input.insert('1.0','待討論草稿')
        a.new_chat();self.assertEqual(a.workflow_mode.get(),'chat')
        a.stash_draft();a.conversation=cid;a.restore_draft();a.show_chat()
        self.assertEqual(a.workflow_mode.get(),'workflow');self.assertEqual(a.input.get('1.0','end-1c'),'待討論草稿')
        self.assertEqual(load_preferences(a.preferences_path)['conversation_modes'][cid],'workflow')
        self.assertEqual(a.store.tasks(),[]);self.assertEqual(a.workflows.list(cid),[])

    def test_accepted_discussion_clears_saved_draft_and_fences_late_save(self):
        a=self.app;self.mode();cid=a.conversation
        revision=a.store.reserve_draft(cid)
        a.store.save_draft(cid,revision,'先前草稿','一般對話',False,False)
        late=a.store.reserve_draft(cid)
        a.input.insert('1.0','合成需求討論')
        with patch.object(a.profiles,'workflow_call',side_effect=self.answer):
            a.send_chat();self.ready()
        self.assertIsNone(a.store.draft(cid))
        self.assertFalse(a.store.save_draft(cid,late,'晚到的舊草稿','一般對話',False,False))
        self.assertIsNone(a.store.draft(cid))

    def test_retained_workflow_table_paging_copy_and_no_dispatch(self):
        a=self.app
        result={'columns':[{'name':'code','label':'代碼','type':'text'},{'name':'value','type':'decimal'}],
                'rows':[['=unsafe'+str(i),'1234567890.123456789'] for i in range(205)],'parameters':{},'fetched_at_utc':'2026-09-27T00:00:00+00:00'}
        with patch.object(a,'clipboard') as clipboard,patch.object(a.profiles,'workflow_call',side_effect=AssertionError('no dispatch')):
            w=a.show_workflow_table(result);self.root.update();self.assertEqual(len(w.workflow_table.get_children()),100)
            w.workflow_table.selection_set('0');w.workflow_page(1);w.workflow_table.selection_set('100');w.workflow_copy(True)
            text=clipboard.call_args.args[0];self.assertIn("'=unsafe0",text);self.assertIn("'=unsafe100",text)
            self.assertEqual(text.count('1234567890.123456789'),2)
            w.workflow_copy(False);self.assertEqual(clipboard.call_args.args[0].count('1234567890.123456789'),205)
            w.destroy()


if __name__=='__main__':unittest.main()
