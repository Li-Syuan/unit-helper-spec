"""Native demo sign-in -> real WebView -> host draft flush -> logout.

The observer reads synthetic SQLite before temporary workspace cleanup.
No real AD, credentials or external API is used.
"""
import json
import os
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import webview
from desktop_app.continuity import Continuity
from desktop_app.login_view import LoginView
from desktop_app.web_app import launch
from desktop_app.web_session import WebSession

MAIN_DRAFT = '合成主對話登出草稿，必須由宿主關閉流程保存。'
ADVANCED_DRAFT = '合成進階登出草稿'


def main():
    destination = ROOT / 'artifacts' / 'login-launch'
    destination.mkdir(parents=True, exist_ok=True)
    report = {'status': 'failed', 'company_real': 'not_tested', 'checks': []}
    directories, threads = [], []
    finished = threading.Event()
    report_lock = threading.RLock()

    def write_report():
        with report_lock:
            (destination / 'result.json').write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    def fail(code):
        with report_lock:
            report.setdefault('errors', []).append(code)
        write_report()

    def watchdog():
        # This isolated smoke subprocess alone is terminated on timeout. A broken
        # on_closing handler can veto destroy(), so that is not sufficient.
        if not finished.wait(60):
            fail('watchdog_timeout_60s_cleanup_not_confirmed')
            os._exit(1)

    threading.Thread(target=watchdog, daemon=True).start()

    def login(directory, **kwargs):
        assert kwargs == {'demo': True}
        root = tk.Tk()
        view = LoginView(root, directory, demo=True)

        def submit():
            view.employee.set('admin')
            view.password.set('admin')
            view.submit()

        root.after(300, submit)
        root.mainloop()
        result = view.result
        root.destroy()
        assert result and result.current()['mode'] == 'demo_login'
        report['checks'].append('actual_native_demo_login_before_workspace')
        return result

    def session(*args, **kwargs):
        directories.append(Path(kwargs['directory']))
        return WebSession(*args, **kwargs)

    original_create = webview.create_window
    original_flush = Continuity.save_view_for_close

    def observe_flush(continuity, value):
        try:
            assert value['text'] == MAIN_DRAFT, 'host_received_wrong_main_draft'
            assert continuity.session.demo_session._closed.is_set(), 'flush_not_after_logout'
            with continuity.store.connect() as db:
                before = db.execute('SELECT draft FROM thread_views WHERE thread_id=?',
                                    (value['id'],)).fetchone()
                assert before and before['draft'] != MAIN_DRAFT, 'host_flush_not_observable'
            result = original_flush(continuity, value)
            with continuity.store.connect() as db:
                saved = db.execute('SELECT draft,revision FROM thread_views WHERE thread_id=?',
                                   (value['id'],)).fetchone()
                assert saved['draft'] == MAIN_DRAFT, 'main_draft_not_persisted'
                assert saved['revision'] == result['revision'], 'main_draft_revision_mismatch'
            with continuity.session.store.connection() as db:
                assert db.execute('SELECT 1 FROM drafts WHERE text=?',
                                  (ADVANCED_DRAFT,)).fetchone(), 'advanced_draft_not_persisted'
            report['checks'].append('host_flush_after_logout_persists_main_and_advanced_drafts_before_cleanup')
            return result
        except Exception as exc:
            fail('host_flush_' + type(exc).__name__)
            raise

    def create(*args, **kwargs):
        window = original_create(*args, **kwargs)

        def loaded():
            def check():
                try:
                    for _ in range(150):
                        if window.evaluate_js(
                            "document.getElementById('identity').textContent.includes('離線展示已登入')"
                            " && window.qaDialogueViewSnapshot && !!window.qaDialogueViewSnapshot()"
                            " && document.getElementById('dialogue-status').textContent.includes('示範模式')"
                        ):
                            break
                        time.sleep(.1)
                    else:
                        raise AssertionError('workspace_main_dialogue_not_ready')
                    window.evaluate_js(
                        "document.querySelector('[data-page=todo]').click();"
                        "document.getElementById('message-input').value=" + json.dumps(ADVANCED_DRAFT) + ";"
                        "document.getElementById('message-input').dispatchEvent(new Event('input'));"
                        "document.getElementById('logout').click()"
                    )
                    for _ in range(30):
                        if window.evaluate_js("document.getElementById('modal').open"):
                            break
                        time.sleep(.1)
                    else:
                        raise AssertionError('logout_confirmation_not_open')
                    # Settle navigation's save, then bypass input debounce for the
                    # main draft to prove this save originates in the host flush.
                    time.sleep(.3)
                    window.evaluate_js(
                        "document.getElementById('dialogue-input').value=" + json.dumps(MAIN_DRAFT) + ";"
                        "Array.from(document.querySelectorAll('#modal-actions button'))"
                        ".find(b=>b.textContent==='登出').click()"
                    )
                    report['checks'].append('actual_logout_with_two_unsent_drafts_requested')
                except Exception as exc:
                    fail('ui_' + type(exc).__name__)
                    window.destroy()

            thread = threading.Thread(target=check, daemon=True)
            threads.append(thread)
            thread.start()

        window.events.loaded += loaded
        return window

    try:
        with patch('desktop_app.login_view.show_login', side_effect=login), \
                patch('desktop_app.web_app.WebSession', side_effect=session), \
                patch('webview.create_window', side_effect=create), \
                patch.object(Continuity, 'save_view_for_close', new=observe_flush):
            ok = launch(demo_login=True)
        for thread in threads:
            thread.join(5)
        assert ok and not report.get('errors'), 'native_lifecycle_failed'
        assert len(report['checks']) == 3, 'missing_host_flush_evidence'
        assert directories and all(not path.exists() for path in directories), 'demo_data_not_removed'
        report['checks'].append('native_webview_closed_and_temporary_workspace_removed')
        report['status'] = 'passed'
    except Exception as exc:
        fail('lifecycle_' + type(exc).__name__)
    finally:
        finished.set()
        write_report()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
