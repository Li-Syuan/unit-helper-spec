"""Real bundled image loading and GUI fallback; no company-service claims."""
import gc
import ctypes
from ctypes import wintypes
import os
import struct
import tempfile
import unittest
from pathlib import Path
import tkinter as tk
from unittest.mock import patch
from desktop_app import branding
from desktop_app.config import DEFAULT
from desktop_app.ui import App, ChoiceDialog
from types import SimpleNamespace


class BrandingTests(unittest.TestCase):
    def test_ico_sizes_and_png_transparent_corners(self):
        data=(branding.ASSETS/'qa-agent.ico').read_bytes()
        reserved,kind,count=struct.unpack_from('<HHH',data)
        self.assertEqual((reserved,kind,count),(0,1,7))
        sizes=[]
        for i in range(count):
            width,height,colors,reserved,planes,depth,length,offset=struct.unpack_from('<BBBBHHII',data,6+i*16)
            width=width or 256; height=height or 256; sizes.append(width)
            self.assertEqual(width,height); self.assertEqual(depth,32)
            self.assertEqual(data[offset:offset+8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(data[offset:offset+length],(branding.ASSETS/f'qa-agent-{width}.png').read_bytes())
        self.assertEqual(sizes,[16,24,32,48,64,128,256])
        root=tk.Tk(); root.withdraw()
        try:
            for size in sizes:
                image=tk.PhotoImage(master=root,file=str(branding.ASSETS/f'qa-agent-{size}.png'))
                self.assertEqual((image.width(),image.height()),(size,size))
                self.assertTrue(image.transparency_get(0,0))
                self.assertFalse(image.transparency_get(size//2,size//2))
                del image
        finally: root.destroy()

    def test_icons_load_from_another_working_directory_and_child_inherits(self):
        self.assertTrue(branding.set_windows_identity())
        with tempfile.TemporaryDirectory() as directory:
            old=os.getcwd(); root=tk.Tk(); root.withdraw()
            try:
                os.chdir(directory)
                icon,error=branding.apply_icons(root)
                self.assertFalse(error); self.assertEqual(icon.width(),32)
                child=ChoiceDialog(SimpleNamespace(root=root,safe=lambda fn:fn()),{'questions':[]},lambda _:None)
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
