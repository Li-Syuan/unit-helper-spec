"""Failure coverage for the fixed offline launcher check."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check-launch.py'
spec = importlib.util.spec_from_file_location('qa_launch_check', SCRIPT)
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


class LaunchCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qa launch ' 中文 ")
        self.project = Path(self.tmp.name)
        for relative in ('.venv/Scripts/python.exe', '.venv/Scripts/pythonw.exe',
                         'desktop_app/assets/qa-agent.ico', 'desktop_app/assets/qa-agent.png'):
            target = self.project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'fixture')

    def tearDown(self):
        self.tmp.cleanup()

    def test_version_architecture_and_platform_fail_closed(self):
        cases = [('version_info', (3, 10, 5), 'PYTHON_3104_REQUIRED'),
                 ('platform', 'linux', 'WINDOWS_REQUIRED')]
        for attribute, value, code in cases:
            with self.subTest(attribute=attribute), patch.object(launch.sys, attribute, value):
                with self.assertRaisesRegex(launch.LaunchCheckError, code):
                    launch.check_environment(self.project)
        with patch.object(launch.struct, 'calcsize', return_value=4):
            with self.assertRaisesRegex(launch.LaunchCheckError, 'PYTHON_X64_REQUIRED'):
                launch.check_environment(self.project)

    def test_missing_asset_fails_before_tk(self):
        (self.project / 'desktop_app/assets/qa-agent.png').unlink()
        with patch.object(launch.importlib, 'import_module') as importer:
            with self.assertRaisesRegex(launch.LaunchCheckError, 'REQUIRED_PROJECT_FILE_MISSING'):
                launch.check_environment(self.project)
            importer.assert_not_called()

    def test_tk_and_sdk_failures_are_clear_and_cleanup_root(self):
        with patch.object(launch.importlib, 'import_module', side_effect=ImportError('private details')):
            with self.assertRaisesRegex(launch.LaunchCheckError, '^TCL_TK_UNAVAILABLE$'):
                launch.check_environment(self.project)
        tk_module = Mock()
        with patch.object(launch.importlib, 'import_module', side_effect=[tk_module, ImportError('secret')]):
            with self.assertRaisesRegex(launch.LaunchCheckError, '^OPENAI_SDK_UNAVAILABLE$'):
                launch.check_environment(self.project, check_sdk=True)
        tk_module.Tk.return_value.destroy.assert_called_once()

    def test_sdk_check_optional_for_relocated_shortcut_fixture(self):
        tk_module = Mock()
        with patch.object(launch.importlib, 'import_module', return_value=tk_module) as importer:
            launch.check_environment(self.project)
            importer.assert_called_once_with('tkinter')
        tk_module.Tk.return_value.destroy.assert_called_once()


if __name__ == '__main__':
    unittest.main()
