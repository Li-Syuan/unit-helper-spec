"""Native navigation/team journeys. No external services or fabricated verification."""
import copy
import gc
import tempfile
import tkinter as tk
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch
from desktop_app.config import DEFAULT
from desktop_app.preferences import load_preferences
from desktop_app.ui import App


class TeamNavigationTests(unittest.TestCase):
    def test_closed_app_releases_interpreter_and_missing_icons_remain_usable(self):
        a=self.app;a.ui_images.pop(('team',a.appearance.name),None)
        a.navigation.toggle_sidebar();self.assertEqual(a.nav_buttons['team'].cget('text'),'助理')
        self.assertEqual(a.navigation.toggle._nav_title,'展開側欄')
        app_ref=weakref.ref(a);root_ref=weakref.ref(self.root)
        a.close(force=True);self.app=None;self.root=None;del a;gc.collect()
        self.assertIsNone(app_ref());self.assertIsNone(root_ref())
        self.root=tk.Tk();self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.tmp.name))

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=tk.Tk();self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.tmp.name));self.root.update()
    def tearDown(self):
        self.app.close(force=True);self.app=None;self.root=None;gc.collect();self.tmp.cleanup()

    def add(self,name='品質分析',id_='synthetic-analysis'):
        pid=self.app.profiles.save(name,id_,'合成用途：分析品質數據')
        self.app.refresh_profiles();self.root.update();return pid

    def test_all_routes_have_icons_and_no_navigation_dispatch(self):
        a=self.app
        with patch.object(a.profiles,'respond',side_effect=AssertionError('no dispatch')):
            for key,button in a.nav_buttons.items():
                self.assertTrue(button.cget('image'),key)
                button.invoke();self.root.update();self.assertEqual(a.book.select(),str(a.tabs[key]))
                a.open_page_help=lambda:None
        self.assertEqual(a.store.tasks(),[])

    def test_collapse_keeps_widgets_drafts_selection_and_attachment(self):
        a=self.app;a.input.insert('1.0','保留這份草稿');a.input.tag_add('sel','1.0','1.2')
        a.attachment={'name':'test.txt','text':'synthetic'}
        before=(str(a.input),a.input.get('1.0','end-1c'),a.input.tag_ranges('sel'),a.attachment.copy())
        for _ in range(2):a.navigation.toggle_sidebar();self.root.update()
        self.assertEqual(before,(str(a.input),a.input.get('1.0','end-1c'),a.input.tag_ranges('sel'),a.attachment))
        self.assertFalse(load_preferences(a.preferences_path)['sidebar_collapsed'])
        self.assertEqual(a.store.tasks(),[])

    def test_collapsed_persistence_and_failed_save_keeps_current_view(self):
        a=self.app;a.navigation.toggle_sidebar()
        self.assertTrue(load_preferences(a.preferences_path)['sidebar_collapsed'])
        with patch('desktop_app.navigation.update_preferences',side_effect=OSError('locked')):a.navigation.toggle_sidebar()
        self.assertFalse(a.navigation.collapsed);self.assertIn('保存失敗',a.status.get())
        a.close(force=True);self.root=tk.Tk();self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.tmp.name));self.root.update()
        self.assertTrue(self.app.navigation.collapsed)
        self.assertEqual(self.app.nav_buttons['chat'].cget('text'),'')

    def test_more_tools_is_reachable_from_compact_and_theme_preserves_it(self):
        a=self.app;a.navigation.toggle_sidebar();a.toggle_more_tools();self.root.update()
        self.assertFalse(a.navigation.collapsed);self.assertTrue(a.more_tools.winfo_manager())
        a.navigation.toggle_sidebar();a.change_theme('light');self.root.update()
        self.assertTrue(a.navigation.collapsed)
        self.assertTrue(a.nav_buttons['team'].cget('image'))

    def test_team_search_and_status_never_fabricate_verification(self):
        a=self.app;pid=self.add();a.book.select(a.tabs['team']);self.root.update()
        self.assertEqual(a.team_cards[pid]['state'],'待設定 API 格式')
        a.team_search.set('不存在');self.assertEqual(a.team_cards,{})
        a.team_search.set('品質');self.assertEqual(list(a.team_cards),[pid])
        a.team_filter.set('可參與分工');a.refresh_team();self.assertEqual(a.team_cards,{})
        self.assertEqual(a.profiles.workflow_catalog(),[]);self.assertEqual(a.store.tasks(),[])

    def test_team_chat_creates_new_bound_conversation_preserving_old_draft(self):
        a=self.app;pid=self.add();old=a.conversation;a.input.insert('1.0','之前的內容')
        a.team_chat(pid);self.root.update()
        self.assertNotEqual(old,a.conversation)
        self.assertEqual(a.store.conversation(a.conversation)['binding']['profile_id'],pid)
        self.assertEqual(a.input.get('1.0','end-1c'),'')
        self.assertEqual(a.store.tasks(),[])

    def test_verified_planner_entry_is_explicit_and_never_runs(self):
        a=self.app;pid=self.add('合成規劃助理')
        with self.assertRaises(ValueError):a.team_plan(pid)
        a.profiles.set_workflow_capability(pid,['planner'],verified=True,evidence='synthetic-test-only')
        a.team_plan(pid);self.root.update()
        self.assertEqual(a.workflow_mode.get(),'workflow')
        self.assertEqual(a.workflow_planners[a.workflow_planner.current()]['id'],pid)
        self.assertEqual(a.workflows.list(a.conversation),[]);self.assertEqual(a.store.tasks(),[])

    def test_details_and_edit_reuse_existing_profile_actions(self):
        a=self.app;pid=self.add();w=a.team_details(pid);self.root.update()
        def children(w):
            for c in w.winfo_children():yield c;yield from children(c)
        edit=next(c for c in children(w) if 'text' in c.keys() and c.cget('text')=='編輯名稱、ID、用途與金鑰')
        with patch.object(a,'edit_profile') as call:edit.invoke();call.assert_called_once_with(pid)
        self.assertEqual(a.profile_table.selection(),(pid,))

    def test_responsive_cards_and_theme(self):
        a=self.app;self.add();self.add('覆核','synthetic-review');a.book.select(a.tabs['team'])
        for size in ('1050x700','1500x900'):
            self.root.geometry(size);self.root.deiconify();self.root.update()
            for theme in ('dark','light'):
                a.change_theme(theme);self.root.update()
                self.assertTrue(a.team_cards)
                for parts in a.team_cards.values():
                    self.assertTrue(parts['chat'].winfo_ismapped())
                    self.assertLessEqual(parts['chat'].winfo_rootx()+parts['chat'].winfo_width(),a.team_body.winfo_rootx()+a.team_body.winfo_width()+2)
        self.assertEqual(a.team_columns,2)
