"""Atomic UI preferences; never contains company connection settings."""
import json
import os
import tempfile
from pathlib import Path

ONBOARDING_VERSION = 1


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


def load_onboarding(path):
    data = load_preferences(path).get('onboarding', {})
    if not isinstance(data, dict) or data.get('version') != ONBOARDING_VERSION:
        return 'new'
    status = data.get('status')
    return status if status in ('invited', 'skipped', 'completed') else 'new'


def save_onboarding(path, status):
    if status not in ('invited', 'skipped', 'completed'):
        raise ValueError('不支援的導覽狀態。')
    update_preferences(path, {'onboarding': {'version': ONBOARDING_VERSION, 'status': status}})
