import gc
import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch,Mock

from desktop_app.report_drafts import extract_draft,looks_like_report
from desktop_app.gateways import GatewayError
from desktop_app.ui import App


class DraftTests(unittest.TestCase):
    def test_schema_and_no_execution(self):
        client=Mock();client._complete.return_value=json.dumps({'query_id':'DEMO03','time_hhmm':'08:00','frequency':'daily','date_mode':'previous_day','category':'A','questions':[]})
        result=extract_draft('每天八點查昨天 A 類數量合計',client)
        self.assertEqual(result['time_hhmm'],'08:00')
        schema=client._complete.call_args.kwargs['response_format']['json_schema']
        self.assertTrue(schema['strict']);self.assertFalse(schema['schema']['additionalProperties'])
        self.assertNotIn('anyOf',json.dumps(schema['schema']))
        client.close.assert_not_called()

    def test_invalid_fields_and_secret_error_rejected(self):
        for raw in ('not json','{}',json.dumps({'query_id':'SQL','secret':'private'}),json.dumps({'query_id':'DEMO03','time_hhmm':'25:00','frequency':'daily','date_mode':'previous_day','category':'A','questions':[]})):
            client=Mock();client._complete.return_value=raw
            with self.assertRaises(GatewayError) as error:extract_draft('每天查資料',client)
            self.assertNotIn('private',str(error.exception))

    def test_bounds_and_intent(self):
        client=Mock()
        for text in ('','x'*2001):
            with self.assertRaises(GatewayError):extract_draft(text,client)
        client._complete.assert_not_called()
        self.assertTrue(looks_like_report('每天八點查資料寫日報'))
        self.assertFalse(looks_like_report('你好'))


class ReportViewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=tk.Tk();self.root.withdraw()
        self.key=patch('desktop_app.trial.read_key',return_value='synthetic');self.key.start()
        self.app=App(self.root,directory=Path(self.temp.name),groq_trial=True)
        self.root.deiconify();self.root.update()

    def tearDown(self):
        self.app.close(force=True);self.app=None;self.root=None;gc.collect();self.key.stop();self.temp.cleanup()

    def complete(self,controls):
        controls['values']['query_id'].set('DEMO03');controls['query_name'].set('示範數量合計')
        controls['values']['time_hhmm'].set('08:00');controls['consent'].set(True)

    def test_chat_opens_confirmation_without_dispatch_and_preserves_draft(self):
        a=self.app;a.input.insert('1.0','每天八點查昨天庫存寫日報')
        with patch('desktop_app.trial.GroqAssistant') as client:
            a.send_chat();self.root.update();client.assert_not_called()
        self.assertEqual(a.store.tasks(),[]);self.assertEqual(a.store.schedules(),[])
        self.assertIn('每天',a.input.get('1.0','end'))

    def test_preview_consent_edit_invalidation_approve_and_theme(self):
        w=self.app.open_report_schedule();self.root.update();c=w.report_controls
        self.complete(c);c['preview']();self.assertEqual(self.app.store.schedules(),[])
        self.assertEqual(str(c['confirm']['state']),'normal')
        c['values']['time_hhmm'].set('09:00')
        self.assertIsNone(c['state']['token']);self.assertFalse(c['consent'].get())
        with self.assertRaises(GatewayError):c['approve']()
        c['consent'].set(True);c['preview']()
        self.app.change_theme('light');self.root.update()
        self.assertTrue(c['confirm'].winfo_viewable())
        self.assertLessEqual(c['confirm'].winfo_rooty()+c['confirm'].winfo_height(),w.winfo_rooty()+w.winfo_height())
        c['approve']();self.assertEqual(len(self.app.store.schedules()),1)
        self.assertTrue(self.app.store.schedules()[0]['enabled'])
        self.assertEqual(self.app.store.tasks(),[])
        self.app.schedule_details();self.assertIn('日報',self.app.schedule_info.get('1.0','end'))

    def test_close_revokes_preview_and_unapproved_no_schedule(self):
        w=self.app.open_report_schedule();self.root.update();c=w.report_controls
        self.complete(c);c['preview']();token=c['state']['token'];w.destroy()
        with self.assertRaises(ValueError):self.app.engine.confirm_report(token)
        self.assertEqual(self.app.store.schedules(),[])

    def test_late_parse_does_not_replace_edited_request(self):
        w=self.app.open_report_schedule();self.root.update();c=w.report_controls;queued=[]
        with patch.object(self.app,'background',side_effect=lambda work,callback:queued.append(callback)):
            c['parse']()
        c['values']['time_hhmm'].set('10:00')
        queued[0](({'query_id':'DEMO01','time_hhmm':'08:00','category':'all','questions':[],'frequency':'daily','date_mode':'previous_day'},None))
        self.assertEqual(c['values']['time_hhmm'].get(),'10:00')
        self.assertIn('不套用',c['message'].get())
