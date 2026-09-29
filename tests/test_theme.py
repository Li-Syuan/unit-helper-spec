"""Real Tk appearance checks; company GUI/Excel acceptance remains separate."""
import copy
import gc
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from unittest import TestCase
from unittest.mock import patch

from desktop_app.config import DEFAULT
from desktop_app.preferences import load_color_style
from desktop_app.theme import Appearance
from desktop_app.ui import App, ChoiceDialog


class ThemeTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.directory=Path(self.temp.name)
        self.root=tk.Tk(); self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=self.directory)
        self.root.update()

    def tearDown(self):
        self.root.update_idletasks(); self.app.close(force=True); self.app=None; self.root=None; gc.collect()
        self.temp.cleanup()

    def test_switch_preserves_widgets_draft_attachment_selection_and_plan(self):
        a=self.app; self.root.deiconify(); self.root.update()
        a.query_plan.set(True); a.submit_query(); plan=a.store.plans()[0]
        a.input.insert('1.0','保留原文\n'*100); a.input.mark_set('insert','5.2')
        a.input.tag_add('sel','3.0','4.2'); a.input.yview_moveto(.5)
        a.attachment={'name':'draft.txt','text':'untouched','kind':'txt'}
        a.book.select(a.tabs['chat']); self.root.update()
        before=(str(a.input),a.input.get('1.0','end'),a.input.index('insert'),a.input.tag_ranges('sel'),a.input.yview(),a.history.curselection(),a.attachment,a.store.plan(plan['id']))
        config=copy.deepcopy(a.config)
        form=a.forms.create([{'id':'q','title':'確認？','type':'yes_no',
            'options':[{'id':'yes','label':'是'},{'id':'no','label':'否'}]}])
        dialog=ChoiceDialog(a,form,lambda _:None)
        dialog.variables['q'].set('yes')
        for name, color_style in ((mode, style) for mode in ('light','dark')
                                  for style in ('violet','forest','ocean')):
            if a.appearance.name != name:
                a.change_theme(name)
            a.change_color_style(color_style)
            self.assertEqual(a.appearance.color_style,color_style)
            self.assertEqual(dialog.variables['q'].get(),'yes')
            self.assertEqual(dialog.cget('background'),a.palette.BG)
            self.assertEqual(a.style.lookup('NotificationBadge.TLabel','foreground'),a.palette.INFO)
            self.assertEqual(load_color_style(a.preferences_path),color_style)
            after=(str(a.input),a.input.get('1.0','end'),a.input.index('insert'),a.input.tag_ranges('sel'),a.input.yview(),a.history.curselection(),a.attachment,a.store.plan(plan['id']))
            self.assertEqual(before,after)
            self.assertEqual(a.input.cget('background'),a.palette.SURFACE)
            self.assertEqual(a.config,config); self.assertFalse(Path(a.config_path).exists())
            self.assertEqual(a.store.tasks(),[])
        dialog.destroy()

    def test_existing_and_future_dialogs_popup_and_all_pages(self):
        a=self.app
        form=a.forms.create([{'id':'q','title':'確認？','type':'yes_no','options':[{'id':'yes','label':'是'},{'id':'no','label':'否'}]}])
        dialog=ChoiceDialog(a,form,lambda _:None); dialog.variables['q'].set('yes')
        for name in ('light','dark'):
            a.change_theme(name)
            self.assertEqual(dialog.cget('background'),a.palette.BG)
            self.assertEqual(dialog.variables['q'].get(),'yes')
            self.assertEqual(a.table.tag_configure('odd')['background'],a.palette.STRIPE)
            self.assertEqual(a.transcript.tag_cget('speaker_user','foreground'),a.palette.ACCENT)
            for orientation in ('Vertical','Horizontal'):
                style=orientation+'.TScrollbar'
                self.assertEqual(a.style.lookup(style,'lightcolor'),a.palette.BORDER)
                self.assertEqual(a.style.lookup(style,'darkcolor'),a.palette.BORDER)
                self.assertEqual(a.style.lookup(style,'troughcolor'),a.palette.BG)
                self.assertEqual(a.style.lookup(style,'arrowcolor'),a.palette.MUTED)
            popup=a.query_picker.tk.call('ttk::combobox::PopdownWindow',str(a.query_picker))
            self.assertEqual(a.root.tk.call(str(popup)+'.f.l','cget','-background'),a.palette.SURFACE)
            for tab in a.tabs.values():
                a.book.select(tab); self.root.update()
                self.assertEqual(a.style.lookup('TFrame','background'),a.palette.BG)
        dialog.destroy()
        future=ChoiceDialog(a,form,lambda _:None)
        self.assertEqual(future.cget('background'),a.palette.BG); future.destroy()
        a.preview_upload({'name':'local.txt','preview':'原文','kind':'txt','text':'原文'})
        upload=next(w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel))
        a.change_theme('light')
        text=next(w for w in upload.winfo_children() if isinstance(w,tk.Text))
        self.assertEqual(text.cget('background'),a.palette.SURFACE)
        self.assertEqual(text.get('1.0','end-1c'),'原文'); upload.destroy()

    def test_switch_while_work_is_running_does_not_dispatch_or_cancel(self):
        a=self.app; entered=threading.Event(); release=threading.Event(); calls=[]
        def respond(messages,purpose):
            calls.append(messages); entered.set(); release.wait(5); return 'finished'
        a.engine.assistant_router=lambda messages,purpose,binding:respond(messages,purpose); a.input.insert('end','工作'); a.send_chat()
        self.assertTrue(entered.wait(2))
        try:
            task=a.store.tasks()[0]; a.change_theme('light'); a.change_theme('dark')
            self.assertTrue(a.engine.has_inflight())
            self.assertEqual(a.store.task(task['id'])['state'],'running')
            self.assertEqual(len(calls),1); self.assertEqual(len(a.store.tasks()),1)
        finally: release.set()

    def test_save_failure_remains_applied_and_restart_preference(self):
        a=self.app
        a.change_theme('light')
        with patch('desktop_app.ui.save_appearance',side_effect=OSError('denied')), patch('desktop_app.ui.messagebox.showwarning') as notice:
            a.change_theme('dark')
        self.assertEqual(a.appearance.name,'dark'); self.assertEqual(a.input.cget('background'),a.palette.SURFACE)
        self.assertIn('無法保存',a.status.get()); notice.assert_called_once()
        self.root.update_idletasks(); a.close(force=True); self.app=None; self.root=None; del a; gc.collect()
        self.root=tk.Tk(); self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=self.directory)
        self.assertEqual(self.app.appearance.name,'light')

    def test_minimum_size_actions_fit_both_themes(self):
        a=self.app; self.root.deiconify(); self.root.geometry('1050x700')
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        for name in ('light','dark'):
            a.change_theme(name)
            for page in a.tabs.values():
                a.book.select(page); self.root.update()
                bottom=page.winfo_rooty()+page.winfo_height(); right=page.winfo_rootx()+page.winfo_width()
                for widget in descendants(page):
                    if isinstance(widget,ttk.Button):
                        if widget is a.draft_retry or (page is a.tabs['todo'] and not widget.winfo_ismapped()):
                            continue  # Conditional retry and inactive narrow-board columns.
                        if page is a.tabs['chat'] and not widget.winfo_ismapped() and (str(widget).startswith(str(a.action_panel))
                                or str(widget).startswith(str(a.more_options)) or str(widget).startswith(str(a.task_card))
                                or str(widget).startswith(str(a.work_toolbar))
                                or str(widget).startswith(str(a.workflow_panel))
                                or widget in (a.selection_todo,a.selection_handoff,a.cancel_button,a.remove_upload_button)):
                            continue  # Explicitly conditional controls have focused action-journey coverage.
                        self.assertTrue(widget.winfo_ismapped())
                        self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),bottom+2,widget.cget('text'))
                        self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),right+2,widget.cget('text'))


class PaletteInterpreterTests(TestCase):
    """Style interpreter isolation needs two Tk roots, not a full App/database."""
    def test_palette_isolation_between_tk_interpreters(self):
        root=tk.Tk(); root.withdraw()
        other=tk.Tk(); other.withdraw()
        try:
            first=Appearance(root,'dark'); second=Appearance(other,'light')
            light=second.colors.BG
            first.configure('dark')
            self.assertEqual(second.style.lookup('TFrame','background'),light)
            second.configure('dark'); first.configure('light')
            self.assertNotEqual(second.style.lookup('TFrame','background'),first.style.lookup('TFrame','background'))
        finally:
            other.update_idletasks(); other.destroy()
            root.update_idletasks(); root.destroy()
