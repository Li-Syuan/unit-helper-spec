"""Read-only personal work inbox; no dispatch, authorization or duplicate state."""
from datetime import datetime, timezone
from .assistant_errors import decode_failure


def work_inbox(session):
    rows = []
    with session.store.connection() as db:
        sources = {r['id']: r['title'] for r in db.execute('SELECT id,title FROM conversations')}
        for table, title in (('plans', 'kind'), ('workflows', 'goal'), ('conversation_actions', 'request')):
            for item in db.execute(f"SELECT * FROM {table} WHERE state IN ('draft','ready','pending','planning') ORDER BY created_at DESC"):
                item = dict(item)
                if item.get('task_id') or item.get('schedule_id'):
                    continue
                cid = item.get('conversation_id')
                if cid not in sources:
                    continue
                state = item['state']
                expired = table == 'plans' and item.get('expires_at', '') < datetime.now(timezone.utc).isoformat()
                rows.append(dict(id=item['id'], kind=table, title=item[title], state=state,
                                 conversation_id=cid, source=sources[cid],
                                 note='計畫已逾期，請回來源重新預覽。' if expired else '尚未執行；回來源補齊條件或檢視確認。',
                                 created_at=item['created_at']))
        for item in db.execute("SELECT id,kind,state,error,conversation_id,created_at FROM tasks WHERE state IN ('queued','running','failed','cancelled') ORDER BY created_at DESC LIMIT 50"):
            item = dict(item)
            cid = item['conversation_id']
            rows.append(dict(id=item['id'], kind='task', title={'query':'資料查詢','workflow':'多助理協作','assistant_briefing':'助理日報'}.get(item['kind'], '助理工作'),
                             state=item['state'], conversation_id=cid if cid in sources else None,
                             source=sources.get(cid, '獨立工作／來源已刪除'),
                             note=item['error'] or ('等待工作結束，可查看目前結果。' if item['state'] in ('queued','running') else '查看已取得成果；需要重試時回原流程確認。'),
                             created_at=item['created_at']))
    # Main chat uses its own store; show only each thread's newest unresolved request.
    with session.dialogue.lock, session.dialogue.store.connect() as db:
        for item in db.execute("SELECT r.thread_id,r.status,r.error_code,r.created_at,substr(r.text,1,120) AS title FROM requests r WHERE r.rowid=(SELECT MAX(last.rowid) FROM requests last WHERE last.thread_id=r.thread_id) AND r.status IN ('pending','failed','cancelled') ORDER BY r.created_at DESC LIMIT 50"):
            item = dict(item)
            failure = decode_failure(item['error_code'])
            note = str(failure) if failure else '回原對話檢查原請求；不自動重送。'
            rows.append(dict(id=item['thread_id'], kind='dialogue', title=item['title'] or '主對話',
                             state={'pending':'running'}.get(item['status'], item['status']),
                             source='主對話', note=note,
                             created_at=item['created_at']))
    rank = {'failed':0,'ready':1,'pending':1,'draft':2,'planning':3,'running':3,'queued':3,'cancelled':4}
    rows.sort(key=lambda row: (rank.get(row['state'], 5), row['created_at']), reverse=False)
    return rows
