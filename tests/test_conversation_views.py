"""Synthetic real-Tk history cleanup; never changes process DPI or user data."""
import copy
import gc
import tempfile
import threading
import time
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from desktop_app.config import DEFAULT
from desktop_app.ui import App


class ConversationViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        # Local Tk point scaling only: do not initialize process-wide DPI here.
        self.root.tk.call('tk', 'scaling', 96 / 72)
        self.errors_patch = patch('desktop_app.ui.messagebox.showerror')
        self.errors = self.errors_patch.start()
        self.a = App(self.root, config=copy.deepcopy(DEFAULT), directory=Path(self.temp.name))
        self.root.deiconify()
        self.root.geometry('1280x860')
        self.root.update()
        self.root.focus_force()
        self.root.update()

    def tearDown(self):
        self.a.close(force=True)
        deadline = time.monotonic() + 5
        while not self.a.lock.handle.closed and time.monotonic() < deadline:
            time.sleep(.01)
        self.errors_patch.stop()
        self.a = None
        self.root = None
        gc.collect()
        self.temp.cleanup()

    def wait_idle(self):
        deadline = time.monotonic() + 5
        while self.a.engine.has_inflight() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.005)
        self.assertFalse(self.a.engine.has_inflight())
        self.a.refresh_lists()
        self.root.update()

    def remove(self, *ids):
        dialog = self.a.confirm_conversation_deletion(list(ids))
        self.root.update()
        dialog.delete_confirm.invoke()
        self.root.update()
        self.errors.assert_not_called()
        return dialog

    def select_chat(self, cid):
        self.a.refresh_history()
        self.a.history.selection_clear(0, 'end')
        self.a.history.selection_set(self.a.conversation_ids.index(cid))
        self.a.choose_chat()
        self.root.update()

    def test_context_menu_targets_clicked_history_without_switching_chat(self):
        a = self.a
        old = a.conversation
        a.new_chat()
        current = a.conversation
        self.root.update()
        index = a.conversation_ids.index(old)
        bounds = a.history.bbox(index)
        self.assertIsNotNone(bounds)
        event = SimpleNamespace(y=bounds[1] + bounds[3] // 2, x_root=100, y_root=100)
        before_selection = a.history.curselection()
        with patch('desktop_app.conversation_views.tk.Menu') as menu_type, patch.object(a, 'confirm_conversation_deletion') as confirm:
            menu = menu_type.return_value
            a.history_context(event)
            menu.add_command.assert_called_once()
            self.assertEqual(menu.add_command.call_args.kwargs['label'], '刪除此對話')
            menu.add_command.call_args.kwargs['command']()
            confirm.assert_called_once_with([old])
            menu.tk_popup.assert_called_once_with(100, 100)
            menu.grab_release.assert_called_once()
        self.assertEqual(a.conversation, current)
        self.assertEqual(a.history.curselection(), before_selection)

    def test_filtered_bulk_selection_and_cancel_defaults_do_not_delete(self):
        a = self.a
        first = a.store.create_conversation('合成 Alpha 一')
        second = a.store.create_conversation('合成 Alpha 二')
        beta = a.store.create_conversation('合成 Beta')
        before = a.store.conversations()
        manager = a.manage_conversations()
        self.assertIs(a.manage_conversations(), manager)
        manager.history_search.set('alpha')
        manager.history_select_all()
        self.assertEqual(manager.history_chosen, {first, second})
        manager.history_search.set('Beta')
        self.assertEqual(manager.history_chosen, set())
        self.assertEqual(str(manager.history_delete['state']), 'disabled')
        manager.history_toggle(beta)
        self.assertEqual(manager.history_chosen, {beta})
        manager.history_search.set('Alpha')
        manager.history_select_all()
        dialog = a.confirm_conversation_deletion(sorted(manager.history_chosen))
        self.root.update()
        self.assertEqual(dialog.focus_lastfor(), dialog.delete_cancel)
        self.assertEqual(dialog.delete_preview['counts']['conversations'], 2)
        self.assertEqual({c['title'] for c in dialog.delete_preview['conversations']}, {'合成 Alpha 一', '合成 Alpha 二'})
        dialog.delete_cancel.invoke()
        self.root.update()
        self.assertFalse(dialog.winfo_exists())
        self.assertEqual(a.store.conversations(), before)
        self.assertEqual(a.store.tasks(), [])
        manager.history_delete.invoke()
        self.root.update()
        dialogs = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel) and hasattr(w, 'delete_confirm')]
        self.assertEqual(len(dialogs), 1)
        dialogs[0].delete_confirm.invoke()
        self.root.update()
        self.errors.assert_not_called()
        self.assertFalse(manager.history_tree.get_children())
        self.assertEqual(manager.history_chosen, set())
        self.assertEqual(a.store.conversation(beta)['title'], '合成 Beta')

    def test_delete_current_then_last_preserves_other_draft_attachment_and_file(self):
        a = self.a
        kept = a.conversation
        original = Path(self.temp.name) / '原始附件.txt'
        original.write_text('不刪除原檔', encoding='utf-8')
        attachment = {'name': original.name, 'text': '保留附件內容', 'kind': 'txt'}
        a.input.insert('end', '保留對話草稿')
        a.attachment = copy.deepcopy(attachment)
        a.new_chat()
        removed = a.conversation
        a.input.insert('end', '要刪的草稿')
        a.attachment = {'name': '移除引用.txt', 'text': '移除引用', 'kind': 'txt'}
        a.stash_draft()
        self.remove(removed)
        self.assertEqual(a.conversation, kept)
        self.assertEqual(a.input.get('1.0', 'end-1c'), '保留對話草稿')
        self.assertEqual(a.attachment, attachment)
        self.assertNotIn(removed, a.drafts)
        self.assertEqual(original.read_text(encoding='utf-8'), '不刪除原檔')
        self.remove(kept)
        self.assertNotIn(a.conversation, (kept, removed))
        self.assertEqual(len(a.store.conversations()), 1)
        self.assertEqual(a.store.messages(a.conversation), [])
        self.assertEqual(a.input.get('1.0', 'end-1c'), '')
        self.assertIsNone(a.attachment)
        self.assertNotIn(kept, a.drafts)
        self.assertTrue(original.exists())

    def test_deleting_other_chat_keeps_live_draft_attachment_selection(self):
        a = self.a
        removed = a.conversation
        a.input.insert('end', '較早草稿')
        a.new_chat()
        kept = a.conversation
        a.input.insert('end', '目前未送出內容')
        a.input.tag_add('sel', '1.0', '1.2')
        a.attachment = {'name': '目前.txt', 'text': '目前附件', 'kind': 'txt'}
        attachment = copy.deepcopy(a.attachment)
        chosen = a.input.get('sel.first', 'sel.last')
        self.remove(removed)
        self.assertEqual(a.conversation, kept)
        self.assertEqual(a.input.get('1.0', 'end-1c'), '目前未送出內容')
        self.assertEqual(a.attachment, attachment)
        self.assertEqual(a.input.get('sel.first', 'sel.last'), chosen)
        self.assertNotIn(removed, a.drafts)

    def test_pending_plan_details_result_and_source_dialogs_are_cleared(self):
        a = self.a
        cid = a.conversation
        task = a.engine.run_chat(cid, '已完成的合成內容')
        self.wait_idle()
        a.show_result(task)
        plan = a.engine.create_plan('rewrite', {'text': '未批准草稿', 'conversation_id': cid})
        a.refresh_lists()
        a.plans.selection_set(plan)
        a.preview_selected_plan()
        a.edit_plan()
        a.open_work_detail('plan', plan)
        related = tk.Toplevel(self.root)
        related.conversation_source = cid
        self.root.update()
        self.assertIsNotNone(a.editing_plan)
        self.assertIsNotNone(a.preview_plan)
        self.assertEqual(a.workspace_selection, ('plan', plan))
        self.remove(cid)
        self.assertIsNone(a.editing_plan)
        self.assertIsNone(a.preview_plan)
        self.assertEqual(a.plan_preview.get('1.0', 'end-1c'), '')
        self.assertIsNone(a.workspace_selection)
        self.assertFalse(a.detail_requested)
        self.assertIsNone(a.result_task)
        self.assertIsNone(a.result)
        self.assertEqual(a.output.get('1.0', 'end-1c'), '')
        self.assertEqual(str(a.text_copy['state']), 'disabled')
        self.assertEqual(str(a.text_save['state']), 'disabled')
        self.assertFalse(related.winfo_exists())
        self.assertEqual(a.store.tasks(), [])
        self.assertEqual(a.store.plans(), [])

    def test_all_selected_source_handoff_windows_close_other_source_and_copy_survive(self):
        a = self.a
        removed = a.conversation
        other = a.store.create_conversation('其他來源')
        copy_id = a.store.create_conversation('已轉交副本', source={'kind': 'conversation', 'conversation_id': removed})
        a.store.add_message(copy_id, 'user', '獨立轉交內容')

        def preview(cid):
            a.handoff_dialog(lambda scope: ('合成預覽', {'kind': 'conversation', 'conversation_id': cid}))
            return a.handoff_window

        first = preview(removed)
        second = preview(removed)
        independent = preview(other)
        self.root.update()
        self.assertEqual(len(a.handoff_windows), 3)
        self.remove(removed)
        self.assertFalse(first.winfo_exists())
        self.assertFalse(second.winfo_exists())
        self.assertTrue(independent.winfo_exists())
        self.assertEqual(a.store.messages(copy_id)[0]['text'], '獨立轉交內容')
        self.assertIn('來源對話已刪除', a.source_description(a.store.conversation(copy_id)['source']))
        with self.assertRaises(ValueError):
            first.transfer_submit()
        self.assertEqual(a.store.tasks(), [])
        independent.destroy()

    def test_expired_or_changed_confirmation_shows_error_without_deletion(self):
        a = self.a
        cid = a.conversation
        with patch('desktop_app.core.time.monotonic', return_value=1000):
            expired = a.confirm_conversation_deletion([cid])
        with patch('desktop_app.core.time.monotonic', return_value=1600):
            expired.delete_confirm.invoke()
        self.errors.assert_called_once()
        self.assertTrue(expired.winfo_exists())
        self.assertEqual(a.store.conversation(cid)['id'], cid)
        expired.delete_cancel.invoke()
        self.errors.reset_mock()
        changed = a.confirm_conversation_deletion([cid])
        a.store.add_message(cid, 'user', '預覽之後新增內容')
        changed.delete_confirm.invoke()
        self.errors.assert_called_once()
        self.assertIn('變更', a.status.get())
        self.assertTrue(changed.winfo_exists())
        self.assertEqual(a.store.messages(cid)[0]['text'], '預覽之後新增內容')
        changed.delete_cancel.invoke()

    def test_failed_initial_handoff_previews_close_and_late_upload_is_ignored(self):
        a = self.a
        removed = a.conversation
        a.store.add_message(removed, 'user', '合' * 50001)
        a.show_chat()
        a.transcript.tag_add('sel', '1.0', 'end-1c')
        a.open_chat_handoff()  # Production caller must retain source despite overflow.
        oversized = a.handoff_window
        self.errors.assert_called_once()
        self.assertEqual(str(oversized.transfer_confirm['state']), 'disabled')
        self.assertEqual(oversized.handoff_source['conversation_id'], removed)

        def cannot_build(scope):
            raise ValueError('合成預覽組裝失敗')

        a.handoff_dialog(cannot_build, source_hint={'kind': 'conversation', 'conversation_id': removed})
        failed = a.handoff_window
        self.assertEqual(self.errors.call_count, 2)
        self.assertEqual(str(failed.transfer_confirm['state']), 'disabled')
        self.assertEqual(failed.handoff_source['conversation_id'], removed)
        a.new_chat()
        kept = a.conversation
        a.input.insert('end', '其他對話草稿')
        a.attachment = {'name': '保留.txt', 'text': '保留附件', 'kind': 'txt'}
        self.errors.reset_mock()
        self.remove(removed)
        self.assertFalse(oversized.winfo_exists())
        self.assertFalse(failed.winfo_exists())
        before = set(self.root.winfo_children())
        attachment = copy.deepcopy(a.attachment)
        late_data = {'name': '晚到.txt', 'text': '已刪來源的內容', 'preview': '已刪來源的內容', 'kind': 'txt'}
        self.assertIsNone(a.preview_upload(late_data, removed))
        self.root.update()
        self.assertEqual(set(self.root.winfo_children()), before)
        self.assertEqual(a.conversation, kept)
        self.assertEqual(a.attachment, attachment)
        self.assertEqual(a.input.get('1.0', 'end-1c'), '其他對話草稿')
        self.assertEqual(a.store.tasks(), [])
        self.errors.assert_not_called()

    def test_running_and_cancelled_remote_request_refuse_ui_confirmation(self):
        a = self.a
        cid = a.conversation
        idle = a.store.create_conversation('同批次閒置對話')
        entered = threading.Event()
        release = threading.Event()

        def delayed(messages, purpose, binding):
            entered.set()
            release.wait(5)
            return '晚到結果'

        a.engine.assistant_router = delayed
        task = a.engine.run_chat(cid, '等待合成遠端')
        try:
            self.assertTrue(entered.wait(2))
            self.assertIsNone(a.safe(lambda: a.confirm_conversation_deletion([cid, idle])))
            self.errors.assert_called_once()
            self.assertIn('進行中', a.status.get())
            a.engine.cancel_task(task)
            self.errors.reset_mock()
            self.assertIsNone(a.safe(lambda: a.confirm_conversation_deletion([cid, idle])))
            self.errors.assert_called_once()
            self.assertIn('尚未結束', a.status.get())
            self.assertEqual(len(a.store.conversations()), 2)
            dialogs = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel) and hasattr(w, 'delete_preview')]
            self.assertEqual(dialogs, [])
        finally:
            release.set()
            self.wait_idle()
        self.assertEqual(a.store.task(task)['state'], 'cancelled')
        self.assertEqual(len(a.store.messages(cid)), 1)
        self.errors.reset_mock()
        self.remove(cid, idle)
        self.assertEqual(len(a.store.conversations()), 1)
        self.assertEqual(a.store.tasks(), [])


if __name__ == '__main__':
    unittest.main()
