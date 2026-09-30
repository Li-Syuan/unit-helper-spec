import copy
import tempfile
import threading
import time
import tkinter as tk
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from desktop_app.authentication import authenticate, LoginSession, AuthenticationError
from desktop_app.config import DEFAULT
from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge


def grant(subject='synthetic-a'):
    return dict(authenticated=True, allowed=True, subject=subject, employee_id='TEST001',
                name='合成測試帳號', expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())


class AuthenticationTests(unittest.TestCase):
    def test_strict_contract_denial_and_errors_without_secrets(self):
        secret='SYNTHETIC_PASSWORD_DO_NOT_LOG'
        for response in (True, {}, dict(grant(), allowed=False), dict(grant(), authenticated=1),
                         dict(grant(), expires_at='2099-01-01'), dict(grant(), subject='')):
            with self.subTest(response_type=type(response).__name__), self.assertRaises(AuthenticationError):
                authenticate('TEST001',secret,provider=lambda e,p: response)
        def fail(e,p):raise RuntimeError(secret+' https://private.invalid')
        with self.assertRaises(AuthenticationError) as error:authenticate('TEST001',secret,provider=fail)
        self.assertNotIn(secret,str(error.exception))
        with self.assertRaises(AuthenticationError):authenticate('TEST001',secret)
        session=authenticate('TEST001',secret,provider=lambda e,p: grant())
        self.assertEqual(session.current()['mode'],'company')
        self.assertNotIn(secret,repr(vars(session)))
        session.close()
        with self.assertRaises(AuthenticationError):session.current()

    def test_login_required_before_data_open_and_isolation(self):
        from desktop_app.ui import launch
        with patch('desktop_app.ui.load_config',side_effect=ValueError('PRIVATE')), patch('desktop_app.ui.tk.Tk') as window, patch('desktop_app.ui.messagebox.showerror') as message:
            self.assertFalse(launch())
            self.assertNotIn('PRIVATE',str(message.call_args))
            window.return_value.destroy.assert_called_once()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'untouched'
            config=copy.deepcopy(DEFAULT);config['identity_mode']='company'
            with self.assertRaises(ValueError):WebSession(directory=root,config=config)
            self.assertFalse(root.exists())
            first=WebSession(directory=root,config=config,login_session=LoginSession(grant()))
            cid=first.store.create_conversation('只屬於A',first.profiles.default_binding())
            first.close()
            second=WebSession(directory=root,config=config,login_session=LoginSession(grant('synthetic-b')))
            self.assertEqual(second.store.conversations(),[])
            self.assertNotEqual(first.directory,second.directory)
            second.close()
            reopened=WebSession(directory=root,config=config,login_session=LoginSession(grant()))
            self.assertEqual(reopened.store.conversation(cid)['title'],'只屬於A')
            reopened.close()
            self.assertFalse((root/'local-v1.sqlite3').exists())

    def test_expired_identity_blocks_dispatch_bridge_and_schedule(self):
        with tempfile.TemporaryDirectory() as folder:
            clock=[0.0]
            identity=LoginSession(grant(),clock=lambda:clock[0])
            config=copy.deepcopy(DEFAULT);config['identity_mode']='company'
            session=WebSession(directory=folder,config=config,login_session=identity)
            try:
                binding=session.profiles.default_binding()
                clock[0]=40000
                api=WebBridge(session)
                self.assertFalse(api.call('new_chat')['ok'])
                with self.assertRaises(AuthenticationError):session.engine.tick()
                with self.assertRaises(AuthenticationError):session.queries.run('DEMO01',{})
                with self.assertRaises(AuthenticationError):session.profiles.respond([{'role':'user','content':'不派發'}],'chat',binding)
                self.assertEqual(session.store.tasks(),[])
            finally:session.close()


class LoginViewTests(unittest.TestCase):
    def pump(self, root, predicate):
        deadline=time.monotonic()+3
        while not predicate() and time.monotonic()<deadline:
            root.update();time.sleep(.01)
        self.assertTrue(predicate())

    def test_preview_themes_do_not_call_auth_or_open_data(self):
        from desktop_app.login_view import LoginView
        with tempfile.TemporaryDirectory() as folder, patch('desktop_app.about.publisher_info',return_value=dict(employee_id='尚未設定',name='尚未設定',phone='尚未設定')):
            root=tk.Tk()
            try:
                with patch('desktop_app.login_view.authenticate') as auth:
                    view=LoginView(root,Path(folder),preview=True)
                    root.update()
                    view.employee.set('TEST001');view.password.set('synthetic')
                    view.submit()
                    self.assertEqual(view.password.get(),'')
                    self.assertIsNone(view.result);auth.assert_not_called()
                    view.appearance.configure('light')
                    root.update()
                    self.assertTrue(view.submit_button.winfo_ismapped())
                    view.cancel()
                    self.assertFalse(list(Path(folder).glob('*.sqlite3')))
            finally:root.destroy()

    def test_double_click_and_cancel_discards_late_login(self):
        from desktop_app.login_view import LoginView
        release=threading.Event();entered=threading.Event();calls=[]
        def provider(employee,password):
            calls.append((employee,password));entered.set();release.wait(3);return grant()
        with tempfile.TemporaryDirectory() as folder, patch('desktop_app.about.publisher_info',return_value=dict(employee_id='尚未設定',name='尚未設定',phone='尚未設定')):
            root=tk.Tk()
            try:
                view=LoginView(root,Path(folder),provider=provider)
                view.employee.set('TEST001');view.password.set('synthetic')
                view.submit();view.submit()
                self.assertTrue(entered.wait(1));self.assertEqual(view.password.get(),'')
                view.cancel();release.set()
                self.pump(root,lambda:not view.pending)
                self.assertIsNone(view.result);self.assertEqual(len(calls),1)
            finally:
                release.set();root.destroy()
