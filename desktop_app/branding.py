"""Application identity and bundled icons; independent of cwd and user data paths."""
from pathlib import Path
import sys
import tkinter as tk

APP_NAME = 'QA agent'
APP_ID = 'QAagent.UnitHelper.Desktop'
ASSETS = Path(__file__).resolve().parent / 'assets'


def set_windows_identity():
    if sys.platform != 'win32':
        return True
    try:
        import ctypes
        setter = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        setter.argtypes = [ctypes.c_wchar_p]
        setter.restype = ctypes.c_long
        return setter(APP_ID) == 0
    except (AttributeError, OSError):
        return False


def apply_icons(root, assets=None):
    folder = Path(assets) if assets is not None else ASSETS
    images = {}
    failed = False
    for size in (16, 32, 48, 64, 128, 256):
        try:
            images[size] = tk.PhotoImage(master=root, file=str(folder / f'qa-agent-{size}.png'))
        except (tk.TclError, OSError):
            failed = True
    root._qa_icon_folder = folder
    root._qa_icon_images = images  # Tk must retain these references for root's lifetime.
    if images:
        try:
            root.iconphoto(True, *images.values())  # Default inherited by future Toplevels.
        except tk.TclError:
            failed = True
    if sys.platform == 'win32':
        try:
            root.iconbitmap(default=str(folder / 'qa-agent.ico'))
            root.iconbitmap(str(folder / 'qa-agent.ico'))
        except (tk.TclError, OSError):
            failed = True
    return images.get(32), ('應用圖示未完整載入；功能仍可使用，請重新取得完整程式檔。' if failed else '')


def apply_child_icons(window):
    """Explicit per-window icon as Windows/Tk bitmap queries omit inherited defaults."""
    root=window._root()
    images=getattr(root, '_qa_icon_images', {})
    try:
        if images:
            window.iconphoto(False, *images.values())
        if sys.platform == 'win32':
            folder=getattr(root, '_qa_icon_folder', ASSETS)
            window.iconbitmap(str(folder/'qa-agent.ico'))
    except (tk.TclError, OSError):
        pass  # Main window already displays the missing-resource notice.
