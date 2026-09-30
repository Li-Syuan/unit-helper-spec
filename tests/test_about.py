"""Publisher fields use synthetic fixtures; never read private publisher.json."""
import json
from pathlib import Path
import tempfile
import tkinter as tk
from unittest import TestCase
from unittest.mock import patch

from desktop_app import about


class PublisherInfoTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / 'publisher.json'
        self.addCleanup(self.temp.cleanup)

    def write(self, value):
        self.path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8-sig')

    def test_only_author_whitelist_is_exposed_and_default_is_project_root(self):
        self.write({'author': {'employee_id': '  SYNTHETIC-007  ', 'name': ' 合成作者 ',
                              'phone': ' +886 (00) SYNTHETIC #123 ', 'private_note': 'DO_NOT_EXPOSE'},
                    'api_key': 'DO_NOT_EXPOSE', 'name': 'wrong top-level name'})
        expected = {'employee_id': 'SYNTHETIC-007', 'name': '合成作者',
                    'phone': '+886 (00) SYNTHETIC #123'}
        with patch.object(about, 'ROOT', self.root):
            self.assertEqual(about.publisher_info(), expected)
            text = about.about_text()
        self.assertNotIn('DO_NOT_EXPOSE', text)
        for label, field in [('工號', 'employee_id'), ('姓名', 'name'), ('電話', 'phone')]:
            self.assertIn(label + '：' + expected[field], text)
        for notice in ('回報目前只存本機', '不會自動送給維護者', '通過不代表公司接線完成',
                       '第三方套件授權', 'docs/licenses'):
            self.assertIn(notice, text)

    def test_missing_corrupt_oversized_and_unreadable_files_have_no_raw_errors(self):
        expected = {field: about.UNSET for field in about.FIELD_LIMITS}
        self.assertEqual(about.publisher_info(self.path), expected)
        for raw in (b'not-json', b'\xff', b'[]', b'{"author":null}', b'{"author":[]}',
                    b' ' * (about.MAX_BYTES + 1)):
            with self.subTest(raw_prefix=raw[:20]):
                self.path.write_bytes(raw)
                self.assertEqual(about.publisher_info(self.path), expected)
        with patch.object(Path, 'open', side_effect=PermissionError('PRIVATE_PATH_OR_ERROR')):
            self.assertEqual(about.publisher_info(self.path), expected)
            self.assertNotIn('PRIVATE_PATH_OR_ERROR', about.about_text(self.path))

    def test_each_field_rejects_nontext_controls_markup_and_overflow(self):
        for field, limit in about.FIELD_LIMITS.items():
            for invalid in (None, False, 123, [], {}, '', '   ', 'x' * (limit + 1),
                            'one\ntwo', 'one\ttwo', 'one\x00two', 'one\u202etwo',
                            'one\u2028two', '<script>synthetic</script>'):
                with self.subTest(field=field, invalid=repr(invalid)):
                    self.write({'author': {'employee_id': 'fixture', 'name': '合成',
                                          'phone': 'synthetic', field: invalid}})
                    self.assertEqual(about.publisher_info(self.path)[field], about.UNSET)
            self.write({'author': {field: '字' * limit}})
            self.assertEqual(about.publisher_info(self.path)[field], '字' * limit)

    def test_example_contains_no_invented_identity_or_contact(self):
        path = Path(__file__).resolve().parents[1] / 'publisher.example.json'
        self.assertEqual(json.loads(path.read_text('utf-8')),
                         {'author': {'employee_id': '', 'name': '', 'phone': ''}})
        self.assertEqual(about.publisher_info(path), {field: about.UNSET for field in about.FIELD_LIMITS})


class PublisherTkTests(TestCase):
    def test_about_displays_shared_author_fields_and_keeps_license_entry(self):
        from desktop_app.display import Display
        from desktop_app.experience import ExperienceMixin
        from desktop_app.theme import Appearance

        with tempfile.TemporaryDirectory() as directory:
            publisher_root = Path(directory)
            (publisher_root / 'publisher.json').write_text(json.dumps({'author': {
                'employee_id': 'SYNTHETIC-007', 'name': '合成作者', 'phone': 'SYNTHETIC-PHONE'}}), encoding='utf-8')
            root = tk.Tk()
            root.withdraw()
            helper = ExperienceMixin()
            helper.root = root
            helper.display = Display(root)
            helper.appearance = Appearance(root, 'dark')
            try:
                with patch.object(about, 'ROOT', publisher_root):
                    window = helper.show_help('關於')
                    root.update()
                    text = window.help_content.get('1.0', 'end-1c')
                    self.assertIn('工號：SYNTHETIC-007', text)
                    self.assertIn('姓名：合成作者', text)
                    self.assertIn('電話：SYNTHETIC-PHONE', text)
                    self.assertEqual(str(window.help_content['state']), 'disabled')
                    self.assertIn('第三方套件授權', window.help_toc.get(0, 'end'))
                    window.destroy()
            finally:
                root.destroy()
