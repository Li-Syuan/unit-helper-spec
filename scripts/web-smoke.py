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


def main():
    destination=Path(__file__).resolve().parents[1]/'artifacts'/'web-smoke'
    destination.mkdir(parents=True,exist_ok=True)
    report={'status':'failed','checks':[]}
    with tempfile.TemporaryDirectory() as tmp:
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
                time.sleep(.4);capture('dark.png')
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
                report['checks'].append('provider_failure_preserves_input_and_messages_no_fallback')
                window.evaluate_js("document.getElementById('dialogue-task-mode').click()")
                time.sleep(.3)
                assert window.evaluate_js("document.querySelectorAll('#dialogue-messages .message').length")==0,'mode_not_reset'
                for text in ('我要建立追蹤任務','A類庫存','公司核准資料庫','資料追蹤','每天08:00'):dialogue_send(text)
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
                profiles.set_endpoint('https://fixture.example.test/v1');profiles.set_wire_mode('assistants')
                pid=profiles.save('合成公司助理','asst_synthetic')
                profiles.key=lambda:'synthetic-test-key'
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
                dialogue_send('合成第一題');dialogue_send('接續合成追問')
                assert len(company_mock.threads)==1 and len(company_mock.runs)==2,'company_thread_continuity'
                assert window.evaluate_js("document.getElementById('dialogue-mode-label').textContent.includes('公司助理')"),'company_badge'
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
                report['checks'].append('company_setup_and_metadata_probe_no_model_dispatch')
                report['checks'].append('search_consent_no_dispatch_reopen_policy_and_exactly_one_mock_search')
                report['viewport']=window.evaluate_js("({width:innerWidth,height:innerHeight,devicePixelRatio})")
                report['text']=window.evaluate_js('document.body.innerText')
                report['state']=api.call('state',{})
                report['status']='passed'
            except Exception as e:
                report['error_type']=type(e).__name__
                # This runner contains synthetic data only; keep the assertion location.
                import traceback
                report['error_line']=traceback.extract_tb(e.__traceback__)[-1].lineno
                report['runner_line']=[frame.lineno for frame in traceback.extract_tb(e.__traceback__)
                                       if Path(frame.filename).resolve()==Path(__file__).resolve()][-1]
            finally:
                (destination/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                window.destroy()
        try:webview.start(inspect,gui='edgechromium',debug=False,private_mode=True)
        finally:session.close()
    print(json.dumps({'status':report['status'],'checks':report['checks']}))
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
