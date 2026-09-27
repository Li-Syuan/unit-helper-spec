"""Local config and single-instance ownership; secrets are never saved here."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path

DEFAULT = {
    "identity_mode": "demo", "query_mode": "demo",
    "assistant": {"mode": "demo", "base_url": "", "model": "",
                  "api_key_env": "UNITHELPER_API_KEY", "timeout_seconds": 30,
                  "max_context_chars": 50000, "verified_side_effect_free": False},
}

def data_directory():
    return Path(os.environ.get("UNITHELPER_DATA_DIR", str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "UnitHelperLocal"))).resolve()

def validate_config(source):
    config = copy.deepcopy(DEFAULT)
    if not isinstance(source, dict) or set(source) - set(DEFAULT):
        raise ValueError("設定格式不正確，請參考 config.example.json。")
    for key, value in source.items():
        if key == "assistant":
            permitted = set(DEFAULT["assistant"]) | {"header_env", "assistant_ref", "assistant_ref_field", "ca_bundle"}
            if not isinstance(value, dict) or set(value) - permitted:
                raise ValueError("assistant 設定不正確；金鑰請放環境變數。")
            config[key].update(value)
        else:
            config[key] = value
    if config["identity_mode"] not in ("demo", "company") or config["query_mode"] not in ("demo", "oracle"):
        raise ValueError("身分或查詢模式不正確。")
    a = config["assistant"]
    if a["mode"] not in ("demo", "company"):
        raise ValueError("助理模式不正確。")
    if isinstance(a["timeout_seconds"], bool) or not isinstance(a["timeout_seconds"], (float,int)) or not 1 <= a["timeout_seconds"] <= 120:
        raise ValueError("Timeout 須為 1 至 120 秒。")
    if type(a["max_context_chars"]) is not int or not 1 <= a["max_context_chars"] <= 50000:
        raise ValueError("文字上限須為 1 至 50,000。")
    return config


def load_config(path=None):
    location = Path(path) if path else data_directory() / "config.json"
    return validate_config(json.loads(location.read_text(encoding="utf-8-sig")) if location.exists() else {})


def save_config(config, path=None):
    config = validate_config(config)
    location = Path(path) if path else data_directory() / "config.json"
    location.parent.mkdir(parents=True, exist_ok=True)
    temp = location.with_suffix(".tmp")
    temp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    # Validate before replacing the previous usable configuration.
    load_config(temp)
    os.replace(temp, location)

class InstanceLock:
    def __init__(self, directory):
        import msvcrt
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.handle = (directory / "desktop.lock").open("a+b")
        self.handle.seek(0, 2)
        if self.handle.tell() == 0:
            self.handle.write(b"0"); self.handle.flush()
        self.handle.seek(0)
        try:
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            self.handle.close()
            raise ValueError("同一資料目錄已有小幫手執行中，請使用原視窗。") from None
    def close(self):
        if not self.handle.closed:
            import msvcrt
            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            self.handle.close()
