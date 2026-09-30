"""Shared, offline unittest runner. Daily reports are local; release evidence is explicit."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def classified_tests(root=ROOT):
    registry = json.loads((root / 'tests/suites.json').read_text(encoding='utf-8'))
    if not isinstance(registry, dict) or set(registry) != {'quick', 'integration'}:
        raise ValueError('Suite registry must contain quick and integration.')
    groups = {}
    for group, names in registry.items():
        if not isinstance(names, list):
            raise ValueError('Suite classes must be a list.')
        for name in names:
            if not isinstance(name, str) or name in groups:
                raise ValueError('Invalid or duplicate suite class.')
            groups[name] = group
    loader = unittest.TestLoader()
    cases = list(flatten(loader.discover(str(root / 'tests'), top_level_dir=str(root))))
    if loader.errors:
        raise ValueError('Test import failed:\n' + '\n'.join(loader.errors))
    ids = [case.id() for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate test IDs discovered.')
    classes = {case.id().rsplit('.', 1)[0] for case in cases}
    unknown, stale = classes - groups.keys(), groups.keys() - classes
    if unknown or stale:
        raise ValueError(f'Unclassified classes: {sorted(unknown)}; stale classes: {sorted(stale)}')
    modules = {case.__class__.__module__ for case in cases}
    empty = {'.'.join(p.relative_to(root).with_suffix('').parts)
             for p in (root / 'tests').rglob('test_*.py')} - modules
    if empty:
        raise ValueError(f'Test modules without cases: {sorted(empty)}')
    if not cases:
        raise ValueError('No tests discovered.')
    return cases, groups


def select_tests(cases, groups, suite, selectors):
    if suite not in ('quick', 'targeted', 'full'):
        raise ValueError('Unknown suite.')
    if suite != 'targeted' and selectors:
        raise ValueError('--tests is only valid with --suite targeted.')
    if suite == 'targeted':
        if not selectors:
            raise ValueError('Targeted suite requires --tests.')
        selected = set()
        for name in selectors:
            if not re.fullmatch(r'tests\.test_[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){0,2}', name):
                raise ValueError('Use a tests.test_module, class or test method selector.')
            matched = {case.id() for case in cases if case.id() == name or case.id().startswith(name + '.')}
            if not matched:
                raise ValueError(f'No tests match: {name}')
            selected.update(matched)
        result = [case for case in cases if case.id() in selected]
    else:
        result = [case for case in cases if suite == 'full' or groups[case.id().rsplit('.', 1)[0]] == 'quick']
    if not result:
        raise ValueError('No tests selected.')
    return result


class TimedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings = []
        self._starts = {}

    def startTest(self, test):
        self._starts[test.id()] = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        elapsed = time.perf_counter() - self._starts.pop(test.id())
        self.timings.append({'id': test.id(), 'seconds': round(elapsed, 4)})
        super().stopTest(test)


class Tee:
    def __init__(self, stream):
        self.stream, self.capture = stream, io.StringIO()

    def write(self, value):
        self.stream.write(value)
        self.capture.write(value)
        self.flush()

    def flush(self):
        self.stream.flush()


def execute(cases, quick=False, stream=None):
    output = Tee(stream if stream is not None else sys.stdout)
    started = time.perf_counter()
    with ExitStack() as guards:
        # A misclassified GUI or live socket must fail, never silently join quick.
        if quick:
            for target in ('tkinter.Tk', 'webview.create_window', 'webview.start',
                           'socket.socket.connect', 'socket.socket.connect_ex'):
                guards.enter_context(patch(target, side_effect=AssertionError('Quick suite forbids GUI/network access')))
        result = unittest.TextTestRunner(stream=output, verbosity=2, resultclass=TimedResult).run(unittest.TestSuite(cases))
    passed = (result.wasSuccessful() and result.testsRun > 0 and not result.skipped
              and not result.expectedFailures and result.testsRun == len(cases))
    return {'passed': passed, 'count': result.testsRun, 'seconds': round(time.perf_counter() - started, 4),
            'skipped': len(result.skipped), 'failures': len(result.failures), 'errors': len(result.errors),
            'expected_failures': len(result.expectedFailures), 'unexpected_successes': len(result.unexpectedSuccesses),
            'tests': result.timings, 'output': output.capture.getvalue()}


def environment_checks():
    records = []
    for args in (['scripts/doctor.py'], ['-m', 'pip', 'check'], ['-m', 'pip', 'freeze', '--all']):
        print('Environment: ' + ' '.join(args), flush=True)
        started = time.perf_counter()
        try:
            process = subprocess.run([sys.executable, *args], cwd=ROOT, text=True, encoding='utf-8',
                                     errors='replace', capture_output=True, timeout=120,
                                     env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
            output, code = process.stdout + process.stderr, process.returncode
        except subprocess.TimeoutExpired:
            output, code = 'Environment check timed out.', 2
        print(output, flush=True)
        records.append({'command': [sys.executable, *args], 'exit_code': code, 'output': output,
                        'seconds': round(time.perf_counter() - started, 4)})
    installed = records[-1]['output'].splitlines()
    lock = (ROOT / 'requirements.lock').read_text('ascii').splitlines()
    matched = sorted(installed) == sorted(lock)
    records[-1]['matches_lock'] = matched
    if not matched:
        print('Installed packages differ from requirements.lock.', flush=True)
    return records, matched and all(record['exit_code'] == 0 for record in records)


def save_report(report, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    temporary.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=('quick', 'targeted', 'full'), default='quick')
    parser.add_argument('--tests', nargs='+', default=[])
    parser.add_argument('--evidence', help='Explicit full-suite release evidence label')
    args = parser.parse_args(argv)
    if args.evidence and (args.suite != 'full' or not re.fullmatch('[a-z-]+', args.evidence)):
        parser.error('--evidence requires full suite and a lowercase hyphenated label')
    os.chdir(ROOT)
    started = time.perf_counter()
    report = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'environment': sys.executable,
              'python': platform.python_version(), 'architecture_bits': __import__('struct').calcsize('P') * 8,
              'suite': args.suite, 'selectors': args.tests, 'passed': False, 'commands': [],
              'company_real': 'not_tested', 'webview_smoke': 'not_tested', 'status': 'running',
              'discovered': None, 'selected': None,
              'result': {'status': 'not_run', 'count': 0, 'tests': []}}
    save_report(report, ROOT / 'artifacts/testing/latest.json')
    try:
        if sys.version_info[:3] != (3, 10, 4) or sys.flags.optimize:
            raise ValueError('Tests require Python exactly 3.10.4 without -O.')
        if args.suite == 'full':
            report['commands'], environment_ok = environment_checks()
            if not environment_ok:
                raise ValueError('Full-suite environment checks failed; tests were not discovered or run. '
                                 'Restore the environment from requirements.lock and inspect commands in the report.')
        cases, groups = classified_tests()
        selected = select_tests(cases, groups, args.suite, args.tests)
        report.update(discovered=len(cases), selected=len(selected))
        print(f'Suite: {args.suite}; selected {len(selected)}/{len(cases)}. Company services NOT tested.', flush=True)
        result = execute(selected, quick=args.suite == 'quick')
        report['result'] = {key: value for key, value in result.items() if key != 'output'}
        report['result']['status'] = 'completed'
        report['commands'].append({'command': [sys.executable, 'scripts/test_runner.py', '--suite', args.suite, *(['--tests', *args.tests] if args.tests else [])],
                                   'exit_code': 0 if result['passed'] else 1, 'output': result['output'], 'seconds': result['seconds']})
        report['passed'] = result['passed']
        report['slowest'] = sorted(result['tests'], key=lambda item: item['seconds'], reverse=True)[:10]
        for item in report['slowest']:
            print(f"  {item['seconds']:.3f}s {item['id']}")
    except (ValueError, OSError, RuntimeError) as error:
        report['error'] = str(error)
        print(str(error), file=sys.stderr)
    except KeyboardInterrupt:
        report['error'] = 'Interrupted; this run is incomplete.'
        print(report['error'], file=sys.stderr)
    report['status'] = 'passed' if report['passed'] else 'failed'
    report['seconds'] = round(time.perf_counter() - started, 4)
    save_report(report, ROOT / 'artifacts/testing/latest.json')
    if args.evidence:
        save_report(report, ROOT / 'docs/validation' / (args.evidence + '.json'))
    print(f"{args.suite}: {'PASSED' if report['passed'] else 'FAILED'} ({report['seconds']:.2f}s). artifacts/testing/latest.json", flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
