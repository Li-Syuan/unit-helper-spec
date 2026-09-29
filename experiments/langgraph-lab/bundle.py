"""Standard-library verification for the optional Windows/Python wheel bundle."""
import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root=ROOT):
    packages = root / 'packages'
    if packages.is_symlink() or not packages.is_dir():
        raise ValueError('Invalid packages directory')
    rows = []
    seen = set()
    for path in sorted(packages.iterdir()):
        if path.is_symlink() or not path.is_file() or not re.fullmatch(r'[A-Za-z0-9_.+!-]+\.whl', path.name):
            raise ValueError('Unexpected package file')
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            metadata = [n for n in names if n.endswith('.dist-info/METADATA') and n.count('/') == 1]
            if len(metadata) != 1:
                raise ValueError('Invalid wheel metadata')
            info = BytesParser().parsebytes(archive.read(metadata[0]))
            name = re.sub(r'[-_.]+', '-', info['Name']).lower()
            version = info['Version']
            if name in seen or not re.fullmatch(r'[a-z0-9-]+', name) or not re.fullmatch(r'[A-Za-z0-9.!+]+', version):
                raise ValueError('Duplicate or invalid package')
            seen.add(name)
            rows.append({'file': path.name, 'name': name, 'version': version,
                         'sha256': sha(path), 'bytes': path.stat().st_size,
                         'license': info.get('License-Expression') or info.get('License') or 'See wheel metadata',
                         'license_files': [n for n in names if any(x in n.upper() for x in ('LICENSE', 'COPYING', 'NOTICE'))]})
    if not rows:
        raise ValueError('No wheels found')
    return sorted(rows, key=lambda row: row['name'])


def lock_text(rows):
    return ''.join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}\n" for r in rows)


def verify(root=ROOT):
    rows = inventory(root)
    expected = json.loads((root / 'bundle-manifest.json').read_text('utf-8'))
    if expected != {'target': 'Windows x64 / CPython 3.10.4', 'packages': rows,
                    'lock_sha256': sha(root / 'requirements.lock')}:
        raise ValueError('Bundle integrity or lock fingerprint mismatch')
    if (root / 'requirements.lock').read_text('utf-8') != lock_text(rows):
        raise ValueError('Lock/package mismatch')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Maintainer only: seal reviewed wheels')
    args = parser.parse_args()
    if args.write:
        rows = inventory()
        (ROOT / 'requirements.lock').write_text(lock_text(rows), encoding='utf-8', newline='\n')
        record = {'target': 'Windows x64 / CPython 3.10.4', 'packages': rows,
                  'lock_sha256': sha(ROOT / 'requirements.lock')}
        (ROOT / 'bundle-manifest.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
    rows = verify()
    print(f"Verified {len(rows)} wheels, {sum(r['bytes'] for r in rows):,} bytes")
