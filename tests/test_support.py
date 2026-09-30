"""Safe local diagnostics contain only reviewed fields, including on failure."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from desktop_app import support


class SupportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.secret='FAKE_API_KEY_PRIVATE_PROMPT_https://private.company.example/user'
    def tearDown(self):self.tmp.cleanup()
    def test_capture_does_not_format_exception_or_include_raw_attributes(self):
        class PrivateError(Exception):
            status_code=403
            def __str__(inner):raise AssertionError('Do not format original error')
            def __repr__(inner):raise AssertionError('Do not repr original error')
        try:raise PrivateError(self.secret)
        except PrivateError as exc:result=support.record(self.root,'run_poll',exc)
        self.assertTrue(result['saved'])
        text=(self.root/'logs/events.jsonl').read_text('utf-8');self.assertNotIn(self.secret,text)
        value=json.loads(text);self.assertEqual(value['code'],'FORBIDDEN');self.assertEqual(value['http_status'],403)
        self.assertEqual(value['id'],result['id']);self.assertIn('version',value)
        self.assertEqual(value['frames'],[])  # The test module is outside the permitted app source directory.
        from desktop_app.assistant_errors import AssistantFailure
        support.record(self.root,'ui',AssistantFailure('RUN_FAILED','run_poll',remote_code='server_error'))
        value=json.loads((self.root/'logs/events.jsonl').read_text('utf-8').splitlines()[-1])
        self.assertEqual((value['code'],value['stage'],value['provider_code']),('RUN_FAILED','run_poll','server_error'))
        value['provider_code']=self.secret
        self.assertNotIn('provider_code',support.clean_record(value))

    def test_export_revalidates_whitelist_and_ignores_corrupted_records(self):
        support.record(self.root,'ui',ValueError(self.secret))
        path=self.root/'logs/events.jsonl';record=json.loads(path.read_text('utf-8'))
        record.update(message=self.secret,endpoint=self.secret,api_key=self.secret,local_path=str(self.root))
        record['frames']=[{'file':'../secret.py','line':1},{'file':str(self.root/'private.py'),'line':1},
                          {'file':'ui.py','line':12,'locals':self.secret,'source':self.secret}]
        invalid=dict(record,frames={'text':self.secret})
        path.write_text(json.dumps(record)+'\n'+json.dumps(invalid)+'\n'+self.secret+'\n',encoding='utf-8')
        (self.root/'.env').write_text(self.secret);(self.root/'private.sqlite3').write_text(self.secret)
        result=support.export_bundle(self.root,self.root/'safe.zip')
        self.assertTrue(result['saved']);self.assertEqual(result['events'],1);self.assertEqual(result['ignored_records'],2)
        with zipfile.ZipFile(self.root/'safe.zip') as archive:
            self.assertEqual(set(archive.namelist()),{'README.txt','diagnostics.json'})
            raw=archive.read('diagnostics.json').decode();report=json.loads(raw)
        self.assertNotIn(self.secret,raw);self.assertNotIn(str(self.root),raw)
        self.assertEqual(report['events'][0]['frames'],[{'file':'ui.py','line':12}])
        self.assertEqual(report['company_real'],'not_tested')
        for value in (None,[],dict(record,stage=[]),dict(record,id=123),dict(record,time=self.secret)):
            self.assertIsNone(support.clean_record(value))

    def test_rotation_bounded_and_logging_failures_return_unsaved(self):
        folder=self.root/'logs';folder.mkdir()
        for _ in range(6):
            (folder/'events.jsonl').write_bytes(b'X'*(1024*1024-10))
            self.assertTrue(support.record(self.root,'background')['saved'])
        self.assertEqual({p.name for p in folder.iterdir()},{'events.jsonl','events.jsonl.1','events.jsonl.2','events.jsonl.3'})
        self.assertTrue(all(p.stat().st_size<=1024*1024 for p in folder.iterdir()))
        with patch.object(support,'RotatingFileHandler',side_effect=PermissionError(self.secret)):
            result=support.record(self.root,'ui',ValueError(self.secret))
        self.assertFalse(result['saved']);self.assertRegex(result['id'],r'^[a-f0-9]{32}$')
        class BrokenError(Exception):
            @property
            def status_code(inner):raise RuntimeError('untrusted exception property')
        self.assertFalse(support.record(self.root,'ui',BrokenError())['saved'])

    def test_export_failure_removes_only_partial_new_file_and_allows_retry(self):
        support.record(self.root,'startup');destination=self.root/'retry.zip'
        with patch.object(zipfile.ZipFile,'writestr',side_effect=OSError(self.secret)):
            with self.assertRaises(OSError):support.export_bundle(self.root,destination)
        self.assertFalse(destination.exists())
        self.assertTrue(support.export_bundle(self.root,destination)['saved'])
        before=destination.read_bytes()
        with self.assertRaises(FileExistsError):support.export_bundle(self.root,destination)
        self.assertEqual(destination.read_bytes(),before)
        with patch.object(Path,'read_text',side_effect=PermissionError(self.secret)):
            with self.assertRaises(PermissionError):support.export_bundle(self.root,self.root/'read-failed.zip')
        self.assertFalse((self.root/'read-failed.zip').exists())

    def test_linked_log_directory_is_not_followed(self):
        with patch.object(Path,'is_symlink',lambda path:path.name=='logs'):
            self.assertFalse(support.record(self.root,'ui')['saved'])
            with self.assertRaises(ValueError):support.export_bundle(self.root,self.root/'linked.zip')
        self.assertFalse((self.root/'linked.zip').exists())
