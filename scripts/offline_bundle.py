"""Prepare and verify an integrity-checked Windows CPython 3.10 wheelhouse."""
from __future__ import annotations
import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from doctor import canonical, locked_packages


class BundleError(ValueError):
    pass


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def wheel_identity(path):
    try:
        with zipfile.ZipFile(path) as archive:
            metadata = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA") and n.count("/") == 1]
            if len(metadata) != 1 or archive.getinfo(metadata[0]).file_size > 2 * 1024 * 1024:
                raise BundleError("wheel_metadata_invalid")
            item = BytesParser().parsebytes(archive.read(metadata[0]))
            if not item["Name"] or not item["Version"]:
                raise BundleError("wheel_metadata_invalid")
            return canonical(item["Name"]), item["Version"]
    except (OSError, zipfile.BadZipFile, KeyError):
        raise BundleError("wheel_metadata_invalid") from None


def valid_name(name):
    return isinstance(name, str) and bool(re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.+!-]*\.whl", name))


def manifest_for(folder, lock):
    folder, lock = Path(folder), Path(lock)
    expected = locked_packages(lock)
    files = {}
    packages = {}
    for path in sorted(folder.iterdir()):
        if path.name == "manifest.json":
            continue
        if not valid_name(path.name) or path.is_symlink() or not path.is_file():
            raise BundleError("unexpected_bundle_file")
        name, version = wheel_identity(path)
        if name in packages or expected.get(name) != version:
            raise BundleError("wheel_package_mismatch")
        packages[name] = version
        files[path.name] = {"sha256": digest(path), "package": name, "version": version}
    if packages != expected:
        raise BundleError("wheel_packages_missing")
    return {"schema_version": 1, "target": "cp310-win_amd64", "python": "3.10.4",
            "lock_sha256": digest(lock), "files": files}


def verify_bundle(folder, lock):
    folder, lock = Path(folder), Path(lock)
    try:
        if folder.is_symlink() or not folder.is_dir() or (folder / "manifest.json").is_symlink():
            raise BundleError("bundle_location_invalid")
        raw = (folder / "manifest.json").read_text(encoding="utf-8")
        if len(raw) > 1024 * 1024:
            raise BundleError("bundle_manifest_invalid")
        manifest = json.loads(raw)
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or manifest.get("target") != "cp310-win_amd64" or manifest.get("python") != "3.10.4":
            raise BundleError("bundle_target_invalid")
        if manifest.get("lock_sha256") != digest(lock):
            raise BundleError("lock_fingerprint_mismatch")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files or any(not valid_name(name) for name in files):
            raise BundleError("bundle_manifest_invalid")
        actual = manifest_for(folder, lock)
        if manifest != actual:
            raise BundleError("bundle_integrity_failed")
        return actual
    except BundleError:
        raise
    except Exception:
        raise BundleError("bundle_validation_failed") from None


def build_bundle(folder, lock):
    if sys.platform != "win32" or sys.version_info[:3] != (3, 10, 4) or struct.calcsize("P") != 8:
        raise BundleError("requires_windows_x64_python3104")
    folder, lock = Path(folder).resolve(), Path(lock).resolve()
    locked_packages(lock)
    if folder.exists():
        raise BundleError("bundle_destination_exists")
    folder.mkdir(parents=True)
    # pywebview's tiny pure-Python proxy_tools dependency only publishes an sdist.
    # Build that one pinned dependency on this verified Windows/Python host; all
    # other packages must still have compatible binary wheels. Install remains
    # offline-only and verifies the resulting wheel's manifest hash.
    packages=locked_packages(lock)
    if 'proxy-tools' in packages:
        command=[sys.executable,'-m','pip','wheel','--no-deps','--wheel-dir',str(folder),
                 'proxy_tools=='+packages['proxy-tools']]
        if subprocess.run(command).returncode:raise BundleError('proxy_wheel_build_failed')
    command = [sys.executable, "-m", "pip", "download", "--disable-pip-version-check", "--only-binary=:all:",
               "--no-deps", "--platform", "win_amd64", "--python-version", "3.10.4", "--implementation", "cp",
               "--abi", "cp310", "--find-links",str(folder),"--dest", str(folder), "--requirement", str(lock)]
    if subprocess.run(command).returncode:
        raise BundleError("wheel_download_failed")
    manifest = manifest_for(folder, lock)
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return verify_bundle(folder, lock)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("build", "verify"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=PROJECT / "requirements.lock")
    args = parser.parse_args(argv)
    try:
        manifest = (build_bundle if args.operation == "build" else verify_bundle)(args.directory, args.lock)
    except (BundleError, OSError, ValueError) as error:
        # Only BundleError uses a fixed safe code. Never print external path/error contents.
        print(str(error) if isinstance(error, BundleError) else "bundle_operation_failed", file=sys.stderr)
        return 1
    print(json.dumps({"status": "passed", "operation": args.operation, "wheel_count": len(manifest["files"]),
                      "lock_sha256": manifest["lock_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
