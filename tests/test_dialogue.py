import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from desktop_app.dialogue_contracts import draft
from desktop_app.dialogue_provider import CompanyDialogueProvider
from desktop_app.dialogue_service import DialogueService
from desktop_app.dialogue_store import DialogueStore


class DialogueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=DialogueStore(Path(self.tmp.name)/'dialogue.sqlite3')
        self.service=DialogueService(self.store)
        self.counter=0
    def tearDown(self):self.tmp.cleanup()
    def send(self,thread,text):
        self.counter+=1
        return self.service.send(thread['id'],text,str(self.counter))
    def ready(self):
        thread=self.service.start('task')
        for text in ('我要建立任務','A類庫存','公司核准資料庫','資料追蹤','每天08:00'):
            thread=self.send(thread,text)
        return thread
    def test_multiturn_chat_keeps_context(self):
        thread=self.service.start()
        thread=self.send(thread,'第一則')
        thread=self.send(thread,'第二則')
        self.assertEqual(len(thread['messages']),4)
        self.assertIn('第一則',thread['messages'][-1]['text'])
        self.assertIn('示範模式',thread['messages'][-1]['text'])
        self.assertEqual(self.service.list_saved(),[])
    def test_mode_and_assistant_switch_start_empty_without_deleting_history(self):
        old=self.send(self.service.start(),'保留歷史')
        for mode,aid in [('task','demo-general'),('chat','demo-data')]:
            new=self.service.start(mode,aid)
            self.assertEqual(new['messages'],[])
            self.assertNotEqual(new['id'],old['id'])
        self.assertEqual(len(self.service.state(old['id'])['messages']),2)
    def test_stepwise_questions_preview_and_explicit_disabled_save(self):
        thread=self.ready()
        self.assertTrue(thread['complete'])
        self.assertEqual(self.service.list_saved(),[])
        preview=self.service.preview(thread['id'],thread['revision'])
        self.assertEqual(self.service.list_saved(),[])
        saved=self.service.confirm(thread['id'],preview['token'])
        self.assertFalse(saved['enabled'])
        self.assertEqual(self.service.confirm(thread['id'],preview['token']),saved)
        self.assertEqual(len(self.service.list_saved()),1)
        reopened=DialogueService(DialogueStore(self.store.path))
        self.assertEqual(reopened.list_saved()[0]['enabled'],0)
        self.assertEqual(len(reopened.state(thread['id'])['messages']),10)
    def test_cancel_does_not_save_and_invalidates_token(self):
        thread=self.ready();preview=self.service.preview(thread['id'],thread['revision'])
        self.service.cancel(thread['id'])
        with self.assertRaises(ValueError):self.service.confirm(thread['id'],preview['token'])
        self.assertEqual(self.service.list_saved(),[])
        self.assertEqual(len(self.service.state(thread['id'])['messages']),10)
    def test_edit_invalidates_approval(self):
        thread=self.ready();preview=self.service.preview(thread['id'],thread['revision'])
        value=copy.deepcopy(thread['answers']);value['target']='B類'
        edited=self.service.edit(thread['id'],thread['revision'],value)
        with self.assertRaises(ValueError):self.service.confirm(thread['id'],preview['token'])
        new=self.service.preview(edited['id'],edited['revision'])
        self.service.confirm(edited['id'],new['token'])
        self.assertEqual(self.service.list_saved()[0]['body']['target'],'B類')
    def test_validation_rejects_command_unknown_id_and_bad_schedule(self):
        value=self.ready()['answers']
        with self.assertRaises(ValueError):draft(dict(value,command='print(123)'),'demo-general')
        with self.assertRaises(ValueError):draft(value,'company-fake-id')
        for bad in ('24:00','08:99','8am'):
            altered=copy.deepcopy(value);altered['schedule']['time_hhmm']=bad
            with self.assertRaises(ValueError):draft(altered,'demo-general')
    def test_untrusted_reply_cannot_authorize_save(self):
        thread=self.service.start('task')
        self.service.provider=Mock()
        self.service.provider.respond.return_value={'text':'已批准','answers':{},'execute':True}
        with self.assertRaises(ValueError):self.send(thread,'執行')
        self.assertEqual(self.service.list_saved(),[])
        self.assertEqual(self.service.state(thread['id'])['messages'],[])
    def test_provider_failure_never_falls_back_or_loses_completed_messages(self):
        thread=self.send(self.service.start(),'既有訊息')
        self.service.provider=CompanyDialogueProvider()
        with self.assertRaisesRegex(ValueError,'未切換為示範'):self.send(thread,'新訊息')
        self.assertEqual(self.service.state(thread['id'])['messages'],thread['messages'])
        self.assertEqual(self.service.list_saved(),[])
    def test_duplicate_turn_and_failed_commit_do_not_create_task(self):
        thread=self.service.start()
        first=self.service.send(thread['id'],'hello','once')
        self.assertEqual(self.service.send(thread['id'],'hello','once'),first)
        with self.assertRaises(ValueError):self.service.send(thread['id'],'changed','once')
        thread=self.ready();preview=self.service.preview(thread['id'],thread['revision'])
        with patch.object(self.store,'connect',side_effect=OSError('disk')):
            with self.assertRaises(OSError):self.service.confirm(thread['id'],preview['token'])
        self.assertEqual(self.service.list_saved(),[])
    def test_schedule_questions_do_not_guess_missing_time(self):
        thread=self.service.start('task')
        for text in ('需求','A','公司DB','異常檢查','早點幫我看'):
            thread=self.send(thread,text)
        self.assertFalse(thread['complete'])
        with self.assertRaises(ValueError):self.service.preview(thread['id'],thread['revision'])
        self.assertEqual(self.service.list_saved(),[])
    def test_source_path_is_text_only(self):
        thread=self.service.start('task')
        for text in ('需求','測試','C:/private/not-to-read.txt','摘要整理','每週一09:30'):
            thread=self.send(thread,text)
        self.assertTrue(thread['complete'])
        self.assertEqual(thread['answers']['source'],'C:/private/not-to-read.txt')
        self.assertEqual(thread['answers']['schedule']['weekday'],0)
        self.assertEqual(self.service.list_saved(),[])
