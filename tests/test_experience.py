import copy
import gc
import json
from pathlib import Path
import tempfile
import time
import tkinter as tk
from unittest import TestCase
from unittest.mock import patch, Mock

from desktop_app.config import DEFAULT
from desktop_app.experience import ExperienceMixin, TutorialProgress, manual_sections
from desktop_app.preferences import load_onboarding, save_onboarding, load_theme, save_theme
from desktop_app.ui import App


class ExperienceDataTests(TestCase):
    def test_preferences_preserve_theme_and_unknown_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'ui-preferences.json'
            path.write_text('{"theme":"light","future":12}',encoding='utf-8')
            save_onboarding(path,'completed');save_theme(path,'dark')
            self.assertEqual(load_onboarding(path),'completed')
            self.assertEqual(load_theme(path),'dark')
            self.assertEqual(json.loads(path.read_text())['future'],12)
            with patch('desktop_app.preferences.os.replace',side_effect=OSError('blocked')):
                with self.assertRaises(OSError):save_onboarding(path,'skipped')
            self.assertEqual(load_onboarding(path),'completed')
            for value in ('[]','{"onboarding":3}','{"onboarding":{"version":999,"status":"completed"}}','broken'):
                path.write_text(value,encoding='utf-8');self.assertEqual(load_onboarding(path),'new')

    def test_manual_has_required_workflows(self):
        sections=dict(manual_sections())
        for title in ('快速開始','設定公司助理','對話與鍵盤','Plan 與選項確認','將資料交給助理','資料保存與金鑰','關於'):
            if title!='關於':self.assertIn(title,sections)
        text='\n'.join(sections.values())
        self.assertIn('Shift+Enter',text);self.assertIn('不是真正 AI 分析',text)
        self.assertIn('只存本機',text);self.assertIn('不保證',text)

    def test_first_run_diagnostic_and_completed_marker_are_scoped(self):
        with tempfile.TemporaryDirectory() as temp:
            a=ExperienceMixin();a.directory=Path(temp);a.config_path=a.directory/'config.json'
            a.preferences_path=a.directory/'ui-preferences.json';a.status=Mock()
            a.background=lambda work,done:done(work())
            with patch('desktop_app.experience.subprocess.run',return_value=Mock(returncode=0)) as run:
                a._help_diagnose()
                args,kwargs=run.call_args
                self.assertNotIn('--config',args[0])
                self.assertEqual(kwargs['env']['UNITHELPER_DATA_DIR'],temp)
                self.assertNotIn('--company',args[0])
            marker=a.directory/'marker.json';marker.write_text('{"completed":true,"settings":false}',encoding='utf-8')
            a._experience_processes=[(Mock(poll=lambda:0),marker)];a.root=Mock();a.closed=False
            a._poll_experiences()
            self.assertEqual(load_onboarding(a.preferences_path),'completed');self.assertFalse(marker.exists())

    def test_progress_cannot_skip_approval_selection_or_success(self):
        p=TutorialProgress();p.filled()
        plan={'id':'p','kind':'query','state':'ready','task_id':None}
        self.assertEqual(p.observe([plan],[],None,[],[]),3)
        self.assertEqual(p.observe([plan],[],None,[],[]),3)
        plan.update(state='succeeded',task_id='t')
        task={'id':'t','kind':'query','state':'succeeded','conversation_id':None}
        self.assertEqual(p.observe([plan],[task],'t',[],[]),4)
        self.assertEqual(p.observe([plan],[task],'other',['0'],[]),4)
        self.assertEqual(p.observe([plan],[task],'t',['0'],[]),5)
        convo={'id':'c','source':{'kind':'query','task_id':'t'}}
        transfer={'id':'s','kind':'summarize','state':'failed','conversation_id':'c'}
        self.assertEqual(p.observe([plan],[task,transfer],'t',['0'],[convo]),5)
        transfer['state']='succeeded'
        self.assertEqual(p.observe([plan],[task,transfer],'t',['0'],[convo]),6)


class ExperienceUITests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.directory=Path(self.temp.name)
        self.root=tk.Tk();self.root.withdraw();self.app=None
    def tearDown(self):
        if self.app is not None:self.app.close(force=True)
        else:self.root.destroy()
        self.app=None;self.root=None;gc.collect();self.temp.cleanup()
    def app_create(self,tutorial=False):
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=self.directory,tutorial=tutorial,show_welcome=False)
        self.root.update();return self.app
    def wait_for(self,predicate):
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            self.root.update()
            if predicate():return
            time.sleep(.03)
        self.fail('Real tutorial workflow did not reach expected state')
    def test_welcome_skip_and_offline_help_themes(self):
        a=self.app_create();window=a.show_welcome();self.root.update()
        close_cmd=window.protocol('WM_DELETE_WINDOW');window.tk.call(close_cmd)
        self.assertEqual(load_onboarding(a.preferences_path),'skipped')
        help_window=a.show_help('對話與鍵盤');self.root.update()
        self.assertIn('Shift+Enter',help_window.help_content.get('1.0','end'))
        for name in ('light','dark'):
            a.change_theme(name);self.root.geometry('1050x700');self.root.update()
            self.assertEqual(help_window.help_content.cget('background'),a.palette.SURFACE)
        help_window.destroy()
    def test_isolated_demo_entire_five_step_workflow(self):
        with patch('desktop_app.ui.CompanyAssistant',side_effect=AssertionError('network forbidden')),patch('desktop_app.ui.OracleQueries',side_effect=AssertionError('database forbidden')):
            a=self.app_create(tutorial=True);c=a.tutorial_controller
            self.root.deiconify();self.root.geometry('1050x700');self.root.update()
            self.assertEqual(c.progress.step,1);c.fill();self.assertEqual(c.progress.step,2)
            self.root.update()
            self.assertLessEqual(c.panel.winfo_height(),85)
            # A mapped button can still be clipped by a packed ancestor.
            button=a.query_submit
            bx,by=button.winfo_rootx(),button.winfo_rooty()
            right,bottom=bx+button.winfo_width(),by+button.winfo_height()
            parent=button.master
            while parent is not None:
                self.assertGreaterEqual(bx,parent.winfo_rootx())
                self.assertGreaterEqual(by,parent.winfo_rooty())
                self.assertLessEqual(right,parent.winfo_rootx()+parent.winfo_width())
                self.assertLessEqual(bottom,parent.winfo_rooty()+parent.winfo_height())
                parent=parent.master
            self.assertLessEqual(bottom,c.panel.winfo_rooty())
            self.assertEqual(a.store.tasks(),[])
            a.submit_query();self.wait_for(lambda:c.progress.step==3)
            self.assertEqual(a.store.tasks(),[])
            a.approve_plan();self.wait_for(lambda:c.progress.step==4)
            self.wait_for(lambda:a.store.task(c.progress.task_id)['state']=='succeeded')
            c.act();self.root.update();children=a.table.get_children();self.assertTrue(children)
            a.table.selection_set(children[0]);self.wait_for(lambda:c.progress.step==5)
            c.act();self.root.update();dialog=a.handoff_window
            before=len(a.store.tasks());self.assertEqual(str(dialog.transfer_confirm['state']),'normal')
            self.assertEqual(len(a.store.tasks()),before)
            dialog.transfer_submit();self.wait_for(lambda:c.progress.step==6)
            self.assertTrue(c.completed)
            self.assertTrue(a.store.conversation(a.conversation)['source']['rows'])
            self.assertFalse((self.directory/'config.json').exists())
            self.assertEqual(a.store.schedules(),[])
            self.assertTrue(c.action.winfo_ismapped())
            with self.assertRaises(ValueError):a.apply_settings()
