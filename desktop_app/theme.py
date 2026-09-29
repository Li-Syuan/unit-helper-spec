"""Per-Tcl-interpreter appearance; recolor existing widgets without rebuilding them."""
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk
from .window_chrome import apply_titlebar
from .preferences import COLOR_STYLES

FONT = 'Microsoft JhengHei'
_TOKENS = {
    'dark': dict(BG='#141B27', SURFACE='#1C2635', INK='#EAF0F8', MUTED='#A3B2C5',
        BORDER='#3B4B61', ACCENT='#53C8E8', ACCENT_HOVER='#87DDF2', TINT='#183C4D',
        SIDEBAR='#101722', SIDEBAR_HOVER='#26354A', STRIPE='#243145',
        ERROR='#F08086', SUCCESS='#72D6AA', DISABLED='#8897AB', BUTTON_INK='#10242A',
        WARNING='#F2BC62', RUNNING='#7DA9FF', TEAM='#B29BFF'),
    'light': dict(BG='#F2F5FA', SURFACE='#FFFFFF', INK='#202D42', MUTED='#52647B',
        BORDER='#CED8E6', ACCENT='#086D87', ACCENT_HOVER='#07586D', TINT='#DEF2F8',
        SIDEBAR='#E8EEF7', SIDEBAR_HOVER='#DCE7F4', STRIPE='#EFF4FA',
        ERROR='#AE3542', SUCCESS='#1C7050', DISABLED='#6A7A90', BUTTON_INK='#FFFFFF',
        WARNING='#865300', RUNNING='#305BB6', TEAM='#7150B5'),
}
_STYLE_TOKENS = {
    'violet': {
        'dark': dict(ACCENT='#B29BFF', ACCENT_HOVER='#C9B8FF', TINT='#302943', BUTTON_INK='#201331'),
        'light': dict(ACCENT='#6946B6', ACCENT_HOVER='#553591', TINT='#F0EAFF', BUTTON_INK='#FFFFFF'),
    },
    'forest': {
        'dark': dict(ACCENT='#69CBB5', ACCENT_HOVER='#94DECA', TINT='#173A32', BUTTON_INK='#082C26'),
        'light': dict(ACCENT='#136F60', ACCENT_HOVER='#0D594D', TINT='#E0F3EC', BUTTON_INK='#FFFFFF'),
    },
}


def palette(name, color_style='ocean'):
    if name not in _TOKENS: raise ValueError('不支援的外觀主題。')
    if color_style not in COLOR_STYLES: raise ValueError('不支援的配色風格。')
    colors = dict(_TOKENS[name])
    # Informational notices retain their meaning when the action accent changes.
    colors.update(INFO=colors['ACCENT'], TINT_INFO=colors['TINT'])
    colors.update(_STYLE_TOKENS.get(color_style, {}).get(name, {}))
    return SimpleNamespace(**colors, FONT=FONT)


class Appearance:
    def __init__(self, root, name='dark', color_style='ocean'):
        self.root = root
        root._qa_appearance=self
        root.bind('<Map>',self._mapped,add='+')
        # bind_class uses needcleanup=0 in Python 3.10 Tkinter. Attach its command
        # to this root's cleanup list, or a closed interpreter retains its bitmaps.
        mapped_command=root.bind_class('Toplevel','<Map>',self._mapped,add='+')
        root._tclCommands.append(mapped_command)
        self.style = ttk.Style(root)
        self.style.theme_use('clam')
        self.name = name
        self.color_style = color_style
        self.colors = palette(name, color_style)
        self.configure(name)

    def _mapped(self,event):
        if isinstance(event.widget,(tk.Tk,tk.Toplevel)):
            apply_titlebar(event.widget,self.name,self.colors)

    def configure(self, name, color_style=None):
        color_style = self.color_style if color_style is None else color_style
        c = palette(name, color_style)
        self.name = name
        self.color_style = color_style
        self.colors = c
        root = self.root
        root.configure(background=c.BG)
        # Defaults are scoped to this Tk interpreter and used by future dialogs.
        for key, value in {'background':c.SURFACE, 'foreground':c.INK, 'relief':'flat',
            'borderWidth':0, 'highlightThickness':1, 'highlightBackground':c.BORDER,
            'highlightColor':c.ACCENT, 'insertBackground':c.INK, 'selectBackground':c.TINT,
            'selectForeground':c.INK, 'padX':14, 'padY':10, 'spacing1':3, 'spacing3':5}.items():
            root.option_add('*Text.'+key, value)
        root.option_add('*font', (FONT, 11))
        root.option_add('*Text.font', (FONT, 12))
        root.option_add('*Toplevel.background', c.BG)
        root.option_add('*Canvas.background', c.BG)
        for key,value in {'background':c.SURFACE,'foreground':c.INK,'selectBackground':c.TINT,'selectForeground':c.INK}.items():
            root.option_add('*TCombobox*Listbox.'+key,value)
        s=self.style
        s.configure('.',font=(FONT,11),background=c.BG,foreground=c.INK)
        s.configure('TFrame',background=c.BG)
        s.configure('Surface.TFrame',background=c.SURFACE)
        s.configure('Card.TFrame',background=c.SURFACE,borderwidth=1,relief='solid',bordercolor=c.BORDER,lightcolor=c.BORDER,darkcolor=c.BORDER)
        s.configure('CardBody.TFrame',background=c.SURFACE,borderwidth=0,relief='flat')
        s.configure('CardMuted.TLabel',background=c.SURFACE,foreground=c.MUTED,font=(FONT,10))
        s.configure('CardTitle.TLabel',background=c.SURFACE,foreground=c.INK,font=(FONT,11,'bold'))
        s.configure('CardError.TLabel',background=c.SURFACE,foreground=c.ERROR,font=(FONT,10))
        s.configure('CardSuccess.TLabel',background=c.SURFACE,foreground=c.SUCCESS,font=(FONT,10,'bold'))
        s.configure('CardWarning.TLabel',background=c.SURFACE,foreground=c.WARNING,font=(FONT,10,'bold'))
        s.configure('Warning.TLabel',background=c.BG,foreground=c.WARNING,font=(FONT,10))
        s.configure('Compact.TButton',padding=(8,4),font=(FONT,10))
        s.configure('Card.TCheckbutton',background=c.SURFACE)
        s.configure('Workspace.Horizontal.TProgressbar',troughcolor=c.SURFACE,background=c.RUNNING,borderwidth=0,thickness=3)
        s.configure('TLabel',background=c.BG,foreground=c.INK)
        s.configure('Muted.TLabel',foreground=c.MUTED)
        s.configure('Title.TLabel',font=(FONT,16,'bold'))
        s.configure('Section.TLabel',font=(FONT,11,'bold'))
        s.configure('DialogMark.TLabel',background=c.TINT_INFO,foreground=c.INFO,font=(FONT,20,'bold'),padding=6)
        # Unread is informational, not an error. Severity belongs to the notice itself.
        s.configure('NotificationBadge.TLabel',background=c.TINT_INFO,foreground=c.INFO,padding=(7,3),font=(FONT,10,'bold'))
        for name,color in [('Info',c.INFO),('Success',c.SUCCESS),('Warning',c.WARNING),('Error',c.ERROR),('Neutral',c.MUTED)]:
            s.configure(name+'.ToastBorder.TFrame',background=color)
            s.configure(name+'.ToastMark.TLabel',background=c.SURFACE,foreground=color,font=(FONT,20,'bold'))
        s.configure('Error.DialogMark.TLabel',background=c.SURFACE,foreground=c.ERROR)
        s.configure('Warning.DialogMark.TLabel',background=c.SURFACE,foreground=c.WARNING)
        s.configure('Surface.TLabel',background=c.SURFACE)
        s.configure('Empty.TLabel',background=c.SURFACE,foreground=c.MUTED)
        s.configure('Chip.TLabel',background=c.TINT,foreground=c.ACCENT,padding=(10,5),font=(FONT,10,'bold'))
        s.configure('Status.TLabel',background=c.SURFACE,foreground=c.MUTED,font=(FONT,10),padding=(16,6))
        s.configure('TButton',padding=(12,7),background=c.SURFACE,foreground=c.INK,bordercolor=c.BORDER,
            lightcolor=c.SURFACE,darkcolor=c.SURFACE,borderwidth=1,focuscolor=c.ACCENT)
        s.map('TButton',background=[('disabled',c.BG),('pressed',c.TINT),('active',c.STRIPE)],foreground=[('disabled',c.DISABLED)])
        s.configure('Primary.TButton',background=c.ACCENT,foreground=c.BUTTON_INK,bordercolor=c.ACCENT,
            lightcolor=c.ACCENT,darkcolor=c.ACCENT,font=(FONT,11,'bold'))
        s.map('Primary.TButton',background=[('disabled',c.BORDER),('pressed',c.ACCENT_HOVER),('active',c.ACCENT_HOVER)],
            foreground=[('disabled',c.DISABLED),('!disabled',c.BUTTON_INK)])
        s.configure('Quiet.TButton',background=c.BG,bordercolor=c.BG,lightcolor=c.BG,darkcolor=c.BG,foreground=c.MUTED)
        s.configure('Danger.TButton',foreground=c.ERROR)
        s.configure('Quick.TButton',padding=(12,9),anchor='w',font=(FONT,11))
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
        s.layout('Mode.TRadiobutton',[('Radiobutton.padding',{'sticky':'nswe','children':[('Radiobutton.label',{'sticky':'nswe'})]})])
        s.configure('Mode.TRadiobutton',padding=(12,4),background=c.BG,foreground=c.MUTED,font=(FONT,10,'bold'))
        s.map('Mode.TRadiobutton',background=[('selected',c.TINT),('active',c.STRIPE)],foreground=[('selected',c.ACCENT),('active',c.INK)])
        s.configure('Treeview',rowheight=32,background=c.SURFACE,fieldbackground=c.SURFACE,foreground=c.INK,
            bordercolor=c.BORDER,lightcolor=c.BORDER,darkcolor=c.BORDER,borderwidth=1)
        s.configure('Treeview.Heading',background=c.STRIPE,foreground=c.MUTED,font=(FONT,10,'bold'),padding=(10,8),relief='flat')
        s.map('Treeview',background=[('selected',c.TINT)],foreground=[('selected',c.INK)])
        s.map('Treeview.Heading',background=[('active',c.BORDER)])
        s.configure('TScrollbar',background=c.BORDER,troughcolor=c.BG,arrowcolor=c.MUTED,
            lightcolor=c.BORDER,darkcolor=c.BORDER,bordercolor=c.BG,borderwidth=0,arrowsize=12,relief='flat')
        s.map('TScrollbar',background=[('pressed',c.ACCENT),('active',c.MUTED)],
            lightcolor=[('pressed',c.ACCENT),('active',c.MUTED)],
            darkcolor=[('pressed',c.ACCENT),('active',c.MUTED)],arrowcolor=[('disabled',c.DISABLED),('active',c.INK)])
        s.configure('TSeparator',background=c.BORDER)
        s.configure('TNotebook',background=c.BG,borderwidth=0,tabmargins=(0,0,0,4),bordercolor=c.BORDER,lightcolor=c.BORDER,darkcolor=c.BORDER)
        s.configure('TNotebook.Tab',background=c.BG,foreground=c.MUTED,padding=(14,8),borderwidth=0,bordercolor=c.BORDER,lightcolor=c.BORDER,darkcolor=c.BORDER)
        s.map('TNotebook.Tab',background=[('selected',c.SURFACE),('active',c.STRIPE)],foreground=[('selected',c.ACCENT),('active',c.INK)])
        s.layout('Workspace.TNotebook', [('Notebook.client', {'sticky':'nswe'})])
        s.layout('Workspace.TNotebook.Tab', [])
        s.configure('Workspace.TNotebook',background=c.BG,borderwidth=0,tabmargins=0,bordercolor=c.BG,lightcolor=c.BG,darkcolor=c.BG)
        display=getattr(root,'_qa_display',None)
        if display:
            for name,keys in {
                'Compact.TButton':('padding',),'Chip.TLabel':('padding',),'Status.TLabel':('padding',),
                'TButton':('padding','borderwidth'),'Quick.TButton':('padding',),'TEntry':('padding',),
                'TCombobox':('padding',),'TCheckbutton':('padding',),'TRadiobutton':('padding',),
                'Card.TRadiobutton':('padding',),'Treeview':('rowheight','borderwidth'),
                'Mode.TRadiobutton':('padding',),
                'Treeview.Heading':('padding',),'TScrollbar':('arrowsize',),
                'Workspace.Horizontal.TProgressbar':('thickness',)
            }.items():
                for key in keys:
                    raw=s.configure(name,key)
                    values=raw if isinstance(raw,(tuple,list)) else root.tk.splitlist(str(raw))
                    if values:s.configure(name,**{key:tuple(display.px(float(v)) for v in values) if key=='padding' else display.px(float(values[0]))})
        self.apply(root)

    def apply(self, widget, sidebar=False):
        c=self.colors
        display=getattr(self.root,'_qa_display',None)
        if display:display.scale_widget(widget)
        sidebar=sidebar or getattr(widget,'_theme_role','')=='sidebar'
        role=getattr(widget,'_theme_role','')
        if isinstance(widget,(tk.Tk,tk.Toplevel)):
            widget.configure(background=c.BG)
            apply_titlebar(widget,self.name,c)
        elif isinstance(widget,tk.Text):
            widget.configure(background=c.SURFACE,foreground=c.INK,insertbackground=c.INK,
                selectbackground=c.TINT,selectforeground=c.INK,highlightbackground=c.BORDER,highlightcolor=c.ACCENT)
            for tag,opts in {'welcome_title':{'foreground':c.INK},'welcome_body':{'foreground':c.MUTED},
                'speaker_user':{'foreground':c.ACCENT},'speaker_assistant':{'foreground':c.TEAM},'body_user':{'background':c.TINT},'body_assistant':{'background':c.SURFACE},'separator':{'foreground':c.BORDER}}.items():
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
