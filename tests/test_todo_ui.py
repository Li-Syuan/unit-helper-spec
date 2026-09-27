"""Synthetic real-Tk todo interactions; no company service or user profile."""
import gc
from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from desktop_app.core import Store
from desktop_app.display import Display
from desktop_app.preferences import load_preferences, update_preferences
from desktop_app.theme import Appearance
from desktop_app.todo_views import TodoViews, taipei_today


class TodoHarness(TodoViews):
    def __init__(self, root, directory):
        self.root = root
        self.display = Display(root, factor=1)
        self.preferences_path = directory / 'ui-preferences.json'
        self.appearance = Appearance(root)
        self.store = Store(directory / 'test.sqlite')
        self.status = tk.StringVar(master=root)
        self.errors = []
        self.conversation = self.store.create_conversation('合成來源對話')
        self.book = ttk.Notebook(root)
        self.book.pack(fill='both', expand=True)
        self.tabs = {key: ttk.Frame(self.book) for key in ('chat', 'todo')}
        for key, page in self.tabs.items():
            self.book.add(page, text=key)
        self.transcript = tk.Text(self.tabs['chat'], exportselection=False)
        self.transcript.pack(fill='both', expand=True)
        self.build_todos()
        self.appearance.apply(root)

    def safe(self, action):
        try:
            return action()
        except Exception as exc:
            self.errors.append(exc)

    def button(self, parent, text, action, style=None):
        return ttk.Button(parent, text=text, style=style or 'TButton', command=lambda: self.safe(action))


class TodoViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.root.tk.call('tk', 'scaling', 96 / 72)
        self.root.geometry('1100x740')
        self.a = TodoHarness(self.root, Path(self.temp.name))
        self.root.update()
        self.root.focus_force()

    def tearDown(self):
        self.root.update_idletasks()
        self.root.destroy()
        self.a = None
        self.root = None
        gc.collect()
        self.temp.cleanup()

    def create(self, title='合成待辦', **kwargs):
        item = self.a.store.create_todo(title, **kwargs)
        self.a.refresh_todos()
        self.root.update()
        return item

    def test_selection_copies_all_text_without_dispatch_or_forced_navigation(self):
        a = self.a
        original = '\n第一項工作\n跨行完整文字：00123456789012345678\n第二項補充\n'
        a.transcript.insert('1.0', original)
        a.transcript.tag_add('sel', '1.0', 'end-1c')
        a.book.select(a.tabs['chat'])
        dialog = a.add_selected_todo()
        self.assertEqual(dialog.todo_title.get(), '第一項工作')
        self.assertEqual(dialog.todo_description.get('1.0', 'end-1c'), original)
        before_tab = a.book.select()
        with patch.object(a.store, 'create_todo', wraps=a.store.create_todo) as create:
            dialog.todo_save_action()
            dialog.todo_save_action()
            create.assert_called_once()
            self.assertEqual(create.call_args.kwargs['request_id'], dialog.todo_request_id)
        self.assertEqual(a.book.select(), before_tab)
        rows = a.store.todos()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['description'], original)
        self.assertEqual(rows[0]['source_conversation_id'], a.conversation)
        self.assertTrue(a.todo_saved_notice.winfo_exists())
        self.assertEqual(a.errors, [])

    def test_empty_selection_and_overlong_title_never_silently_truncate(self):
        a = self.a
        with self.assertRaises(ValueError):
            a.add_selected_todo()
        text = '長' * 121 + '\n原文要保留'
        dialog = a.open_todo(text=text)
        self.assertEqual(dialog.todo_title.get(), '長' * 121)
        dialog.todo_save_action()
        self.assertIn('120', dialog.todo_error.get())
        self.assertEqual(a.store.todos(), [])
        self.assertEqual(dialog.todo_description.get('1.0', 'end-1c'), text)
        dialog.todo_title.set('自行修改標題')
        dialog.todo_save_action()
        self.assertEqual(a.store.todos()[0]['description'], text)

    def test_editor_validates_date_and_description_without_creating_rows(self):
        dialog = self.a.open_todo(text='合成工作')
        dialog.todo_due.set('2026-02-30')
        dialog.todo_save_action()
        self.assertIn('有效日期', dialog.todo_error.get())
        dialog.todo_due.set('2026-09-30')
        dialog.todo_description.delete('1.0', 'end')
        dialog.todo_description.insert('1.0', '文' * 50001)
        dialog.todo_save_action()
        self.assertIn('50,000', dialog.todo_error.get())
        self.assertEqual(self.a.store.todos(), [])
        dialog.todo_description.delete('1.0', 'end')
        dialog.todo_description.insert('1.0', '合法內容')
        dialog.todo_save_action()
        self.assertEqual(self.a.store.todos()[0]['due_date'], '2026-09-30')

    def test_cards_transition_and_edit_preserve_source(self):
        a = self.a
        item = self.create(source_conversation_id=a.conversation)
        a.todo_cards[item['id']].todo_action.invoke()
        self.assertEqual(a.store.todo(item['id'])['state'], 'ongoing')
        a.todo_cards[item['id']].todo_action.invoke()
        self.assertEqual(a.store.todo(item['id'])['state'], 'done')
        a.todo_cards[item['id']].todo_action.invoke()
        self.assertEqual(a.store.todo(item['id'])['state'], 'todo')
        editor = a.open_todo(item['id'])
        self.assertIs(a.open_todo(item['id']), editor)
        editor.todo_title.set('改後標題')
        editor.todo_state.set('進行中')
        editor.todo_save_action()
        changed = a.store.todo(item['id'])
        self.assertEqual(changed['title'], '改後標題')
        self.assertEqual(changed['state'], 'ongoing')
        self.assertEqual(changed['source_conversation_id'], a.conversation)
        self.assertEqual(a.errors, [])

    def test_search_show_done_preference_and_write_failure_keep_current_view(self):
        a = self.a
        item = self.create('Alpha 合成項目')
        done = self.create('Beta 已完成')
        a.store.set_todo_state(done['id'], 'done')
        a.todo_search.set('Alpha')
        self.assertEqual(set(a.todo_cards), {item['id']})
        a.todo_search.set('')
        a.todo_show_done.set(False)
        a._todo_done_changed()
        self.assertFalse(load_preferences(a.preferences_path)['todo_show_done'])
        self.assertFalse(a.todo_columns['done']['frame'].winfo_manager())
        with patch('desktop_app.todo_views.update_preferences', side_effect=OSError('synthetic')):
            a.todo_show_done.set(True)
            a._todo_done_changed()
        self.assertTrue(a.todo_show_done.get())
        self.assertIn('無法保存偏好', a.status.get())

    def test_refresh_and_responsive_layout_reuse_cards_and_keep_selection(self):
        a = self.a
        item = self.create('保留選取')
        a.todo_selected_id = item['id']
        a.book.select(a.tabs['todo'])
        self.root.geometry('1100x740')
        self.root.update()
        card = a.todo_cards[item['id']]
        self.assertTrue(a._todo_wide)
        for _ in range(3):
            a.refresh_todos()
        self.assertIs(a.todo_cards[item['id']], card)
        a._todo_select_state('ongoing')
        self.root.geometry('760x620')
        self.root.update()
        self.assertFalse(a._todo_wide)
        self.assertEqual(a.todo_active_state, 'ongoing')
        self.assertIs(a.todo_cards[item['id']], card)
        self.assertEqual(a.todo_selected_id, item['id'])
        a.appearance.configure('light')
        self.assertIs(a.todo_cards[item['id']], card)
        self.assertEqual(a.todo_active_state, 'ongoing')

    def test_deleted_source_is_marked_but_independent_todo_survives(self):
        a = self.a
        item = self.create(description='保留的文字副本', source_conversation_id=a.conversation)
        editor = a.open_todo(item['id'])
        with patch.object(a, 'open_todo_source') as navigate:
            editor.todo_source_button.invoke()
            navigate.assert_called_once_with(a.conversation)
        with a.store.connection() as db:
            db.execute('DELETE FROM conversations WHERE id=?', (a.conversation,))
        a.refresh_todos()
        self.assertEqual(a.store.todo(item['id'])['description'], '保留的文字副本')
        self.assertIn('已刪除', a.todo_cards[item['id']].todo_source.cget('text'))
        self.assertTrue(editor.winfo_exists())
        self.assertIn('已刪除', editor.todo_source.cget('text'))
        self.assertEqual(str(editor.todo_source_button.cget('state')), 'disabled')

    def test_delete_cancel_defaults_and_confirmation_preserve_source_and_others(self):
        a = self.a
        item = self.create(source_conversation_id=a.conversation)
        other = self.create('另一筆')
        editor = a.open_todo(item['id'])
        dialog = a.confirm_todo_deletion(item['id'])
        self.root.update()
        self.assertEqual(dialog.focus_lastfor(), dialog.todo_delete_cancel)
        dialog.todo_delete_cancel.invoke()
        self.assertEqual(a.store.todo(item['id'])['id'], item['id'])
        dialog = a.confirm_todo_deletion(item['id'])
        dialog.todo_delete_confirm.invoke()
        self.assertFalse(editor.winfo_exists())
        with self.assertRaises(ValueError):
            a.store.todo(item['id'])
        self.assertEqual(a.store.todo(other['id'])['id'], other['id'])
        self.assertEqual(a.store.conversation(a.conversation)['title'], '合成來源對話')
        self.assertEqual(a.errors, [])

    def test_show_link_is_explicit_navigation_and_filters_do_not_hide_target(self):
        a = self.a
        item = self.create('查看合成工作')
        a.store.set_todo_state(item['id'], 'done')
        a.todo_search.set('找不到')
        a.todo_show_done.set(False)
        a.show_todo(item['id'])
        self.assertEqual(a.book.select(), str(a.tabs['todo']))
        self.assertEqual(a.todo_search.get(), '')
        self.assertTrue(a.todo_show_done.get())
        self.assertEqual(a.todo_active_state, 'done')
        self.assertEqual(a.todo_selected_id, item['id'])

    def test_title_opens_editor_and_completed_action_uses_clear_label(self):
        a = self.a
        item = self.create('點標題查看')
        a.book.select(a.tabs['todo'])
        self.root.update()
        a.todo_cards[item['id']].todo_title.event_generate('<Button-1>')
        self.root.update()
        self.assertTrue(a.todo_windows[item['id']].winfo_exists())
        self.assertEqual(a.todo_windows[item['id']].todo_state.get(), '待處理')
        a.store.set_todo_state(item['id'], 'done')
        a.refresh_todos()
        self.assertEqual(a.todo_cards[item['id']].todo_action.cget('text'), '重新開啟')

    def test_taipei_clock_controls_overdue_and_date_shortcuts(self):
        a = self.a
        with patch.object(a, 'todo_today', return_value=date(2026, 9, 28)):
            past = self.create('已到期', due_date='2026-09-27')
            today = self.create('今天到期', due_date='2026-09-28')
            self.assertIn('已逾期', a.todo_cards[past['id']].todo_due.cget('text'))
            self.assertNotIn('已逾期', a.todo_cards[today['id']].todo_due.cget('text'))
            editor = a.open_todo()
            editor.todo_today_button.invoke()
            self.assertEqual(editor.todo_due.get(), '2026-09-28')
            editor.todo_tomorrow_button.invoke()
            self.assertEqual(editor.todo_due.get(), '2026-09-29')

    def test_each_column_uses_its_own_stable_order(self):
        a = self.a
        def row(name, state='todo', due=None, created='2026-09-01T01:00:00+00:00', updated=None, completed=None):
            return {'id': name, 'title': name, 'description': '', 'due_date': due, 'state': state,
                    'created_at': created, 'updated_at': updated or created, 'completed_at': completed,
                    'source_conversation_id': None}
        rows = [row('no-date'), row('later-created', due='2026-09-10', created='2026-09-02T01:00:00+00:00'),
                row('later-date', due='2026-09-11'), row('first', due='2026-09-10'),
                row('older-update', state='ongoing'),
                row('newer-update', state='ongoing', updated='2026-09-03T01:00:00+00:00'),
                row('older-complete', state='done', completed='2026-09-01T01:00:00+00:00'),
                row('newer-complete', state='done', completed='2026-09-04T01:00:00+00:00')]
        with patch.object(a.store, 'todos', return_value=rows):
            a.refresh_todos()
        def titles(state):
            return [card.todo_title.cget('text') for card in a.todo_columns[state]['body'].winfo_children()]
        self.assertEqual(titles('todo'), ['first', 'later-created', 'later-date', 'no-date'])
        self.assertEqual(titles('ongoing'), ['newer-update', 'older-update'])
        self.assertEqual(titles('done'), ['newer-complete', 'older-complete'])


class TaipeiDateTests(unittest.TestCase):
    def test_utc_midnight_boundary_uses_fixed_taipei_offset(self):
        self.assertEqual(taipei_today(datetime(2026, 9, 27, 15, 59, tzinfo=timezone.utc)), date(2026, 9, 27))
        self.assertEqual(taipei_today(datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc)), date(2026, 9, 28))
        with self.assertRaises(ValueError):
            taipei_today(datetime(2026, 9, 27))


if __name__ == '__main__':
    unittest.main()
