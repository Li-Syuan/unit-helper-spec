"""Offline, share-safe readiness checks. Never send credentials or contact services."""
from __future__ import annotations
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import ssl
import struct
import sys
import tempfile
from urllib.parse import urlsplit

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
from desktop_app.config import data_directory, load_config


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def locked_packages(path):
    result = {}
    for line in Path(path).read_text(encoding="ascii").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+", line):
            raise ValueError("invalid lock")
        name, version = line.split("==")
        if canonical(name) in result:
            raise ValueError("duplicate lock")
        result[canonical(name)] = version
    if not result:
        raise ValueError("empty lock")
    return result


def inspect_environment(project=PROJECT, config_path=None, data_path=None, environ=None):
    environ = os.environ if environ is None else environ
    checks = []
    runtime_details = {"tk_patch": None, "packages": {}}
    def check(name, code, operation):
        try:
            passed = operation()
            checks.append({"check": name, "status": "passed" if passed else "failed", "code": "ok" if passed else code})
        except Exception:
            checks.append({"check": name, "status": "failed", "code": code})

    check("python", "python_version_mismatch", lambda: sys.version_info[:3] == (3, 10, 4))
    check("architecture", "requires_x64", lambda: struct.calcsize("P") * 8 == 64)
    check("platform", "requires_windows", lambda: sys.platform == "win32")
    def tk_available():
        import tkinter
        root = tkinter.Tk()
        try:
            root.withdraw()
            patch = str(root.tk.call("info", "patchlevel"))
            runtime_details["tk_patch"] = patch if re.fullmatch(r"[0-9.]+", patch) else None
            return bool(runtime_details["tk_patch"])
        finally:
            root.destroy()
    check("tk", "tk_unavailable", tk_available)
    from desktop_app.web_environment import runtime_available
    check('webview2','webview2_or_dotnet_missing',runtime_available)
    def dependencies():
        installed = {canonical(d.metadata["Name"]): d.version for d in importlib.metadata.distributions()}
        locked = locked_packages(Path(project) / "requirements.lock")
        runtime_details["packages"] = {name: installed[name] for name in locked if name in installed and re.fullmatch(r"[0-9A-Za-z.+!-]+", installed[name])}
        return installed == locked
    check("dependencies", "packages_differ_from_lock", dependencies)
    config = None
    try:
        if config_path is not None and not Path(config_path).is_file():
            raise ValueError()
        config = load_config(config_path)
        assistant = config["assistant"]
        if not isinstance(assistant.get("verified_side_effect_free"), bool):
            raise ValueError()
        if assistant["mode"] == "company":
            url = urlsplit(assistant.get("base_url", ""))
            if (url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment
                    or url.hostname.lower().rstrip(".") in {"openai.com", "api.openai.com"}):
                raise ValueError()
            if not isinstance(assistant.get("model"), str) or not assistant["model"].strip():
                raise ValueError()
        names = [assistant["api_key_env"]]
        headers = assistant.get("header_env", {})
        if not isinstance(headers, dict) or any(not isinstance(k, str) or not re.fullmatch(r"[A-Za-z0-9-]+", k) or k.lower() in {"authorization", "host", "content-length", "content-type"} for k in headers):
            raise ValueError()
        names += list(headers.values())
        if any(not isinstance(n, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n) for n in names):
            raise ValueError()
        if assistant.get("assistant_ref") is not None:
            field = assistant.get("assistant_ref_field")
            ref = assistant["assistant_ref"]
            if (not isinstance(field, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field)
                    or field in {"messages", "model", "stream", "tools", "tool_choice"}
                    or not isinstance(ref, str) or not ref.strip()):
                raise ValueError()
        if assistant.get("ca_bundle") is not None and (not isinstance(assistant["ca_bundle"], str) or not assistant["ca_bundle"].strip()):
            raise ValueError()
        checks.append({"check": "configuration", "status": "passed", "code": "ok"})
    except Exception:
        config = None
        checks.append({"check": "configuration", "status": "failed", "code": "configuration_invalid"})
    # Assistant metadata may exist independently of legacy config; inspect locally only.
    profile_path=(Path(data_path) if data_path is not None else data_directory())/'assistants.json'
    if profile_path.exists():
        try:
            from desktop_app.profiles import Profiles
            profiles=Profiles(profile_path,config['assistant'] if config else {})
            checks.append({"check":"assistant_profiles","status":"passed","code":"ok"})
            if any(p['id']!='demo' and p['enabled'] for p in profiles.items()):
                check("profile_credential","credential_store_unavailable_or_empty",lambda:bool(profiles.key()))
                checks.append({"check":"assistant_mapping","status":"not_tested","code":"requires_company_acceptance"})
        except Exception:
            checks.append({"check":"assistant_profiles","status":"failed","code":"assistant_profiles_invalid"})
    else:
        checks.append({"check":"assistant_profiles","status":"not_applicable","code":"no_assistant_profiles"})
    if config:
        assistant = config["assistant"]
        if profile_path.exists():
            names = list(headers.values())
        if assistant["mode"] == "company" or (profile_path.exists() and headers):
            check("credential_presence", "required_environment_missing_or_invalid", lambda: all(bool(environ.get(n)) for n in names) and all("\r" not in environ.get(n, "") and "\n" not in environ.get(n, "") for n in headers.values()))
        else:
            checks.append({"check": "credential_presence", "status": "not_applicable", "code": "demo_mode"})
        if assistant.get("ca_bundle"):
            check("ca_bundle", "ca_bundle_invalid", lambda: bool(ssl.create_default_context(cafile=assistant["ca_bundle"])))
        else:
            checks.append({"check": "ca_bundle", "status": "not_applicable", "code": "default_trust_store"})
    else:
        for name in ("credential_presence", "ca_bundle"):
            checks.append({"check": name, "status": "not_tested", "code": "configuration_invalid"})
    def directory_available():
        directory = Path(data_path) if data_path is not None else data_directory()
        if directory.exists() and not directory.is_dir():
            return False
        # Probe the actual directory, or a temporary sibling of a new directory.
        if directory.exists():
            with tempfile.TemporaryFile(dir=directory) as handle:
                handle.write(b"readiness"); handle.flush()
            return True
        missing = []
        current = directory
        while not current.exists():
            missing.append(current.name)
            if current.parent == current:
                raise OSError("root unavailable")
            current = current.parent
        with tempfile.TemporaryDirectory(prefix="unithelper-check-", dir=current) as folder:
            probe = Path(folder).joinpath(*reversed(missing))
            probe.mkdir(parents=True)
            with tempfile.TemporaryFile(dir=probe) as handle:
                handle.write(b"readiness"); handle.flush()
        return True
    check("data_directory", "data_directory_unavailable", directory_available)
    for name in ("company_chatbot", "company_identity", "company_queries", "excel"):
        checks.append({"check": name, "status": "not_tested", "code": "requires_company_acceptance"})
    # Only constants/statuses and safe runtime version fields may enter a share report.
    return {"schema_version": 1, "local_environment": "failed" if any(c["status"] == "failed" for c in checks) else "passed",
            "company_acceptance": "not_tested", "python_version": platform.python_version(),
            "architecture_bits": struct.calcsize("P") * 8, **runtime_details, "checks": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline diagnostics; never tests company services.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--human", action="store_true")
    args = parser.parse_args(argv)
    report = inspect_environment(config_path=args.config, data_path=args.data_dir)
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded + "\n", encoding="utf-8")
        except OSError:
            print("report_write_failed", file=sys.stderr)
            return 2
    if args.human:
        labels = {"python":"Python 3.10.4", "architecture":"64 位元架構", "platform":"Windows 平台", "tk":"Tk 視窗元件",'webview2':'WebView2 與 .NET Framework',
                  "dependencies":"套件與鎖檔", "configuration":"設定格式", "credential_presence":"必要環境變數",
                  "assistant_profiles":"助理清單", "profile_credential":"助理金鑰", "assistant_mapping":"公司請求格式",
                  "ca_bundle":"CA 憑證", "data_directory":"資料目錄", "company_chatbot":"公司助理", "company_identity":"AD 與名單",
                  "company_queries":"Oracle 查詢", "excel":"Excel 貼上"}
        statuses = {"passed":"通過", "failed":"需修正", "not_tested":"尚未實測", "not_applicable":"無需檢查"}
        remedies = {"python_version_mismatch":"使用 Python 恰好 3.10.4 重建環境。", "requires_x64":"使用 64 位元 Python。",
                    "requires_windows":"請在 Windows 執行。", "tk_unavailable":"確認完整 Python 安裝包含 Tcl/Tk 且可開啟視窗。",
                    "packages_differ_from_lock":"依 requirements.lock 重建乾淨環境。",
                    "configuration_invalid":"檢查設定檔存在、欄位格式及公司端點；參照 config.example.json。",
                    "required_environment_missing_or_invalid":"設定公司要求的金鑰與標頭環境變數；標頭不可含換行。",
                    "ca_bundle_invalid":"確認公司 CA 憑證檔存在且為有效 PEM。", "data_directory_unavailable":"確認資料目錄路徑有效且可寫入。"}
        print("本機環境：" + statuses[report["local_environment"]])
        for item in report["checks"]:
            print(labels[item["check"]] + "：" + statuses[item["status"]] + " (" + item["code"] + ")")
            if item["status"] == "failed":
                print("  " + remedies.get(item["code"], "請聯絡維護者。"))
        print("公司 API／AD／Oracle／Excel 必須另行實測；本機通過不代表公司接線成功。")
        print("分享報告不含路徑、內部網址、環境變數名稱或值，以及私人內容。")
    else:
        print(encoded)
    return 0 if report["local_environment"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
