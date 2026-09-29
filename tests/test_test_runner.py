"""Suite selection and truthful evidence; synthetic tests never call company services."""
from contextlib import contextmanager, redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import webview  # Resolve application resources before synthetic runner roots are installed.

from scripts import test_runner as runner


@contextmanager
def restore_cwd():
    import os
    before = Path.cwd()
    try:
        yield
    finally:
        os.chdir(before)


def case(name='test_ok', body=lambda self: None):
    cls = type('ContractTests', (unittest.TestCase,), {'__module__': 'tests.test_fixture', name: body})
    return cls(name)


class RunnerTests(unittest.TestCase):
    def test_selection_is_explicit_nonempty_and_deduplicated(self):
        cases = [case('test_a'), case('test_b')]
        groups = {'tests.test_fixture.ContractTests': 'quick'}
        for mode in ('quick', 'full'):
            self.assertEqual(runner.select_tests(cases, groups, mode, []), cases)
        self.assertEqual(runner.select_tests(cases, groups, 'targeted',
            ['tests.test_fixture', cases[0].id()]), cases)
        self.assertEqual(runner.select_tests(cases, groups, 'targeted', [cases[0].id()]), cases[:1])
        for mode, names in [('targeted', []), ('targeted', ['tests.test_missing']),
                            ('targeted', ['os.system']), ('quick', ['tests.test_fixture']), ('other', [])]:
            with self.subTest(mode=mode, names=names), self.assertRaises(ValueError):
                runner.select_tests(cases, groups, mode, names)
        with self.assertRaises(ValueError):
            runner.select_tests([], {}, 'full', [])

    def test_registry_rejects_new_stale_duplicate_empty_and_import_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'tests').mkdir()
            (root/'tests/test_fixture.py').touch()
            with patch.object(runner.unittest, 'TestLoader') as factory:
                loader = factory.return_value
                loader.discover.side_effect = lambda *a, **kw: unittest.TestSuite([case()])
                loader.errors = []
                valid = {'quick': ['tests.test_fixture.ContractTests'], 'integration': []}
                path = root/'tests/suites.json'
                path.write_text(json.dumps(valid))
                self.assertEqual(len(runner.classified_tests(root)[0]), 1)
                invalid = [None, 42, [], {'quick': [], 'integration': []},
                           {'quick': valid['quick']+['tests.test_stale.X'], 'integration': []},
                           {'quick': valid['quick'], 'integration': valid['quick']}]
                for value in invalid:
                    path.write_text(json.dumps(value))
                    with self.assertRaises(ValueError): runner.classified_tests(root)
                path.write_text(json.dumps(valid))
                loader.errors = ['synthetic import failure']
                with self.assertRaisesRegex(ValueError, 'import failed'): runner.classified_tests(root)
                loader.errors = []
                (root/'tests/test_empty.py').touch()
                with self.assertRaisesRegex(ValueError, 'without cases'): runner.classified_tests(root)

    def test_failures_skips_and_expected_failures_never_pass(self):
        def fail(self): self.fail('synthetic failure')
        def error(self): raise ValueError('synthetic error')
        def skip(self): self.skipTest('synthetic skip')
        for body in (fail, error, skip, unittest.expectedFailure(fail), unittest.expectedFailure(lambda self: None)):
            result = runner.execute([case(body=body)], stream=io.StringIO())
            self.assertFalse(result['passed'])
            self.assertEqual(result['count'], 1)
            self.assertEqual(len(result['tests']), 1)
        self.assertFalse(runner.execute([], stream=io.StringIO())['passed'])
        self.assertTrue(runner.execute([case()], stream=io.StringIO())['passed'])

    def test_quick_blocks_unexpected_gui_and_socket(self):
        def gui(self):
            import tkinter
            tkinter.Tk()
        def network(self):
            import socket
            with socket.socket() as connection: connection.connect(('127.0.0.1', 9))
        def web(self):
            import webview
            webview.create_window('forbidden')
        for body in (gui, web, network):
            result = runner.execute([case(body=body)], quick=True, stream=io.StringIO())
            self.assertFalse(result['passed'])
            self.assertIn('Quick suite forbids', result['output'])

    def test_cli_report_is_scoped_overwritten_and_full_checks_run_once(self):
        import os
        before = Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as directory, patch.object(runner, 'ROOT', Path(directory)), \
                    patch.object(runner, 'environment_checks', return_value=([], True)) as checks, \
                    patch.object(runner, 'classified_tests') as discover, \
                    restore_cwd(), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                discover.side_effect = lambda: ([case()], {'tests.test_fixture.ContractTests': 'quick'})
                report_path = Path(directory)/'artifacts/testing/latest.json'
                self.assertEqual(runner.main([]), 0, report_path.read_text())
                self.assertEqual(json.loads(report_path.read_text())['suite'], 'quick')
                self.assertNotIn(b'\r\n', report_path.read_bytes())
                checks.assert_not_called()
                self.assertEqual(runner.main(['--suite','targeted','--tests','tests.test_fixture']), 0)
                self.assertEqual(json.loads(report_path.read_text())['suite'], 'targeted')
                self.assertEqual(runner.main(['--suite','full','--evidence','fixture']), 0)
                checks.assert_called_once()
                self.assertTrue((Path(directory)/'docs/validation/fixture.json').is_file())
                checks.return_value = ([], False)
                self.assertEqual(runner.main(['--suite','full']), 1)
                self.assertFalse(json.loads(report_path.read_text())['passed'])
                def fail(self): self.fail('fixture')
                discover.side_effect = lambda: ([case(body=fail)], {'tests.test_fixture.ContractTests': 'quick'})
                self.assertEqual(runner.main(['--suite','targeted','--tests','tests.test_fixture']), 1)
                self.assertEqual(json.loads(report_path.read_text())['result']['failures'], 1)
                # Do not remove a temporary directory while it is the Windows cwd.
                os.chdir(before)
        finally: os.chdir(before)
