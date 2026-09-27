import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from desktop_app.core import Engine, Store, stamp
from desktop_app.gateways import GatewayError


def sample_result(value="7", fetched="2026-09-01T00:00:00Z"):
    return {"columns": [{"name": "value", "label": "筆數", "type": "number", "copy_as_text": False}],
            "rows": [{"value": value}], "row_count": 1, "truncated": False,
            "source_label": "合成測試資料", "fetched_at_utc": fetched,
            "query_ref": {"id": "demo", "version": 1}, "parameters": {}}


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "state.db")
        self.calls = []
        self.release = threading.Event()
        self.release.set()

        def query(query_id, parameters):
            self.calls.append((query_id, parameters))
            self.release.wait(3)
            return sample_result()

        self.engine = Engine(self.store, query, lambda messages, purpose: "結果：" + messages[-1]["content"])

    def tearDown(self):
        self.release.set()
        self.engine.close(wait=True)
        self.temp.cleanup()

    def wait_task(self, task_id):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            task = self.store.task(task_id)
            if task["state"] in {"succeeded", "failed", "cancelled"}:
                return task
            time.sleep(0.01)
        self.fail("工作未在期限內完成")

    def success(self):
        task_id = self.engine.run_query("demo", {"from_date": "2026-09-25", "to_date": "2026-09-26", "category": "all"})
        self.assertEqual(self.wait_task(task_id)["state"], "succeeded")
        return task_id

    def make_schedule(self, **kwargs):
        return self.engine.create_schedule(self.success(), "每日測試", "daily", "09:00", **kwargs)

    def test_history_and_issue_survive_reopen(self):
        conversation = self.store.create_conversation("測試")
        task = self.engine.run_chat(conversation, "原文", purpose="rewrite")
        self.assertEqual(self.wait_task(task)["result"]["original"], "原文")
        issue = self.store.save_issue("app", "標題", "描述", "預期")
        self.store.submit_issue(issue)
        second = Store(self.store.path)
        self.assertEqual([m["role"] for m in second.messages(conversation)], ["user", "assistant"])
        self.assertEqual(second.issue(issue)["status"], "local_saved")
        self.assertNotIn("conversation_id", second.issue(issue))
        with self.assertRaises(ValueError):
            self.store.save_issue("app", "標題", "描述", "預期", status="submitted")

    def test_plan_gate_revision_duplicate_confirmation(self):
        plan = self.engine.create_plan("query", {"query_id": "demo", "parameters": {}})
        self.assertFalse(self.calls)
        self.assertEqual(self.store.tasks(), [])
        revised = self.engine.edit_plan(plan, 1, "query", {"query_id": "demo", "parameters": {"category": "all"}})
        self.assertEqual(revised["revision"], 2)
        with self.assertRaises(ValueError):
            self.engine.confirm_plan(plan, 1, "old")
        task = self.engine.confirm_plan(plan, 2, "approved")
        self.assertEqual(task, self.engine.confirm_plan(plan, 2, "second-click"))
        self.assertEqual(self.wait_task(task)["state"], "succeeded")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.store.plan(plan)["state"], "succeeded")

    def test_plan_concurrent_confirmations_one_task(self):
        plan = self.engine.create_plan("query", {"query_id": "demo", "parameters": {}})
        ids = []
        threads = [threading.Thread(target=lambda: ids.append(self.engine.confirm_plan(plan, 1, "click"))) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(set(ids)), 1)
        self.wait_task(ids[0])
        self.assertEqual(len(self.calls), 1)

    def test_expired_and_cancelled_plan_never_calls_runner(self):
        p1 = self.engine.create_plan("query", {"query_id": "demo", "parameters": {}})
        self.engine.cancel_plan(p1)
        with self.assertRaises(ValueError):
            self.engine.confirm_plan(p1, 1, "cancelled")
        p2 = self.engine.create_plan("query", {"query_id": "demo", "parameters": {}})
        with self.store.connection() as db:
            db.execute("UPDATE plans SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?", (p2,))
        with self.assertRaises(ValueError):
            self.engine.confirm_plan(p2, 1, "expired")
        self.assertFalse(self.calls)

    def test_task_idempotency_compares_payload(self):
        t = self.engine.run_query("demo", {}, request_id="stable")
        self.assertEqual(t, self.engine.run_query("demo", {}, request_id="stable"))
        with self.assertRaises(ValueError):
            self.engine.run_query("demo", {"other": 1}, request_id="stable")
        self.wait_task(t)
        self.assertEqual(len(self.calls), 1)

    def test_cancel_fences_late_result(self):
        self.release.clear()
        t = self.engine.run_query("demo", {})
        deadline = time.monotonic() + 2
        while not self.calls and time.monotonic() < deadline:
            time.sleep(0.01)
        self.engine.cancel_task(t)
        self.release.set()
        self.engine.close(wait=True)
        self.assertEqual(self.store.task(t)["state"], "cancelled")
        self.assertIsNone(self.store.task(t)["result"])
        self.assertEqual(self.store.notifications(), [])

    def test_conversation_busy_and_context_isolation(self):
        first = self.store.create_conversation("一")
        second = self.store.create_conversation("二")
        contexts = []
        entered = threading.Event()
        self.release.clear()

        def assistant(messages, purpose):
            contexts.append(messages)
            entered.set()
            self.release.wait(2)
            return "好"

        self.engine.assistant_runner = assistant
        t1 = self.engine.run_chat(first, "秘密一")
        entered.wait(2)
        with self.assertRaises(ValueError):
            self.engine.run_chat(first, "另一個請求")
        t2 = self.engine.run_chat(second, "秘密二")
        self.release.set()
        self.wait_task(t1)
        self.wait_task(t2)
        self.assertEqual(sorted(c[-1]["content"] for c in contexts), ["秘密一", "秘密二"])
        self.assertTrue(all(len(c) == 1 for c in contexts))

    def test_provider_error_does_not_persist_secret(self):
        def failing(*args):
            raise RuntimeError("authorization=secret123 oracle://password")
        self.engine.query_runner = failing
        t = self.wait_task(self.engine.run_query("demo", {}))
        self.assertEqual(t["state"], "failed")
        self.assertNotIn("secret123", t["error"])
        self.assertIsNone(t["result"])

    def test_restart_marks_interrupted_and_does_not_reexecute(self):
        with self.store.connection() as db:
            t, _ = self.engine._new_task(db, "query", {"query_id": "demo", "parameters": {}}, request_id="interrupted")
        self.engine.close()
        with self.store.connection() as db:
            db.execute("UPDATE tasks SET state='running' WHERE id=?", (t,))
        self.engine = Engine(self.store, lambda *a: self.fail("不應重送"), lambda *a: "")
        self.assertEqual(self.store.task(t)["state"], "failed")
        self.assertIn("未自動重送", self.store.task(t)["error"])

    def test_schedule_is_disabled_until_confirmed_and_validated(self):
        s = self.make_schedule()
        self.assertFalse(self.store.schedule(s)["enabled"])
        previews = self.engine.schedule_preview(s, datetime(2026, 9, 26, tzinfo=timezone.utc))
        self.assertEqual(len(previews), 3)
        self.assertTrue(all(p["scheduled_at"].endswith("+00:00") for p in previews))
        with self.assertRaises(ValueError):
            self.engine.create_schedule(self.success(), "壞時間", "daily", "25:99")

    def test_daily_occurrence_once_and_previous_day_by_scheduled_time(self):
        s = self.make_schedule()
        self.engine.set_schedule_date_mode(s, "previous_day")
        start = datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)
        self.engine.set_schedule_enabled(s, True, now=start)
        fire = datetime(2026, 9, 25, 1, 0, tzinfo=timezone.utc)
        self.engine.tick(fire + timedelta(hours=6))
        self.engine.tick(fire + timedelta(hours=6))
        run = self.store.schedule_runs(s)[0]
        self.wait_task(run["task_id"])
        self.assertEqual(len(self.store.schedule_runs(s)), 1)
        params = self.store.task(run["task_id"])["payload"]["parameters"]
        self.assertEqual(params["from_date"], "2026-09-24")
        self.assertEqual(params["to_date"], "2026-09-25")
        self.assertNotIn("_date_mode", params)
        self.engine.set_schedule_enabled(s, False)
        self.engine.tick(fire + timedelta(days=3))
        self.assertEqual(len(self.store.schedule_runs(s)), 1)

    def test_offline_coalesce_latest_and_overlap_skip(self):
        s = self.make_schedule()
        self.engine.set_schedule_enabled(s, True, now=datetime(2026, 9, 20, tzinfo=timezone.utc))
        self.release.clear()
        now = datetime(2026, 9, 25, 2, tzinfo=timezone.utc)
        self.engine.tick(now)
        rows = self.store.schedule_runs(s)
        self.assertEqual(sum(r["state"] == "missed" for r in rows), 1)
        self.assertEqual(sum(r["task_id"] is not None for r in rows), 1)
        self.engine.tick(now + timedelta(days=1))
        self.assertIn("skipped_overlap", [r["state"] for r in self.store.schedule_runs(s)])
        self.release.set()

    def test_weekly_older_than_24_hours_not_replayed(self):
        task = self.success()
        s = self.engine.create_schedule(task, "每週", "weekly", "09:00", weekday=0)
        self.engine.set_schedule_enabled(s, True, now=datetime(2026, 9, 20, tzinfo=timezone.utc))
        self.engine.tick(datetime(2026, 9, 23, 12, tzinfo=timezone.utc))
        self.assertEqual([r["state"] for r in self.store.schedule_runs(s)], ["missed"])

    def test_same_result_does_not_notify_due_to_fetch_timestamp(self):
        s = self.make_schedule()
        t1 = self.engine.run_schedule_now(s)
        self.wait_task(t1)
        self.engine.query_runner = lambda *a: sample_result(fetched="2026-10-20T02:00:00Z")
        self.wait_task(self.engine.run_schedule_now(s))
        self.assertEqual(len(self.store.notifications()), 1)
        self.store.mark_read(self.store.notifications()[0]["id"])
        self.assertEqual(self.store.notifications()[0]["is_read"], 1)

    def test_threshold_only_notifies_crossing(self):
        s = self.make_schedule(notify_rule="threshold_crossing", threshold={"operator": ">", "value": "5"})
        for value in ("7", "8", "2", "6"):
            self.engine.query_runner = lambda *a, value=value: sample_result(value)
            self.wait_task(self.engine.run_schedule_now(s))
        self.assertEqual(len(self.store.notifications()), 2)

    def test_schedule_failure_one_notification(self):
        s = self.make_schedule()
        def fail(*args):
            raise ValueError("private provider failure")
        self.engine.query_runner = fail
        self.wait_task(self.engine.run_schedule_now(s, request_id="once"))
        self.engine.run_schedule_now(s, request_id="once")
        self.assertEqual(len(self.store.notifications()), 1)
        self.assertNotIn("private", self.store.notifications()[0]["text"])

    def test_newer_schema_fails_without_overwrite(self):
        with self.store.connection() as db:
            db.execute("PRAGMA user_version=99")
        with self.assertRaises(ValueError):
            Store(self.store.path)
        with self.store.connection() as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 99)

    def test_validator_rejects_before_plan_ready_and_rechecks_confirmation(self):
        allowed = [False]
        def validate(query_id, parameters):
            if not allowed[0]:
                raise GatewayError("查詢已停用。")
        self.engine.query_validator = validate
        with self.assertRaises(GatewayError):
            self.engine.create_plan("query", {"query_id": "demo", "parameters": {}})
        self.assertEqual(self.store.plans(), [])
        allowed[0] = True
        p = self.engine.create_plan("query", {"query_id": "demo", "parameters": {}})
        allowed[0] = False
        with self.assertRaises(GatewayError):
            self.engine.confirm_plan(p, 1, "blocked")
        self.assertEqual(self.store.tasks(), [])
        self.assertFalse(self.calls)

    def test_query_summary_partial_failure_preserves_table(self):
        def fail_summary(*args):
            raise GatewayError("助理連線逾時。")
        self.engine.assistant_runner = fail_summary
        p = self.engine.create_plan("query_summarize", {"query_id": "demo", "parameters": {}})
        self.assertFalse(self.calls)
        t = self.wait_task(self.engine.confirm_plan(p, 1, "approve"))
        self.assertEqual(t["state"], "succeeded")
        self.assertEqual(t["result"]["summary_status"], "failed")
        self.assertEqual(t["result"]["rows"], [{"value": "7"}])
        self.assertEqual(t["result"]["summary_error"], "助理連線逾時。")
        self.assertEqual(len(self.calls), 1)
        s = self.engine.create_schedule(t["id"], "可排程", "daily", "09:00")
        self.assertEqual(self.store.schedule(s)["query_id"], "demo")

    def test_query_summary_success_calls_only_once_on_snapshot(self):
        seen = []
        def summarize(messages, purpose):
            seen.append((messages, purpose))
            return "共 7 筆"
        self.engine.assistant_runner = summarize
        p = self.engine.create_plan("query_summarize", {"query_id": "demo", "parameters": {}})
        t = self.wait_task(self.engine.confirm_plan(p, 1, "approve"))
        self.assertEqual(t["result"]["summary"], "共 7 筆")
        self.assertEqual(t["result"]["summary_status"], "succeeded")
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][1], "summarize")
        self.assertIn('"value":"7"', seen[0][0][0]["content"])

    def test_summary_cancel_retains_completed_table_and_discards_late_summary(self):
        entered = threading.Event()
        self.release.clear()
        # Query must not block in this case; block only the following summary.
        self.engine.query_runner = lambda *a: sample_result()
        def summarize(*args):
            entered.set()
            self.release.wait(2)
            return "晚到摘要"
        self.engine.assistant_runner = summarize
        p = self.engine.create_plan("query_summarize", {"query_id": "demo", "parameters": {}})
        task = self.engine.confirm_plan(p, 1, "approve")
        self.assertTrue(entered.wait(2))
        self.engine.cancel_task(task)
        self.release.set()
        self.engine.close(wait=True)
        t = self.store.task(task)
        self.assertEqual(t["state"], "cancelled")
        self.assertEqual(t["result"]["rows"], [{"value": "7"}])
        self.assertNotIn("summary", t["result"])

    def test_safe_gateway_error_retained(self):
        def fail(*args):
            raise GatewayError("Oracle 尚未接線。")
        self.engine.query_runner = fail
        t = self.wait_task(self.engine.run_query("demo", {}))
        self.assertEqual(t["error"], "Oracle 尚未接線。")

    def test_only_transient_readonly_query_retried_three_times(self):
        attempts = []
        def transient(*args):
            attempts.append(1)
            if len(attempts) < 3:
                raise TimeoutError("private server detail")
            return sample_result()
        self.engine.query_runner = transient
        t = self.wait_task(self.engine.run_query("demo", {}))
        self.assertEqual(t["state"], "succeeded")
        self.assertEqual(len(attempts), 3)

    def test_general_query_summary_validates_and_deduplicates_without_plan(self):
        validations = []
        def validate(query_id, parameters):
            validations.append((query_id, parameters))
            if query_id != "demo":
                raise GatewayError("查詢已停用。")
        self.engine.query_validator = validate
        with self.assertRaises(GatewayError):
            self.engine.run_query_summarize("blocked", {})
        self.assertEqual(self.store.tasks(), [])
        task = self.engine.run_query_summarize("demo", {}, request_id="summary-request")
        self.assertEqual(task, self.engine.run_query_summarize("demo", {}, request_id="summary-request"))
        result = self.wait_task(task)
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(result["result"]["summary_status"], "succeeded")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.store.plans(), [])
        self.assertGreaterEqual(len(validations), 3)

    def test_issue_draft_can_reopen_edit_but_local_saved_cannot(self):
        issue_id = self.store.save_issue("app", "原標題", "原描述", "原預期")
        reopened = Store(self.store.path)
        edited = reopened.update_issue(issue_id, "query", "新標題", "新描述", "新預期")
        self.assertEqual(edited["id"], issue_id)
        self.assertEqual(edited["status"], "draft")
        self.assertEqual(edited["title"], "新標題")
        self.assertEqual(edited["type"], "query")
        self.assertEqual(len(reopened.issues()), 1)
        with self.assertRaises(ValueError):
            reopened.update_issue(issue_id, "query", "", "描述", "預期")
        reopened.submit_issue(issue_id)
        with self.assertRaises(ValueError):
            reopened.update_issue(issue_id, "app", "偷偷覆寫", "描述", "預期")
        self.assertEqual(reopened.issue(issue_id)["title"], "新標題")
        with self.assertRaises(ValueError):
            reopened.update_issue("missing", "app", "標題", "描述", "預期")

    def test_cancel_before_summary_dispatch_prevents_provider_call(self):
        ready_to_dispatch = threading.Event()
        dispatch_release = threading.Event()
        called = []
        original_dispatch = self.engine._dispatch_assistant
        def delayed_dispatch(task_id, messages, purpose):
            ready_to_dispatch.set()
            dispatch_release.wait(2)
            return original_dispatch(task_id, messages, purpose)
        self.engine._dispatch_assistant = delayed_dispatch
        self.engine.assistant_runner = lambda *args: called.append(args) or "不應出現"
        task = self.engine.run_query_summarize("demo", {})
        self.assertTrue(ready_to_dispatch.wait(2))
        self.engine.cancel_task(task)
        dispatch_release.set()
        self.engine.close(wait=True)
        self.assertFalse(called)
        self.assertEqual(self.store.task(task)["state"], "cancelled")
        self.assertEqual(self.store.task(task)["result"]["rows"], [{"value": "7"}])

    def test_cancelled_remote_call_remains_inflight_until_drained(self):
        entered = threading.Event()
        self.release.clear()
        def remote(*args):
            entered.set()
            self.release.wait(3)
            return "晚到結果"
        self.engine.assistant_runner = remote
        conversation = self.store.create_conversation("遠端作業")
        task = self.engine.run_chat(conversation, "測試")
        self.assertTrue(entered.wait(2))
        self.assertEqual(self.engine.inflight_count(), 1)
        self.engine.cancel_task(task)
        self.assertEqual(self.store.task(task)["state"], "cancelled")
        self.assertTrue(self.engine.has_inflight())
        self.engine.close()
        self.assertFalse(self.engine.wait_closed(timeout=0.02))
        self.release.set()
        self.assertTrue(self.engine.wait_closed(timeout=2))
        self.assertFalse(self.engine.has_inflight())
        self.assertIsNone(self.store.task(task)["result"])

    def test_wait_closed_requires_closed_engine(self):
        with self.assertRaises(ValueError):
            self.engine.wait_closed(timeout=0)
        self.engine.close(wait=True)
        self.assertTrue(self.engine.wait_closed(timeout=0))


if __name__ == "__main__":
    unittest.main()
