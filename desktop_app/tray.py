"""A local notification-area host; no remote calls and no extra dependency."""
from pathlib import Path
import threading


class TrayController:
    def __init__(self, backend):
        self.backend = backend
        self.ready = False
        self._registration = threading.Lock()

    def background(self):
        try:
            with self._registration:
                if not self.ready:
                    self.backend.create()
                    self.ready = True
                self.backend.hide()
            return True
        except Exception:
            # If registering the icon fails, leave a reachable desktop window.
            try:
                self.backend.show()
            except Exception:
                pass
            return False

    def show(self):
        self.backend.show()

    def close(self):
        self.ready = False
        self.backend.dispose()


class WinFormsTray:
    def __init__(self, window, status, exit_callback):
        self.window = window
        self.status = status
        self.exit_callback = exit_callback
        self.notify = self.menu = self.timer = self.icon = None

    def _ui(self, callback):
        from System import Action
        if self.window.native.InvokeRequired:
            self.window.native.Invoke(Action(callback))
        else:
            callback()

    def create(self):
        def make():
            from System.Drawing import Icon
            from System.Windows.Forms import NotifyIcon, ContextMenuStrip, ToolStripMenuItem, Timer
            try:
                self.icon = Icon(str(Path(__file__).parent/'assets'/'qa-agent.ico'))
                self.menu = ContextMenuStrip()
                show = ToolStripMenuItem('開啟 QA agent')
                show.Click += lambda *_: self._show_native()
                state = ToolStripMenuItem('讀取本機排程狀態…')
                state.Enabled = False
                end = ToolStripMenuItem('退出（停止本機自動工作）')
                end.Click += lambda *_: self.exit_callback()
                for item in (show, state, end):
                    self.menu.Items.Add(item)
                self.notify = NotifyIcon()
                self.notify.Icon = self.icon
                self.notify.Text = 'QA agent · 本機自動工作'
                self.notify.ContextMenuStrip = self.menu
                self.notify.DoubleClick += lambda *_: self._show_native()
                def refresh(*_):
                    try:
                        state.Text = self.status()
                    except Exception:
                        state.Text = '狀態暫時無法讀取，請開啟視窗檢查'
                self.timer = Timer()
                self.timer.Interval = 15000
                self.timer.Tick += refresh
                refresh()
                self.notify.Visible = True
                if not self.notify.Visible:
                    raise RuntimeError('tray_unavailable')
                self.timer.Start()
            except Exception:
                self._dispose_native()
                raise
        self._ui(make)

    def _show_native(self):
        from System.Windows.Forms import FormWindowState
        form = self.window.native
        form.Show()
        if form.WindowState == FormWindowState.Minimized:
            form.WindowState = FormWindowState.Normal
        form.Activate()
        form.BringToFront()

    def show(self):
        self._ui(self._show_native)

    def hide(self):
        self._ui(lambda: self.window.native.Hide())

    def _dispose_native(self):
        if self.timer:
            self.timer.Stop()
            self.timer.Dispose()
        if self.notify:
            self.notify.Visible = False
            self.notify.Dispose()
        if self.menu:
            self.menu.Dispose()
        if self.icon:
            self.icon.Dispose()
        self.notify = self.menu = self.timer = self.icon = None

    def dispose(self):
        if self.notify is not None:
            self._ui(self._dispose_native)
