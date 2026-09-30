"""Explicit DSE test: ten synthetic turns per selected profile; no automatic run."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))


def exercise(profiles,profile_ids,directory,search=False):
    from desktop_app.dialogue_provider import ProfileDialogueProvider
    from desktop_app.dialogue_service import DialogueService
    from desktop_app.dialogue_store import DialogueStore
    from desktop_app.assistant_errors import AssistantFailure
    report={'service':'not_tested','data':'synthetic_only','mode':'search' if search else 'text',
            'automatic_retry':False,'profiles':[],'source_accuracy':'not_tested',
            'user_workspace_changed':False}
    # Keep configured credential references, but isolate all requests/history/logs.
    profiles.path=Path(directory)/'profiles.json'
    profiles.data=copy.deepcopy(profiles.data)
    if not search:
        for row in profiles.data['profiles']:row['chat_search_enabled']=False
    service=DialogueService(DialogueStore(Path(directory)/'dialogue.sqlite3'),ProfileDialogueProvider(profiles))
    try:
        for index,pid in enumerate(profile_ids,1):
            result={'profile_number':index,'status':'failed','completed_turns':0}
            report['profiles'].append(result)
            try:
                binding=profiles.snapshot(pid);profile=profiles.validate(binding)
                if pid=='demo' or profiles.data.get('wire_mode')!='assistants':
                    raise ValueError('not_assistants')
                if search and (not profile.get('chat_search_enabled') or not profile.get('search_policy',{}).get('tools')):
                    raise ValueError('search_not_approved')
                tid=service.start(assistant_id=f"company:{pid}:{binding['revision']}")['id']
                for turn in range(1,2 if search else 11):
                    prompt=('請使用已核准搜尋查找 Python 官方網站的 Python 3.10.4 發布日期。列出來源網址與日期；找不到就明示，勿捏造。'
                            if search else f'這是合成連線驗收第 {turn} 輪，測試標記 SAMPLE-{index}-{turn}。請簡短回覆收到；不查詢資料、不使用工具。')
                    state=service.send(tid,prompt,f'live-{index}-{turn}')
                    if len(state['messages'])!=turn*2 or state['request']['state']!='completed':
                        raise ValueError('incomplete_turn')
                    result['completed_turns']=turn
                result['status']='company_real_passed'
                if search:
                    import sqlite3
                    from desktop_app.assistants_gateway import session_context
                    key,rid,_,_=session_context(binding,'chat',{'conversation_id':'dialogue:'+tid,'request_id':f'live-{index}-1'})
                    with sqlite3.connect(Path(directory)/'assistant-sessions.sqlite3') as db:
                        row=db.execute('SELECT data FROM requests WHERE session_id=? AND id=?',(key,rid)).fetchone()
                    receipt=json.loads(row[0]) if row else {}
                    calls=[c for b in receipt.get('tool_batches',[]) if b.get('submit_state')=='submitted'
                           for c in b.get('calls',[]) if c.get('state')=='completed']
                    result.update(sources_require_manual_review=True,completed_search_calls=len(calls),
                                  search_execution='company_real_passed' if calls else 'not_tested')
                    if not calls:result['status']='failed'
            except AssistantFailure as exc:
                result['failure']=exc.metadata()
            except Exception:
                result['failure']={'code':'LOCAL_OR_CONTRACT_FAILURE'}
        report['service']='company_real_passed' if report['profiles'] and all(r['status']=='company_real_passed' for r in report['profiles']) else 'failed'
    finally:service.close()
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Explicitly authorize real requests and possible usage charges')
    parser.add_argument('--profiles',type=Path,help='Existing assistants.json; never an API key')
    parser.add_argument('--profile',action='append',default=[],help='Local profile ID, up to four; repeat for each assistant')
    parser.add_argument('--config',type=Path,help='Optional existing config.json for CA and request time limits')
    parser.add_argument('--search',action='store_true',help='Separate one-turn search test using already approved chat tools')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    if sys.version_info[:3]!=(3,10,4):parser.error('Use Python exactly 3.10.4')
    report={'service':'not_tested','requests':0,'reason':'Use --live explicitly; no settings or keys were read.'}
    if args.live:
        if not args.profiles or not args.profiles.is_file() or not 1<=len(set(args.profile))<=4 or len(set(args.profile))!=len(args.profile):
            parser.error('--live requires an existing --profiles and one to four distinct --profile IDs')
        from desktop_app.config import load_config,validate_config
        from desktop_app.profiles import Profiles
        try:
            legacy=(load_config(args.config) if args.config else validate_config({}))['assistant']
            profiles=Profiles(args.profiles,legacy)
            with tempfile.TemporaryDirectory(prefix='qa-assistants-test-') as directory:
                report=exercise(profiles,args.profile,directory,args.search)
        except Exception:
            report={'service':'failed','reason':'LOCAL_SETUP','requests_not_confirmed':True}
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text+'\n',encoding='utf-8')
    print(text)
    return 1 if report['service']=='failed' else 0


if __name__=='__main__':raise SystemExit(main())
