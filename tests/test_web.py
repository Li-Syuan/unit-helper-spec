import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge
from desktop_app.web_render import render_markdown


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.session = WebSession(directory=self.tmp.name)
        self.api = WebBridge(self.session)

    def tearDown(self):
        self.session.close()
        self.tmp.cleanup()

    def call(self, name, **payload):
        result = self.api.call(name, payload)
        self.assertTrue(result['ok'], result)
        return result['data']

    def wait(self, tid):
        deadline = time.monotonic()+5
        while self.session.engine.has_inflight() and time.monotonic()<deadline:
            time.sleep(.01)
        return self.session.store.task(tid)

    def test_initial_state_and_draft_isolation(self):
        state = self.call('state')
        cid = state['conversation']['id']
        self.call('save_draft', cid=cid, text='原文', purpose='summarize', planned=True, seq=2)
        self.call('save_draft', cid=cid, text='舊內容', purpose='chat', seq=1)
        self.assertEqual(self.call('state',cid=cid)['draft']['text'],'原文')
        other = self.call('new_chat')
        self.assertIsNone(self.call('state',cid=other)['draft'])
        self.assertEqual(self.session.store.tasks(),[])

    def test_chat_and_plan_use_existing_gates(self):
        cid = self.call('new_chat')
        result = self.call('send',cid=cid,text='hello',purpose='chat',planned=True,request_id='p1',seq=1)
        self.assertEqual(self.session.store.tasks(),[])
        plan = self.call('plan_preview',plan_id=result['plan_id'])
        tid = self.call('plan_confirm',plan_id=plan['id'],revision=plan['revision'],request_id='approve1')
        self.assertEqual(self.wait(tid)['state'],'succeeded')
        self.assertEqual(self.call('plan_confirm',plan_id=plan['id'],revision=plan['revision'],request_id='approve1'),tid)
        self.assertEqual(len(self.session.store.tasks()),1)

    def test_query_preview_requires_confirmation(self):
        cid=self.call('new_chat')
        preview=self.call('query_preview',cid=cid,query_id='DEMO03',parameters={'category':'A','from_date':'2026-09-20','to_date':'2026-09-21'})
        self.assertTrue(preview['ready'],preview)
        self.assertEqual(self.session.store.tasks(),[])
        record=self.session.actions.list(cid)[0]
        result=self.call('action_confirm',action_id=record['id'],revision=record['revision'])
        tasks=self.session.store.tasks()
        self.assertEqual(len(tasks),1)
        self.assertEqual(self.wait(tasks[0]['id'])['state'],'succeeded')

    def test_no_arbitrary_commands_or_sensitive_errors(self):
        self.assertFalse(self.api.call('eval',{'text':'x'})['ok'])
        with patch.object(self.session.store,'conversations',side_effect=RuntimeError('SECRET')):
            result=self.api.call('state',{})
        self.assertFalse(result['ok'])
        self.assertNotIn('SECRET',json.dumps(result))

    def test_markdown_cannot_execute_or_fetch(self):
        output=render_markdown('<script>alert(1)</script>\n\n[x](javascript:alert(1)) ![x](https://evil/x)\n\n**粗體**\n\n|A|B|\n|-|-|\n|1|2|')
        self.assertNotIn('<script',output)
        self.assertNotIn('<img',output)
        self.assertNotIn('href=',output)
        self.assertIn('<strong>',output)
        self.assertIn('<table>',output)

    def test_todo_repeated_save_and_source_deletion(self):
        cid=self.call('new_chat')
        payload=dict(title='核對成果',description='另存內容',source_conversation_id=cid,request_id='t1')
        todo=self.call('todo_save',**payload)
        self.assertEqual(self.call('todo_save',**payload)['id'],todo['id'])
        preview=self.call('delete_preview',ids=[cid])
        self.call('delete_confirm',token=preview['token'])
        self.assertEqual(self.session.store.todo(todo['id'])['description'],'另存內容')

    def test_trial_rejects_company_config(self):
        with self.assertRaises(ValueError):
            WebSession(directory=self.tmp.name,config={},groq_trial=True)

    def test_close_rejects_further_dispatch(self):
        self.session.close()
        self.assertFalse(self.api.call('new_chat',{})['ok'])

    def test_transfer_preview_is_pure_and_confirmation_idempotent(self):
        cid=self.call('new_chat')
        preview=self.call('transfer_preview',cid=cid,text='只選此段',profile_id='demo')
        self.assertEqual(self.session.store.tasks(),[])
        result=self.call('transfer_confirm',token=preview['token'])
        self.assertEqual(self.call('transfer_confirm',token=preview['token']),result)
        self.assertEqual(self.wait(result['task_id'])['state'],'succeeded')
        self.assertNotEqual(result['cid'],cid)

    def test_deleted_source_invalidates_transfer(self):
        cid=self.call('new_chat')
        preview=self.call('transfer_preview',cid=cid,text='來源',profile_id='demo')
        delete=self.call('delete_preview',ids=[cid])
        self.call('delete_confirm',token=delete['token'])
        self.assertFalse(self.api.call('transfer_confirm',{'token':preview['token']})['ok'])
        self.assertEqual(self.session.store.tasks(),[])

    def test_send_fences_old_draft_and_changed_idempotency_payload(self):
        cid=self.call('new_chat')
        self.call('save_draft',cid=cid,text='文字',seq=1)
        p=dict(cid=cid,text='文字',seq=2,request_id='send-once')
        result=self.call('send',**p)
        self.assertEqual(self.call('send',**p),result)
        self.wait(result['task_id'])
        self.assertFalse(self.api.call('send',dict(p,text='不同內容'))['ok'])
        self.call('save_draft',cid=cid,text='舊內容',seq=1)
        self.assertIsNone(self.session.store.draft(cid))

    def test_company_intent_uses_form_without_model(self):
        cid=self.call('new_chat')
        with patch('desktop_app.intent_drafts.extract_action',side_effect=AssertionError('must not call')):
            record=self.call('intent_prepare',cid=cid,text='每天查資料',kind='schedule',seq=1)
        self.assertEqual(record['state'],'draft')
        self.assertEqual(self.session.store.tasks(),[])
        self.assertEqual(self.session.store.schedules(),[])

    def test_clipboard_export_uses_precision_and_formula_protection(self):
        tid=self.session.engine.run_query('DEMO01',{'from_date':'2026-09-20','to_date':'2026-09-21','category':'A'})
        self.wait(tid)
        result=self.call('table_export',task_id=tid,format='tsv')
        self.assertIn('料號',result['text'])
        self.assertIsInstance(result['protected_cells'],int)
