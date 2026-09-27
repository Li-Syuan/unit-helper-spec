"""Local appearance preferences are independent of assistant connection settings."""
import json
import os
import tempfile
from pathlib import Path


def load_theme(path):
    try:
        data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
        value=data.get('theme') if isinstance(data,dict) else None
        return value if value in ('dark','light') else 'dark'
    except (OSError,ValueError,TypeError):
        return 'dark'


def save_theme(path, name):
    if name not in ('dark','light'): raise ValueError('不支援的外觀主題。')
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix='.appearance-',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump({'theme':name},stream,ensure_ascii=False)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None and temporary.exists(): temporary.unlink()
