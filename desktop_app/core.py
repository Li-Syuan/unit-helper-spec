"""Local-only persistence and bounded workflows; no Tk or provider dependencies.

One Engine owns a data directory. Each transaction uses a separate connection.
Cancellation fences result writes; it cannot interrupt a remote provider call.
"""
from __future__ import annotations

import hashlib
import copy
import json
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .gateways import GatewayError
from .local_work import LocalWorkStore, initialize_work_schema
from .conversation_actions import initialize_action_schema
from .query_schema import find_template, parameters as validate_parameters, date_mapping, LEGACY_DATE_RANGES

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


class Store(LocalWorkStore):
    """All data is for the explicitly labelled single local demonstration profile."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._draft_lock = threading.RLock()
        self._draft_revisions = {}
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 6:
                raise ValueError("資料庫版本較新，請使用相容的應用程式。")
            if version in (1, 2, 3, 4, 5):
                backup=self.path.with_name(self.path.name+'.pre-v6-'+uid()+'.bak')
                with sqlite3.connect(str(backup)) as target: db.backup(target)
            db.executescript("""
                PRAGMA journal_mode=WAL;
                BEGIN IMMEDIATE;
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

            """)
            if version < 2:
                db.execute("ALTER TABLE conversations ADD COLUMN binding TEXT")
                db.execute("ALTER TABLE conversations ADD COLUMN source TEXT")
            initialize_work_schema(db)
            initialize_action_schema(db)
            from .workflows import initialize_workflow_schema
            initialize_workflow_schema(db)
            from .outcomes import initialize_outcome_schema
            initialize_outcome_schema(db)
            db.execute("PRAGMA user_version=6")
            self._draft_revisions = {row['conversation_id']: row['revision'] for row in db.execute('SELECT conversation_id,revision FROM drafts')}

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
        for field in ("payload", "result", "parameters", "threshold", "binding", "source"):
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

    def conversation(self, record_id):
        return self._get("conversations",record_id)

    def create_conversation(self, title, binding=None, source=None):
        if not isinstance(title, str) or not title.strip():
            raise ValueError("請輸入對話名稱。")
        record_id = uid()
        with self.connection() as db:
            db.execute("INSERT INTO conversations(id,title,created_at,binding,source) VALUES(?,?,?,?,?)",
                       (record_id,title[:120],stamp(),dumps(binding or {"profile_id":"demo","revision":1}),dumps(source) if source else None))
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
        return self._list("tasks", "WHERE state!='deleted'")

    def task(self, task_id):
        task=self._get("tasks", task_id)
        if task['state']=='deleted':raise ValueError('工作內容已刪除；舊請求不會重新執行。')
        return task

    def plans(self):
        return self._list("plans")

    def plan(self, plan_id):
        return self._get("plans", plan_id)

    def schedules(self):
        return self._list("schedules")

    def schedule(self, schedule_id):
        return self._get("schedules", schedule_id)

    def schedule_source(self, schedule_id):
        with self.connection() as db:
            row=db.execute('SELECT conversation_id FROM schedule_sources WHERE schedule_id=?',(schedule_id,)).fetchone()
            return dict(row) if row is not None else None

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

    def __init__(self, store, query_runner, assistant_runner, query_validator=None, query_catalog=None, assistant_router=None, binding_validator=None):
        self.store, self.query_runner, self.assistant_runner = store, query_runner, assistant_runner
        self.assistant_router=assistant_router; self.binding_validator=binding_validator
        self.query_validator = query_validator
        self.query_catalog = query_catalog or getattr(getattr(query_runner, "__self__", None), "catalog", None)
        self._lock = threading.RLock()
        self._closed = False
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="unit-helper")
        self._futures = set()
        self._future_tasks = {}
        self._deletion_previews = {}
        self._assistant_dispatching = set()
        # Only the process holding the app's data-directory lock may create Engine.
        with store.connection() as db:
            db.execute("UPDATE schedules SET enabled=0 WHERE id IN (SELECT schedule_id FROM tasks WHERE kind IN ('workflow','assistant_briefing') AND state IN ('queued','running'))")
            db.execute("UPDATE tasks SET state='failed',error=?,finished_at=? WHERE state IN ('queued','running')",
                       ("應用程式已中斷；未自動重送，請確認後重新操作。", stamp()))
            db.execute("UPDATE plans SET state='failed' WHERE state='executing'")
            db.execute("UPDATE occurrences SET state='failed' WHERE state IN ('queued','running')")

    def _ensure_open(self):
        if getattr(self,'authorization',None):self.authorization()
        if self._closed:
            raise ValueError("應用程式正在關閉。")

    def _submit(self, task_id):
        """Called with _lock held so a fast completion cannot evade tracking."""
        future = self._pool.submit(self._work, task_id)
        self._futures.add(future)
        self._future_tasks[future] = task_id
        future.add_done_callback(self._future_done)

    def _future_done(self, future):
        with self._lock:
            self._futures.discard(future)
            self._future_tasks.pop(future, None)

    def _deletion_snapshot(self, db, ids):
        """Read one consistent deletion boundary; never follow copied source links."""
        placeholders = ','.join('?' for _ in ids)
        data = {}
        for table, column in (("conversations", "id"), ("messages", "conversation_id"),
                              ("plans", "conversation_id"), ("tasks", "conversation_id")):
            data[table] = [dict(row) for row in db.execute(
                f"SELECT * FROM {table} WHERE {column} IN ({placeholders}) ORDER BY id", ids)]
        if len(data["conversations"]) != len(ids):
            raise ValueError("選定對話已不存在，請重新整理後選擇。")
        data['drafts'] = [dict(row) for row in db.execute(
            f"SELECT * FROM drafts WHERE conversation_id IN ({placeholders}) ORDER BY conversation_id", ids)]
        actions=[dict(row) for row in db.execute(
            f"SELECT * FROM conversation_actions WHERE conversation_id IN ({placeholders}) ORDER BY id",ids)]
        if actions:data['actions']=actions
        if hasattr(self,'_workflows'):
            workflows=self._workflows.deletion_snapshot(db,ids)
            if workflows:data['workflows']=workflows
        if any(cid in ids for cid in getattr(self,'_action_parsing',{}).values()):
            raise ValueError('選定對話的需求解析尚未結束，請稍後再刪除。')
        linked={a['task_id'] for a in actions if a['task_id']}
        for task_id in linked:
            row=db.execute('SELECT state FROM tasks WHERE id=?',(task_id,)).fetchone()
            if (row and row['state'] in {'queued','running'}) or any(
                tid==task_id and not f.done() for f,tid in self._future_tasks.items()):
                raise ValueError('選定對話交辦的工作尚未結束，請稍後再刪除。')
        task_ids = {row["id"] for row in data["tasks"]}
        plan_ids = {row["id"] for row in data["plans"]}
        if (any(row["state"] in {"queued", "running", "executing"} for row in data["tasks"])
                or any(row["state"] == "executing" for row in data["plans"])
                or any(task_id in task_ids and not future.done()
                       for future, task_id in self._future_tasks.items())
                or bool(task_ids & self._assistant_dispatching)):
            raise ValueError("選定對話仍有工作進行中，或取消後的遠端請求尚未結束；請稍後再刪除。")
        # An unexpected cross-boundary link is not permission to delete independent work.
        if (any(row["schedule_id"] for row in data["tasks"])
                or any(row["plan_id"] and row["plan_id"] not in plan_ids for row in data["tasks"])
                or any(row["task_id"] and row["task_id"] not in task_ids for row in data["plans"])):
            raise ValueError("選定對話含獨立工作或排程關聯，不能直接刪除。")
        data["notifications"] = []
        if task_ids:
            task_marks = ','.join('?' for _ in task_ids)
            task_args = sorted(task_ids)
            if db.execute(f"SELECT 1 FROM occurrences WHERE task_id IN ({task_marks})", task_args).fetchone():
                raise ValueError("選定對話含排程執行紀錄，不能直接刪除。")
            linked_plans = db.execute(f"SELECT id FROM plans WHERE task_id IN ({task_marks})", task_args)
            if any(row["id"] not in plan_ids for row in linked_plans):
                raise ValueError("選定對話含獨立計畫關聯，不能直接刪除。")
            data["notifications"] = [dict(row) for row in db.execute(
                f"SELECT * FROM notifications WHERE task_id IN ({task_marks}) ORDER BY id", task_args)]
        if plan_ids:
            plan_marks = ','.join('?' for _ in plan_ids)
            linked_tasks = db.execute(f"SELECT id FROM tasks WHERE plan_id IN ({plan_marks})", sorted(plan_ids))
            if any(row["id"] not in task_ids for row in linked_tasks):
                raise ValueError("選定對話含獨立工作關聯，不能直接刪除。")
        summary = {"conversations": [{"id": row["id"], "title": row["title"]}
                                     for row in data["conversations"]],
                   "counts": {table: len(rows) for table, rows in data.items()},
                   "task_ids": sorted(task_ids), "plan_ids": sorted(plan_ids)}
        fingerprint = hashlib.sha256(dumps(data).encode('utf-8')).hexdigest()
        return summary, fingerprint

    def preview_conversation_deletion(self, ids):
        """Issue an opaque, ten-minute confirmation token for this exact snapshot."""
        if not isinstance(ids, (list, tuple, set)) or not ids or any(
                not isinstance(item, str) or not item for item in ids):
            raise ValueError("請先選擇要刪除的對話。")
        selected = tuple(sorted(set(ids)))
        with self._lock:
            self._ensure_open()
            with self.store.connection() as db:
                db.execute("BEGIN")
                summary, fingerprint = self._deletion_snapshot(db, selected)
            now = time.monotonic()
            self._deletion_previews = {key: value for key, value in self._deletion_previews.items()
                                       if value["expires"] > now}
            token = uid()
            self._deletion_previews[token] = {"ids": selected, "fingerprint": fingerprint,
                                              "expires": now + 600}
            return dict(summary, token=token)

    def delete_conversations(self, token):
        """Recheck the preview and remove the whole batch in one SQLite transaction."""
        with self._lock:
            self._ensure_open()
            preview = self._deletion_previews.get(token) if isinstance(token, str) else None
            if preview is None or preview["expires"] <= time.monotonic():
                if isinstance(token, str):
                    self._deletion_previews.pop(token, None)
                raise ValueError("刪除確認已失效，請重新預覽。")
            with self.store.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                summary, fingerprint = self._deletion_snapshot(db, preview["ids"])
                if fingerprint != preview["fingerprint"]:
                    self._deletion_previews.pop(token, None)
                    raise ValueError("對話內容或工作狀態已變更，請重新預覽後刪除。")
                owner=getattr(self.assistant_router,'__self__',None)
                if hasattr(owner,'forget_conversations_tx') and hasattr(owner,'path'):
                    owner.forget_conversations_tx(db,preview['ids'])
                if summary["task_ids"]:
                    marks = ','.join('?' for _ in summary["task_ids"])
                    db.execute(f"DELETE FROM notifications WHERE task_id IN ({marks})", summary["task_ids"])
                marks = ','.join('?' for _ in preview["ids"])
                db.execute(f"DELETE FROM conversation_actions WHERE conversation_id IN ({marks})",preview['ids'])
                db.execute(f"UPDATE schedule_sources SET conversation_id=NULL WHERE conversation_id IN ({marks})",preview['ids'])
                if hasattr(self,'_workflows'):self._workflows.delete_source(db,preview['ids'])
                for table in ("messages", "plans", "tasks", "drafts"):
                    db.execute(f"DELETE FROM {table} WHERE conversation_id IN ({marks})", preview["ids"])
                db.execute(f"DELETE FROM conversations WHERE id IN ({marks})", preview["ids"])
            self._deletion_previews.pop(token, None)
            return dict(summary, token=token, deleted_ids=list(preview["ids"]))

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
            if self.assistant_router is not None:
                binding=self.store.task(task_id)["payload"].get("_binding")
                self.binding_validator(binding)
                owner=getattr(self.assistant_router,'__self__',None)
                if hasattr(owner,'inspect_request') and getattr(owner,'data',{}).get('wire_mode')=='assistants':
                    task=self.store.task(task_id)
                    context={'conversation_id':('engine:'+task['conversation_id']) if purpose=='chat' and task['conversation_id'] else 'task:'+task_id,
                             'search_authorized':task['kind']=='assistant_briefing',
                             'request_id':task_id,'cancelled':lambda:self._closed or self.store.task(task_id)['state']!='running'}
                    return self.assistant_router(messages,purpose,binding,context=context)
                return self.assistant_router(messages,purpose,binding)
            return self.assistant_runner(messages, purpose)
        finally:
            with self._lock:
                self._assistant_dispatching.discard(task_id)

    def _validate(self, kind, payload):
        if getattr(self,'authorization',None):self.authorization()
        if kind not in {"query", "query_summarize", "chat", "summarize", "rewrite"} or not isinstance(payload, dict):
            raise ValueError("不支援此工作流程。")
        if kind == "query_summarize" and self.assistant_router is not None:
            raise ValueError("請先完成查詢，再選擇資料與助理，預覽後送出。")
        if kind in {"query", "query_summarize"}:
            if not isinstance(payload.get("query_id"), str) or not payload["query_id"] or not isinstance(payload.get("parameters"), dict):
                raise ValueError("請先填妥查詢及條件。")
            if self.query_catalog is not None:
                validate_parameters(find_template(self.query_catalog(), payload["query_id"]), payload["parameters"])
            if self.query_validator is not None:
                self.query_validator(payload["query_id"], payload["parameters"])
        elif not isinstance(payload.get("text"), str) or not payload["text"].strip() or len(payload["text"]) > 50000:
            raise ValueError("請提供 1 至 50,000 字文字。")
        dumps(payload)  # Reject non-serializable values before any write.

    def _new_task(self, db, kind, payload, conversation_id=None, request_id=None, plan_id=None, schedule_id=None):
        if conversation_id is not None and not db.execute(
                "SELECT 1 FROM conversations WHERE id=?", (conversation_id,)).fetchone():
            raise ValueError("找不到對話，請建立新對話。")
        if self.assistant_router is not None and kind not in {"query","query_summarize"}:
            row=db.execute("SELECT binding FROM conversations WHERE id=?",(conversation_id,)).fetchone()
            if not row: raise ValueError("找不到對話。")
            binding=json.loads(row["binding"]) if row["binding"] else None
            self.binding_validator(binding)
            if "_binding" in payload and payload["_binding"]!=binding: raise ValueError("計畫助理版本不符，請建立新計畫。")
            payload=dict(payload,_binding=binding)
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

    def _consume_draft(self, db, cid, revision):
        if revision is not None:
            if not cid or self.store._draft_revisions.get(cid) != revision:
                raise ValueError('草稿內容已變更，請重新送出。')
            db.execute('DELETE FROM drafts WHERE conversation_id=?', (cid,))

    def _queue(self, kind, payload, conversation_id=None, request_id=None, draft_revision=None):
        self._validate(kind, payload)
        with self._lock, self.store._draft_lock:
            self._ensure_open()
            with self.store.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                task_id, created = self._new_task(db, kind, payload, conversation_id, request_id)
                self._consume_draft(db, conversation_id, draft_revision)
            if draft_revision is not None:
                self.store.reserve_draft(conversation_id)
            if created:
                self._submit(task_id)
            return task_id

    def run_query(self, query_id, params, request_id=None):
        return self._queue("query", {"query_id": query_id, "parameters": params}, request_id=request_id)

    def run_query_summarize(self, query_id, parameters, request_id=None):
        """General-mode explicit submission; shares the same validated bounded flow."""
        return self._queue("query_summarize", {"query_id": query_id, "parameters": parameters}, request_id=request_id)

    def run_chat(self, conversation_id, text, purpose="chat", request_id=None, draft_revision=None):
        if purpose not in {"chat", "summarize", "rewrite"}:
            raise ValueError("文字操作類型無效。")
        return self._queue(purpose, {"text": text, "conversation_id": conversation_id}, conversation_id, request_id, draft_revision)

    def _plan_binding(self,kind,payload,conversation_id=None):
        if self.assistant_router is None or kind in {"query","query_summarize"}: return payload
        binding=self.store.conversation(conversation_id or payload.get("conversation_id"))["binding"]
        self.binding_validator(binding)
        return dict(payload,_binding=binding)

    def create_plan(self, kind, payload, conversation_id=None, draft_revision=None):
        payload=self._plan_binding(kind,payload,conversation_id)
        self._validate(kind, payload)
        with self._lock, self.store._draft_lock:
            self._ensure_open()
            record_id = uid()
            with self.store.connection() as db:
                db.execute("BEGIN IMMEDIATE")
                target_id = conversation_id or payload.get("conversation_id")
                if target_id is not None and not db.execute(
                        "SELECT 1 FROM conversations WHERE id=?", (target_id,)).fetchone():
                    raise ValueError("找不到對話，請建立新對話。")
                db.execute("INSERT INTO plans VALUES(?,?,?,?,1,'ready',NULL,?,?)",
                           (record_id, kind, dumps(payload), conversation_id or payload.get("conversation_id"),
                            stamp(), stamp(utcnow() + timedelta(hours=24))))
                self._consume_draft(db, target_id, draft_revision)
            if draft_revision is not None:
                self.store.reserve_draft(target_id)
            return record_id

    def edit_plan(self, plan_id, expected_revision, kind, payload):
        payload=self._plan_binding(kind,payload)
        self._validate(kind, payload)
        with self._lock, self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            p = self.store.decode(db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone())
            if p["state"] != "ready" or p["revision"] != expected_revision or p["expires_at"] <= stamp():
                raise ValueError("計畫已失效或已執行，請建立新計畫。")
            target_id = payload.get("conversation_id", p["conversation_id"])
            if target_id is not None and not db.execute(
                    "SELECT 1 FROM conversations WHERE id=?", (target_id,)).fetchone():
                raise ValueError("找不到對話，請建立新對話。")
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
                task_id, created = self._confirm_plan_tx(db, plan_id, revision, request_id)
            if created:
                self._submit(task_id)
            return task_id

    def _confirm_plan_tx(self, db, plan_id, revision, request_id):
        """Caller holds the engine lock and transaction; dispatch only after commit."""
        if not request_id:
            raise ValueError("確認必須有請求編號。")
        p = self.store.decode(db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone())
        if p["revision"] != revision:
            raise ValueError("計畫已修改，請重新預覽後確認。")
        if p["state"] == "cancelled":
            raise ValueError("計畫已取消，請建立新計畫。")
        if p["task_id"]:
            return p["task_id"], False
        if p["state"] != "ready" or p["expires_at"] <= stamp():
            raise ValueError("計畫已取消或過期，請建立新計畫。")
        self._validate(p["kind"], p["payload"])
        task_id, created = self._new_task(db, p["kind"], p["payload"], p["conversation_id"], request_id, plan_id)
        db.execute("UPDATE plans SET state='executing',task_id=? WHERE id=?", (task_id, plan_id))
        return task_id, created

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
            if hasattr(self,'_workflows'):self._workflows.cancel_task_tx(db,task_id)
            db.execute("UPDATE schedules SET enabled=0 WHERE id IN (SELECT schedule_id FROM tasks WHERE id=? AND kind='assistant_briefing' AND state='cancelled')",(task_id,))

    def _work(self, task_id):
        if hasattr(self,'_briefings') and self.store.task(task_id)['kind']=='assistant_briefing':
            return self._briefings.work(task_id)
        if hasattr(self,'_workflows') and self.store.task(task_id)['kind']=='workflow':
            return self._workflows.work(task_id)
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
                if t['kind']=='workflow':self._workflows.notify(db,t,state)
                elif t['kind']=='assistant_briefing':self._briefings.notify(db,t,state)
                else:self._notify_result(db, t, state, result)

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
        self._validate(t["kind"], t["payload"])
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
            if enabled:
                self._schedule_parameters(s, now or utcnow())
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
            if '_workflow' in s['parameters']:raise ValueError('協作流程日期屬於已批准計畫；請另建流程修改並試跑。')
            if '_assistant_briefing' in s['parameters']:raise ValueError('日報使用每次實際執行時間；修改需求請重新試跑。')
            if s["enabled"]:
                raise ValueError("請先停用排程再修改日期模式。")
            if mode == 'previous_day' and not self.schedule_date_mapping(s['query_id']):
                raise ValueError("此模板未宣告日期映射，只能使用固定參數排程。")
            parameters = s["parameters"]
            parameters["_date_mode"] = mode
            self._schedule_parameters(s, utcnow())
            db.execute("UPDATE schedules SET parameters=? WHERE id=?", (dumps(parameters), schedule_id))

    def schedule_date_mapping(self, query_id, legacy=False):
        if self.query_catalog is not None:
            return date_mapping(find_template(self.query_catalog(), query_id), legacy=legacy)
        return LEGACY_DATE_RANGES.get(query_id) if legacy else None

    def _schedule_parameters(self, schedule, occurrence):
        if '_assistant_briefing' in schedule['parameters']:
            if not hasattr(self,'_briefings'):raise ValueError('助理日報服務尚未初始化。')
            self._briefings.validate(schedule['parameters']['_assistant_briefing'])
            return copy.deepcopy(schedule['parameters'])
        if '_workflow' in schedule['parameters']:
            if not hasattr(self,'_workflows'):raise ValueError('協作服務尚未初始化。')
            self._workflows.schedule_spec(schedule,occurrence)
            return copy.deepcopy(schedule['parameters'])
        parameters = dict(schedule["parameters"])
        mode = parameters.pop("_date_mode", "literal")
        if mode == "previous_day":
            mapping = self.schedule_date_mapping(schedule['query_id'], legacy=True)
            if not mapping: raise ValueError("此模板未宣告日期映射，只能使用固定參數排程。")
            today = occurrence.astimezone(TAIPEI).date()
            parameters.update({mapping['start']:str(today-timedelta(days=1)), mapping['end']:str(today)})
        elif mode != 'literal': raise ValueError("排程日期模式無效。")
        self._validate('query', {'query_id':schedule['query_id'], 'parameters':parameters})
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
        if '_assistant_briefing' in schedule['parameters']:
            if not hasattr(self,'_briefings'):raise ValueError('助理日報服務尚未初始化。')
            return self._briefings.claim(db,schedule,key,occurrence)
        if '_workflow' in schedule['parameters']:
            if not hasattr(self,'_workflows'):raise ValueError('協作服務尚未初始化。')
            return self._workflows.claim(db,schedule,key,occurrence)
        old = db.execute("SELECT task_id FROM occurrences WHERE schedule_id=? AND scheduled_at=?", (schedule["id"], key)).fetchone()
        if old:
            return None
        overlap = db.execute("SELECT 1 FROM tasks WHERE schedule_id=? AND state IN ('queued','running')", (schedule["id"],)).fetchone()
        if overlap:
            db.execute("INSERT INTO occurrences VALUES(?,?,?,'skipped_overlap',NULL)", (uid(), schedule["id"], key))
            return None
        try:
            params = self._schedule_parameters(schedule, occurrence)
        except ValueError:
            db.execute("INSERT INTO occurrences VALUES(?,?,?,'failed',NULL)", (uid(), schedule['id'], key))
            db.execute("INSERT OR IGNORE INTO notifications VALUES(?,?,NULL,?,0,?)",
                       (uid(), 'invalid-schedule:'+schedule['id']+':'+key,
                        '排程「'+schedule['name']+'」模板或參數已失效，未執行查詢。請停用並重新設定。', stamp()))
            return None
        task_id, _ = self._new_task(db, "query", {"query_id": schedule["query_id"], "parameters": params},
                                  request_id="schedule:" + schedule["id"] + ":" + key, schedule_id=schedule["id"])
        db.execute("INSERT INTO occurrences VALUES(?,?,?,'queued',?)", (uid(), schedule["id"], key, task_id))
        return task_id

    def tick(self, now=None):
        if getattr(self,'authorization',None):self.authorization()
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
                    db.execute("UPDATE schedules SET enabled=0 WHERE id IN (SELECT schedule_id FROM tasks WHERE kind IN ('workflow','assistant_briefing') AND state IN ('queued','running'))")
                    db.execute("UPDATE tasks SET state='cancelled',finished_at=? WHERE state IN ('queued','running')", (stamp(),))
                    db.execute("UPDATE plans SET state='cancelled' WHERE state='executing'")
                    db.execute("UPDATE occurrences SET state='cancelled' WHERE state IN ('queued','running')")
                    if hasattr(self,'_workflows'):
                        db.execute("UPDATE workflow_steps SET state='cancelled',error='應用已關閉；未自動重送。' WHERE state IN ('queued','running')")
                        db.execute("UPDATE workflows SET state='draft',revision=revision+1,error='規劃已中斷，請重新送出。' WHERE state='planning'")
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
