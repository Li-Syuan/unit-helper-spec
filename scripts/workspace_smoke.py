"""rc4 UI journey for web-smoke.py; all data and model replies are synthetic."""
import json
import time
from unittest.mock import patch


def journey(session,api,window,capture,wait,report):
    js=window.evaluate_js
    def click(label,scope='body'):
        js("(()=>{const b=Array.from(document.querySelectorAll("+json.dumps(scope+' button')+")).find(n=>n.textContent==="+json.dumps(label)+");if(!b)throw Error('button_missing');b.click();})()")
    def value(selector,text):
        js("(()=>{const n=document.querySelector("+json.dumps(selector)+");n.value="+json.dumps(text)+";n.dispatchEvent(new Event('input',{bubbles:true}));})()")
    def send(text):
        value('#dialogue-input',text);js("document.getElementById('dialogue-send').click()")
    def nav(page):js("window.qaSkillUI.navigate("+json.dumps(page)+")")
    def fits(selector):
        return js("(()=>{const e=document.querySelector("+json.dumps(selector)+");const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&r.left>=0&&r.right<=innerWidth+2&&r.bottom<=innerHeight+2;})()")
    if js("document.getElementById('modal').open"):click('返回工作區','#modal-actions')
    wait("window.qaDialogueContext()?.id && document.getElementById('workspace-skill').options.length>1")
    assert js("Array.from(document.querySelectorAll('#navigation [data-page]')).map(n=>n.dataset.page)")==['dialogue','work']
    assert session.dialogue.state(js('window.qaDialogueContext().id'))['mode']=='auto'
    capture('workspace-empty-dark.png')
    send('你好')
    wait("document.querySelectorAll('#dialogue-messages article').length===2&&!window.qaDialogueContext().busy")
    assert not session.agents.list() and not session.store.tasks()
    send('請整理本週工作報告，不搜尋；只整理已完成的介面調整')
    wait("!!document.getElementById('agent-confirm')&&!document.getElementById('dialogue-send').disabled")
    tid=js('window.qaDialogueContext().id');job=session.workspace.state(tid)['work'];assert job['state']=='ready' and not session.store.tasks()
    assert js("!document.getElementById('workspace-composing').hidden && !document.getElementById('dialogue-input').closest('[hidden]')")
    assert not js("!!document.getElementById('agent-preview')")
    # Pending composer text must never be mistaken for approved changes.
    value('#dialogue-input','尚未送出的補充');js("document.getElementById('agent-confirm').click()")
    time.sleep(.2);assert not session.store.tasks()
    value('#dialogue-input','');click('修改步驟與限制','#agent-job-panel')
    wait("document.getElementById('modal').open && !!document.getElementById('agent-edit-save')")
    value('#modal-body textarea','依原始已提供文字整理，不編造原因與負責人。')
    js("document.getElementById('agent-edit-save').click()")
    wait("!document.getElementById('modal').open&&!!document.getElementById('agent-confirm')")
    assert session.workspace.state(tid)['work']['revision']>job['revision'] and not session.store.tasks()
    js("document.getElementById('agent-confirm').scrollIntoView({block:'end'});document.getElementById('toast').hidden=true")
    assert fits('#agent-confirm')
    capture('workspace-plan-dark.png')
    js("document.getElementById('agent-confirm').click();document.getElementById('agent-confirm')?.click()")
    wait("document.getElementById('agent-job-result')?.textContent.includes('離線示範')&&!window.qaDialogueContext().busy")
    for _ in range(100):
        if not session.engine.has_inflight():break
        time.sleep(.05)
    assert len(session.store.tasks())==1 and session.store.tasks()[0]['state']=='succeeded'
    wait("document.querySelector('#agent-job-result h3')?.textContent==='這次成果'")
    wait("document.getElementById('workspace-composing').hidden")
    value('#dialogue-input','下一件工作尚未送出')
    js("document.getElementById('theme-toggle').click()")
    wait("document.body.dataset.theme==='light'")
    assert js("document.getElementById('dialogue-input').value")=='下一件工作尚未送出'
    window.resize(1050,700);time.sleep(.3)
    assert fits('#dialogue-send') and fits('#workspace-skill')
    js("document.getElementById('agent-job-result').scrollIntoView({block:'start'});document.getElementById('toast').hidden=true")
    capture('workspace-result-light.png')
    nav('work');wait("!!document.getElementById('work-status-filter')")
    assert js("document.getElementById('page-content').textContent.includes('介面調整')")
    click('自動工作','#page-content');wait("document.querySelector('[data-work-tab=schedule]').classList.contains('primary')")
    click('待辦','#page-content');wait("document.querySelector('[data-work-tab=todo]').classList.contains('primary')")
    click('工作','#page-content');wait("!!document.getElementById('work-status-filter')")
    click('查看工作','#page-content');wait("window.qaDialogueContext().id==="+json.dumps(tid)+"&&!document.getElementById('dialogue-page').hidden")
    assert js("document.getElementById('dialogue-input').value")=='下一件工作尚未送出'
    js("document.getElementById('workspace-more').click()")
    wait("document.getElementById('modal').open")
    assert js("document.getElementById('modal-body').textContent.includes('查詢')")
    click('關閉','#modal-actions')
    report['checks'].append('two_primary_entries_unified_chat_plan_edit_approval_dedup_result_work_tabs_draft_preserved_small_light')
    import copy
    from desktop_app.skills import TEMPLATE
    method=copy.deepcopy(TEMPLATE);method.update(name='合成選項方法',search=False,fields=[{'id':'include','text':'是否保留問題？','type':'boolean','options':[]}])
    skill=session.skills.save_confirm(session.skills.save_preview(method)['token'])
    js('window.qaDialogueNew()');wait('window.qaDialogueContext().id!=='+json.dumps(tid))
    wait("Array.from(document.querySelectorAll('#workspace-skill option')).some(n=>n.value==="+json.dumps(skill['id'])+")")
    js("document.getElementById('workspace-skill').value="+json.dumps(skill['id'])+";document.getElementById('workspace-skill').dispatchEvent(new Event('change'))")
    send('請整理文字工作報告')
    wait("!!document.querySelector('#agent-job-panel select')&&!window.qaDialogueContext().busy&&!document.getElementById('dialogue-send').disabled")
    assert not js("document.getElementById('dialogue-input').value")
    js("const c=document.querySelector('#agent-job-panel select');c.value='true';c.dispatchEvent(new Event('input'));document.getElementById('dialogue-send').click()")
    wait("!!document.getElementById('agent-confirm')")
    assert len(session.store.tasks())==1
    js("document.getElementById('agent-cancel').click()")
    wait("document.getElementById('workspace-composing').hidden")
    assert len(session.store.tasks())==1
    js('window.qaDialogueOpen('+json.dumps(tid)+')')
    wait('window.qaDialogueContext().id==='+json.dumps(tid)+"&&document.getElementById('workspace-skill').value===''")
    js('window.qaDialogueNew()');time.sleep(.3)
    send('幫我處理一下');wait("Array.from(document.querySelectorAll('.workspace-route button')).some(n=>n.textContent==='直接回答')")
    click('直接回答','.workspace-route');wait("document.getElementById('dialogue-input').value.includes('請直接回答')")
    assert len(session.store.tasks())==1
    report['checks'].append('skill_composer_choice_only_supplement_cancel_and_ambiguous_request_zero_execution')
    # Real integrated activation service; only transport returns fixture replies.
    from tests.test_workspace_turns import WorkspaceTurnTests
    fixture=WorkspaceTurnTests();fixture.calls=[]
    from tests.test_profiles import MemoryVault
    # Saving key uses an isolated in-memory credential fixture, never user keyring.
    secrets=MemoryVault()
    original=session.profiles.vault
    session.profiles.vault=secrets
    try:
        with patch.object(session.profiles,'respond',side_effect=fixture.activation_reply):
            js("document.dispatchEvent(new Event('qa-activation-open'))")
            wait("document.getElementById('modal').open&&!!document.getElementById('activation-endpoint')")
            value('#activation-endpoint','https://synthetic.example.test/v1')
            value('#activation-assistant-id','synthetic-ui');value('#activation-api-key','synthetic-only')
            click('保存並繼續','#modal-body')
            wait("!!document.querySelector('.activation-profile')")
            assert not fixture.calls
            from tests.test_search_tools import SEARCH_TOOL
            with patch.object(session.profiles,'inspect_assistant',return_value={'search_candidates':[SEARCH_TOOL]}):
                js("document.querySelector('.activation-search').open=true")
                click('讀取這位助理的工具宣告','#modal-body')
                wait("document.querySelectorAll('.activation-search input').length===2")
                js("document.querySelectorAll('.activation-search input').forEach(n=>n.checked=true)")
                click('保存選取的搜尋核准','#modal-body')
                wait("document.querySelector('.capability-summary').textContent.includes('已核准，待測試')")
            assert not fixture.calls
            click('測試並開始使用','#modal-body');time.sleep(.1);assert not fixture.calls
            js("document.querySelector('.activation-tests input[type=checkbox]').checked=true")
            click('測試並開始使用','#modal-body')
            wait("Array.from(document.querySelectorAll('.activation-progress button')).some(b=>b.textContent==='開始使用')")
            assert len(fixture.calls)==8 and not any(c.get('search_authorized') for _,c in fixture.calls)
            assert js("document.querySelector('.capability-summary').textContent.includes('自動交辦：可用')")
            js("document.querySelector('.activation-progress').scrollIntoView({block:'end'});document.getElementById('toast').hidden=true")
            capture('workspace-activation-light.png')
            click('開始使用','.activation-progress')
            wait("!document.getElementById('modal').open&&window.qaDialogueContext().assistant_id.startsWith('company:')")
            assert session.dialogue.state(js('window.qaDialogueContext().id'))['mode']=='auto'
            assert not js("document.getElementById('dialogue-send').disabled")
    finally:session.profiles.vault=original
    nav('work');wait("!!document.getElementById('work-status-filter')")
    js("document.getElementById('theme-toggle').click()")
    wait("document.body.dataset.theme==='dark'")
    window.maximize();time.sleep(.3);capture('workspace-work-dark.png')
    assert fits('#work-status-filter')
    report['checks'].append('three_field_save_search_policy_before_eight_explicit_synthetic_checks_start_auto_chat_maximized')
    report['not_tested']=['real_DVC','AD','source_quality','human_usability','physical_IME']
