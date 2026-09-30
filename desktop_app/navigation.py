"""Collapsible native navigation; changes presentation only, never recreates pages."""
import tkinter as tk
from tkinter import ttk
from .preferences import load_preferences,update_preferences
from .branding import APP_NAME
from . import __version__


class Tooltip:
    def __init__(self,app,widget,text):
        self.app=app;self.widget=widget;self.text=text;self.window=None;self.timer=None
        widget.bind('<Enter>',self.schedule,add='+');widget.bind('<FocusIn>',self.schedule,add='+')
        for event in ('<Leave>','<FocusOut>','<ButtonPress>','<Destroy>'):widget.bind(event,self.hide,add='+')
    def schedule(self,event=None):
        self.hide();self.timer=self.widget.after(450,self.show)
    def show(self):
        self.timer=None
        if not self.widget.winfo_viewable():return
        w=self.window=tk.Toplevel(self.app.root);w.withdraw();w.overrideredirect(True);w.attributes('-topmost',True)
        ttk.Label(w,text=self.text() if callable(self.text) else self.text,style='Chip.TLabel').pack()
        self.app.appearance.apply(w);w.update_idletasks()
        x=self.widget.winfo_rootx()+self.widget.winfo_width()+8;y=self.widget.winfo_rooty()
        from .display import work_area
        ax,ay,aw,ah=work_area(self.widget)
        w.geometry(f'+{min(x,ax+aw-w.winfo_reqwidth()-8)}+{min(y,ay+ah-w.winfo_reqheight()-8)}');w.deiconify()
    def hide(self,event=None):
        if self.timer is not None:
            self.widget.after_cancel(self.timer);self.timer=None
        if self.window is not None:self.window.destroy();self.window=None


class Navigation:
    def __init__(self,app,surface):
        self.app=app;self.tooltips=[]
        self.collapsed=load_preferences(app.preferences_path).get('sidebar_collapsed') is True
        side=self.side=tk.Frame(surface,width=224);side._theme_role='sidebar';side.pack(side='left',fill='y');side.pack_propagate(False)
        self.expanded=[];self.buttons=[]
        identity=getattr(app,'identity',{})
        identity_text='已登入 · '+identity['name'] if identity.get('mode')=='company' else '本機身分 · 非 AD'
        self.identity=tk.Label(side,text=identity_text+'  /  '+__version__,font=(app.palette.FONT,10),anchor='w',wraplength=190)
        self.identity.pack(side='bottom',fill='x',padx=16,pady=(4,12));self.expanded.append(self.identity)
        self.help=self.button(side,'說明與關於','help',lambda:app.show_help('快速開始'));self.help.pack(side='bottom',fill='x',padx=10,pady=2)
        self.author=self.button(side,'作者','team',lambda:app.show_author(self.author));self.author.pack(side='bottom',fill='x',padx=10,pady=2)
        self.options=self.button(side,'待回答的選項','work',app.resume_form);self.options.pack(side='bottom',fill='x',padx=10,pady=2)
        self.brand=tk.Frame(side);self.brand.pack(fill='x',padx=14,pady=(14,8))
        app.brand_image_label=tk.Label(self.brand,image=app.brand_icon or '');app.brand_image_label.pack(side='left',padx=(0,8))
        self.brand_title=tk.Label(self.brand,text=APP_NAME,font=(app.palette.FONT,13,'bold'));self.brand_title._theme_role='brand';self.brand_title.pack(side='left')
        self.toggle=self.button(side,'收合側欄','collapse',self.toggle_sidebar);self.toggle.pack(fill='x',padx=10,pady=(0,4))
        self.new=self.button(side,'開始新對話','new',app.new_chat);self.new._theme_role='new_chat';self.new.pack(fill='x',padx=10,pady=(0,8))
        app.routes=[('chat','對話','從需求開始，一起完成工作。'),('team','助理團隊','選擇助理與安排分工。'),
            ('todo','我的待辦','追蹤個人工作。'),('query','查資料','使用核准查詢。'),('work','計畫與任務','核對計畫與執行紀錄。'),
            ('result','查詢結果','檢視與匯出資料。'),('schedule','自動工作','管理已核准的自動工作。'),
            ('activity','活動紀錄','查看工作狀態。'),('notice','通知','查看新結果與執行狀態。'),
            ('settings','設定','管理連線與外觀。'),('issue','問題回報','保存問題與需求。')]
        app.nav_buttons={};app.more_tools=ttk.Frame(side)
        for key in ('chat','team','todo','schedule','activity','notice','query','result','work','settings','issue'):
            title=next(title for name,title,_ in app.routes if name==key)
            parent=app.more_tools if key in ('query','result','work') else side
            button=self.button(parent,title,key,lambda key=key:app.book.select(app.tabs[key]))
            button.pack(side='bottom' if key in ('settings','issue') else 'top',fill='x',padx=10,pady=1)
            app.nav_buttons[key]=button
        self.more=self.button(side,'更多工具','more',app.toggle_more_tools);self.more.pack(fill='x',padx=10,pady=(5,4))
        self.divider=ttk.Separator(side);self.divider.pack(fill='x',padx=16,pady=8);self.expanded.append(self.divider)
        self.history_head=tk.Frame(side);self.history_head.pack(fill='x',padx=16)
        tk.Label(self.history_head,text='最近對話',font=(app.palette.FONT,10)).pack(side='left')
        app.button(self.history_head,'管理',app.manage_conversations,'Compact.TButton').pack(side='right')
        self.expanded.append(self.history_head)
        self.history_box=ttk.Frame(side);self.history_box.pack(fill='both',expand=True,padx=12,pady=(5,8));self.expanded.append(self.history_box)
        app.history=tk.Listbox(self.history_box,height=2,width=16,exportselection=False,relief='flat',bd=0,highlightthickness=0,font=(app.palette.FONT,10),activestyle='none')
        app.history.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(self.history_box,command=app.history.yview);scroll.pack(side='right',fill='y');app.history.configure(yscrollcommand=scroll.set)
        app.history.bind('<Button-3>',app.history_context);app.history.bind('<<ListboxSelect>>',lambda e:app.safe(app.choose_chat))
        self.packed=[]

    def button(self,parent,title,icon,action):
        a=self.app
        button=tk.Button(parent,text='  '+title,anchor='w',font=(a.palette.FONT,11),relief='flat',bd=0,padx=10,pady=5,
                         compound='left',cursor='hand2',takefocus=True,command=lambda:a.safe(action))
        button._workspace_icon=icon;button._nav_title=title
        button.bind('<Enter>',lambda e:button.configure(bg=a.palette.SIDEBAR_HOVER),add='+')
        button.bind('<Leave>',lambda e:a.route_changed() if hasattr(a,'tabs') else None,add='+')
        self.buttons.append(button);self.tooltips.append(Tooltip(a,button,lambda:button._nav_title));return button

    def initialize(self):
        self.packed=[(w,w.pack_info()) for w in self.side.pack_slaves()]
        self.apply()

    def toggle_sidebar(self):
        if hasattr(self.app,'author_popover'):self.app.author_popover.close()
        self.collapsed=not self.collapsed;self.apply()
        try:update_preferences(self.app.preferences_path,{'sidebar_collapsed':self.collapsed})
        except OSError:self.app.status.set('側欄已切換；偏好保存失敗，重開可能恢復原樣。')

    def apply(self):
        a=self.app
        more_open=bool(a.more_tools.winfo_manager())
        for t in self.tooltips:t.hide()
        self.side.configure(width=a.display.px(68 if self.collapsed else 224))
        # Keep instances and their contents. Pack from the original order on expansion.
        for w,info in self.packed:w.pack_forget()
        a.more_tools.pack_forget()
        for w,info in self.packed:
            if self.collapsed and w in self.expanded:continue
            opts={k:v for k,v in info.items() if k!='in'}
            if self.collapsed:opts['padx']=a.display.px(7)
            w.pack(**opts)
        if more_open and not self.collapsed:a.more_tools.pack(fill='x',after=self.more)
        if self.collapsed:
            self.brand_title.pack_forget()
            a.brand_image_label.pack_configure(side='top',anchor='center',padx=0)
        else:
            self.brand_title.pack(side='left')
            a.brand_image_label.pack_configure(side='left',anchor='center',padx=(0,a.display.px(8)))
        self.toggle._nav_title='展開側欄' if self.collapsed else '收合側欄'
        for b in self.buttons:
            has_icon=(b._workspace_icon,a.appearance.name) in a.ui_images
            text=('' if has_icon else b._nav_title[:2]) if self.collapsed else '  '+b._nav_title
            b.configure(image=a.ui_images.get((b._workspace_icon,a.appearance.name),''),
                        text=text,anchor='center' if self.collapsed else 'w')
        self.toggle._workspace_icon='expand' if self.collapsed else 'collapse'
        a.workspace_theme();a.route_changed()
        if hasattr(a,'notification_presenter'):a.notification_presenter.update(a.store.notifications())

    def close(self):
        if hasattr(self.app,'author_popover'):self.app.author_popover.close()
        for tip in self.tooltips:tip.hide()
