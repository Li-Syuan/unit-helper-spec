"""Independent offline conversation store; never read by the execution scheduler."""
from contextlib import contextmanager
import sqlite3
from pathlib import Path


class DialogueStore:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0,1):raise ValueError('對話資料版本不相容。')
            db.executescript('''BEGIN IMMEDIATE;
            CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY, mode TEXT NOT NULL,assistant_id TEXT NOT NULL,answers TEXT NOT NULL,revision INTEGER NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,thread_id TEXT NOT NULL REFERENCES threads(id),role TEXT NOT NULL,text TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS turns(request_id TEXT PRIMARY KEY,thread_id TEXT NOT NULL,text TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS task_drafts(id TEXT PRIMARY KEY,thread_id TEXT NOT NULL REFERENCES threads(id),revision INTEGER NOT NULL,assistant_id TEXT NOT NULL,body TEXT NOT NULL,enabled INTEGER NOT NULL CHECK(enabled=0),created_at TEXT NOT NULL,UNIQUE(thread_id,revision));
            PRAGMA user_version=1;COMMIT;''')
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:yield db
        finally:db.close()
