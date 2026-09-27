import io
from contextlib import redirect_stdout, redirect_stderr
import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path
from desktop_app.gateways import DemoQueries
from scripts.company_check import CASES, check
from test_support.query_contract import QueryContractMixin, assert_query_result

PARAMETERS = {'from_date': '2026-09-25', 'to_date': '2026-09-26', 'category': 'all'}


class DemoContractTests(QueryContractMixin, unittest.TestCase):
    query_id = 'DEMO02'
    valid_parameters = PARAMETERS
    invalid_parameters = [dict(PARAMETERS, unknown='x'), dict(PARAMETERS, category='INVALID')]
    def make_gateway(self):
        return DemoQueries()


class ContractToolsTests(unittest.TestCase):
    def test_result_contract_empty_truncated_precision_and_corruption(self):
        result = DemoQueries().run('DEMO02', PARAMETERS)
        result['rows'] = [['2026-09-25', '00001234567890123456', 'A', '12345678901234567890.0001']]
        result['row_count'] = 1
        assert_query_result(self, result, 'DEMO02', PARAMETERS)
        for change in ({'row_count': 2}, {'truncated': 'false'}, {'rows': [['x']]},
                       {'rows': [['2026-09-25', '001', 'A', 1.2]]},
                       {'rows': [['2026-09-25', '001', 'A', 'NaN']]}):
            with self.subTest(change=change), self.assertRaises((AssertionError, ValueError)):
                assert_query_result(self, dict(result, **change), 'DEMO02', PARAMETERS)
        for truncated in (False, True):
            empty = dict(result, rows=[], row_count=0, truncated=truncated)
            assert_query_result(self, empty, 'DEMO02', PARAMETERS)

    def test_no_hooks_import_without_explicit_execution_and_review(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'hooks.py'
            marker = Path(directory) / 'marker'
            path.write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()\nCASES={}\n')
            self.assertEqual(check(path)['status'], 'not_tested')
            self.assertEqual(check(path, True)['code'], 'CAPABILITY_REVIEW_REQUIRED')
            self.assertFalse(marker.exists())
            self.assertEqual(check(path, True, True)['code'], 'COMPANY_CASES_INCOMPLETE')
            self.assertTrue(marker.exists())

    def test_missing_failed_and_passed_are_separate_and_errors_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'hooks.py'
            path.write_text('def fail():\n    raise RuntimeError("PRIVATE-TOKEN")\nCASES={"chatbot.reply":fail}\n')
            report = check(path, True, True)
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['cases']['chatbot.isolation'], 'not_tested')
            self.assertNotIn('PRIVATE-TOKEN', json.dumps(report))
            path.write_text('CASES={name:(lambda: True) for name in '+repr(CASES)+'}\n')
            report = check(path, True, True)
            self.assertEqual(report['status'], 'company_real_passed')
            self.assertEqual(set(report['cases'].values()), {'company_real_passed'})
            path.write_text('CASES={"chatbot.reply":lambda:"true"}\n')
            self.assertEqual(check(path, True, True)['status'], 'failed')

    def test_load_failure_is_not_company_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'hooks.py'
            path.write_text('raise RuntimeError("PRIVATE")\n')
            report = check(path, True, True)
            self.assertEqual(report['code'], 'HOOK_LOAD_FAILED')
            self.assertNotIn('PRIVATE', json.dumps(report))
        self.assertEqual(check(None, True, True)['code'], 'COMPANY_HOOKS_REQUIRED')

class HookLoggingTests(unittest.TestCase):
    def test_hook_output_suppressed_and_system_exit_not_passed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'hooks.py'
            path.write_text('print("PRIVATE-IMPORT")\n'
                            'def fail():\n    print("PRIVATE-BODY")\n    raise SystemExit(0)\n'
                            'CASES={"chatbot.reply":fail}\n')
            sink = io.StringIO()
            with redirect_stdout(sink), redirect_stderr(sink):
                report = check(path, True, True)
            self.assertEqual(sink.getvalue(), '')
            self.assertEqual(report['status'], 'failed')

class CompanyCommandTests(unittest.TestCase):
    def test_documented_cli_can_import_project_and_optimized_mode_refused(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'hooks.py'
            path.write_text('from desktop_app import __version__\n'
                            'from test_support.query_contract import assert_query_result\n'
                            'CASES={"chatbot.reply":lambda: bool(__version__)}\n')
            for flags, code in [([], 'COMPANY_CASES_INCOMPLETE'), (['-O'], 'OPTIMIZED_PYTHON_UNSUPPORTED')]:
                result = subprocess.run([sys.executable, *flags, str(root/'scripts/company_check.py'),
                    '--hooks', str(path), '--execute', '--capabilities-reviewed'],
                    cwd=directory, capture_output=True, text=True, timeout=10)
                report = json.loads(result.stdout)
                self.assertEqual(report['code'], code)
                self.assertNotEqual(result.returncode, 0)
                if not flags:
                    self.assertEqual(report['cases']['chatbot.reply'], 'company_real_passed')
