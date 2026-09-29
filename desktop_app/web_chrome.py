"""Optional native frame branding. Failure never changes business behaviour."""
from pathlib import Path


def seal_navigation(window):
    """After local HTML load, reject all further top-level/document navigation."""
    from System import Action
    def update():
        if getattr(window,'_qa_navigation_sealed',False):return
        core=window.native.webview.CoreWebView2
        def navigation(sender,args):args.Cancel=True
        def new_window(sender,args):args.Handled=True
        core.NavigationStarting+=navigation
        core.NewWindowRequested+=new_window
        core.Settings.IsPasswordAutosaveEnabled=False
        core.Settings.IsGeneralAutofillEnabled=False
        window._qa_navigation_handlers=(navigation,new_window)
        window._qa_navigation_sealed=True
    window.native.Invoke(Action(update))


def apply_chrome(window, theme):
    if window is None or window.native is None:return
    try:
        import ctypes
        from ctypes import wintypes
        from System import Action
        from System.Drawing import Icon
        def update():
            form=window.native
            cached=getattr(window,'_qa_icons',{})
            if theme not in cached:
                folder=Path(__file__).parent/'assets'
                if theme=='light':folder/='light'
                cached[theme]=Icon(str(folder/'qa-agent.ico'));window._qa_icons=cached
            form.Icon=cached[theme]
            setter=ctypes.WinDLL('dwmapi').DwmSetWindowAttribute
            setter.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
            setter.restype=ctypes.c_long
            for attribute,value in [(20,int(theme=='dark')),(35,0x221610 if theme=='dark' else 0xF7EDE6),(36,0xE8E8E8 if theme=='dark' else 0x342D24)]:
                item=wintypes.DWORD(value)
                setter(form.Handle.ToInt64(),attribute,ctypes.byref(item),ctypes.sizeof(item))
        window.native.Invoke(Action(update))
    except Exception:pass
