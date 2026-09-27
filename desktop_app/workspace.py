"""Presentation-only workspace components; no provider calls or persistence."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from .branding import APP_NAME, apply_child_icons

STATES={'queued':'排隊中','running':'執行中','succeeded':'已完成','failed':'執行失敗','cancelled':'已取消','ready':'待批准','executing':'已批准・執行中','expired':'已過期'}
KINDS={'chat':'對話','query':'查詢資料','summarize':'整理重點','rewrite':'改寫文字','query_summarize':'查詢整理'}


class WorkspaceViews:
    def init_workspace(self):
        self.workspace_selection=None
        self.detail_requested=False
        self.detail_window=None
        self.detail_widgets=None
        self.ui_images={}
        for name in ('chat','query','work','result','schedule','notice','issue','settings','send','attach'):
            for variant in ('dark','light'):
                path=Path(__file__).parent/'assets'/'ui'/f'{name}-{variant}.png'
                try:self.ui_images[name,variant]=tk.PhotoImage(master=self.root,file=str(path))
                except tk.TclError:pass  # Text labels remain usable without optional icons.

    def icon_button(self,parent,text,command,icon,style='Quiet.TButton'):
        button=self.button(parent,text,command,style)
        button._workspace_icon=icon
        image=self.ui_images.get((icon,self.appearance.name))
        if image:button.configure(image=image,compound='left')
        return button

    def build_workspace_chat(self):
        page=self.tabs['chat']
        page.columnconfigure(0,weight=1);page.columnconfigure(2,weight=1);page.rowconfigure(0,weight=1)
        self.chat_column=tab=ttk.Frame(page)
        tab.grid(row=0,column=1,sticky='nsew')
        def width(event):page.columnconfigure(1,minsize=min(820,max(1,event.width)),weight=0)
        page.bind('<Configure>',width)
        self.build_assistant_bar(tab)
        self.task_card=ttk.Frame(tab,style='Card.TFrame',padding=(12,8))
        self.task_card.pack(fill='x',pady=(4,8))
        self.task_card_label=ttk.Label(self.task_card,text='準備就緒',style='CardMuted.TLabel')
        self.task_card_label.pack(side='left',fill='x',expand=True)
        self.task_card_action=self.button(self.task_card,'工作詳情',self.open_chat_detail,'Compact.TButton')
        self.task_card_action.pack(side='right')
        self.task_progress=ttk.Progressbar(self.task_card,mode='indeterminate',length=64,style='Workspace.Horizontal.TProgressbar')
        self.task_progress_running=False
        quick=ttk.Frame(tab);quick.pack(fill='x',pady=(0,8))
        for index,(title,kind,icon) in enumerate((('查詢資料','query','query'),('整理文字','summarize','result'),('改寫內容','rewrite','chat'))):
            quick.columnconfigure(index,weight=1,uniform='quick')
            self.icon_button(quick,title,lambda k=kind:self.quick_work(k),icon,'Quick.TButton').grid(row=0,column=index,sticky='ew',padx=(0,8 if index<2 else 0))
        conversation=ttk.Frame(tab);conversation.pack(fill='both',expand=True)
        self.transcript=tk.Text(conversation,height=1,wrap='word',state='disabled',highlightthickness=0,padx=24,pady=16,exportselection=False)
        self.transcript._theme_role='transcript'
        self.transcript.pack(side='left',fill='both',expand=True)
        scrollbar=ttk.Scrollbar(conversation,command=self.transcript.yview)
        scrollbar.pack(side='right',fill='y');self.transcript.configure(yscrollcommand=scrollbar.set)
        for name,settings in {
            'welcome_title':{'font':(self.palette.FONT,20,'bold'),'justify':'center','spacing1':24,'spacing3':12},
            'welcome_body':{'justify':'center','spacing3':8},
            'speaker_user':{'font':(self.palette.FONT,9,'bold'),'lmargin1':16,'lmargin2':16,'spacing1':16,'spacing3':8},
            'speaker_assistant':{'font':(self.palette.FONT,9,'bold'),'lmargin1':16,'lmargin2':16,'spacing1':20,'spacing3':8},
            'body_user':{'lmargin1':16,'lmargin2':16,'rmargin':16,'spacing1':8,'spacing3':16},
            'body_assistant':{'lmargin1':16,'lmargin2':16,'rmargin':16,'spacing1':8,'spacing3':16},
            'separator':{'foreground':self.palette.BORDER,'spacing1':4,'spacing3':8}
        }.items():self.transcript.tag_configure(name,**settings)
        self.composer=ttk.Frame(tab,style='Card.TFrame',padding=8)
        self.composer.pack(fill='x',pady=(8,0))
        self.input=tk.Text(self.composer,height=3,wrap='word',padx=12,pady=8,exportselection=False,undo=True)
        self.input.pack(fill='x')
        self.input.bind('<<Modified>>',self.resize_composer)
        self.input.bind('<Configure>',lambda e:self.resize_composer(force=True))
        options=ttk.Frame(self.composer,style='CardBody.TFrame');options.pack(fill='x',pady=(8,0))
        self.purpose=tk.StringVar(value='一般對話')
        ttk.Combobox(options,textvariable=self.purpose,values=['一般對話','整理重點','改寫文字'],state='readonly',width=9).pack(side='left')
        self.plan_mode=tk.BooleanVar()
        ttk.Checkbutton(options,text='先規劃',variable=self.plan_mode,style='Card.TCheckbutton').pack(side='left',padx=8)
        self.send_button=self.icon_button(options,'送出需求',self.send_chat,'send','Primary.TButton');self.send_button.pack(side='right')
        self.cancel_button=self.button(options,'取消工作',self.cancel_latest,'Compact.TButton');self.cancel_button.pack(side='right',padx=8)
        self.plan_mode.trace_add('write',lambda *args:self.update_composer())
        attachments=ttk.Frame(self.composer,style='CardBody.TFrame');attachments.pack(fill='x',pady=(4,0))
        self.icon_button(attachments,'TXT / CSV',self.upload,'attach','Compact.TButton').pack(side='left')
        self.attachment_label=ttk.Label(attachments,text='可先預覽，再送出',style='CardMuted.TLabel',width=19)
        self.attachment_label.pack(side='left',padx=8)
        self.button(attachments,'移除',self.clear_upload,'Compact.TButton').pack(side='left')
        ttk.Label(attachments,text='Enter 送出 · Shift+Enter 換行',style='CardMuted.TLabel').pack(side='right')
        self._rendered_conversation=None;self._rendered_messages=None

    def resize_composer(self,event=None,force=False):
        if not force and not self.input.edit_modified():return
        self.input.edit_modified(False)
        # Display lines include wrapping; reading draft only, never changing cursor/selection.
        lines=self.input.count('1.0','end','displaylines')
        wanted=max(3,min(6,(lines[0] if lines else 1)))
        if int(self.input.cget('height'))!=wanted:self.input.configure(height=wanted)

    def quick_work(self,kind):
        if kind=='query':self.book.select(self.tabs['query']);return
        self.purpose.set('整理重點' if kind=='summarize' else '改寫文字')
        if not self.input.get('1.0','end-1c').strip():
            self.input.insert('1.0','請整理下列文字的重點：\n' if kind=='summarize' else '請將下列文字改寫得清楚、精簡：\n')
        self.input.focus_set()

    def render_workspace_chat(self):
        self.refresh_profile_picker();self.update_mode()
        messages=self.store.messages(self.conversation)
        key=[(m['role'],m['text']) for m in messages]
        same=self._rendered_conversation==self.conversation
        if same and self._rendered_messages==key:
            self.update_composer();self.refresh_workspace();return
        selection=tuple(str(x) for x in self.transcript.tag_ranges('sel')) if same else ()
        scroll=self.transcript.yview();bottom=scroll[1]>=.98
        top_index=self.transcript.index('@0,0')
        self.transcript.configure(state='normal');self.transcript.delete('1.0','end')
        if not messages:
            self.transcript.insert('end','今天，想先完成哪件事？\n','welcome_title')
            self.transcript.insert('end','從一個小任務開始。\n查找資料、整理重點，或讓文字更清楚。\n','welcome_body')
            self.transcript.insert('end','初次使用？側欄「快速體驗」帶你完成第一件事。\n','welcome_body')
            if (self.store.conversation(self.conversation)['binding'] or {}).get('profile_id')=='demo':
                self.transcript.insert('end','示範模式 · 合成資料 · 不會呼叫公司服務','welcome_body')
        else:
            for message in messages:
                role='user' if message['role']=='user' else 'assistant'
                self.transcript.insert('end',('你  /  需求' if role=='user' else APP_NAME+'  /  回覆')+'\n','speaker_'+role)
                self.transcript.insert('end',message['text']+'\n','body_'+role)
                self.transcript.insert('end','────────────────────\n','separator')
        self.transcript.configure(state='disabled')
        if selection:self.transcript.tag_add('sel',*selection)
        if same and not bottom:self.transcript.yview(top_index)
        else:self.transcript.see('end' if messages else '1.0')
        self._rendered_conversation=self.conversation;self._rendered_messages=key
        self.update_composer();self.refresh_workspace()

    def chat_work(self):
        tasks=[t for t in self.store.tasks() if t['conversation_id']==self.conversation]
        plans=[p for p in self.store.plans() if p['conversation_id']==self.conversation and p['state']=='ready']
        active=next((t for t in tasks if t['state'] in ('queued','running')),None)
        return ('task',active) if active else ('plan',plans[0]) if plans else ('task',tasks[0]) if tasks else (None,None)

    def refresh_workspace(self):
        if not hasattr(self,'task_card_label'):return
        kind,record=self.chat_work()
        state=record['state'] if record else ''
        label=(STATES.get(state,state)+' · '+KINDS.get(record['kind'],record['kind'])) if record else '準備就緒 · 先寫下需求，或選擇上方工作'
        self.task_card_label.configure(text=label,style='CardError.TLabel' if state=='failed' else 'CardMuted.TLabel')
        self.task_card_action.configure(state='normal' if record else 'disabled')
        active=state in ('queued','running')
        if active!=self.task_progress_running:
            if active:self.task_progress.pack(side='right',padx=8);self.task_progress.start(30)
            else:self.task_progress.stop();self.task_progress.pack_forget()
            self.task_progress_running=active
        if self.detail_widgets:self.refresh_detail()

    def open_chat_detail(self):
        kind,record=self.chat_work()
        if record:self.open_work_detail(kind,record['id'])

    def open_work_detail(self,kind,record_id):
        self.workspace_selection=(kind,record_id)
        self.detail_requested=True
        self.place_detail()
        self.refresh_detail()

    def detail_content(self,parent):
        box=ttk.Frame(parent,style='Card.TFrame',padding=16);box.pack(fill='both',expand=True)
        head=ttk.Frame(box,style='CardBody.TFrame');head.pack(fill='x')
        ttk.Label(head,text='工作詳情',style='CardTitle.TLabel').pack(side='left')
        self.button(head,'關閉',self.close_detail,'Compact.TButton').pack(side='right')
        title=ttk.Label(box,style='CardTitle.TLabel',wraplength=258);title.pack(fill='x',pady=(24,8))
        text=tk.Text(box,wrap='word',state='disabled',height=6,width=24,padx=8,pady=12)
        text.pack(fill='both',expand=True)
        action=self.button(box,'查看結果',self.detail_action,'Primary.TButton');action.pack(fill='x',pady=(16,8))
        self.button(box,'回報問題',lambda:self.quick_issue('app'),'Compact.TButton').pack(fill='x')
        self.detail_widgets=(box,title,text,action);self._detail_render=None
        self.appearance.apply(box)

    def place_detail(self,event=None):
        if event is not None and event.widget is not self.root:return
        if not self.detail_requested:return
        wide=self.root.winfo_width()>=1380
        mode='panel' if wide else 'window'
        if getattr(self,'detail_mode',None)==mode and self.detail_widgets:return
        self.destroy_detail_view();self.detail_mode=mode
        if wide:
            self.detail_panel=ttk.Frame(self.main_area,width=300)
            self.detail_panel.pack(side='right',fill='y',before=self.main_content,padx=(0,16),pady=(8,12));self.detail_panel.pack_propagate(False)
            self.detail_content(self.detail_panel)
        else:
            self.detail_window=tk.Toplevel(self.root);apply_child_icons(self.detail_window)
            self.detail_window.title('QA agent · 工作詳情');self.detail_window.geometry('380x500');self.detail_window.minsize(340,360)
            self.detail_window.transient(self.root);self.detail_window.protocol('WM_DELETE_WINDOW',self.close_detail)
            self.detail_content(self.detail_window)
        self.refresh_detail()

    def destroy_detail_view(self):
        if self.detail_widgets:self.detail_widgets[0].destroy()
        self.detail_widgets=None
        for name in ('detail_panel','detail_window'):
            w=getattr(self,name,None)
            if w is not None:
                try:w.destroy()
                except tk.TclError:pass
                setattr(self,name,None)

    def close_detail(self):
        self.detail_requested=False;self.destroy_detail_view();self.workspace_selection=None

    def refresh_detail(self):
        if not self.detail_widgets or not self.workspace_selection:return
        kind,record_id=self.workspace_selection
        record=self.store.plan(record_id) if kind=='plan' else self.store.task(record_id)
        state=record['state'];payload=record['payload'];cid=record['conversation_id']
        lines=['編號：'+record_id,'狀態：'+STATES.get(state,state),'建立時間（UTC）：'+record['created_at'],'']
        if cid:
            convo=self.store.conversation(cid);p=self.profiles.information(payload.get('_binding') or convo['binding'])
            lines+=['對話：'+convo['title'],'助理：'+(p['name'] if p else '舊版／未知歸屬')]
            if p:lines+=['連線版本：'+str((payload.get('_binding') or convo['binding'])['revision'])]
            if convo['source']:lines+=['來源：'+str(convo['source'])]
        else:lines+=['來源：本機查詢／排程，不自動交給助理']
        if 'query_id' in payload:lines+=['模板：'+payload['query_id'],*self.query_conditions(payload['query_id'],payload['parameters'])]
        if kind=='plan':lines+=['修訂：'+str(record['revision']),'請至計畫頁檢視內容並自行批准。']
        if record.get('error'):lines+=['','失敗原因：'+record['error']]
        if state=='cancelled':lines+=['取消不保證已送出的遠端請求停止。']
        body='\n'.join(lines);_,title,text,action=self.detail_widgets
        title.configure(text=STATES.get(state,state)+' · '+KINDS.get(record['kind'],record['kind']))
        if body!=self._detail_render:
            top=text.index('@0,0');ranges=text.tag_ranges('sel')
            chosen=text.get(*ranges) if len(ranges)==2 else ''
            text.configure(state='normal');text.delete('1.0','end');text.insert('1.0',body);text.configure(state='disabled')
            if chosen:
                position=text.search(chosen,'1.0',stopindex='end',exact=True)
                if position:text.tag_add('sel',position,position+'+'+str(len(chosen))+'c')
            text.yview(top);self._detail_render=body
        action.configure(text='檢視計畫' if kind=='plan' else '查看結果',state='normal' if kind=='plan' or (state=='succeeded' and record.get('result') is not None) else 'disabled')

    def detail_action(self):
        kind,record_id=self.workspace_selection
        if kind=='plan':
            self.plans.selection_set(record_id);self.preview_selected_plan();self.book.select(self.tabs['work'])
        else:self.show_result(record_id)

    def workspace_theme(self):
        def update(w):
            name=getattr(w,'_workspace_icon',None)
            image=self.ui_images.get((name,self.appearance.name))
            if image:w.configure(image=image)
            for child in w.winfo_children():update(child)
        update(self.root)
