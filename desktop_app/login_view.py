"""Native sign-in before either desktop host starts services or opens data."""
import queue
import threading
import tkinter as tk
from tkinter import ttk

from .authentication import authenticate, AuthenticationError
from .branding import APP_NAME, apply_icons, set_windows_identity
from .display import Display, initialize_dpi, scroll_frame
from .preferences import load_theme, load_color_style
from .theme import Appearance


class LoginView:
    def __init__(self, root, directory, *, preview=False, provider=None):
        from .about import publisher_info
        self.root, self.preview, self.provider = root, preview, provider
        self.result = None
        self.pending = False
        self.closing = False
        self.events = queue.Queue()
        root.title(APP_NAME+' · 公司登入'+('（畫面預覽）' if preview else ''))
        self.display = Display(root)
        self.display.size_window(root, 560, 690, (480, 550))
        self.appearance = Appearance(root, load_theme(directory/'ui-preferences.json'), load_color_style(directory/'ui-preferences.json'))
        self.icon, _ = apply_icons(root, theme=self.appearance.name)
        body = scroll_frame(root, padding=32)
        body.pack(fill='both', expand=True)
        brand = ttk.Frame(body)
        brand.pack(fill='x', pady=(0, 24))
        if self.icon:
            ttk.Label(brand, image=self.icon).pack(side='left', padx=(0, 12))
        ttk.Label(brand, text=APP_NAME, style='Section.TLabel').pack(side='left')
        ttk.Label(body, text='登入你的工作區', style='Section.TLabel').pack(anchor='w')
        ttk.Label(body, text='使用公司工號與密碼。成功驗證身分與使用資格後，\n才會開啟你的資料與自動工作。', wraplength=440).pack(anchor='w', pady=(8, 20))
        self.employee = tk.StringVar()
        self.password = tk.StringVar()
        ttk.Label(body, text='工號').pack(anchor='w', pady=(0, 6))
        self.employee_entry = ttk.Entry(body, textvariable=self.employee)
        self.employee_entry.pack(fill='x')
        ttk.Label(body, text='密碼').pack(anchor='w', pady=(16, 6))
        self.password_entry = ttk.Entry(body, textvariable=self.password, show='●')
        self.password_entry.pack(fill='x')
        self.visible = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text='顯示密碼', variable=self.visible,
                        command=lambda: self.password_entry.configure(show='' if self.visible.get() else '●')).pack(anchor='w', pady=8)
        self.status = tk.StringVar(value='畫面預覽：不會驗證 AD，也不會開啟工作區。' if preview else 'AD 密碼不會保存於設定、資料庫或日誌。')
        ttk.Label(body, textvariable=self.status, wraplength=440).pack(anchor='w', pady=(6, 12))
        self.progress = ttk.Progressbar(body, mode='indeterminate',style='Workspace.Horizontal.TProgressbar')
        actions = ttk.Frame(body)
        self.actions = actions
        actions.pack(fill='x')
        self.submit_button = ttk.Button(actions, text='登入公司工作區', style='Primary.TButton', command=self.submit)
        self.submit_button.pack(side='left')
        if not preview and provider is None:
            from .company_auth import is_configured
            if not is_configured():
                self.submit_button.configure(state='disabled')
                self.status.set('AD 驗證尚未接線，暫時無法登入；請由公司維護者接上驗證函數。')
        ttk.Button(actions, text='關閉預覽' if preview else '取消', command=self.cancel).pack(side='right')
        ttk.Separator(body).pack(fill='x', pady=24)
        info = publisher_info()
        ttk.Label(body, text='作者與聯絡方式', style='Section.TLabel').pack(anchor='w')
        ttk.Label(body, text=f"姓名：{info['name']}\n工號：{info['employee_id']}\n電話／分機：{info['phone']}", wraplength=440).pack(anchor='w', pady=8)
        ttk.Label(body, text='登入不等於助理或資料庫接線已通過驗收。', style='Muted.TLabel', wraplength=440).pack(anchor='w')
        root.protocol('WM_DELETE_WINDOW', self.cancel)
        root.bind('<Return>', lambda event: self.submit())
        root.bind('<Escape>', lambda event: self.cancel())
        self.appearance.apply(root)
        self.employee_entry.focus_set()
        self.timer = root.after(50, self.poll)

    def submit(self):
        if self.pending or self.closing:
            return
        if self.preview:
            self.password.set('')
            self.status.set('這是畫面預覽，未驗證身分。接好 AD 函數並啟用公司登入後才能進入。')
            return
        if self.provider is None:
            from .company_auth import is_configured
            if not is_configured():
                self.password.set('')
                return
        employee, password = self.employee.get().strip(), self.password.get()
        if not employee or not password:
            self.status.set('請輸入工號與密碼。')
            return
        self.password.set('')
        self.pending = True
        for widget in (self.employee_entry, self.password_entry, self.submit_button):
            widget.configure(state='disabled')
        self.status.set('正在驗證身分與使用資格…')
        self.progress.pack(fill='x', pady=(0, 12), before=self.actions)
        self.progress.start(12)
        def work(employee, password):
            try:
                self.events.put((authenticate(employee, password, provider=self.provider), None))
            except AuthenticationError as exc:
                self.events.put((None, str(exc)))
            except Exception:
                self.events.put((None, '登入未完成，請聯絡維護者。'))
            finally:
                password = None
        threading.Thread(target=work, args=(employee, password), daemon=False).start()

    def poll(self):
        try:
            result, error = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.pending = False
            self.progress.stop()
            self.progress.pack_forget()
            if self.closing:
                if result:
                    result.close()
                self.finish()
                return
            if result:
                self.result = result
                self.finish()
                return
            self.status.set(error)
            for widget in (self.employee_entry, self.password_entry, self.submit_button):
                widget.configure(state='normal')
            self.password_entry.focus_set()
        self.timer = self.root.after(50, self.poll)

    def cancel(self):
        self.password.set('')
        self.closing = True
        if self.pending:
            self.status.set('正在結束登入；等待驗證函數返回，不會進入工作區。')
        else:
            self.finish()

    def finish(self):
        self.password.set('')
        self.progress.stop()
        try:
            self.root.after_cancel(self.timer)
        except tk.TclError:
            pass
        self.root.quit()


def show_login(directory, *, preview=False):
    initialize_dpi()
    set_windows_identity()
    root = tk.Tk()
    view = LoginView(root, directory, preview=preview)
    root.mainloop()
    result = view.result
    root.destroy()
    return result
