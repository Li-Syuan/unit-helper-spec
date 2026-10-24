"""Sequential LangGraph executor. Store step receipts remain authoritative.

Checkpoints contain identifiers only, never credentials or a second task status.
No retry policy or cloud tracing is enabled.
"""
import os
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import TypedDict

for _name in ('LANGCHAIN_TRACING', 'LANGCHAIN_TRACING_V2', 'LANGSMITH_TRACING'):
    os.environ[_name] = 'false'

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver


class Cursor(TypedDict, total=False):
    task_id: str
    version: int
    completed_step: str
    fingerprint: str
    round: int
    done: bool
    last_receipt: str


def execute_autonomous(path, task_id, spec, runner):
    """Same persisted runner, with validated decision/action conditional edges."""
    runner.validate_receipts()
    graph = StateGraph(Cursor)
    fingerprint=hashlib.sha256(json.dumps(spec,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    def decide(state):
        return {'last_receipt':runner.decide(state['round'])}
    def act(state):
        done=runner.act(state['round'])
        return {'round':state['round']+1,'done':done,'last_receipt':f"qa_action_{state['round']+1}"}
    graph.add_node('decide',decide);graph.add_node('act',act)
    graph.add_edge(START,'decide');graph.add_edge('decide','act')
    graph.add_conditional_edges('act',lambda s:'end' if s['done'] else 'next',{'end':END,'next':'decide'})
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(str(path),check_same_thread=False,timeout=30)) as connection:
        compiled=graph.compile(checkpointer=SqliteSaver(connection))
        config={'configurable':{'thread_id':task_id},'recursion_limit':20}
        snapshot=compiled.get_state(config)
        if snapshot.values:
            state=snapshot.values
            if state.get('version')!=2 or state.get('task_id')!=task_id or state.get('fingerprint')!=fingerprint:
                raise ValueError('自主工作 checkpoint 定義不一致；未重新執行。')
            rows=runner.rows();last=state.get('last_receipt')
            receipt=next((r for r in rows if r['step_id']==last),None)
            if last and (not receipt or any(r['state']!='succeeded' or not r['output'] for r in rows if r['position']<=receipt['position'])):
                raise ValueError('自主 checkpoint 與成果收據不一致，請核對備份。')
        return compiled.invoke(None if snapshot.values else {'task_id':task_id,'version':2,'fingerprint':fingerprint,'round':0,'done':False},config)


def execute(path, task_id, steps, dispatch, receipts=None):
    """Only called after the existing service approval transaction has committed."""
    graph = StateGraph(Cursor)
    fingerprint=hashlib.sha256(json.dumps(steps,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    previous = START
    for index, step in enumerate(steps):
        name = 'step_' + str(index)
        def node(state, selected=step):
            if state.get('version') != 1 or state.get('task_id') != task_id:
                raise ValueError('流程 checkpoint 版本或工作識別不符。')
            dispatch(selected)
            return {'completed_step': selected['id']}
        graph.add_node(name, node)
        graph.add_edge(previous, name)
        previous = name
    graph.add_edge(previous, END)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(str(path), check_same_thread=False, timeout=30)) as connection:
        saver = SqliteSaver(connection)
        compiled = graph.compile(checkpointer=saver)
        config = {'configurable': {'thread_id': task_id}, 'recursion_limit': 20}
        snapshot = compiled.get_state(config)
        if snapshot.values and snapshot.values.get('version') != 1:
            raise ValueError('不支援此 checkpoint 版本。')
        if snapshot.values:
            if snapshot.values.get('fingerprint')!=fingerprint:
                raise ValueError('checkpoint 的流程定義不一致；未重新執行。')
            completed=snapshot.values.get('completed_step')
            ids=[s['id'] for s in steps]
            if completed is not None and completed not in ids:
                raise ValueError('checkpoint 步驟不存在。')
            if receipts is not None and completed is not None:
                if any(sid not in receipts for sid in ids[:ids.index(completed)+1]):
                    raise ValueError('checkpoint 與工作成果不一致；停止恢復，請核對備份。')
        # Reconciliation belongs to the caller. Resuming a node may run it again;
        # dispatch must consult its committed receipt before sending anything.
        return compiled.invoke(None if snapshot.values else {'task_id': task_id, 'version': 1,'fingerprint':fingerprint}, config)


def remove(path, task_id):
    if not Path(path).exists():
        return
    with closing(sqlite3.connect(str(path), check_same_thread=False)) as connection:
        SqliteSaver(connection).delete_thread(task_id)
