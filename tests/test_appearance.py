"""Appearance choices persist independently of company settings and work."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from desktop_app.preferences import load_color_style, load_preferences, save_appearance, update_preferences
from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge


class AppearancePreferencesTests(unittest.TestCase):
    def test_missing_corrupt_and_invalid_styles_default_to_ocean(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ui-preferences.json'
            self.assertEqual(load_color_style(path),'ocean')
            for content in ('broken','[]','{"color_style": []}','{"color_style": "unknown"}'):
                path.write_text(content,encoding='utf-8')
                self.assertEqual(load_color_style(path),'ocean')

    def test_atomic_pair_preserves_unrelated_preferences(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ui-preferences.json'
            update_preferences(path,{'sidebar_collapsed':True,'page_hints':{'chat':False}})
            save_appearance(path,'light','forest')
            before=path.read_bytes()
            self.assertEqual(load_color_style(path),'forest')
            with patch('desktop_app.preferences.os.replace',side_effect=OSError('synthetic')):
                with self.assertRaises(OSError):save_appearance(path,'dark','violet')
            self.assertEqual(before,path.read_bytes())
            self.assertEqual(load_preferences(path)['page_hints'],{'chat':False})
            self.assertEqual(list(Path(tmp).glob('.appearance-*.tmp')),[])


class WebAppearanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.session=WebSession(directory=self.temp.name)
        self.api=WebBridge(self.session)

    def tearDown(self):
        self.session.close();self.temp.cleanup()

    def call(self,name,payload=None):
        result=self.api.call(name,payload)
        self.assertTrue(result['ok'],result)
        return result['data']

    def test_six_choices_reset_and_reopen_do_not_dispatch_or_touch_connection(self):
        initial=self.call('state')
        cid=initial['conversation']['id']
        self.call('save_draft',dict(cid=cid,text='未送出的草稿',purpose='chat',planned=True,seq=1))
        update_preferences(self.session.preferences_path,{'sidebar_collapsed':True})
        for mode in ('dark','light'):
            for style in ('ocean','violet','forest'):
                result=self.call('appearance',dict(theme=mode,color_style=style))
                self.assertTrue(result['saved'])
                state=self.call('state',{'cid':cid})
                self.assertEqual((state['theme'],state['color_style']),(mode,style))
                self.assertEqual(state['settings'],initial['settings'])
                self.assertEqual(state['draft']['text'],'未送出的草稿')
        self.assertEqual(self.session.store.tasks(),[])
        self.assertEqual(self.session.store.schedules(),[])
        self.assertEqual(WebBridge(self.session).call('state')['data']['color_style'],'forest')
        self.call('appearance',dict(theme='dark',color_style='ocean'))
        self.assertTrue(load_preferences(self.session.preferences_path)['sidebar_collapsed'])
        self.assertEqual(load_color_style(self.session.preferences_path),'ocean')

    def test_invalid_choice_is_rejected_without_changing_preferences(self):
        self.call('appearance',dict(theme='light',color_style='forest'))
        before=self.session.preferences_path.read_bytes()
        for payload in ({'color_style':'arbitrary.css'},{'theme':'auto'},{'color_style':[]},{'url':'https://invalid.test'}):
            self.assertFalse(self.api.call('appearance',payload)['ok'])
            self.assertEqual(self.session.preferences_path.read_bytes(),before)
        self.assertEqual(self.call('state')['color_style'],'forest')

    def test_save_failure_keeps_session_style_and_reports_retry_truthfully(self):
        self.call('appearance',dict(theme='dark',color_style='ocean'))
        with patch('desktop_app.web_bridge.save_appearance',side_effect=OSError('PRIVATE_PATH')):
            value=self.call('appearance',{'color_style':'violet'})
            self.assertFalse(value['saved'])
            self.assertNotIn('PRIVATE_PATH',json.dumps(value))
            self.assertEqual(self.call('state')['color_style'],'violet')
            self.assertFalse(self.call('state')['appearance_saved'])
        self.assertEqual(load_color_style(self.session.preferences_path),'ocean')
        self.assertTrue(self.call('appearance',{'color_style':'violet'})['saved'])
        self.assertEqual(load_color_style(self.session.preferences_path),'violet')

    def test_legacy_theme_toggle_preserves_selected_style(self):
        self.call('appearance',{'color_style':'violet'})
        self.call('theme',{'name':'light'})
        self.assertEqual(self.call('state')['color_style'],'violet')

