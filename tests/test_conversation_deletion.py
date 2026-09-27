import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_app.core import Engine, Store, stamp, uid
from tests.test_core import sample_result


class ConversationDeletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'state.db')
        self.release = threading.Event()
        self.release.set()
        self.entered = threading.Event()

        def assistant(messages, purpose):
            self.entered.set()
            self.release.wait(5)
            return '合成結果'

        self.engine = Engine(self.store, lambda *_: sample_result(), assistant)

    def tearDown(self):
        self.release.set()
        self.engine.close(wait=True)
        self.temp.cleanup()

    def wait_idle(self):
        deadline = time.monotonic() + 5
        while self.engine.has_inflight() and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertFalse(self.engine.has_inflight())

    def conversation(self, title='可刪除對話'):
        cid = self.store.create_conversation(title)
        task = self.engine.run_chat(cid, '原始內容')
        self.wait_idle()
        return cid, task

    def preview(self, *ids):
        return self.engine.preview_conversation_deletion(list(ids))

    def test_bulk_counts_and_dependent_records_deleted_persistently(self):
        first, task = self.conversation('第一筆')
        second, other_task = self.conversation('第二筆')
        plan = self.engine.create_plan('chat', {'text': '尚未批准', 'conversation_id': first})
        with self.store.connection() as db:
            db.execute('INSERT INTO notifications VALUES(?,?,?,?,0,?)',
                       (uid(), 'test-key', task, '通知', stamp()))
        preview = self.preview(first, second, first)
        self.assertEqual(preview['counts'], dict(conversations=2, messages=4, plans=1, tasks=2, notifications=1))
        self.assertEqual(set(preview['task_ids']), {task, other_task})
        self.assertEqual(preview['plan_ids'], [plan])
        self.assertEqual(len(self.store.messages(first)), 2)  # Preview is read-only.
        result = self.engine.delete_conversations(preview['token'])
        self.assertEqual(set(result['deleted_ids']), {first, second})
        reopened = Store(self.store.path)
        for read in (reopened.conversations, reopened.tasks, reopened.plans, reopened.notifications):
            self.assertEqual(read(), [])
        self.assertEqual(reopened.messages(first), [])
        with self.assertRaises(ValueError):
            self.engine.delete_conversations(preview['token'])
        with self.assertRaises(ValueError):
            self.engine.run_chat(first, '舊畫面重送')
        with self.assertRaises(ValueError):
            self.engine.create_plan('chat', {'text': '舊畫面', 'conversation_id': first})
        with self.assertRaises(ValueError):
            self.engine.confirm_plan(plan, 1, 'old-approval')

    def test_independent_query_schedule_issue_and_transferred_copy_survive(self):
        source, _ = self.conversation()
        copy_id = self.store.create_conversation('轉交副本', source={'conversation_id': source})
        self.store.add_message(copy_id, 'user', '獨立複製內容')
        query = self.engine.run_query('demo', {})
        self.wait_idle()
        schedule = self.engine.create_schedule(query, '保留排程', 'daily', '09:00')
        scheduled_task = self.engine.run_schedule_now(schedule)
        self.wait_idle()
        issue = self.store.save_issue('app', '保留回報', '內容', '預期')
        self.engine.delete_conversations(self.preview(source)['token'])
        self.assertEqual(self.store.conversation(copy_id)['source'], {'conversation_id': source})
        self.assertEqual(self.store.messages(copy_id)[0]['text'], '獨立複製內容')
        self.assertEqual(self.store.task(query)['state'], 'succeeded')
        self.assertEqual(self.store.task(scheduled_task)['state'], 'succeeded')
        self.assertEqual(len(self.store.schedule_runs(schedule)), 1)
        self.assertEqual(self.store.issue(issue)['title'], '保留回報')
        self.assertEqual(len(self.store.notifications()), 1)

    def test_database_failure_rolls_back_entire_batch(self):
        first, task = self.conversation()
        second, _ = self.conversation()
        plan = self.engine.create_plan('chat', {'text': '待批准', 'conversation_id': first})
        with self.store.connection() as db:
            db.execute('INSERT INTO notifications VALUES(?,?,?,?,0,?)',
                       (uid(), 'rollback-key', task, '保留通知', stamp()))
            db.execute("CREATE TRIGGER fail_deletion BEFORE DELETE ON conversations BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        preview = self.preview(first, second)
        with self.assertRaises(sqlite3.IntegrityError):
            self.engine.delete_conversations(preview['token'])
        self.assertEqual(len(self.store.conversations()), 2)
        self.assertEqual(len(self.store.messages(first)), 2)
        self.assertEqual(self.store.plan(plan)['state'], 'ready')
        self.assertEqual(len(self.store.tasks()), 2)
        self.assertEqual(len(self.store.notifications()), 1)
        with self.store.connection() as db:
            db.execute('DROP TRIGGER fail_deletion')
        self.engine.delete_conversations(preview['token'])
        self.assertEqual(self.store.conversations(), [])

    def test_content_and_title_changes_invalidate_confirmation(self):
        for mutation in ('message', 'title', 'result', 'plan'):
            with self.subTest(mutation=mutation):
                cid, task = self.conversation()
                plan = self.engine.create_plan('chat', {'text': '待批准', 'conversation_id': cid})
                preview = self.preview(cid)
                if mutation == 'message':
                    self.store.add_message(cid, 'user', '新文字')
                else:
                    with self.store.connection() as db:
                        if mutation == 'title':
                            db.execute('UPDATE conversations SET title=? WHERE id=?', ('新名稱', cid))
                        elif mutation == 'result':
                            db.execute("UPDATE tasks SET result='{}' WHERE id=?", (task,))
                        else:
                            db.execute('UPDATE plans SET revision=revision+1 WHERE id=?', (plan,))
                with self.assertRaisesRegex(ValueError, '變更'):
                    self.engine.delete_conversations(preview['token'])
                self.assertEqual(self.store.conversation(cid)['id'], cid)

    def test_notification_change_invalidates_preview(self):
        cid, task = self.conversation()
        with self.store.connection() as db:
            notification = uid()
            db.execute('INSERT INTO notifications VALUES(?,?,?,?,0,?)',
                       (notification, 'read-test', task, '通知', stamp()))
        preview = self.preview(cid)
        self.store.mark_read(notification)
        with self.assertRaisesRegex(ValueError, '變更'):
            self.engine.delete_conversations(preview['token'])

    def test_invalid_expired_and_caller_tampered_tokens(self):
        cid, _ = self.conversation()
        with patch('desktop_app.core.time.monotonic', return_value=1000):
            preview = self.preview(cid)
        preview['conversations'].clear()
        preview['counts']['messages'] = 0
        with patch('desktop_app.core.time.monotonic', return_value=1600):
            with self.assertRaises(ValueError):
                self.engine.delete_conversations(preview['token'])
        for invalid in (None, {}, 'forged'):
            with self.assertRaises(ValueError):
                self.engine.delete_conversations(invalid)
        preview = self.preview(cid)
        preview['counts'].clear()
        self.assertEqual(self.engine.delete_conversations(preview['token'])['counts']['messages'], 2)

    def test_selection_validation_and_missing_conversation_are_atomic(self):
        cid, _ = self.conversation()
        for invalid in ([], cid, [None], [cid, 'missing']):
            with self.assertRaises(ValueError):
                self.engine.preview_conversation_deletion(invalid)
        self.assertEqual(len(self.store.conversations()), 1)

    def test_active_and_cancelled_remote_request_block_entire_batch(self):
        idle, _ = self.conversation()
        running = self.store.create_conversation('執行中')
        self.entered.clear()
        self.release.clear()
        task = self.engine.run_chat(running, '等待远端')
        self.assertTrue(self.entered.wait(2))
        with self.assertRaisesRegex(ValueError, '進行中'):
            self.preview(idle, running)
        self.engine.cancel_task(task)
        self.assertEqual(self.store.task(task)['state'], 'cancelled')
        with self.assertRaisesRegex(ValueError, '尚未結束'):
            self.preview(idle, running)
        self.assertEqual(len(self.store.conversations()), 2)
        self.release.set()
        self.wait_idle()
        self.assertEqual(len(self.store.messages(running)), 1)  # Late answer is fenced.
        self.engine.delete_conversations(self.preview(idle, running)['token'])
        self.assertEqual(self.store.conversations(), [])

    def test_unrelated_remote_request_does_not_block_deletion(self):
        idle, _ = self.conversation()
        running = self.store.create_conversation('其他對話')
        self.entered.clear()
        self.release.clear()
        task = self.engine.run_chat(running, '繼續執行')
        self.assertTrue(self.entered.wait(2))
        self.engine.delete_conversations(self.preview(idle)['token'])
        self.assertEqual(self.store.task(task)['state'], 'running')
        self.release.set()
        self.wait_idle()
        self.assertEqual(self.store.task(task)['state'], 'succeeded')

    def test_dispatch_after_preview_requires_new_confirmation(self):
        cid, _ = self.conversation()
        preview = self.preview(cid)
        self.entered.clear()
        self.release.clear()
        task = self.engine.run_chat(cid, '新工作')
        self.assertTrue(self.entered.wait(2))
        with self.assertRaises(ValueError):
            self.engine.delete_conversations(preview['token'])
        self.release.set()
        self.wait_idle()
        with self.assertRaisesRegex(ValueError, '變更'):
            self.engine.delete_conversations(preview['token'])
        self.assertEqual(self.store.task(task)['state'], 'succeeded')

    def test_schedule_occurrence_or_cross_plan_dependency_refuses_deletion(self):
        cid, task = self.conversation()
        query = self.engine.run_query('demo', {})
        self.wait_idle()
        schedule = self.engine.create_schedule(query, '獨立排程', 'daily', '10:00')
        with self.store.connection() as db:
            db.execute('UPDATE tasks SET schedule_id=? WHERE id=?', (schedule, task))
        with self.assertRaises(ValueError):
            self.preview(cid)
        with self.store.connection() as db:
            db.execute('UPDATE tasks SET schedule_id=NULL WHERE id=?', (task,))
            occurrence = uid()
            db.execute("INSERT INTO occurrences VALUES(?,?,?,'succeeded',?)", (occurrence, schedule, stamp(), task))
        with self.assertRaises(ValueError):
            self.preview(cid)
        with self.store.connection() as db:
            db.execute('DELETE FROM occurrences WHERE id=?', (occurrence,))
        plan = self.engine.create_plan('query', {'query_id': 'demo', 'parameters': {}})
        with self.store.connection() as db:
            db.execute('UPDATE plans SET task_id=? WHERE id=?', (task, plan))
        with self.assertRaises(ValueError):
            self.preview(cid)
        self.assertEqual(self.store.schedule(schedule)['id'], schedule)
        self.assertEqual(self.store.conversation(cid)['id'], cid)

    def test_approved_plan_and_task_deleted_together(self):
        cid = self.store.create_conversation('批准過的對話')
        plan = self.engine.create_plan('rewrite', {'text': '原文', 'conversation_id': cid})
        task = self.engine.confirm_plan(plan, 1, 'approved')
        self.wait_idle()
        preview = self.preview(cid)
        self.assertEqual(preview['counts'], dict(conversations=1, messages=2, tasks=1, plans=1, notifications=0))
        self.engine.delete_conversations(preview['token'])
        with self.assertRaises(ValueError):
            self.store.task(task)
        with self.assertRaises(ValueError):
            self.store.plan(plan)

    def test_pending_states_and_concurrent_confirmation_are_service_guarded(self):
        cid, task = self.conversation()
        plan = self.engine.create_plan('chat', {'text': '待批准', 'conversation_id': cid})
        with self.store.connection() as db:
            db.execute("UPDATE tasks SET state='queued' WHERE id=?", (task,))
        with self.assertRaises(ValueError):
            self.preview(cid)
        with self.store.connection() as db:
            db.execute("UPDATE tasks SET state='succeeded' WHERE id=?", (task,))
            db.execute("UPDATE plans SET state='executing' WHERE id=?", (plan,))
        with self.assertRaises(ValueError):
            self.preview(cid)
        with self.store.connection() as db:
            db.execute("UPDATE plans SET state='ready' WHERE id=?", (plan,))
        token = self.preview(cid)['token']
        outcomes = []

        def confirm():
            try:
                self.engine.delete_conversations(token)
                outcomes.append('deleted')
            except ValueError:
                outcomes.append('rejected')

        threads = [threading.Thread(target=confirm) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(3)
            self.assertFalse(thread.is_alive())
        self.assertCountEqual(outcomes, ['deleted', 'rejected'])
        self.assertEqual(self.store.conversations(), [])

    def test_deleted_conversation_cannot_receive_reassigned_plan(self):
        cid, _ = self.conversation()
        self.engine.delete_conversations(self.preview(cid)['token'])
        other = self.store.create_conversation('保留')
        plan = self.engine.create_plan('chat', {'text': '待批准', 'conversation_id': other})
        with self.assertRaises(ValueError):
            self.engine.edit_plan(plan, 1, 'chat', {'text': '誤送', 'conversation_id': cid})
        self.assertEqual(self.store.plan(plan)['conversation_id'], other)


if __name__ == '__main__':
    unittest.main()
