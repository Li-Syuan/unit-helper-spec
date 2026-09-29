"""Private local ledger for Assistants sessions, never credentials or endpoints.

Records are written *before* remote mutations. An interrupted mutation without a
known remote ID is deliberately not retried: the remote outcome is unknown.
"""
import contextlib
import json
import sqlite3
import threading
from pathlib import Path
from .gateways import GatewayError

_LOCKS = {}
_SESSION_LOCKS = {}
_GUARD = threading.Lock()


class AssistantSessions:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _GUARD:
            self.lock = _LOCKS.setdefault(str(self.path.resolve()), threading.RLock())
        with self.lock, self.connect() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise GatewayError('公司連線紀錄版本不相容；未啟動遠端工作。')
            db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS requests (session_id TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(session_id,id))')
            db.execute('PRAGMA user_version=1')

    @contextlib.contextmanager
    def connect(self):
        db=sqlite3.connect(self.path, timeout=5)
        try:
            with db:yield db
        finally:db.close()

    @contextlib.contextmanager
    def session(self, key):
        # Shared across all adapter instances using this ledger. Never hold a
        # SQLite transaction across HTTP. Concurrent requests refuse, not queue.
        with _GUARD:
            lock = _SESSION_LOCKS.setdefault((str(self.path.resolve()), key), threading.Lock())
        if not lock.acquire(blocking=False):
            raise GatewayError('公司助理仍有請求處理中，請稍候再試。')
        try:
            yield
        finally:
            lock.release()

    def get_session(self, key):
        with self.connect() as db:
            row = db.execute('SELECT data FROM sessions WHERE id=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def get_request(self, key, request_id):
        with self.connect() as db:
            row = db.execute('SELECT data FROM requests WHERE session_id=? AND id=?', (key, request_id)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, key, session, request_id=None, request=None):
        with self.connect() as db:
            db.execute('INSERT INTO sessions VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                       (key, json.dumps(session, ensure_ascii=False)))
            if request_id is not None:
                db.execute('INSERT INTO requests VALUES (?,?,?) ON CONFLICT(session_id,id) DO UPDATE SET data=excluded.data',
                           (key, request_id, json.dumps(request, ensure_ascii=False)))
