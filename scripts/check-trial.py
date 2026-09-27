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
    from desktop_app.report_drafts import extract_draft
    from desktop_app.report_engine import ReportEngine
    from desktop_app.core import Store
    from desktop_app.gateways import DemoQueries
    from desktop_app.trial import TrialProfiles
    parsed=extract_draft('每天早上八點查昨天 A 類數量合計，整理日報。')
    if any(parsed[k]!=v for k,v in {'query_id':'DEMO03','time_hhmm':'08:00','category':'A','date_mode':'previous_day','frequency':'daily'}.items()):
        raise GatewayError('完整需求解析未符合預期；沒有啟用使用者排程。')
    missing=extract_draft('每天幫我查資料做報告。')
    if missing['query_id'] is not None or missing['time_hhmm'] is not None or not missing['questions']:
        raise GatewayError('缺少條件時未正確追問；沒有啟用使用者排程。')
    with tempfile.TemporaryDirectory(prefix='qa-report-check-') as tmp:
        store=Store(Path(tmp)/'test.sqlite3');queries=DemoQueries();profiles=TrialProfiles()
        engine=ReportEngine(store,queries.run,None,query_validator=queries.validate,query_catalog=queries.catalog,
                            assistant_router=profiles.respond,binding_validator=profiles.validate)
        try:
            preview=engine.preview_report({'name':'合成日報測試','query_id':parsed['query_id'],
                'parameters':{'category':parsed['category']},'time_hhmm':parsed['time_hhmm']},profiles.default_binding())
            if store.schedules() or store.tasks():raise GatewayError('未批准前產生工作，驗證失敗。')
            sid=engine.confirm_report(preview['token']);tid=engine.run_schedule_now(sid,request_id='synthetic-check')
            until=time.monotonic()+40
            while time.monotonic()<until:
                task=store.task(tid)
                if task['state'] in ('failed','succeeded','cancelled'):break
                time.sleep(.05)
            if task['state']!='succeeded' or task['result'].get('summary_status')!='succeeded' or not task['result'].get('summary') or not store.notifications():
                raise GatewayError('合成查詢／日報／通知未全部通過；沒有啟用使用者排程。')
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
