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
            if version not in (0,1,2,3,4):raise ValueError('對話資料版本不相容。')
            if version==4:return
            if version:
                backup=self.path.with_name(self.path.name+'.pre-v4-'+uuid.uuid4().hex+'.bak')
                with sqlite3.connect(backup) as destination:db.backup(destination)
            db.execute('BEGIN IMMEDIATE')
            if version<2:self._upgrade(db)
            if version<3:self._continuity_upgrade(db)
            self._folders_upgrade(db)

    @staticmethod
    def _folders_upgrade(db):
        db.execute('CREATE TABLE dialogue_folders(id TEXT PRIMARY KEY,name TEXT NOT NULL COLLATE NOCASE UNIQUE,collapsed INTEGER NOT NULL DEFAULT 0,revision INTEGER NOT NULL DEFAULT 1)')
        db.execute('ALTER TABLE thread_views ADD COLUMN folder_id TEXT REFERENCES dialogue_folders(id) ON DELETE SET NULL')
        db.execute('CREATE INDEX thread_views_folder ON thread_views(folder_id)')
        db.execute('PRAGMA user_version=4')

    @staticmethod
    def _continuity_upgrade(db):
        db.execute("CREATE TABLE thread_views(thread_id TEXT PRIMARY KEY REFERENCES threads(id) ON DELETE CASCADE,title TEXT NOT NULL DEFAULT '',pinned INTEGER NOT NULL DEFAULT 0,draft TEXT NOT NULL DEFAULT '',scroll REAL NOT NULL DEFAULT 0,revision INTEGER NOT NULL DEFAULT 0,memories TEXT NOT NULL DEFAULT '[]',source_thread_id TEXT,updated_at TEXT NOT NULL)")
        db.execute("CREATE TABLE memories(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,assistant_id TEXT NOT NULL,title TEXT NOT NULL,text TEXT NOT NULL,category TEXT NOT NULL,enabled INTEGER NOT NULL,source_thread_id TEXT,updated_at TEXT NOT NULL)")
        db.execute("CREATE TABLE continuation_requests(thread_id TEXT PRIMARY KEY REFERENCES threads(id) ON DELETE CASCADE,request_id TEXT NOT NULL,state TEXT NOT NULL)")
        db.execute('CREATE TABLE activation_checks(profile_id TEXT PRIMARY KEY,revision INTEGER NOT NULL,passed INTEGER NOT NULL,checked_at TEXT NOT NULL)')
        db.execute('PRAGMA user_version=3')

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
