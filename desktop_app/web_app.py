"""Windows WebView2 host using only bundled HTML/CSS/JS."""
import base64
from pathlib import Path
import secrets
import threading
from . import __version__
from .web_session import WebSession
from .web_bridge import WebBridge


def application_html():
    folder=Path(__file__).resolve().parent/'web_assets'
    nonce=secrets.token_urlsafe(24)
    html=(folder/'index.html').read_text('utf-8')
    css=(folder/'app.css').read_text('utf-8')
    script='\n'.join((folder/name).read_text('utf-8') for name in ('app.js','dialogue.js','author.js','orders.js','skills.js','memories.js','activation.js','agent-jobs.js'))
    policy=("default-src 'none'; img-src data:; style-src 'nonce-"+nonce+"'; script-src 'nonce-"+nonce+"' 'unsafe-eval'; "
            "connect-src 'none'; font-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'")
    html=html.replace('<!--APP_STYLE-->',f'<meta http-equiv="Content-Security-Policy" content="{policy}"><style nonce="{nonce}">{css}</style>')
    html=html.replace('<!--APP_SCRIPT-->',f'<script nonce="{nonce}">{script}</script>')
    assets=folder.parent/'assets'
    for tag,path in [('__BRAND_DARK__',assets/'qa-agent-64.png'),('__BRAND_LIGHT__',assets/'light'/'qa-agent-64.png')]:
        if path.exists():html=html.replace(tag,'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode('ascii'))
        else:html=html.replace(tag,'')
    return html


def launch(config_path=None, groq_trial=False, *, demo_login=False):
    from .branding import set_windows_identity
    from .display import initialize_dpi
    set_windows_identity();initialize_dpi()
    if demo_login and (config_path is not None or groq_trial):
        raise ValueError('離線展示不能載入公司設定或外部試用。')
    import tempfile
    temporary=tempfile.TemporaryDirectory(prefix='qa-login-demo-') if demo_login else None
    session=None
    login_session=None
    demo_session=None
    try:
        import webview
        html=application_html()
        from .config import load_config, data_directory
        if demo_login:
            from .config import DEFAULT
            from .login_view import show_login
            directory=Path(temporary.name)
            demo_session=show_login(directory,demo=True)
            if demo_session is None:return True
            config=DEFAULT
        else:
            config=None if groq_trial else load_config(config_path or data_directory()/'config.json')
        if config and config['identity_mode']=='company':
            from .login_view import show_login
            login_session=show_login(data_directory())
            if login_session is None:return True
        session=WebSession(directory=Path(temporary.name) if temporary else None,config=config,groq_trial=groq_trial,login_session=login_session,demo_session=demo_session,deployment_defaults=not (groq_trial or demo_login))
        api=WebBridge(session)
        webview.settings['ALLOW_DOWNLOADS']=False
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']=False
        window=webview.create_window('QA agent · '+__version__,html=html,js_api=api,width=1280,height=860,
            min_size=(800,600),background_color='#11151b',text_select=True)
        api._window=window
        from .web_chrome import apply_chrome,seal_navigation
        from .preferences import load_theme
        def loaded():
            seal_navigation(window)
            apply_chrome(window,load_theme(session.preferences_path))
        window.events.loaded+=loaded
        closing=[False];finished=[False];asking=[False]
        from .tray import TrayController,WinFormsTray
        from .preferences import load_preferences,update_preferences
        def tray_status():
            try:session.assert_identity()
            except Exception:return '登入已失效 · 請重新開啟並登入'
            count=sum(bool(row.get('enabled')) for row in session.store.schedules())
            return ('排程需檢查 · ' if session.scheduler_error else '')+f'{count} 個已啟用自動工作 · 電腦須保持運作'
        def request_exit():
            threading.Thread(target=lambda:host_close('exit',False),daemon=True).start()
        tray=TrayController(WinFormsTray(window,tray_status,request_exit))
        def host_close(value,remember=False):
            if value not in ('background','exit') or type(remember) is not bool:
                raise ValueError('關閉方式無效。')
            asking[0]=False
            if session.demo_session or api._closing:value='exit'
            if closing[0]:return {'value':'exit','saved':False}
            if value=='exit' and not api._closing and not session.demo_session:
                needs_confirmation=window.evaluate_js('!!(window.qaOrderHasUnsaved && window.qaOrderHasUnsaved() && !window.qaOrderExitConfirmed)')
                if needs_confirmation:
                    tray.show()
                    window.evaluate_js('window.qaRequestClose && window.qaRequestClose(true,'+('true' if remember else 'false')+')')
                    return {'value':'exit','saved':False,'pending':True}
            # Register first; on failure we leave the window reachable.
            if value=='background' and not tray.background():
                raise ValueError('系統匣無法啟用，視窗保持開啟。請重試或選擇退出。')
            saved=not remember
            if remember:
                try:update_preferences(session.preferences_path,{'close_behavior':value});saved=True
                except (OSError,ValueError):
                    saved=False
                    if value=='background':tray.show()
            if value=='exit':begin_exit()
            return {'value':value,'saved':saved}
        api._host_close=host_close
        def begin_exit():
            if closing[0]:return
            closing[0]=True;api._closing=True
            # Reachable even when initiated from the tray; save/drain errors stay visible.
            try:tray.show()
            except Exception:pass
            def drain():
                try:
                    draft=window.evaluate_js('window.qaSetClosing && window.qaSetClosing(true); window.qaDraftSnapshot ? window.qaDraftSnapshot() : null')
                    if draft:
                        result=api.call('save_draft',draft)
                        if not result['ok']:raise ValueError('draft_save_failed')
                    main_draft=window.evaluate_js('window.qaDialogueViewSnapshot ? window.qaDialogueViewSnapshot() : null')
                    if main_draft:
                        # Host-only local flush also works after logout/expiry and
                        # during a request; ordinary bridge authorization is unchanged.
                        result=session.continuity.save_view_for_close(main_draft)
                        import json
                        window.evaluate_js('window.qaDialogueViewSaved && window.qaDialogueViewSaved('+json.dumps({'id':main_draft['id'],'revision':result['revision']})+')')
                    # No bridge lock across pending remote I/O or scheduler shutdown.
                    session.close()
                except Exception:
                    closing[0]=False;api._closing=False
                    try:window.evaluate_js("window.qaSetClosing && window.qaSetClosing(false);document.getElementById('status-text').textContent='關閉未完成，視窗保持開啟。請確認草稿或稍後重試。'")
                    except Exception:pass
                    return
                try:tray.close()
                finally:
                    finished[0]=True;window.destroy()
            threading.Thread(target=drain,daemon=False).start()
        def on_closing():
            if finished[0]:return True
            if closing[0]:return False
            if api._closing or session.demo_session:
                begin_exit();return False
            choice=load_preferences(session.preferences_path).get('close_behavior','ask')
            if choice in ('background','exit'):
                def apply_choice():
                    try:host_close(choice)
                    except Exception:
                        try:window.evaluate_js("document.getElementById('status-text').textContent='系統匣無法啟用，視窗保持開啟；可在設定改為退出。'")
                        except Exception:pass
                threading.Thread(target=apply_choice,daemon=True).start()
            elif not asking[0]:
                asking[0]=True
                def ask():
                    try:window.evaluate_js('window.qaRequestClose && window.qaRequestClose()')
                    finally:asking[0]=False
                threading.Thread(target=ask,daemon=True).start()
            return False
        window.events.closing+=on_closing
        try:webview.start(gui='edgechromium',debug=False,private_mode=True)
        finally:
            try:tray.close()
            except Exception:pass
        return True
    except Exception as exc:
        from .support import record
        from .config import data_directory
        record(session.directory if session else Path(temporary.name) if temporary else data_directory(),'startup',exc)
        # A missing WebView2 runtime must not silently switch data or renderers.
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk();root.withdraw()
        messagebox.showerror('新版介面未能啟動','請確認已安裝 Microsoft Edge WebView2 Runtime 與專案套件。\n可使用 start-tk.bat 開啟備用 Tkinter 介面。',parent=root)
        root.destroy();return False
    finally:
        if session:session.close()
        elif login_session:login_session.close()
        if demo_session:demo_session.close()
        if temporary:temporary.cleanup()
