"""Actual Tk outcome journeys with synthetic workflow calls and temporary data."""
import unittest
from tkinter import ttk
from unittest.mock import patch

from tests import test_workflow_ui as fixture
from desktop_app.outcomes import OutcomeService


class OutcomeUITests(unittest.TestCase):
    setUp = fixture.WorkflowUITests.setUp
    tearDown = fixture.WorkflowUITests.tearDown
    wait = fixture.WorkflowUITests.wait
    mode = fixture.WorkflowUITests.mode
    ready = fixture.WorkflowUITests.ready
    answer = fixture.WorkflowUITests.answer

    def complete(self):
        self.mode()
        self.app.input.insert('1.0', '整理合成筆記')
        with patch.object(self.app.profiles, 'workflow_call', side_effect=self.answer):
            self.app.send_chat()
            self.ready()
            self.app.workflow_consent.set(True)
            self.app.confirm_workflow()
            self.wait(lambda: self.app.workflows.snapshot(self.app.workflow_id)['task']['state'] == 'succeeded'
                      and not self.app.engine.has_inflight())
        self.app.refresh_lists()
        return self.app.workflows.snapshot(self.app.workflow_id)['task']['id']

    def test_result_opens_outcome_first_and_preserves_draft_selection(self):
        tid = self.complete()
        self.app.input.insert('1.0', '保留這個尚未送出的草稿')
        self.app.input.tag_add('sel', '1.0', '1.2')
        with patch.object(self.app.profiles, 'workflow_call', side_effect=AssertionError('no model')):
            window = self.app.show_workflow_result(tid)
            self.root.update()
            frame = window.outcome_view
            book = frame.master
            self.assertIsInstance(book, ttk.Notebook)
            self.assertEqual(book.tab(book.select(), 'text'), '成果')
            self.assertIn('合成 compose 成果', frame.outcome_text.get('1.0', 'end'))
            self.app.change_theme('light')
            self.assertEqual(self.app.input.get('1.0', 'end-1c'), '保留這個尚未送出的草稿')
            self.assertEqual(self.app.input.get('sel.first', 'sel.last'), '保留')
            window.destroy()

    def test_feedback_background_save_edit_clear_and_no_dispatch(self):
        tid = self.complete()
        service = OutcomeService(self.app.workflows)
        with patch.object(self.app.profiles, 'workflow_call', side_effect=AssertionError('no model')):
            window = self.app.show_workflow_result(tid)
            controls = window.outcome_view.feedback_controls
            controls['note'].set('需要人工確認單位')
            controls['save']('revise')
            self.wait(lambda: controls['status'].get().startswith('已保存：'))
            self.assertEqual(service.feedback(tid)['note'], '需要人工確認單位')
            self.assertEqual(service.feedback(tid)['rating'], 'revise')
            controls['save']('usable')
            self.wait(lambda: controls['status'].get() == '已保存：可採用')
            controls['clear']()
            self.wait(lambda: controls['status'].get() == '已清除評價')
            self.assertIsNone(service.feedback(tid))
            self.assertEqual(controls['note'].get(), '')
            self.assertEqual(self.app.store.task(tid)['state'], 'succeeded')
            window.destroy()

    def test_failed_feedback_retains_note_and_retry_choice(self):
        tid = self.complete()
        window = self.app.show_workflow_result(tid)
        controls = window.outcome_view.feedback_controls
        controls['note'].set('保留備註')
        with patch.object(OutcomeService, 'save_feedback', side_effect=OSError('synthetic disk failure')):
            controls['save']('usable')
            self.wait(lambda: '保存失敗' in controls['status'].get())
        self.assertEqual(controls['note'].get(), '保留備註')
        self.assertIsNone(OutcomeService(self.app.workflows).feedback(tid))
        controls['save']()
        self.wait(lambda: controls['status'].get() == '已保存：可採用')
        self.assertEqual(OutcomeService(self.app.workflows).feedback(tid)['rating'], 'usable')
        with patch.object(OutcomeService, 'clear_feedback', side_effect=OSError('synthetic disk failure')):
            controls['clear']()
            self.wait(lambda: '清除失敗' in controls['status'].get())
        self.assertEqual(OutcomeService(self.app.workflows).feedback(tid)['rating'], 'usable')
        window.destroy()

    def test_outcome_controls_reachable_in_both_themes_and_sizes(self):
        tid = self.complete()
        self.root.deiconify()
        self.app.input.insert('1.0', '保留草稿')
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        for theme in ('dark', 'light'):
            self.app.change_theme(theme)
            window = self.app.show_workflow_result(tid)
            for size in ('1050x700', '1280x860', 'maximized'):
                with self.subTest(theme=theme, size=size):
                    window.state('normal')
                    if size == 'maximized':
                        window.state('zoomed')
                    else:
                        window.geometry(size + '+20+20')
                    self.root.update()
                    controls = {child.cget('text'): child for child in descendants(window)
                                if isinstance(child, ttk.Button)}
                    for label in ('可採用', '需修改', '無幫助', '清除', '保存備註／重試保存', '複製成果'):
                        button = controls[label]
                        self.assertTrue(button.winfo_ismapped(), label)
                        self.assertGreaterEqual(button.winfo_rootx(), window.winfo_rootx(), label)
                        self.assertGreaterEqual(button.winfo_rooty(), window.winfo_rooty(), label)
                        self.assertLessEqual(button.winfo_rootx() + button.winfo_width(),
                                             window.winfo_rootx() + window.winfo_width(), label)
                        self.assertLessEqual(button.winfo_rooty() + button.winfo_height(),
                                             window.winfo_rooty() + window.winfo_height(), label)
                    self.assertEqual(self.app.input.get('1.0', 'end-1c'), '保留草稿')
            window.destroy()


if __name__ == '__main__':
    unittest.main()
