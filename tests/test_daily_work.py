"""Real Tk daily workflows with isolated local data, no company services."""
import copy
import gc
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest import TestCase, mock

from desktop_app.config import DEFAULT
from desktop_app.ui import App


class DailyWorkTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.directory = Path(self.temp.name)
        self.open()

    def open(self):
        self.root = tk.Tk(); self.root.withdraw()
        self.app = App(self.root, config=copy.deepcopy(DEFAULT), directory=self.directory)
        self.root.update()

    def close(self):
        self.root.update_idletasks(); self.app.close(force=True)
        self.app = None; self.root = None; gc.collect()

    def tearDown(self):
        if self.app: self.close()
        self.temp.cleanup()

    def wait(self, predicate):
        until = time.monotonic()+5
        while time.monotonic() < until:
            self.root.update()
            if predicate(): return
            time.sleep(.02)
        self.fail('Daily work operation timed out')

    def test_autosave_reopen_and_attachment_requires_selection(self):
        a = self.app; cid = a.conversation
        a.input.insert('1.0', '保留原文 000123')
        a.purpose.set('改寫文字'); a.plan_mode.set(True)
        a.attachment = {'name':'private.txt','text':'not copied to draft','kind':'txt'}
        self.wait(lambda: a.store.draft(cid) is not None)
        self.assertEqual(a.store.draft(cid)['text'], '保留原文 000123')
        self.close(); self.open(); a = self.app
        self.assertEqual(a.conversation, cid)
        self.assertEqual(a.input.get('1.0','end-1c'), '保留原文 000123')
        self.assertEqual(a.purpose.get(), '改寫文字'); self.assertTrue(a.plan_mode.get())
        self.assertIsNone(a.attachment); self.assertIn('重新選取', a.attachment_label['text'])
        self.assertEqual(a.store.tasks(), [])

    def test_cards_preserve_existing_draft_binding_and_do_not_dispatch(self):
        a = self.app; old = a.conversation
        binding = a.store.conversation(old)['binding']
        a.input.insert('1.0', '原草稿'); a.plan_mode.set(True)
        a.use_work_card('report')
        self.assertNotEqual(a.conversation, old)
        self.assertEqual(a.store.conversation(a.conversation)['binding'], binding)
        self.assertEqual(a.drafts[old][0], '原草稿')
        self.assertTrue(a.plan_mode.get()); self.assertIn('已完成', a.input.get('1.0','end'))
        self.assertEqual(a.store.tasks(), []); self.assertEqual(a.store.plans(), [])
        a.use_work_card('rewrite', '精簡')
        self.assertIn('精簡', a.input.get('1.0','end')); self.assertEqual(a.purpose.get(), '改寫文字')

    def test_failed_save_visible_retry_and_failed_send_keeps_draft(self):
        a = self.app; cid = a.conversation
        a.input.insert('1.0', '不能遺失')
        with mock.patch.object(a.store, 'save_draft', side_effect=OSError('private path')):
            a.queue_draft(force=True)
            self.wait(lambda:'保存失敗' in a.draft_notice['text'])
            self.assertNotIn('private', a.draft_notice['text'])
            self.assertEqual(a.input.get('1.0','end-1c'), '不能遺失')
        a.queue_draft(force=True)
        self.wait(lambda:a.store.draft(cid) is not None)
        with mock.patch.object(a.engine, 'run_chat', side_effect=ValueError('not accepted')):
            with self.assertRaises(ValueError): a.send_chat()
        self.assertEqual(a.store.draft(cid)['text'], '不能遺失')

    def test_failed_submission_rearms_superseded_autosave_without_more_typing(self):
        import threading
        a=self.app;cid=a.conversation
        entered=threading.Event();release=threading.Event()
        original=a.store.save_draft
        def delayed(*args,**kwargs):
            entered.set();release.wait(3)
            return original(*args,**kwargs)
        a.input.insert('1.0','尚未成功保存的文字')
        with mock.patch.object(a.store,'save_draft',side_effect=delayed):
            a.queue_draft(force=True)
            self.assertTrue(entered.wait(2))
            with mock.patch.object(a.engine,'run_chat',side_effect=ValueError('not accepted')):
                with self.assertRaises(ValueError):a.send_chat()
            release.set()
            self.wait(lambda:a.store.draft(cid) is not None)
        self.assertEqual(a.store.draft(cid)['text'],'尚未成功保存的文字')
        self.assertEqual(a.store.tasks(),[])

    def test_accepted_plan_clears_draft_and_late_save_is_rejected(self):
        a = self.app; cid = a.conversation
        a.input.insert('1.0', '等待批准'); a.queue_draft()
        self.wait(lambda:a.store.draft(cid) is not None)
        old = a.draft_versions[cid]
        a.plan_mode.set(True); a.send_chat()
        self.assertEqual(len(a.store.plans()), 1); self.assertEqual(a.store.tasks(), [])
        self.assertIsNone(a.store.draft(cid))
        self.assertFalse(a.store.save_draft(cid, old, 'late', '一般對話', False))

    def test_plan_edit_is_not_autosaved_or_approved_and_original_draft_returns(self):
        a = self.app; cid = a.conversation
        a.input.insert('1.0','原草稿'); a.queue_draft()
        self.wait(lambda:a.store.draft(cid) is not None)
        pid = a.engine.create_plan('chat', {'text':'計畫原文','conversation_id':cid}, cid)
        a.refresh_lists(); a.plans.selection_set(pid); a.edit_plan()
        a.input.insert('end','修改'); a.queue_draft(force=True)
        self.assertEqual(a.store.draft(cid)['text'], '原草稿')
        self.assertEqual(a.store.plan(pid)['revision'], 1)
        a.discard_edit()
        self.assertEqual(a.input.get('1.0','end-1c'), '原草稿')
        self.assertEqual(a.store.tasks(), [])

    def test_deleted_conversation_fences_pending_save_and_keeps_todo(self):
        a = self.app; cid = a.conversation
        a.input.insert('1.0','delete this draft'); a.queue_draft()
        self.wait(lambda:a.store.draft(cid) is not None)
        item = a.store.create_todo('keep', source_conversation_id=cid)
        preview = a.engine.preview_conversation_deletion([cid])
        result = a.engine.delete_conversations(preview['token']); a.conversations_deleted(result)
        self.root.update()
        self.assertIsNone(a.store.draft(cid)); self.assertNotEqual(a.conversation, cid)
        self.assertEqual(a.store.todo(item['id'])['title'], 'keep')

    def test_switch_preserves_drafts_and_does_not_move_to_other_binding(self):
        a = self.app; old = a.conversation
        a.input.insert('1.0','first'); a.new_chat(); new = a.conversation
        a.input.insert('1.0','second'); a.stash_draft()
        a.conversation = old; a.restore_draft()
        self.assertEqual(a.input.get('1.0','end-1c'), 'first')
        self.wait(lambda:a.store.draft(new) is not None)
        self.assertEqual(a.store.draft(new)['text'], 'second')
        a.change_theme('light'); self.root.update()
        self.assertEqual(a.input.get('1.0','end-1c'), 'first')

    def test_query_plan_edit_does_not_discard_ordinary_chat_draft(self):
        a=self.app;cid=a.conversation
        a.query_plan.set(True);a.submit_query()
        plan=a.store.plans()[0];a.plans.selection_set(plan['id']);a.edit_plan()
        a.book.select(a.tabs['chat']);a.input.insert('1.0','查詢計畫旁的普通草稿')
        a.queue_draft(force=True)
        self.wait(lambda:a.store.draft(cid) is not None)
        self.assertEqual(a.store.draft(cid)['text'],'查詢計畫旁的普通草稿')
        self.close();self.open()
        self.assertEqual(self.app.input.get('1.0','end-1c'),'查詢計畫旁的普通草稿')

    def test_name_labels_and_empty_card_visibility(self):
        a = self.app
        p1 = a.profiles.save('同名', 'assistant-one', '文件整理')
        p2 = a.profiles.save('同名', 'assistant-two', '查詢說明')
        a.refresh_profile_picker()
        labels = list(a.profile_picker['values'])
        self.assertEqual(len(labels), len(set(labels)))
        self.assertFalse(any('assistant-one' in x for x in labels))
        a.next_binding = a.profiles.snapshot(p1); a.new_chat()
        self.assertIn('文件整理', a.assistant_usage['text'])
        self.assertIn('待組織確認', a.assistant_usage['text'])
        self.assertEqual(a.work_cards_box.winfo_manager(), 'pack')
        a.store.add_message(a.conversation, 'user', 'something'); a.show_chat()
        self.assertEqual(a.work_cards_box.winfo_manager(), '')
