"""Synthetic company Assistants protocol fixture; no credentials or real data."""
import json
import threading
from urllib.parse import parse_qs
import httpx


class AssistantsMock:
    def __init__(self, reply='【協定模擬】這是合成文字，未查詢公司資料。', statuses=None):
        self.reply = reply
        self.statuses = list(statuses or ['completed'])
        self.requests = []
        self.threads = {}
        self.runs = {}
        self.lock = threading.RLock()
        self.fail_status = None
        self.paginate = False

    def handle(self, request):
        body = json.loads(request.content) if request.content else {}
        query = parse_qs(request.url.query.decode('ascii'))
        status, value = self.dispatch(request.method, request.url.path, body, query)
        return httpx.Response(status, json=value)

    def dispatch(self, method, path, body=None, query=None):
        body, query = body or {}, query or {}
        path = path.removeprefix('/v1').rstrip('/')
        with self.lock:
            self.requests.append((method, path, body))
            if self.fail_status:
                return self.fail_status, {'error': {'message': 'synthetic rejected', 'type': 'synthetic'}}
            parts = path.strip('/').split('/')
            if path == '/health' and method == 'GET':
                return 200, {'mode': 'synthetic', 'company_verified': False}
            if path == '/threads' and method == 'POST':
                tid = 'thread_mock_' + str(len(self.threads) + 1)
                self.threads[tid] = []
                return 200, {'id': tid, 'object': 'thread', 'created_at': 0, 'metadata': {}}
            if len(parts) < 3 or parts[0] != 'threads' or parts[1] not in self.threads:
                return 404, {'error': {'message': 'synthetic unknown thread'}}
            tid = parts[1]
            if parts[2] == 'messages':
                if method == 'POST':
                    item = self.message(tid, body['role'], body['content'])
                    self.threads[tid].append(item)
                    return 200, item
                data = self.threads[tid]
                after = query.get('after', [None])[0]
                if after:
                    data = data[next((i + 1 for i, item in enumerate(data) if item['id'] == after), len(data)):]
                count = 1 if self.paginate else len(data)
                page = data[:count]
                return 200, {'object': 'list', 'data': page, 'has_more': len(data) > count,
                             'first_id': page[0]['id'] if page else None, 'last_id': page[-1]['id'] if page else None}
            if parts[2] == 'runs':
                if len(parts) == 3 and method == 'POST':
                    rid = 'run_mock_' + str(len(self.runs) + 1)
                    run = {'id': rid, 'object': 'thread.run', 'thread_id': tid, 'assistant_id': body['assistant_id'],
                           'created_at': 0, 'status': self.statuses[0], 'model': 'synthetic', 'instructions': '',
                           'tools': [], 'metadata': {}, 'required_action': None}
                    self.runs[rid] = {'run': run, 'poll': 0, 'replied': False}
                    self._advance(rid)
                    return 200, dict(run)
                if len(parts) >= 4 and parts[3] in self.runs:
                    rid = parts[3]
                    record = self.runs[rid]
                    if len(parts) == 5 and parts[4] == 'cancel' and method == 'POST':
                        record['run']['status'] = 'cancelled'
                        return 200, dict(record['run'])
                    if method == 'GET':
                        record['poll'] += 1
                        self._advance(rid)
                        return 200, dict(record['run'])
            return 400, {'error': {'message': 'unsupported synthetic operation'}}

    def message(self, tid, role, text, run_id=None):
        return {'id': 'msg_' + str(len(self.threads[tid]) + 1), 'object': 'thread.message', 'created_at': 0,
                'thread_id': tid, 'role': role, 'run_id': run_id,
                'content': [{'type': 'text', 'text': {'value': text, 'annotations': []}}]}

    def _advance(self, rid):
        record = self.runs[rid]
        run = record['run']
        if run['status'] == 'cancelled':
            return
        run['status'] = self.statuses[min(record['poll'], len(self.statuses) - 1)]
        if run['status'] == 'requires_action':
            run['required_action'] = {'type': 'submit_tool_outputs', 'submit_tool_outputs': {'tool_calls': [
                {'id': 'call_synthetic', 'type': 'function', 'function': {'name': 'unapproved_tool', 'arguments': '{}'}}]}}
        if run['status'] == 'completed' and not record['replied']:
            tid = run['thread_id']
            self.threads[tid].append(self.message(tid, 'assistant', self.reply, rid))
            record['replied'] = True
