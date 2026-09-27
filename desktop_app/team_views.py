"""Assistant directory UI over existing Profiles; never enables capabilities itself."""
import tkinter as tk
from tkinter import ttk
from .display import scroll_frame
from .gateways import GatewayError

ROLE_NAMES={'planner':'規劃','analysis':'分析','review':'覆核','compose':'彙整','rag':'資料查找'}


class TeamViews:
    def build_team(self):
        tab=self.tabs['team'];self.team_render_key=None;self.team_cards={}
        head=ttk.Frame(tab);head.pack(fill='x',pady=(0,12))
        left=ttk.Frame(head);left.pack(side='left',fill='x',expand=True)
        ttk.Label(left,text='把合適的工作，交給合適的助理。',style='Section.TLabel').pack(anchor='w')
        self.team_summary=ttk.Label(left,style='Muted.TLabel');self.team_summary.pack(anchor='w',pady=(5,0))
        self.button(head,'連線設定',lambda:self.book.select(self.tabs['settings']),'Compact.TButton').pack(side='right')
        if not self.groq_trial:
            self.button(head,'＋ 新增助理',self.edit_profile,'Primary.TButton').pack(side='right',padx=8)
        row=ttk.Frame(tab);row.pack(fill='x',pady=(0,10))
        ttk.Label(row,text='搜尋助理').pack(side='left',padx=(0,8))
        self.team_search=tk.StringVar();self.team_search.trace_add('write',lambda *args:self.refresh_team())
        ttk.Entry(row,textvariable=self.team_search).pack(side='left',fill='x',expand=True)
        self.team_filter=tk.StringVar(value='全部')
        select=ttk.Combobox(row,textvariable=self.team_filter,values=['全部','可參與分工','待設定','停用'],state='readonly',width=12)
        select.pack(side='left',padx=(8,0));select.bind('<<ComboboxSelected>>',lambda e:self.refresh_team())
        self.team_message=ttk.Label(tab,style='Muted.TLabel',wraplength=700,justify='left')
        self.team_message.pack(fill='x',pady=(0,8))
        holder=ttk.Frame(tab);holder.pack(fill='both',expand=True)
        self.team_canvas=tk.Canvas(holder,highlightthickness=0,borderwidth=0)
        self.team_canvas.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(holder,command=self.team_canvas.yview);scroll.pack(side='right',fill='y')
        self.team_canvas.configure(yscrollcommand=scroll.set)
        self.team_body=ttk.Frame(self.team_canvas)
        self.team_canvas_item=self.team_canvas.create_window(0,0,window=self.team_body,anchor='nw')
        self.team_canvas.bind('<Configure>',self.resize_team)
        self.team_body.bind('<Configure>',lambda e:self.team_canvas.configure(scrollregion=self.team_canvas.bbox('all')))
        self.root.bind('<MouseWheel>',self.scroll_team,add='+')
        self.team_columns=1
        self.refresh_team()

    def resize_team(self,event=None):
        self.team_canvas.itemconfigure(self.team_canvas_item,width=max(1,self.team_canvas.winfo_width()))
        self.layout_team()

    def scroll_team(self,event):
        if str(event.widget).startswith(str(self.team_body)) or event.widget is self.team_canvas:
            self.team_canvas.yview_scroll(-int(event.delta/120),'units');return 'break'

    def team_state(self,p):
        if not p['enabled']:return '停用','CardMuted.TLabel'
        if p['id']=='demo':return '本機示範','CardMuted.TLabel'
        if not self.groq_trial and self.profiles.data['wire_mode']=='unconfigured' and not p.get('legacy'):
            return '待設定 API 格式','CardWarning.TLabel'
        cap=p.get('workflow',{})
        if cap.get('verified') is True and cap.get('read_only') is True and cap.get('roles'):
            return '可參與分工','CardSuccess.TLabel'
        return '協作能力待驗證','CardWarning.TLabel'

    def refresh_team(self):
        if not hasattr(self,'team_body'):return
        profiles=self.profiles.items();search=self.team_search.get().strip().casefold();filter_=self.team_filter.get()
        profiles=sorted(profiles,key=lambda p:(not p['enabled'],p['id']=='demo',0 if 'planner' in p.get('workflow',{}).get('roles',[]) else 1 if p.get('workflow',{}).get('roles') else 2))
        key=(str(profiles),self.profiles.data['wire_mode'],search,filter_)
        if key==self.team_render_key:return
        self.team_render_key=key
        count=sum(self.team_state(p)[0]=='可參與分工' for p in profiles)
        self.team_summary.configure(text=f'{len(profiles)} 位助理 · {count} 位可參與分工')
        self.team_message.configure(text=('Groq 試用：同一模型的隔離角色，用於測試分工流程；不是公司不同 assistant ID。' if self.groq_trial else
            '公司平台建立助理 → 新增 assistant ID 與用途 → 設定分工角色 → 公司驗證後加入 Plan。'))
        for child in self.team_body.winfo_children():child.destroy()
        self.team_cards={}
        for p in profiles:
            state,style=self.team_state(p);roles=p.get('workflow',{}).get('roles',[])
            role_text=' / '.join(ROLE_NAMES.get(r,r) for r in roles) or '一般對話'
            if search and search not in (p['name']+' '+p['notes']+' '+role_text+' '+p['assistant_id']).casefold():continue
            if filter_=='可參與分工' and state!='可參與分工':continue
            if filter_=='停用' and p['enabled']:continue
            if filter_=='待設定' and state not in ('待設定 API 格式','協作能力待驗證'):continue
            card=ttk.Frame(self.team_body,style='Card.TFrame',padding=16)
            top=ttk.Frame(card,style='Surface.TFrame');top.pack(fill='x')
            icon=next(({'planner':'work','analysis':'query','review':'todo','compose':'result','rag':'query'}[r] for r in roles),'team')
            image=self.ui_images.get((icon,self.appearance.name))
            avatar=ttk.Label(top,image=image or '',style='Surface.TLabel');avatar._workspace_icon=icon;avatar.pack(side='left',padx=(0,10))
            name=ttk.Label(top,text=p['name'],style='CardTitle.TLabel',wraplength=270);name.pack(side='left',fill='x',expand=True)
            ttk.Label(card,text=state,style=style).pack(anchor='w',pady=(8,3))
            ttk.Label(card,text=role_text,style='CardMuted.TLabel').pack(anchor='w')
            preview=p['notes'] or '用途尚未填寫，建議補上專長與適用情境。'
            notes=ttk.Label(card,text=preview[:140]+('…（查看完整設定）' if len(preview)>140 else ''),style='Surface.TLabel',wraplength=300,justify='left')
            notes.pack(fill='x',pady=(10,12))
            row=ttk.Frame(card,style='Surface.TFrame');row.pack(fill='x')
            chat=self.button(row,'開始對話',lambda pid=p['id']:self.team_chat(pid),'Compact.TButton');chat.pack(side='left')
            if not p['enabled']:chat.configure(state='disabled')
            info=self.button(row,'查看設定',lambda pid=p['id']:self.team_details(pid),'Quiet.TButton');info.pack(side='right')
            if 'planner' in roles and state=='可參與分工':
                self.button(card,'用此助理規劃工作',lambda pid=p['id']:self.team_plan(pid),'Compact.TButton').pack(fill='x',pady=(10,0))
            self.team_cards[p['id']]={'frame':card,'name':name,'notes':notes,'chat':chat,'info':info,'state':state}
        if not self.team_cards:
            ttk.Label(self.team_body,text='沒有符合條件的助理。請調整搜尋，或新增公司助理。',style='Muted.TLabel').grid(row=0,column=0,pady=30)
        self.appearance.apply(self.team_body);self.layout_team()

    def layout_team(self):
        if not hasattr(self,'team_body'):return
        width=self.team_canvas.winfo_width()
        columns=2 if width>=self.display.px(780) else 1
        self.team_columns=columns
        for col in range(2):self.team_body.columnconfigure(col,weight=1 if col<columns else 0,minsize=0,uniform='cards' if col<columns else '')
        for index,parts in enumerate(self.team_cards.values()):
            parts['frame'].grid(row=index//columns,column=index%columns,sticky='nsew',padx=self.display.px(4),pady=self.display.px(5))
            wrap=max(self.display.px(200),width//columns-self.display.px(60))
            parts['notes'].configure(wraplength=wrap);parts['name'].configure(wraplength=max(120,wrap-self.display.px(45)))

    def team_chat(self,pid):
        binding=self.profiles.snapshot(pid)
        self.profiles.validate(binding);self.next_binding=binding
        self.new_chat()  # Preserves the previous conversation's draft; never sends it.

    def team_plan(self,pid):
        self.profiles.validate_workflow(self.profiles.workflow_binding(pid),'planner')
        self.team_chat(pid);self.refresh_workflow_catalog()
        index=next(i for i,p in enumerate(self.workflow_planners) if p['id']==pid)
        self.workflow_planner.current(index);self.workflow_mode.set('workflow');self.change_workflow_mode()

    def team_details(self,pid):
        from .branding import apply_child_icons
        p=next((p for p in self.profiles.items() if p['id']==pid),None)
        if p is None:raise GatewayError('此助理已不存在，請重新整理清單。')
        w=tk.Toplevel(self.root);apply_child_icons(w);w.title('助理設定 · '+p['name']);self.display.size_window(w,650,540,(480,380))
        body=scroll_frame(w,padding=20);body.pack(fill='both',expand=True)
        ttk.Label(body,text=p['name'],style='Title.TLabel',wraplength=500).pack(anchor='w',pady=(0,12))
        content='assistant ID：'+p['assistant_id']+'\n連線版本：'+str(p['revision'])+'\n狀態：'+self.team_state(p)[0]+'\n用途：'+(p['notes'] or '未填寫')
        text=tk.Text(body,height=6,wrap='word');text.pack(fill='x');text.insert('1.0',content);text.configure(state='disabled')
        roles=p.get('workflow',{}).get('roles',[])
        ttk.Label(body,text='分工角色：'+('、'.join(ROLE_NAMES[r] for r in roles) or '尚未設定'),wraplength=500).pack(anchor='w',pady=10)
        if self.groq_trial or pid=='demo':
            ttk.Label(body,text='這是固定的試用／示範助理。公司助理請從正式入口新增。',wraplength=500,style='Muted.TLabel').pack(anchor='w')
        else:
            def action(fn):
                self.profile_table.selection_set(pid);w.destroy();fn()
            self.button(body,'編輯名稱、ID 與用途',lambda:action(lambda:self.edit_profile(pid))).pack(fill='x',pady=4)
            self.button(body,'設定分工角色',lambda:action(self.edit_workflow_capability)).pack(fill='x',pady=4)
            row=ttk.Frame(body);row.pack(fill='x',pady=4)
            self.button(row,'設為預設',lambda:action(self.default_profile),'Compact.TButton').pack(side='left')
            self.button(row,'停用' if p['enabled'] else '啟用',lambda:action(self.toggle_profile),'Compact.TButton').pack(side='right')
            ttk.Label(body,text='新增角色不等於通過驗證。公司接線者須完成 API、隔離與唯讀能力測試。',style='Muted.TLabel',wraplength=500).pack(fill='x',pady=10)
        self.button(w,'關閉',w.destroy,'Compact.TButton').pack(side='bottom',pady=10)
        self.appearance.apply(w)
        return w
