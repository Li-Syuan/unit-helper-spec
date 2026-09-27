import copy
import csv
import io
import tempfile
import unittest
from pathlib import Path

from desktop_app.files import FileError, MAX_BYTES, load_upload, render_csv, render_tsv


class UploadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def file(self, name, content):
        path = self.root / name
        path.write_bytes(content)
        return path

    def test_bom_chinese_original_and_preview(self):
        text = "原文\r\n" + "甲" * 3000
        uploaded = load_upload(self.file("sample.txt", text.encode("utf-8-sig")))
        self.assertEqual(uploaded["text"], text)
        self.assertEqual(len(uploaded["preview"]), 2000)
        self.assertEqual(len(uploaded["sha256"]), 64)

    def test_csv_exact_strings_and_metadata(self):
        uploaded = load_upload(self.file("sample.csv", '工號,內容,金額\r\n00123,"甲,乙",1234567890123456.1234\r\n00124,"多\n行",\r\n'.encode("utf-8-sig")))
        self.assertEqual(uploaded["rows"][0], ["00123", "甲,乙", "1234567890123456.1234"])
        self.assertEqual(uploaded["rows"][1][1], "多\n行")
        self.assertEqual(uploaded["metadata"], {"row_count": 2, "column_count": 3, "empty_cells": 1})

    def test_csv_bad_headers_rows_and_quoting(self):
        for text in ["", "a,a\n1,2", "a, a\n1,2", "a, \n1,2", "a,b\n1", 'a,b\n"unterminated,2', "a,b\n\n"]:
            with self.subTest(text=text), self.assertRaises(FileError):
                load_upload(self.file("bad.csv", text.encode()))

    def test_input_limits_encoding_and_extension(self):
        cases = [("bad.txt", b"a" * (MAX_BYTES + 1)), ("bad.txt", b"a" * 50001),
                 ("bad.txt", b"\xff"), ("bad.txt", b"a\x00b"), ("bad.xlsx", b"anything"),
                 ("bad.csv", ("a\n" + "x\n" * 10001).encode()),
                 ("bad.csv", ",".join(str(i) for i in range(101)).encode())]
        for name, content in cases:
            with self.subTest(name=name, size=len(content)), self.assertRaises(FileError):
                load_upload(self.file(name, content))
        self.assertEqual(len(load_upload(self.file("boundary.txt", b"a" * 50000))["text"]), 50000)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.result = {"columns": [{"name": "id", "label": "工號", "type": "text", "copy_as_text": True},
                                   {"name": "value", "label": "精確值", "type": "decimal"},
                                   {"name": "note", "label": "備註", "type": "text"}],
                       "rows": [["00001", "1234567890123456.1234", "  =1+1"],
                                ["00002", "-42.00", None]]}

    def test_formula_protection_precision_and_snapshot_not_mutated(self):
        original = copy.deepcopy(self.result)
        text, protected = render_tsv(self.result)
        self.assertEqual(text, "工號\t精確值\t備註\r\n00001\t1234567890123456.1234\t'  =1+1\r\n00002\t-42.00\t")
        self.assertEqual(protected, 1)
        self.assertEqual(self.result, original)
        parsed = list(csv.reader(io.StringIO(render_csv(self.result))))
        self.assertEqual(parsed[1], ["00001", "1234567890123456.1234", "'  =1+1"])

    def test_selection_and_cross_page_copy(self):
        self.result["rows"] = [[f"{i:05d}", "1.00", "ok"] for i in range(150)]
        text, _ = render_tsv(self.result)
        self.assertEqual(len(text.splitlines()), 151)
        selected, _ = render_tsv(self.result, [103, 105], False)
        self.assertEqual(selected, "00103\t1.00\tok\r\n00105\t1.00\tok")
        for indices in [[-1], [150], [True], [1, 1]]:
            with self.assertRaises(FileError):
                render_tsv(self.result, indices)

    def test_special_characters_csv_fallback_and_nul(self):
        self.result["rows"][0][2] = '多\n行\t"內容"'
        with self.assertRaises(FileError):
            render_tsv(self.result)
        parsed = list(csv.reader(io.StringIO(render_csv(self.result))))
        self.assertEqual(parsed[1][2], '多\n行\t"內容"')
        # Unselected unsafe data does not prevent safe selected-row copying.
        self.assertIn("00002", render_tsv(self.result, [1])[0])
        self.result["rows"][0][2] = "\x00"
        with self.assertRaises(FileError):
            render_csv(self.result)

    def test_invalid_numeric_never_bypasses_guard(self):
        for value in ["=cmd()", "NaN", "Infinity", True, 0.1]:
            with self.subTest(value=value):
                self.result["rows"][0][1] = value
                with self.assertRaises(FileError):
                    render_tsv(self.result)

    def test_header_formula_and_separator_validation(self):
        self.result["columns"][0]["label"] = "@header"
        self.assertTrue(render_tsv(self.result)[0].startswith("'@header"))
        self.assertEqual(render_tsv(self.result)[1], 2)
        self.result["columns"][0]["label"] = "bad\tlabel"
        with self.assertRaises(FileError):
            render_tsv(self.result)
        self.assertTrue(render_tsv(self.result, include_headers=False)[0].startswith("00001"))


if __name__ == "__main__":
    unittest.main()
