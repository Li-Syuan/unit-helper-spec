"""Real bundled image loading and GUI fallback; no company-service claims."""
import gc
import ctypes
from ctypes import wintypes
import os
import struct
import tempfile
import shutil
import unittest
from pathlib import Path
import tkinter as tk
from unittest.mock import patch
from desktop_app import branding
from desktop_app.theme import Appearance
from desktop_app.config import DEFAULT
from desktop_app.display import Display
from desktop_app.preferences import save_theme
from desktop_app.ui import App, ChoiceDialog
from types import SimpleNamespace


class BrandingTests(unittest.TestCase):
    def test_ico_sizes_and_png_transparent_corners(self):
        for folder in (branding.ASSETS, branding.ASSETS/'light'):
            with self.subTest(folder=folder): self.check_icon_pack(folder)

    def check_icon_pack(self, folder):
        data=(folder/'qa-agent.ico').read_bytes()
        reserved,kind,count=struct.unpack_from('<HHH',data)
        self.assertEqual((reserved,kind,count),(0,1,7))
        sizes=[]
        for i in range(count):
            width,height,colors,reserved,planes,depth,length,offset=struct.unpack_from('<BBBBHHII',data,6+i*16)
            width=width or 256; height=height or 256; sizes.append(width)
            self.assertEqual(width,height); self.assertEqual(depth,32)
            self.assertEqual(data[offset:offset+8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(data[offset:offset+length],(folder/f'qa-agent-{width}.png').read_bytes())
        self.assertEqual(sizes,[16,24,32,48,64,128,256])
        root=tk.Tk(); root.withdraw()
        try:
            for size in sizes:
                image=tk.PhotoImage(master=root,file=str(folder/f'qa-agent-{size}.png'))
                self.assertEqual((image.width(),image.height()),(size,size))
                self.assertTrue(image.transparency_get(0,0))
                self.assertFalse(image.transparency_get(size//2,size//2))
                del image
        finally: root.destroy()

    def test_saved_theme_and_live_existing_and_future_window_icons(self):
        with tempfile.TemporaryDirectory() as directory:
            save_theme(Path(directory)/'ui-preferences.json','light')
            root=tk.Tk(); root.withdraw()
            app=App(root,config=DEFAULT,directory=Path(directory))
            try:
                self.assertEqual(root._qa_icon_theme,'light')
                self.assertEqual(root._qa_icon_folder,branding.ASSETS/'light')
                label=app.brand_image_label
                child=tk.Toplevel(root); branding.apply_child_icons(child)
                for theme in ('dark','light','dark'):
                    before=app.brand_icon.get(16,16)
                    app.change_theme(theme); root.update()
                    self.assertEqual(root._qa_icon_theme,theme)
                    self.assertEqual(child._qa_icon_theme,theme)
                    self.assertIs(label,app.brand_image_label)
                    self.assertEqual(str(label.cget('image')),str(app.brand_icon))
                    self.assertNotEqual(before,app.brand_icon.get(16,16))
                    future=tk.Toplevel(root); branding.apply_child_icons(future)
                    self.assertEqual(future._qa_icon_theme,theme)
                    future.destroy()
                self.assertEqual(app.store.tasks(),[])
            finally:
                app.close(force=True); del app,root; gc.collect()

    def test_missing_light_pack_reports_warning_and_uses_dark_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            for source in branding.ASSETS.glob('qa-agent*'):
                shutil.copyfile(source,folder/source.name)
            root=tk.Tk(); root.withdraw()
            try:
                icon,error=branding.apply_icons(root,assets=folder,theme='light')
                self.assertIsNotNone(icon); self.assertTrue(error)
                self.assertEqual(root._qa_icon_theme,'dark')
                child=tk.Toplevel(root); branding.apply_child_icons(child)
                self.assertEqual(child._qa_icon_theme,'dark')
            finally: root.destroy(); del root; gc.collect()

    def test_icons_load_from_another_working_directory_and_child_inherits(self):
        self.assertTrue(branding.set_windows_identity())
        with tempfile.TemporaryDirectory() as directory:
            old=os.getcwd(); root=tk.Tk(); root.withdraw()
            try:
                os.chdir(directory)
                icon,error=branding.apply_icons(root)
                self.assertFalse(error); self.assertEqual(icon.width(),32)
                appearance=Appearance(root)
                child=ChoiceDialog(SimpleNamespace(root=root,display=Display(root),appearance=appearance,palette=appearance.colors,safe=lambda fn:fn()),{'questions':[]},lambda _:None)
                root.deiconify(); child.deiconify(); root.update()
                user=ctypes.windll.user32
                user.SendMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
                user.SendMessageW.restype=ctypes.c_void_p
                for window in (root,child):
                    # Tk's bitmap getter returns '' for Windows ICOs; inspect the real wrapper HWND.
                    hwnd=int(window.tk.call('wm','frame',window._w),16)
                    self.assertTrue(user.SendMessageW(hwnd,0x7F,0,0))
                    self.assertTrue(user.SendMessageW(hwnd,0x7F,1,0))
                child.destroy()
            finally:
                os.chdir(old); root.destroy()
                root._qa_icon_images.clear(); del root; gc.collect()

    def test_missing_assets_keeps_app_usable_and_names_consistent(self):
        with tempfile.TemporaryDirectory() as directory:
            root=tk.Tk(); root.withdraw()
            with patch.object(branding,'ASSETS',Path(directory)/'missing'):
                app=App(root,config=DEFAULT,directory=Path(directory)/'data')
            try:
                root.update()
                self.assertTrue(root.title().startswith('QA agent'))
                self.assertTrue(app.brand_warning)
                self.assertIsNone(app.brand_icon)
                app.store.add_message(app.conversation,'assistant','測試答案')
                app.show_chat()
                self.assertIn('QA agent',app.transcript.get('1.0','end'))
                self.assertNotIn('小幫手',app.transcript.get('1.0','end'))
                self.assertTrue(app.query_submit.winfo_exists())
            finally:
                app.close(force=True); del app,root; gc.collect()
