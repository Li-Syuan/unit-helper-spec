"""Build a NEW official App environment from verified local wheels; no PowerShell needed."""
import argparse
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from offline_bundle import BundleError, verify_bundle


class InstallError(ValueError):
    pass


def install(project, bundle, environment='.venv', data_dir=None, progress=None):
    """Only the newly requested venv is written; never repair or delete existing environments."""
    project, bundle = Path(project).resolve(), Path(bundle).resolve()
    report = progress if progress is not None else {}
    report.update(status='failed', environment_created=False, checks=[],
                  full_regression='not_tested', company_real='not_tested')
    if sys.platform != 'win32' or sys.version_info[:3] != (3, 10, 4) or struct.calcsize('P') != 8:
        raise InstallError('requires_windows_x64_python3104')
    if not re.fullmatch(r'\.venv(?:-[a-zA-Z0-9]+)?', environment):
        raise InstallError('invalid_environment_name')
    target = project / environment
    if os.path.lexists(target):
        raise InstallError('environment_exists_not_overwritten')
    if target.resolve().parent != project:
        raise InstallError('environment_outside_project')
    # Verify the App lock, all wheels and hashes BEFORE creating any environment.
    manifest = verify_bundle(bundle, project/'requirements.lock')
    report.update(wheels=len(manifest['files']), lock_sha256=manifest['lock_sha256'])
    report['checks'].append({'name':'bundle_integrity', 'status':'passed'})
    # --no-index does not disable a global pip.ini find-links setting.
    # NUL disables config files for these child processes, without editing company policy.
    env = {**os.environ, 'PYTHONIOENCODING':'utf-8', 'PIP_CONFIG_FILE':os.devnull}
    if data_dir is not None:
        env['UNITHELPER_DATA_DIR'] = str(Path(data_dir).resolve())

    def run(name, command):
        print('Checking: ' + name, flush=True)
        result = subprocess.run(command, cwd=project, env=env)
        report['checks'].append({'name':name, 'exit_code':result.returncode,
                                 'status':'passed' if result.returncode == 0 else 'failed'})
        if result.returncode:
            raise InstallError(name + '_failed')

    run('base_python', [sys.executable, str(project/'scripts/check-python.py')])
    # mkdir is exclusive: a second installer cannot silently share this target.
    target.mkdir()
    report['environment_created'] = True
    run('create_environment', [sys.executable, '-m', 'venv', str(target)])
    python = str(target/'Scripts/python.exe')
    run('offline_install', [python, '-m', 'pip', '--isolated', 'install', '--disable-pip-version-check',
                           '--no-index', '--no-deps', '--no-cache-dir', '--only-binary=:all:',
                           '--find-links', str(bundle), '--requirement', str(project/'requirements.lock')])
    run('pip_check', [python, '-m', 'pip', 'check'])
    run('environment_diagnostic', [python, str(project/'scripts/doctor.py'), '--human'])
    # Doctor checks all pinned distributions; full runner also enforces exact freeze spelling.
    result = subprocess.run([python, '-m', 'pip', 'freeze', '--all'], cwd=project, env=env,
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    matches = result.returncode == 0 and sorted(result.stdout.splitlines()) == sorted(
        (project/'requirements.lock').read_text('ascii').splitlines())
    report['checks'].append({'name':'lock_match', 'status':'passed' if matches else 'failed'})
    if not matches:
        raise InstallError('packages_differ_from_lock')
    report['status'] = 'passed'
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline-bundle', type=Path, default=ROOT/'wheelhouse')
    parser.add_argument('--environment', default='.venv')
    parser.add_argument('--data-dir', type=Path, help='Optional isolated diagnostic data location')
    args = parser.parse_args(argv)
    report = {}
    try:
        install(ROOT, args.offline_bundle, args.environment, args.data_dir, progress=report)
    except (InstallError, BundleError) as error:
        report['code'] = str(error)
    except (OSError, ValueError):
        report['code'] = 'local_installation_failed'
    except KeyboardInterrupt:
        report['code'] = 'installation_interrupted'
    output = ROOT/'artifacts/installation/latest.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(report, indent=2)+'\n').encode('utf-8'))
    print(json.dumps(report), flush=True)
    if report.get('status') != 'passed':
        print('Install stopped. Existing .venv is never overwritten. Use a NEW extracted project folder. '
              'A newly created partial environment is retained for inspection; no online fallback.', file=sys.stderr)
        return 1
    print('Offline environment ready. This is NOT full regression or company acceptance. '
          f'Next: {args.environment}\\Scripts\\python.exe scripts\\test_runner.py --suite full')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
