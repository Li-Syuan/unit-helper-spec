"""Conversation action cards and a selectable local timeline; no model-history writes."""
import copy
import uuid
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from .core import TAIPEI
from .query_schema import find_template, parameters, initial_values, describe, date_mapping

ACTION_NAMES={'query':'查詢資料','schedule':'只查詢','report':'查詢並整理日報','choose':'選擇工作','plan':'確認計畫'}
FREQUENCIES={'daily':'每日','weekly':'每週'}
DATE_MODES={'previous_day':'每次查前一日','literal':'使用固定日期'}
WEEKDAYS=['星期一','星期二','星期三','星期四','星期五','星期六','星期日']
STATUS_NAMES={'expired':'已過期／修訂已失效','parsing':'整理條件中','draft':'待確認','submitted':'已受理','queued':'等待中','running':'執行中','succeeded':'完成','failed':'失敗','cancelled':'已取消','enabled':'已啟用','disabled':'已暫停','ready':'待批准','executing':'執行中'}


def local_time(value):
    if not value:return ''
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(TAIPEI).strftime('%Y-%m-%d %H:%M')+' 台北'
    except (ValueError,TypeError):return str(value)


class ActionViews:
    def toggle_more_tools(self):
        if self.more_tools.winfo_manager():self.more_tools.pack_forget()
        else:self.more_tools.pack(fill='x',after=self.nav_buttons['notice'])

    def toggle_composer_options(self):
        if self.more_options.winfo_manager():self.more_options.pack_forget()
        else:self.more_options.pack(fill='x',pady=4)

    def update_selection_actions(self,event=None):
        chosen=bool(self.transcript.tag_ranges('sel'))
        if chosen:self.work_toolbar.pack(in_=self.chat_column,fill='x',before=self._action_conversation_widget)
        else:self.work_toolbar.pack(in_=self.more_options,fill='x')
        for control in (self.selection_todo,self.selection_handoff):
            if chosen:control.pack(side='right',padx=4)
            else:control.pack_forget()

    def build_entry_tiles(self,parent):
        for column,(label,kind) in enumerate((('試查一筆資料','query'),('整理一段文字','text'),('我自己輸入','own'))):
            parent.columnconfigure(column,weight=1,uniform='entries')
            self.button(parent,label,lambda kind=kind:self.use_entry(kind),'Compact.TButton').grid(row=0,column=column,sticky='ew',padx=3,pady=5)

    def use_entry(self,kind):
        if kind=='own':self.input.focus_set();return
        if self.editing_plan:raise ValueError('請先保存或退出計畫修改。')
        if self.input.get('1.0','end-1c').strip() or self.attachment:
            self.next_binding=self.store.conversation(self.conversation)['binding'];self.new_chat()
        self.purpose.set('一般對話');self.plan_mode.set(False)
        self.input.insert('1.0','查昨天 A 類數量合計' if kind=='query' else '請整理以下虛構會議筆記的重點與待辦：\n小林週五前完成測試；小王週三確認需求；下週一再一起核對結果。')
        self.input.focus_set();self.draft_changed()
        self.status.set('範例已填入；核對後按送出。')

    def route_action(self,text):
        from .intent_drafts import intent_hint, example_query, can_parse_actions
        hint=intent_hint(text)
        if hint is None:return False
        scheduled=any(word in text for word in ('每天','每日','每週','每周','排程','定時'))
        kind=hint if hint in ('report','choose','schedule') else 'schedule' if scheduled else 'query'
        spec=None
        if text=='查昨天 A 類數量合計' and self.config['query_mode']=='demo':spec=example_query()
        for existing in reversed(self.actions.list(self.conversation)):
            if existing['request']==text and existing['kind']==kind and existing['state']=='draft':
                self.show_action(existing['id']);self.show_chat();return True
        record=self.start_action(kind,text,spec)
        binding=record.get('binding') or {}
        if (spec is None and kind in ('query','schedule','report') and self.groq_trial
                and can_parse_actions(self.groq_trial,binding) and self.config['query_mode']=='demo'):
            self.parse_action(record)
        return True

    def start_action(self,kind,request='',spec=None):
        request=request or ('設定自動工作' if kind in ('schedule','report') else '查詢資料')
        spec=copy.deepcopy(spec or {})
        if kind in ('schedule','report'):
            spec.setdefault('name','每日合成資料日報' if kind=='report' else '定期查詢')
            spec.setdefault('frequency','daily');spec.setdefault('weekday',0);spec.setdefault('date_mode','previous_day')
        record=self.actions.create(self.conversation,kind,request,spec=spec)
        self.action_selected[self.conversation]=record['id']
        self.show_action(record['id']);self.show_chat();self.book.select(self.tabs['chat'])
        self.status.set('請核對確認卡；尚未查詢或啟用。')
        return self.actions.get(record['id'])

    def build_action_panel(self,parent,conversation):
        self.action_selected={};self.action_id=None;self.action_record=None;self.action_loading=False
        self.action_vars={};self.action_param_vars={};self.action_panel_key=None;self.action_collapsed=False
        self.timeline_events=[];self.timeline_cid=None;self.action_busy=set();self.action_run_deadlines={}
        self.action_panel=ttk.Frame(parent,style='Card.TFrame',padding=8)
        self.action_panel.pack(side='bottom',fill='x',before=conversation)
        header=ttk.Frame(self.action_panel);header.pack(fill='x')
        self.action_title=ttk.Label(header,text='確認工作',style='Section.TLabel');self.action_title.pack(side='left')
        self.action_toggle=self.button(header,'收合',self.toggle_action_panel,'Compact.TButton');self.action_toggle.pack(side='right')
        self.action_boundary=ttk.Label(self.action_panel,style='Muted.TLabel',wraplength=650)
        self.action_boundary.pack(fill='x',pady=(2,3))
        self.action_buttons=ttk.Frame(self.action_panel);self.action_buttons.pack(side='bottom',fill='x',pady=(6,0))
        self.action_consent_area=ttk.Frame(self.action_panel)
        self.action_preview_button=self.button(self.action_buttons,'預覽',self.preview_action,'Compact.TButton')
        self.action_confirm_button=self.button(self.action_buttons,'確認執行',self.confirm_action,'Primary.TButton')
        self.action_edit_button=self.button(self.action_buttons,'修改計畫',self.edit_action_plan,'Compact.TButton')
        self.action_cancel_button=self.button(self.action_buttons,'取消',self.cancel_action,'Compact.TButton')
        self.action_retry_button=self.button(self.action_buttons,'修改條件再試',self.retry_query_action,'Compact.TButton')
        self.action_copy_button=self.button(self.action_buttons,'複製',self.copy_action_result,'Compact.TButton')
        self.action_export_button=self.button(self.action_buttons,'匯出',self.export_action_result,'Compact.TButton')
        self.action_handoff_button=self.button(self.action_buttons,'整理這份資料',self.handoff_action_result,'Compact.TButton')
        self.action_result_button=self.button(self.action_buttons,'完整結果',self.action_result,'Compact.TButton')
        self.action_schedule_button=self.button(self.action_buttons,'設為自動工作',self.action_to_schedule,'Compact.TButton')
        self.action_run_button=self.button(self.action_buttons,'現在測試一次',self.run_action_now,'Compact.TButton')
        self.action_pause_button=self.button(self.action_buttons,'暫停',self.pause_action_schedule,'Compact.TButton')
        holder=self.action_scroll=ttk.Frame(self.action_panel);holder.pack(fill='x')
        canvas=self.action_canvas=tk.Canvas(holder,height=220,highlightthickness=0)
        canvas.pack(side='left',fill='both',expand=True)
        scrollbar=ttk.Scrollbar(holder,command=canvas.yview);scrollbar.pack(side='right',fill='y');canvas.configure(yscrollcommand=scrollbar.set)
        self.action_body=ttk.Frame(canvas);window=canvas.create_window((0,0),window=self.action_body,anchor='nw')
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        self.root.bind('<FocusIn>',self.reveal_action_field,add='+')
        self.action_body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        self.action_panel.pack_forget();self._action_conversation_widget=conversation

    def reveal_action_field(self,event):
        widget=event.widget
        if not str(widget).startswith(str(self.action_body)):return
        top=widget.winfo_rooty()-self.action_body.winfo_rooty();height=self.action_body.winfo_height();visible=self.action_canvas.winfo_height()
        start=self.action_canvas.yview()[0]*height
        if top<start:self.action_canvas.yview_moveto(top/max(1,height))
        elif top+widget.winfo_height()>start+visible:self.action_canvas.yview_moveto((top+widget.winfo_height()-visible)/max(1,height))

    def toggle_action_panel(self):
        self.action_collapsed=not self.action_collapsed
        if self.action_collapsed:self.action_scroll.pack_forget()
        else:self.action_scroll.pack(fill='x')
        self.action_toggle.configure(text='展開' if self.action_collapsed else '收合')

    def show_action(self,action_id):
        record=self.actions.snapshot(action_id)
        cid=record['conversation_id']
        if cid!=self.conversation:
            self.stash_draft();self.conversation=cid;self.restore_draft();self.refresh_history();self.show_chat()
        self.action_selected[cid]=action_id
        self.action_id=action_id;self.action_record=record;self.action_panel_key=None
        self.action_collapsed=False;self.action_scroll.pack(fill='x');self.action_toggle.configure(text='收合')
        self.action_panel.pack(side='bottom',fill='x',before=self._action_conversation_widget)
        self.populate_action(record);self.book.select(self.tabs['chat'])

    def populate_action(self,record):
        self.action_loading=True
        try:
            for child in self.action_body.winfo_children():child.destroy()
            for child in self.action_consent_area.winfo_children():child.destroy()
            self.action_consent_area.pack_forget()
            self.action_vars={};self.action_param_vars={};self.action_record=record
            self.action_panel_key=(record['id'],record['revision'],record.get('status'),str(record.get('result')),record.get('error'))
            kind=record['kind'];spec=record.get('spec') or {};draft=record['state']=='draft' and (kind!='plan' or record.get('status') in ('ready','draft','expired',None))
            self.action_title.configure(text=ACTION_NAMES.get(kind,kind)+' · '+STATUS_NAMES.get(record.get('status'),record.get('status','待確認')))
            binding=record.get('binding');profile=self.profiles.information(binding) if binding else None
            destination=(profile or {}).get('name','未知／停用助理')
            boundary=('整理助理：'+destination+'；只傳送彙總資料，不含逐筆資料。' if kind=='report' else '不傳送資料給助理；只執行核准查詢。' if kind in ('query','schedule') else '目的助理：'+destination+'；僅送出本卡確認的內容。' if kind=='plan' else '選擇工作後，仍須核對並確認。')
            self.action_boundary.configure(text=('尚未執行。' if draft else '')+boundary)
            if kind=='choose':
                ttk.Label(self.action_body,text='請選擇這次要做的工作；選擇後仍須核對並確認。').pack(anchor='w',pady=5)
                choices=ttk.Frame(self.action_body);choices.pack(fill='x')
                for name,title in [('query','查一次'),('schedule','定期查詢'),('report','查詢並整理日報')]:
                    if name=='report' and not self.groq_trial:continue
                    self.button(choices,title,lambda name=name:self.change_action_kind(name),'Compact.TButton').pack(side='left',padx=3)
                self.button(choices,'一般討論',self.discuss_action,'Compact.TButton').pack(side='left',padx=3)
            elif kind=='plan':
                plan=record.get('plan') or self.store.plan(spec['plan_id'])
                ttk.Label(self.action_body,text='修訂 '+str(spec['plan_revision'])+' · 核對後批准，只執行這份修訂。',wraplength=650).pack(anchor='w')
                view=tk.Text(self.action_body,height=5,wrap='word');view.pack(fill='x')
                payload=plan.get('payload',{});binding=payload.get('_binding') or record.get('binding');profile=self.profiles.information(binding)
                lines=['目的助理：'+(profile['name'] if profile else '未知／停用'), '確認期限：'+local_time(plan['expires_at']),'',payload.get('text','')]
                if payload.get('query_id'):
                    lines+=self.query_conditions(payload['query_id'],payload.get('parameters',{}))
                view.insert('1.0','\n'.join(lines));view.configure(state='disabled')
            elif draft:
                if kind in ('schedule','report'):
                    row=ttk.Frame(self.action_body);row.pack(fill='x')
                    ttk.Label(row,text='處理方式').pack(side='left')
                    for name,title in [('schedule','只查詢'),('report','查詢並整理日報')]:
                        if name=='report' and not self.groq_trial:continue
                        self.button(row,title,lambda name=name:self.change_action_kind(name),'Compact.TButton').pack(side='left',padx=3)
                self.action_catalog=self.queries.catalog()
                self.action_query_name=tk.StringVar(value=next((q['name'] for q in self.action_catalog if q['id']==spec.get('query_id')),''))
                picker=ttk.Combobox(self.action_body,textvariable=self.action_query_name,values=[q['name'] for q in self.action_catalog],state='readonly')
                picker.pack(fill='x',pady=4);picker.bind('<<ComboboxSelected>>',lambda e:self.safe(self.action_query_changed))
                fields=ttk.Frame(self.action_body);fields.pack(fill='x');fields.columnconfigure(1,weight=1)
                template=next((q for q in self.action_catalog if q['id']==spec.get('query_id')),None)
                if template:
                    mapping=date_mapping(template)
                    for row,(key,field) in enumerate(template['parameters'].items()):
                        if kind in ('schedule','report') and spec.get('date_mode')=='previous_day' and mapping and key in mapping.values():continue
                        value=spec.get('parameters',{}).get(key,'');value='是' if value is True else '否' if value is False else str(value)
                        variable=tk.StringVar(value=value);self.action_param_vars[key]=variable
                        ttk.Label(fields,text=field['label']).grid(row=row,column=0,sticky='w',padx=(0,12))
                        opts=field.get('options') if field['type']=='single_choice' else ['是','否'] if field['type']=='boolean' else None
                        entry=ttk.Combobox(fields,textvariable=variable,values=opts,state='readonly') if opts else ttk.Entry(fields,textvariable=variable)
                        entry.grid(row=row,column=1,sticky='ew',pady=2);variable.trace_add('write',self.action_edited)
                if kind in ('schedule','report'):
                    mapping=date_mapping(template) if template else None
                    settings=[('name','名稱',spec.get('name','定期查詢'),None),('time_hhmm','台北時間',spec.get('time_hhmm',''),None)]
                    if kind=='schedule':
                        frequency=spec.get('frequency','daily');mode=spec.get('date_mode','previous_day' if mapping else 'literal')
                        settings.append(('frequency','頻率',FREQUENCIES.get(frequency,''),list(FREQUENCIES.values())))
                        if frequency=='weekly':
                            weekday=spec.get('weekday',0)
                            settings.append(('weekday','星期',WEEKDAYS[weekday] if type(weekday) is int and 0<=weekday<7 else '',WEEKDAYS))
                        settings.append(('date_mode','查詢日期',DATE_MODES.get(mode,''),list(DATE_MODES.values()) if mapping else [DATE_MODES['literal']]))
                    for key,title,value,choices in settings:
                        row=ttk.Frame(self.action_body);row.pack(fill='x',pady=2)
                        ttk.Label(row,text=title,width=12).pack(side='left')
                        var=tk.StringVar(value=str(value));self.action_vars[key]=var
                        entry=ttk.Combobox(row,textvariable=var,values=choices,state='readonly') if choices else ttk.Entry(row,textvariable=var)
                        entry.pack(side='left',fill='x',expand=True)
                        var.trace_add('write',lambda *args,key=key:self.action_schedule_edited(key))
                    ttk.Label(self.action_body,text=('每日查前一日。' if kind=='report' else '')+'程式須保持開啟；確認後不會立即執行，可按「現在測試一次」。',wraplength=650,style='Muted.TLabel').pack(anchor='w')
                if kind=='report':
                    if spec.get('frequency')!='daily' or spec.get('date_mode')!='previous_day':
                        self.button(self.action_body,'採用每日查前一日',self.adopt_report_rule,'Compact.TButton').pack(anchor='w',pady=4)
                    self.action_consent=tk.BooleanVar(value=False)
                    self.action_consent_area.pack(side='bottom',fill='x',before=self.action_scroll)
                    self.action_consent_checkbox=ttk.Checkbutton(self.action_consent_area,text='我確認每日查前一日，授權每次將筆數與精確合計交給 Groq 整理。\n只傳彙總，不傳逐筆資料；可隨時暫停。',variable=self.action_consent,command=self.action_consent_changed)
                    self.action_consent_checkbox.pack(anchor='w',pady=3)
            self.action_feedback=tk.StringVar(value='解析中；尚未執行。' if record['id'] in self.action_busy else record.get('error') or '請核對條件，再確認。' if draft else record.get('error') or '')
            if draft or record.get('error'):ttk.Label(self.action_body,textvariable=self.action_feedback,wraplength=650,style='Muted.TLabel').pack(anchor='w',pady=5)
            if not draft:self.action_summary(record)
            for button in self.action_buttons.winfo_children():button.pack_forget()
            if draft:
                if kind!='choose':
                    self.action_confirm_button.pack(side='left',padx=5)
                    self.action_confirm_button.configure(text='確認啟用' if kind in ('schedule','report') else '批准此修訂' if kind=='plan' else '確認查詢',state='disabled')
                if kind=='plan':
                    stale=record.get('status') in ('expired','cancelled','failed','succeeded','executing')
                    self.action_edit_button.pack(side='left',padx=4);self.action_edit_button.configure(state='disabled' if stale else 'normal')
                    self.action_cancel_button.configure(state='disabled' if stale else 'normal')
                else:self.action_cancel_button.configure(state='normal')
                self.action_cancel_button.pack(side='right')
            else:
                if kind=='query' and record.get('status') in ('failed','cancelled'):self.action_retry_button.pack(side='left',padx=3)
                if record.get('result') is not None:
                    self.action_result_button.pack(side='left')
                    if isinstance(record['result'],dict) and 'rows' in record['result']:
                        self.action_copy_button.pack(side='left',padx=3);self.action_export_button.pack(side='left',padx=3);self.action_handoff_button.pack(side='left',padx=3)
                if kind=='query' and record.get('result') is not None:self.action_schedule_button.pack(side='left',padx=4)
                if record.get('schedule'):
                    self.action_run_button.pack(side='left',padx=4);self.action_pause_button.pack(side='left')
                    self.refresh_action_run_state(record)
                    self.action_pause_button.configure(text='暫停' if record['schedule']['enabled'] else '恢復')
                if record.get('status') in ('queued','running'):self.action_cancel_button.pack(side='right')
        finally:self.action_loading=False
        self.appearance.apply(self.action_panel)
        self.action_canvas.configure(height=self.display.px(180 if draft and kind=='report' else 220))
        if draft and kind!='choose':self.auto_preview_action()

    def action_summary(self,record):
        spec=copy.deepcopy(record.get('spec') or {});result=record.get('result');lines=[]
        if isinstance(result,dict) and isinstance(result.get('parameters'),dict):spec['parameters']=result['parameters']
        if spec.get('query_id'):
            try:
                template=find_template(self.queries.catalog(),spec['query_id'])
                lines.append(template['name']+' · '+'；'.join(describe(template,spec.get('parameters',{}))))
            except ValueError:pass
        if record.get('schedule'):
            schedule=record['schedule'];lines.append(schedule['name']+' · '+FREQUENCIES.get(schedule['frequency'],schedule['frequency'])+' '+schedule['time_hhmm']+' 台北 · '+DATE_MODES.get(schedule.get('parameters',{}).get('_date_mode','previous_day'),''))
        if isinstance(result,dict) and 'rows' in result:
            lines+=['共 '+str(result['row_count'])+' 列'+('（已截斷）' if result.get('truncated') else '')+' · 資料時間：'+local_time(result.get('fetched_at_utc'))]
            lines.append('前 5 列預覽（完整結果保留在本機）')
            columns=result.get('columns',[]);lines.append(' ｜ '.join(c['label'] for c in columns))
            for row in result['rows'][:5]:lines.append(' ｜ '.join(str(row.get(c['name'],'')) for c in columns) if isinstance(row,dict) else ' ｜ '.join(map(str,row)))
            if result.get('summary'):lines+=['',result['summary']]
            if result.get('summary_error'):lines+=['整理失敗；表格仍保留。',result['summary_error']]
        elif result:lines.append(result.get('text',str(result)) if isinstance(result,dict) else str(result))
        if lines:
            text=tk.Text(self.action_body,height=min(12,max(3,len(lines)+2)),wrap='word',spacing1=0,spacing3=0,padx=8,pady=6);text.pack(fill='x')
            text.insert('1.0','\n'.join(lines));text.configure(state='disabled')

    def action_spec(self):
        spec=copy.deepcopy(self.action_record['spec']);raw={key:var.get() for key,var in self.action_param_vars.items()}
        if self.action_record['kind'] in ('plan','choose'):return spec
        template=next((q for q in self.action_catalog if q['id']==spec.get('query_id')),None)
        if template:
            for key,value in list(raw.items()):
                field=template['parameters'][key]
                try:raw[key]=parameters({'id':'field','name':'field','parameters':{key:field}},{key:value},from_ui=True).get(key,'')
                except ValueError:pass
        spec['parameters']=dict(spec.get('parameters',{}),**raw)
        for key,var in self.action_vars.items():
            value=var.get()
            if key=='frequency':value=next((k for k,v in FREQUENCIES.items() if v==value),value)
            if key=='date_mode':value=next((k for k,v in DATE_MODES.items() if v==value),value)
            if key=='weekday':value=WEEKDAYS.index(value) if value in WEEKDAYS else int(value) if value.isdigit() else value
            spec[key]=value
        return spec

    def action_edited(self,*args):
        if self.action_loading or not self.action_record or self.action_record['state']!='draft':return
        self.action_confirm_button.configure(state='disabled')
        if hasattr(self,'action_consent'):self.action_consent.set(False)
        self.action_record=self.actions.update(self.action_id,self.action_record['revision'],self.action_spec())
        self.action_feedback.set('條件已修改。')
        self.auto_preview_action()

    def action_schedule_edited(self,key):
        self.action_edited()
        if not self.action_loading and key in ('frequency','date_mode'):self.populate_action(self.actions.snapshot(self.action_id))

    def action_consent_changed(self):
        self.auto_preview_action()

    def action_query_changed(self):
        template=next(q for q in self.action_catalog if q['name']==self.action_query_name.get())
        spec=copy.deepcopy(self.action_record['spec']);spec.update(query_id=template['id'],parameters=initial_values(template))
        if self.action_record['kind']=='schedule' and not date_mapping(template):spec['date_mode']='literal'
        if self.action_record['kind'] in ('schedule','report') and spec.get('name') in ('定期查詢','每日合成資料日報',''):
            spec['name']=('每日日報 · ' if self.action_record['kind']=='report' else '定期查詢 · ')+template['name']
        record=self.actions.update(self.action_id,self.action_record['revision'],spec);self.populate_action(record)

    def adopt_report_rule(self):
        spec=copy.deepcopy(self.action_record['spec']);spec.update(frequency='daily',date_mode='previous_day',weekday=0)
        record=self.actions.update(self.action_id,self.action_record['revision'],spec)
        self.populate_action(record)

    def change_action_kind(self,kind):
        spec=copy.deepcopy(self.action_record['spec'])
        spec={'query_id':spec.get('query_id',''),'parameters':spec.get('parameters',{})} if kind=='query' else dict(spec,name=spec.get('name') or ('每日合成資料日報' if kind=='report' else '定期查詢'),time_hhmm=spec.get('time_hhmm',''),frequency='daily',weekday=0,date_mode='previous_day')
        record=self.actions.update(self.action_id,self.action_record['revision'],spec,kind=kind);self.populate_action(record);self.show_chat()

    def auto_preview_action(self):
        if not self.action_record or self.action_record['state']!='draft':return
        if self.action_id in self.action_busy:
            self.action_confirm_button.configure(state='disabled');return
        if self.action_record['kind']=='report' and not self.action_consent.get():
            self.action_confirm_button.configure(state='disabled');self.action_feedback.set('請核對條件，並勾選每日資料傳送授權。');return
        self.preview_action()

    def preview_action(self):
        if self.action_id in self.action_busy:raise ValueError('請等待解析完成。')
        if self.action_record['kind']=='report' and not self.action_consent.get():raise ValueError('請先確認每日範圍與資料傳送授權。')
        if self.action_record['kind'] not in ('plan','choose'):
            spec=self.action_spec()
            if spec!=self.action_record['spec']:self.action_record=self.actions.update(self.action_id,self.action_record['revision'],spec)
        record=self.actions.preview(self.action_id,self.action_record['revision'])
        self.action_feedback.set(record.get('error') or '條件已核對；按確認後才執行。此確認卡 10 分鐘內有效。')
        self.action_confirm_button.configure(state='normal' if record.get('ready') else 'disabled')

    def confirm_action(self):
        record=self.actions.confirm(self.action_id,self.action_record['revision'],consent=self.action_record['kind']=='report' and self.action_consent.get())
        # Only accepted work consumes the original composer draft.
        if self.input.get('1.0','end-1c').strip()==record.get('request'):
            self.clear_saved_draft(self.conversation);self.input.delete('1.0','end');self.drafts.pop(self.conversation,None)
        self.populate_action(self.actions.snapshot(record['id']));self.show_chat();self.refresh_lists()

    def edit_action_plan(self):
        record=self.actions.get(self.action_id)
        self.plans.selection_set(record['plan_id']);self.preview_selected_plan();self.edit_plan()
        if not self.more_options.winfo_manager():self.more_options.pack(fill='x',pady=4)

    def cancel_action(self):
        snap=self.actions.snapshot(self.action_id)
        if snap.get('schedule') and snap.get('task') and snap['task']['state'] in ('queued','running'):
            self.engine.cancel_task(snap['task']['id'])
        else:self.actions.cancel(self.action_id)
        self.populate_action(self.actions.snapshot(self.action_id));self.show_chat()

    def parse_action(self,record):
        from .intent_drafts import extract_action
        aid=record['id'];revision=record['revision'];kind=record['kind'];spec=copy.deepcopy(record['spec'])
        self.actions.begin_parse(aid,revision);self.action_busy.add(aid)
        self.action_feedback.set('Groq 正在整理條件；尚未查詢或建立排程。')
        def work():
            try:return extract_action(record['request'],kind=kind),None
            except Exception:return None,'解析未完成；請手動補齊條件。沒有執行或自動重試。'
            finally:self.actions.end_parse(aid)
        def done(outcome):
            self.action_busy.discard(aid);result,error=outcome
            try:current=self.actions.get(aid)
            except ValueError:return
            if current['state']!='draft' or current['revision']!=revision:
                if current['state']=='draft' and self.action_id==aid and self.conversation==current['conversation_id']:
                    self.auto_preview_action()
                return
            if result:
                spec['query_id']=result.get('query_id') or '';spec['parameters']={k:v for k,v in (result.get('parameters') or {}).items() if v is not None}
                if kind in ('schedule','report'):
                    for key in ('time_hhmm','frequency','date_mode'):
                        spec[key]=result.get(key) or ''
                    if result.get('weekday') is not None:spec['weekday']=result['weekday']
                    elif spec.get('frequency')=='weekly':spec['weekday']=''
                    template=next((q for q in self.queries.catalog() if q['id']==spec['query_id']),None)
                    if template and spec.get('name') in ('定期查詢','每日合成資料日報',''):
                        spec['name']=('每日日報 · ' if kind=='report' else '定期查詢 · ')+template['name']
                updated=self.actions.apply_parse(aid,revision,spec)
                if updated is None:return
            if self.action_id==aid and self.conversation==current['conversation_id']:
                self.populate_action(self.actions.snapshot(aid))
                questions=(result or {}).get('questions') or []
                self.action_feedback.set(error or '；'.join(questions) or '請核對解析條件，再確認。')
            self.render_action_timeline()
        self.background(work,done)

    def discuss_action(self):
        request=self.action_record['request'];self.actions.cancel(self.action_id)
        if self.input.get('1.0','end-1c').strip()!=request:raise ValueError('草稿已改變；請回輸入框確認後送出一般討論。')
        self.action_chat_only=True
        try:self.send_chat()
        finally:self.action_chat_only=False
        self.show_chat()

    def load_action_result(self):
        task=self.actions.snapshot(self.action_id).get('task')
        if not task:raise ValueError('尚無結果。')
        page=self.book.select();self.show_result(task['id']);self.book.select(page)

    def copy_action_result(self):
        self.load_action_result();self.copy_table(False)

    def export_action_result(self):
        self.load_action_result();self.export_csv()

    def handoff_action_result(self):
        self.load_action_result();self.open_result_handoff()

    def action_result(self):
        snap=self.actions.snapshot(self.action_id);task=snap.get('task')
        if not task:raise ValueError('尚無執行結果。')
        self.action_return=(self.conversation,self.action_id,self.transcript.yview()[0]);self.show_result(task['id'])
        if not hasattr(self,'action_back_button'):
            self.action_back_button=self.button(self.tabs['result'],'返回原對話',self.return_to_action,'Compact.TButton');self.action_back_button.grid(row=7,column=0,sticky='w',pady=4)

    def return_to_action(self):
        cid,aid,scroll=self.action_return;self.show_action(aid);self.show_chat();self.transcript.yview_moveto(scroll)

    def action_to_schedule(self):
        record=self.actions.snapshot(self.action_id);spec=copy.deepcopy(record['spec'])
        template=find_template(self.queries.catalog(),spec['query_id'])
        spec.update(name='定期查詢 · '+template['name'],time_hhmm='',frequency='daily',weekday=0,date_mode='previous_day' if date_mapping(template) else 'literal',source_task_id=record['task']['id'])
        self.start_action('schedule','將這次查詢設為自動工作',spec)

    def retry_query_action(self):
        record=self.actions.snapshot(self.action_id)
        if record['kind']!='query' or record['status'] not in ('failed','cancelled'):
            raise ValueError('只有已結束的查詢可以重新準備。')
        self.start_action('query',record['request'],record['spec'])

    def refresh_action_run_state(self,record):
        blocked=record.get('status') in ('queued','running') or time.monotonic()<self.action_run_deadlines.get(record['id'],0)
        self.action_run_button.configure(state='disabled' if blocked else 'normal')

    def run_action_now(self):
        record=self.actions.snapshot(self.action_id);now=time.monotonic()
        if record.get('status') in ('queued','running') or now<self.action_run_deadlines.get(self.action_id,0):return
        # A double-click must remain one test even if a synthetic query finishes immediately.
        self.action_run_deadlines[self.action_id]=now+1.5;self.action_run_button.configure(state='disabled')
        self.actions.run_now(self.action_id,uuid.uuid4().hex);self.populate_action(self.actions.snapshot(self.action_id));self.refresh_lists()

    def pause_action_schedule(self):
        record=self.actions.snapshot(self.action_id);schedule=record['schedule']
        self.engine.set_schedule_enabled(schedule['id'],not schedule['enabled']);self.populate_action(self.actions.snapshot(self.action_id));self.refresh_lists()

    def render_action_timeline(self):
        if not self.conversation:return
        events=[]
        for index,message in enumerate(self.store.messages(self.conversation)):
            role='user' if message['role']=='user' else 'assistant'
            events.append((message.get('created_at',''), 'm:'+str(message.get('id',index)),('你' if role=='user' else 'QA agent')+'\n'+message['text']+'\n\n',role,None))
        records=self.actions.list(self.conversation)
        for record in records:
            snap=self.actions.snapshot(record['id']);state=snap.get('status',snap['state'])
            body='工作 · '+ACTION_NAMES.get(snap['kind'],snap['kind'])+' · '+STATUS_NAMES.get(state,state)+'\n'+snap.get('request','')+'\n點此查看確認卡／結果\n\n'
            events.append((record.get('created_at',''), 'a:'+record['id'],body,'action',record['id']))
        events.sort(key=lambda item:(item[0],item[1]))
        key=[(e[1],e[2]) for e in events];same=self.timeline_cid==self.conversation
        old=self.timeline_events if same else []
        if key!=old or not same:
            top=self.transcript.yview();at_bottom=top[1]>=.98
            self.transcript.mark_set('view_anchor',self.transcript.index('@0,0'))
            self.transcript.configure(state='normal')
            old_ids=[x[0] for x in old];new_ids=[x[0] for x in key]
            # Existing events update within their own marks; new events append.
            compatible=same and old_ids==new_ids[:len(old_ids)] and bool(old)
            if not compatible:self.transcript.delete('1.0','end')
            if not events:self.transcript.insert('end','今天，想先完成哪件事？\n選一個範例，或直接輸入需求。\n','welcome_body')
            for index,event in enumerate(events):
                _,eid,body,role,aid=event;mark='event_'+eid.replace(':','_');endmark=mark+'_end'
                if compatible and index<len(old) and old[index]==key[index]:continue
                if compatible and index<len(old):
                    pos=self.transcript.index(mark);self.transcript.delete(mark,endmark)
                    for later in events[index+1:len(old)]:self.transcript.mark_gravity('event_'+later[1].replace(':','_'),'right')
                else:pos=self.transcript.index('end-1c')
                self.transcript.mark_set(mark,pos);self.transcript.mark_gravity(mark,'left')
                tag=mark+'_tag' if aid else 'body_'+role
                self.transcript.insert(pos,body,tag);self.transcript.mark_set(endmark,pos+'+'+str(len(body))+'c');self.transcript.mark_gravity(endmark,'left')
                if compatible:
                    for later in events[index+1:len(old)]:self.transcript.mark_gravity('event_'+later[1].replace(':','_'),'left')
                if aid:
                    self.transcript.tag_configure(tag,foreground=self.palette.ACCENT)
                    self.transcript.tag_bind(tag,'<Button-1>',lambda e,aid=aid:self.safe(lambda:self.show_action(aid)))
            self.transcript.configure(state='disabled')
            if same and not at_bottom:self.transcript.yview('view_anchor')
            elif events:self.transcript.see('end')
            self.timeline_events=key;self.timeline_cid=self.conversation
        self._rendered_messages=key;self._rendered_conversation=self.conversation;self.update_work_card_visibility()
        target=self.action_selected.get(self.conversation)
        if target and target!=self.action_id:
            try:self.show_action(target)
            except ValueError:self.action_selected.pop(self.conversation,None);self.action_panel.pack_forget()
        elif not target:self.action_panel.pack_forget();self.action_id=None

    def build_activity(self):
        self.activity_tree=self.tree(self.tabs['activity'],[('kind','類型'),('state','狀態／內容'),('time','台北時間')],9)
        self.activity_tree.bind('<Double-1>',lambda e:self.safe(self.open_activity))
        self.button(self.tabs['activity'],'查看',self.open_activity,'Primary.TButton').pack(anchor='w',pady=6)
        self.activity_targets={}

    def refresh_action_activity(self):
        if not hasattr(self,'activity_tree') or not self.conversation:return
        self.render_action_timeline()
        if self.action_id:
            try:record=self.actions.snapshot(self.action_id)
            except ValueError:self.action_panel.pack_forget();self.action_id=None
            else:
                key=(record['id'],record['revision'],record.get('status'),str(record.get('result')),record.get('error'))
                if (record['state']!='draft' or record['kind']=='plan') and key!=self.action_panel_key:self.populate_action(record)
                if record.get('schedule'):self.refresh_action_run_state(record)
        rows=[];targets={}
        for task in self.store.tasks():
            key='task:'+task['id'];rows.append((task['created_at'],key,['工作',STATUS_NAMES.get(task['state'],task['state']),local_time(task['created_at'])]));targets[key]=('task',task['id'])
        for notice in self.store.notifications():
            key='notice:'+notice['id'];rows.append((notice['created_at'],key,['通知',notice['text'],local_time(notice['created_at'])]));targets[key]=('notice',notice['id'])
        for conversation in self.store.conversations():
            for action in self.actions.list(conversation['id']):
                if action['state']!='draft':continue
                key='action:'+action['id'];snap=self.actions.snapshot(action['id'])
                rows.append((action['created_at'],key,[ACTION_NAMES.get(action['kind'],'待確認工作'),STATUS_NAMES.get(snap['status'],snap['status']),local_time(action['created_at'])]));targets[key]=('action',action['id'])
        self.activity_targets=targets;self.sync_tree(self.activity_tree,[(key,values) for _,key,values in sorted(rows,reverse=True)])

    def open_activity(self):
        chosen=self.activity_tree.selection()
        if not chosen:raise ValueError('請先選取活動。')
        kind,record_id=self.activity_targets[chosen[0]]
        if kind=='action':self.show_action(record_id);return
        if kind=='notice':
            self.notices.selection_set(record_id);self.read_notice();return
        task=self.store.task(record_id)
        for conversation in self.store.conversations():
            for action in self.actions.list(conversation['id']):
                snap=self.actions.snapshot(action['id'])
                if (snap.get('task') or {}).get('id')==record_id:self.show_action(action['id']);return
        if task.get('result') is not None:self.show_result(record_id)
        else:self.open_work_detail('task',record_id)
