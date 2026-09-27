import gc
import tkinter as tk
import ctypes
from unittest import TestCase
from unittest.mock import patch
from desktop_app.theme import Appearance
from desktop_app.display import Display
from desktop_app.dialogs import MessageDialog,askyesno,showerror
from desktop_app.window_chrome import apply_titlebar,colorref


def windows_clipboard_text():
    # Tk 8.6 clipboard_get can split long UTF-8 chunks incorrectly on Windows.
    # Verify what Windows consumers actually receive, not that Tcl readback path.
    user=ctypes.WinDLL('user32');kernel=ctypes.WinDLL('kernel32')
    user.GetClipboardData.restype=ctypes.c_void_p
    kernel.GlobalLock.argtypes=[ctypes.c_void_p];kernel.GlobalLock.restype=ctypes.c_void_p
    kernel.GlobalUnlock.argtypes=[ctypes.c_void_p]
    if not user.OpenClipboard(None):raise RuntimeError('clipboard busy')
    try:
        handle=user.GetClipboardData(13);pointer=kernel.GlobalLock(handle)
        try:return ctypes.wstring_at(pointer).replace('\r\n','\n')
        finally:kernel.GlobalUnlock(handle)
    finally:user.CloseClipboard()


class DialogTests(TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.geometry('800x600');Display(self.root)
        self.appearance=Appearance(self.root,'dark');self.root.update()

    def tearDown(self):
        self.root.destroy();self.root=None;self.appearance=None;gc.collect()

    def test_long_message_theme_copy_and_close_without_mutation(self):
        entry=tk.Text(self.root);entry.pack();entry.insert('1.0','原草稿');entry.focus_force()
        text='查詢失敗，請核對條件。\n'*120
        dialog=MessageDialog(self.root,'操作未完成',text,'error');self.root.update()
        self.assertEqual(dialog.grab_current(),dialog)
        dialog.copy_message();self.root.update();self.assertEqual(windows_clipboard_text(),text)
        self.appearance.configure('light');self.root.update()
        self.assertEqual(dialog.message_text.cget('background'),self.appearance.colors.SURFACE)
        self.assertEqual(dialog.message_text.get('1.0','end-1c'),text)
        self.assertLessEqual(dialog.close_button.winfo_rooty()+dialog.close_button.winfo_height(),dialog.winfo_rooty()+dialog.winfo_height())
        dialog.dismiss();self.assertEqual(entry.get('1.0','end-1c'),'原草稿')

    def test_confirmation_defaults_cancel_escape_and_explicit_accept(self):
        dialog=MessageDialog(self.root,'確認操作','合成條件',question=True);self.root.update()
        self.assertEqual(dialog.focus_get(),dialog.close_button)
        dialog.event_generate('<Escape>');self.root.update();self.assertFalse(dialog.result)
        def accept():
            for child in self.root.winfo_children():
                if isinstance(child,MessageDialog):child.accept_button.invoke()
        self.root.after(150,accept)
        self.assertTrue(askyesno('確認','合成條件',parent=self.root))

    def test_nested_grab_is_restored_and_copy_error_is_inline(self):
        parent=tk.Toplevel(self.root);parent.grab_set();self.root.update()
        dialog=MessageDialog(parent,'訊息','合成訊息')
        with patch.object(dialog,'clipboard_append',side_effect=tk.TclError('busy')):dialog.copy_message()
        self.assertIn('無法使用剪貼簿',dialog.copy_status.get())
        dialog.dismiss();self.assertEqual(parent.grab_current(),parent)
        parent.destroy()

    def test_titlebar_optional_and_colorref(self):
        self.assertEqual(colorref('#123456'),0x563412)
        with patch('desktop_app.window_chrome.ctypes.WinDLL',side_effect=OSError('unsupported')):
            self.assertFalse(apply_titlebar(self.root,'dark',self.appearance.colors)['supported'])
        child=tk.Toplevel(self.root);self.root.update()
        self.assertTrue(hasattr(child,'_qa_chrome_status'))
        self.appearance.configure('light');self.root.update();child.destroy()

    def test_startup_fallback_without_appearance(self):
        with patch('desktop_app.dialogs.native.showerror',return_value='ok') as native:
            self.assertEqual(showerror('啟動','合成訊息'),'ok');native.assert_called_once()
