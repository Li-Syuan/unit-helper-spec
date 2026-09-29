"""Real LangGraph orchestration with SYNTHETIC roles, no model or company calls."""
import os

# Keep the demonstration offline even on a developer machine with tracing configured.
# These assignments affect only this process; no user configuration is changed.
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGSMITH_TRACING'] = 'false'
os.environ['LANGCHAIN_TRACING'] = 'false'

from decimal import Decimal
from typing import TypedDict
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt


class State(TypedDict, total=False):
    request: str
    steps: list[str]
    approved: bool
    values: list[str]
    total: str
    verdict: str
    text: str


def plan(state):
    # User text is merely displayed, never interpreted as code or a file path.
    if not isinstance(state.get('request'), str) or not 1 <= len(state['request']) <= 1000:
        raise ValueError('Request must be 1..1000 characters')
    return {'steps': ['synthetic query', 'analysis', 'review', 'compose']}


def approve(state):
    choice = interrupt({'demo': True, 'request': state['request'], 'steps': state['steps']})
    if type(choice) is not bool:
        raise ValueError('Approval must be explicit True or False')
    return {'approved': choice}


def query(state):
    if state.get('approved') is not True:
        raise ValueError('Not approved')
    return {'values': ['1.10', '2.20', '3.30']}


def analyze(state):
    return {'total': str(sum((Decimal(x) for x in state['values']), Decimal('0')))}


def review(state):
    expected = str(sum((Decimal(x) for x in state['values']), Decimal('0')))
    return {'verdict': 'pass' if state['total'] == expected else 'needs_attention'}


def compose(state):
    return {'text': f"DEMO ONLY: {len(state['values'])} synthetic rows; exact total {state['total']}. No live data or AI analysis."}


def make_graph(checkpointer):
    graph = StateGraph(State)
    for name, function in [('plan', plan), ('approve', approve), ('query', query),
                           ('analyze', analyze), ('review', review), ('compose', compose)]:
        graph.add_node(name, RunnableLambda(function))
    graph.add_edge(START, 'plan')
    graph.add_edge('plan', 'approve')
    graph.add_conditional_edges('approve', lambda state: 'query' if state['approved'] else END)
    graph.add_edge('query', 'analyze')
    graph.add_edge('analyze', 'review')
    graph.add_conditional_edges('review', lambda state: 'compose' if state['verdict'] == 'pass' else END)
    graph.add_edge('compose', END)
    return graph.compile(checkpointer=checkpointer)
