"""Real Windows shortcut integration checks; never touches the user's Desktop."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'QA agent desktop launcher [unit-helper-spec]'
FIXTURE = ROOT / 'tests/helpers/shortcut-fixture.ps1'


def powershell_file(script, *arguments):
    return subprocess.run(
        ['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-File', str(script),
         *map(str, arguments)],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45,
    )


class ShortcutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='qa-shortcut-')
        self.destination = Path(self.tmp.name)
        self.shortcut = self.destination / 'QA agent.lnk'

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, project=ROOT, destination=None):
        return powershell_file(project / 'scripts/create-shortcut.ps1',
                               '-Destination', destination or self.destination)

    def inspect(self):
        result = powershell_file(FIXTURE, '-Action', 'Inspect', '-ShortcutPath', self.shortcut)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def assert_target(self, project):
        data = self.inspect()
        self.assertEqual(Path(data['target']), project / '.venv/Scripts/pythonw.exe')
        self.assertEqual(data['arguments'], '-m desktop_app')
        self.assertEqual(Path(data['directory']), project)
        self.assertEqual(data['icon'], str(project / 'desktop_app/assets/qa-agent.ico') + ',0')
        self.assertEqual(data['description'], MARKER)

    def test_create_and_repeat_update(self):
        for _ in range(2):
            result = self.create()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_target(ROOT)
        self.assertEqual(list(self.destination.glob('*.lnk')), [self.shortcut])

    def test_unrelated_shortcut_is_preserved(self):
        result = powershell_file(FIXTURE, '-Action', 'CreateUnrelated', '-ShortcutPath', self.shortcut)
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.shortcut.read_bytes()
        result = self.create()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.shortcut.read_bytes(), before)
        self.assertIn('unrelated', result.stderr)

    def fixture_project(self):
        project = self.destination / "relocated project ' 中文"
        for relative in ['scripts/create-shortcut.ps1', 'scripts/check-launch.py',
                         '.venv/Scripts/python.exe', '.venv/Scripts/pythonw.exe', '.venv/pyvenv.cfg',
                         'desktop_app/assets/qa-agent.ico', 'desktop_app/assets/qa-agent.png']:
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        return project

    def test_relocation_updates_managed_shortcut(self):
        result = self.create()
        self.assertEqual(result.returncode, 0, result.stderr)
        project = self.fixture_project()
        result = self.create(project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_target(project)

    def test_missing_assets_do_not_change_existing_shortcut(self):
        result = self.create()
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.shortcut.read_bytes()
        project = self.fixture_project()
        (project / 'desktop_app/assets/qa-agent.png').unlink()
        result = self.create(project)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.shortcut.read_bytes(), before)
        self.assertIn('missing', result.stderr)

    def test_invalid_destination_is_not_created(self):
        target = self.destination / 'missing-directory'
        result = self.create(destination=target)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
