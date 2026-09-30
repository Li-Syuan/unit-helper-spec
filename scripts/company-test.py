"""One local acceptance entry; never reads credentials or contacts company services."""
import argparse
import ast
import json
import os
import tempfile
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', nargs='?', choices=('local','quick','ui','company-info'), default='local')
    args = parser.parse_args(argv)
    if args.mode == 'company-info':
        print('Company API / search / AD / Oracle: NOT TESTED.')
        print('See docs/ONE-CLICK-TEST.md. Live tests require approved settings, tools and explicit --live.')
        return 2
    report = {'status':'failed', 'company_real':'not_tested', 'steps':[]}
    destination = ROOT/'artifacts/company-test/latest.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    def save():
        destination.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    save()
    if sys.version_info[:3] != (3,10,4) or sys.flags.optimize:
        print('Requires project Python exactly 3.10.4, without -O.', file=sys.stderr)
        return 1
    try:
        for folder in ('desktop_app','scripts','tests','test_support'):
            for path in (ROOT/folder).rglob('*.py'):
                ast.parse(path.read_text('utf-8-sig'), filename=path.relative_to(ROOT).as_posix())
        report['steps'].append({'name':'python_syntax', 'status':'passed'})
    except (SyntaxError,UnicodeError):
        report['steps'].append({'name':'python_syntax', 'status':'failed'})
        save();print('Python syntax check failed. Inspect the changed source.', file=sys.stderr);return 1
    commands = []
    if args.mode != 'ui':
        commands.append(('regression', ['scripts/test_runner.py','--suite','quick']) if args.mode == 'quick'
                        else ('full_regression', ['scripts/verify.py','development']))
    if args.mode in ('local','ui'):
        commands.append(('webview_synthetic', ['scripts/web-smoke.py']))
        commands.append(('demo_login_lifecycle', ['scripts/login-smoke.py']))
    for name, arguments in commands:
        print('Running '+name+'; company services NOT tested.', flush=True)
        with tempfile.TemporaryDirectory(prefix='qa-local-acceptance-') as directory:
            result = subprocess.run([sys.executable,*arguments], cwd=ROOT,
                                    env={**os.environ, 'UNITHELPER_DATA_DIR':directory, 'PYTHONIOENCODING':'utf-8'})
        report['steps'].append({'name':name, 'exit_code':result.returncode,
                                'status':'passed' if result.returncode == 0 else 'failed'})
        save()
        if result.returncode:
            print('FAILED: '+name+'. See artifacts/testing/latest.json or artifacts/web-smoke/result.json.', file=sys.stderr)
            return 1
    report['status']='passed';save()
    print('LOCAL PASSED. Company API/search/AD/Oracle remain NOT TESTED.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
