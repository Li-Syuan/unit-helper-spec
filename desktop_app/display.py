"""System-DPI startup and logical-pixel layout. No process-wide Tk monkeypatch."""
import ctypes
from ctypes import wintypes
import sys
import tkinter as tk
from tkinter import ttk, font


def awareness():
    if sys.platform != 'win32':
        return 'not_windows'
    try:
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        user.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        return {0:'unaware', 1:'system', 2:'per_monitor'}.get(
            user.GetAwarenessFromDpiAwarenessContext(user.GetThreadDpiAwarenessContext()), 'unknown')
    except (AttributeError, OSError):
        return 'unknown'


def initialize_dpi():
    """Must run before the first Tk HWND. Never downgrade existing awareness."""
    before = awareness()
    if before != 'unaware':
        return {'before':before, 'after':before, 'changed':False}
    try:
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        changed = bool(user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-2)))
    except (AttributeError, OSError):
        try:
            changed = bool(ctypes.windll.user32.SetProcessDPIAware())
        except (AttributeError, OSError):
            changed = False
    return {'before':before, 'after':awareness(), 'changed':changed}


def work_area(root):
    """Monitor work area in this process's coordinate space, excluding taskbar."""
    if sys.platform == 'win32':
        try:
            user=ctypes.WinDLL('user32',use_last_error=True)
            class Info(ctypes.Structure):
                _fields_=[('size',wintypes.DWORD),('monitor',wintypes.RECT),('work',wintypes.RECT),('flags',wintypes.DWORD)]
            user.MonitorFromWindow.argtypes=[wintypes.HWND,wintypes.DWORD];user.MonitorFromWindow.restype=wintypes.HANDLE
            user.GetMonitorInfoW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Info)]
            info=Info();info.size=ctypes.sizeof(Info)
            monitor=user.MonitorFromWindow(root.winfo_id(),2)
            if user.GetMonitorInfoW(monitor,ctypes.byref(info)):
                r=info.work;return r.left,r.top,r.right-r.left,r.bottom-r.top
        except (AttributeError,OSError):
            pass
    return 0,0,root.winfo_screenwidth(),root.winfo_screenheight()


class Display:
    def __init__(self, root, factor=None):
        self.root=root
        # Tk fonts already use points. Do not multiply font sizes or tk scaling.
        self.factor=factor if factor is not None else round(root.winfo_fpixels('1i')/96,2)
        self.factor=max(.75,min(4.0,self.factor))
        root._qa_display=self

    def px(self, value):
        if isinstance(value,(tuple,list)):
            return tuple(self.px(v) for v in value)
        return round(float(value)*self.factor)

    def size_window(self, window, width, height, minimum=(520,360)):
        x,y,w,h=work_area(window)
        # Leave room for native borders and the title bar.
        available=(max(240,w-self.px(24)),max(240,h-self.px(64)))
        size=(min(self.px(width),available[0]),min(self.px(height),available[1]))
        window.minsize(min(self.px(minimum[0]),available[0]),min(self.px(minimum[1]),available[1]))
        window.geometry(f'{size[0]}x{size[1]}+{x+self.px(12)}+{y+self.px(12)}')

    def icon_size(self, base=24):
        wanted=self.px(base)
        return min((24,30,36,48,60,72,96),key=lambda n:abs(n-wanted))

    def scale_widget(self, widget):
        """Scale fixed pixel dimensions once; never character/point dimensions.

        Dynamic measurements (Configure event widths) are already physical pixels
        and must be explicitly handled by callers, not rescaled on theme changes.
        """
        if getattr(widget,'_qa_pixels_scaled',False):return
        widget._qa_pixels_scaled=True
        if self.factor==1:return
        keys=set(widget.keys())
        props={'padx','pady','borderwidth','highlightthickness','spacing1','spacing2','spacing3','wraplength'}
        if isinstance(widget,(tk.Frame,ttk.Frame,tk.Canvas)):
            props.update(('width','height'))
        if isinstance(widget,ttk.Progressbar):props.add('length')
        for key in props & keys:
            value=widget.cget(key)
            if str(value):widget.configure(**{key:self.px(widget.winfo_pixels(value))})
        if 'padding' in keys:
            values=widget.tk.splitlist(widget.cget('padding'))
            if values:widget.configure(padding=tuple(self.px(widget.winfo_pixels(v)) for v in values))
        manager=widget.winfo_manager()
        if manager in ('pack','grid'):
            info=widget.pack_info() if manager=='pack' else widget.grid_info()
            opts={}
            for key in ('padx','pady','ipadx','ipady'):
                raw=info.get(key,0)
                values=raw if isinstance(raw,(tuple,list)) else widget.tk.splitlist(str(raw))
                opts[key]=tuple(self.px(widget.winfo_pixels(v)) for v in values)
            (widget.pack_configure if manager=='pack' else widget.grid_configure)(**opts)
        if isinstance(widget,ttk.Treeview):
            for col in ('#0',*widget['columns']):
                for key in ('width','minwidth'):widget.column(col,**{key:self.px(widget.column(col,key))})
        if isinstance(widget,tk.Text):
            for tag in widget.tag_names():
                for key in ('spacing1','spacing2','spacing3','lmargin1','lmargin2','rmargin'):
                    value=widget.tag_cget(tag,key)
                    if value:widget.tag_configure(tag,**{key:self.px(widget.winfo_pixels(value))})

    def diagnostics(self, window=None):
        w=window or self.root
        return {'awareness':awareness(),'dpi':round(w.winfo_fpixels('1i'),2),
                'layout_factor':self.factor,'tk_scaling':float(w.tk.call('tk','scaling')),
                'window_pixels':[w.winfo_width(),w.winfo_height()],
                'work_area_pixels':list(work_area(w)),
                'font':font.Font(root=w,family='Microsoft JhengHei',size=12).actual(),
                'cross_monitor_live_scaling':'not_supported'}


class WorkspaceViewport(ttk.Frame):
    """Keep the minimum logical workspace reachable on small/high-DPI displays."""
    def __init__(self, parent, display, minimum=(1050,700)):
        super().__init__(parent)
        self.display=display
        self.minimum=minimum
        self.columnconfigure(0,weight=1);self.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,highlightthickness=0,borderwidth=0)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        self.vbar=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.hbar=ttk.Scrollbar(self,orient='horizontal',command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vbar.set,xscrollcommand=self.hbar.set)
        self.body=ttk.Frame(self.canvas)
        self.item=self.canvas.create_window(0,0,window=self.body,anchor='nw')
        self.canvas.bind('<Configure>',self.layout)
        self.body.bind('<Configure>',self.layout,add='+')

    def layout(self,event=None):
        width=self.canvas.winfo_width();height=self.canvas.winfo_height()
        minimum=self.display.px(self.minimum) if self.minimum else (self.body.winfo_reqwidth(),self.body.winfo_reqheight())
        self.canvas.itemconfigure(self.item,width=max(width,minimum[0]),height=max(height,minimum[1]))
        self.canvas.configure(scrollregion=(0,0,max(width,minimum[0]),max(height,minimum[1])))
        if height<minimum[1]:self.vbar.grid(row=0,column=1,sticky='ns')
        else:self.vbar.grid_remove();self.canvas.yview_moveto(0)
        if width<minimum[0]:self.hbar.grid(row=1,column=0,sticky='ew')
        else:self.hbar.grid_remove();self.canvas.xview_moveto(0)

    def reveal(self,event):
        widget=event.widget
        if not str(widget).startswith(str(self.body)):return
        # Keyboard traversal into a clipped part brings it into view.
        x=widget.winfo_rootx()-self.body.winfo_rootx();y=widget.winfo_rooty()-self.body.winfo_rooty()
        for axis,offset,extent,total in [('x',x,widget.winfo_width(),self.body.winfo_width()),('y',y,widget.winfo_height(),self.body.winfo_height())]:
            view=getattr(self.canvas,axis+'view')();visible=(self.canvas.winfo_width() if axis=='x' else self.canvas.winfo_height())
            start=view[0]*total
            if offset<start:getattr(self.canvas,axis+'view_moveto')(offset/max(1,total))
            elif offset+extent>start+visible:getattr(self.canvas,axis+'view_moveto')((offset+extent-visible)/max(1,total))


def scroll_frame(window, padding=16):
    display=window._root()._qa_display
    view=WorkspaceViewport(window,display,minimum=None);view.pack(fill='both',expand=True)
    window.bind('<FocusIn>',view.reveal,add='+')
    return ttk.Frame(view.body,padding=padding)
