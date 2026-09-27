"""Chat keyboard policy with a Windows IME composition guard.

The native hook records state only. All Tk interaction stays on the Tk thread.
Real Chinese IME acceptance remains an explicit manual verification step.
"""
import ctypes
import sys
import time


class WindowsIMEGuard:
    def __init__(self, widget, clock=time.monotonic):
        self.widget, self.clock = widget, clock
        self.composing = False
        self.last_end = float('-inf')
        self._hook = None
        self._previous = None
        self.hwnd = None
        if sys.platform != 'win32':
            return
        from ctypes import wintypes
        widget.update_idletasks()
        self.hwnd = widget.winfo_id()
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.imm = ctypes.WinDLL('imm32', use_last_error=True)
        self.imm.ImmGetContext.argtypes = [wintypes.HWND]
        self.imm.ImmGetContext.restype = wintypes.HANDLE
        self.imm.ImmReleaseContext.argtypes = [wintypes.HWND, wintypes.HANDLE]
        self.imm.ImmGetCompositionStringW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        self.imm.ImmGetCompositionStringW.restype = ctypes.c_long
        proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        self.user.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user.CallWindowProcW.restype = ctypes.c_ssize_t
        self.user.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        self.user.SetWindowLongPtrW.restype = ctypes.c_void_p

        def dispatch(hwnd, message, wparam, lparam):
            if message == 0x010D:  # WM_IME_STARTCOMPOSITION
                self.composing = True
            elif message == 0x010E:  # WM_IME_ENDCOMPOSITION
                self.composing = False
                self.last_end = self.clock()
            return self.user.CallWindowProcW(self._previous, hwnd, message, wparam, lparam)

        self._hook = proc_type(dispatch)
        self._previous = self.user.SetWindowLongPtrW(self.hwnd, -4, ctypes.cast(self._hook, ctypes.c_void_p))
        if not self._previous:
            self._hook = None
            raise OSError('輸入法鍵盤保護無法啟用。')

    def blocked(self):
        if self.composing or self.clock() - self.last_end < 0.25:
            return True
        if self.hwnd is None:
            return False
        context = self.imm.ImmGetContext(self.hwnd)
        if not context:
            return False
        try:
            return self.imm.ImmGetCompositionStringW(context, 0x0008, None, 0) > 0
        finally:
            self.imm.ImmReleaseContext(self.hwnd, context)

    def close(self):
        if self._hook is not None:
            self.user.SetWindowLongPtrW(self.hwnd, -4, self._previous)
            self._hook = None


class ChatKeyboard:
    def __init__(self, widget, send, guard=None, clock=time.monotonic):
        self.widget, self.send, self.clock = widget, send, clock
        self.guard = guard if guard is not None else WindowsIMEGuard(widget, clock)
        self.held = False
        self.last_send = float('-inf')
        self.release_id = None
        self.bindings = []
        for sequence, callback in [('<Return>', self.press), ('<Control-Return>', self.press),
                                   ('<Shift-Return>', self.newline), ('<KeyRelease-Return>', self.release),
                                   ('<FocusOut>', self.blur)]:
            self.bindings.append((sequence, widget.bind(sequence, callback)))

    def press(self, event=None):
        if self.release_id is not None:
            self.widget.after_cancel(self.release_id)
            self.release_id = None
        repeated = self.held
        self.held = True
        if repeated or self.guard.blocked():
            return 'break'
        if self.clock() - self.last_send < 0.35 or not self.widget.get('1.0', 'end-1c').strip():
            return 'break'
        self.last_send = self.clock()
        self.send()
        return 'break'

    def newline(self, event=None):
        if not self.guard.blocked():
            self.widget.insert('insert', '\n')
            self.widget.see('insert')
        return 'break'

    def release(self, event=None):
        if self.release_id is not None:
            self.widget.after_cancel(self.release_id)
        self.release_id = self.widget.after_idle(self.reset)

    def reset(self):
        self.held = False
        self.release_id = None

    def blur(self, event=None):
        self.held = False

    def close(self):
        if self.release_id is not None:
            self.widget.after_cancel(self.release_id)
            self.release_id = None
        for sequence, binding in self.bindings:
            self.widget.unbind(sequence, binding)
        self.bindings.clear()
        self.guard.close()


def install_chat_keyboard(widget, send):
    return ChatKeyboard(widget, send)
