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
    script='\n'.join((folder/name).read_text('utf-8') for name in ('app.js','dialogue.js','author.js'))
    policy=("default-src 'none'; img-src data:; style-src 'nonce-"+nonce+"'; script-src 'nonce-"+nonce+"' 'unsafe-eval'; "
            "connect-src 'none'; font-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'")
    html=html.replace('<!--APP_STYLE-->',f'<meta http-equiv="Content-Security-Policy" content="{policy}"><style nonce="{nonce}">{css}</style>')
    html=html.replace('<!--APP_SCRIPT-->',f'<script nonce="{nonce}">{script}</script>')
    assets=folder.parent/'assets'
    for tag,path in [('__BRAND_DARK__',assets/'qa-agent-64.png'),('__BRAND_LIGHT__',assets/'light'/'qa-agent-64.png')]:
        if path.exists():html=html.replace(tag,'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode('ascii'))
        else:html=html.replace(tag,'')
    return html


def launch(config_path=None, groq_trial=False):
    from .branding import set_windows_identity
    from .display import initialize_dpi
    set_windows_identity();initialize_dpi()
    session=None
    login_session=None
    try:
        import webview
        html=application_html()
        from .config import load_config, data_directory
        config=None if groq_trial else load_config(config_path or data_directory()/'config.json')
        if config and config['identity_mode']=='company':
            from .login_view import show_login
            login_session=show_login(data_directory())
            if login_session is None:return True
        session=WebSession(config=config,groq_trial=groq_trial,login_session=login_session)
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
        closing=[False];finished=[False]
        def on_closing():
            if finished[0]:return True
            if not closing[0]:
                closing[0]=True
                api._closing=True
                def drain():
                    try:
                        draft=window.evaluate_js('window.qaSetClosing && window.qaSetClosing(true); window.qaDraftSnapshot ? window.qaDraftSnapshot() : null')
                        if draft:
                            result=api.call('save_draft',draft)
                            if not result['ok']:
                                closing[0]=False
                                api._closing=False
                                window.evaluate_js("window.qaSetClosing && window.qaSetClosing(false);document.getElementById('draft-status').textContent='保存失敗，請重試；視窗尚未關閉。'")
                                return
                    except Exception:
                        closing[0]=False
                        api._closing=False
                        try:window.evaluate_js('window.qaSetClosing && window.qaSetClosing(false)')
                        except Exception:pass
                        return
                    with api._lock:session.close()
                    finished[0]=True;window.destroy()
                threading.Thread(target=drain,daemon=False).start()
            return False
        window.events.closing+=on_closing
        webview.start(gui='edgechromium',debug=False,private_mode=True)
        return True
    except Exception as exc:
        from .support import record
        from .config import data_directory
        record(session.directory if session else data_directory(),'startup',exc)
        # A missing WebView2 runtime must not silently switch data or renderers.
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk();root.withdraw()
        messagebox.showerror('新版介面未能啟動','請確認已安裝 Microsoft Edge WebView2 Runtime 與專案套件。\n可使用 start-tk.bat 開啟備用 Tkinter 介面。',parent=root)
        root.destroy();return False
    finally:
        if session:session.close()
        elif login_session:login_session.close()
