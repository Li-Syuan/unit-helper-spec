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


def apply_icons(root, assets=None, theme='dark'):
    base = Path(assets) if assets is not None else ASSETS
    folder = base / 'light' if theme == 'light' else base
    images = {}
    failed = False
    # Keep a usable bundled dark icon if a partial installation lacks the light set.
    if theme == 'light' and not all((folder / name).is_file() for name in
            [f'qa-agent-{n}.png' for n in (16,32,48,64,128,256)] + ['qa-agent.ico']):
        folder = base
        failed = True
    for size in (16, 32, 48, 64, 128, 256):
        try:
            images[size] = tk.PhotoImage(master=root, file=str(folder / f'qa-agent-{size}.png'))
        except (tk.TclError, OSError):
            failed = True
    root._qa_icon_folder = folder
    root._qa_icon_theme = 'light' if folder == base / 'light' else 'dark'
    root._qa_icon_images = images  # Tk must retain these references for root's lifetime.
    if images:
        try:
            root.iconphoto(True, *images.values())  # Default inherited by future Toplevels.
            root.iconphoto(False, *images.values())  # Also set this existing wrapper HWND.
        except tk.TclError:
            failed = True
    # iconphoto supplies native Windows icons too. Tk 8.6's repeated ICO loads
    # retain GDI/USER handles across theme changes; ICOs remain for shortcuts.
    def update_children(parent):
        for child in parent.winfo_children():
            if isinstance(child, tk.Toplevel):
                apply_child_icons(child)
            update_children(child)
    update_children(root)
    display=getattr(root,'_qa_display',None)
    wanted=display.px(32) if display else 32
    selected=images.get(min(images,key=lambda n:abs(n-wanted))) if images else None
    return selected, ('應用圖示未完整載入；功能仍可使用，請重新取得完整程式檔。' if failed else '')


def apply_child_icons(window):
    """Apply native window icons from the retained multi-size PNG resources."""
    root=window._root()
    images=getattr(root, '_qa_icon_images', {})
    window._qa_icon_theme = getattr(root, '_qa_icon_theme', 'dark')
    try:
        if images:
            window.iconphoto(False, *images.values())
    except (tk.TclError, OSError):
        pass  # Main window already displays the missing-resource notice.
