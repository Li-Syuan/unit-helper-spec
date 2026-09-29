"""Interactive local-only approval / restart demonstration."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import json
import uuid
from offline_graph import make_graph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

root = Path(__file__).resolve().parent
directory = root / 'data'
directory.mkdir(exist_ok=True)
cursor = directory / 'current.json'
print('離線示範：使用真正 LangChain / LangGraph，所有助理與資料都是本機模擬。')
print('不讀 API key、不接公司、不啟用排程；與 QA agent 的資料分開。')
with SqliteSaver.from_conn_string(str(directory / 'checkpoints.sqlite3')) as saver:
    graph = make_graph(saver)
    if cursor.exists():
        thread_id = json.loads(cursor.read_text('utf-8'))['thread_id']
    else:
        thread_id = uuid.uuid4().hex
        cursor.write_text(json.dumps({'thread_id': thread_id}), encoding='utf-8')
    config = {'configurable': {'thread_id': thread_id}}
    state = graph.get_state(config)
    if not state.values:
        graph.invoke({'request': '整理三筆合成數據，分析後覆核並產出摘要。'}, config)
        state = graph.get_state(config)
    print(json.dumps(state.values, ensure_ascii=False, indent=2))
    if state.next:
        print('尚未查詢或分析。輸入 y 確認、n 拒絕、其他按鍵離開（保留進度）。')
        decision = input('> ').strip().lower()
        if decision in ('y', 'n'):
            result = graph.invoke(Command(resume=decision == 'y'), config)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print('示範結束。再開啟可查看結果，不會重新執行。')
        else:
            print('已保留待確認進度；再次開啟 demo.bat 可接續。')
    else:
        print('這次流程已結束，不會重跑。若要另開範例，輸入 new；其他按鍵離開。')
        if input('> ').strip().lower() == 'new':
            cursor.write_text(json.dumps({'thread_id': uuid.uuid4().hex}), encoding='utf-8')
            print('下次開啟將開始新範例。既有 checkpoint 保留。')
