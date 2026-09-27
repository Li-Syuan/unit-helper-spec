"""Local-only persistence and bounded workflows; no Tk or provider dependencies.

One Engine owns a data directory. Each transaction uses a separate connection.
Cancellation fences result writes; it cannot interrupt a remote provider call.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .gateways import GatewayError

UTC = timezone.utc
TAIPEI = timezone(timedelta(hours=8))
TERMINAL = {"succeeded", "failed", "cancelled"}
_NOT_DISPATCHED = object()


def utcnow():
    return datetime.now(UTC)


def stamp(value=None):
    return (value or utcnow()).astimezone(UTC).isoformat()


def uid():
    return uuid.uuid4().hex


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Store:
    """All data is for the explicitly labelled single local demonstration profile."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise ValueError("資料庫版本較新，請使用相容的應用程式。")
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS conversations(
                    id TEXT PRIMARY KEY,title TEXT NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages(
                    id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    role TEXT NOT NULL,text TEXT NOT NULL,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks(
                    id TEXT PRIMARY KEY,kind TEXT NOT NULL,state TEXT NOT NULL,
                    payload TEXT NOT NULL,result TEXT,error TEXT,conversation_id TEXT,
                    request_id TEXT UNIQUE,request_hash TEXT NOT NULL,
                    plan_id TEXT,schedule_id TEXT,created_at TEXT NOT NULL,finished_at TEXT);
                CREATE TABLE IF NOT EXISTS plans(
                    id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,
                    conversation_id TEXT,revision INTEGER NOT NULL,state TEXT NOT NULL,
                    task_id TEXT UNIQUE,created_at TEXT NOT NULL,expires_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS schedules(
                    id TEXT PRIMARY KEY,name TEXT NOT NULL,query_id TEXT NOT NULL,
                    parameters TEXT NOT NULL,frequency TEXT NOT NULL,time_hhmm TEXT NOT NULL,
                    weekday INTEGER NOT NULL,notify_rule TEXT NOT NULL,threshold TEXT,
                    enabled INTEGER NOT NULL,next_fire TEXT,previous_hash TEXT,
                    previous_condition INTEGER,created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS occurrences(
                    id TEXT PRIMARY KEY,schedule_id TEXT NOT NULL REFERENCES schedules(id),
                    scheduled_at TEXT NOT NULL,state TEXT NOT NULL,task_id TEXT,
                    UNIQUE(schedule_id,scheduled_at));
                CREATE TABLE IF NOT EXISTS notifications(
                    id TEXT PRIMARY KEY,notification_key TEXT NOT NULL UNIQUE,
                    task_id TEXT,text TEXT NOT NULL,is_read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS issues(
                    id TEXT PRIMARY KEY,type TEXT NOT NULL,title TEXT NOT NULL,
                    description TEXT NOT NULL,expected TEXT NOT NULL,status TEXT NOT NULL,
                    created_at TEXT NOT NULL);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(str(self.path), timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def decode(row):
        if row is None:
            raise ValueError("找不到這筆本機資料。")
        item = dict(row)
        for field in ("payload", "result", "parameters", "threshold"):
            if field in item and item[field] is not None:
                item[field] = json.loads(item[field])
        return item

    def _list(self, table, where="", args=()):
        # Table and WHERE come only from the fixed methods below.
        with self.connection() as db:
            return [self.decode(r) for r in db.execute(
                f"SELECT * FROM {table} {where} ORDER BY rowid DESC", args)]

    def _get(self, table, record_id):
        with self.connection() as db:
            return self.decode(db.execute(f"SELECT * FROM {table} WHERE id=?", (record_id,)).fetchone())

    def conversations(self):
        return self._list("conversations")

    def create_conversation(self, title):
        if not isinstance(title, str) or not title.strip():
            raise ValueError("請輸入對話名稱。")
        record_id = uid()
        with self.connection() as db:
            db.execute("INSERT INTO conversations VALUES(?,?,?)", (record_id, title[:120], stamp()))
        return record_id

    def messages(self, conversation_id):
        return list(reversed(self._list("messages", "WHERE conversation_id=?", (conversation_id,))))

    def add_message(self, conversation_id, role, text):
        if role not in {"user", "assistant", "system"} or not isinstance(text, str):
            raise ValueError("訊息格式錯誤。")
        record_id = uid()
        with self.connection() as db:
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
                       (record_id, conversation_id, role, text, stamp()))
        return record_id

    def tasks(self):
        return self._list("tasks")

    def task(self, task_id):
        return self._get("tasks", task_id)

    def plans(self):
        return self._list("plans")

    def plan(self, plan_id):
        return self._get("plans", plan_id)

    def schedules(self):
        return self._list("schedules")

    def schedule(self, schedule_id):
        return self._get("schedules", schedule_id)

    def schedule_runs(self, schedule_id):
        return self._list("occurrences", "WHERE schedule_id=?", (schedule_id,))

    def notifications(self):
        return self._list("notifications")

    def mark_read(self, notification_id):
        with self.connection() as db:
            db.execute("UPDATE notifications SET is_read=1 WHERE id=?", (notification_id,))

    def issues(self):
        return self._list("issues")

    def issue(self, issue_id):
        return self._get("issues", issue_id)

    @staticmethod
    def _validate_issue(type, title, description, expected):
        if type not in {"answer", "query", "app", "schedule", "update", "feature"}:
            raise ValueError("問題類型無效。")
        if not all(isinstance(value, str) for value in (title, description, expected)):
            raise ValueError("回報欄位必須是文字。")
        if not title.strip() or len(title) > 120 or not description.strip() or len(description) > 5000 or len(expected) > 5000:
            raise ValueError("請填寫標題與描述；標題最多 120 字，內容最多 5,000 字。")

    def save_issue(self, type, title, description, expected, status="draft"):
        self._validate_issue(type, title, description, expected)
        if status not in {"draft", "local_saved"}:
            raise ValueError("本機回報不能標示已送至管理平台。")
        record_id = "LOCAL-" + uid()[:12].upper()
        with self.connection() as db:
            db.execute("INSERT INTO issues VALUES(?,?,?,?,?,?,?)",
                       (record_id, type, title, description, expected, status, stamp()))
        return record_id

    def update_issue(self, issue_id, type, title, description, expected):
        self._validate_issue(type, title, description, expected)
        with self.connection() as db:
            cursor = db.execute("""UPDATE issues SET type=?,title=?,description=?,expected=?
                                   WHERE id=? AND status='draft'""",
                                (type, title, description, expected, issue_id))
            if not cursor.rowcount:
                raise ValueError("找不到可修改的草稿；已保存回報不能直接修改。")
        return self.issue(issue_id)

    def submit_issue(self, issue_id):
        with self.connection() as db:
            cursor = db.execute("UPDATE issues SET status='local_saved' WHERE id=?", (issue_id,))
            if not cursor.rowcount:
                raise ValueError("找不到這筆本機回報。")
        return self.issue(issue_id)


class Engine:
    """Single-process local runner. UI polls Store; never receives worker callbacks."""

    def __init__(self, store, query_runner, assistant_runner, query_validator=None):
        self.store, self.query_runner, self.assistant_runner = store, query_runner, assistant_runner
        self.query_validator = query_validator
        self._lock = threading.RLock()
        self._closed = False
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="unit-helper")
        self._futures = set()
        self._assistant_dispatching = set()
        # Only the process holding the app's data-directory lock may create Engine.
        with store.connection() as db:
            db.execute("UPDATE tasks SET state='failed',error=?,finished_at=? WHERE state IN ('queued','running')",
                       ("應用程式已中斷；未自動重送，請確認後重新操作。", stamp()))
            db.execute("UPDATE plans SET state='failed' WHERE state='executing'")
            db.execute("UPDATE occurrences SET state='failed' WHERE state IN ('queued','running')")

    def _ensure_open(self):
        if self._closed:
            raise ValueError("應用程式正在關閉。")

    def _submit(self, task_id):
        """Called with _lock held so a fast completion cannot evade tracking."""
        future = self._pool.submit(self._work, task_id)
        self._futures.add(future)
        future.add_done_callback(self._future_done)

    def _future_done(self, future):
        with self._lock:
            self._futures.discard(future)

    def inflight_count(self):
        """Real unfinished workers, including cancelled tasks whose HTTP is draining."""
        with self._lock:
            return sum(not future.done() for future in self._futures)

    def has_inflight(self):
        return self.inflight_count() > 0

    def _dispatch_assistant(self, task_id, messages, purpose):
        # This locked claim is the dispatch boundary. Cancellation before it prevents
        # the call; cancellation after it cannot revoke an in-flight provider request.
        # Never hold the shared lock through HTTP; results are separately fenced.
        with self._lock:
            if self._closed or self.store.task(task_id)["state"] != "running":
                return _NOT_DISPATCHED
            self._assistant_dispatching.add(task_id)
        try:
            return self.assistant_runner(messages, purpose)
        finally:
            with self._lock:
                self._assistant_dispatching.discard(task_id)

    def _validate(self, kind, payload):
        if kind not in {"query", "query_summarize", "chat", "summarize", "rewrite"} or not isinstance(payload, dict):
            raise ValueError("不支援此工作流程。")
        if kind in {"query", "query_summarize"}:
            if not isinstance(payload.get("query_id"), str) or not payload["query_id"] or not isinstance(payload.get("parameters"), dict):
                raise ValueError("請先填妥查詢及條件。")
            if self.query_validator is not None:
                self.query_validator(payload["query_id"], payload["parameters"])
        elif not isinstance(payload.get("text"), str) or not payload["text"].strip() or len(payload["text"]) > 50000:
            raise ValueError("請提供 1 至 50,000 字文字。")
        dumps(payload)  # Reject non-serializable values before any write.

    def _new_task(self, db, kind, payload, conversation_id=None, request_id=None, plan_id=None, schedule_id=None):
        request_hash = hashlib.sha256(dumps([kind, payload, conversation_id, plan_id, schedule_id]).encode()).hexdigest()
        if request_id:
            existing = db.execute("SELECT id,request_hash FROM tasks WHERE request_id=?", (request_id,)).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise ValueError("相同請求編號不能提交不同內容。")
                return existing["id"], False
        if conversation_id and kind not in {"query", "query_summarize"}:
            if not db.execute("SELECT 1 FROM conversations WHERE id=?", (conversation_id,)).fetchone():
                raise ValueError("找不到對話，請建立新對話。")
            if db.execute("SELECT 1 FROM tasks WHERE conversation_id=? AND state IN ('queued','running')", (conversation_id,)).fetchone():
                raise ValueError("此對話還有工作進行中，請等待或取消。")
            history = [{"role": r["role"], "content": r["text"]} for r in db.execute(
                "SELECT role,text FROM messages WHERE conversation_id=? ORDER BY rowid", (conversation_id,))]
            payload = dict(payload)
            payload["_messages"] = history + [{"role": "user", "content": payload["text"]}]
        record_id = uid()
        db.execute("""INSERT INTO tasks(id,kind,state,payload,conversation_id,request_id,
                      request_hash,plan_id,schedule_id,created_at) VALUES(?,?,'queued',?,?,?,?,?,?,?)""",
                   (record_id, kind, dumps(payload), conversation_id, request_id, request_hash, plan_id, schedule_id, stamp()))
        if conversation_id and kind not in {"query", "query_summarize"}:
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
                       (uid(), conversation_id, "user", payload["text"], stamp()))
        return record_id, True

    def _queue(self, kind, payload, conversation_id=None, request_id=None):
        self._validate(kind, payload)
        with self._lock:
            self._ensure_open()
            with self.store.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                task_id, created = self._new_task(db, kind, payload, conversation_id, request_id)
            if created:
                self._submit(task_id)
            return task_id

    def run_query(self, query_id, params, request_id=None):
        return self._queue("query", {"query_id": query_id, "parameters": params}, request_id=request_id)

    def run_query_summarize(self, query_id, parameters, request_id=None):
        """General-mode explicit submission; shares the same validated bounded flow."""
        return self._queue("query_summarize", {"query_id": query_id, "parameters": parameters}, request_id=request_id)

    def run_chat(self, conversation_id, text, purpose="chat", request_id=None):
        if purpose not in {"chat", "summarize", "rewrite"}:
            raise ValueError("文字操作類型無效。")
        return self._queue(purpose, {"text": text, "conversation_id": conversation_id}, conversation_id, request_id)

    def create_plan(self, kind, payload, conversation_id=None):
        self._validate(kind, payload)
        with self._lock:
            self._ensure_open()
            record_id = uid()
            with self.store.connection() as db:
                db.execute("INSERT INTO plans VALUES(?,?,?,?,1,'ready',NULL,?,?)",
                           (record_id, kind, dumps(payload), conversation_id or payload.get("conversation_id"),
                            stamp(), stamp(utcnow() + timedelta(hours=24))))
            return record_id

    def edit_plan(self, plan_id, expected_revision, kind, payload):
        self._validate(kind, payload)
        with self._lock, self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            p = self.store.decode(db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone())
            if p["state"] != "ready" or p["revision"] != expected_revision or p["expires_at"] <= stamp():
                raise ValueError("計畫已失效或已執行，請建立新計畫。")
            db.execute("UPDATE plans SET kind=?,payload=?,revision=revision+1,conversation_id=? WHERE id=?",
                       (kind, dumps(payload), payload.get("conversation_id", p["conversation_id"]), plan_id))
        return self.store.plan(plan_id)

    def confirm_plan(self, plan_id, revision, request_id):
        if not request_id:
            raise ValueError("確認必須有請求編號。")
        with self._lock:
            self._ensure_open()
            with self.store.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                p = self.store.decode(db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone())
                if p["revision"] != revision:
                    raise ValueError("計畫已修改，請重新預覽後確認。")
                if p["state"] == "cancelled":
                    raise ValueError("計畫已取消，請建立新計畫。")
                if p["task_id"]:
                    return p["task_id"]
                if p["state"] != "ready" or p["expires_at"] <= stamp():
                    raise ValueError("計畫已取消或過期，請建立新計畫。")
                self._validate(p["kind"], p["payload"])
                task_id, created = self._new_task(db, p["kind"], p["payload"], p["conversation_id"], request_id, plan_id)
                db.execute("UPDATE plans SET state='executing',task_id=? WHERE id=?", (task_id, plan_id))
            if created:
                self._submit(task_id)
            return task_id

    def cancel_plan(self, plan_id):
        with self._lock:
            p = self.store.plan(plan_id)
            if p["task_id"]:
                self.cancel_task(p["task_id"])
            with self.store.connection() as db:
                db.execute("UPDATE plans SET state='cancelled' WHERE id=? AND state NOT IN ('succeeded','failed')", (plan_id,))

    def cancel_task(self, task_id):
        with self._lock, self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE tasks SET state='cancelled',finished_at=? WHERE id=? AND state IN ('queued','running')", (stamp(), task_id))
            db.execute("UPDATE plans SET state='cancelled' WHERE task_id=? AND state='executing'", (task_id,))
            db.execute("UPDATE occurrences SET state='cancelled' WHERE task_id=? AND state IN ('queued','running')", (task_id,))

    def _work(self, task_id):
        with self._lock, self.store.connection() as db:
            cursor = db.execute("UPDATE tasks SET state='running' WHERE id=? AND state='queued'", (task_id,))
            if not cursor.rowcount:
                return
            db.execute("UPDATE occurrences SET state='running' WHERE task_id=?", (task_id,))
        task = self.store.task(task_id)
        try:
            if task["kind"] in {"query", "query_summarize"}:
                self._validate(task["kind"], task["payload"])
                for attempt in range(3):
                    if self.store.task(task_id)["state"] != "running":
                        return
                    try:
                        result = self.query_runner(task["payload"]["query_id"], task["payload"]["parameters"])
                        break
                    except (ConnectionError, TimeoutError):
                        if attempt == 2:
                            raise
                if not isinstance(result, dict) or not isinstance(result.get("rows"), list):
                    raise ValueError("查詢結果格式錯誤。")
                if task["kind"] == "query_summarize":
                    # Fixed two-step flow; a failed summary cannot discard or requery data.
                    result = dict(result)
                    result["summary_status"] = "pending"
                    with self._lock, self.store.connection() as db:
                        if not db.execute("UPDATE tasks SET result=? WHERE id=? AND state='running'",
                                          (dumps(result), task_id)).rowcount:
                            return
                    summary_input = dumps({"source": result.get("source_label"),
                                           "parameters": result.get("parameters"),
                                           "truncated": result.get("truncated", False),
                                           "columns": result.get("columns"), "rows": result["rows"]})
                    try:
                        if len(summary_input) > 50000:
                            raise GatewayError("結果超過摘要文字上限，請縮小查詢範圍。")
                        summary = self._dispatch_assistant(task_id, [{"role": "user", "content": summary_input}], "summarize")
                        if summary is _NOT_DISPATCHED:
                            return
                        if not isinstance(summary, str) or not summary.strip():
                            raise GatewayError("助理未提供有效摘要。")
                        result.update(summary=summary, summary_status="succeeded")
                    except Exception as exc:
                        result.update(summary_status="failed", summary_error=(str(exc) if isinstance(exc, GatewayError)
                                      else "表格已完成，摘要未完成。請檢查助理連線設定。"))
            else:
                # Immutable context snapshot avoids interleaving another request's text.
                history = task["payload"].get("_messages", [{"role": "user", "content": task["payload"]["text"]}])
                answer = self._dispatch_assistant(task_id, history, task["kind"])
                if answer is _NOT_DISPATCHED:
                    return
                if not isinstance(answer, str) or not answer.strip():
                    raise ValueError("助理未提供有效文字。")
                result = {"text": answer, "original": task["payload"]["text"]}
            self._finish(task_id, "succeeded", result=result)
        except Exception as exc:
            # Provider exception strings may contain URLs, headers, SQL or credentials.
            safe_error = str(exc) if isinstance(exc, GatewayError) else "工作失敗，請檢查連線或輸入設定後重試。錯誤編號 TASK_FAILED。"
            self._finish(task_id, "failed", error=safe_error)

    def _finish(self, task_id, state, result=None, error=None):
        with self._lock, self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            t = self.store.decode(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
            if t["state"] != "running":
                return  # Cancellation/close fences every later result and notification.
            db.execute("UPDATE tasks SET state=?,result=?,error=?,finished_at=? WHERE id=?",
                       (state, dumps(result) if result is not None else None, error, stamp(), task_id))
            db.execute("UPDATE plans SET state=? WHERE task_id=?", (state, task_id))
            db.execute("UPDATE occurrences SET state=? WHERE task_id=?", (state, task_id))
            if state == "succeeded" and t["conversation_id"] and t["kind"] not in {"query", "query_summarize"}:
                db.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
                           (uid(), t["conversation_id"], "assistant", result["text"], stamp()))
            if t["schedule_id"]:
                self._notify_result(db, t, state, result)

    @staticmethod
    def _next_fire(schedule, after):
        local = after.astimezone(TAIPEI)
        hour, minute = map(int, schedule["time_hhmm"].split(":"))
        candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if schedule["frequency"] == "weekly":
            candidate += timedelta(days=(schedule["weekday"] - candidate.weekday()) % 7)
        if candidate <= local:
            candidate += timedelta(days=7 if schedule["frequency"] == "weekly" else 1)
        return candidate.astimezone(UTC)

    def create_schedule(self, source_task_id, name, frequency, time_hhmm, weekday=0,
                        notify_rule="nonempty_on_change", threshold=None):
        t = self.store.task(source_task_id)
        if t["kind"] not in {"query", "query_summarize"} or t["state"] != "succeeded":
            raise ValueError("只能從成功的查詢建立排程。")
        try:
            hour, minute = map(int, time_hhmm.split(":"))
            valid_time = 0 <= hour <= 23 and 0 <= minute <= 59 and len(time_hhmm) == 5
        except (ValueError, AttributeError):
            valid_time = False
        if not name.strip() or len(name) > 120 or frequency not in {"daily", "weekly"} or not valid_time or weekday not in range(7):
            raise ValueError("請填寫有效名稱、每日／每週頻率及 HH:MM 時間。")
        if notify_rule not in {"nonempty_on_change", "threshold_crossing"}:
            raise ValueError("通知條件無效。")
        if notify_rule == "threshold_crossing":
            self._threshold_condition(t["result"], threshold)
        record_id = uid()
        with self.store.connection() as db:
            db.execute("""INSERT INTO schedules(id,name,query_id,parameters,frequency,time_hhmm,
                weekday,notify_rule,threshold,enabled,created_at) VALUES(?,?,?,?,?,?,?,?,?,0,?)""",
                       (record_id, name, t["payload"]["query_id"], dumps(t["payload"]["parameters"]),
                        frequency, time_hhmm, weekday, notify_rule, dumps(threshold) if threshold is not None else None, stamp()))
        return record_id

    def schedules(self):
        return self.store.schedules()

    def schedule_runs(self, schedule_id):
        return self.store.schedule_runs(schedule_id)

    def schedule_preview(self, schedule_id, now=None):
        s = self.store.schedule(schedule_id)
        current = now or utcnow()
        result = []
        for _ in range(3):
            current = self._next_fire(s, current)
            result.append({"scheduled_at": stamp(current), "parameters": self._schedule_parameters(s, current)})
        return result

    def set_schedule_enabled(self, schedule_id, enabled, now=None):
        with self._lock:
            s = self.store.schedule(schedule_id)
            # Repeated enabling does not reset the occurrence watermark.
            if bool(s["enabled"]) == bool(enabled):
                return
            next_fire = stamp(self._next_fire(s, now or utcnow())) if enabled else s["next_fire"]
            with self.store.connection() as db:
                db.execute("UPDATE schedules SET enabled=?,next_fire=? WHERE id=?", (int(bool(enabled)), next_fire, schedule_id))

    def set_schedule_date_mode(self, schedule_id, mode):
        """Explicit draft-only choice: literal dates or rolling previous_day."""
        if mode not in {"literal", "previous_day"}:
            raise ValueError("日期模式無效。")
        with self._lock, self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            s = self.store.decode(db.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone())
            if s["enabled"]:
                raise ValueError("請先停用排程再修改日期模式。")
            parameters = s["parameters"]
            parameters["_date_mode"] = mode
            db.execute("UPDATE schedules SET parameters=? WHERE id=?", (dumps(parameters), schedule_id))

    @staticmethod
    def _schedule_parameters(schedule, occurrence):
        parameters = dict(schedule["parameters"])
        mode = parameters.pop("_date_mode", "literal")
        if mode == "previous_day":
            today = occurrence.astimezone(TAIPEI).date()
            parameters.update(from_date=str(today - timedelta(days=1)), to_date=str(today))
        return parameters

    def run_schedule_now(self, schedule_id, request_id=None):
        with self._lock:
            self._ensure_open()
            s = self.store.schedule(schedule_id)
            now = utcnow()
            key = "manual:" + (request_id or uid())
            with self.store.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                task_id = self._claim_occurrence(db, s, key, now)
            if task_id:
                self._submit(task_id)
            return task_id

    def _claim_occurrence(self, db, schedule, key, occurrence):
        old = db.execute("SELECT task_id FROM occurrences WHERE schedule_id=? AND scheduled_at=?", (schedule["id"], key)).fetchone()
        if old:
            return None
        overlap = db.execute("SELECT 1 FROM tasks WHERE schedule_id=? AND state IN ('queued','running')", (schedule["id"],)).fetchone()
        if overlap:
            db.execute("INSERT INTO occurrences VALUES(?,?,?,'skipped_overlap',NULL)", (uid(), schedule["id"], key))
            return None
        params = self._schedule_parameters(schedule, occurrence)
        task_id, _ = self._new_task(db, "query", {"query_id": schedule["query_id"], "parameters": params},
                                  request_id="schedule:" + schedule["id"] + ":" + key, schedule_id=schedule["id"])
        db.execute("INSERT INTO occurrences VALUES(?,?,?,'queued',?)", (uid(), schedule["id"], key, task_id))
        return task_id

    def tick(self, now=None):
        now = now or utcnow()
        if now.tzinfo is None:
            raise ValueError("排程時鐘必須包含時區。")
        queued = []
        with self._lock:
            if self._closed:
                return
            with self.store.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                schedules = [self.store.decode(r) for r in db.execute("SELECT * FROM schedules WHERE enabled=1 AND next_fire<=?", (stamp(now),))]
                for s in schedules:
                    due = datetime.fromisoformat(s["next_fire"])
                    period = timedelta(days=7 if s["frequency"] == "weekly" else 1)
                    # At most one compact missed record even after years offline.
                    skipped = int((now - due) // period)
                    latest = due + skipped * period
                    if skipped:
                        db.execute("INSERT OR IGNORE INTO occurrences VALUES(?,?,?,'missed',NULL)", (uid(), s["id"], stamp(due)))
                    if now - latest <= timedelta(hours=24):
                        task_id = self._claim_occurrence(db, s, stamp(latest), latest)
                        if task_id:
                            queued.append(task_id)
                    else:
                        db.execute("INSERT OR IGNORE INTO occurrences VALUES(?,?,?,'missed',NULL)", (uid(), s["id"], stamp(latest)))
                    db.execute("UPDATE schedules SET next_fire=? WHERE id=?", (stamp(latest + period), s["id"]))
            for task_id in queued:
                self._submit(task_id)

    @staticmethod
    def _threshold_condition(result, threshold):
        if not isinstance(threshold, dict) or threshold.get("operator") not in {">", ">=", "<", "<=", "=="}:
            raise ValueError("門檻需指定 operator 及 value。")
        rows, columns = result.get("rows", []), result.get("columns", [])
        if result.get("truncated") or len(rows) != 1 or len(columns) != 1 or columns[0].get("type") not in {"number", "integer", "decimal", "float"}:
            raise ValueError("門檻通知只支援未截斷的單一數值結果。")
        raw = rows[0][columns[0]["name"]] if isinstance(rows[0], dict) else rows[0][0]
        try:
            value, limit = Decimal(str(raw)), Decimal(str(threshold["value"]))
            if not value.is_finite() or not limit.is_finite():
                raise InvalidOperation
        except (InvalidOperation, KeyError):
            raise ValueError("門檻及結果必須是有限數字。") from None
        return {">": value > limit, ">=": value >= limit, "<": value < limit,
                "<=": value <= limit, "==": value == limit}[threshold["operator"]]

    def _notify_result(self, db, task, state, result):
        s = self.store.decode(db.execute("SELECT * FROM schedules WHERE id=?", (task["schedule_id"],)).fetchone())
        notify = state == "failed"
        text = "排程「" + s["name"] + "」執行失敗，請查看工作狀態。"
        if state == "succeeded":
            digest = hashlib.sha256(dumps([result.get("columns"), result["rows"]]).encode()).hexdigest()
            if s["notify_rule"] == "threshold_crossing":
                try:
                    condition = self._threshold_condition(result, s["threshold"])
                    notify = condition and not s["previous_condition"]
                    db.execute("UPDATE schedules SET previous_condition=? WHERE id=?", (int(condition), s["id"]))
                except ValueError:
                    notify = True
                    text = "排程「" + s["name"] + "」查詢完成，但結果不符合單值門檻條件。"
            else:
                notify = bool(result["rows"]) and digest != s["previous_hash"]
            db.execute("UPDATE schedules SET previous_hash=? WHERE id=?", (digest, s["id"]))
            if "不符合" not in text:
                text = "排程「" + s["name"] + "」有符合條件的新結果。"
        if notify:
            db.execute("INSERT OR IGNORE INTO notifications VALUES(?,?,?,?,0,?)",
                       (uid(), "task:" + task["id"] + ":result", task["id"], text, stamp()))

    def close(self, wait=False):
        """Fence tasks immediately; optionally wait for actual remote workers to drain."""
        with self._lock:
            if not self._closed:
                self._closed = True
                with self.store.connection() as db:
                    db.execute("UPDATE tasks SET state='cancelled',finished_at=? WHERE state IN ('queued','running')", (stamp(),))
                    db.execute("UPDATE plans SET state='cancelled' WHERE state='executing'")
                    db.execute("UPDATE occurrences SET state='cancelled' WHERE state IN ('queued','running')")
        # Workers and future callbacks need _lock during shutdown.
        self._pool.shutdown(wait=wait, cancel_futures=True)

    def wait_closed(self, timeout=None):
        """Wait after close; return whether all real worker futures have completed."""
        with self._lock:
            if not self._closed:
                raise ValueError("請先關閉工作引擎，再等待工作結束。")
            futures = tuple(future for future in self._futures if not future.done())
        if not futures:
            return True
        _, unfinished = wait(futures, timeout=timeout)
        return not unfinished
