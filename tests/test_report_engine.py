import copy
import json
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from desktop_app.core import Store, stamp
from desktop_app.gateways import DemoQueries, GatewayError
from desktop_app.report_engine import REPORT_BINDING, ReportEngine, report_input


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'test.db')
        self.query = DemoQueries()
        self.query_calls, self.ai_calls = [], []
        self.query_gate, self.ai_gate = threading.Event(), threading.Event()
        self.query_gate.set()
        self.ai_gate.set()
        self.query_error = self.ai_error = None
        self.result_override = None
        self.valid = True
        self.engine = self.make_engine()

    def make_engine(self):
        return ReportEngine(self.store, self.run_query, None, query_validator=self.query.validate,
                            query_catalog=self.query.catalog, assistant_router=self.respond,
                            binding_validator=self.validate_binding)

    def validate_binding(self, binding):
        if not self.valid or binding != REPORT_BINDING:
            raise ValueError('invalid binding')

    def run_query(self, query_id, parameters):
        self.query_calls.append((query_id, copy.deepcopy(parameters)))
        self.query_gate.wait(5)
        if self.query_error:
            raise self.query_error
        return copy.deepcopy(self.result_override) if self.result_override is not None else self.query.run(query_id, parameters)

    def respond(self, messages, purpose, binding):
        self.ai_calls.append((copy.deepcopy(messages), purpose, copy.deepcopy(binding)))
        self.ai_gate.wait(5)
        if self.ai_error:
            raise self.ai_error
        return '合成日報：請核對表格。'

    def tearDown(self):
        self.query_gate.set()
        self.ai_gate.set()
        self.engine.close(wait=True)
        self.temp.cleanup()

    def preview(self, **kwargs):
        spec = dict(query_id='DEMO01', parameters={'category': 'all'}, time_hhmm='08:00', name='合成日報')
        spec.update(kwargs)
        return self.engine.preview_report(spec, copy.deepcopy(REPORT_BINDING))

    def schedule(self, **kwargs):
        return self.engine.confirm_report(self.preview(**kwargs)['token'])

    def wait_task(self, task_id):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            task = self.store.task(task_id)
            if task['state'] in {'succeeded', 'failed', 'cancelled'} and not self.engine.has_inflight():
                return task
            time.sleep(.01)
        self.fail('Worker did not finish')

    def wait_call(self, target):
        deadline = time.monotonic() + 3
        while not target and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(target)

    def test_preview_immutable_and_double_confirmation_no_dispatch(self):
        preview = self.preview()
        token = preview['token']
        preview['parameters']['category'] = 'B'
        preview['binding']['revision'] = 9
        sid = self.engine.confirm_report(token)
        self.assertEqual(sid, self.engine.confirm_report(token))
        self.assertEqual(len(self.store.schedules()), 1)
        self.assertEqual(self.store.schedule(sid)['parameters']['category'], 'all')
        self.assertTrue(self.store.schedule(sid)['enabled'])
        self.assertEqual(self.query_calls, [])
        self.assertEqual(self.ai_calls, [])
        self.assertEqual(self.store.tasks(), [])

    def test_expiration_cancel_binding_and_invalid_input(self):
        with patch('desktop_app.report_engine.time.monotonic', return_value=100):
            token = self.preview()['token']
        with patch('desktop_app.report_engine.time.monotonic', return_value=701), self.assertRaises(ValueError):
            self.engine.confirm_report(token)
        token = self.preview()['token']
        self.engine.cancel_report(token)
        with self.assertRaises(ValueError):
            self.engine.confirm_report(token)
        for changes in ({'query_id': 'ORACLE'}, {'time_hhmm': '25:00'}, {'name': ''},
                        {'parameters': {'category': 'all', '_report': {}}}, {'parameters': {'category': 'C'}},
                        {'parameters': {'category': 'all', 'secret': 'x'}}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, GatewayError)):
                self.preview(**changes)
        for binding in (None, {'profile_id': 'demo', 'revision': 1}, {'profile_id': 'groq-trial', 'revision': True}):
            with self.assertRaises(ValueError):
                self.engine.preview_report({}, binding)
        token = self.preview()['token']
        self.valid = False
        with self.assertRaises(ValueError):
            self.engine.confirm_report(token)
        self.assertFalse(self.store.schedules())

    def test_success_aggregate_only_and_repeat_notification(self):
        sid = self.schedule()
        one = self.engine.run_schedule_now(sid, 'one')
        task = self.wait_task(one)
        self.assertEqual(task['state'], 'succeeded')
        self.assertEqual(task['result']['summary_status'], 'succeeded')
        self.assertEqual(task['result']['row_count'], 150)
        text = self.ai_calls[0][0][0]['content']
        self.assertLessEqual(len(text), 6000)
        self.assertNotIn('000001', text)
        data = json.loads(text.split('\n', 1)[1])
        self.assertEqual(data['row_count'], 150)
        self.assertEqual(data['numeric_totals']['quantity'], str(sum(row[-1] for row in task['result']['rows'])))
        self.assertNotIn('_report', self.query_calls[0][1])
        self.assertEqual(self.ai_calls[0][2], REPORT_BINDING)
        self.assertIsNone(self.engine.run_schedule_now(sid, 'one'))
        self.wait_task(self.engine.run_schedule_now(sid, 'two'))
        self.assertEqual(len(self.store.notifications()), 2)
        self.assertEqual(len(self.query_calls), 2)

    def test_ai_failure_preserves_result_and_hides_secret(self):
        self.ai_error = GatewayError('SECRET_KEY http://private/ response-body')
        task = self.wait_task(self.engine.run_schedule_now(self.schedule()))
        self.assertEqual(task['state'], 'failed')
        self.assertEqual(task['result']['summary_status'], 'failed')
        self.assertEqual(task['result']['row_count'], 150)
        self.assertNotIn('SECRET_KEY', json.dumps(task))
        self.assertIn('未完成', self.store.notifications()[0]['text'])
        self.assertEqual(len(self.query_calls), 1)

    def test_query_failure_no_retry_or_ai(self):
        self.query_error = TimeoutError('SECRET_KEY')
        task = self.wait_task(self.engine.run_schedule_now(self.schedule()))
        self.assertEqual(task['state'], 'failed')
        self.assertNotIn('SECRET_KEY', task['error'])
        self.assertEqual(len(self.query_calls), 1)
        self.assertFalse(self.ai_calls)

    def test_empty_and_truncated_skip_ai(self):
        self.result_override = self.query.run('DEMO03', {'category': 'all', 'from_date': '2026-09-26', 'to_date': '2026-09-27'})
        self.result_override.update(rows=[], row_count=0)
        sid = self.schedule()
        task = self.wait_task(self.engine.run_schedule_now(sid))
        self.assertEqual(task['result']['summary_status'], 'succeeded')
        self.assertIn('0 筆', task['result']['summary'])
        self.result_override.update(truncated=True)
        task = self.wait_task(self.engine.run_schedule_now(sid))
        self.assertEqual(task['state'], 'failed')
        self.assertEqual(task['result']['summary_status'], 'failed')
        self.assertIn('截斷', task['result']['summary_error'])
        self.assertFalse(self.ai_calls)

    def test_cancel_query_and_real_future_blocks_overlap(self):
        self.query_gate.clear()
        sid = self.schedule()
        tid = self.engine.run_schedule_now(sid, 'first')
        self.wait_call(self.query_calls)
        self.engine.cancel_task(tid)
        self.assertIsNone(self.engine.run_schedule_now(sid, 'second'))
        self.query_gate.set()
        task = self.wait_task(tid)
        self.assertEqual(task['state'], 'cancelled')
        self.assertIsNone(task['result'])
        self.assertFalse(self.ai_calls)
        self.assertEqual(len(self.store.notifications()), 1)
        self.assertIn('skipped_overlap', [run['state'] for run in self.store.schedule_runs(sid)])

    def test_cancel_ai_retains_pending_snapshot_but_no_late_report(self):
        self.ai_gate.clear()
        sid = self.schedule()
        tid = self.engine.run_schedule_now(sid, 'first')
        self.wait_call(self.ai_calls)
        self.engine.cancel_task(tid)
        self.assertIsNone(self.engine.run_schedule_now(sid, 'second'))
        self.ai_gate.set()
        task = self.wait_task(tid)
        self.assertEqual(task['state'], 'cancelled')
        self.assertEqual(task['result']['row_count'], 150)
        self.assertNotIn('summary', task['result'])
        self.assertEqual(len(self.store.notifications()), 1)

    def test_clock_restart_previous_day_dedup_disable_and_missed(self):
        now = datetime(2026, 9, 27, 0, 0, tzinfo=timezone.utc)
        with patch('desktop_app.report_engine.utcnow', return_value=now - timedelta(minutes=1)):
            sid = self.schedule()
        preview = self.engine.schedule_preview(sid, now=now - timedelta(minutes=1))
        self.assertEqual(preview[0]['parameters']['from_date'], '2026-09-26')
        self.assertEqual(preview[0]['parameters']['to_date'], '2026-09-27')
        self.engine.tick(now)
        self.wait_task(self.store.schedule_runs(sid)[0]['task_id'])
        self.engine.close(wait=True)
        self.engine = self.make_engine()
        self.engine.tick(now)
        self.assertEqual(len(self.query_calls), 1)
        self.engine.tick(now + timedelta(days=4))
        run = next(run for run in self.store.schedule_runs(sid) if run['task_id'] and run['scheduled_at'] == stamp(now + timedelta(days=4)))
        self.wait_task(run['task_id'])
        self.assertEqual(len(self.query_calls), 2)
        self.assertIn('missed', [run['state'] for run in self.store.schedule_runs(sid)])
        self.engine.set_schedule_enabled(sid, False)
        self.engine.set_schedule_date_mode(sid, 'previous_day')
        self.engine.tick(now + timedelta(days=5))
        self.assertEqual(len(self.query_calls), 2)
        with self.assertRaises(ValueError):
            self.engine.set_schedule_date_mode(sid, 'literal')

    def test_normal_query_schedule_does_not_summarize(self):
        tid = self.engine.run_query('DEMO03', {'category': 'all', 'from_date': '2026-09-26', 'to_date': '2026-09-27'})
        self.wait_task(tid)
        sid = self.engine.create_schedule(tid, '普通查詢', 'daily', '08:00')
        result = self.wait_task(self.engine.run_schedule_now(sid))
        self.assertNotIn('summary_status', result['result'])
        self.assertFalse(self.ai_calls)

    def test_exact_totals_malformed_and_oversized_metadata(self):
        result = {'columns': [{'name': 'amount', 'type': 'decimal'}, {'name': 'secret', 'type': 'text'}],
                  'rows': [['9999999999999999999999999999.99', 'private'], ['0.01', 'private']],
                  'parameters': {'category': 'all'}, 'truncated': False}
        data = json.loads(report_input(result).split('\n', 1)[1])
        self.assertEqual(data['numeric_totals']['amount'], '10000000000000000000000000000.00')
        self.assertNotIn('private', report_input(result))
        for rows in ([[1]], [['NaN', 'x']], [[1.5, 'x']]):
            with self.assertRaises(ValueError):
                report_input(dict(result, rows=rows))
        with self.assertRaises(ValueError):
            report_input(dict(result, source_label='x' * 6001))

    def test_confirm_transaction_rollback_and_concurrent_clicks(self):
        import sqlite3
        token = self.preview()['token']
        with self.store.connection() as db:
            db.execute("CREATE TRIGGER reject_report BEFORE INSERT ON schedules BEGIN SELECT RAISE(ABORT, 'test rollback'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.engine.confirm_report(token)
        self.assertEqual(self.store.schedules(), [])
        with self.store.connection() as db:
            db.execute('DROP TRIGGER reject_report')
        ids = []
        threads = [threading.Thread(target=lambda: ids.append(self.engine.confirm_report(token))) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(ids), 5)
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual(len(self.store.schedules()), 1)
        self.assertFalse(self.ai_calls)

    def test_expired_binding_at_run_blocks_query_and_notifies(self):
        sid = self.schedule()
        self.valid = False
        self.assertIsNone(self.engine.run_schedule_now(sid, 'invalid'))
        self.assertEqual(self.store.schedule_runs(sid)[0]['state'], 'failed')
        self.assertEqual(len(self.store.notifications()), 1)
        self.assertFalse(self.query_calls)
        self.assertFalse(self.ai_calls)

    def test_recovery_failure_is_not_retried_and_notification_deduplicates(self):
        sid = self.schedule()
        schedule = self.store.schedule(sid)
        parameters = self.engine._schedule_parameters(schedule, datetime(2026, 9, 27, tzinfo=timezone.utc))
        self.engine.close(wait=True)
        # Persist the exact pre-dispatch state left by a terminated process.
        with self.store.connection() as db:
            task, _ = self.engine._new_task(db, 'query', {'query_id': 'DEMO01', 'parameters': parameters}, schedule_id=sid)
            db.execute("INSERT INTO occurrences VALUES('crash',?,'crash','queued',?)", (sid, task))
        self.engine = self.make_engine()
        self.assertEqual(self.store.task(task)['state'], 'failed')
        self.assertEqual(self.store.schedule_runs(sid)[0]['state'], 'failed')
        self.assertFalse(self.query_calls)
        self.assertFalse(self.ai_calls)
        self.assertEqual(len(self.store.notifications()), 1)
        self.engine.close(wait=True)
        self.engine = self.make_engine()
        self.assertEqual(len(self.store.notifications()), 1)

    def test_close_fences_late_report_and_notifies_once(self):
        self.ai_gate.clear()
        tid = self.engine.run_schedule_now(self.schedule())
        self.wait_call(self.ai_calls)
        self.engine.close(wait=False)
        self.ai_gate.set()
        self.assertTrue(self.engine.wait_closed(3))
        task = self.store.task(tid)
        self.assertEqual(task['state'], 'cancelled')
        self.assertNotIn('summary', task['result'])
        self.engine.close(wait=True)
        self.assertEqual(len(self.store.notifications()), 1)


if __name__ == '__main__':
    unittest.main()
