"""Real WebView diagnostic UI; all services and data are synthetic, no live API."""
import json
import time
from unittest.mock import patch
from desktop_app.assistant_errors import AssistantFailure


def journey(session, api, window, capture, wait, report):
    js = window.evaluate_js
    pid = session.profiles.items()[0]['id']
    if pid == 'demo':pid = next(r['id'] for r in session.profiles.items() if r['id'] != 'demo')
    other = session.profiles.save('合成：權限檢查未通過', 'asst_synthetic_denied')
    with patch.object(session.profiles, 'respond', return_value='synthetic invalid format'):
        session.agents.probe(pid, True)
    with patch.object(session.profiles, 'respond', side_effect=AssistantFailure('FORBIDDEN', 'run_create', http_status=403)):
        session.activation.test(other, True)
    window.restore();window.resize(1280, 860)
    js("document.dispatchEvent(new Event('qa-activation-open'))")
    root = '.connection-diagnostics[data-profile-id="' + pid + '"]'
    denied = '.connection-diagnostics[data-profile-id="' + other + '"]'
    def query(selector):return 'document.querySelector(' + json.dumps(selector) + ')'
    def click(selector):js(query(selector) + '.click()')
    wait(query(root + ' [data-diagnostic-status=failed]'))
    wait(query(denied + ' [data-diagnostic-check=chat]') + '?.textContent.includes("FORBIDDEN")')
    assert js(query(root + ' [data-diagnostic-check=chat]') + '.dataset.diagnosticStatus') == 'passed'
    assert js(query(root + ' [data-diagnostic-action=chat]') + '!==null')
    js(query(root) + '.scrollIntoView({block:"start"})');capture('diagnostics-dark.png')
    click(root + ' [data-diagnostic-action=report]')
    wait(query(root + ' [data-diagnostic-report=preview]'))
    preview = js(query(root + ' [data-diagnostic-report=preview]') + '.value')
    assert 'asst_synthetic' not in preview and 'synthetic.example.test' not in preview
    # Explicit clipboard denial: the existing preview must survive, with save offered.
    js("window.originalDiagnosticClipboard=Object.getOwnPropertyDescriptor(navigator,'clipboard');Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('synthetic denied')}}})")
    click(root + ' [data-diagnostic-action=copy-report]')
    wait(query(root) + '.textContent.includes("剪貼簿無法使用")')
    assert js(query(root + ' [data-diagnostic-report=preview]') + '.value') == preview
    js("if(window.originalDiagnosticClipboard)Object.defineProperty(navigator,'clipboard',window.originalDiagnosticClipboard);else delete navigator.clipboard")
    with patch.object(window, 'create_file_dialog', return_value=[str(session.directory / 'missing' / 'repair.md')]):
        click(root + ' [data-diagnostic-action=save-report]');wait(query(root) + '.textContent.includes("保存失敗")')
    assert js(query(root + ' [data-diagnostic-report=preview]') + '.value') == preview
    exported = session.directory / 'synthetic-repair.md'
    with patch.object(window, 'create_file_dialog', return_value=[str(exported)]):
        click(root + ' [data-diagnostic-action=save-report]');wait(query(root) + '.textContent.includes("工作單已保存")')
    assert exported.read_text('utf-8') == preview
    click(root + ' [data-diagnostic-action=hide-report]')
    # One selected work-format check, cancellation before consent sends nothing.
    calls = []
    def response(messages, purpose, binding, context=None):
        calls.append(context)
        content = messages[0]['content']
        return content[content.index('{'):]
    work = root + ' [data-diagnostic-check=work]'
    with patch.object(session.profiles, 'respond', side_effect=response):
        click(work + ' [data-diagnostic-action=retest]')
        click(work + ' [data-diagnostic-action=cancel-retest]');assert not calls
        click(work + ' [data-diagnostic-action=retest]')
        click(work + ' [data-diagnostic-action=confirm-retest]');assert not calls
        js(query(work + ' [data-diagnostic-consent=work]') + '.checked=true')
        click(work + ' [data-diagnostic-action=confirm-retest]')
        wait(query(work) + '?.dataset.diagnosticStatus==="passed"')
    assert len(calls) == 3
    assert js(query(denied + ' [data-diagnostic-check=chat]') + '.dataset.diagnosticStatus') == 'failed'
    js("document.getElementById('theme-toggle').click()")
    wait("document.body.dataset.theme==='light'");window.resize(1050, 700)
    js(query(root) + '.scrollIntoView({block:"start"})');time.sleep(.2);capture('diagnostics-light-small.png')
    button = query(root + ' [data-diagnostic-action=report]')
    js(button + '.scrollIntoView({block:"center"})')
    assert js('(()=>{const r=' + button + '.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight&&r.right<=innerWidth})()')
    js('window.qaSkillUI.closeModal()')
    # Failed conversation: preserve the old messages and the exact unsent text.
    revision = session.profiles.snapshot(pid)['revision']
    thread = session.dialogue.start('chat', f'company:{pid}:{revision}')
    with patch.object(session.profiles, 'respond', return_value='合成既有回覆'):
        session.dialogue.send(thread['id'], '合成第一輪', 'diagnostics-first')
    with patch.object(session.profiles, 'respond', side_effect=AssistantFailure('TIMEOUT', 'run_poll')):
        try:session.dialogue.send(thread['id'], '合成待送內容', 'diagnostics-failed')
        except AssistantFailure:pass
    js('window.qaDialogueOpen(' + json.dumps(thread['id']) + ')')
    wait("document.querySelector('[data-diagnostic-action=open-dialogue]')")
    draft = js("document.getElementById('dialogue-input').value")
    click('[data-diagnostic-action=open-dialogue]')
    wait("document.querySelector('.diagnostic-request')?.textContent.includes('TIMEOUT')")
    with patch.object(session.profiles, 'respond', side_effect=AssertionError('diagnostic must not send')):
        click('#modal [data-diagnostic-action=report]')
        wait("document.querySelector('#modal [data-diagnostic-report=preview]')")
        assert not js("document.querySelector('#modal [data-diagnostic-report=preview]').value.includes('合成待送內容')")
        click('#modal [data-diagnostic-action=close]')
    assert js("document.getElementById('dialogue-input').value") == draft
    assert len(session.dialogue.state(thread['id'])['messages']) == 2
    report['checks'].append('diagnostics_two_profiles_partial_capabilities_safe_report_clipboard_denial_save_failure_export_selected_retest_chat_failure_draft_preserved_dark_light_small')
    report['not_tested'] += ['company_Copilot', 'native_file_picker_manual', 'diagnostic_physical_clipboard']
