"""Local key check; --live sends one synthetic request, --live --reports up to three."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from desktop_app.trial import GroqAssistant, read_key
from desktop_app.gateways import GatewayError


def check_reports():
    """Temporary synthetic data only; never change the user's schedules."""
    import tempfile
    import time
    from desktop_app.intent_drafts import extract_action
    from desktop_app.conversation_actions import ActionService
    from desktop_app.report_engine import ReportEngine
    from desktop_app.core import Store
    from desktop_app.gateways import DemoQueries
    from desktop_app.trial import TrialProfiles
    parsed=extract_action('每天早上八點查昨天 A 類數量合計，整理日報。','report')
    if parsed['parameters'].get('category')!='A' or any(parsed[k]!=v for k,v in {'query_id':'DEMO03','time_hhmm':'08:00','date_mode':'previous_day','frequency':'daily'}.items()):
        raise GatewayError('完整需求解析未符合預期；沒有啟用使用者排程。')
    missing=extract_action('每天幫我查資料做報告。','report')
    if missing['query_id'] is not None or missing['time_hhmm'] is not None or not missing['questions']:
        raise GatewayError('缺少條件時未正確追問；沒有啟用使用者排程。')
    with tempfile.TemporaryDirectory(prefix='qa-report-check-') as tmp:
        store=Store(Path(tmp)/'test.sqlite3');queries=DemoQueries();profiles=TrialProfiles()
        engine=ReportEngine(store,queries.run,None,query_validator=queries.validate,query_catalog=queries.catalog,
                            assistant_router=profiles.respond,binding_validator=profiles.validate)
        try:
            actions=ActionService(engine);cid=store.create_conversation('合成驗證',profiles.default_binding())
            spec={k:parsed[k] for k in ('query_id','parameters','time_hhmm','frequency','date_mode')}
            spec.update(name='合成日報測試',weekday=0)
            action=actions.create(cid,'report','合成日報驗證',spec)
            preview=actions.preview(action['id'],1)
            if not preview['ready']:raise GatewayError('合成需求尚未通過條件核對。')
            if store.schedules() or store.tasks():raise GatewayError('未批准前產生工作，驗證失敗。')
            action=actions.confirm(action['id'],1,True);sid=action['schedule_id']
            next_fire=store.schedule(sid)['next_fire']
            tid=actions.run_now(action['id'],'synthetic-check')
            until=time.monotonic()+40
            while time.monotonic()<until:
                task=store.task(tid)
                if task['state'] in ('failed','succeeded','cancelled'):break
                time.sleep(.05)
            if task['state']!='succeeded' or task['result'].get('summary_status')!='succeeded' or not task['result'].get('summary') or not store.notifications():
                raise GatewayError('合成查詢／日報／通知未全部通過；沒有啟用使用者排程。')
            if store.messages(cid) or store.schedule(sid)['next_fire']!=next_fire:
                raise GatewayError('模型歷史或原定時間被改變，驗證失敗。')
        finally:engine.close(wait=True)
    return {'complete_request':'external_real_passed','missing_conditions':'external_real_passed',
            'approved_query_report_notification':'external_real_passed','synthetic_only':True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--reports', action='store_true', help='Requires --live; isolated daily report workflow')
    args = parser.parse_args()
    if args.reports and not args.live:parser.error('--reports requires explicit --live')
    if sys.version_info[:3] != (3, 10, 4):
        raise SystemExit('Use project Python 3.10.4')
    result = {'key_configured':False, 'external_service':'not_tested'}
    try:
        read_key()
        result['key_configured'] = True
        if args.reports:
            result['reports']=check_reports()
            result['external_service']='external_real_passed'
        elif args.live:
            client = GroqAssistant()
            try:
                answer = client.respond([{'role':'user','content':'這是虛構測試。請只用一句繁體中文說明你可以協助整理文字。'}])
                result['external_service'] = 'external_real_passed'
                result['nonempty_response'] = bool(answer.strip())
            finally:
                client.close()
    except GatewayError as exc:
        result['error'] = str(exc)
        if args.live: result['external_service'] = 'failed'
    except Exception:
        result['error'] = 'Trial check failed; no raw provider errors recorded.'
    print(json.dumps(result, ensure_ascii=True))
    return int('error' in result)


if __name__ == '__main__':
    raise SystemExit(main())
