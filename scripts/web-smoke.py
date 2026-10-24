"""Exercise the actual WebView2 host with synthetic, temporary data only."""
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import webview
from desktop_app.web_app import application_html
from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge


def agent_followup_journey(session,api,window,capture,wait,report):
    """Two UI-only response fixtures; no provider/network requests or execution."""
    import copy
    from desktop_app.skills import TEMPLATE
    def js(script):return window.evaluate_js(script)
    definition=copy.deepcopy(TEMPLATE);definition.update(name='合成接續方法',search=False,fields=[])
    skill=session.skills.save_confirm(session.skills.save_preview(definition)['token'])
    js("document.getElementById('dialogue-agent-mode').click()")
    wait("!!document.getElementById('agent-create')")
    job=session.agents.create('demo','合成原需求：只整理已提供的工作記錄',skill_id=skill['id'],skill_revision=skill['revision'],autonomous=False)
    for _ in range(100):
        if not session.engine.has_inflight():break
        time.sleep(.05)
    job=session.agents.state(job['id']);assert job['state']=='ready'
    fixture=copy.deepcopy(job);fixture['task']={'id':'ui-fixture-only','state':'failed','error':'AGENT_NEEDS_INPUT：缺少指定資料。','result':{'report':''}}
    def show(value):js('window.qaAgentUI.show('+json.dumps(value,ensure_ascii=False)+')')
    show(fixture);wait("!!document.getElementById('agent-restart-draft')")
    before=(len(session.agents.list()),len(session.store.tasks()))
    js("document.getElementById('agent-restart-draft').click()")
    wait("!!document.getElementById('agent-create')")
    assert js("document.getElementById('agent-goal').value")==job['goal']
    assert js("document.getElementById('agent-profile').value")=='demo'
    assert js("document.getElementById('agent-skill').value")==skill['id']
    assert js("document.querySelectorAll('.agent-memory-choices input:checked').length")==0
    assert before==(len(session.agents.list()),len(session.store.tasks())),'restart_draft_dispatched'
    assert js("document.getElementById('agent-job-panel').textContent.includes('不帶入舊成果、記憶、批准或排程')")
    capture('agent-restart-draft.png')
    fixture['skill']['revision']+=1;fixture['task']['error']='AGENT_REQUEST_LIMIT：已達本機上限。'
    show(fixture);js("document.getElementById('agent-restart-draft').click()")
    wait("!!document.getElementById('agent-create')")
    assert js("document.getElementById('agent-skill').value")==''
    assert js("document.getElementById('agent-job-panel').textContent.includes('未自動選用其他版本')")
    fixture['task']['error']='RUN_OUTCOME_UNKNOWN：送出結果未明，不可重送。';show(fixture)
    assert js("!document.getElementById('agent-restart-draft')"),'unknown_send_shortcut_offered'
    assert before==(len(session.agents.list()),len(session.store.tasks()))
    # Expired identity is a cancellation acknowledgement, not a full state snapshot.
    show(job)
    js("window.agentFollowupCall=window.qaSkillUI.call;window.agentCancelCalls=0;window.qaSkillUI.call=async(name,payload)=>{if(name==='agent_cancel'){window.agentCancelCalls++;return {cancelled:true,identity_expired:true};}return window.agentFollowupCall(name,payload);}")
    js("document.getElementById('agent-cancel').click()")
    wait("document.getElementById('agent-job-heading').textContent.includes('已要求取消；登入已到期')")
    assert js("window.agentCancelCalls")==1
    assert js("document.getElementById('agent-job-heading').textContent.includes('合成原需求')"),'expired_cancel_repainted_incomplete_snapshot'
    assert not session.store.tasks()
    js("document.getElementById('agent-job-heading').scrollIntoView({block:'start'});window.qaSkillUI.call=window.agentFollowupCall")
    capture('agent-expired-cancel.png')
    report['checks'].extend(['ui_fixture_restart_prepares_goal_profile_search_skill_only_no_dispatch_stale_skill_unselected_unknown_send_excluded','ui_fixture_expired_cancel_acknowledged_without_snapshot_repaint_or_dispatch'])


def agent_journey(session,api,window,capture,wait,report):
    """Actual WebView controls over temporary services; all provider replies synthetic."""
    import copy
    from unittest.mock import patch
    from desktop_app.core import dumps,stamp
    from desktop_app.skills import TEMPLATE
    from tests.test_search_tools import SEARCH_TOOL
    def js(script):return window.evaluate_js(script)
    def click(selector):js(f"document.querySelector({json.dumps(selector)}).click()")
    def put(selector,value):js(f"(()=>{{const n=document.querySelector({json.dumps(selector)});n.value={json.dumps(value)};n.dispatchEvent(new Event('input',{{bubbles:true}}));}})()")
    def text_button(text,root='#modal-actions'):
        js(f"Array.from(document.querySelectorAll({json.dumps(root+' button')})).find(b=>b.textContent==={json.dumps(text)}).click()")
    def answer(label,value):
        js(f"(()=>{{const label=Array.from(document.querySelectorAll('#agent-job-panel label')).find(n=>n.textContent==={json.dumps(label)});const input=document.getElementById(label.htmlFor);input.value={json.dumps(value)};input.dispatchEvent(new Event('input',{{bubbles:true}}));}})()")
    def legacy():js("document.getElementById('agent-execution-mode').value='fixed';document.getElementById('agent-execution-mode').dispatchEvent(new Event('change'))")
    put('#dialogue-input','保留中的合成聊天草稿')
    click('#dialogue-agent-mode');wait("!!document.getElementById('agent-create')")
    assert js("document.getElementById('agent-execution-mode').value")=='autonomous'
    legacy()
    assert js("document.getElementById('dialogue-input').value")=='保留中的合成聊天草稿'
    put('#agent-goal','將合成工作筆記整理成重點，不編造期限。')
    click('#dialogue-chat-mode');wait("document.getElementById('modal').open")
    text_button('返回工作編輯');wait("!document.getElementById('modal').open")
    assert js("document.getElementById('agent-goal').value")=='將合成工作筆記整理成重點，不編造期限。'
    assert js("document.getElementById('dialogue-page').classList.contains('agent-mode')")
    # Composition Enter must not dispatch; the existing chat draft is kept independently.
    js("document.getElementById('agent-goal').dispatchEvent(new CompositionEvent('compositionstart'));document.getElementById('agent-goal').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,isComposing:true}));document.getElementById('agent-goal').dispatchEvent(new CompositionEvent('compositionend'))")
    assert not session.agents.list(),'agent_ime_dispatched'
    time.sleep(.05);click('#agent-create');wait("!!document.getElementById('agent-preview')")
    assert not session.store.tasks(),'agent_planning_dispatched'
    click('#agent-edit');wait("document.getElementById('modal').open")
    put('#agent-limit-supplements','0');click('#agent-edit-save');wait("!!document.getElementById('agent-confirm')")
    assert not session.store.tasks(),'agent_preview_dispatched'
    wait("(()=>{const r=document.getElementById('agent-confirm').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;})()")
    assert js("!document.querySelector('#navigation [data-page=dialogue]').classList.contains('active') && document.getElementById('agent-jobs-nav').classList.contains('active')"),'agent_navigation_double_selected'
    capture('agent-preview-dark.png')
    click('#agent-confirm');wait("!!document.getElementById('agent-save-skill')")
    first=session.agents.list()[0];assert first['task']['state']=='succeeded'
    assert js("!document.getElementById('agent-schedule')"),'demo_schedule_offered'
    assert js("!document.getElementById('agent-inspect')"),'successful_job_recovery_offered'
    assert js("document.getElementById('agent-job-result').textContent.includes('離線示範')")
    click('#agent-save-skill');wait("document.getElementById('modal').open")
    assert not session.skills.list(),'skill_draft_autosaved'
    text_button('取消');wait("!document.getElementById('modal').open")
    click('#dialogue-chat-mode');wait("!document.getElementById('dialogue-page').classList.contains('agent-mode')")
    assert js("document.getElementById('dialogue-input').value")=='保留中的合成聊天草稿'
    click('#agent-jobs-nav');wait("!!document.getElementById('agent-job-search')")
    text_button('開啟工作','#agent-job-panel');wait("!!document.getElementById('agent-save-skill')")
    report['checks'].append('agent_chat_draft_preserved_mode_guard_ime_preview_edit_single_confirmation_result_and_reopen')
    click('#agent-new');wait("!!document.getElementById('agent-create')")
    legacy()
    put('#agent-goal','合成取消測試：不執行這份計畫')
    click('#agent-create');wait("!!document.getElementById('agent-preview')")
    click('#agent-cancel');wait("!document.getElementById('agent-cancel') && document.getElementById('agent-job-heading').textContent.includes('已取消')")
    assert session.agents.list()[0]['state']=='cancelled'
    assert len(session.store.tasks())==1,'cancelled_plan_dispatched'
    assert js("!document.getElementById('agent-inspect')"),'cancelled_job_recovery_offered'
    # Four fields deliberately exercise multiple question rounds and all answer kinds.
    definition=copy.deepcopy(TEMPLATE);definition.update(name='合成文字 Skill',search=False)
    definition['fields']=[{'id':'short','text':'是否精簡','type':'boolean','options':[]},{'id':'style','text':'採用語氣','type':'single','options':['正式','簡單']},{'id':'parts','text':'需要段落','type':'multi','options':['重點','待辦']},{'id':'note','text':'補充背景','type':'text','options':[]}]
    skill=session.skills.save_confirm(session.skills.save_preview(definition)['token'])
    click('#agent-new');wait("!!document.getElementById('agent-create')")
    legacy()
    put('#agent-goal','整理成文字工作報告')
    js(f"document.getElementById('agent-skill').value={json.dumps(skill['id'])};document.getElementById('agent-skill').dispatchEvent(new Event('change'))")
    click('#agent-create');wait("!!document.getElementById('agent-reply-send')")
    answer('是否精簡','false');answer('採用語氣','正式')
    js("(()=>{const n=Array.from(document.querySelectorAll('#agent-job-panel fieldset label')).find(n=>n.textContent==='重點').querySelector('input');n.checked=true;n.dispatchEvent(new Event('change'));})()")
    click('#agent-reply-send');wait("Array.from(document.querySelectorAll('#agent-job-panel label')).some(n=>n.textContent==='補充背景')")
    answer('補充背景','只有合成工作紀錄，沒有確定期限');click('#agent-reply-send');wait("!!document.getElementById('agent-preview')")
    assert len(session.store.tasks())==1,'skill_questions_executed'
    click('#agent-preview');wait("!!document.getElementById('agent-confirm')");click('#agent-confirm');wait("!!document.getElementById('agent-save-skill')")
    assert session.agents.list()[0]['task']['state']=='succeeded'
    report['checks'].append('agent_skill_four_types_multiple_question_rounds_and_explicit_execution')
    # A local synthetic provider exercises the genuine search/supplement runner.
    p=session.profiles;p.set_endpoint('https://synthetic.example.test/v1');p.set_wire_mode('assistants')
    pid=p.save('合成工作助理','asst_synthetic');p.set_search_policy(p.snapshot(pid),{'tools':[SEARCH_TOOL]});binding=p.snapshot(pid)
    with session.store.connection() as db:db.execute('INSERT INTO skill_capabilities VALUES(?,?,?,?,?)',(pid,binding['revision'],'synthetic-proof',dumps(['planner','compose','assess','rag']),stamp()))
    calls=[]
    def respond(messages,purpose,binding,context=None):
        calls.append(dict(context));sid=context['step_id']
        if str(context.get('run_id','')).startswith('agent-probe:'):
            prompt=messages[0]['content'];return prompt.split('請只回覆 ',1)[1] if '請只回覆 ' in prompt else prompt.split('僅回覆 ',1)[1]
        if sid=='planner':return dumps({'message':'合成核准範圍','questions':[],'steps':[{'id':'search','title':'核對來源','kind':'assistant','role':'rag','profile_id':pid,'instruction':'只搜尋指定市場及來源','inputs':[]},{'id':'compose','title':'整理日報','kind':'assistant','role':'compose','profile_id':pid,'instruction':'保留來源限制','inputs':['search']}]})
        if sid.startswith('qa_assess_'):return dumps({'decision':'supplement' if sid=='qa_assess_0' else 'complete','step_id':'search' if sid=='qa_assess_0' else '', 'reason':'同範圍補充' if sid=='qa_assess_0' else '合成資料已齊'})
        return dumps({'text':'合成來源資料，非即時搜尋：https://example.test/source','facts':{}})
    with patch.object(p,'respond',side_effect=respond):
        for limit,expected in ((2,'succeeded'),(0,'failed')):
            click('#agent-new');wait("!!document.getElementById('agent-create')")
            legacy()
            js(f"document.getElementById('agent-profile').value={json.dumps(pid)};document.getElementById('agent-profile').dispatchEvent(new Event('change'))")
            put('#agent-goal','合成台美市場資料來源核對');js("document.getElementById('agent-search').checked=true")
            assert js("document.getElementById('connection').textContent.includes('合成工作助理') && !document.getElementById('connection').textContent.includes('離線示範')"),'agent_connection_label_mismatched'
            put('#agent-limit-supplements',str(limit));click('#agent-create');wait("!!document.getElementById('agent-preview')")
            before=len(session.store.tasks());click('#agent-preview');wait("!!document.getElementById('agent-confirm')")
            assert len(session.store.tasks())==before
            assert js("document.querySelector('.agent-approval').textContent.includes('internet_search')"),'search_tool_name_missing'
            click('#agent-confirm')
            wait("!!document.getElementById('agent-schedule')" if expected=='succeeded' else "!!document.getElementById('agent-restart-draft') && document.getElementById('agent-job-result').textContent.includes('未完成')")
            job=session.agents.list()[0];assert job['task']['state']==expected
            if expected=='succeeded':
                assert any(c['step_id']=='qa_supplement_1' for c in calls)
                click('#agent-schedule');wait("!!document.getElementById('agent-schedule-confirm')")
                click('#agent-schedule-confirm');assert not session.store.schedules(),'schedule_without_consent'
                js("document.getElementById('agent-schedule-frequency').value='weekly';document.getElementById('agent-schedule-frequency').dispatchEvent(new Event('change'));document.getElementById('agent-schedule-weekday').value='4';document.getElementById('agent-reviewed').checked=true;document.getElementById('agent-schedule-consent').checked=true")
                click('#agent-schedule-confirm');wait("!document.getElementById('modal').open")
                assert session.agents.state(job['id'])['schedule']['weekday']==4
                text_button('暫停自動工作','#agent-job-panel');wait("document.getElementById('agent-job-result').textContent.includes('已暫停')")
            else:
                assert 'AGENT_SUPPLEMENT_LIMIT' in job['task']['error']
                assert js("document.getElementById('agent-job-result').textContent.includes('合成來源資料')"),'partial_result_lost'
                assert js("!document.getElementById('agent-inspect')"),'local_limit_recovery_offered'
                # Failure remains part of the journey, but release images show a
                # completed job so the gallery is not four copies of an error.
                for size in ((1050,700),(1280,860)):
                    window.resize(*size);time.sleep(.2)
                    js("document.getElementById('agent-restart-draft').scrollIntoView({block:'center'})")
                    assert js("(()=>{const r=document.getElementById('agent-restart-draft').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;})()"),'agent_failure_action_unreachable'
        # Settings opens consent before three synthetic no-tool capability calls.
        js("document.dispatchEvent(new CustomEvent('qa-navigate',{detail:'settings'}))")
        wait("!!document.querySelector('.activation-work-check')")
        before=len(calls);text_button('測試工作格式（最多三次）','.activation-work-check');wait("!!document.getElementById('agent-probe-confirm')")
        assert len(calls)==before
        click('#agent-probe-confirm');wait("document.getElementById('modal-title').textContent==='工作能力檢查結果'")
        assert len(calls)-before==3 and all(not c['search_authorized'] for c in calls[before:])
        text_button('關閉');click('#agent-jobs-nav');wait("!!document.getElementById('agent-job-search')")
        text_button('開啟工作','#agent-job-panel');wait("!!document.getElementById('agent-restart-draft')")
        assert js("!document.getElementById('agent-inspect')"),'reopened_local_limit_recovery_offered'
        assert js("document.getElementById('connection').textContent.includes('合成工作助理')"),'reopened_agent_label_mismatched'
    report['checks'].append('agent_synthetic_supplement_bound_partial_failure_weekly_consent_pause_and_explicit_three_call_probe')
    # Reopen the earlier successful demo job through the same visible history
    # controls users have; taking screenshots must not start another execution.
    before=len(session.store.tasks())
    click('#agent-jobs-nav');wait("!!document.getElementById('agent-job-search')")
    put('#agent-job-search',first['goal'])
    text_button('開啟工作','#agent-job-panel');wait("!!document.getElementById('agent-save-skill')")
    assert len(session.store.tasks())==before,'reopen_for_capture_dispatched'
    assert js("document.getElementById('agent-job-result').textContent.includes('已完成')")
    assert js("!document.getElementById('agent-inspect')"),'reopened_success_recovery_offered'
    for theme,size,name in [('dark',(1280,860),'agent-dark.png'),('light',(1050,700),'agent-light-small.png')]:
        api.call('appearance',{'theme':theme});js(f"document.body.dataset.theme={json.dumps(theme)}")
        js("document.getElementById('toast').hidden=true")
        window.resize(*size);time.sleep(.4)
        js("document.getElementById('agent-job-result').scrollIntoView({block:'start'})")
        capture(name)
        assert js("document.getElementById('dialogue-scroll').scrollHeight>=document.getElementById('dialogue-scroll').clientHeight")
        js("document.getElementById('agent-save-skill').scrollIntoView({block:'center'})")
        assert js("(()=>{const r=document.getElementById('agent-save-skill').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;})()"),'agent_action_unreachable'
    window.maximize();time.sleep(.4)
    js("document.getElementById('agent-job-result').scrollIntoView({block:'start'})")
    capture('agent-maximized.png')
    report['checks'].append('agent_real_webview_dark_light_1050x700_normal_maximized_reachable_controls')


def autonomous_journey(session,api,window,capture,wait,report):
    """Real controls and runner, synthetic adaptive replies, no service network."""
    from unittest.mock import patch
    from desktop_app.core import dumps,stamp
    from tests.test_search_tools import SEARCH_TOOL
    def js(script):return window.evaluate_js(script)
    def click(selector):js(f"document.querySelector({json.dumps(selector)}).click()")
    def put(selector,value):js(f"(()=>{{const n=document.querySelector({json.dumps(selector)});n.value={json.dumps(value)};n.dispatchEvent(new Event('input',{{bubbles:true}}));}})()")
    def text_button(text,root='#modal-actions'):js(f"Array.from(document.querySelectorAll({json.dumps(root+' button')})).find(b=>b.textContent==={json.dumps(text)}).click()")
    p=session.profiles;p.set_endpoint('https://synthetic.example.test/v1');p.set_wire_mode('assistants')
    pid=p.save('合成自主助理','asst_autonomous');p.set_search_policy(p.snapshot(pid),{'tools':[SEARCH_TOOL]})
    other=p.save('合成分析助理','asst_analysis');p.set_workflow_capability(other,['analysis'],True,'synthetic-ui-fixture')
    binding=p.snapshot(pid)
    with session.store.connection() as db:db.execute('INSERT INTO skill_capabilities VALUES(?,?,?,?,?)',(pid,binding['revision'],'autonomy-ui-fixture',dumps(['planner','compose','assess','rag']),stamp()))
    calls=[];stuck=False
    def decision(action,who,role,instruction,inputs,reason):return dumps(dict(action=action,profile_id=who,role=role,instruction=instruction,inputs=inputs,reason=reason))
    def respond(messages,purpose,binding,context=None):
        prompt=messages[0]['content'];calls.append((purpose,binding['profile_id'],dict(context),prompt));sid=context['step_id']
        if context['run_id'].startswith('autonomy-probe:'):
            if sid=='decision_3':return decision('ask','','','請提供查詢對象',[],'缺少必要條件')
            return decision('compose',pid,'compose','只整理合成文字',['qa_action_1'] if sid=='decision_2' else [],'已有指定文字')
        if sid=='planner':return dumps({'message':'合成策略：先查資料再整理；實際順序由成果決定。','questions':[],'steps':[{'id':'search','title':'取得指定市場資料','kind':'assistant','role':'rag','profile_id':pid,'instruction':'只查指定台美市場及日期','inputs':[]},{'id':'compose','title':'整理成果','kind':'assistant','role':'compose','profile_id':pid,'instruction':'附日期與來源限制','inputs':['search']}]})
        if sid.startswith('qa_decide_'):
            data=json.loads(prompt.split('\n工作資料：',1)[1]);sources=data['sources'];content=dumps(sources)
            if stuck or not sources:return decision('search',pid,'rag','查指定台美市場當日資料',[],'需要先取得資料')
            if '日期已核對' not in content:return decision('search',pid,'rag','補查當日台美市場，排除已過期內容',list(sources),'第一批日期落後，需要調整關鍵字')
            if '分析已完成' not in content:return decision('delegate',other,'analysis','核對指定成果的資料日期與限制',list(sources),'資料已齊，交由核准分析助理核對')
            return decision('compose',pid,'compose','整理指定來源、日期與待確認事項',list(sources),'分析已完成，可以整理成果')
        data=json.loads(prompt.split('核准工作與輸入：',1)[1])
        if context.get('search_authorized'):
            from desktop_app.assistant_sessions import AssistantSessions
            from desktop_app.assistants_gateway import session_context
            key,rid,_,_=session_context(binding,purpose,context)
            # Explicit synthetic tool receipt, only inside the temporary smoke workspace.
            AssistantSessions(session.store.path.with_name('assistant-sessions.sqlite3')).save(key,{'thread_id':'synthetic-ui'},rid,
                {'state':'completed','tool_batches':[{'submit_state':'submitted','calls':[{'state':'completed','id':'synthetic-search'}]}]})
            if context.get('reserve_tool_round'):context['reserve_tool_round']('synthetic-search-return')
        if binding['profile_id']==other:text='分析已完成；來源日期與限制已列出，仍需人工核對。'
        elif '補查當日' in data.get('instruction',''):text='日期已核對：合成當日來源 https://example.test/current'
        elif '查指定台美' in data.get('instruction',''):text='第一批合成資料日期落後 https://example.test/old'
        else:text='合成自主成果：依來源整理完成，非即時資料。https://example.test/current'
        return dumps({'text':text,'facts':{}})
    with patch.object(p,'respond',side_effect=respond),patch('httpx.Client.send',side_effect=AssertionError('network_not_allowed')):
        api.call('appearance',{'theme':'dark'});js("document.body.dataset.theme='dark'")
        js("document.dispatchEvent(new CustomEvent('qa-navigate',{detail:'settings'}))")
        wait("Array.from(document.querySelectorAll('.activation-work-check')).some(n=>n.textContent.includes('合成自主助理'))")
        js("Array.from(document.querySelectorAll('.activation-work-check')).find(n=>n.textContent.includes('合成自主助理')).querySelectorAll('button')[1].click()")
        wait("!!document.getElementById('agent-probe-confirm')");assert not calls
        click('#agent-probe-confirm');wait("document.getElementById('modal-title').textContent==='工作能力檢查結果'")
        assert len(calls)==3 and all(c[0]=='workflow_plan' and not c[2].get('search_authorized') for c in calls),'autonomy_probe_bounds'
        assert session.skills.proof(pid,binding['revision'])['roles'].count('autonomous')==1
        wait("Array.from(document.querySelectorAll('#modal-actions button')).some(b=>b.textContent==='關閉')")
        text_button('關閉');wait("!document.getElementById('modal').open")
        click('#agent-jobs-nav');wait("!!document.getElementById('agent-job-search')")
        click('#agent-new');wait("!!document.getElementById('agent-create')")
        assert js("document.getElementById('agent-execution-mode').value")=='autonomous'
        js(f"document.getElementById('agent-profile').value={json.dumps(pid)};document.getElementById('agent-profile').dispatchEvent(new Event('change'));document.getElementById('agent-search').checked=true;Array.from(document.querySelectorAll('[data-team-id]')).find(n=>n.dataset.teamId==={json.dumps(other)}).checked=true")
        put('#agent-goal','整理當日台美市場資訊，核對日期及來源。')
        before=len(session.store.tasks());click('#agent-create');wait("!!document.getElementById('agent-preview')")
        click('#agent-preview');wait("!!document.getElementById('agent-confirm')")
        assert len(session.store.tasks())==before,'autonomy_preview_executed'
        assert js("document.querySelector('.agent-approval').textContent.includes('6 個動作') && document.querySelector('.agent-authority').textContent.includes('合成分析助理')")
        capture('autonomy-preview-dark.png')
        click('#agent-confirm');wait("!!document.getElementById('agent-save-skill')")
        job=session.agents.list()[0];assert job['task']['state']=='succeeded',job['task']['error']
        decisions=[r['output']['decision']['action'] for r in job['steps_status'] if (r.get('output') or {}).get('decision')]
        assert decisions==['search','search','delegate','compose'],decisions
        assert len(job['budget']['actions'])==4 and len(job['budget']['requests'])==10
        assert js("document.querySelectorAll('.agent-decision').length")==4
        assert js("(()=>{const n=document.querySelector('.agent-step-records');return Array.from(n.querySelectorAll('h4')).some(h=>h.textContent==='決策 1') && Array.from(n.querySelectorAll('h4')).some(h=>h.textContent==='動作 1') && n.textContent.includes('使用成果：動作 1') && !/qa_(decide|action)_\\d+/.test(n.textContent);})()"),'autonomy_readable_activity_labels'
        assert js("document.getElementById('agent-job-result').textContent.includes('第一批日期落後') && document.getElementById('agent-job-result').textContent.includes('合成分析助理')")
        assert any(c[1]==other for c in calls),'selected_assistant_not_used'
        for theme,size,name in [('dark',(1280,860),'autonomy-dark.png'),('light',(1050,700),'autonomy-light-small.png')]:
            api.call('appearance',{'theme':theme});js(f"document.body.dataset.theme={json.dumps(theme)}")
            window.resize(*size);time.sleep(.3);js("document.getElementById('toast').hidden=true;document.getElementById('agent-job-result').scrollIntoView({block:'start'})")
            capture(name);js("document.getElementById('agent-save-skill').scrollIntoView({block:'center'})")
            assert js("(()=>{const r=document.getElementById('agent-save-skill').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;})()")
        window.maximize();time.sleep(.3);capture('autonomy-maximized.png')
        report['checks'].append('autonomy_explicit_three_call_probe_default_mode_authority_preview_adaptive_search_synthetic_receipts_selected_delegate_compose_budget_and_themes')
        stuck=True;click('#agent-new');wait("!!document.getElementById('agent-create')")
        js(f"document.getElementById('agent-profile').value={json.dumps(pid)};document.getElementById('agent-profile').dispatchEvent(new Event('change'));document.getElementById('agent-search').checked=true")
        put('#agent-goal','合成無進展案例，保留當日來源限制');click('#agent-create');wait("!!document.getElementById('agent-preview')")
        click('#agent-preview');wait("!!document.getElementById('agent-confirm')");click('#agent-confirm');wait("!!document.getElementById('agent-restart-draft')")
        stopped=session.agents.list()[0];assert 'AGENT_NO_PROGRESS' in stopped['task']['error']
        before=len(calls);count=len(session.store.tasks());click('#agent-restart-draft');wait("!!document.getElementById('agent-create')")
        assert len(calls)==before and len(session.store.tasks())==count,'restart_implicitly_dispatched'
        assert js("document.getElementById('agent-execution-mode').value")=='autonomous'
        put('#agent-goal','補充明確條件後重新規劃');click('#agent-create');wait("!!document.getElementById('agent-preview')")
        revised=session.agents.list()[0];assert revised['prior_task_id']==stopped['task']['id'] and not revised['task']
        assert js("!!document.getElementById('agent-prior-task')")
        click('#agent-cancel');wait("!document.getElementById('agent-cancel')")
        assert len(session.store.tasks())==count
        report['checks'].append('autonomy_no_progress_preserves_partial_restart_only_draft_explicit_new_planning_source_link_and_cancel')
        # Advanced history routes autonomous jobs to the same authority-aware UI.
        before=len(calls)
        js("document.dispatchEvent(new CustomEvent('qa-navigate',{detail:'chat'}))")
        wait("Array.from(document.querySelectorAll('#recent-chats button')).some(b=>b.textContent==="+json.dumps(stopped['goal'])+")")
        text_button(stopped['goal'],'#recent-chats')
        wait("Array.from(document.querySelectorAll('#workflow-panel button')).some(b=>b.textContent==='開啟自主工作')")
        assert js("!document.getElementById('workflow-panel').textContent.includes('重試未完成步驟') && !document.getElementById('workflow-panel').textContent.includes('檢視並確認')")
        text_button('開啟自主工作','#workflow-panel');wait("!!document.getElementById('agent-restart-draft') && !document.getElementById('dialogue-page').hidden")
        assert len(calls)==before and len(session.store.tasks())==count
        report['checks'].append('autonomy_advanced_history_routes_to_authority_ui_without_fixed_plan_approval_or_retry')


def skills_journey(session, api, window, capture, wait_script, report, tmp, company_mock):
    expected_chat_draft=window.evaluate_js("document.getElementById('dialogue-input').value")
    # Skills use one assistant, explicit local saves and a separate execution gate.
    skill_tasks_before={t['id'] for t in session.store.tasks()}
    skill_company_before=len(company_mock.runs)
    window.evaluate_js("document.getElementById('dialogue-skill').click()")
    wait_script("!!document.getElementById('skill-new')")
    window.evaluate_js("document.getElementById('skill-example').click()")
    wait_script("!!document.getElementById('skill-name')")
    window.evaluate_js("document.getElementById('skill-name').value='合成 Skill 驗證';document.getElementById('skill-name').dispatchEvent(new Event('input'));document.getElementById('skill-generator-profile').value='demo';document.getElementById('skill-generate-request').value='整理合成工作內容，不要編造資料';document.getElementById('skill-generate').click()")
    wait_script("!!document.getElementById('skill-accept-generated')")
    window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='保留原草稿').click()")
    assert window.evaluate_js("document.getElementById('skill-name').value")=='合成 Skill 驗證','skill_generate_overwrote_draft'
    window.evaluate_js("document.getElementById('skill-save-preview').click()")
    wait_script("!!document.getElementById('skill-save-confirm')")
    assert not session.skills.list(),'skill_preview_saved'
    window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='返回修改').click()")
    assert not session.skills.list(),'skill_cancel_saved'
    window.evaluate_js("document.getElementById('skill-save-preview').click()")
    wait_script("!!document.getElementById('skill-save-confirm')")
    window.evaluate_js("document.getElementById('skill-save-confirm').click();document.getElementById('skill-save-confirm')?.click()")
    wait_script("!!document.querySelector('.skill-card')")
    assert len(session.skills.list())==1,'skill_save_duplicate'
    assert {t['id'] for t in session.store.tasks()}==skill_tasks_before,'skill_definition_dispatched'
    record=session.skills.list()[0]
    # Additional typed fields are synthetic fixture data, consumed by real controls.
    from desktop_app.skills import FIELDS as SKILL_FIELDS
    definition={k:record[k] for k in SKILL_FIELDS}
    definition['fields'] += [{'id':'confirmed','text':'已確認測試資料','type':'boolean','options':[]},{'id':'length','text':'成果長度','type':'single','options':['精簡','完整']}]
    p=session.skills.save_preview(definition,record['id'],record['revision']);record=session.skills.save_confirm(p['token'])
    window.evaluate_js("document.getElementById('skill-new').click()")
    wait_script("!!document.getElementById('skill-name')")
    assert window.evaluate_js("document.getElementById('skill-name').value===''&&document.getElementById('skill-instructions').value===''&&document.querySelectorAll('.skill-field-card').length===0"),'skill_new_not_blank'
    window.evaluate_js("Array.from(document.querySelectorAll('#skill-actions button')).find(b=>b.textContent==='返回我的 Skills').click()")
    wait_script("document.getElementById('modal').open")
    window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='放棄未保存編輯並繼續').click()")
    wait_script("!!document.querySelector('.skill-card')")
    window.evaluate_js("Array.from(document.querySelectorAll('.skill-card button')).find(b=>b.textContent==='使用 Skill').click()")
    wait_script("!!document.getElementById('skill-start')")
    window.evaluate_js("document.getElementById('skill-profile').value='demo';document.getElementById('skill-probe').click()")
    wait_script("document.getElementById('modal').open&&!!document.getElementById('skill-probe-confirm')")
    window.evaluate_js("document.getElementById('skill-probe-confirm').click()")
    wait_script("document.getElementById('modal-title').textContent==='能力驗證結果'")
    assert window.evaluate_js("document.getElementById('modal-body').textContent.includes('未驗證真實助理')"),'skill_demo_probe_mislabeled'
    window.evaluate_js("document.getElementById('modal-close').click()")
    window.evaluate_js("document.getElementById('skill-profile').value='demo';document.getElementById('skill-start').click()")
    wait_script("!!document.getElementById('skill-discuss')")
    assert {t['id'] for t in session.store.tasks()}==skill_tasks_before,'skill_start_dispatched'
    window.evaluate_js("document.getElementById('skill-discuss').click()")
    wait_script("!!document.getElementById('skill-discuss')&&!document.getElementById('skill-discuss').disabled")
    assert not session.skills.runs()[0]['steps'],'skill_missing_fields_planned'
    window.evaluate_js("document.getElementById('skill-value-markets-0').checked=true;document.getElementById('skill-value-markets-2').checked=true;document.getElementById('skill-value-sources').value='只用合成資料，未連即時來源';document.getElementById('skill-value-confirmed').value='false';document.getElementById('skill-value-length').value='精簡';document.getElementById('skill-value-sources').dispatchEvent(new Event('input'))")
    for theme in ('dark','light'):
        api.call('appearance',{'theme':theme});time.sleep(1.7)
        assert window.evaluate_js("document.getElementById('skill-value-confirmed').value==='false'&&document.getElementById('skill-value-sources').value==='只用合成資料，未連即時來源'"),'skill_theme_lost_fields'
        capture('skills-input-'+theme+'.png')
    window.evaluate_js("document.getElementById('skill-discuss').click()")
    wait_script("!!document.getElementById('skill-run-preview')&&!document.getElementById('skill-run-preview').disabled")
    assert {t['id'] for t in session.store.tasks()}==skill_tasks_before,'skill_planning_dispatched'
    assert session.skills.runs()[0]['values']['confirmed'] is False,'skill_false_answer_lost'
    window.evaluate_js("document.getElementById('skill-edit-steps').click()")
    wait_script("!!document.getElementById('skill-steps-save')")
    window.evaluate_js("document.querySelector('.skill-step-editor input').value='核對合成來源';document.querySelector('.skill-step-editor input').dispatchEvent(new Event('input'));document.getElementById('skill-steps-save').click()")
    wait_script("!!document.getElementById('skill-run-preview')&&!document.getElementById('skill-run-preview').disabled")
    window.resize(1050,700);time.sleep(.2)
    window.evaluate_js("document.getElementById('skill-run-preview').scrollIntoView({block:'center'})")
    capture('skills-plan-small.png')
    window.evaluate_js("document.getElementById('skill-run-preview').click()")
    wait_script("document.getElementById('modal').open&&!!document.getElementById('skill-confirm')")
    assert window.evaluate_js("document.getElementById('modal-body').textContent.includes('目的助理')&&document.getElementById('modal-body').textContent.includes('只用合成資料，未連即時來源')&&document.getElementById('modal-body').textContent.includes('輸入來源')"),'skill_preview_missing_transfer_scope'
    window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='取消這次預覽').click()")
    wait_script("!document.getElementById('modal').open")
    assert {t['id'] for t in session.store.tasks()}==skill_tasks_before,'skill_cancel_plan_dispatched'
    window.evaluate_js("document.getElementById('skill-run-preview').click()")
    wait_script("document.getElementById('modal').open&&!!document.getElementById('skill-confirm')")
    window.evaluate_js("document.getElementById('skill-confirm').click();document.getElementById('skill-confirm')?.click()")
    wait_script("!!document.getElementById('skill-schedule-preview')")
    assert len({t['id'] for t in session.store.tasks()}-skill_tasks_before)==1,'skill_confirm_duplicate'
    assert len(company_mock.runs)==skill_company_before,'demo_skill_called_company'
    assert window.evaluate_js("document.getElementById('dialogue-input').value")==expected_chat_draft,'skill_lost_chat_draft'
    window.evaluate_js("document.getElementById('skill-schedule-preview').scrollIntoView({block:'center'})")
    assert window.evaluate_js("(()=>{const r=document.getElementById('skill-schedule-preview').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;})()"),'skill_result_action_unreachable'
    capture('skills-result-small.png');window.resize(1280,860)
    report['checks'].append('skills_definition_draft_preservation_typed_questions_plan_edit_cancel_and_single_confirmation_zero_external_dispatch')
    schedule_before={s['id'] for s in session.store.schedules()}
    window.evaluate_js("document.getElementById('skill-schedule-preview').click()")
    wait_script("!!document.getElementById('skill-schedule-confirm')")
    window.evaluate_js("document.getElementById('skill-schedule-confirm').click()")
    wait_script("!!document.querySelector('.skill-modal-error')")
    assert {s['id'] for s in session.store.schedules()}==schedule_before,'skill_schedule_without_consent'
    window.evaluate_js("document.getElementById('skill-schedule-reviewed').checked=true;document.getElementById('skill-schedule-consent').checked=true;document.getElementById('skill-schedule-confirm').click()")
    wait_script("!document.getElementById('modal').open&&document.getElementById('skill-result').textContent.includes('每日工作已啟用')")
    window.evaluate_js("Array.from(document.querySelectorAll('#skill-result button')).find(b=>b.textContent==='暫停每日工作').click()")
    wait_script("document.getElementById('skill-result').textContent.includes('每日工作已暫停')")
    window.evaluate_js("Array.from(document.querySelectorAll('#skill-actions button')).find(b=>b.textContent==='返回我的 Skills').click()")
    wait_script("!!document.querySelector('.skill-card')")
    # Exercise the actual bridge file format with a synthetic native-dialog selection.
    from types import SimpleNamespace
    export_path=Path(tmp)/'synthetic-skill.md'
    api._window=SimpleNamespace(create_file_dialog=lambda *a,**k:[str(export_path)])
    try:
        window.evaluate_js("Array.from(document.querySelectorAll('.skill-card button')).find(b=>b.textContent==='匯出 Markdown').click()")
        wait_script("document.getElementById('skill-notice').textContent.includes('已匯出')")
        assert export_path.exists() and 'default_profile_id' not in export_path.read_text('utf-8'),'skill_export_binding_leak'
        window.evaluate_js("Array.from(document.querySelectorAll('#skill-actions button')).find(b=>b.textContent==='匯入 Markdown').click()")
        wait_script("!!document.getElementById('skill-name')")
        assert window.evaluate_js("document.getElementById('skill-default-profile').value")== '','skill_import_bound_assistant'
        assert len(session.skills.list())==1,'skill_import_saved_automatically'
        window.evaluate_js("Array.from(document.querySelectorAll('#skill-actions button')).find(b=>b.textContent==='返回我的 Skills').click()")
        wait_script("document.getElementById('modal').open")
        window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='放棄未保存編輯並繼續').click()")
        wait_script("!!document.querySelector('.skill-card')")
    finally:api._window=window
    window.evaluate_js("Array.from(document.querySelectorAll('.skill-card button')).find(b=>b.textContent==='複製').click()")
    wait_script("!!document.getElementById('skill-name')")
    assert len(session.skills.list())==1,'skill_copy_saved_automatically'
    window.evaluate_js("document.getElementById('skill-name').value='合成 Skill 副本';document.getElementById('skill-name').dispatchEvent(new Event('input'));document.getElementById('skill-save-preview').click()")
    wait_script("document.getElementById('modal').open&&!!document.getElementById('skill-save-confirm')")
    window.evaluate_js("document.getElementById('skill-save-confirm').click()")
    wait_script("document.querySelectorAll('.skill-card').length===2")
    window.evaluate_js("window.skillCopyCard=Array.from(document.querySelectorAll('.skill-card')).find(c=>c.querySelector('h3').textContent==='合成 Skill 副本');skillCopyCard.querySelector('details').open=true;Array.from(skillCopyCard.querySelectorAll('button')).find(b=>b.textContent==='刪除 Skill').click()")
    wait_script("document.getElementById('modal').open&&document.getElementById('modal-title').textContent==='刪除 Skill'")
    window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='取消').click()")
    assert len(session.skills.list())==2,'skill_delete_cancel_removed'
    window.evaluate_js("Array.from(skillCopyCard.querySelectorAll('button')).find(b=>b.textContent==='刪除 Skill').click()")
    wait_script("document.getElementById('modal').open")
    window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='確認刪除').click()")
    wait_script("document.querySelectorAll('.skill-card').length===1")
    window.evaluate_js("document.querySelector('.skill-card details').open=true;Array.from(document.querySelectorAll('.skill-card button')).find(b=>b.textContent==='停用').click()")
    wait_script("document.getElementById('modal-title').textContent==='變更 Skill 狀態'")
    window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='確認停用').click()")
    wait_script("!!document.querySelector('.skill-card')&&document.querySelector('.skill-card').textContent.includes('已停用')")
    assert not session.skills.list()[0]['enabled'],'skill_disable_not_saved'
    assert not session.skills.runs()[0]['schedule']['enabled'],'skill_disable_schedule_active'
    window.evaluate_js("document.querySelector('[data-page=help]').click()")
    wait_script("Array.from(document.querySelectorAll('#page-content .card')).some(c=>c.textContent.includes('Skills 使用說明'))")
    window.evaluate_js("Array.from(document.querySelectorAll('#page-content .card')).find(c=>c.textContent.includes('Skills 使用說明')).querySelector('button').click()")
    wait_script("document.getElementById('modal').open&&document.getElementById('modal-title').textContent==='Skills 使用說明'")
    assert window.evaluate_js("document.getElementById('modal-body').textContent.includes('Skill')&&document.getElementById('modal-body').textContent.length>300"),'skill_offline_manual_empty'
    window.evaluate_js("document.getElementById('modal-close').click()")
    report['checks'].append('skills_explicit_daily_consent_pause_markdown_roundtrip_and_disable_preserves_history')


def v1_journey(session,api,window,capture,wait,report):
    def js(script):return window.evaluate_js(script)
    def click(text,root='#modal-actions'):
        js("Array.from(document.querySelectorAll("+json.dumps(root+' button')+")).find(b=>b.textContent==="+json.dumps(text)+").click()")
    def input_value(selector,value):
        js("window.f=document.querySelector("+json.dumps(selector)+");f.value="+json.dumps(value)+";f.dispatchEvent(new Event('input',{bubbles:true}))")
    def field(label,value):
        js("window.f=Array.from(document.querySelectorAll('#modal-body .field')).find(r=>r.querySelector('label').textContent==="+json.dumps(label)+").querySelector('input,textarea,select');f.value="+json.dumps(value)+";f.dispatchEvent(new Event('input',{bubbles:true}))")
    def modal_actions_reachable():
        assert js("Array.from(document.querySelectorAll('#modal-actions button')).every(b=>{const r=b.getBoundingClientRect();return r.width>0&&r.height>0&&r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth})"),'modal_actions_outside_viewport'
    source='合成工作筆記：所有報告使用繁體中文，數字須附來源，不要編造期限。'
    input_value('#dialogue-input',source);js("document.getElementById('dialogue-send').click();document.getElementById('dialogue-send').click()")
    wait("document.querySelectorAll('#dialogue-messages .message').length===2&&!document.getElementById('dialogue-send').disabled")
    original=js('window.qaDialogueViewSnapshot().id')
    automatic=next(row for row in session.dialogue.history() if row['id']==original)
    assert automatic['title_source']=='auto' and automatic['title']!='新對話' and source.startswith(automatic['title'].rstrip('…')),'first_message_local_title_missing'
    js("window.r=document.createRange();r.selectNodeContents(document.querySelector('#dialogue-messages .message-body'));window.getSelection().removeAllRanges();window.getSelection().addRange(r);document.dispatchEvent(new Event('selectionchange'));document.getElementById('dialogue-remember').click()")
    wait("document.getElementById('modal-title').textContent==='記住這件事'")
    field('標題','合成報告偏好');click('預覽保存')
    wait("document.getElementById('modal-title').textContent==='確認保存這份記憶'")
    assert not api.call('memory_list',{})['data'],'memory_preview_saved'
    click('取消');assert not api.call('memory_list',{})['data'],'memory_cancel_saved'
    js("document.getElementById('dialogue-remember').click()")
    wait("document.getElementById('modal-title').textContent==='記住這件事'")
    field('標題','合成報告偏好');click('預覽保存')
    wait("document.getElementById('modal-title').textContent==='確認保存這份記憶'");click('確認保存')
    wait("!document.getElementById('modal').open")
    memories=api.call('memory_list',{})['data'];assert len(memories)==1,'memory_not_saved'
    mid=memories[0]['id'];assert memories[0]['text']==source,'selection_truncated'
    input_value('#dialogue-input','原對話尚未送出的草稿')
    js("document.getElementById('new-chat').click()")
    wait("document.getElementById('modal-title').textContent==='新對話將使用這些記憶'&&document.getElementById('modal').open")
    assert session.dialogue.state(original)['draft_text']=='原對話尚未送出的草稿','main_draft_not_saved'
    js("document.getElementById('chat-use-memory').checked=false");click('開始新對話')
    wait("!document.getElementById('modal').open&&document.getElementById('dialogue-input').value===''")
    no_memory=js('window.qaDialogueViewSnapshot().id');assert not session.dialogue.state(no_memory)['memory_snapshot'],'memory_optout_ignored'
    js("document.querySelector('[data-dialogue-id=\""+original+"\"] .recent-item').click()")
    wait("document.getElementById('dialogue-input').value==='原對話尚未送出的草稿'")
    js("document.querySelector('[data-dialogue-id=\""+original+"\"] .icon-button').click()")
    wait("document.getElementById('modal-title').textContent==='管理這段對話'")
    field('對話名稱','合成置頂專案');click('保存名稱');wait("!document.getElementById('modal').open")
    js("document.querySelector('[data-dialogue-id=\""+original+"\"] .icon-button').click()")
    wait("document.getElementById('modal').open");click('置頂');wait("!document.getElementById('modal').open")
    assert session.dialogue.state(original)['pinned'],'pin_not_saved'
    input_value('#recent-search','合成置頂');assert js("document.querySelectorAll('#recent-chats .recent-row').length")==1,'recent_search_wrong'
    input_value('#recent-search','')
    # Sidebar organization is entirely local and never changes the selected
    # assistant, conversation contents, pending draft or remote thread.
    before_folder=session.dialogue.state(original)
    js("document.getElementById('new-dialogue-folder').click()")
    wait("document.getElementById('modal-title').textContent==='新增資料夾'")
    field('資料夾名稱','合成日常工作');click('建立資料夾');wait("!document.getElementById('modal').open")
    folder=api.call('dialogue_folders',{})['data'][0];fid=folder['id']
    js("document.querySelector('[data-dialogue-id=\""+original+"\"] .icon-button').click()")
    wait("document.getElementById('modal').open");field('資料夾',fid);click('移至選定資料夾','#modal-body')
    wait("!document.getElementById('modal').open&&!!document.querySelector('[data-folder-id=\""+fid+"\"] [data-dialogue-id=\""+original+"\"]')")
    assert session.dialogue.state(original)['folder_id']==fid,'folder_move_not_saved'
    js("document.querySelector('[data-folder-id=\""+fid+"\"] .folder-toggle').click()")
    wait("document.querySelector('[data-folder-id=\""+fid+"\"] .folder-content').hidden")
    assert api.call('dialogue_folders',{})['data'][0]['collapsed'],'folder_collapse_not_saved'
    js("document.dispatchEvent(new Event('qa-dialogue-enter'))")
    wait("document.querySelector('[data-folder-id=\""+fid+"\"] .folder-toggle').getAttribute('aria-expanded')==='false'")
    input_value('#recent-search','合成置頂')
    assert not js("document.querySelector('[data-folder-id=\""+fid+"\"] .folder-content').hidden"),'folder_search_not_expanded'
    input_value('#recent-search','')
    assert js("document.querySelector('[data-folder-id=\""+fid+"\"] .folder-content').hidden"),'search_overwrote_saved_collapse'
    js("document.getElementById('recent-toggle').click()")
    wait("document.getElementById('recent-chats').hidden")
    wait("!document.getElementById('recent-toggle').disabled")
    preference=api.call('dialogue_recent_preference',{})
    assert preference['data']['collapsed'],'recent_collapse_not_saved'
    js("document.getElementById('recent-toggle').click()")
    wait("!document.getElementById('recent-chats').hidden")
    js("document.querySelector('[data-folder-id=\""+fid+"\"] .folder-heading .icon-button').click()")
    wait("document.getElementById('modal-title').textContent==='管理資料夾'")
    field('資料夾名稱','合成已改名工作');click('保存資料夾名稱');wait("!document.getElementById('modal').open")
    assert api.call('dialogue_folders',{})['data'][0]['name']=='合成已改名工作','folder_rename_not_saved'
    capture('v1-folders-dark.png')
    window.resize(1050,700);time.sleep(.3)
    js("document.querySelector('[data-folder-id=\""+fid+"\"] .folder-heading .icon-button').click()")
    wait("document.getElementById('modal-title').textContent==='管理資料夾'")
    assert js("document.querySelector('#modal-body .field input').maxLength")==60,'folder_name_limit_drift'
    modal_actions_reachable();capture('v1-folders-small.png');click('刪除資料夾')
    wait("document.getElementById('modal-title').textContent==='刪除資料夾 · 對話保留'");click('取消')
    assert api.call('dialogue_folders',{})['data'],'folder_delete_cancel_deleted'
    js("document.querySelector('[data-folder-id=\""+fid+"\"] .folder-heading .icon-button').click()")
    wait("document.getElementById('modal-title').textContent==='管理資料夾'");click('刪除資料夾')
    wait("document.getElementById('modal-title').textContent==='刪除資料夾 · 對話保留'");click('確認刪除資料夾');wait("!document.getElementById('modal').open")
    after_folder=session.dialogue.state(original)
    assert not after_folder['folder_id'] and not api.call('dialogue_folders',{})['data'],'folder_delete_did_not_unfile'
    assert all(after_folder[k]==before_folder[k] for k in ('messages','draft_text','assistant_id','memory_snapshot')),'folder_changed_conversation'
    assert js("document.getElementById('dialogue-input').value")=='原對話尚未送出的草稿','folder_lost_visible_draft'
    js("document.querySelector('[data-dialogue-id=\""+original+"\"] .icon-button').click()")
    wait("document.getElementById('modal').open");modal_actions_reachable();click('恢復自動命名');wait("!document.getElementById('modal').open")
    assert next(row for row in session.dialogue.history() if row['id']==original)['title_source']=='auto','restore_auto_title_failed'
    window.resize(1280,860)
    report['checks'].append('local_auto_title_folder_create_move_collapse_reload_search_rename_delete_keeps_conversation_recent_preference')
    js("document.getElementById('new-chat').click()")
    wait("document.getElementById('modal').open&&!!document.getElementById('chat-use-memory')");click('開始新對話')
    wait("!document.getElementById('modal').open&&document.getElementById('dialogue-memory-status').textContent.includes('1 份記憶')")
    fixed=js('window.qaDialogueViewSnapshot().id');assert session.dialogue.state(fixed)['memory_snapshot'][0]['text']==source,'snapshot_wrong'
    report['checks'].append('main_dialogue_selected_memory_preview_cancel_confirm_newchat_optout_fixed_snapshot_recent_search_rename_pin_draft_restore')
    # Selected memories enter the visible approved method only; default is none.
    skill_definition={'name':'合成記憶報告','purpose':'整理測試筆記','instructions':'只整理提供內容。','output_format':'列出重點與限制。','fields':[],'search':False,'default_profile_id':'demo'}
    p=api.call('skill_save_preview',{'data':skill_definition});assert p['ok'],'skill_memory_fixture_preview'
    assert api.call('skill_save_confirm',{'token':p['data']['token']})['ok'],'skill_memory_fixture_save'
    js("document.querySelector('[data-page=skills]').click()")
    wait("!!document.querySelector('.skill-card')")
    click('使用 Skill','.skill-card');wait("!!document.querySelector('.memory-choices input[type=checkbox]')")
    assert not js("document.querySelector('.memory-choices input').checked"),'skill_memory_auto_selected'
    js("document.querySelector('.memory-choices input').checked=true;document.querySelector('.memory-choices input').dispatchEvent(new Event('change'));document.getElementById('skill-start').click()")
    wait("!!document.getElementById('skill-discuss')")
    w=session.skills.runs()[0];assert source in session.skills.state(w['id'])['skill']['instructions'],'skill_memory_not_visible_method'
    assert not session.store.tasks(),'skill_memory_started_work'
    report['checks'].append('skill_memory_default_none_explicit_selection_visible_method_snapshot_zero_execution')
    # Explicit continuation: an isolated demo summary call, then an editable local preview.
    js("document.querySelector('[data-dialogue-id=\""+original+"\"] .recent-item').click()")
    wait("document.getElementById('dialogue-input').value==='原對話尚未送出的草稿'")
    js("window.r=document.createRange();r.selectNodeContents(document.querySelector('#dialogue-messages .message-body'));window.getSelection().removeAllRanges();window.getSelection().addRange(r);document.dispatchEvent(new Event('selectionchange'));document.getElementById('dialogue-continue').click()")
    wait("document.getElementById('modal-title').textContent==='整理後接續 · 原對話完整保留'")
    click('請助理整理選取內容（一次請求）')
    wait("Array.from(document.querySelectorAll('#modal-body .field')).find(r=>r.querySelector('label').textContent==='可編輯的接續摘要').querySelector('textarea').value.length>0")
    field('可編輯的接續摘要','合成接續摘要，原文與限制須保留。');click('預覽接續草稿')
    wait("document.getElementById('modal-title').textContent==='確認建立接續對話'")
    before=len(session.dialogue.history());click('建立接續對話')
    wait("!document.getElementById('modal').open&&document.getElementById('dialogue-input').value==='合成接續摘要，原文與限制須保留。'")
    continued=js('window.qaDialogueViewSnapshot().id');t=session.dialogue.state(continued)
    assert len(session.dialogue.history())==before+1 and not t['messages'] and not t['memory_snapshot'] and t['source_thread_id']==original,'continuation_not_inert'
    assert len(session.dialogue.state(original)['messages'])==2,'continuation_changed_original'
    report['checks'].append('explicit_summary_editable_continuation_preview_newdraft_original_and_source_retained_no_autosend')
    js("document.querySelector('[data-page=memories]').click()")
    wait("!!document.querySelector('[data-memory-id]')")
    for theme in ('dark','light'):
        api.call('appearance',{'theme':theme});time.sleep(1.7);capture('v1-memories-'+theme+'.png')
    window.resize(1050,700);time.sleep(.3);capture('v1-memories-small.png')
    assert js("document.getElementById('memories-page').scrollWidth<=document.getElementById('memories-page').clientWidth+2"),'memory_small_overflow'
    click('停用','#memory-content');wait("document.getElementById('modal').open");click('確認停用');wait("!document.getElementById('modal').open")
    assert not api.call('memory_list',{})['data'][0]['enabled'],'memory_disable_failed'
    assert session.dialogue.state(fixed)['memory_snapshot'],'disable_changed_snapshot'
    click('刪除','#memory-content');wait("document.getElementById('modal').open");click('取消');assert api.call('memory_list',{})['data'],'delete_cancel_deleted'
    click('刪除','#memory-content');wait("document.getElementById('modal').open");click('確認刪除');wait("!document.getElementById('modal').open")
    assert not api.call('memory_list',{})['data'] and session.dialogue.state(fixed)['memory_snapshot'],'delete_retracted_snapshot'
    report['checks'].append('memory_manage_disable_delete_cancel_preserves_existing_snapshot_dark_light_small')
    # No live endpoint, key or network. Setup works without deployment defaults.
    js("document.querySelector('[data-page=settings]').click()")
    wait("document.getElementById('activation-settings').textContent.includes('啟用你的助理')")
    assert js("document.querySelector('#page-content details').open===false"),'deployment_controls_not_collapsed'
    assert not session.store.tasks(),'continuity_dispatched_work'
    capture('v1-settings-small.png')
    report['checks'].append('optional_deployment_setup_entry_no_task_dispatch')
    # UI contract fixture only: no keyring, deployment mutation or model transport.
    from unittest.mock import patch
    activation_calls=[]
    def fake_save(assistant_id,api_key,endpoint=None,confirm_endpoint_change=False):
        activation_calls.append(('save',endpoint,confirm_endpoint_change));assert assistant_id=='synthetic-assistant' and api_key=='synthetic-not-a-secret'
        return {'saved':True,'profile_id':'synthetic-profile','assistant_id':'demo-general'}
    def fake_test(profile_id,consent):
        activation_calls.append('test');assert profile_id=='synthetic-profile' and consent is True
        return {'passed':True,'checks':[{'name':'two_turns','status':'synthetic_passed'}],'message':'合成介面測試，並非真實助理驗收。','assistant_id':'demo-general'}
    with patch.object(session.activation,'status',return_value={'available':True,'configured':False,'needed':False,'endpoint':'','wire_mode':'unconfigured','chat_profiles':[],'message':''}),patch.object(session.activation,'save',side_effect=fake_save),patch.object(session.activation,'test',side_effect=fake_test):
        js("document.dispatchEvent(new Event('qa-activation-open'))")
        wait("!!document.getElementById('activation-assistant-id')&&document.getElementById('modal').open")
        assert js("Array.from(document.querySelectorAll('#modal-body .field label')).map(e=>e.textContent)")==['Endpoint','Assistant ID','API key'],'activation_not_three_fields'
        input_value('#modal-body #activation-endpoint','https://synthetic.invalid/api/assts/v1')
        input_value('#modal-body #activation-assistant-id','synthetic-assistant');input_value('#modal-body #activation-api-key','synthetic-not-a-secret')
        click('測試並開始使用');time.sleep(.2);assert not activation_calls,'activation_no_consent_dispatched'
        js("document.querySelector('#modal-body #activation-consent').checked=true");click('測試並開始使用')
        wait("document.querySelector('#modal-body .activation-result').textContent.includes('synthetic_passed')")
        assert activation_calls==[('save','https://synthetic.invalid/api/assts/v1',False),'test'],'activation_duplicate_or_missing'
        assert js("document.querySelector('#modal-body #activation-api-key').value")==''
        capture('v1-activation-small.png')
        # Same form now has an existing destination. Editing it requires human
        # confirmation before any backend save; cancelling must leave it intact.
        input_value('#modal-body #activation-endpoint','https://other-synthetic.invalid/api/assts/v1')
        input_value('#modal-body #activation-api-key','synthetic-not-a-secret')
        click('只保存，不測試');wait("document.querySelector('#modal-body .activation-result').textContent.includes('確認更換連線')")
        assert len(activation_calls)==2,'endpoint_changed_before_confirmation'
        click('取消更換','#modal-body');wait("!document.querySelector('#modal-body #activation-endpoint').disabled")
        assert len(activation_calls)==2,'cancel_endpoint_dispatched'
        click('只保存，不測試');wait("document.querySelector('#modal-body .activation-result').textContent.includes('確認更換連線')")
        click('確認更換連線','#modal-body');wait("document.querySelector('#modal-body .activation-result').textContent.includes('已保存')")
        assert activation_calls[-1]==('save','https://other-synthetic.invalid/api/assts/v1',True) and len(activation_calls)==3,'endpoint_confirmation_not_bound'
        click('稍後設定')
    report['checks'].append('three_field_activation_explicit_consent_endpoint_change_cancel_confirm_key_cleared_no_real_credentials')
    window.resize(1280,860);window.maximize();time.sleep(.3)
    js("document.querySelector('[data-page=dialogue]').click()")
    wait("!document.getElementById('dialogue-page').hidden")
    capture('v1-dialogue-maximized.png')
    report['not_tested']=['company_api','real_two_turn_activation','AD','human_usability','physical_IME','clipboard']


def main():
    destination=Path(__file__).resolve().parents[1]/'artifacts'/'web-smoke'
    destination.mkdir(parents=True,exist_ok=True)
    skills_only='--skills-only' in sys.argv
    v1_only='--v1-only' in sys.argv
    agent_only='--agent-only' in sys.argv
    agent_followup_only='--agent-followup-only' in sys.argv
    autonomy_only='--autonomy-only' in sys.argv
    workspace_only='--workspace-only' in sys.argv
    report={'status':'failed','scope':'workspace' if workspace_only else 'autonomy' if autonomy_only else 'agent-followup' if agent_followup_only else 'agent' if agent_only else 'v1' if v1_only else 'skills' if skills_only else 'full','checks':[]}
    with tempfile.TemporaryDirectory() as tmp:
        from desktop_app import about
        publisher_root=about.ROOT;about.ROOT=Path(tmp)
        (Path(tmp)/'publisher.json').write_text(json.dumps({'author':{'name':'合成作者','employee_id':'SYNTHETIC-001','phone':'SYNTHETIC-EXT'}}),encoding='utf-8')
        session=WebSession(directory=tmp)
        api=WebBridge(session)
        window=webview.create_window('QA agent · 合成介面驗證',html=application_html(),js_api=api,width=1280,height=860,text_select=True)
        api._window=window
        def inspect():
            try:
                for _ in range(100):
                    ready=window.evaluate_js("document.getElementById('dialogue-status') && document.getElementById('dialogue-status').textContent.includes('示範模式')")
                    if ready:break
                    time.sleep(.2)
                if not ready:raise AssertionError('bridge_not_ready')
                from desktop_app.web_chrome import seal_navigation
                seal_navigation(window)
                report['checks'].append('bridge_ready')
                # Fresh ordinary workspaces offer optional setup; this offline
                # journey explicitly defers it, then tests setup below with fixtures.
                time.sleep(.4)
                window.evaluate_js("(() => {const m=document.getElementById('modal');if(m.open&&m.textContent.includes('三個欄位開始')){const b=Array.from(document.querySelectorAll('#modal-actions button')).find(e=>e.textContent==='稍後設定');if(b)b.click();}})()")
                from System import Action
                from System.IO import FileStream, FileMode
                from Microsoft.Web.WebView2.Core import CoreWebView2CapturePreviewImageFormat
                def capture(name):
                    stream=FileStream(str(destination/name),FileMode.Create)
                    pending=[]
                    try:
                        def start():pending.append(window.native.webview.CoreWebView2.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png,stream))
                        window.native.Invoke(Action(start))
                        if not pending[0].Wait(10000):raise AssertionError('capture_timeout')
                    finally:stream.Dispose()
                if workspace_only:
                    from workspace_smoke import journey
                    def wait_workspace(script):
                        for _ in range(220):
                            if window.evaluate_js(script):return
                            time.sleep(.1)
                        raise AssertionError('workspace_wait_timeout: '+script)
                    journey(session,api,window,capture,wait_workspace,report)
                    report['status']='passed'
                    return
                if agent_only or agent_followup_only or autonomy_only:
                    def wait_agent(script):
                        for _ in range(220):
                            if window.evaluate_js(script):return
                            time.sleep(.1)
                        raise AssertionError('agent_wait_timeout: '+script)
                    (autonomous_journey if autonomy_only else agent_followup_journey if agent_followup_only else agent_journey)(session,api,window,capture,wait_agent,report)
                    if agent_only:autonomous_journey(session,api,window,capture,wait_agent,report)
                    report['status']='passed'
                    return
                if v1_only:
                    def wait_v1(script):
                        for _ in range(160):
                            if window.evaluate_js(script):return
                            time.sleep(.1)
                        raise AssertionError('v1_wait_timeout: '+script)
                    v1_journey(session,api,window,capture,wait_v1,report)
                    report['status']='passed'
                    return
                if skills_only:
                    def wait_skills(script):
                        for _ in range(100):
                            if window.evaluate_js(script):return
                            time.sleep(.1)
                        raise AssertionError('skills_wait_timeout')
                    from types import SimpleNamespace
                    window.evaluate_js("document.getElementById('dialogue-input').value='合成未送出草稿'")
                    skills_journey(session,api,window,capture,wait_skills,report,tmp,SimpleNamespace(runs=[]))
                    report['status']='passed'
                    return
                time.sleep(.4);capture('dark.png')
                window.evaluate_js("document.getElementById('author-toggle').click()")
                for _ in range(80):
                    if window.evaluate_js("document.getElementById('author-content').textContent.includes('SYNTHETIC-EXT')"):break
                    time.sleep(.05)
                assert window.evaluate_js("document.getElementById('author-content').textContent.includes('合成作者')"),'author_data_missing'
                assert window.evaluate_js("document.getElementById('author-toggle').getAttribute('aria-expanded')==='true'"),'author_not_open'
                assert not session.store.tasks(),'author_dispatched'
                capture('author-dark.png')
                window.evaluate_js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
                assert window.evaluate_js("document.getElementById('author-popover').hidden && document.activeElement.id==='author-toggle'"),'author_escape_focus'
                window.evaluate_js("document.getElementById('author-toggle').click()")
                window.evaluate_js("document.getElementById('dialogue-input').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))")
                time.sleep(.1)
                assert window.evaluate_js("document.getElementById('author-popover').hidden"),'author_late_reply_reopened'
                report['checks'].append('author_popover_readonly_escape_outside_and_late_reply_fence')
                # Work palette is local navigation, not an execution/approval surface.
                window.evaluate_js("document.getElementById('dialogue-input').value='保留主對話草稿';document.getElementById('dialogue-input').focus();document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true}))")
                assert window.evaluate_js("document.getElementById('modal').open&&document.activeElement.id==='work-entry-search'"),'work_entry_shortcut_focus'
                assert window.evaluate_js("document.querySelectorAll('[data-work-entry]').length")==11,'work_entry_missing_destinations'
                window.evaluate_js("document.getElementById('work-entry-search').value='不存在的入口';document.getElementById('work-entry-search').dispatchEvent(new Event('input'))")
                assert window.evaluate_js("document.querySelectorAll('[data-work-entry]').length")==0,'work_entry_filter'
                window.evaluate_js("document.getElementById('work-entry-search').value='成果';document.getElementById('work-entry-search').dispatchEvent(new Event('input'));document.getElementById('work-entry-search').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}))")
                assert window.evaluate_js("document.activeElement.dataset.workEntry==='activity'"),'work_entry_arrow_navigation'
                window.evaluate_js("document.activeElement.click()")
                assert window.evaluate_js("document.getElementById('page-title').textContent==='活動紀錄'&&document.getElementById('dialogue-input').value==='保留主對話草稿'"),'work_entry_draft_lost'
                window.evaluate_js("document.getElementById('work-entry').click();document.querySelector('[data-work-entry=chat]').click()")
                assert window.evaluate_js("document.getElementById('plan-mode').classList.contains('active')"),'work_entry_empty_plan_mode'
                window.evaluate_js("document.getElementById('chat-mode').click();document.getElementById('message-input').value='保留進階草稿';document.getElementById('work-entry').click();document.querySelector('[data-work-entry=chat]').click()")
                assert window.evaluate_js("document.getElementById('message-input').value==='保留進階草稿'&&document.getElementById('chat-mode').classList.contains('active')"),'work_entry_changed_draft_mode'
                window.evaluate_js("document.getElementById('work-entry').click();document.querySelector('[data-work-entry=briefing]').click()")
                time.sleep(.3)
                assert window.evaluate_js("document.getElementById('modal-title').textContent==='財經日報'&&!document.getElementById('modal').classList.contains('work-palette')"),'work_entry_briefing_preview'
                # Do not replace an already open preview when Ctrl+K is pressed.
                window.evaluate_js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true}))")
                assert window.evaluate_js("document.getElementById('modal-title').textContent==='財經日報'"),'work_entry_replaced_preview'
                window.evaluate_js("document.getElementById('modal-close').click();document.getElementById('work-entry').focus();document.getElementById('work-entry').click()")
                capture('work-entry-dark.png')
                window.resize(1050,700);time.sleep(.2);capture('work-entry-small.png')
                assert window.evaluate_js("(()=>{const r=document.getElementById('modal').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight;})()"),'work_entry_small_bounds'
                window.evaluate_js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
                time.sleep(.1)
                assert window.evaluate_js("!document.getElementById('modal').open&&document.activeElement.id==='work-entry'"),'work_entry_escape_focus'
                window.resize(1280,860)
                assert not session.store.tasks(),'work_entry_dispatched_work'
                window.evaluate_js("document.getElementById('message-input').value='';document.getElementById('dialogue-input').value='';document.querySelector('[data-page=dialogue]').click()")
                report['checks'].append('work_entry_keyboard_search_draft_preservation_preview_only_small_window')
                # Theme choices use existing widgets; unsaved connection inputs stay local.
                window.evaluate_js("document.querySelector('[data-page=settings]').click()")
                time.sleep(.3)
                assert window.evaluate_js("document.querySelectorAll('[data-color-choice]').length")==3,'missing_style_cards'
                window.evaluate_js("window.paletteEndpoint=document.querySelector('#page-content input:not([type=password])');paletteEndpoint.value='https://unsaved.example.test/v1'")
                def wait_script(script):
                    for _ in range(60):
                        if window.evaluate_js(script):return
                        time.sleep(.1)
                    raise AssertionError('appearance_wait_timeout')
                state_colors={}
                for theme in ('dark','light'):
                    window.evaluate_js("document.querySelector('[data-theme-choice="+theme+"]').click()")
                    wait_script("document.body.dataset.theme==="+json.dumps(theme)+"&&!document.querySelector('[data-theme-choice="+theme+"]').disabled")
                    window.evaluate_js("document.getElementById('work-entry').click()")
                    capture('work-entry-'+theme+'.png')
                    window.evaluate_js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
                    for style in ('ocean','violet','forest'):
                        window.evaluate_js("document.querySelector('[data-color-choice="+style+"]').click()")
                        wait_script("document.body.dataset.colorStyle==="+json.dumps(style)+"&&!document.querySelector('[data-color-choice="+style+"]').disabled")
                        assert window.evaluate_js("document.querySelector('[data-color-choice="+style+"]').getAttribute('aria-pressed')")=='true','selected_style_not_marked'
                        assert window.evaluate_js("paletteEndpoint===document.querySelector('#page-content input:not([type=password])')&&paletteEndpoint.value==='https://unsaved.example.test/v1'"),'appearance_rebuilt_connection_form'
                        colors=window.evaluate_js("Array.from(document.querySelectorAll('.appearance-legend .pill')).map(e=>getComputedStyle(e).color)")
                        if theme in state_colors:assert colors==state_colors[theme],'style_changed_status_colors'
                        else:state_colors[theme]=colors
                        capture('style-'+theme+'-'+style+'.png')
                assert not session.store.tasks(),'style_choice_dispatched_work'
                from desktop_app.preferences import load_color_style
                if load_color_style(session.preferences_path)!='forest':
                    report['appearance_failure']={'disk':load_color_style(session.preferences_path),'ui':window.evaluate_js('document.body.dataset.colorStyle'),'status':window.evaluate_js("document.getElementById('appearance-status').textContent")}
                assert load_color_style(session.preferences_path)=='forest','style_not_persisted'
                from unittest.mock import patch
                with patch('desktop_app.web_bridge.save_appearance',side_effect=OSError('synthetic_write_failure')):
                    window.evaluate_js("document.querySelector('[data-color-choice=violet]').click()")
                    wait_script("document.getElementById('appearance-status').dataset.saved==='false'&&!document.querySelector('[data-color-choice=violet]').disabled")
                    assert window.evaluate_js('document.body.dataset.colorStyle')=='violet','failed_save_lost_session_style'
                    assert load_color_style(session.preferences_path)=='forest','failed_save_overwrote_disk'
                    assert not window.evaluate_js("document.getElementById('appearance-retry').hidden"),'missing_save_retry'
                window.evaluate_js("document.getElementById('appearance-retry').click()")
                wait_script("document.getElementById('appearance-status').dataset.saved==='true'&&!document.getElementById('appearance-retry').disabled")
                assert load_color_style(session.preferences_path)=='violet','retry_not_persisted'
                assert window.evaluate_js("document.getElementById('toast').textContent")=='外觀已保存。','stale_save_failure_toast'
                window.resize(1050,700);time.sleep(.3);capture('appearance-settings-small.png')
                window.evaluate_js("document.getElementById('appearance-reset').scrollIntoView({block:'center'})")
                assert window.evaluate_js("(()=>{const r=document.getElementById('appearance-reset').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;})()"),'appearance_reset_unreachable'
                window.evaluate_js("document.getElementById('appearance-reset').click()")
                wait_script("document.body.dataset.colorStyle==='ocean'&&document.body.dataset.theme==='dark'&&!document.getElementById('appearance-reset').disabled")
                assert session.profiles.data.get('endpoint','')!='https://unsaved.example.test/v1','appearance_saved_connection'
                window.resize(1280,860)
                window.evaluate_js("document.querySelector('[data-page=dialogue]').click()")
                time.sleep(.3)
                report['checks'].append('six_style_modes_preserve_form_semantic_colors_save_retry_reset_zero_dispatch')
                # Semantic palette and live theme updates are local presentation only.
                window.evaluate_js("document.getElementById('dialogue-input').value='保留配色驗收草稿';document.getElementById('dialogue-input').setSelectionRange(2,6)")
                for theme in ('light','dark'):
                    window.evaluate_js("document.getElementById('theme-toggle').click()")
                    time.sleep(.4)
                    assert window.evaluate_js('document.body.dataset.theme')==theme,'theme_not_applied'
                    assert window.evaluate_js("document.getElementById('dialogue-input').value")=='保留配色驗收草稿','theme_lost_draft'
                    assert window.evaluate_js("document.getElementById('dialogue-input').selectionStart")==2,'theme_lost_caret'
                    capture('palette-'+theme+'.png')
                assert not session.store.tasks(),'palette_dispatched_work'
                window.resize(1050,700);time.sleep(.3);capture('palette-small.png')
                assert window.evaluate_js("document.documentElement.scrollWidth<=innerWidth"),'palette_horizontal_overflow'
                window.resize(1280,860)
                report['checks'].append('semantic_theme_keeps_draft_selection_and_zero_dispatch')
                def dialogue_send(text):
                    window.evaluate_js("document.getElementById('dialogue-input').value="+json.dumps(text)+";document.getElementById('dialogue-send').click()")
                    for _ in range(50):
                        time.sleep(.05)
                        if not window.evaluate_js("document.getElementById('dialogue-send').disabled"):break
                dialogue_send('這是第一則合成測試訊息')
                dialogue_send('請接續上一則')
                assert window.evaluate_js("document.querySelectorAll('#dialogue-messages .message').length")==4,'dialogue_multiturn'
                from desktop_app.dialogue_provider import CompanyDialogueProvider
                provider=session.dialogue.provider
                session.dialogue.provider=CompanyDialogueProvider()
                dialogue_send('服務錯誤時保留這段輸入')
                assert window.evaluate_js("document.getElementById('dialogue-input').value")=='服務錯誤時保留這段輸入','error_lost_input'
                assert window.evaluate_js("document.querySelectorAll('#dialogue-messages .message').length")==4,'error_lost_history'
                session.dialogue.provider=provider
                assert window.evaluate_js("document.getElementById('dialogue-send').disabled"),'unresolved_request_not_fenced'
                window.evaluate_js("Array.from(document.querySelectorAll('#dialogue-result button')).find(b=>b.textContent==='檢查原請求').click()")
                wait_script("Array.from(document.querySelectorAll('#dialogue-result button')).some(b=>b.textContent==='檢查原請求'&&!b.disabled)")
                capture('dialogue-recovery.png')
                window.evaluate_js("Array.from(document.querySelectorAll('#dialogue-result button')).find(b=>b.textContent==='另開對話保留內容').click()")
                time.sleep(.15)
                assert not window.evaluate_js("document.querySelector('#modal-body input[type=checkbox]').checked"),'history_copied_without_choice'
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='建立新對話').click()")
                wait_script("!document.getElementById('modal').open&&!document.getElementById('dialogue-send').disabled")
                assert window.evaluate_js("document.getElementById('dialogue-input').value")=='服務錯誤時保留這段輸入','fork_lost_failed_draft'
                assert window.evaluate_js("document.querySelectorAll('#dialogue-messages .message').length")==0,'fork_shared_history_by_default'
                dialogue_send('新對話可以繼續，合成測試')
                assert window.evaluate_js("document.querySelectorAll('#dialogue-messages .message').length")==2,'fork_cannot_continue'
                window.evaluate_js("document.getElementById('dialogue-history').click()")
                time.sleep(.2)
                window.evaluate_js("document.querySelector('#modal-body input').value='新對話可以繼續';document.querySelector('#modal-body input').dispatchEvent(new Event('input'))")
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-body button')).find(b=>b.textContent==='刪除').click()")
                wait_script("document.getElementById('modal-title').textContent.includes('永久刪除')")
                assert window.evaluate_js('document.activeElement.textContent')=='取消','delete_default_not_cancel'
                capture('dialogue-delete.png')
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='永久刪除').click()")
                wait_script("!document.getElementById('modal').open&&!document.getElementById('dialogue-send').disabled")
                assert not any('新對話可以繼續' in (r['title'] or '') for r in session.dialogue.history()),'dialogue_not_deleted'
                report['checks'].append('failed_request_fenced_inspect_fork_and_explicit_delete')
                report['checks'].append('provider_failure_preserves_input_and_messages_no_fallback')
                window.evaluate_js("document.getElementById('dialogue-task-mode').click()")
                time.sleep(.3)
                assert window.evaluate_js("document.querySelectorAll('#dialogue-messages .message').length")==0,'mode_not_reset'
                for text in ('我要建立追蹤任務','A類庫存','組織核准資料庫','資料追蹤','每天08:00'):dialogue_send(text)
                assert not session.dialogue.list_saved(),'task_saved_before_confirmation'
                window.evaluate_js("Array.from(document.querySelectorAll('#dialogue-result button')).find(b=>b.textContent==='預覽任務').click()")
                time.sleep(.2);capture('dialogue-task-preview.png')
                assert window.evaluate_js("Boolean(document.querySelector('#modal-body .notice[data-tone=attention]'))"),'draft_preview_not_attention'
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='取消').click()")
                time.sleep(.2)
                assert not session.dialogue.list_saved(),'cancel_saved_task'
                window.evaluate_js("Array.from(document.querySelectorAll('#dialogue-result button')).find(b=>b.textContent==='預覽任務').click()")
                time.sleep(.2)
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='確認儲存（不啟用）').click()")
                time.sleep(.3)
                saved=session.dialogue.list_saved()
                assert len(saved)==1 and saved[0]['enabled']==0,'offline_draft_not_disabled'
                assert not session.store.tasks() and not session.store.schedules(),'offline_task_dispatched'
                capture('dialogue-saved.png')
                report['checks'].append('offline_multiturn_mode_reset_questions_preview_cancel_and_disabled_save')
                window.evaluate_js("document.getElementById('theme-toggle').click()")
                time.sleep(.4);capture('dialogue-light.png')
                window.resize(1050,700);time.sleep(.3);capture('dialogue-small.png')
                window.resize(1280,860)
                window.evaluate_js("document.getElementById('theme-toggle').click();document.getElementById('dialogue-assistant').value='demo-data';document.getElementById('dialogue-assistant').dispatchEvent(new Event('change'))")
                time.sleep(.3)
                assert window.evaluate_js("document.querySelectorAll('#dialogue-messages .message').length")==0,'assistant_switch_kept_old_history'
                report['checks'].append('assistant_switch_starts_empty_view')
                window.evaluate_js("document.querySelector('[data-page=chat]').click()")
                time.sleep(.2)
                window.evaluate_js("document.getElementById('message-input').value='請整理以下合成筆記：完成資料檢查，明天確認格式。';document.getElementById('message-input').dispatchEvent(new Event('input'));document.getElementById('send').click()")
                for _ in range(60):
                    if session.store.tasks() and not session.engine.has_inflight():break
                    time.sleep(.2)
                assert session.store.tasks()[0]['state']=='succeeded','chat_failed'
                report['checks'].append('chat_sent_from_dom')
                time.sleep(2);capture('chat.png')
                window.evaluate_js("document.getElementById('new-chat').click()")
                time.sleep(.5)
                window.evaluate_js("document.querySelector('[data-starter=query]').click()")
                time.sleep(.5)
                window.evaluate_js("document.getElementById('send').click()")
                time.sleep(.6)
                assert len(session.store.tasks())==1,'query_dispatched_before_approval'
                assert window.evaluate_js("Boolean(document.querySelector('#modal-body .notice[data-tone=attention]'))"),'query_preview_not_attention'
                capture('query-preview.png')
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='確認查詢').click()")
                time.sleep(2)
                assert len(session.store.tasks())==2,'query_not_dispatched'
                assert session.store.tasks()[0]['state']=='succeeded','query_failed'
                report['checks'].append('three_click_query_zero_dispatch_before_confirm')
                capture('query-result.png')
                window.evaluate_js("document.getElementById('theme-toggle').click()")
                time.sleep(2);capture('light.png')
                window.resize(1050,700);time.sleep(.5);capture('small.png')
                window.maximize();time.sleep(.5);capture('maximized.png')
                # Explicit synthetic planner/child replies, never a live provider.
                from desktop_app.trial import TrialProfiles
                trial=TrialProfiles()
                for method in ('workflow_catalog','workflow_binding','validate_workflow'):
                    setattr(session.profiles,method,getattr(trial,method))
                steps=[{'id':'s1','title':'查合成數量','kind':'query','query_id':'DEMO03','parameters':{'category':'A'},'date_mode':'previous_day','inputs':[]},
                       {'id':'s2','title':'整理合成成果','kind':'assistant','role':'compose','binding':trial.workflow_binding('groq-compose'),'instruction':'只整理來源','inputs':['s1']}]
                def synthetic(messages,role,binding,context):
                    payload=json.loads(messages[-1]['content'].split('核准工作與輸入：')[1])
                    facts={}
                    for source in payload['sources'].values():facts.update(source.get('numeric_totals',source.get('facts',{})))
                    return json.dumps({'text':'## 結論\n合成介面驗證成果。\n## 需要注意\n非真實 AI 分析。\n## 待確認與決策\n請核對來源。','facts':facts},ensure_ascii=False)
                session.profiles.workflow_call=synthetic
                cid=api.call('state',{})['data']['conversation']['id']
                workflow=session.workflows.create(cid,'合成分工介面驗證',trial.workflow_binding('groq-planner'))
                session.workflows.update(workflow['id'],workflow['revision'],steps)
                wait_script("Array.from(document.querySelectorAll('#workflow-panel button')).some(b=>b.textContent==='檢視並確認')")
                window.evaluate_js("Array.from(document.querySelectorAll('#workflow-panel button')).find(b=>b.textContent==='檢視並確認').click()")
                time.sleep(.3);capture('workflow-preview.png')
                assert len(session.store.tasks())==2,'workflow_dispatched_before_confirmation'
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='確認執行').click()")
                time.sleep(2)
                task=session.store.tasks()[0]
                assert task['kind']=='workflow' and task['state']=='succeeded','workflow_failed'
                wait_script("Array.from(document.querySelectorAll('#workflow-panel button')).some(b=>b.textContent==='查看成果')")
                window.evaluate_js("Array.from(document.querySelectorAll('#workflow-panel button')).find(b=>b.textContent==='查看成果').click()")
                wait_script("Array.from(document.querySelectorAll('#modal-body button')).some(b=>b.textContent==='可採用')")
                capture('outcome.png')
                assert window.evaluate_js("Boolean(document.querySelector('#modal-body .pill[data-tone=success]'))"),'outcome_not_success'
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-body button')).find(b=>b.textContent==='可採用').click()")
                time.sleep(.3)
                assert session.outcomes.feedback(task['id'])['rating']=='usable','feedback_failed'
                report['checks'].append('workflow_explicit_approval_and_outcome_feedback_mock')
                window.evaluate_js("document.getElementById('modal-close').click();document.querySelector('[data-page=activity]').click()")
                time.sleep(.3)
                assert window.evaluate_js("Array.from(document.querySelectorAll('.status-legend .pill')).map(e=>e.dataset.tone).join(',')")=='attention,working,success,danger','semantic_status_mapping'
                for theme in ('light','dark'):
                    if window.evaluate_js('document.body.dataset.theme')!=theme:
                        window.evaluate_js("document.getElementById('theme-toggle').click()")
                        time.sleep(.4)
                    colors=window.evaluate_js("Array.from(document.querySelectorAll('.status-legend .pill')).map(e=>getComputedStyle(e).color)")
                    assert len(set(colors))==4,'semantic_status_colors_collapsed'
                    capture('activity-'+theme+'.png')
                report['checks'].append('attention_running_success_failure_distinct_in_both_themes')
                from desktop_app.core import stamp
                with session.store.connection() as db:
                    db.execute('INSERT INTO notifications VALUES(?,?,?,?,0,?)',
                               ('palette-notice','palette-notice',task['id'],'合成通知：成果已完成，請核對來源。',stamp()))
                time.sleep(2)
                window.evaluate_js("document.querySelector('[data-page=notice]').click()")
                time.sleep(.3);capture('notifications-dark.png')
                assert window.evaluate_js("document.querySelector('[data-page=notice] .badge').hidden===false"),'unread_badge_missing'
                assert not session.store.notifications()[0]['is_read'],'opening_inbox_marked_read'
                assert window.evaluate_js("getComputedStyle(document.querySelector('[data-page=notice] .badge')).color===getComputedStyle(document.querySelector('[data-page=notice]')).color"),'unread_badge_not_informational'
                assert window.evaluate_js("Boolean(document.querySelector('#page-content .list-row[data-tone=success]'))"),'notification_severity_missing'
                window.evaluate_js("Array.from(document.querySelectorAll('#page-content button')).find(b=>b.textContent==='查看').click()")
                time.sleep(.4)
                assert session.store.notifications()[0]['is_read'],'explicit_view_did_not_mark_read'
                assert window.evaluate_js("document.querySelector('[data-page=notice] .badge').hidden"),'read_badge_stale'
                assert window.evaluate_js("document.getElementById('page-content').innerText.includes('已讀')"),'read_label_stale'
                window.evaluate_js("document.getElementById('modal-close').click()")
                report['checks'].append('notification_unread_is_informational_explicit_view_only_and_state_retained')
                window.evaluate_js("location.href='data:text/html,<h1>UNTRUSTED</h1>'")
                time.sleep(.3)
                assert window.evaluate_js("Boolean(document.getElementById('dialogue-input'))"),'navigation_not_blocked'
                report['checks'].append('untrusted_navigation_blocked')
                # Company-shaped HTTP remains synthetic, using the actual SDK adapter.
                window.evaluate_js("if(document.getElementById('modal').open)document.getElementById('modal').close()")
                import httpx
                from openai import OpenAI
                from desktop_app.assistants_gateway import AssistantsGateway
                from test_support.search_mock import SearchMock
                company_mock=SearchMock()
                profiles=session.profiles
                from tests.test_profiles import MemoryVault
                profiles.vault=MemoryVault()
                profiles.set_endpoint('https://fixture.example.test/v1');profiles.set_wire_mode('assistants')
                pid=profiles.save('合成AI 助理','asst_synthetic')
                profiles.key=lambda binding=None:'synthetic-test-key'
                def mock_client(d,p,key,binding):
                    sdk=OpenAI(base_url='https://fixture.example.test/v1',api_key=key,max_retries=0,
                        http_client=httpx.Client(transport=httpx.MockTransport(company_mock.handle)))
                    return AssistantsGateway({'base_url':d['endpoint'],'assistant_id':p['assistant_id'],'search_policy':p.get('search_policy')},key,
                        session.directory/'assistant-sessions.sqlite3',binding,client=sdk)
                profiles._assistants_client=mock_client
                window.evaluate_js("document.querySelector('[data-page=dialogue]').click()")
                time.sleep(.4)
                selection='company:'+pid+':'+str(profiles.snapshot(pid)['revision'])
                window.evaluate_js("document.getElementById('dialogue-chat-mode').click()")
                time.sleep(.2)
                window.evaluate_js("document.getElementById('dialogue-assistant').value="+json.dumps(selection)+";document.getElementById('dialogue-assistant').dispatchEvent(new Event('change'))")
                time.sleep(.3)
                dialogue_send('合成第一題')
                from desktop_app.gateways import GatewayError
                def unavailable_key(binding=None):raise GatewayError('合成認證儲存暫不可用')
                profiles.key=unavailable_key
                dialogue_send('接續合成追問')
                wait_script("Array.from(document.querySelectorAll('#dialogue-result button')).some(b=>b.textContent==='重試未送出')")
                assert len(company_mock.runs)==1,'preflight_dispatched'
                window.evaluate_js("Array.from(document.querySelectorAll('#dialogue-result button')).find(b=>b.textContent==='檢查原請求').click()")
                wait_script("Array.from(document.querySelectorAll('#dialogue-result button')).some(b=>b.textContent==='檢查原請求'&&!b.disabled)")
                assert window.evaluate_js("Array.from(document.querySelectorAll('#dialogue-result button')).some(b=>b.textContent==='重試未送出')"),'inspect_hid_unsent_retry'
                capture('unsent-retry.png')
                profiles.key=lambda binding=None:'synthetic-test-key'
                window.evaluate_js("Array.from(document.querySelectorAll('#dialogue-result button')).find(b=>b.textContent==='重試未送出').click()")
                wait_script("!document.getElementById('dialogue-send').disabled")
                assert window.evaluate_js("document.getElementById('dialogue-input').value")=='' ,'retry_kept_sent_draft'
                report['checks'].append('proven_unsent_retry_same_request_preserves_history')
                assert len(company_mock.threads)==1 and len(company_mock.runs)==2,'company_thread_continuity'
                assert window.evaluate_js("document.getElementById('dialogue-mode-label').textContent.includes('AI 助理')"),'company_badge'
                window.restore();window.resize(1050,700);time.sleep(.3);capture('company-small.png')
                for control in ('dialogue-send','dialogue-plan','dialogue-stop','dialogue-briefing'):
                    assert window.evaluate_js("(()=>{const e=document.getElementById("+json.dumps(control)+");if(e.hidden)return true;const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight;})()"),'company_controls_clipped'
                window.evaluate_js("document.getElementById('theme-toggle').click()")
                time.sleep(.3);capture('company-dark.png')
                report['checks'].append('company_sdk_mock_multiturn_main_ui_badge_small_controls')
                # Guided setup does not query a model; the explicit probe is metadata GET only.
                def click_button(text):
                    window.evaluate_js("Array.from(document.querySelectorAll('#modal button,#page-content button,#page-actions button')).find(b=>b.textContent==="+json.dumps(text)+").click()")
                def wait_text(text):
                    for _ in range(100):
                        if window.evaluate_js("document.getElementById('modal-body').innerText.includes("+json.dumps(text)+")"):return
                        time.sleep(.1)
                    raise AssertionError('missing_modal_text')
                window.evaluate_js("document.querySelector('[data-page=settings]').click()")
                time.sleep(.3);count=len(company_mock.runs)
                click_button('檢查本機設定');wait_text('下一步')
                assert len(company_mock.runs)==count,'readiness_dispatched_model'
                click_button('檢查搜尋助理連線');wait_text('internet_search')
                assert len(company_mock.runs)==count,'metadata_probe_dispatched_model'
                assert not window.evaluate_js("document.querySelector('[data-search-tool]').checked"),'search_default_selected'
                assert not company_mock.plugin_requests,'metadata_dispatched_search'
                window.evaluate_js("document.querySelector('[data-search-save]').scrollIntoView({block:'center'})")
                assert window.evaluate_js("(()=>{const r=document.querySelector('[data-search-save]').getBoundingClientRect(),b=document.getElementById('modal-body').getBoundingClientRect();return r.top>=b.top&&r.bottom<=b.bottom;})()"),'search_consent_control_unreachable'
                window.evaluate_js("document.querySelector('[data-search-tool]').click();document.querySelector('[data-search-consent]').click();document.querySelector('[data-search-save]').click()")
                wait_text('已保存搜尋核准')
                assert not company_mock.plugin_requests,'approval_dispatched_search'
                capture('company-setup.png')
                window.evaluate_js("document.getElementById('modal-close').click()")
                click_button('檢查本機設定');wait_text('目前核准的搜尋工具：internet_search')
                capture('search-policy-dark.png')
                window.evaluate_js("document.getElementById('theme-toggle').click()")
                time.sleep(.3);capture('search-policy-light.png')
                window.evaluate_js("document.getElementById('theme-toggle').click()")
                window.evaluate_js("document.getElementById('modal-close').click();document.querySelector('[data-page=dialogue]').click()")
                time.sleep(.3);window.evaluate_js("document.getElementById('dialogue-briefing').click()");wait_text('台北')
                company_mock.reply='【合成財經日報，非真實新聞】\n台股、美股、總經：此處僅展示回覆與排程流程。\n來源：https://example.test/synthetic'
                time.sleep(.3);click_button('預覽試跑');wait_text('尚未執行')
                assert len(company_mock.runs)==count,'briefing_preview_dispatched_model'
                wait_script("Array.from(document.querySelectorAll('#modal button')).some(b=>b.textContent==='現在試跑'&&!b.disabled)")
                click_button('現在試跑');wait_text('我已核對日報內容')
                briefings=[t for t in session.store.tasks() if t['kind']=='assistant_briefing']
                assert len(briefings)==1 and briefings[0]['state']=='succeeded','briefing_trial_failed'
                assert len(company_mock.plugin_requests)==1,'approved_search_not_executed_once'
                wait_text('結果已交回助理')
                capture('briefing-result.png')
                for text in ('關閉','啟用每日'):
                    assert window.evaluate_js("(()=>{const e=Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent.startsWith("+json.dumps(text)+"));const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;})()"),'briefing_controls_clipped'
                window.evaluate_js("document.getElementById('theme-toggle').click()")
                time.sleep(.3);capture('briefing-light-small.png')
                window.resize(1280,860);time.sleep(.3);capture('briefing-light-normal.png')
                window.maximize();time.sleep(.3);capture('briefing-light-maximized.png')
                window.evaluate_js("document.getElementById('theme-toggle').click()")
                time.sleep(.3);capture('briefing-dark-maximized.png')
                window.restore();window.resize(1050,700);time.sleep(.3)
                window.evaluate_js("document.querySelector('#modal-body input[type=checkbox]').click()")
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent.startsWith('啟用每日')).click()")
                wait_text('已啟用每日')
                schedules=[s for s in session.store.schedules() if s['query_id']=='ASSISTANT_BRIEFING']
                assert len(schedules)==1 and schedules[0]['enabled'],'briefing_schedule_missing'
                assert len(company_mock.runs)==count+1,'briefing_schedule_ran_immediately'
                click_button('暫停每日工作');wait_text('已暫停')
                assert not session.store.schedule(schedules[0]['id'])['enabled'],'briefing_pause_failed'
                assert not window.evaluate_js("document.getElementById('modal-body').innerText.includes('已啟用每日')"),'stale_enabled_label'
                report['checks'].append('briefing_dom_preview_trial_review_schedule_pause_mock')
                window.evaluate_js("document.getElementById('modal-close').click();document.querySelector('[data-page=activity]').click()")
                time.sleep(.3);click_button('管理／批次刪除');wait_text('資料類別')
                window.evaluate_js("document.querySelector('#modal-body input:not([type=checkbox])').value='assistant_briefing';document.querySelector('#modal-body input:not([type=checkbox])').dispatchEvent(new Event('input'))")
                time.sleep(.2);capture('manage-data.png')
                # At least one briefing task exists; cancel first, then confirm through the same UI.
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='全選目前搜尋結果').click()")
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='刪除選取項目').click()")
                wait_script("document.getElementById('modal-title').textContent.startsWith('永久刪除')")
                assert window.evaluate_js('document.activeElement.textContent')=='取消','cleanup_default_not_cancel'
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='取消').click()")
                assert session.store.task(briefings[0]['id'])['state']=='succeeded','cancel_cleanup_deleted_task'
                click_button('管理／批次刪除');wait_text('資料類別')
                window.evaluate_js("document.querySelector('#modal-body input:not([type=checkbox])').value='assistant_briefing';document.querySelector('#modal-body input:not([type=checkbox])').dispatchEvent(new Event('input'))")
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='全選目前搜尋結果').click()")
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='刪除選取項目').click()")
                wait_script("document.getElementById('modal-title').textContent.startsWith('永久刪除')")
                click_button('確認刪除');wait_script("!document.getElementById('modal').open")
                assert not any(t['id']==briefings[0]['id'] for t in session.store.tasks()),'cleanup_kept_visible_task'
                assert session.store.schedule(schedules[0]['id']),'cleanup_removed_independent_schedule'
                assert len(company_mock.runs)==count+1,'cleanup_dispatched_model'
                window.evaluate_js("document.querySelector('[data-page=query]').click()")
                time.sleep(.3);capture('query-entry.png')
                assert window.evaluate_js("document.documentElement.scrollWidth<=innerWidth"),'query_horizontal_overflow'
                report['checks'].append('cleanup_cancel_confirm_no_dispatch_preserves_schedule_query_entry')
                report['checks'].append('company_setup_and_metadata_probe_no_model_dispatch')
                report['checks'].append('search_consent_no_dispatch_reopen_policy_and_exactly_one_mock_search')
                # Opting chat in is separate from the existing daily-briefing permission.
                assert profiles.validate(profiles.snapshot(pid)).get('chat_search_enabled') is not True,'old_policy_widened'
                result=api.call('company_probe',{'profile_id':pid})
                assert result['ok'],'chat_probe_failed'
                token=result['data']['policy_token']
                result=api.call('search_policy_save',{'token':token,'names':['internet_search'],'consent':True,'chat_enabled':True})
                assert result['ok'],'chat_approval_failed'
                before_search=len(company_mock.plugin_requests)
                window.evaluate_js("document.querySelector('[data-page=dialogue]').click()")
                time.sleep(.4)
                selection='company:'+pid+':'+str(profiles.snapshot(pid)['revision'])
                window.evaluate_js("document.getElementById('dialogue-assistant').value="+json.dumps(selection)+";document.getElementById('dialogue-assistant').dispatchEvent(new Event('change'))")
                time.sleep(.3);dialogue_send('使用核准搜尋的合成測試')
                assert len(company_mock.plugin_requests)==before_search+1,'chat_search_not_dispatched_once'
                assert window.evaluate_js("document.getElementById('dialogue-mode-label').textContent.includes('搜尋')"),'chat_search_not_labeled'
                capture('chat-search.png')
                report['checks'].append('chat_search_separate_opt_in_and_single_mock_tool_roundtrip')
                profiles.key=unavailable_key
                dialogue_send('更換金鑰後要保留的合成草稿')
                profiles.save_profile_key(pid,'synthetic-new-key');profiles.key=lambda binding=None:'synthetic-new-key'
                before_fork=len(company_mock.runs)
                window.evaluate_js("Array.from(document.querySelectorAll('#dialogue-result button')).find(b=>b.textContent==='另開對話保留內容').click()")
                wait_text('原連線已失效')
                target='company:'+pid+':'+str(profiles.snapshot(pid)['revision'])
                assert window.evaluate_js("document.querySelector('#modal-body select').value")==target,'fork_destination_not_current_revision'
                assert not window.evaluate_js("document.querySelector('#modal-body input[type=checkbox]').checked"),'fork_history_default_changed'
                capture('new-connection-preview.png')
                click_button('建立新對話');wait_script("!document.getElementById('modal').open")
                assert window.evaluate_js("document.getElementById('dialogue-input').value")=='更換金鑰後要保留的合成草稿','revision_fork_lost_draft'
                assert len(company_mock.runs)==before_fork,'revision_fork_dispatched'
                report['checks'].append('credential_revision_fork_explicit_destination_and_preserved_draft_zero_dispatch')
                # One-assistant work orders use synthetic data, and preserve the chat draft.
                order_tasks_before={t['id'] for t in session.store.tasks()}
                order_runs_before=len(company_mock.runs)
                window.evaluate_js("document.getElementById('dialogue-order').click()")
                wait_script("!!document.getElementById('order-goal')")
                window.evaluate_js("document.getElementById('order-assistant').value='demo';document.getElementById('order-goal').value='請幫我規劃每天的日報';document.getElementById('order-goal').dispatchEvent(new Event('input'));document.getElementById('order-create').click()")
                wait_script("!!document.getElementById('order-discuss')&&!document.getElementById('order-planning')")
                assert window.evaluate_js("document.getElementById('order-content').textContent.includes('要關注哪些新聞')"),'order_missing_questions'
                window.evaluate_js("document.getElementById('order-reply').value='台股、美股與總經，公開網路可靠來源，每天08:00';document.getElementById('order-reply').dispatchEvent(new Event('input'));document.getElementById('order-discuss').click()")
                wait_script("document.getElementById('order-time').value==='08:00'&&!document.getElementById('order-planning')")
                assert {t['id'] for t in session.store.tasks()}==order_tasks_before,'order_planning_dispatched'
                window.evaluate_js("document.getElementById('order-trial-preview').click()")
                wait_script("document.getElementById('order-preview').textContent.includes('確認試跑一次')")
                window.evaluate_js("Array.from(document.querySelectorAll('#order-preview button')).find(b=>b.textContent==='取消').click()")
                assert {t['id'] for t in session.store.tasks()}==order_tasks_before,'order_preview_cancel_dispatched'
                for theme in ('dark','light'):
                    api.call('appearance',{'theme':theme})
                    time.sleep(1.7)
                    capture('work-order-'+theme+'.png')
                window.resize(1050,700);time.sleep(.3);capture('work-order-small.png')
                window.evaluate_js("document.getElementById('order-trial-preview').scrollIntoView({block:'center'});document.getElementById('order-trial-preview').click()")
                wait_script("document.getElementById('order-preview').textContent.includes('確認試跑一次')")
                window.evaluate_js("Array.from(document.querySelectorAll('#order-preview button')).find(b=>b.textContent==='確認試跑一次').click()")
                wait_script("document.getElementById('order-outcome').textContent.includes('離線示範成果')")
                assert window.evaluate_js("document.getElementById('order-outcome').textContent.includes('不能啟用真實排程')"),'order_demo_enable_exposed'
                assert window.evaluate_js("document.getElementById('order-scope').readOnly&&document.getElementById('order-discuss').disabled"),'order_executed_revision_editable'
                assert window.evaluate_js("document.getElementById('dialogue-input').value")=='更換金鑰後要保留的合成草稿','order_lost_chat_draft'
                assert len(company_mock.runs)==order_runs_before,'demo_order_called_company'
                capture('work-order-result-small.png')
                # Minimal expiry cancellation receipt must not replace visible results.
                original_order_state=session.orders.state
                original_order_cancel=session.orders.cancel
                def expired_running_state(oid):
                    r=original_order_state(oid)
                    r['task']['state']='running'
                    return r
                try:
                    session.orders.state=expired_running_state
                    session.orders.cancel=lambda oid:{'id':oid,'cancelled':True,'identity_expired':True}
                    window.evaluate_js("Array.from(document.querySelectorAll('#order-actions button')).find(b=>b.textContent==='工作紀錄').click()")
                    wait_script("document.getElementById('order-content').textContent.includes('交辦紀錄')")
                    window.evaluate_js("document.querySelector('#order-content button').click()")
                    wait_script("document.getElementById('order-outcome')?.textContent.includes('取消這次試跑')")
                    before_expired=window.evaluate_js("document.getElementById('order-outcome').textContent")
                    window.evaluate_js("Array.from(document.querySelectorAll('#order-outcome button')).find(b=>b.textContent==='取消這次試跑').click()")
                    wait_script("document.getElementById('order-error').textContent.includes('登入已到期')")
                    assert window.evaluate_js("document.getElementById('order-outcome').textContent")==before_expired,'expired_cancel_replaced_outcome'
                    assert not window.evaluate_js("document.getElementById('order-outcome').textContent.includes('尚未試跑')"),'expired_cancel_reset_trial'
                finally:
                    session.orders.state=original_order_state
                    session.orders.cancel=original_order_cancel
                window.resize(1280,860)
                report['checks'].append('work_order_demo_discussion_questions_preview_cancel_trial_readonly_and_chat_draft_preserved')
                # Register a real Windows tray icon before hiding; no model or remote calls.
                from desktop_app.tray import TrayController,WinFormsTray
                tray_backend=WinFormsTray(window,lambda:'合成測試 · 0 個自動工作',lambda:None)
                tray=TrayController(tray_backend)
                try:
                    assert tray.background(),'native_tray_register_failed'
                    visibility=[]
                    tray_backend._ui(lambda:visibility.extend([bool(window.native.Visible),bool(tray_backend.notify.Visible)]))
                    assert visibility==[False,True],'native_tray_hide_before_icon'
                    tray.show();visibility=[]
                    tray_backend._ui(lambda:visibility.append(bool(window.native.Visible)))
                    assert visibility==[True],'native_tray_restore_failed'
                finally:tray.close()
                assert tray_backend.notify is None,'native_tray_not_disposed'
                report['checks'].append('real_winforms_tray_register_hide_restore_dispose_local_only')
                # First-close UI offers an explicit choice; no implicit approval of a task.
                close_choices=[]
                api._host_close=lambda value,remember:close_choices.append((value,remember)) or {'value':value,'saved':True}
                window.evaluate_js("window.qaRequestClose()")
                assert window.evaluate_js("document.getElementById('modal-title').textContent.includes('繼續自動工作')"),'close_choice_missing'
                window.evaluate_js("document.querySelector('#modal-body input[type=checkbox]').checked=true;Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='留在系統匣').click()")
                wait_script("!document.getElementById('modal').open")
                assert close_choices==[('background',True)],'close_choice_changed'
                window.evaluate_js("window.qaRequestClose(true)")
                assert window.evaluate_js("document.getElementById('modal-body').textContent.includes('尚未提交')"),'close_unsaved_warning_missing'
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='返回保存').click()")
                assert close_choices==[('background',True)],'close_unsaved_cancel_exited'
                assert api.call('close_behavior',{'value':'background'})['data']['saved'],'close_preference_not_saved'
                assert api.call('close_behavior',{})['data']['value']=='background','close_preference_not_restored'
                api.call('close_behavior',{'value':'ask'})
                report['checks'].append('close_choice_explicit_remember_unsaved_cancel_and_preference_roundtrip')
                skills_journey(session,api,window,capture,wait_script,report,tmp,company_mock)
                # Real desktop WebView2, synthetic personal work only; never user data.
                inbox_baseline={t['id'] for t in session.store.tasks()}
                from datetime import datetime, timezone, timedelta
                today=(datetime.now(timezone.utc)+timedelta(hours=8)).date()
                source=session.store.create_conversation('合成待辦來源',session.profiles.default_binding())
                overdue=session.store.create_todo('核對出貨清單','等待 QA 確认後記錄結論',(today-timedelta(days=1)).isoformat(),source,'smoke-todo-1')
                future=session.store.create_todo('整理下週規格','附件仍待提供',(today+timedelta(days=3)).isoformat(),None,'smoke-todo-2')
                completed=session.store.create_todo('已完成合成事項','已保存核對結論',None,None,'smoke-todo-3')
                session.store.set_todo_state(completed['id'],'done')
                plan=api.call('send',{'cid':source,'text':'合成待確認工作','purpose':'chat','planned':True,'request_id':'smoke-inbox-plan','seq':1})
                assert plan['ok'], 'inbox_plan_creation_failed'
                window.evaluate_js("if(document.body.dataset.theme!=='dark')document.getElementById('theme-toggle').click()")
                wait_script("document.body.dataset.theme==='dark'")
                window.evaluate_js("document.querySelector('[data-page=todo]').click()")
                wait_script("document.querySelector('[data-todo-id]')!==null")
                wait_script("document.getElementById('page-content').textContent.includes('核對出貨清單')")
                assert window.evaluate_js("document.getElementById('page-content').textContent.includes('逾期')"),'overdue_missing'
                assert not window.evaluate_js("Array.from(document.querySelectorAll('[data-todo-id]')).some(e=>e.textContent.includes('已完成合成事項'))"),'done_not_hidden'
                capture('todos-dark.png')
                def todo_script(script):window.evaluate_js(script)
                todo_script("window.todoSearch=document.querySelector('#page-content .toolbar input');todoSearch.value='附件';todoSearch.dispatchEvent(new Event('input'))")
                assert window.evaluate_js("document.querySelectorAll('[data-todo-id]').length")==1,'description_search_wrong'
                todo_script("todoSearch.value='';todoSearch.dispatchEvent(new Event('input'));window.todoScope=document.querySelector('#page-content .toolbar select');todoScope.value='due';todoScope.dispatchEvent(new Event('change'))")
                assert window.evaluate_js("document.querySelectorAll('[data-todo-id]').length")==1,'due_filter_wrong'
                todo_script("Array.from(document.querySelectorAll('[data-todo-id] button')).find(b=>b.textContent==='開始處理').click()")
                wait_script("Array.from(document.querySelectorAll('[data-todo-id] button')).some(b=>b.textContent==='完成')")
                assert session.store.todo(overdue['id'])['state']=='ongoing','start_not_persisted'
                todo_script("Array.from(document.querySelectorAll('[data-todo-id] button')).find(b=>b.textContent==='完成').click()")
                wait_script("document.querySelectorAll('[data-todo-id]').length===0")
                assert session.store.todo(overdue['id'])['state']=='done','completion_not_persisted'
                window.evaluate_js("document.querySelector('[data-page=activity]').click();document.querySelector('[data-page=todo]').click()")
                assert window.evaluate_js("document.querySelector('#page-content .toolbar select').value")=='due','filter_navigation_reset'
                todo_script("document.querySelector('#page-content .toolbar select').value='all';document.querySelector('#page-content .toolbar select').dispatchEvent(new Event('change'))")
                todo_script("Array.from(document.querySelectorAll('#page-content .work-inbox button')).find(b=>b.textContent==='回來源處理').click()")
                wait_script("!document.getElementById('chat-page').hidden")
                assert window.evaluate_js("document.getElementById('workflow-panel').textContent.includes('待確認計畫')"),'inbox_source_plan_missing'
                assert {t['id'] for t in session.store.tasks()}==inbox_baseline,'inbox_navigation_dispatched'
                window.evaluate_js("document.querySelector('[data-page=todo]').click()")
                time.sleep(.2)
                window.resize(850,650);time.sleep(.3);capture('todos-small.png')
                assert window.evaluate_js("document.getElementById('page-content').scrollWidth<=document.getElementById('page-content').clientWidth+2"),'todo_horizontal_overflow'
                window.evaluate_js("document.querySelector('[data-page=settings]').click()")
                window.evaluate_js("document.querySelector('[data-theme-choice=light]').click()")
                wait_script("document.body.dataset.theme==='light'")
                window.evaluate_js("document.querySelector('[data-page=todo]').click()")
                time.sleep(.2);capture('todos-light.png')
                window.resize(1280,860);window.maximize();time.sleep(.3);capture('todos-maximized.png')
                # Cancel and invalid submission preserve input and never create records.
                window.evaluate_js("Array.from(document.querySelectorAll('#page-actions button')).find(b=>b.textContent==='新增待辦').click()")
                before_todos=len(session.store.todos())
                window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='保存').click()")
                assert len(session.store.todos())==before_todos,'empty_todo_saved'
                window.evaluate_js("document.querySelector('#modal-body input').value='合成新待辦';Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='保存').click();Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='保存').click()")
                wait_script("!document.getElementById('modal').open")
                assert len(session.store.todos())==before_todos+1,'duplicate_todo_save'
                window.evaluate_js("Array.from(document.querySelectorAll('#page-actions button')).find(b=>b.textContent==='新增待辦').click();Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='取消').click()")
                assert len(session.store.todos())==before_todos+1,'cancel_created_todo'
                inbox_row=next(row for row in api.call('state',{})['data']['work_inbox'] if row['kind']=='dialogue')
                target=inbox_row['id'];pending=session.dialogue.state(target)['request']['pending_text']
                before_source=window.evaluate_js('window.qaDialogueViewSnapshot().id')
                window.evaluate_js("document.getElementById('dialogue-input').value='尚未送出的合成草稿'")
                source_button="document.querySelector('[data-inbox-id=\""+target+"\"] button').click()"
                window.evaluate_js(source_button)
                wait_script("window.qaDialogueViewSnapshot().id==="+json.dumps(target))
                assert session.dialogue.state(before_source)['draft_text']=='尚未送出的合成草稿','inbox_overwrote_main_draft'
                assert window.evaluate_js("document.getElementById('dialogue-input').value")==pending,'inbox_pending_not_restored'
                assert {t['id'] for t in session.store.tasks()}==inbox_baseline,'main_inbox_dispatched'
                window.evaluate_js("document.querySelector('[data-page=todo]').click()")
                # Move off the advanced source before deleting its independent record.
                window.evaluate_js("document.querySelector('[data-page=chat]').click();document.getElementById('new-chat').click()")
                wait_script("!document.getElementById('chat-page').hidden && document.getElementById('page-title').textContent!=='我的待辦'")
                time.sleep(.3)
                p=api.call('delete_preview',{'ids':[source]});assert p['ok'], 'todo_source_delete_preview_failed'
                deleted=api.call('delete_confirm',{'token':p['data']['token']});assert deleted['ok'], 'todo_source_delete_failed'
                window.evaluate_js("document.querySelector('[data-page=activity]').click();document.querySelector('[data-page=todo]').click()")
                wait_script("document.getElementById('page-content').textContent.includes('來源對話已刪除')")
                assert session.store.todo(overdue['id'])['state']=='done','deleted_source_removed_todo'
                report['checks'].append('todo_real_inbox_source_zero_dispatch_description_search_due_filters_transitions_duplicate_save_empty_cancel_small_light_maximized')
                report['checks'].append('todo_main_source_navigation_preserves_unsent_draft_and_deleted_source_keeps_copy_zero_dispatch')
                report['viewport']=window.evaluate_js("({width:innerWidth,height:innerHeight,devicePixelRatio})")
                report['text']=window.evaluate_js('document.body.innerText')
                report['state']=api.call('state',{})
                # A separate empty offline fixture; normal/company data never reused.
                from desktop_app.demo_login import authenticate_demo
                from desktop_app.config import DEFAULT
                with tempfile.TemporaryDirectory(prefix='qa-login-ui-') as demo_folder:
                    grant=authenticate_demo('admin','admin',demo_folder)
                    demo=WebSession(directory=demo_folder,config=DEFAULT,demo_session=grant)
                    original_api=api
                    try:
                        # Keep the real window open long enough to verify its logged-out veil.
                        # pywebview keeps the original exposed object; route its fixture session.
                        api._s=demo;api._closing=False
                        window.evaluate_js("document.getElementById('new-chat').click()")
                        wait_script("document.getElementById('logout') && !document.getElementById('logout').hidden && document.getElementById('identity').textContent.includes('離線展示已登入')")
                        window.evaluate_js("document.querySelector('[data-page=settings]').click();window.demoDenied=null;window.pywebview.api.call('connection_save',{endpoint:'https://blocked.example.test/v1'}).then(r=>window.demoDenied=r)")
                        wait_script("window.demoDenied && !window.demoDenied.ok")
                        assert demo.profiles.data.get('endpoint','')=='','demo_changed_endpoint'
                        window.evaluate_js("document.querySelector('[data-page=todo]').click()")
                        wait_script("document.getElementById('page-title').textContent==='我的待辦'")
                        capture('demo-login-workspace.png')
                        window.evaluate_js("document.getElementById('message-input').value='登出前的合成草稿';document.getElementById('message-input').dispatchEvent(new Event('input'))")
                        api._window=None
                        window.evaluate_js("document.getElementById('logout').click()")
                        wait_script("document.getElementById('modal').open")
                        window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='登出').click()")
                        wait_script("document.body.textContent.includes('已登出。請重新啟動並登入。')")
                        window.evaluate_js("window.demoBypass=null;window.pywebview.api.call('state',{}).then(r=>window.demoBypass=r)")
                        wait_script("window.demoBypass && !window.demoBypass.ok")
                        assert window.evaluate_js("document.querySelector('.app-shell').hidden && document.querySelector('.app-shell').inert"),'logout_navigation_remained'
                        snapshot=window.evaluate_js('window.qaDraftSnapshot()')
                        assert snapshot and snapshot['text']=='登出前的合成草稿','logout_lost_close_snapshot'
                        assert api.call('save_draft',snapshot)['ok'],'logout_drain_failed'
                        capture('demo-logout.png')
                        report['checks'].append('offline_demo_login_workspace_network_settings_denied_logout_veil_and_bridge_navigation_bypass_rejected')
                    finally:
                        api._s=session;api._closing=False;api._window=window
                        demo.close()
                report['status']='passed'
            except Exception as e:
                report['error_type']=type(e).__name__
                # This runner contains synthetic data only; keep the assertion location.
                import traceback
                report['error_line']=traceback.extract_tb(e.__traceback__)[-1].lineno
                report['runner_line']=[frame.lineno for frame in traceback.extract_tb(e.__traceback__)
                                       if Path(frame.filename).resolve()==Path(__file__).resolve()][-1]
                report['runner_trace']=[frame.lineno for frame in traceback.extract_tb(e.__traceback__)
                                       if Path(frame.filename).resolve()==Path(__file__).resolve()]
                try:capture('failure.png')
                except Exception:pass
            finally:
                (destination/('result-workspace.json' if workspace_only else 'result-autonomy.json' if autonomy_only else 'result-agent-followup.json' if agent_followup_only else 'result-agent.json' if agent_only else 'result-v1.json' if v1_only else 'result-skills.json' if skills_only else 'result.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                window.destroy()
        try:webview.start(inspect,gui='edgechromium',debug=False,private_mode=True)
        finally:
            session.close();about.ROOT=publisher_root
    print(json.dumps({'status':report['status'],'checks':report['checks']}))
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
