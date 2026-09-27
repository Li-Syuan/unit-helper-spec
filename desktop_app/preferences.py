"""Atomic UI preferences; never contains company connection settings."""
import json
import os
import tempfile
from pathlib import Path

HINT_PAGES = ('activity', 'todo', 'chat', 'query', 'work', 'result', 'schedule', 'notice', 'settings', 'issue')


def load_preferences(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def update_preferences(path, changes):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = load_preferences(path)
    data.update(changes)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.appearance-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def load_theme(path):
    value = load_preferences(path).get('theme')
    return value if value in ('dark', 'light') else 'dark'


def save_theme(path, name):
    if name not in ('dark', 'light'):
        raise ValueError('不支援的外觀主題。')
    update_preferences(path, {'theme': name})


def load_page_hints(path):
    data = load_preferences(path).get('page_hints', {})
    if not isinstance(data, dict):
        data = {}
    return {page: data[page] if type(data.get(page)) is bool else True for page in HINT_PAGES}


def save_page_hint(path, page, visible):
    if page not in HINT_PAGES or type(visible) is not bool:
        raise ValueError('不支援的操作提示偏好。')
    data = load_preferences(path).get('page_hints', {})
    data = dict(data) if isinstance(data, dict) else {}
    data[page] = visible
    update_preferences(path, {'page_hints': data})
