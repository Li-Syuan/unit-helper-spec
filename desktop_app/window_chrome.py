"""Optional native Windows frame colors; keep system window controls and behavior."""
import ctypes
from ctypes import wintypes
import sys
import tkinter as tk


def colorref(color):
    red, green, blue = (int(color[i:i+2], 16) for i in (1, 3, 5))
    return red | (green << 8) | (blue << 16)


def apply_titlebar(window, name, colors):
    if sys.platform != 'win32':
        return {'supported':False}
    try:
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
        user.GetAncestor.restype=wintypes.HWND
        hwnd=user.GetAncestor(window.winfo_id(),2)
        setter=ctypes.WinDLL('dwmapi').DwmSetWindowAttribute
        setter.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
        setter.restype=ctypes.c_long
        result={}
        for key,attribute,value in [('dark',20,int(name=='dark')),
                                    ('caption',35,colorref(colors.SIDEBAR)),
                                    ('text',36,colorref(colors.INK)),
                                    ('border',34,colorref(colors.BORDER))]:
            data=wintypes.DWORD(value)
            result[key]=setter(hwnd,attribute,ctypes.byref(data),ctypes.sizeof(data))==0
        result['supported']=result['caption']
        window._qa_chrome_status=result
        return result
    except (OSError,AttributeError,tk.TclError):
        return {'supported':False}
