"""Offline help and an isolated, real-workflow practice workspace."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import ttk

from . import __version__
from .branding import APP_NAME, apply_child_icons
from .preferences import load_onboarding, save_onboarding

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = [('使用手冊', 'USER-GUIDE.md'), ('資料使用與功能限制', 'DATA-USAGE.md'),
             ('第三方套件授權', 'THIRD-PARTY-NOTICES.md')]


def manual_sections():
    sections = []
    for label, filename in DOCUMENTS:
        try:
            content = (ROOT / 'docs' / filename).read_text(encoding='utf-8-sig')
        except OSError:
            sections.append((label, '文件無法讀取，請向維護者取得完整程式資料夾。'))
            continue
        current, lines = label, []
        for line in content.splitlines():
            if line.startswith('## '):
                if lines:
                    sections.append((current, '\n'.join(lines).strip()))
                current, lines = line[3:].strip(), []
            else:
                lines.append(line)
        if lines:
            sections.append((current, '\n'.join(lines).strip()))
    licenses = ROOT / 'docs' / 'licenses'
    if licenses.is_dir():
        for path in sorted(licenses.rglob('*')):
            if path.is_file() and path.suffix.lower() in ('.txt', '.md', ''):
                try:
                    body = path.read_text(encoding='utf-8-sig')
                except (OSError, UnicodeError):
                    continue
                sections.append(('授權 · ' + str(path.relative_to(licenses)), body))
    return sections


class ExperienceMixin:
    def setup_experience(self, show_welcome=True):
        self._experience_processes = []
        self._experience_after = None
        self.tutorial_controller = None
        if getattr(self, 'tutorial', False):
            self.tutorial_controller = TutorialController(self)
        elif show_welcome and load_onboarding(self.preferences_path) == 'new':
            self._experience_after = self.root.after_idle(self.show_welcome)

    def _save_onboarding(self, status):
        try:
            save_onboarding(self.preferences_path, status)
        except OSError:
            self.status.set('本次操作仍有效，但無法保存導覽偏好；下次開啟可能再次顯示。')

    def show_welcome(self):
        self._experience_after = None
        if self.closed:
            return
        window = tk.Toplevel(self.root)
        apply_child_icons(window)
        window.title('歡迎使用 ' + APP_NAME)
        window.transient(self.root)
        window.geometry('640x390')
        window.minsize(560, 360)
        body = ttk.Frame(window, padding=28)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='先完成一件小事，認識 QA agent', style='Section.TLabel').pack(anchor='w')
        ttk.Label(body, text='不用 API key，也不用公司的資料。\n用獨立體驗視窗，試著查資料、批准計畫，再把結果交给示範助理。',
                  wraplength=555, justify='left').pack(anchor='w', pady=18)
        ttk.Label(body, text='示範回覆只展示流程，不是真正 AI 分析。\n體驗不混入個人對話或排程；可隨時退出。',
                  style='Muted.TLabel', wraplength=550).pack(anchor='w', pady=(0, 20))
        def choose(action, status='invited'):
            self._save_onboarding(status)
            window.destroy()
            if action:
                action()
        for title, action, state in [('先體驗，不用設定', self.start_tutorial, 'invited'),
                                     ('設定公司助理', lambda:self.book.select(self.tabs['settings']), 'invited'),
                                     ('稍後再說', None, 'skipped')]:
            ttk.Button(body, text=title, command=lambda a=action,s=state:choose(a,s),
                       style='Primary.TButton' if action == self.start_tutorial else 'TButton').pack(fill='x', pady=4)
        window.protocol('WM_DELETE_WINDOW', lambda:choose(None,'skipped'))
        self.appearance.apply(window)
        window.focus_set()
        return window

    def show_help(self, section='快速開始'):
        window = tk.Toplevel(self.root)
        apply_child_icons(window)
        window.title(APP_NAME + ' · 說明與關於')
        window.geometry('900x610')
        window.minsize(680, 420)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill='both', expand=True)
        bar = ttk.Frame(frame)
        bar.pack(fill='x', pady=(0,12))
        ttk.Label(bar, text='說明與關於', style='Section.TLabel').pack(side='left')
        ttk.Button(bar,text='快速體驗',command=lambda:self.safe(self.start_tutorial)).pack(side='right')
        ttk.Button(bar,text='回報問題',command=lambda:(window.destroy(), self.book.select(self.tabs['issue']))).pack(side='right',padx=8)
        ttk.Button(bar,text='環境診斷',command=lambda:self.safe(self._help_diagnose)).pack(side='right')
        pane = ttk.Panedwindow(frame, orient='horizontal')
        pane.pack(fill='both', expand=True)
        toc = tk.Listbox(pane, width=24, exportselection=False, activestyle='none')
        pane.add(toc, weight=0)
        content_frame = ttk.Frame(pane)
        pane.add(content_frame, weight=1)
        content = tk.Text(content_frame, wrap='char', padx=18, pady=16, spacing3=3, state='disabled')
        scroll = ttk.Scrollbar(content_frame, command=content.yview)
        scroll.pack(side='right',fill='y')
        content.pack(fill='both',expand=True)
        content.configure(yscrollcommand=scroll.set)
        sections = manual_sections()
        sections.append(('關於', f'{APP_NAME} {__version__}\n\nWindows 本機桌面應用。\n維護聯絡方式：尚未設定。請使用問題回報保存紀錄，再依單位指定管道提供。\n\n回報目前只存本機，不會自動送給維護者。\n環境診斷不呼叫模型或資料庫；通過不代表公司接線完成。\n\n第三方授權：請選左側「第三方套件授權」，完整文字存於程式 docs/licenses。'))
        for title, _ in sections:
            toc.insert('end', title)
        def render(event=None):
            if not toc.curselection():
                return
            title, body = sections[toc.curselection()[0]]
            content.configure(state='normal')
            content.delete('1.0','end')
            content.insert('end', title + '\n\n' + body)
            content.configure(state='disabled')
            content.yview_moveto(0)
        toc.bind('<<ListboxSelect>>', render)
        target = next((i for i,(title,_) in enumerate(sections) if title == section), 0)
        toc.selection_set(target)
        toc.see(target)
        render()
        self.appearance.apply(window)
        window.help_toc, window.help_content = toc, content
        return window

    def _help_diagnose(self):
        output = self.directory / 'diagnostics' / 'environment.json'
        command = [sys.executable, str(ROOT/'scripts'/'doctor.py'),
                   '--data-dir', str(self.directory), '--output', str(output)]
        if Path(self.config_path).is_file():
            command.extend(['--config', str(self.config_path)])
        environment = os.environ.copy()
        environment['UNITHELPER_DATA_DIR'] = str(self.directory)
        def run():
            result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, timeout=120,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            return result.returncode
        def done(code):
            self.status.set(('本機診斷完成' if code == 0 else '診斷有項目需修正') + '；報告：' + str(output) + '。公司服務仍需另行驗收。')
        self.background(run, done)

    def start_tutorial(self):
        if getattr(self,'tutorial',False):
            self.status.set('請使用導覽列的「重新體驗」；它會開啟全新的隔離工作區。')
            return
        handle, marker = tempfile.mkstemp(prefix='qa-experience-',suffix='.json')
        os.close(handle)
        Path(marker).unlink()
        try:
            command = [sys.executable, '-c', 'from desktop_app.experience import tutorial_main; import sys; tutorial_main(sys.argv[1],sys.argv[2])',
                       self.theme_choice.get(), marker]
            process = subprocess.Popen(command, cwd=ROOT, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except OSError:
            Path(marker).unlink(missing_ok=True)
            raise ValueError('體驗視窗無法啟動；請確認專案環境完整。') from None
        self._experience_processes.append((process, Path(marker)))
        self._save_onboarding('invited')
        self.status.set('已開啟獨立體驗視窗。個人草稿保持原樣；體驗視窗可自行關閉。')
        if self._experience_after is None:
            self._experience_after = self.root.after(500,self._poll_experiences)

    def _poll_experiences(self):
        self._experience_after = None
        remaining=[]
        for process, marker in self._experience_processes:
            if marker.exists():
                try:
                    report=json.loads(marker.read_text(encoding='utf-8'))
                    if report.get('completed') is True:
                        self._save_onboarding('completed')
                    if report.get('settings') is True:
                        self.book.select(self.tabs['settings'])
                        self.root.deiconify(); self.root.lift()
                except (OSError,ValueError,AttributeError):
                    pass
                marker.unlink(missing_ok=True)
            if process.poll() is None:
                remaining.append((process,marker))
        self._experience_processes=remaining
        if remaining and not self.closed:
            self._experience_after=self.root.after(500,self._poll_experiences)

    def close_experience(self):
        if self._experience_after is not None:
            self.root.after_cancel(self._experience_after)
            self._experience_after=None
        if self.tutorial_controller is not None:
            self.tutorial_controller.close()
        # Separate demo windows drain their own workers and clean their temp data.
        # Never terminate them abruptly when closing the user's real workspace.
        self._experience_processes.clear()


class TutorialProgress:
    """Advance only from real workflow evidence, never a cosmetic next button."""
    def __init__(self):
        self.step=1
        self.plan_id=None
        self.task_id=None
    def filled(self):
        if self.step==1:
            self.step=2
    def observe(self, plans, tasks, result_task, selection, conversations):
        if self.step==2:
            plan=next((p for p in plans if p['kind']=='query' and p['state']=='ready'),None)
            if plan:
                self.plan_id=plan['id']; self.step=3
        if self.step==3:
            plan=next((p for p in plans if p['id']==self.plan_id),None)
            if plan and plan.get('task_id') and plan['state'] in ('executing','succeeded'):
                self.task_id=plan['task_id']; self.step=4
        if self.step==4 and result_task==self.task_id and selection:
            task=next((t for t in tasks if t['id']==self.task_id and t['state']=='succeeded'),None)
            if task:
                self.step=5
        if self.step==5:
            targets={c['id'] for c in conversations if isinstance(c.get('source'),dict) and
                     c['source'].get('kind')=='query' and c['source'].get('task_id')==self.task_id}
            if any(t['conversation_id'] in targets and t['kind']=='summarize' and t['state']=='succeeded' for t in tasks):
                self.step=6
        return self.step


class TutorialController:
    TEXT = {1:('1 / 5  填入範例條件','先填入合成查詢條件。資料只用於本次體驗。','填入範例條件'),
            2:('2 / 5  建立並檢視 Plan','按查詢頁的「建立查詢計畫」，看看將執行的條件；目前還沒有查資料。','前往查資料'),
            3:('3 / 5  自行批准','閱讀計畫預覽，按「批准此修訂」。不按批准，就不會執行。','前往批准計畫'),
            4:('4 / 5  查看並選取資料','查詢完成後打開結果，點選至少一列；Ctrl 可複選。','查看體驗結果'),
            5:('5 / 5  預覽後轉交','按「交給助理整理」，選取列與示範助理，檢視預覽，再確認送出。','交給示範助理'),
            6:('體驗完成','你已完成查詢 → 批准 → 選取資料 → 助理整理。示範文字不是 AI 分析。','設定公司助理')}
    def __init__(self,app):
        self.app=app; self.progress=TutorialProgress(); self.after_id=None; self.completed=False
        self.marker=None; self.restart=False; self._highlighted=[]
        app.root.title('QA agent · 獨立體驗工作區（合成資料）')
        children=app.root.winfo_children()
        self.panel=ttk.Frame(app.root,padding=(16,8),style='Surface.TFrame')
        self.panel.pack(side='bottom',fill='x',before=children[0] if children else None)
        self.panel.columnconfigure(0,weight=1)
        text=ttk.Frame(self.panel); text.grid(row=0,column=0,sticky='nsew',padx=(0,14))
        self.heading=ttk.Label(text,style='Section.TLabel'); self.heading.pack(anchor='w')
        self.description=ttk.Label(text,wraplength=610,style='Muted.TLabel')
        self.description.pack(anchor='w',pady=(3,0))
        text.bind('<Configure>',lambda event:self.description.configure(wraplength=max(240,event.width)))
        controls=ttk.Frame(self.panel); controls.grid(row=0,column=1,sticky='e')
        self.action=ttk.Button(controls,style='Primary.TButton',command=lambda:app.safe(self.act))
        self.action.pack(side='left',padx=(0,8))
        ttk.Button(controls,text='重新體驗',command=self.repeat).pack(side='left',padx=(0,8))
        self.exit_button=ttk.Button(controls,text='退出體驗',command=app.close)
        self.exit_button.pack(side='left')
        # Guardrails are also enforced by App's tutorial mode; hide irrelevant navigation.
        for name in ('settings','schedule','issue'):
            app.nav_buttons[name].configure(state='disabled')
        app.appearance.apply(self.panel)
        app.book.select(app.tabs['query'])
        self.render()
        self.after_id=app.root.after(150,self.poll)
    def render(self):
        title,text,action=self.TEXT[self.progress.step]
        self.heading.configure(text=title); self.description.configure(text=text); self.action.configure(text=action)
        for widget, style in self._highlighted:
            if widget.winfo_exists(): widget.configure(style=style)
        self._highlighted=[]
        labels={2:'建立查詢計畫',3:'批准此修訂',5:'交給助理整理'}
        label=labels.get(self.progress.step)
        def highlight(widget):
            if isinstance(widget,ttk.Button) and label and widget.cget('text')==label:
                self._highlighted.append((widget,widget.cget('style')))
                widget.configure(style='Primary.TButton')
            for child in widget.winfo_children(): highlight(child)
        highlight(self.app.root)
        self.exit_button.configure(text='返回工作區' if self.progress.step==6 else '退出體驗')
    def fill(self):
        a=self.app
        a.query_id.set('DEMO01')
        a.render_query_fields({'from_date':'2026-01-01','to_date':'2026-01-04','category':'all'})
        a.query_plan.set(True)
        if hasattr(a,'query_summary'): a.query_summary.set(False)
        a.book.select(a.tabs['query']); self.progress.filled(); self.render()
    def act(self):
        a=self.app; step=self.progress.step
        if step==1: self.fill()
        elif step==2: a.book.select(a.tabs['query']); a.query_submit.focus_set()
        elif step==3: a.book.select(a.tabs['work'])
        elif step==4:
            task=a.store.task(self.progress.task_id)
            if task['state']!='succeeded': a.status.set('查詢尚未完成，請稍候。')
            else: a.show_result(self.progress.task_id)
        elif step==5: a.open_result_handoff()
        elif step==6:
            self.report(settings=True); a.close()
    def report(self,settings=False):
        if self.marker:
            Path(self.marker).write_text(json.dumps({'completed':self.completed,'settings':settings}),encoding='utf-8')
    def poll(self):
        a=self.app; self.after_id=None
        if a.closed: return
        old=self.progress.step
        self.progress.observe(a.store.plans(),a.store.tasks(),a.result_task,a.table.selection(),a.store.conversations())
        if self.progress.step!=old:
            self.render()
            if self.progress.step==6:
                self.completed=True; self.report()
        self.after_id=a.root.after(200,self.poll)
    def repeat(self):
        self.restart=True; self.app.close()
        if not self.app.closed: self.restart=False
    def close(self):
        if self.after_id is not None:
            self.app.root.after_cancel(self.after_id); self.after_id=None


def tutorial_main(theme='dark',marker=None):
    """Never reads the user's config, DB, credential store, or data directory."""
    from .config import DEFAULT
    from .preferences import save_theme
    from .branding import set_windows_identity
    from .ui import App
    import gc
    repeat=True
    while repeat:
        with tempfile.TemporaryDirectory(prefix='qa-agent-practice-') as temp:
            directory=Path(temp)
            save_theme(directory/'ui-preferences.json',theme)
            set_windows_identity(); root=tk.Tk()
            app=App(root,config=copy.deepcopy(DEFAULT),directory=directory,tutorial=True,show_welcome=False)
            controller=app.tutorial_controller
            controller.marker=marker
            root.mainloop()
            repeat=controller.restart
            del controller,app,root
            gc.collect()
