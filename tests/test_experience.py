"""Inline guidance and offline help with real local workflow coverage."""
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
from desktop_app.experience import ExperienceMixin, manual_sections
from desktop_app.guidance import CHAPTERS, work_hint
from desktop_app.preferences import load_page_hints, save_page_hint, load_theme, save_theme
from desktop_app.ui import App


class GuidanceDataTests(TestCase):
    def test_preferences_preserve_legacy_theme_and_unknown_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'ui-preferences.json';legacy={'version':1,'status':'invited'}
            path.write_text(json.dumps({'theme':'light','onboarding':legacy,'future':12}),encoding='utf-8')
            self.assertTrue(all(load_page_hints(path).values()))
            save_page_hint(path,'chat',False);save_theme(path,'dark');save_page_hint(path,'query',False)
            self.assertFalse(load_page_hints(path)['chat']);self.assertFalse(load_page_hints(path)['query'])
            self.assertTrue(load_page_hints(path)['work']);self.assertEqual(load_theme(path),'dark')
            self.assertEqual(json.loads(path.read_text())['future'],12)
            self.assertEqual(json.loads(path.read_text())['onboarding'],legacy)
            with patch('desktop_app.preferences.os.replace',side_effect=OSError('blocked')):
                with self.assertRaises(OSError):save_page_hint(path,'chat',True)
            self.assertFalse(load_page_hints(path)['chat'])
            for value in ('[]','{"page_hints":3}','{"page_hints":{"chat":"false","query":0}}','broken'):
                path.write_text(value,encoding='utf-8');self.assertTrue(all(load_page_hints(path).values()))
            with self.assertRaises(ValueError):save_page_hint(path,'unknown',True)
            with self.assertRaises(ValueError):save_page_hint(path,'chat','false')
    def test_manual_has_required_workflows_and_all_page_links(self):
        sections=dict(manual_sections())
        for title in (*CHAPTERS.values(),'快速開始','資料保存與金鑰'):self.assertIn(title,sections)
        text='\n'.join(sections.values())
        for word in ('Shift+Enter','不是真正 AI 分析','只存本機','不保證'):self.assertIn(word,text)
    def test_first_run_diagnostic_is_scoped_and_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            a=ExperienceMixin();a.directory=Path(temp);a.config_path=a.directory/'config.json'
            a.status=Mock();a.background=lambda work,done:done(work())
            with patch('desktop_app.experience.subprocess.run',return_value=Mock(returncode=0)) as run:
                a._help_diagnose();args,kwargs=run.call_args
                self.assertNotIn('--config',args[0]);self.assertNotIn('--company',args[0])
                self.assertEqual(kwargs['env']['UNITHELPER_DATA_DIR'],temp)
    def test_work_hints_distinguish_pending_success_failure_and_cancel(self):
        self.assertIn('尚未執行',work_hint('plan',{'state':'ready'}))
        self.assertIn('不能批准',work_hint('plan',{'state':'expired'}))
        for state,word in [('queued','排隊'),('running','執行'),('succeeded','已完成'),('failed','未完成'),('cancelled','取消')]:
            self.assertIn(word,work_hint('task',{'state':state}))
        self.assertIsNone(work_hint(None,None))


class GuidanceUITests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.directory=Path(self.temp.name)
        self.root=tk.Tk();self.root.withdraw();self.app=None
    def tearDown(self):
        if self.app is not None:self.app.close(force=True)
        else:self.root.destroy()
        self.app=None;self.root=None;gc.collect();self.temp.cleanup()
    def app_create(self):
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=self.directory)
        self.root.update();return self.app
    def wait_for(self,predicate):
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            self.root.update()
            if predicate():return
            time.sleep(.03)
        self.fail('Local workflow did not reach expected state')
    def select(self,page):
        self.app.book.select(self.app.tabs[page]);self.root.update();self.app.refresh_page_hint()
        return self.app.page_hint.cget('text')
    def assert_visible(self,button):
        self.assertTrue(button.winfo_ismapped());x,y=button.winfo_rootx(),button.winfo_rooty()
        right,bottom=x+button.winfo_width(),y+button.winfo_height();parent=button.master
        while parent is not None:
            self.assertGreaterEqual(x,parent.winfo_rootx());self.assertGreaterEqual(y,parent.winfo_rooty())
            self.assertLessEqual(right,parent.winfo_rootx()+parent.winfo_width())
            self.assertLessEqual(bottom,parent.winfo_rooty()+parent.winfo_height());parent=parent.master
    def test_startup_no_popup_process_or_service_request_and_offline_help(self):
        pref=self.directory/'ui-preferences.json';original='{"onboarding":{"version":1,"status":"invited"},"theme":"light"}'
        pref.write_text(original,encoding='utf-8')
        with patch('desktop_app.experience.subprocess.Popen',side_effect=AssertionError('no process')), patch('desktop_app.ui.CompanyAssistant',side_effect=AssertionError('no company')), patch('desktop_app.ui.OracleQueries',side_effect=AssertionError('no Oracle')):
            a=self.app_create();self.assertFalse(any(isinstance(w,tk.Toplevel) for w in self.root.winfo_children()))
            self.assertEqual(pref.read_text('utf-8'),original);self.assertEqual(a.store.tasks(),[]);self.assertEqual(a.store.plans(),[])
            for page,chapter in CHAPTERS.items():
                self.select(page);window=a.open_page_help();self.root.update()
                self.assertTrue(window.help_content.get('1.0','end').startswith(chapter+'\n'))
                self.assertEqual(str(window.help_content['state']),'disabled');window.destroy()
            window=a.show_help('對話與鍵盤')
            for name in ('light','dark'):
                a.change_theme(name);self.root.update();self.assertEqual(window.help_content.cget('background'),a.palette.SURFACE)
            window.destroy()
    def test_toggle_all_pages_preserves_draft_attachment_selection_no_dispatch(self):
        a=self.app_create();self.root.deiconify();self.root.geometry('1050x700');self.root.update()
        a.input.insert('end','保留草稿\n第二行');a.input.tag_add('sel','1.0','1.2');a.input.mark_set('insert','2.1')
        a.attachment={'name':'private.txt','text':'private contents','kind':'txt'}
        draft=a.input.get('1.0','end-1c');selection=tuple(map(str,a.input.tag_ranges('sel')))
        cursor=a.input.index('insert');original=len(a.store.conversations())
        for theme in ('dark','light'):
            a.change_theme(theme)
            for page in CHAPTERS:
                self.select(page);self.assertTrue(a.page_hint.cget('text'))
                self.assert_visible(a.hint_toggle);self.assert_visible(a.hint_manual)
                a.toggle_page_hint();self.root.update();self.assertFalse(a.page_hint.winfo_ismapped())
                self.assertTrue(a.mode_label.winfo_ismapped())
                a.toggle_page_hint();self.root.update();self.assertTrue(a.page_hint.winfo_ismapped())
        self.assertEqual(a.input.get('1.0','end-1c'),draft);self.assertEqual(tuple(map(str,a.input.tag_ranges('sel'))),selection)
        self.assertEqual(a.input.index('insert'),cursor);self.assertEqual(a.attachment['text'],'private contents')
        self.assertEqual(a.store.tasks(),[]);self.assertEqual(a.store.plans(),[])
        self.assertEqual(len(a.store.conversations()),original);self.assertEqual(a.store.messages(a.conversation),[])
        self.assertFalse((self.directory/'config.json').exists())
    def test_preference_restart_and_failed_save_keep_current_toggle(self):
        a=self.app_create();self.select('chat');a.toggle_page_hint();self.select('query');self.assertTrue(a.page_hints['query'])
        a.close(force=True);self.app=None;self.root=None;del a;gc.collect()
        self.root=tk.Tk();self.root.withdraw();a=self.app_create()
        self.assertFalse(a.page_hints['chat']);self.assertTrue(a.page_hints['query'])
        with patch('desktop_app.guidance.save_page_hint',side_effect=OSError('blocked')):
            self.select('query');a.toggle_page_hint()
        self.assertFalse(a.page_hints['query']);self.assertFalse(a.page_hint.winfo_manager())
        self.assertIn('無法保存',a.status.get());self.assertTrue(load_page_hints(a.preferences_path)['query'])
    def test_current_conversation_plan_and_query_validation_hints_are_scoped(self):
        a=self.app_create();a.plan_mode.set(True);a.input.insert('end','待批准內容');a.send_chat()
        plan=a.store.plans()[0];before=copy.deepcopy(plan)
        self.assertIn('尚未執行',self.select('chat'));a.new_chat();self.assertNotIn('尚未執行',self.select('chat'))
        self.assertEqual(a.store.plan(plan['id']),before);self.assertEqual(a.store.tasks(),[])
        self.select('query');a.from_date.set('not-a-date');a.validate_query_fields();a.refresh_page_hint()
        self.assertIn('尚未就緒',a.page_hint.cget('text'))
        a.from_date.set('2026-01-01');a.to_date.set('2026-01-04');a.validate_query_fields()
        a.query_plan.set(True);a.refresh_page_hint();self.assertIn('批准',a.page_hint.cget('text'))
        self.assertEqual(a.store.tasks(),[])
        pid=a.profiles.save('公司助理','unmapped');a.profiles.set_endpoint('https://company.invalid/v1')
        a.next_binding=a.profiles.snapshot(pid);a.new_chat()
        self.assertIn('請求格式',self.select('chat'));self.assertIn('格式仍待確認',self.select('settings'))
    def test_normal_demo_query_approval_selection_and_transfer(self):
        with patch('desktop_app.ui.CompanyAssistant',side_effect=AssertionError('network forbidden')), patch('desktop_app.ui.OracleQueries',side_effect=AssertionError('database forbidden')):
            a=self.app_create();self.root.deiconify();self.root.geometry('1050x700')
            a.query_id.set('DEMO01');a.render_query_fields({'from_date':'2026-01-01','to_date':'2026-01-04','category':'all'})
            a.query_plan.set(True);self.select('query');self.assert_visible(a.query_submit)
            a.submit_query();self.root.update();plan=a.store.plans()[0];before=copy.deepcopy(plan)
            a.toggle_page_hint();a.toggle_page_hint();self.root.update()
            self.assertEqual(a.store.plan(plan['id']),before);self.assertEqual(a.store.tasks(),[])
            a.approve_plan();tid=a.store.plan(plan['id'])['task_id'];self.wait_for(lambda:a.store.task(tid)['state']=='succeeded')
            a.show_result(tid);self.root.update();children=a.table.get_children();self.assertTrue(children)
            a.table.selection_set(children[0]);a.refresh_page_hint();self.assertIn('已選取 1 列',a.page_hint.cget('text'))
            for _ in range(2):a.toggle_page_hint();self.root.update()
            self.assertEqual(a.table.selection(),(children[0],));self.assert_visible(a.handoff_button)
            a.open_result_handoff();self.root.update();dialog=a.handoff_window;self.assertEqual(len(a.store.tasks()),1)
            dialog.transfer_submit();self.wait_for(lambda:len(a.store.tasks())==2 and a.store.tasks()[0]['state']=='succeeded')
            self.assertTrue(a.store.conversation(a.conversation)['source']['rows']);self.assertEqual(a.store.schedules(),[])
            self.assertFalse((self.directory/'config.json').exists())
            a.refresh_lists();self.select('work');a.tasks.selection_set(tid);self.root.update();self.assertIn('已完成',a.page_hint.cget('text'))

    def test_editing_context_expiry_and_plan_terminal_states(self):
        a=self.app_create();a.query_plan.set(True);a.submit_query();self.root.update()
        query=a.store.plans()[0];a.edit_plan()
        self.assertIn('修改查詢計畫',self.select('query'))
        self.assertIn('另一項計畫',self.select('chat'))
        a.discard_edit();a.plan_mode.set(True);a.input.insert('end','文字計畫');a.send_chat();self.root.update()
        plan=a.store.plans()[0];a.edit_plan()
        self.assertIn('此對話',self.select('chat'));self.assertIn('另一項計畫',self.select('query'))
        with a.store.connection() as db:
            db.execute("UPDATE plans SET expires_at=? WHERE id=?",('2000-01-01T00:00:00+00:00',plan['id']))
        self.assertIn('已失效',self.select('chat'));a.discard_edit()
        self.select('work');a.plans.selection_set(plan['id']);a.select_hint_work('plan')
        self.assertIn('已過期',a.page_hint.cget('text'))
        self.assertEqual(a.store.plan(plan['id'])['state'],'ready');self.assertEqual(a.store.tasks(),[])
        a.plans.selection_set(query['id']);a.preview_selected_plan();a.approve_plan()
        tid=a.store.plan(query['id'])['task_id'];self.wait_for(lambda:a.store.task(tid)['state']=='succeeded')
        a.select_hint_work('plan');self.assertIn('不需再次批准',a.page_hint.cget('text'))
        self.assertIn('失敗原因',work_hint('plan',{'state':'failed'}))

    def test_schedule_result_notice_and_issue_hints_only_read_current_state(self):
        a=self.app_create();tid=a.engine.run_query('DEMO01',{'from_date':'2026-01-01','to_date':'2026-01-04','category':'all'})
        self.wait_for(lambda:a.store.task(tid)['state']=='succeeded');a.show_result(tid)
        snapshot=copy.deepcopy(a.store.task(tid)['result'])
        sid=a.engine.create_schedule(tid,'合成查詢','daily','09:00',0,'nonempty_on_change',None)
        a.refresh_lists();a.schedules.selection_set(sid)
        self.assertIn('停用',self.select('schedule'))
        a.engine.set_schedule_enabled(sid,True);self.assertIn('已啟用',self.select('schedule'))
        a.engine.set_schedule_enabled(sid,False)
        self.assertIn('沒有通知',self.select('notice'))
        with patch.object(a.store,'notifications',return_value=[{'task_id':None}]):
            self.assertIn('有結果時',a.page_hint_content('notice'))
        a.issue_title.set('合成回報');a.issue_description.insert('end','步驟');a.issue_expected.insert('end','預期')
        a.save_issue(False);self.assertIn('已保存',self.select('issue'))
        self.assertEqual(a.store.task(tid)['result'],snapshot);self.assertEqual(len(a.store.tasks()),1)
