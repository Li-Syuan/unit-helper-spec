"""Actual native sign-in and WebView lifecycle; isolated demo fixture only."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import json,threading,time,tkinter as tk
from pathlib import Path
from unittest.mock import patch
import webview
from desktop_app.login_view import LoginView
from desktop_app.web_app import launch
from desktop_app.web_session import WebSession
report={'status':'failed','company_real':'not_tested','checks':[]}; directories=[];threads=[]
def login(directory,**kwargs):
 assert kwargs=={'demo':True}
 root=tk.Tk();view=LoginView(root,directory,demo=True)
 def submit():
  view.employee.set('admin');view.password.set('admin');view.submit()
 root.after(300,submit);root.mainloop();result=view.result;root.destroy()
 assert result and result.current()['mode']=='demo_login'
 report['checks'].append('actual_native_demo_login_before_workspace');return result
def session(*args,**kwargs):
 directories.append(Path(kwargs['directory']));return WebSession(*args,**kwargs)
original=webview.create_window
def create(*args,**kwargs):
 window=original(*args,**kwargs)
 def loaded():
  def check():
   try:
    for _ in range(150):
     if window.evaluate_js("document.getElementById('identity').textContent.includes('離線展示已登入')"):break
     time.sleep(.1)
    else:raise AssertionError('workspace_not_ready')
    window.evaluate_js("document.querySelector('[data-page=todo]').click();document.getElementById('message-input').value='合成登出草稿';document.getElementById('message-input').dispatchEvent(new Event('input'));document.getElementById('logout').click()")
    time.sleep(.2)
    window.evaluate_js("Array.from(document.querySelectorAll('#modal-actions button')).find(b=>b.textContent==='登出').click()")
    report['checks'].append('actual_logout_with_unsent_draft_requested')
   except Exception as e:
    report['error_type']=type(e).__name__;window.destroy()
  t=threading.Thread(target=check);threads.append(t);t.start()
 window.events.loaded+=loaded;return window
with patch('desktop_app.login_view.show_login',side_effect=login),patch('desktop_app.web_app.WebSession',side_effect=session),patch('webview.create_window',side_effect=create):
 ok=launch(demo_login=True)
for t in threads:t.join(5)
assert ok and 'error_type' not in report and len(report['checks'])==2,report
assert directories and all(not p.exists() for p in directories),'demo_data_not_removed'
report['checks'].append('native_webview_closed_and_temporary_workspace_removed');report['status']='passed'
destination=ROOT/'artifacts/login-launch';destination.mkdir(parents=True,exist_ok=True);(destination/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
