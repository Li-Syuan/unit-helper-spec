"""Per-Tcl-interpreter appearance; recolor existing widgets without rebuilding them."""
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk

FONT = 'Microsoft JhengHei'
_TOKENS = {
    'dark': dict(BG='#181C21', SURFACE='#22272E', INK='#ECEEF1', MUTED='#B1B7C0',
        BORDER='#41464F', ACCENT='#63D3EC', ACCENT_HOVER='#8DE3F5', TINT='#263E49',
        SIDEBAR='#11151A', SIDEBAR_HOVER='#30343B', STRIPE='#2D3035',
        ERROR='#FF9C94', SUCCESS='#88D8B0', DISABLED='#868D98', BUTTON_INK='#10242A', WARNING='#F0CC89'),
    'light': dict(BG='#F6F7F9', SURFACE='#FFFFFF', INK='#222833', MUTED='#5C6675',
        BORDER='#D5DAE2', ACCENT='#08768E', ACCENT_HOVER='#075E73', TINT='#DFF1F6',
        SIDEBAR='#ECEFF3', SIDEBAR_HOVER='#DCE3EB', STRIPE='#F2F5F8',
        ERROR='#AB302C', SUCCESS='#187548', DISABLED='#727B89', BUTTON_INK='#FFFFFF', WARNING='#83580C'),
}


def palette(name):
    if name not in _TOKENS: raise ValueError('不支援的外觀主題。')
    return SimpleNamespace(**_TOKENS[name], FONT=FONT)


class Appearance:
    def __init__(self, root, name='dark'):
        self.root = root
        self.style = ttk.Style(root)
        self.style.theme_use('clam')
        self.name = name
        self.colors = palette(name)
        self.configure(name)

    def configure(self, name):
        self.name = name
        c = self.colors = palette(name)
        root = self.root
        root.configure(background=c.BG)
        # Defaults are scoped to this Tk interpreter and used by future dialogs.
        for key, value in {'background':c.SURFACE, 'foreground':c.INK, 'relief':'flat',
            'borderWidth':0, 'highlightThickness':1, 'highlightBackground':c.BORDER,
            'highlightColor':c.ACCENT, 'insertBackground':c.INK, 'selectBackground':c.TINT,
            'selectForeground':c.INK, 'padX':14, 'padY':10, 'spacing1':3, 'spacing3':5}.items():
            root.option_add('*Text.'+key, value)
        root.option_add('*Text.font', (FONT, 11))
        root.option_add('*Toplevel.background', c.BG)
        root.option_add('*Canvas.background', c.BG)
        for key,value in {'background':c.SURFACE,'foreground':c.INK,'selectBackground':c.TINT,'selectForeground':c.INK}.items():
            root.option_add('*TCombobox*Listbox.'+key,value)
        s=self.style
        s.configure('.',font=(FONT,10),background=c.BG,foreground=c.INK)
        s.configure('TFrame',background=c.BG)
        s.configure('Surface.TFrame',background=c.SURFACE)
        s.configure('Card.TFrame',background=c.SURFACE,borderwidth=1,relief='solid',bordercolor=c.BORDER,lightcolor=c.BORDER,darkcolor=c.BORDER)
        s.configure('CardBody.TFrame',background=c.SURFACE,borderwidth=0,relief='flat')
        s.configure('CardMuted.TLabel',background=c.SURFACE,foreground=c.MUTED,font=(FONT,9))
        s.configure('CardTitle.TLabel',background=c.SURFACE,foreground=c.INK,font=(FONT,11,'bold'))
        s.configure('CardError.TLabel',background=c.SURFACE,foreground=c.ERROR,font=(FONT,9))
        s.configure('Compact.TButton',padding=(8,4),font=(FONT,9))
        s.configure('Card.TCheckbutton',background=c.SURFACE)
        s.configure('Workspace.Horizontal.TProgressbar',troughcolor=c.SURFACE,background=c.ACCENT,borderwidth=0,thickness=3)
        s.configure('TLabel',background=c.BG,foreground=c.INK)
        s.configure('Muted.TLabel',foreground=c.MUTED)
        s.configure('Title.TLabel',font=(FONT,16,'bold'))
        s.configure('Section.TLabel',font=(FONT,11,'bold'))
        s.configure('Surface.TLabel',background=c.SURFACE)
        s.configure('Empty.TLabel',background=c.SURFACE,foreground=c.MUTED)
        s.configure('Chip.TLabel',background=c.TINT,foreground=c.ACCENT,padding=(10,5),font=(FONT,9,'bold'))
        s.configure('Status.TLabel',background=c.SURFACE,foreground=c.MUTED,font=(FONT,9),padding=(16,6))
        s.configure('TButton',padding=(12,7),background=c.SURFACE,foreground=c.INK,bordercolor=c.BORDER,
            lightcolor=c.SURFACE,darkcolor=c.SURFACE,borderwidth=1,focuscolor=c.ACCENT)
        s.map('TButton',background=[('disabled',c.BG),('pressed',c.TINT),('active',c.STRIPE)],foreground=[('disabled',c.DISABLED)])
        s.configure('Primary.TButton',background=c.ACCENT,foreground=c.BUTTON_INK,bordercolor=c.ACCENT,
            lightcolor=c.ACCENT,darkcolor=c.ACCENT,font=(FONT,10,'bold'))
        s.map('Primary.TButton',background=[('disabled',c.BORDER),('pressed',c.ACCENT_HOVER),('active',c.ACCENT_HOVER)],
            foreground=[('disabled',c.DISABLED),('!disabled',c.BUTTON_INK)])
        s.configure('Quiet.TButton',background=c.BG,bordercolor=c.BG,lightcolor=c.BG,darkcolor=c.BG,foreground=c.MUTED)
        s.configure('Danger.TButton',foreground=c.ERROR)
        s.configure('Quick.TButton',padding=(12,9),anchor='w',font=(FONT,10))
        s.configure('TEntry',padding=7,fieldbackground=c.SURFACE,foreground=c.INK,insertcolor=c.INK,
            selectbackground=c.TINT,selectforeground=c.INK,bordercolor=c.BORDER,lightcolor=c.BORDER,darkcolor=c.BORDER)
        s.map('TEntry',bordercolor=[('focus',c.ACCENT)],fieldbackground=[('disabled',c.BG)],foreground=[('disabled',c.DISABLED)])
        s.configure('TCombobox',padding=6,fieldbackground=c.SURFACE,background=c.SURFACE,foreground=c.INK,
            arrowcolor=c.MUTED,bordercolor=c.BORDER,lightcolor=c.BORDER,darkcolor=c.BORDER)
        s.map('TCombobox',fieldbackground=[('disabled',c.BG),('readonly',c.SURFACE)],
            selectbackground=[('readonly',c.SURFACE)],selectforeground=[('readonly',c.INK)],foreground=[('disabled',c.DISABLED),('readonly',c.INK)])
        for kind in ('TCheckbutton','TRadiobutton'):
            s.configure(kind,padding=(0,5),background=c.BG,foreground=c.INK,indicatorbackground=c.SURFACE,indicatorforeground=c.ACCENT)
            s.map(kind,background=[('active',c.BG)],foreground=[('disabled',c.DISABLED)],indicatorbackground=[('selected',c.ACCENT),('!selected',c.SURFACE)])
        s.configure('Card.TRadiobutton',padding=(16,12),background=c.SURFACE,font=(FONT,11,'bold'))
        s.map('Card.TRadiobutton',background=[('selected',c.TINT),('active',c.STRIPE)])
        s.configure('Treeview',rowheight=32,background=c.SURFACE,fieldbackground=c.SURFACE,foreground=c.INK,
            bordercolor=c.BORDER,lightcolor=c.BORDER,darkcolor=c.BORDER,borderwidth=1)
        s.configure('Treeview.Heading',background=c.STRIPE,foreground=c.MUTED,font=(FONT,9,'bold'),padding=(10,8),relief='flat')
        s.map('Treeview',background=[('selected',c.TINT)],foreground=[('selected',c.INK)])
        s.map('Treeview.Heading',background=[('active',c.BORDER)])
        s.configure('TScrollbar',background=c.BORDER,troughcolor=c.BG,arrowcolor=c.MUTED,
            lightcolor=c.BORDER,darkcolor=c.BORDER,bordercolor=c.BG,borderwidth=0,arrowsize=12,relief='flat')
        s.map('TScrollbar',background=[('pressed',c.ACCENT),('active',c.MUTED)],
            lightcolor=[('pressed',c.ACCENT),('active',c.MUTED)],
            darkcolor=[('pressed',c.ACCENT),('active',c.MUTED)],arrowcolor=[('disabled',c.DISABLED),('active',c.INK)])
        s.configure('TSeparator',background=c.BORDER)
        s.layout('Workspace.TNotebook', [('Notebook.client', {'sticky':'nswe'})])
        s.layout('Workspace.TNotebook.Tab', [])
        s.configure('Workspace.TNotebook',background=c.BG,borderwidth=0,tabmargins=0,bordercolor=c.BG,lightcolor=c.BG,darkcolor=c.BG)
        self.apply(root)

    def apply(self, widget, sidebar=False):
        c=self.colors
        sidebar=sidebar or getattr(widget,'_theme_role','')=='sidebar'
        role=getattr(widget,'_theme_role','')
        if isinstance(widget,(tk.Tk,tk.Toplevel)): widget.configure(background=c.BG)
        elif isinstance(widget,tk.Text):
            widget.configure(background=c.SURFACE,foreground=c.INK,insertbackground=c.INK,
                selectbackground=c.TINT,selectforeground=c.INK,highlightbackground=c.BORDER,highlightcolor=c.ACCENT)
            for tag,opts in {'welcome_title':{'foreground':c.INK},'welcome_body':{'foreground':c.MUTED},
                'speaker_user':{'foreground':c.ACCENT},'speaker_assistant':{'foreground':c.MUTED},'body_user':{'background':c.TINT},'body_assistant':{'background':c.SURFACE},'separator':{'foreground':c.BORDER}}.items():
                if tag in widget.tag_names(): widget.tag_configure(tag,**opts)
        elif isinstance(widget,tk.Canvas): widget.configure(background=c.BG,highlightbackground=c.BORDER)
        elif isinstance(widget,tk.Scrollbar) and not isinstance(widget,ttk.Scrollbar):
            # Native Windows Tk may ignore thumb colors; application scrollbars use ttk.
            widget.configure(background=c.BORDER,troughcolor=c.BG,activebackground=c.MUTED,
                highlightbackground=c.BG,highlightcolor=c.ACCENT,borderwidth=0,relief='flat',activerelief='flat')
        elif isinstance(widget,tk.Frame): widget.configure(background=c.BORDER if role=='divider' else c.SIDEBAR if sidebar else c.BG)
        elif isinstance(widget,tk.Label):
            widget.configure(background=c.SIDEBAR if sidebar else c.BG,foreground=c.WARNING if role=='warning' else c.INK if role=='brand' else c.MUTED)
        elif isinstance(widget,tk.Button):
            widget.configure(background=c.TINT if role=='new_chat' else c.SIDEBAR if sidebar else c.SURFACE,
                foreground=c.ACCENT if role=='new_chat' else c.INK,activebackground=c.SIDEBAR_HOVER,activeforeground=c.INK)
        elif isinstance(widget,tk.Listbox):
            widget.configure(background=c.SIDEBAR if sidebar else c.SURFACE,foreground=c.MUTED,
                selectbackground=c.SIDEBAR_HOVER,selectforeground=c.INK)
        elif isinstance(widget,ttk.Treeview):
            widget.tag_configure('even',background=c.SURFACE)
            widget.tag_configure('odd',background=c.STRIPE)
            widget.tag_configure('failure',foreground=c.ERROR)
            widget.tag_configure('success',foreground=c.SUCCESS)
        elif isinstance(widget,ttk.Combobox):
            # Existing popdowns are Tcl-created widgets, absent from winfo_children().
            pop=widget.tk.call('ttk::combobox::PopdownWindow',str(widget))
            widget.tk.call(str(pop)+'.f.l','configure','-background',c.SURFACE,'-foreground',c.INK,
                '-selectbackground',c.TINT,'-selectforeground',c.INK)
        for child in widget.winfo_children(): self.apply(child,sidebar)
