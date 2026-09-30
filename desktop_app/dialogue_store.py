"""Independent offline conversation store; never read by the execution scheduler."""
from contextlib import contextmanager
import sqlite3
from pathlib import Path
import uuid


class DialogueStore:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0,1,2):raise ValueError('對話資料版本不相容。')
            if version==2:return
            if version==1:
                backup=self.path.with_name(self.path.name+'.pre-v2-'+uuid.uuid4().hex+'.bak')
                with sqlite3.connect(backup) as destination:db.backup(destination)
            db.execute('BEGIN IMMEDIATE')
            self._upgrade(db)

    @staticmethod
    def _upgrade(db):
        for statement in (
            'CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY, mode TEXT NOT NULL,assistant_id TEXT NOT NULL,answers TEXT NOT NULL,revision INTEGER NOT NULL,created_at TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,thread_id TEXT NOT NULL REFERENCES threads(id),role TEXT NOT NULL,text TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS turns(request_id TEXT PRIMARY KEY,thread_id TEXT NOT NULL,text TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS task_drafts(id TEXT PRIMARY KEY,thread_id TEXT NOT NULL REFERENCES threads(id),revision INTEGER NOT NULL,assistant_id TEXT NOT NULL,body TEXT NOT NULL,enabled INTEGER NOT NULL CHECK(enabled=0),created_at TEXT NOT NULL,UNIQUE(thread_id,revision))',
            "CREATE TABLE requests(request_id TEXT PRIMARY KEY,thread_id TEXT NOT NULL REFERENCES threads(id),text TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('pending','failed','cancelled','completed')),revision INTEGER NOT NULL,answers TEXT NOT NULL,history TEXT NOT NULL,remote_state TEXT NOT NULL DEFAULT 'unchecked',recoverable INTEGER NOT NULL DEFAULT 0,error_code TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)",
            'PRAGMA user_version=2',
        ):db.execute(statement)
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:yield db
        finally:db.close()
