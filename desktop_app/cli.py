"""Bounded CLI presentation of the same desktop services; never a shell executor."""
import argparse
import copy
import getpass
import json
import sys
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path


HELP = """QA agent 工作台
直接輸入文字：送給目前助理（預設本機示範）
/assistants                   列出聊天助理及已驗證規劃角色
/skills                       列出我的 Skills
/skill <ID> [profileID]        選取 Skill，建立零派發規劃；預設使用其本機助理
/skill-values <JSON>           填入必要條件，呼叫規劃前仍須 /reply
/skill-save <JSON>             新建或修改：{data:定義,id?:ID,revision?:修訂}；預覽確認後保存
/skill-draft <profileID> <需求> 請指定助理起草方法（一次請求，不保存或執行）
/skill-import <Markdown路徑>   匯入為新草稿，預覽確認保存（缺欄位改用 /skill-save）
/skill-export <ID> <路徑>      分享單一 Markdown，不含助理綁定
/skill-copy <ID>               取得可修改新草稿，不保存
/skill-manage <ID> <disable|enable|delete> 預覽關聯排程後確認
/skill-probe <profileID> [search] 明確確認後相容性測試，最多三次請求
/skill-edit <JSON步驟陣列>     修改目前計畫；舊預覽失效
/skill-inspect 或 /skill-recover 檢查／取回原規劃，不重送未知請求
/skill-schedule <HH:MM>        成果核對與持續授權後每日排程
/order <profile ID> <需求>     建立交辦並請助理補條件（示範ID為demo）
/orders 或 /order-open <ID>    列出／選取既有交辦
/order-reply <補充>            補充交辦；不會搜尋
/order-edit <JSON>             編輯scope、sources、time_hhmm欄位
/order-preview                預覽目前交辦
/order-run                    確認試跑一次
/order-enable                 核對成果與來源後同意每日排程
/order-pause 或 /order-cancel  暫停排程／取消目前交辦工作
/order-inspect 或 /order-recover 檢查原請求／取回已知規劃回覆
/use <聊天助理ID>              開新對話；不轉交舊歷史
/new                          同一助理開新對話
/history                      查看主對話識別
/open <對話ID>                接回既有對話，不重新送出
/plan <主代理profile ID> <需求> 呼叫已驗證主代理，只規劃
/reply <補充或選項答案>        補充目前計畫
/preview                      檢視目前分工，不執行
/approve                      重新顯示預覽並由人確認後執行
/workflow <流程ID>            選取舊流程，讀取真實狀態
/status                       工作、排程及目前計畫狀態
/result <工作ID>              讀取成果；不呼叫模型
/briefing <profile ID>         預覽財經日報，再明確確認試跑一次
/schedule <日報工作ID>         核對試跑成果後，另行同意每日傳送
/pause <排程ID>               暫停排程
/cancel <工作ID>              請求取消，不保證遠端停止
/inspect 或 /recover          檢查或取回目前對話原請求，不重送未知POST
/help 或 /quit
/activation                   查看部署與分項能力狀態
/activate <AssistantID>       互動輸入endpoint及遮蔽金鑰並保存（不呼叫模型）
/activation-test <profileID>  確認後發送兩輪合成訊息
/memories [聊天助理ID]         列出本機記憶
/remember <JSON>              預覽確認保存 {data:{title,text,category,assistant_id},id?,revision?}
/memory-manage <ID> <enable|disable|delete> 預覽後確認
/new-memory <聊天助理ID>       預覽確認記憶後建立新對話（不送出）
/rename <標題> 或 /pin on|off  管理目前主對話
/draft <文字>                 保存目前對話草稿
/summarize <選取原文>          明確呼叫一次，輸出可修改摘要（不建立對話）
/continue <摘要文字>           預覽後建立同助理接續草稿
/continue-to <聊天助理ID> <摘要文字>  舊連線失效時明確選新目的助理
/skill-with-memory <JSON>     指定id/revision/profile_id/memory_ids建立規劃，不派發
/folders                     列出主對話資料夾
/folder-create <名稱>         建立本機資料夾
/folder-move <ID|none>        將目前對話移入資料夾或未分類
排程器在CLI停用；已啟用的排程需關閉CLI後開桌面運作。
CLI與桌面不可同時開同一工作區。Ctrl+C取消本次對話等待。
"""


def terminal_text(value):
    """Untrusted model text must not inject terminal escape/control sequences."""
    return ''.join(c if c in '\n\t' or (ord(c) >= 32 and not 127 <= ord(c) <= 159) else '\ufffd'
                   for c in str(value))


class Workbench:
    def __init__(self, session):
        from .web_bridge import WebBridge
        self.session = session
        self.bridge = WebBridge(session)
        self.thread = None
        self.workflow = None
        self.order = None
        self.skill_values = None

    def skills(self):return self.call('skill_list')

    def orders(self):
        return self.call('order_list')

    def current_order(self):
        if not self.order:raise ValueError('請先 /order 或 /order-open 選取交辦。')
        return self.call('order_state',id=self.order)

    def call(self, operation, **payload):
        result = self.bridge.call(operation, payload)
        if not result['ok']:
            raise ValueError(result['error'])
        return result['data']

    def assistants(self):
        self.session.assert_identity()
        # Deliberately exclude credential indexes, endpoints and secret values.
        rows = self.call('dialogue_catalog')['assistants']
        return {'work':self.call('order_catalog'),'chat': [{k:r[k] for k in ('id','name') if k in r} for r in rows],
                'planners': [{'id':r['id'],'name':r['name']} for r in
                             self.session.profiles.workflow_catalog() if 'planner' in r['workflow']['roles']]}

    def start(self, assistant_id='demo-general'):
        result = self.call('dialogue_start', assistant_id=assistant_id, mode='chat')
        self.thread = result
        return result

    def chat(self, text):
        if self.thread is None:self.start()
        self.thread = self.call('dialogue_send', id=self.thread['id'], text=text, request_id=uuid.uuid4().hex)
        return self.thread

    def plan(self, profile_id, text):
        s = self.session
        s.assert_identity()
        binding = s.profiles.workflow_binding(profile_id)
        s.profiles.validate_workflow(binding, 'planner')
        cid = self.call('new_chat', profile_id=profile_id)
        result = self.call('workflow_discuss', cid=cid, planner_id=profile_id, text=text)
        self.workflow = result['id']
        return result

    def current_workflow(self):
        self.session.assert_identity()
        if not self.workflow:raise ValueError('請先 /plan 或 /workflow 選取流程。')
        return self.session.workflows.snapshot(self.workflow)

    def preview(self):
        r = self.current_workflow()
        return self.call('workflow_preview', wid=r['id'], revision=r['revision'])

    def status(self):
        self.session.assert_identity()
        s = self.session
        return {'scheduler_running':s.scheduler is not None,
                'tasks':[{k:r[k] for k in ('id','kind','state','created_at')} for r in s.store.tasks()],
                'schedules':[{k:r[k] for k in ('id','name','enabled','next_fire')} for r in s.store.schedules()],
                'workflow':self.current_workflow() if self.workflow else None}

    def result(self, task_id):
        task = self.call('task_result', task_id=task_id)
        if task['kind']=='workflow':
            return self.call('outcome', task_id=task_id)
        return {k:task.get(k) for k in ('id','kind','state','result','error')}


def emit(value, output):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    output.write(terminal_text(text)+'\n')
    output.flush()


def confirm(preview, prompt, input_stream, output):
    """Interactive human gate. No --yes and no approval from model/stdin pipe."""
    emit(preview, output)
    if not input_stream.isatty():
        raise ValueError('執行確認需要互動終端；不能以管線或模型輸出批准。請在桌面或終端核對。')
    output.write(prompt+' 輸入「確認執行」，其餘取消：')
    output.flush()
    return input_stream.readline().strip() == '確認執行'


def execute_line(w, line, input_stream, output):
    """Return False only for quit. No dispatch based on assistant output."""
    if not line.strip():return True
    if not line.startswith('/'):
        state=w.chat(line)
        emit(state['messages'][-1]['text'] if state['messages'] else state, output)
        return True
    command, _, argument = line.partition(' ')
    argument=argument.strip()
    if command=='/quit':return False
    if command=='/help':emit(HELP,output)
    elif command=='/activation':emit(w.call('activation_status'),output)
    elif command=='/activate':
        if not input_stream.isatty():raise ValueError('金鑰只接受互動遮蔽輸入，不接受命令列或管線。')
        setup=w.call('activation_status')
        if not setup['available']:raise ValueError(setup['message'])
        output.write('HTTPS endpoint（留空沿用既有設定）：');output.flush()
        endpoint=input_stream.readline().strip() or setup['endpoint']
        changed=bool(setup['endpoint'] and endpoint!=setup['endpoint']) or setup['wire_mode'] not in ('unconfigured','assistants')
        if changed and not confirm({'endpoint':endpoint,'notice':'撤銷舊憑證及能力，舊對話保留唯讀。'},'變更服務端點與協定？',input_stream,output):return True
        key=getpass.getpass('API key（遮蔽）：')
        try:emit(w.call('activation_save',assistant_id=argument,api_key=key,endpoint=endpoint,confirm_endpoint_change=changed),output)
        finally:key=None
    elif command=='/activation-test':
        if confirm({'profile_id':argument,'requests':2},'傳送兩輪合成測試？',input_stream,output):emit(w.call('activation_test',profile_id=argument,consent=True),output)
    elif command=='/memories':emit(w.call('memory_list',assistant_id=argument or None),output)
    elif command=='/folders':emit(w.call('dialogue_folders'),output)
    elif command=='/folder-create':emit(w.call('dialogue_folder_create',name=argument),output)
    elif command=='/folder-move':
        if not w.thread:raise ValueError('請先開啟主對話。')
        emit(w.call('dialogue_folder_move',thread_id=w.thread['id'],folder_id=None if argument=='none' else argument),output)
    elif command=='/remember':
        p=w.call('memory_preview',**json.loads(argument))
        if confirm(p,'保存以上記憶（未送出）？',input_stream,output):emit(w.call('memory_confirm',token=p['token']),output)
    elif command=='/memory-manage':
        mid,_,action=argument.partition(' ');r=next((r for r in w.call('memory_list') if r['id']==mid),None)
        if not r:raise ValueError('記憶不存在。')
        p=w.call('memory_manage_preview',id=mid,revision=r['revision'],action=action)
        if confirm(p,'套用以上記憶變更？',input_stream,output):emit(w.call('memory_manage_confirm',token=p['token']),output)
    elif command=='/new-memory':
        p=w.call('chat_start_preview',mode='chat',assistant_id=argument)
        if confirm(p,'下次送出將使用以上記憶，建立新對話？',input_stream,output):
            w.thread=w.call('chat_start_confirm',token=p['token'],use_memory=True);emit(w.thread,output)
    elif command in ('/rename','/pin','/draft','/summarize','/continue','/continue-to'):
        if not w.thread:raise ValueError('請先開啟主對話。')
        t=w.call('dialogue_state',id=w.thread['id'])
        if command=='/rename':w.thread=w.call('dialogue_rename',id=t['id'],title=argument);emit(w.thread,output)
        elif command=='/pin':
            if argument not in ('on','off'):raise ValueError('使用 /pin on 或 /pin off。')
            w.thread=w.call('dialogue_pin',id=t['id'],pinned=argument=='on');emit(w.thread,output)
        elif command=='/draft':emit(w.call('dialogue_view_save',id=t['id'],text=argument,scroll=t['scroll'],revision=t['view_revision']),output)
        elif command=='/summarize':
            if confirm({'selected':argument,'assistant_id':t['assistant_id']},'傳送選取內容產生摘要一次？',input_stream,output):emit(w.call('continuation_summary',id=t['id'],text=argument,assistant_id=t['assistant_id'],consent=True),output)
        else:
            aid=t['assistant_id'];value=argument
            if command=='/continue-to':aid,_,value=argument.partition(' ')
            p=w.call('continuation_preview',id=t['id'],assistant_id=aid,text=value)
            if confirm(p,'建立接續草稿（不送出）？',input_stream,output):w.thread=w.call('continuation_confirm',token=p['token']);emit(w.thread,output)
    elif command=='/skill-with-memory':
        options=json.loads(argument);r=w.call('skill_start',**options);w.workflow=r['id'];w.skill_values=options.get('values',{});emit(r,output)
    elif command=='/skills':emit(w.skills(),output)
    elif command=='/skill':
        sid,_,pid=argument.partition(' ');s=w.call('skill_get',id=sid)
        pid=pid.strip() or s.get('default_profile_id')
        if not pid:raise ValueError('請指定本機 profile ID：/skill SkillID profileID')
        r=w.call('skill_start',id=sid,revision=s['revision'],profile_id=pid,values={},goal=s['purpose'])
        w.workflow=r['id'];w.skill_values={};emit(r,output)
    elif command=='/skill-values':
        from .skills import answers
        r=w.call('skill_state',wid=w.workflow);v,missing=answers(r['skill']['fields'],json.loads(argument))
        w.skill_values=v;emit({'values':v,'missing':missing,'notice':'尚未傳送；使用 /reply 討論。'},output)
    elif command=='/skill-copy':emit(w.call('skill_copy',id=argument),output)
    elif command=='/skill-draft':
        pid,_,request=argument.partition(' ')
        if not request:raise ValueError('用法：/skill-draft profileID 工作方法需求')
        emit(w.call('skill_generate',profile_id=pid,request=request),output)
    elif command in ('/skill-save','/skill-import'):
        if command=='/skill-import':
            from .skills import import_markdown
            path=Path(argument.strip('"'))
            if path.suffix.lower()!='.md' or path.stat().st_size>65536:raise ValueError('只接受64KiB內單一Markdown。')
            data=import_markdown(path.read_text(encoding='utf-8-sig'));emit({'draft':data},output);p={'data':data}
        else:p=json.loads(argument)
        preview=w.call('skill_save_preview',**p)
        if confirm(preview,'保存工作方法（不執行）？',input_stream,output):emit(w.call('skill_save_confirm',token=preview['token']),output)
        else:emit('未保存。',output)
    elif command=='/skill-export':
        from .skills import export_markdown
        sid,_,name=argument.partition(' ');path=Path(name.strip('"'))
        if not name or path.suffix.lower()!='.md':raise ValueError('請指定單一 .md 路徑。')
        text=export_markdown(w.call('skill_get',id=sid))
        if confirm({'file':str(path),'notice':'指示正文可能包含你自行寫入的私密資料，請先檢查。'},'匯出以上 Markdown？',input_stream,output):
            # CLI never silently overwrites a pre-existing user file.
            with path.open('x',encoding='utf-8') as f:f.write(text)
            emit('已匯出。',output)
    elif command=='/skill-manage':
        sid,_,action=argument.partition(' ');r=w.call('skill_get',id=sid)
        p=w.call('skill_manage_preview',id=sid,revision=r['revision'],action=action)
        if confirm(p,'套用以上 Skill 管理操作？',input_stream,output):emit(w.call('skill_manage_confirm',token=p['token']),output)
    elif command=='/skill-probe':
        pid,_,search=argument.partition(' ')
        if search not in ('','search'):raise ValueError('選項僅支援 search。')
        if confirm({'profile_id':pid,'search':bool(search),'requests':3 if search else 2},'傳送合成相容性測試？',input_stream,output):emit(w.call('skill_probe',profile_id=pid,search=bool(search),consent=True),output)
    elif command=='/skill-edit':
        r=w.current_workflow();emit(w.call('skill_update',wid=r['id'],revision=r['revision'],steps=json.loads(argument)),output)
    elif command in ('/skill-inspect','/skill-recover'):
        r=w.current_workflow();emit(w.call(command[1:].replace('-','_'),wid=r['id']),output)
    elif command=='/skill-schedule':
        r=w.call('skill_state',wid=w.workflow)
        if confirm({'workflow':r,'time_taipei':argument},'已核對成果與來源，且同意每日持續傳送？',input_stream,output):emit(w.call('skill_schedule',wid=r['id'],revision=r['revision'],time_hhmm=argument,reviewed=True,consent=True),output)
    elif command=='/assistants':emit(w.assistants(),output)
    elif command=='/orders':emit(w.orders(),output)
    elif command=='/order':
        pid,_,goal=argument.partition(' ')
        if not goal:raise ValueError('用法：/order profileID 需求')
        r=w.call('order_create',profile_id=pid,goal=goal)
        w.order=r['id']
        emit(w.call('order_discuss',id=r['id'],revision=r['revision'],text=goal),output)
    elif command=='/order-open':
        r=w.call('order_state',id=argument);w.order=r['id'];emit(r,output)
    elif command=='/order-reply':
        r=w.current_order();emit(w.call('order_discuss',id=r['id'],revision=r['revision'],text=argument),output)
    elif command=='/order-edit':
        r=w.current_order();emit(w.call('order_edit',id=r['id'],revision=r['revision'],answers=json.loads(argument)),output)
    elif command=='/order-preview':
        r=w.current_order();emit(w.call('order_preview',id=r['id'],revision=r['revision']),output)
    elif command in ('/order-run','/order-enable'):
        r=w.current_order();enable=command=='/order-enable'
        p=w.call('order_schedule_preview' if enable else 'order_preview',id=r['id'],revision=r['revision'])
        prompt='已人工核對成果與來源，且同意每日持續傳送？' if enable else '同意試跑以上需求一次（不啟用排程）？'
        if confirm(p,prompt,input_stream,output):
            emit(w.call('order_enable' if enable else 'order_trial',id=r['id'],token=p['token'],**({'reviewed':True,'consent':True} if enable else {})),output)
        else:emit('已取消確認；未派發。',output)
    elif command=='/order-cancel':
        if not w.order:raise ValueError('請先選取交辦。')
        emit(w.call('order_cancel',id=w.order),output)
    elif command in ('/order-pause','/order-inspect','/order-recover'):
        r=w.current_order();emit(w.call(command[1:].replace('-','_'),id=r['id']),output)
    elif command=='/use':emit(w.start(argument),output)
    elif command=='/new':emit(w.start(w.thread['assistant_id'] if w.thread else 'demo-general'),output)
    elif command=='/history':emit(w.call('dialogue_history'),output)
    elif command=='/open':
        w.thread=w.call('dialogue_state',id=argument);emit(w.thread,output)
    elif command=='/plan':
        pid, _, text=argument.partition(' ')
        if not text:raise ValueError('用法：/plan 主代理profileID 需求')
        emit(w.plan(pid,text),output)
    elif command=='/reply':
        r=w.current_workflow()
        if w.session.skills.link(r['id']):
            emit(w.call('skill_discuss',wid=r['id'],revision=r['revision'],text=argument,values=w.skill_values if w.skill_values is not None else w.session.skills.link(r['id'])['inputs']),output)
        else:emit(w.call('workflow_discuss',cid=r['conversation_id'],wid=r['id'],revision=r['revision'],text=argument),output)
    elif command=='/workflow':
        w.session.assert_identity()
        r=w.session.workflows.snapshot(argument);w.workflow=r['id'];w.skill_values=None;emit(r,output)
    elif command=='/preview':emit(w.preview(),output)
    elif command=='/approve':
        r=w.preview()
        if not r['ready']:raise ValueError(r['error'] or '計畫尚未就緒。')
        if confirm(r,'同意以上修訂的分工與指定資料傳送？',input_stream,output):
            emit(w.call('workflow_confirm',wid=r['id'],revision=r['revision']),output)
        else:
            w.session.workflows.previews.pop(r['id'],None)
            emit('已取消確認；尚未執行。',output)
    elif command=='/status':emit(w.status(),output)
    elif command=='/result':emit(w.result(argument),output)
    elif command=='/briefing':
        default=w.call('briefing_defaults')
        r=w.call('briefing_preview',profile_id=argument,**default)
        if confirm(r,'同意將上述日報需求送給指定助理試跑一次（不啟用排程）？',input_stream,output):
            emit(w.call('briefing_run',token=r['token']),output)
        else:emit('未派發。',output)
    elif command=='/schedule':
        r=w.call('briefing_status',task_id=argument)
        if r['state']!='succeeded':raise ValueError('請先完成一次成功試跑並核對來源。')
        if confirm({'result':r.get('result'),'spec':r['payload']['spec'],
                    'notice':'每日持續傳送；僅桌面開啟時執行。'},
                   '已人工核對來源，並同意按上述台北時間持續傳送？',input_stream,output):
            emit(w.call('briefing_schedule',task_id=argument,consent=True,reviewed=True),output)
        else:emit('未啟用排程。',output)
    elif command=='/pause':emit(w.call('schedule_toggle',id=argument,enabled=False),output)
    elif command=='/cancel':emit(w.call('cancel_task',task_id=argument),output)
    elif command in ('/inspect','/recover'):
        if not w.thread:raise ValueError('請先開啟對話。')
        w.thread=w.call('dialogue_inspect' if command=='/inspect' else 'dialogue_recover',id=w.thread['id'])
        emit(w.thread,output)
    else:raise ValueError('未知指令。輸入 /help 查看；不會執行系統命令。')
    return True


def shell(w, input_stream, output):
    emit(HELP,output)
    emit('聊天預設為本機示範；使用 /assistants 再 /use 明確選擇真實助理。',output)
    while True:
        try:
            output.write('QA > ');output.flush()
            line=input_stream.readline()
            if not line:break
            if not execute_line(w,line.rstrip('\r\n'),input_stream,output):break
        except KeyboardInterrupt:
            if w.thread:w.call('dialogue_stop',id=w.thread['id'])
            emit('已停止本次等待；未自動重送。規劃或背景工作請查看 /status。',output)
        except ValueError as exc:emit('未完成：'+str(exc),output)
        except Exception:
            emit('操作未完成；未自動重送。請查看本機狀態或安全日誌。',output)


@contextmanager
def open_session(args, input_stream, output):
    from .config import DEFAULT, data_directory, load_config
    from .web_session import WebSession
    temporary=tempfile.TemporaryDirectory(prefix='qa-cli-demo-') if args.demo else None
    session=None;login=None
    try:
        directory=Path(temporary.name) if temporary else data_directory()
        config=copy.deepcopy(DEFAULT) if temporary else load_config(args.config or directory/'config.json')
        if config['identity_mode']=='company':
            if not input_stream.isatty():raise ValueError('AD登入需要互動終端；不接受命令列密碼。')
            from .authentication import authenticate
            output.write('工號：');output.flush()
            employee=input_stream.readline().strip()
            password=getpass.getpass('密碼：')
            try:login=authenticate(employee,password)
            finally:password=None
        session=WebSession(directory=directory,config=config,login_session=login,start_scheduler=False,deployment_defaults=not args.demo,activation_enabled=not args.demo)
        yield session
    finally:
        if session:session.close()
        elif login:login.close()
        if temporary:temporary.cleanup()


def main(argv=None):
    parser=argparse.ArgumentParser(description='QA agent CLI 工作台；共用桌面服務，無任意shell執行。')
    source=parser.add_mutually_exclusive_group()
    source.add_argument('--demo',action='store_true',help='暫存離線示範，不讀取正式設定')
    source.add_argument('--config',help='既有本機設定檔；金鑰仍由原keyring機制取得')
    parser.add_argument('command',nargs='?',choices=['shell','assistants','skills','orders','status','result','desktop'],default='shell')
    parser.add_argument('task_id',nargs='?')
    args=parser.parse_args(argv)
    if sys.version_info[:3]!=(3,10,4):parser.error('請使用專案 Python 3.10.4。')
    if args.command=='result' and not args.task_id:parser.error('result 需要工作ID。')
    if args.command=='desktop':
        if args.demo:parser.error('桌面示範請使用 start-demo-login.bat。')
        from .web_app import launch
        return 0 if launch(args.config) else 1
    try:
        with open_session(args,sys.stdin,sys.stdout) as session:
            w=Workbench(session)
            if args.command=='shell':shell(w,sys.stdin,sys.stdout)
            else:emit(w.result(args.task_id) if args.command=='result' else getattr(w,args.command)(),sys.stdout)
        return 0
    except KeyboardInterrupt:return 130
    except ValueError as exc:
        emit({'ok':False,'error':str(exc)},sys.stderr);return 1
    except Exception:
        emit({'ok':False,'error':'CLI未完成；請執行環境診斷或從桌面查看安全紀錄。'},sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
