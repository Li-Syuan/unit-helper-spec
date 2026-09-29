"""Create a NEW lab-only venv and install verified wheels without network access."""
import os
from pathlib import Path
import struct
import subprocess
import sys
import venv
from bundle import ROOT, verify


def main():
    if sys.platform != 'win32' or sys.version_info[:3] != (3, 10, 4) or struct.calcsize('P') != 8:
        raise SystemExit('Requires Windows x64 and exactly Python 3.10.4.')
    rows = verify()  # Validate before creating or installing anything.
    target = ROOT / '.venv'
    if target.exists() or target.is_symlink():
        raise SystemExit('Lab .venv already exists; it will NOT be overwritten. Run test-lab.bat instead.')
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(target)
    python = target / 'Scripts' / 'python.exe'
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('PIP_')}
    env.update(PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX='1', PYTHONUTF8='1')

    def run(*args):
        subprocess.run([str(python), '-I', '-X', 'utf8', *args], cwd=ROOT, env=env, check=True)

    pip_wheel = next(r['file'] for r in rows if r['name'] == 'pip')
    run('-m', 'pip', 'install', '--no-index', '--no-deps', '--no-cache-dir', '--disable-pip-version-check',
        str(ROOT / 'packages' / pip_wheel))
    run('-m', 'pip', 'install', '--no-index', '--no-cache-dir', '--disable-pip-version-check', '--require-hashes',
        '--find-links', str(ROOT / 'packages'), '-r', str(ROOT / 'requirements.lock'))
    run('-m', 'pip', 'check')
    # verify_lab.py explicitly adds its own directory under isolated Python.
    run(str(ROOT / 'verify_lab.py'))
    print('Offline lab ready. Run demo.bat. QA agent environment was not modified.')


if __name__ == '__main__':
    main()
