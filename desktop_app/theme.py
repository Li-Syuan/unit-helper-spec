"""Shared Tk/ttk visual tokens; no additional GUI dependencies."""
from tkinter import ttk

BG = '#F4F6F5'
SURFACE = '#FFFFFF'
INK = '#22352F'
MUTED = '#65766F'
BORDER = '#DCE5DF'
ACCENT = '#176B50'
ACCENT_HOVER = '#10553F'
TINT = '#E7F3EC'
SIDEBAR = '#172D27'
SIDEBAR_HOVER = '#25443A'
FONT = 'Microsoft JhengHei'

def configure(root):
    root.configure(background=BG)
    for key, value in {'background':SURFACE, 'foreground':INK, 'relief':'flat',
                       'borderWidth':0, 'highlightThickness':1, 'highlightBackground':BORDER,
                       'highlightColor':ACCENT, 'insertBackground':ACCENT,
                       'selectBackground':TINT, 'selectForeground':INK,
                       'padX':14, 'padY':10, 'spacing1':3, 'spacing3':5}.items():
        root.option_add('*Text.'+key, value)
    root.option_add('*Text.font', (FONT, 11))
    style=ttk.Style(root); style.theme_use('clam')
    style.configure('.',font=(FONT,10),background=BG,foreground=INK)
    style.configure('TFrame',background=BG)
    style.configure('Surface.TFrame',background=SURFACE)
    style.configure('TLabel',background=BG,foreground=INK)
    style.configure('Muted.TLabel',foreground=MUTED)
    style.configure('Title.TLabel',font=(FONT,21,'bold'))
    style.configure('Section.TLabel',font=(FONT,12,'bold'))
    style.configure('Surface.TLabel',background=SURFACE)
    style.configure('Chip.TLabel',background=TINT,foreground=ACCENT,padding=(12,6),font=(FONT,9,'bold'))
    style.configure('Status.TLabel',background=SURFACE,foreground=MUTED,font=(FONT,9),padding=(18,8))
    style.configure('TButton',padding=(13,8),background=SURFACE,foreground=INK,bordercolor=BORDER,
                    lightcolor=SURFACE,darkcolor=SURFACE,borderwidth=1,focuscolor=ACCENT)
    style.map('TButton',background=[('active','#EDF3EF'),('pressed',TINT)],foreground=[('disabled','#96A49C')])
    style.configure('Primary.TButton',background=ACCENT,foreground='white',bordercolor=ACCENT,
                    lightcolor=ACCENT,darkcolor=ACCENT,font=(FONT,10,'bold'))
    style.map('Primary.TButton',background=[('disabled','#DCE5DF'),('active',ACCENT_HOVER),('pressed',ACCENT_HOVER)],
              foreground=[('disabled','#75867C'),('!disabled','white')])
    style.configure('Quiet.TButton',background=BG,bordercolor=BG,lightcolor=BG,darkcolor=BG,foreground=MUTED)
    style.configure('Danger.TButton',foreground='#A34439')
    style.configure('Quick.TButton',padding=(18,14),anchor='w',font=(FONT,10,'bold'))
    style.configure('TEntry',padding=8,fieldbackground=SURFACE,bordercolor=BORDER,lightcolor=BORDER,darkcolor=BORDER)
    style.map('TEntry',bordercolor=[('focus',ACCENT)])
    style.configure('TCombobox',padding=7,fieldbackground=SURFACE,background=SURFACE,arrowcolor=MUTED,bordercolor=BORDER)
    style.map('TCombobox',fieldbackground=[('readonly',SURFACE)],selectbackground=[('readonly',SURFACE)],selectforeground=[('readonly',INK)])
    style.configure('TCheckbutton',padding=(0,5),background=BG,indicatorbackground=SURFACE)
    style.map('TCheckbutton',background=[('active',BG)])
    style.configure('TRadiobutton',padding=(4,8),background=BG,indicatorbackground=SURFACE)
    style.configure('Card.TRadiobutton',padding=(16,14),background=SURFACE,font=(FONT,11,'bold'))
    style.map('Card.TRadiobutton',background=[('selected',TINT),('active','#EDF3EF')])
    style.configure('Treeview',rowheight=34,background=SURFACE,fieldbackground=SURFACE,foreground=INK,
                    bordercolor=BORDER,lightcolor=BORDER,darkcolor=BORDER,borderwidth=1)
    style.configure('Treeview.Heading',background='#EDF2EE',foreground=MUTED,font=(FONT,9,'bold'),padding=(10,9),relief='flat')
    style.map('Treeview',background=[('selected',TINT)],foreground=[('selected',INK)])
    style.map('Treeview.Heading',background=[('active','#E1EAE4')])
    style.configure('TScrollbar',background='#CAD8CE',troughcolor=BG,borderwidth=0,arrowsize=12)
    style.layout('Workspace.TNotebook', [('Notebook.client', {'sticky':'nswe'})])
    style.layout('Workspace.TNotebook.Tab', [])
    style.configure('Workspace.TNotebook',background=BG,borderwidth=0,tabmargins=0,bordercolor=BG,lightcolor=BG,darkcolor=BG)
    return style
