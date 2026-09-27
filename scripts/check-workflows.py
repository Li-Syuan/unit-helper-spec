"""Explicit synthetic Groq collaboration check; never loads company/user workspace data."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from desktop_app.core import Store,Engine
from desktop_app.gateways import DemoQueries
from desktop_app.trial import TrialProfiles
from desktop_app.workflows import WorkflowService


def wait(engine,predicate,seconds=180):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate() and not engine.has_inflight():return
        time.sleep(.05)
    raise ValueError('本次流程逾時。')


def check():
    result={'data':'synthetic_only','company_services':'not_tested','external_service':'not_tested','requests':0}
    with tempfile.TemporaryDirectory(prefix='qa-workflow-check-') as tmp:
        store=Store(Path(tmp)/'check.db');queries=DemoQueries();profiles=TrialProfiles()
        raw=profiles.workflow_call
        def call(*args,**kwargs):
            if result['requests']>=4:raise ValueError('已達四次合成請求上限，未繼續呼叫。')
            result['requests']+=1
            return raw(*args,**kwargs)
        profiles.workflow_call=call
        engine=Engine(store,queries.run,None,query_validator=queries.validate,query_catalog=queries.catalog)
        try:
            service=WorkflowService(engine,profiles);cid=store.create_conversation('合成流程驗證',profiles.default_binding())
            goal='查昨天 A 類數量合計，請分析助理整理，交覆核助理檢查，再由日報助理產生日報。先試跑，成功後我自己設定每天早上八點。不需要趨勢或原因推測。'
            r=service.create(cid,goal,profiles.workflow_binding('groq-planner'))
            service.discuss(r['id'],r['revision'],goal)
            wait(engine,lambda:service.get(r['id'])['state']!='planning')
            r=service.get(r['id'])
            if r['state']!='ready':raise ValueError('主代理未產生可執行計畫；外部協作尚未通過。')
            kinds=[s.get('role',s['kind']) for s in r['steps']]
            if kinds!=['query','analysis','review','compose']:raise ValueError('主代理分工未符合本次驗收需求；未批准。')
            if store.tasks() or store.schedules():raise ValueError('批准前已派發工作。')
            result['planning']='external_real_passed'
            if not service.preview(r['id'],r['revision'])['ready']:raise ValueError('計畫未通過本機驗證。')
            tid=service.confirm(r['id'],r['revision'],True)
            wait(engine,lambda:store.task(tid)['state'] not in {'queued','running'})
            task=store.task(tid)
            result['steps']=[{'step':s['step_id'],'state':s['state']} for s in service.get_task_steps(tid)]
            if task['state']!='succeeded':raise ValueError('真實子代理流程未全部完成；沒有使用合成回覆替代。')
            sid=service.schedule(r['id'],r['revision'],'合成自動日報','daily','08:00',consent=True)
            engine.set_schedule_enabled(sid,False)
            result.update(external_service='external_real_passed',schedule_creation='local_real_passed',user_data_changed=False)
        except Exception:
            result['external_service']='failed';result['error_code']='WORKFLOW_LIVE_NOT_COMPLETED'
        finally:engine.close(wait=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if sys.version_info[:3]!=(3,10,4):raise SystemExit('Use project Python 3.10.4')
    result=check() if args.live else {'external_service':'not_tested','company_services':'not_tested','requests':0}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text+'\n',encoding='utf-8',newline='\n')
    print(text)
    return 1 if result['external_service']=='failed' else 0


if __name__=='__main__':raise SystemExit(main())
