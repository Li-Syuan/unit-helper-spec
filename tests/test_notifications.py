"""Real Tk notification presentation, using only temporary synthetic data."""
import copy
import gc
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from desktop_app.config import DEFAULT
from desktop_app.core import uid, stamp
from desktop_app.display import work_area
from desktop_app.notifications import NotificationPresenter
from desktop_app.ui import App


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=tk.Tk();self.root.withdraw()
        self.app=App(self.root,config=copy.deepcopy(DEFAULT),directory=Path(self.tmp.name))
        self.p=self.app.notification_presenter
        self.root.update()

    def tearDown(self):
        self.app.close(force=True)
        deadline=time.monotonic()+5
        while not self.app.lock.handle.closed and time.monotonic()<deadline:time.sleep(.01)
        self.app=None;self.p=None;self.root=None;gc.collect();self.tmp.cleanup()

    def add(self,text='合成日報已完成',task=None,read=False):
        nid=uid()
        with self.app.store.connection() as db:
            db.execute('INSERT INTO notifications VALUES(?,?,?,?,?,?)',(nid,nid,task,text,int(read),stamp()))
        return nid

    def refresh(self):
        self.app.refresh_lists();self.root.update()

    def test_corner_popup_unread_badge_and_repeat_refresh(self):
        self.app.input.insert('1.0','未送出的草稿')
        nid=self.add();self.refresh();w=self.p.toast
        self.assertIsNotNone(w);self.assertIsNone(self.root.grab_current())
        self.assertEqual(self.p.badge.cget('text'),'1 未讀')
        self.assertEqual(self.p.badge.winfo_manager(),'place')
        self.assertEqual(self.app.nav_buttons['notice'].winfo_parent(),str(self.app.nav_buttons['chat'].master))
        x,y,width,height=work_area(self.root);margin=self.app.display.px(16)
        self.assertAlmostEqual(w.winfo_x()+w.winfo_width(),x+width-margin,delta=2)
        self.assertAlmostEqual(w.winfo_y()+w.winfo_height(),y+height-margin,delta=2)
        self.assertGreater(w.winfo_height(),100)
        self.assertLessEqual(self.p.view_button.winfo_rooty()+self.p.view_button.winfo_height(),w.winfo_rooty()+w.winfo_height())
        self.refresh();self.assertIs(w,self.p.toast)
        self.assertEqual(self.app.input.get('1.0','end-1c'),'未送出的草稿')
        self.assertEqual(self.app.notices.item(nid,'tags'),('unread_notice',))
        self.app.toggle_more_tools();self.root.update()
        siblings=self.app.nav_buttons['notice'].master.pack_slaves()
        self.assertLess(siblings.index(self.app.nav_buttons['notice']),siblings.index(self.app.more_tools))
        self.assertTrue(self.p.badge.winfo_ismapped())

    def test_dismiss_retains_unread_without_redisplay(self):
        self.add();self.refresh();self.p.close_button.invoke();self.refresh()
        self.assertIsNone(self.p.toast);self.assertIsNone(self.p.timer)
        self.assertEqual(self.p.badge_count,1)
        self.assertFalse(self.app.store.notifications()[0]['is_read'])

    def test_unread_is_informational_and_cancelled_is_neutral(self):
        with self.app.store.connection() as db:
            tid,_=self.app.engine._new_task(db,'query',{})
            db.execute("UPDATE tasks SET state='cancelled' WHERE id=?",(tid,))
        self.add('工作已取消',task=tid);self.refresh()
        self.assertEqual(self.p.symbol.cget('text'),'—')
        self.assertEqual(self.p.symbol.cget('style'),'Neutral.ToastMark.TLabel')
        for theme in ('light','dark'):
            self.app.change_theme(theme);self.root.update()
            style=self.app.appearance.style
            self.assertEqual(style.lookup('NotificationBadge.TLabel','foreground'),self.app.palette.ACCENT)
            self.assertEqual(style.lookup('NotificationBadge.TLabel','background'),self.app.palette.TINT)
            self.assertEqual(style.lookup('Neutral.ToastMark.TLabel','foreground'),self.app.palette.MUTED)
            self.assertNotEqual(style.lookup('Neutral.ToastMark.TLabel','foreground'),self.app.palette.ERROR)
        self.p.dismiss();self.refresh()
        self.assertFalse(self.app.store.notifications()[0]['is_read'])

    def test_timeout_and_hover(self):
        self.add();self.refresh();self.p.pause();self.p.DURATION_MS=20
        time.sleep(.03);self.root.update();self.assertIsNotNone(self.p.toast)
        self.p.resume();time.sleep(.03);self.root.update()
        self.assertIsNone(self.p.toast);self.assertEqual(self.p.badge_count,1)

    def test_existing_unread_does_not_popup_on_start(self):
        self.add();self.p.close();self.p.badge.destroy()
        self.p=self.app.notification_presenter=NotificationPresenter(self.app)
        self.refresh();self.assertIsNone(self.p.toast);self.assertEqual(self.p.badge_count,1)

    def test_single_view_marks_read_and_opens_inbox(self):
        nid=self.add();self.refresh();self.p.view_button.invoke();self.root.update()
        self.assertIsNone(self.p.toast);self.assertEqual(self.p.badge_count,0)
        self.assertEqual(self.p.badge.winfo_manager(),'')
        self.assertTrue(self.app.store.notifications()[0]['is_read'])
        self.assertEqual(self.app.book.select(),str(self.app.tabs['notice']))
        self.assertEqual(self.app.notices.selection(),(nid,))

    def test_batch_is_one_popup_and_does_not_mark_all_read(self):
        self.add();self.refresh();old=self.p.toast
        nid=self.add('第二則');self.refresh()
        self.assertFalse(old.winfo_exists());self.assertEqual(self.p.toast_count,2)
        self.assertEqual(self.p.view_button.cget('text'),'查看 2 則通知')
        self.p.view_button.invoke();self.root.update()
        self.assertEqual(self.p.badge_count,2)
        self.app.open_notice(nid);self.assertEqual(self.p.badge_count,1)

    def test_badge_over_99_and_read_notifications_never_popup(self):
        self.add(read=True);self.refresh();self.assertIsNone(self.p.toast)
        for _ in range(100):self.add()
        self.refresh();self.assertEqual(self.p.badge.cget('text'),'99+ 未讀')
        self.assertEqual(self.p.toast_count,100)

    def test_deleted_notice_closes_popup_and_stale_click_is_safe(self):
        nid=self.add();self.refresh()
        with self.app.store.connection() as db:db.execute('DELETE FROM notifications WHERE id=?',(nid,))
        self.refresh();self.assertIsNone(self.p.toast)
        self.app.open_notice(nid);self.assertIn('已移除',self.app.status.get())

    def test_result_routing_and_error_theme(self):
        with self.app.store.connection() as db:
            tid,_=self.app.engine._new_task(db,'query',{})
            db.execute("UPDATE tasks SET state='failed',error='合成失敗' WHERE id=?",(tid,))
        nid=self.add('查詢失敗，請查看原因',task=tid);self.refresh()
        self.assertEqual(self.p.symbol.cget('text'),'!')
        self.assertEqual(self.p.symbol.cget('style'),'Error.ToastMark.TLabel')
        with patch('desktop_app.ui.messagebox.showerror') as error:
            self.app.open_notice(nid);error.assert_called_once()
        with self.app.store.connection() as db:db.execute('UPDATE notifications SET is_read=0 WHERE id=?',(nid,))
        self.refresh()
        for theme in ('light','dark'):
            self.app.change_theme(theme);self.root.update()
            self.assertEqual(self.app.appearance.style.lookup('Error.ToastMark.TLabel','foreground'),self.app.palette.ERROR)
            self.assertEqual(self.p.badge_count,1)
        with self.app.store.connection() as db:
            db.execute("UPDATE tasks SET state='succeeded',result=? WHERE id=?",('{"text":"合成結果"}',tid))
        with patch.object(self.app,'show_result') as show:
            self.app.open_notice(nid);show.assert_called_once_with(tid)

    def test_long_content_is_preserved_and_close_cancels_timer(self):
        original='合成內容'*100;self.add(original);self.refresh()
        self.assertTrue(self.p.message.cget('text').endswith('…'))
        self.assertEqual(self.app.store.notifications()[0]['text'],original)
        self.p.close();self.assertIsNone(self.p.timer);self.assertIsNone(self.p.toast)

    def test_missing_source_keeps_notification_readable(self):
        nid=self.add(task='removed-source');self.refresh()
        self.assertEqual(self.p.symbol.cget('style'),'Info.ToastMark.TLabel')
        self.app.open_notice(nid)
        self.assertIn('來源工作已移除',self.app.status.get())
        self.assertEqual(len(self.app.store.notifications()),1)
