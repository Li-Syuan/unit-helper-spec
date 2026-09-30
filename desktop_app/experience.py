"""Offline help and user-initiated local diagnostics."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

from .about import about_text
from .branding import APP_NAME, apply_child_icons
from .display import scroll_frame, work_area

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


class AuthorPopover:
    """Small anchored identity card; no modal grab or service calls."""
    def __init__(self, app):
        self.app = app
        self.window = None
        self.bindings = []
        self.focus_timer = None

    def toggle(self, anchor):
        if self.window is not None:
            self.close()
            return
        from .about import publisher_info
        author = publisher_info()
        self.anchor = anchor
        window = self.window = tk.Toplevel(self.app.root)
        window.withdraw()
        window.overrideredirect(True)
        window.transient(self.app.root)
        window.title(APP_NAME + ' · 作者')
        body = ttk.Frame(window, style='Card.TFrame', padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='作者與聯絡方式', style='CardTitle.TLabel').pack(anchor='w')
        self.details = ttk.Label(body, text=f"姓名：{author['name']}\n工號：{author['employee_id']}\n電話：{author['phone']}",
                                 style='Surface.TLabel', wraplength=300, justify='left')
        self.details.pack(fill='x', pady=(12, 14))
        self.close_button = ttk.Button(body, text='關閉', command=self.close)
        self.close_button.pack(anchor='e')
        window.bind('<Escape>', self._escape)
        window.bind('<FocusOut>', self._focus_out, add='+')
        window.bind('<Destroy>', self._destroyed, add='+')
        self.bindings.append(('<ButtonPress>', self.app.root.bind('<ButtonPress>', self._outside, add='+')))
        self.bindings.append(('<Escape>', self.app.root.bind('<Escape>', self._escape, add='+')))
        self.app.appearance.apply(window)
        self.position()
        window.deiconify()
        self.close_button.focus_set()

    def position(self):
        if self.window is None:
            return
        window = self.window
        window.update_idletasks()
        ax, ay, width, height = work_area(self.anchor)
        margin = self.app.display.px(8)
        x = self.anchor.winfo_rootx() + self.anchor.winfo_width() + margin
        y = self.anchor.winfo_rooty()
        x = max(ax + margin, min(x, ax + width - window.winfo_reqwidth() - margin))
        y = max(ay + margin, min(y, ay + height - window.winfo_reqheight() - margin))
        window.geometry(f'+{x}+{y}')

    def _inside(self, widget, parent):
        while widget is not None:
            if widget == parent:
                return True
            widget = getattr(widget, 'master', None)
        return False

    def _outside(self, event):
        if self.window is not None and not self._inside(event.widget, self.window) and not self._inside(event.widget, self.anchor):
            self.close()

    def _escape(self, event=None):
        self.close()
        return 'break'

    def _focus_out(self, event=None):
        if self.window is not None and self.focus_timer is None:
            self.focus_timer = self.app.root.after_idle(self._check_focus)

    def _check_focus(self):
        self.focus_timer = None
        focused = self.app.root.focus_get()
        # Main-window clicks are handled by _outside. Do not close between the
        # author's button press and release, which would reopen the card.
        if self.window is not None and (focused is None or focused.winfo_toplevel() not in (self.window, self.app.root)):
            self.close()

    def _destroyed(self, event):
        if event.widget == self.window:
            self.window = None
            self._unbind()

    def _unbind(self):
        if self.focus_timer is not None:
            self.app.root.after_cancel(self.focus_timer)
            self.focus_timer = None
        for sequence, token in self.bindings:
            self.app.root.unbind(sequence, token)
        self.bindings.clear()

    def close(self):
        window, self.window = self.window, None
        self._unbind()
        if window is not None:
            window.destroy()


class ExperienceMixin:
    def show_author(self, anchor):
        if not hasattr(self, 'author_popover'):
            self.author_popover = AuthorPopover(self)
        self.author_popover.toggle(anchor)

    def show_help(self, section='快速開始'):
        window = tk.Toplevel(self.root)
        apply_child_icons(window)
        window.title(APP_NAME + ' · 說明與關於')
        self.display.size_window(window,900,610,(680,420))
        frame = scroll_frame(window, padding=16)
        frame.pack(fill='both', expand=True)
        bar = ttk.Frame(frame)
        bar.pack(fill='x', pady=(0,12))
        ttk.Label(bar, text='說明與關於', style='Section.TLabel').pack(side='left')
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
        sections.append(('關於', about_text()))
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
            self.status.set(('本機診斷完成' if code == 0 else '診斷有項目需修正') + '；報告：' + str(output) + '。組織服務仍需另行驗收。')
        self.background(run, done)
