"""Explicit, trusted local company-test hooks. Never contacts services by default."""
import argparse
from contextlib import contextmanager, redirect_stdout, redirect_stderr
import os
import importlib.util
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

CASES = (
    'chatbot.reply', 'chatbot.isolation',
    'identity.allowed', 'identity.denied', 'identity.disabled', 'identity.expired',
    'query.q01', 'query.q02', 'query.q03',
)


@contextmanager
def quiet_hook():
    # Avoid accidental credentials/body logging by trusted Python hooks.
    with open(os.devnull, 'w') as sink, redirect_stdout(sink), redirect_stderr(sink):
        yield


def check(hooks_path=None, execute=False, capabilities_reviewed=False):
    report = {'schema_version': 1, 'status': 'not_tested',
              'code': 'EXPLICIT_EXECUTION_REQUIRED',
              'cases': {name: 'not_tested' for name in CASES}}
    if not execute:
        return report
    if sys.flags.optimize:
        report.update(status='failed', code='OPTIMIZED_PYTHON_UNSUPPORTED')
        return report
    if not capabilities_reviewed:
        report['code'] = 'CAPABILITY_REVIEW_REQUIRED'
        return report
    if not hooks_path or not Path(hooks_path).is_file():
        report['code'] = 'COMPANY_HOOKS_REQUIRED'
        return report
    # Hooks are executable code reviewed by the company, never AI output or a download.
    try:
        spec = importlib.util.spec_from_file_location('unithelper_company_hooks', hooks_path)
        module = importlib.util.module_from_spec(spec)
        with quiet_hook():
            spec.loader.exec_module(module)
        hooks = module.CASES
        if not isinstance(hooks, dict) or set(hooks) - set(CASES):
            raise ValueError('Invalid hook keys')
    except (Exception, SystemExit):
        report.update(status='failed', code='HOOK_LOAD_FAILED')
        return report
    for name in CASES:
        hook = hooks.get(name)
        if hook is None:
            continue
        try:
            with quiet_hook():
                if not callable(hook) or hook() is not True:
                    raise ValueError('Case did not verify success')
            report['cases'][name] = 'company_real_passed'
        except (Exception, SystemExit):
            report['cases'][name] = 'failed'
    states = list(report['cases'].values())
    if 'failed' in states:
        report.update(status='failed', code='COMPANY_CASE_FAILED')
    elif 'not_tested' in states:
        report.update(status='not_tested', code='COMPANY_CASES_INCOMPLETE')
    else:
        report.update(status='company_real_passed', code='REGISTERED_CASES_PASSED')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hooks', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--capabilities-reviewed', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = check(args.hooks, args.execute, args.capabilities_reviewed)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n', encoding='utf-8')
    print(text)
    return 0 if report['status'] == 'company_real_passed' else (1 if report['status'] == 'failed' else 2)


if __name__ == '__main__':
    raise SystemExit(main())
