"""Local publisher display data; never credentials or a remote lookup."""
import json
from pathlib import Path
import unicodedata

from . import __version__
from .branding import APP_NAME

ROOT = Path(__file__).resolve().parents[1]
UNSET = '尚未設定'
MAX_BYTES = 16 * 1024
FIELD_LIMITS = {'employee_id': 40, 'name': 80, 'phone': 40}


def _plain_field(value, limit):
    if not isinstance(value, str):
        return UNSET
    value = value.strip()
    if not value or len(value) > limit:
        return UNSET
    if any(char in '<>' or unicodedata.category(char) in {'Cc', 'Cf', 'Cs', 'Zl', 'Zp'}
           for char in value):
        return UNSET
    return value


def publisher_info(path=None):
    """Return only employee_id/name/phone, with safe missing-value labels.

    The optional path is for trusted local callers and tests. UI bridges should
    use the fixed default, not accept a publisher path from the browser.
    """
    empty = {field: UNSET for field in FIELD_LIMITS}
    try:
        source = ROOT / 'publisher.json' if path is None else Path(path)
        with source.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return empty
        document = json.loads(raw.decode('utf-8-sig'))
        author = document.get('author') if isinstance(document, dict) else None
        if not isinstance(author, dict):
            return empty
        return {field: _plain_field(author.get(field), limit)
                for field, limit in FIELD_LIMITS.items()}
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        return empty


def about_text(path=None):
    author = publisher_info(path)
    return (
        f'{APP_NAME} {__version__}\n\nWindows 本機桌面應用。\n\n'
        f'作者資訊\n工號：{author["employee_id"]}\n姓名：{author["name"]}\n電話：{author["phone"]}\n\n'
        '請使用問題回報保存紀錄，再依單位指定管道提供。\n'
        '回報目前只存本機，不會自動送給維護者。\n'
        '環境診斷不呼叫模型或資料庫；通過不代表服務接線完成。\n\n'
        '第三方授權：請選「第三方套件授權」，完整文字存於程式 docs/licenses。'
    )
