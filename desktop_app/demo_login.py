"""Explicit offline fixture only; never a company credential or access grant."""
import hmac
import threading
from pathlib import Path
from .authentication import AuthenticationError


class DemoLoginSession:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self._closed = threading.Event()

    def current(self):
        if self._closed.is_set():
            raise AuthenticationError('展示登入已登出；請重新啟動離線展示。')
        return dict(mode='demo_login', name='離線展示使用者', employee_id='DEMO', subject='offline-fixture')

    def close(self):
        self._closed.set()


def authenticate_demo(employee_id, password, directory):
    # This pair has no meaning outside the explicitly isolated fixture launcher.
    if not (hmac.compare_digest(employee_id.encode('utf-8'), b'admin') and hmac.compare_digest(password.encode('utf-8'), b'admin')):
        raise AuthenticationError('展示帳號或密碼錯誤；僅此離線模式使用 admin / admin。')
    return DemoLoginSession(directory)
