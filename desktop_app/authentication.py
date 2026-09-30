"""Validated, process-only login grant and isolated per-subject workspace."""
import hashlib
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
import unicodedata

from .gateways import GatewayError


class AuthenticationError(GatewayError):
    pass


def _text(value, maximum):
    if (not isinstance(value, str) or not value.strip() or len(value) > maximum
            or any(unicodedata.category(c).startswith('C') for c in value)):
        raise AuthenticationError('驗證服務回傳格式不符，請聯絡維護者。')
    return value.strip()


class LoginSession:
    """Contains identity only. Not an AD ticket or a substitute for server ACLs."""
    def __init__(self, response, *, now=None, clock=time.monotonic):
        now = now or datetime.now(timezone.utc)
        if not isinstance(response, dict):
            raise AuthenticationError('驗證服務回傳格式不符，請聯絡維護者。')
        if response.get('authenticated') is not True or response.get('allowed') is not True:
            raise AuthenticationError('無法登入：請確認工號、密碼及使用權限。')
        try:
            expires = datetime.fromisoformat(response['expires_at'].replace('Z', '+00:00'))
            if expires.tzinfo is None or not 0 < (expires-now).total_seconds() <= 8*3600:
                raise ValueError()
        except (KeyError, TypeError, AttributeError, ValueError):
            raise AuthenticationError('驗證服務未提供有效登入期限，請聯絡維護者。') from None
        self._identity = dict(subject=_text(response.get('subject'), 200),
            employee_id=_text(response.get('employee_id'), 40),
            name=_text(response.get('name'), 80), mode='company', expires_at=expires.isoformat())
        self._expires = expires
        self._clock = clock
        self._deadline = clock()+(expires-now).total_seconds()
        self._closed = False
        self._lock = threading.Lock()

    def current(self):
        with self._lock:
            if self._closed or self._clock() >= self._deadline or datetime.now(timezone.utc) >= self._expires:
                raise AuthenticationError('登入已到期，請關閉並重新登入；未再派發工作。')
            return dict(self._identity)

    def close(self):
        with self._lock:
            self._closed = True

    def directory(self, base):
        identity = self.current()
        key = hashlib.sha256(identity['subject'].encode('utf-8')).hexdigest()
        base = Path(base).resolve()
        target = base/'users'/key
        # Refuse junction/symlink redirection of another user's local workspace.
        for path in (base/'users', target):
            if path.is_symlink() or (path.exists() and path.resolve() != path):
                raise AuthenticationError('登入資料目錄無效，請聯絡維護者。')
        return target


def authenticate(employee_id, password, *, provider=None):
    from . import company_auth
    employee_id = _text(employee_id, 40)
    if not isinstance(password, str) or not password or len(password) > 1024:
        raise AuthenticationError('請輸入工號與密碼。')
    if provider is None:
        if not company_auth.is_configured():
            raise AuthenticationError('AD 驗證尚未接線，不能登入公司工作區。')
        provider = company_auth.authenticate
    try:
        response = provider(employee_id, password)
    except Exception:
        # Never stringify an AD exception: it may contain credentials or a DN.
        raise AuthenticationError('驗證服務未完成，請稍後重試或聯絡維護者。') from None
    finally:
        password = None
    return LoginSession(response)


class AuthorizedQueries:
    def __init__(self, queries, session):
        self.queries, self.session = queries, session

    def catalog(self):
        return self.queries.catalog()

    def validate(self, query_id, parameters):
        self.session.current()
        return self.queries.validate(query_id, parameters)

    def run(self, query_id, parameters):
        self.session.current()
        return self.queries.run(query_id, parameters)
