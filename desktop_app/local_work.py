"""Personal todos and revision-fenced local drafts; never dispatch provider work."""
from datetime import date, datetime, timezone
import hashlib
import json
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


def initialize_work_schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS todos(
        id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('todo','ongoing','done')), due_date TEXT,
        source_conversation_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        completed_at TEXT, request_id TEXT UNIQUE, request_hash TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS drafts(
        conversation_id TEXT PRIMARY KEY REFERENCES conversations(id), revision INTEGER NOT NULL,
        text TEXT NOT NULL, purpose TEXT NOT NULL, planned INTEGER NOT NULL,
        had_attachment INTEGER NOT NULL, updated_at TEXT NOT NULL)''')


def validate_todo(title, description, due_date, state):
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise ValueError('待辦標題請填寫 1 至 120 字。')
    if not isinstance(description, str) or len(description) > 50000:
        raise ValueError('待辦說明最多 50,000 字；未截斷內容。')
    if state not in ('todo', 'ongoing', 'done'):
        raise ValueError('不支援的待辦狀態。')
    due_date = due_date or None
    if due_date is not None:
        try:
            if not isinstance(due_date, str) or date.fromisoformat(due_date).isoformat() != due_date:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError('到期日請使用有效的 YYYY-MM-DD，或留空。') from None
    return title.strip(), description, due_date, state


class LocalWorkStore:
    def create_todo(self, title, description='', due_date=None, source_conversation_id=None, request_id=None):
        title, description, due_date, state = validate_todo(title, description, due_date, 'todo')
        if request_id is not None and (not isinstance(request_id, str) or not request_id):
            raise ValueError('待辦保存識別不正確。')
        digest = hashlib.sha256(json.dumps([title, description, due_date, source_conversation_id],
                                           ensure_ascii=False).encode()).hexdigest()
        tid, created = uuid.uuid4().hex, now()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if request_id:
                existing = db.execute('SELECT * FROM todos WHERE request_id=?', (request_id,)).fetchone()
                if existing:
                    if existing['request_hash'] != digest:
                        raise ValueError('待辦內容已變更，請重新開啟新增視窗。')
                    return dict(existing)
            if source_conversation_id is not None and not db.execute(
                    'SELECT 1 FROM conversations WHERE id=?', (source_conversation_id,)).fetchone():
                raise ValueError('來源對話已刪除，請取消並重新新增待辦。')
            db.execute('INSERT INTO todos VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (tid, title, description, state, due_date, source_conversation_id,
                        created, created, None, request_id, digest))
        return self.todo(tid)

    def todo(self, tid):
        with self.connection() as db:
            row = db.execute('SELECT * FROM todos WHERE id=?', (tid,)).fetchone()
        if row is None:
            raise ValueError('這筆待辦已不存在。')
        return dict(row)

    def todos(self, search=''):
        with self.connection() as db:
            rows = db.execute('SELECT * FROM todos ORDER BY updated_at DESC,id').fetchall()
        term = search.strip().casefold()
        return [dict(r) for r in rows if term in r['title'].casefold()]

    def update_todo(self, tid, title, description, due_date, state):
        title, description, due_date, state = validate_todo(title, description, due_date, state)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM todos WHERE id=?', (tid,)).fetchone()
            if row is None:
                raise ValueError('這筆待辦已不存在。')
            updated = now()
            completed = (row['completed_at'] or updated) if state == 'done' else None
            db.execute('UPDATE todos SET title=?,description=?,due_date=?,state=?,updated_at=?,completed_at=? WHERE id=?',
                       (title, description, due_date, state, updated, completed, tid))
        return self.todo(tid)

    def set_todo_state(self, tid, state):
        # One write transaction: changing state never overwrites newer edited text.
        if state not in ('todo', 'ongoing', 'done'):
            raise ValueError('不支援的待辦狀態。')
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM todos WHERE id=?', (tid,)).fetchone()
            if row is None:
                raise ValueError('這筆待辦已不存在。')
            updated = now()
            completed = (row['completed_at'] or updated) if state == 'done' else None
            db.execute('UPDATE todos SET state=?,updated_at=?,completed_at=? WHERE id=?',
                       (state, updated, completed, tid))
        return self.todo(tid)

    def delete_todo(self, tid):
        with self.connection() as db:
            if not db.execute('DELETE FROM todos WHERE id=?', (tid,)).rowcount:
                raise ValueError('這筆待辦已不存在。')

    def draft(self, cid):
        with self.connection() as db:
            row = db.execute('SELECT * FROM drafts WHERE conversation_id=?', (cid,)).fetchone()
        return dict(row) if row else None

    def reserve_draft(self, cid):
        # Reservation is memory-only. Single Store + directory singleton owns writers.
        with self._draft_lock:
            revision = self._draft_revisions.get(cid, 0) + 1
            self._draft_revisions[cid] = revision
            return revision

    def save_draft(self, cid, revision, text, purpose, planned, had_attachment=False):
        if not isinstance(text, str) or len(text) > 50000:
            raise ValueError('草稿最多 50,000 字；畫面內容仍保留。')
        if purpose not in ('一般對話', '整理重點', '改寫文字') or type(planned) is not bool or type(had_attachment) is not bool:
            raise ValueError('草稿設定不正確。')
        with self._draft_lock:
            if self._draft_revisions.get(cid) != revision:
                return False
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                if not db.execute('SELECT 1 FROM conversations WHERE id=?', (cid,)).fetchone():
                    return False
                if not text and not had_attachment:
                    db.execute('DELETE FROM drafts WHERE conversation_id=?', (cid,))
                else:
                    db.execute('''INSERT INTO drafts VALUES(?,?,?,?,?,?,?)
                        ON CONFLICT(conversation_id) DO UPDATE SET revision=excluded.revision,
                        text=excluded.text,purpose=excluded.purpose,planned=excluded.planned,
                        had_attachment=excluded.had_attachment,updated_at=excluded.updated_at''',
                        (cid, revision, text, purpose, int(planned), int(had_attachment), now()))
            return True

    def clear_draft(self, cid):
        with self._draft_lock:
            self.reserve_draft(cid)
            with self.connection() as db:
                db.execute('DELETE FROM drafts WHERE conversation_id=?', (cid,))
