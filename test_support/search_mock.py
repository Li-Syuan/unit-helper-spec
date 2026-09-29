"""Synthetic search transport: never accesses Internet or company data."""
import copy
import json
import httpx
from .assistants_mock import AssistantsMock

SEARCH_TOOL={'name':'internet_search','parameters':{'type':'object','properties':{'query':{'type':'string'}},'required':['query'],'additionalProperties':False}}


def call(id='call_search',name='internet_search',raw='{"query":"合成新聞"}'):
    return {'id':id,'type':'function','function':{'name':name,'arguments':raw}}


class SearchMock(AssistantsMock):
    def __init__(self):
        super().__init__('【合成搜尋】測試新聞來源 https://example.test/news；非即時資料。')
        self.assistant_tools=[{'type':'function','function':copy.deepcopy(SEARCH_TOOL)}]
        self.batches=[[call()]];self.plugin_requests=[];self.plugin_reply='synthetic source only'
        self.lose_plugin=False;self.lose_submit=False;self.after_plugin=None;self.force_tools=False

    def handle(self,request):
        if request.method=='POST' and request.url.path.endswith('/pluginapi'):
            body=json.loads(request.content)
            self.requests.append(('POST','/pluginapi',body));self.plugin_requests.append((str(request.url),body))
            if self.after_plugin:self.after_plugin()
            if self.lose_plugin:raise httpx.ReadTimeout('synthetic lost response',request=request)
            return httpx.Response(200,content=self.plugin_reply.encode('utf-8'))
        if request.method=='POST' and request.url.path.endswith('/submit_tool_outputs'):
            if self.lose_submit:
                self.requests.append(('POST',request.url.path,json.loads(request.content)))
                raise httpx.ReadTimeout('synthetic submit receipt lost',request=request)
        return super().handle(request)

    def dispatch(self,method,path,body=None,query=None):
        if method=='POST' and path.endswith('/submit_tool_outputs'):
            self.requests.append((method,path,body))
            rid=path.split('/')[-2];record=self.runs[rid]
            record['batch']=record.get('batch',0)+1
            self._advance(rid)
            return 200,copy.deepcopy(record['run'])
        result=super().dispatch(method,path,body,query)
        if method=='POST' and path.endswith('/runs'):
            record=self.runs[result[1]['id']];record['allow_search']=body.get('tool_choice')=='auto'
            self._advance(result[1]['id']);result=(200,copy.deepcopy(record['run']))
        return result

    def _advance(self,rid):
        record=self.runs[rid];run=record['run']
        if run['status']=='cancelled':return
        # Creation calls us before tool_choice has been captured.
        if 'allow_search' not in record:return
        batch=record.get('batch',0)
        if (record['allow_search'] or self.force_tools) and batch<len(self.batches):
            run['status']='requires_action'
            run['required_action']={'type':'submit_tool_outputs','submit_tool_outputs':{'tool_calls':copy.deepcopy(self.batches[batch])}}
        else:
            run['status']='completed';run['required_action']=None
            if not record['replied']:
                self.threads[run['thread_id']].append(self.message(run['thread_id'],'assistant',self.reply,rid))
                record['replied']=True
