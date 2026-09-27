"""Persistent typed questions, independent of provider-generated UI."""
from __future__ import annotations
from contextlib import contextmanager
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

class ChoiceForms:
    def __init__(self, path):
        self.path = str(path)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS local_forms(id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL, expires TEXT NOT NULL, body TEXT NOT NULL, state TEXT NOT NULL, request_id TEXT, answers TEXT)")
    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()
    def create(self, questions, owner="local-demo", now=None):
        if not 1 <= len(questions) <= 3:
            raise ValueError("每次需 1 至 3 題。")
        ids = set()
        for q in questions:
            if q["id"] in ids: raise ValueError("題目 ID 重複。")
            ids.add(q["id"])
            if q["type"] not in ("yes_no", "single_choice", "multi_choice"): raise ValueError("題型不支援。")
            options = q["options"]
            option_ids = [o["id"] for o in options]
            if not 2 <= len(options) <= 6 or len(set(option_ids)) != len(options): raise ValueError("選項不合法。")
            if q["type"] == "yes_no" and set(option_ids) != {"yes", "no"}: raise ValueError("是非選項須為 yes/no。")
            if not 0 <= q.get("min", 1) <= q.get("max", 1) <= len(options): raise ValueError("選取數不合法。")
        fid = str(uuid.uuid4())
        expiry = ((now or datetime.now(timezone.utc)) + timedelta(hours=24)).isoformat()
        with self._connect() as db:
            db.execute("INSERT INTO local_forms VALUES(?,?,1,?,?,'open',NULL,NULL)", (fid,owner,expiry,json.dumps(questions,ensure_ascii=False)))
        return self.get(fid, owner)
    def get(self, fid, owner="local-demo"):
        with self._connect() as db:
            row = db.execute("SELECT * FROM local_forms WHERE id=? AND owner=?",(fid,owner)).fetchone()
        if not row: raise ValueError("找不到或無權讀取題目。")
        obj = dict(row); obj["questions"] = json.loads(obj.pop("body"))
        return obj
    def submit(self, fid, version, answers, request_id, owner="local-demo", now=None):
        if not request_id: raise ValueError("缺少 request ID。")
        body = json.dumps(answers, ensure_ascii=False, sort_keys=True)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM local_forms WHERE id=? AND owner=?",(fid,owner)).fetchone()
            if not row: raise ValueError("找不到或無權提交題目。")
            if row["version"] != version: raise ValueError("題目修訂已失效。")
            if row["state"] == "submitted" and row["request_id"] == request_id and row["answers"] == body: return answers
            if row["version"] != version or row["state"] != "open": raise ValueError("題目已失效，請重新開啟。")
            if datetime.fromisoformat(row["expires"]) <= (now or datetime.now(timezone.utc)): raise ValueError("題目已過期。")
            questions = json.loads(row["body"])
            if set(answers) != {q["id"] for q in questions}: raise ValueError("請回答所有題目。")
            for q in questions:
                selected = answers[q["id"]]
                if not isinstance(selected,list) or len(set(selected)) != len(selected): raise ValueError("選項重複或格式不符。")
                allowed = {o["id"] for o in q["options"]}
                if set(selected) - allowed: raise ValueError("包含未知選項。")
                minimum, maximum = q.get("min",1), q.get("max",1)
                if q["type"] != "multi_choice": minimum,maximum=1,1
                if not minimum <= len(selected) <= maximum: raise ValueError("請依題目指定數量選取。")
            db.execute("UPDATE local_forms SET state='submitted',request_id=?,answers=? WHERE id=?", (request_id,body,fid))
        return answers
    def open_forms(self, owner="local-demo"):
        with self._connect() as db:
            rows=db.execute("SELECT id FROM local_forms WHERE owner=? AND state='open' AND expires>?",(owner,datetime.now(timezone.utc).isoformat())).fetchall()
        return [self.get(row["id"],owner) for row in rows]

    def cancel(self, fid, version, owner="local-demo"):
        with self._connect() as db:
            cursor=db.execute("UPDATE local_forms SET state='cancelled' WHERE id=? AND owner=? AND version=? AND state='open'",(fid,owner,version))
            if not cursor.rowcount: raise ValueError("題目已失效或無權取消。")
