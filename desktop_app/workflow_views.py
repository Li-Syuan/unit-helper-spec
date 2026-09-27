"""Conversation-first workflow presentation. All dispatch stays in WorkflowService."""
import copy
import json
import uuid
import tkinter as tk
from tkinter import ttk
from .branding import apply_child_icons
from .display import scroll_frame
from .query_schema import find_template, parameters, initial_values
from .preferences import load_preferences, update_preferences
from .workflow_presenter import WorkflowPresenter, detail_text
from . import dialogs as messagebox

ROLES={'planner':'主代理／規劃','analysis':'分析','review':'覆核','compose':'彙整','rag':'資料查找'}
STATES={'draft':'需求討論中','planning':'主代理規劃中','ready':'尚未執行 · 待批准','approved':'已批准',
        'queued':'等待執行','running':'執行中','succeeded':'完成','failed':'失敗／需要處理','cancelled':'已取消'}


class WorkflowViews:
    def build_workflow_ui(self):
        self.workflow_selected={};self.workflow_id=None;self.workflow_record=None;self.workflow_render_key=None
        self.workflow_chat_children=list(self._action_conversation_widget.winfo_children())
        stored=load_preferences(self.preferences_path).get('conversation_modes',{})
        self.workflow_modes=stored if isinstance(stored,dict) else {};self.workflow_cid=None
        self.workflow_mode=tk.StringVar(value='chat');self.workflow_consent=tk.BooleanVar(value=False)
        bar=self.assistant_bar
        self.profile_picker.configure(width=16)
        modes=self.workflow_mode_controls=ttk.Frame(bar);modes.pack(side='left')
        for text,value in [('聊天','chat'),('規劃工作','workflow')]:
            ttk.Radiobutton(modes,text=text,value=value,variable=self.workflow_mode,style='Mode.TRadiobutton',command=self.change_workflow_mode).pack(side='left',padx=(0,4))
        self.button(bar,'流程紀錄',self.open_workflow_list,'Compact.TButton').pack(side='right')
        self.workflow_panel=ttk.Frame(self.chat_column)
        top=ttk.Frame(self.workflow_panel);top.pack(fill='x')
        ttk.Label(top,text='主代理').pack(side='left')
        self.workflow_planner=ttk.Combobox(top,state='readonly',width=24);self.workflow_planner.pack(side='left',padx=5)
        self.button(top,'另開計畫',self.new_workflow,'Compact.TButton').pack(side='right')
        self.workflow_state=ttk.Label(self.workflow_panel,text='',style='Muted.TLabel',wraplength=680)
        self.workflow_state.pack(fill='x',pady=4)
        self.workflow_progress=ttk.Progressbar(self.workflow_panel,mode='indeterminate')
        self.workflow_progress_running=False
        self.workflow_body=ttk.Frame(self.workflow_panel)
        self.workflow_notebook=ttk.Notebook(self.workflow_body)
        self.workflow_notebook.pack(fill='both',expand=True)
        self.workflow_steps_view=WorkflowPresenter(self.workflow_notebook,self,self.show_workflow_step)
        self.workflow_notebook.add(self.workflow_steps_view,text='分工進度')
        body=ttk.Frame(self.workflow_notebook)
        self.workflow_notebook.add(body,text='完整討論與成果')
        self.workflow_text=tk.Text(body,state='disabled',wrap='word',height=5,exportselection=False)
        self.workflow_text.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(body,command=self.workflow_text.yview);scroll.pack(side='right',fill='y')
        self.workflow_text.configure(yscrollcommand=scroll.set)
        self.workflow_steps_key=None
        self.workflow_footer=ttk.Frame(self.workflow_panel);self.workflow_footer.pack(side='bottom',fill='x')
        self.workflow_questions_box=ttk.Frame(self.workflow_footer);self.workflow_questions_box.pack(fill='x')
        self.workflow_question_vars={};self.workflow_questions_key=None
        self.workflow_consent_button=ttk.Label(self.workflow_footer,text='按「確認執行」即同意將指定輸入與前置成果交給上述助理。',style='Muted.TLabel',wraplength=650)
        self.workflow_consent_button.pack(anchor='w',pady=3)
        self.workflow_controls=ttk.Frame(self.workflow_footer);self.workflow_controls.pack(fill='x')
        self.workflow_buttons={}
        for text,fn in [('修改步驟',self.edit_workflow_steps),('批准並試跑',self.confirm_workflow_from_card),('停止',self.cancel_workflow),
                        ('重試未完成步驟',self.retry_workflow),('設為自動工作',self.schedule_workflow),
                        ('現在測試一次',self.run_workflow_now),('暫停自動工作',self.pause_workflow_schedule),('步驟詳情',self.workflow_step_details)]:
            button=self.button(self.workflow_controls,text,fn,'Primary.TButton' if text=='批准並試跑' else 'Compact.TButton')
            self.workflow_buttons[text]=button
            if text=='批准並試跑':button.configure(text='確認執行')
        ttk.Label(self.workflow_footer,text='產生計畫會呼叫主代理；批准前不查詢、不派發子代理。請用輸入框繼續討論。',style='Muted.TLabel',wraplength=680).pack(fill='x',pady=3)
        self.workflow_body.pack(fill='both',expand=True)
        self.refresh_workflow_catalog()

    def refresh_workflow_catalog(self):
        previous=self.workflow_planner.get()
        self.workflow_profiles=self.profiles.workflow_catalog()
        self.workflow_planners=[p for p in self.workflow_profiles if 'planner' in p.get('workflow',{}).get('roles',[])]
        names=[p['name']+' · '+p['id'][-8:] for p in self.workflow_planners]
        self.workflow_planner.configure(values=names)
        if previous in names:self.workflow_planner.set(previous)
        elif names:self.workflow_planner.current(0)
        else:self.workflow_planner.set('尚無已驗證的規劃助理')

    def change_workflow_mode(self):
        if self.workflow_mode.get()=='workflow' and self.editing_plan:
            self.workflow_mode.set('chat');raise ValueError('請先保存或退出原有 Plan 修改。')
        if self.conversation:
            ids={c['id'] for c in self.store.conversations()}
            self.workflow_modes={cid:mode for cid,mode in self.workflow_modes.items() if cid in ids and mode in ('chat','workflow')}
            self.workflow_modes[self.conversation]=self.workflow_mode.get();self.workflow_cid=self.conversation
            try:update_preferences(self.preferences_path,{'conversation_modes':self.workflow_modes})
            except OSError:self.status.set('無法保存聊天／規劃選擇；本次仍可使用，重開後請重新確認模式。')
        self.refresh_workflow_view(force=True);self.update_composer()

    def new_workflow(self):
        self.workflow_selected[self.conversation]=None;self.workflow_id=None;self.workflow_record=None
        self.workflow_consent.set(False);self.refresh_workflow_view(force=True)
        self.input.focus_set()

    def workflow_content(self,record):
        lines=['目標：'+record['goal'],'']
        for index,step in enumerate(record.get('steps',[]),1):
            target='核准查詢 '+step.get('query_id','') if step['kind']=='query' else self.workflow_target(step.get('binding'))
            lines.extend([f'{index}. {step["title"]} → {target}',step.get('instruction',''),
                          '輸入：'+('、'.join(step.get('inputs',[])) or '本次需求')])
            if step['kind']=='query':lines.append('條件：'+json.dumps(step.get('parameters',{}),ensure_ascii=False)+' · '+('每次前一日' if step.get('date_mode')=='previous_day' else '固定日期'))
            lines.append('')
        if record.get('discussion'):lines.append('需求討論紀錄')
        for item in record.get('discussion',[]):
            lines.extend([('你' if item['role']=='user' else '主代理')+'：'+str(item['content']),''])
        for state in record.get('steps_status',[]):
            lines.extend(['步驟 '+str(state.get('step_id',''))+' · '+STATES.get(state.get('state'),state.get('state','')),
                          '輸出：'+self.workflow_output(state.get('output'))])
            if state.get('error'):lines.append('原因：'+str(state['error']))
        task=record.get('task') or {}
        if (task.get('result') or {}).get('report'):lines.extend(['整合結果',task['result']['report']])
        if record.get('error') or task.get('error'):lines.extend(['需要處理：',str(record.get('error') or task['error'])])
        if record.get('schedule'):
            schedule=record['schedule'];lines.extend(['自動工作：'+schedule['name'],('已啟用' if schedule['enabled'] else '已暫停')+' · '+schedule['time_hhmm']+' 台北時間；App 須保持開啟'])
        return '\n'.join(lines)

    @staticmethod
    def workflow_output(value):
        return value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2) if value is not None else '尚無輸出'

    def workflow_target(self,binding):
        binding=binding or {};pid=binding.get('profile_id','')
        item=next((p for p in self.workflow_profiles if p['id']==pid),None)
        return (item['name'] if item else pid)+' · 連線版 '+str(binding.get('revision',''))

    def refresh_workflow_view(self,force=False):
        if not hasattr(self,'workflow_panel'):return
        if self.workflow_cid!=self.conversation:
            self.workflow_cid=self.conversation
            self.workflow_mode.set('workflow' if self.workflow_modes.get(self.conversation)=='workflow' else 'chat')
        visible=self.workflow_mode.get()=='workflow'
        if visible:
            self.chat_assistant_controls.pack_forget();self.assistant_usage.pack_forget()
            for widget in self.workflow_chat_children:widget.pack_forget()
            self.action_panel.pack_forget();self.work_cards_box.pack_forget();self.task_card.pack_forget()
            if not self.workflow_panel.winfo_manager():self.workflow_panel.pack(in_=self._action_conversation_widget,fill='both',expand=True)
        else:
            if not self.chat_assistant_controls.winfo_manager():
                self.chat_assistant_controls.pack(side='left',before=self.workflow_mode_controls)
                self.assistant_usage.pack(fill='x',pady=(0,4),after=self.assistant_bar)
            self.workflow_panel.pack_forget()
            if not self.transcript.winfo_manager():
                self.transcript.pack(side='left',fill='both',expand=True)
                for widget in self.workflow_chat_children:
                    if widget is not self.transcript:widget.pack(side='right',fill='y')
            return
        if self.conversation and self.conversation not in self.workflow_selected:
            records=self.workflows.list(self.conversation)
            self.workflow_selected[self.conversation]=records[-1]['id'] if records else None
        wid=self.workflow_selected.get(self.conversation)
        try:record=self.workflows.snapshot(wid) if wid else None
        except ValueError:
            self.workflow_selected.pop(self.conversation,None);record=None;wid=None
        if self.workflow_id!=wid or (record and self.workflow_record and record['revision']!=self.workflow_record['revision']):
            self.workflow_consent.set(False);force=True
        self.workflow_id=wid;self.workflow_record=record
        steps_key=(wid,bool(record and record.get('steps')))
        if steps_key!=self.workflow_steps_key:
            self.workflow_notebook.select(self.workflow_steps_view if steps_key[1] else self.workflow_text.master)
            self.workflow_steps_key=steps_key
        self.workflow_steps_view.update_record(record)
        if not record:
            text='先說明你想完成什麼工作。\n\n例如：查昨天 A 類數量合計，請分析助理整理，再交覆核助理檢查，最後產生日報。\n\n主代理會和你補齊條件、提出分工；你批准後才由子代理依序執行。'
            self.workflow_state.configure(text='尚未建立計畫' if self.workflow_planners else '請先在設定配置並驗證規劃助理；不會自動改用外部模型。')
            task={};state='draft'
        else:
            text=self.workflow_content(record);task=record.get('task') or {};state=task.get('state') or record['state']
            self.workflow_state.configure(text=f'計畫第 {record["revision"]} 版 · '+STATES.get(state,state))
        # Keep selection and viewport when polling; append discussions without rebuilding history.
        old=self.workflow_text.get('1.0','end-1c')
        if text!=old:
            view=self.workflow_text.yview();selection=self.workflow_text.tag_ranges('sel')
            self.workflow_text.configure(state='normal')
            if old and text.startswith(old):self.workflow_text.insert('end',text[len(old):])
            else:self.workflow_text.delete('1.0','end');self.workflow_text.insert('1.0',text)
            self.workflow_text.configure(state='disabled')
            if selection and not force:self.workflow_text.tag_add('sel',*selection)
            if not force:self.workflow_text.yview_moveto(view[0])
        busy=state in ('planning','queued','running')
        if busy and not self.workflow_progress_running:
            self.workflow_progress.pack(fill='x',before=self.workflow_body);self.workflow_progress.start(12);self.workflow_progress_running=True
        elif not busy and self.workflow_progress_running:
            self.workflow_progress.stop();self.workflow_progress.pack_forget();self.workflow_progress_running=False
        for button in self.workflow_buttons.values():button.pack_forget()
        if record:
            if not busy and not task:
                self.workflow_buttons['修改步驟'].pack(side='left',padx=2)
                self.workflow_buttons['批准並試跑'].pack(side='right',padx=2)
                self.workflow_buttons['批准並試跑'].configure(state='normal' if record['state']=='ready' else 'disabled')
            if busy:self.workflow_buttons['停止'].pack(side='right')
            if state=='failed' and task:self.workflow_buttons['重試未完成步驟'].pack(side='left')
            if task:self.workflow_buttons['步驟詳情'].pack(side='left')
            if state=='succeeded' and not record.get('schedule'):self.workflow_buttons['設為自動工作'].pack(side='right')
            if record.get('schedule') and not busy:
                self.workflow_buttons['現在測試一次'].pack(side='left')
                if record['schedule']['enabled']:self.workflow_buttons['暫停自動工作'].pack(side='right')
        if record and not task and not busy:
            self.workflow_consent_button.pack(anchor='w',pady=3,before=self.workflow_controls)
        else:self.workflow_consent_button.pack_forget()
        self.refresh_workflow_questions(record)
        if record:self.workflow_planner.configure(state='disabled')
        else:self.workflow_planner.configure(state='readonly')

    def refresh_workflow_questions(self,record):
        questions=(record or {}).get('questions',[])
        key=((record or {}).get('id'),(record or {}).get('revision'),str(questions))
        if key==self.workflow_questions_key:return
        self.workflow_questions_key=key;self.workflow_question_vars={}
        for child in self.workflow_questions_box.winfo_children():child.destroy()
        if not questions:return
        # Compact same-page entry opens a scrollable answer form for arbitrarily many questions.
        ttk.Label(self.workflow_questions_box,text=f'需要補充 {len(questions)} 個條件；可選答案，或直接在輸入框回答。',style='Muted.TLabel').pack(side='left')
        self.button(self.workflow_questions_box,'回答條件',self.answer_workflow_questions,'Compact.TButton').pack(side='right')

    def answer_workflow_questions(self):
        record=self.workflow_record;wid=record['id'];revision=record['revision']
        w,body=self.workflow_window('補齊工作條件');variables=[]
        for q in record.get('questions',[]):
            ttk.Label(body,text=q['text'],wraplength=570).pack(anchor='w',pady=(8,3))
            choices=q.get('options',[])
            if q['type']=='multi':
                values=[]
                for choice in choices:
                    var=tk.BooleanVar(value=False);values.append((choice,var));ttk.Checkbutton(body,text=choice,variable=var).pack(anchor='w')
                variables.append((q,values))
            elif q['type'] in ('single','boolean'):
                var=tk.StringVar();variables.append((q,var))
                for choice in (choices or ['是','否']):ttk.Radiobutton(body,text=choice,variable=var,value=choice).pack(anchor='w')
            else:
                var=tk.StringVar();variables.append((q,var));ttk.Entry(body,textvariable=var).pack(fill='x')
        def submit():
            answers=[]
            for question,variable in variables:
                value='、'.join(c for c,v in variable if v.get()) if isinstance(variable,list) else variable.get()
                if not value.strip():raise ValueError('請回答：'+question['text'])
                answers.append(question['text']+'：'+value)
            self.workflows.discuss(wid,revision,'\n'.join(answers));w.destroy();self.refresh_workflow_view()
        self.button(w,'送給主代理補充計畫',submit,'Primary.TButton').pack(side='bottom',pady=10)
        self.appearance.apply(w)

    def send_workflow(self):
        if self.editing_plan:raise ValueError('請先退出既有 Plan 修改。')
        if self.attachment:raise ValueError('規劃討論目前使用文字；請移除附件，並只貼上此次允許傳送的內容。')
        text=self.input.get('1.0','end-1c').strip()
        if not text:raise ValueError('請先說明需求或補充條件。')
        record=self.workflow_record
        if record and (record.get('task') or record['state']=='cancelled'):raise ValueError('此計畫已有執行紀錄；請按「另開計畫」討論新的需求。')
        if not record:
            index=self.workflow_planner.current()
            if index<0 or index>=len(self.workflow_planners):raise ValueError('尚無已驗證的規劃助理，請先完成公司能力接線。')
            binding=self.profiles.workflow_binding(self.workflow_planners[index]['id'])
            record=self.workflows.create(self.conversation,text,binding)
            self.workflow_selected[self.conversation]=record['id']
        self.workflows.discuss(record['id'],record['revision'],text)
        self.clear_saved_draft(self.conversation);self.input.delete('1.0','end')
        self.drafts.pop(self.conversation,None);self.workflow_consent.set(False);self.refresh_workflow_view()

    def confirm_workflow(self):
        if not self.workflow_consent.get():raise ValueError('請先核對每一步的目的助理與資料，再按「確認執行」。')
        r=self.workflow_record;preview=self.workflows.preview(r['id'],r['revision'])
        if not preview.get('ready'):raise ValueError(preview.get('error') or '計畫尚未完整。')
        self.workflows.confirm(r['id'],r['revision'],consent=True);self.refresh_workflow_view()

    def confirm_workflow_from_card(self):
        """One explicit click authorizes exactly the displayed version, never a future revision."""
        record=self.workflow_record
        if not record:raise ValueError('請先與主代理建立計畫。')
        if record.get('task'):return
        if record['state']!='ready':raise ValueError('請先補齊計畫內容。')
        self.workflow_consent.set(True)
        try:self.confirm_workflow()
        finally:self.workflow_consent.set(False)

    def cancel_workflow(self):
        self.workflows.cancel(self.workflow_id);self.refresh_workflow_view()

    def retry_workflow(self):
        if messagebox.askyesno('重試未完成步驟','將沿用未變更的成功前置成果，從失敗處繼續；可能再次呼叫助理。確認重試？',parent=self.root):
            self.workflows.retry(self.workflow_record['task']['id'],uuid.uuid4().hex);self.refresh_workflow_view()

    def run_workflow_now(self):
        self.engine.run_schedule_now(self.workflow_record['schedule']['id'],uuid.uuid4().hex)
        self.refresh_workflow_view()

    def pause_workflow_schedule(self):
        self.engine.set_schedule_enabled(self.workflow_record['schedule']['id'],False);self.refresh_workflow_view()

    def workflow_step_details(self):
        self.show_workflow_result(self.workflow_record['task']['id'])

    def show_workflow_step(self,row,record):
        """Open a fixed read-only snapshot, without dispatching or changing approval."""
        w,body=self.workflow_window('步驟詳情 · '+row['title'])
        ttk.Label(body,text='本視窗為開啟時的快照；最新進度請回分工清單查看。',style='Muted.TLabel',wraplength=570).pack(fill='x',pady=(0,6))
        box=ttk.Frame(body);box.pack(fill='both',expand=True)
        text=tk.Text(box,wrap='word',height=14,exportselection=False)
        text.pack(side='left',fill='both',expand=True)
        bar=ttk.Scrollbar(box,command=text.yview);bar.pack(side='right',fill='y')
        text.configure(yscrollcommand=bar.set)
        content=detail_text(row,record);text.insert('1.0',content);text.configure(state='disabled')
        actions=ttk.Frame(w,padding=8);actions.pack(side='bottom',fill='x')
        self.button(actions,'複製完整內容',lambda:self.clipboard(content),'Compact.TButton').pack(side='left')
        result=(row['observed'].get('output') or {}).get('query_result')
        if result:self.button(actions,'查看原始表格',lambda:self.show_workflow_table(result),'Compact.TButton').pack(side='left',padx=6)
        self.button(actions,'關閉',w.destroy,'Compact.TButton').pack(side='right')
        self.appearance.apply(w);w.workflow_step_text=text
        return w

    def workflow_window(self,title):
        w=tk.Toplevel(self.root);apply_child_icons(w);w.title(title);w.transient(self.root)
        self.display.size_window(w,720,580,(500,350));w.conversation_source=self.conversation
        body=scroll_frame(w,padding=12);body.pack(fill='both',expand=True)
        return w,body

    def edit_workflow_steps(self):
        record=self.workflow_record
        if not record or not record.get('steps'):raise ValueError('請先和主代理討論，產生步驟。')
        steps=copy.deepcopy(record['steps']);wid=record['id'];revision=record['revision']
        w,body=self.workflow_window('修改分工計畫');rows=[]
        ttk.Label(body,text='保存會使原批准失效；輸入來源必須指向較前面的步驟。',style='Muted.TLabel',wraplength=570).pack(anchor='w')
        for index,step in enumerate(steps):
            group=ttk.LabelFrame(body,text=f'{index+1}. {step["id"]}',padding=8);group.pack(fill='x',pady=6)
            title=tk.StringVar(value=step['title']);ttk.Entry(group,textvariable=title).pack(fill='x')
            order=tk.IntVar(value=index+1)
            ttk.Label(group,text='執行順序').pack(anchor='w');ttk.Combobox(group,values=list(range(1,len(steps)+1)),textvariable=order,state='readonly',width=5).pack(anchor='w')
            instruction=tk.Text(group,height=3,wrap='word');instruction.insert('1.0',step.get('instruction',''))
            if step['kind']=='assistant':instruction.pack(fill='x',pady=4)
            inputs=tk.StringVar(value=','.join(step.get('inputs',[])))
            ttk.Label(group,text='輸入步驟 ID（以逗號分隔）').pack(anchor='w');ttk.Entry(group,textvariable=inputs).pack(fill='x')
            row={'title':title,'instruction':instruction,'inputs':inputs,'order':order}
            if step['kind']=='assistant':
                available=[p for p in self.workflow_profiles if step.get('role') in p['workflow']['roles']]
                picker=ttk.Combobox(group,state='readonly',values=[p['name']+' · '+p['id'][-8:] for p in available]);picker.pack(fill='x',pady=4)
                selected=next((i for i,p in enumerate(available) if p['id']==step['binding']['profile_id']),None)
                if selected is not None:picker.current(selected)
                row.update(available=available,picker=picker)
            else:
                template=find_template(self.queries.catalog(),step['query_id']);vars={}
                for key,field in template['parameters'].items():
                    ttk.Label(group,text=field['label']).pack(anchor='w')
                    value=step.get('parameters',{}).get(key,initial_values(template).get(key,''))
                    if field['type']=='boolean':value='是' if value else '否'
                    var=tk.StringVar(value=value);vars[key]=var
                    choices=field.get('options') if field['type']=='single_choice' else ['是','否'] if field['type']=='boolean' else None
                    (ttk.Combobox(group,textvariable=var,values=choices,state='readonly') if choices else ttk.Entry(group,textvariable=var)).pack(fill='x')
                row.update(template=template,parameters=vars)
            rows.append(row)
        def save():
            orders=[row['order'].get() for row in rows]
            if sorted(orders)!=list(range(1,len(steps)+1)):raise ValueError('執行順序需從 1 開始且不重複。')
            for step,row in zip(steps,rows):
                step['title']=row['title'].get()
                step['inputs']=[s.strip() for s in row['inputs'].get().split(',') if s.strip()]
                if step['kind']=='assistant':
                    step['instruction']=row['instruction'].get('1.0','end-1c')
                    idx=row['picker'].current()
                    if idx<0:raise ValueError('請選擇已驗證的負責助理。')
                    step['binding']=self.profiles.workflow_binding(row['available'][idx]['id'])
                else:step['parameters']=parameters(row['template'],{k:v.get() for k,v in row['parameters'].items()},from_ui=True)
            ordered=[step for _,step in sorted(zip(orders,steps),key=lambda pair:pair[0])]
            self.workflows.update(wid,revision,ordered);self.workflow_consent.set(False);w.destroy();self.refresh_workflow_view(force=True)
        self.button(w,'保存修訂',save,'Primary.TButton').pack(side='bottom',pady=8);self.appearance.apply(w)

    def schedule_workflow(self):
        record=self.workflow_record;w,body=self.workflow_window('設為自動工作')
        name=tk.StringVar(value=record['goal'][:80]);frequency=tk.StringVar(value='每日');time=tk.StringVar(value='08:00');weekday=tk.StringVar(value='星期一');consent=tk.BooleanVar(value=False)
        for label,var,options in [('名稱',name,None),('頻率',frequency,['每日','每週']),('時間（台北 HH:MM）',time,None),('每週日期',weekday,['星期一','星期二','星期三','星期四','星期五','星期六','星期日'])]:
            ttk.Label(body,text=label).pack(anchor='w',pady=(8,2))
            (ttk.Combobox(body,textvariable=var,values=options,state='readonly') if options else ttk.Entry(body,textvariable=var)).pack(fill='x')
        ttk.Label(body,text='僅執行本版已成功試跑的計畫，不重新規劃。App 須保持開啟；失敗需處理。',wraplength=560).pack(anchor='w',pady=10)
        ttk.Checkbutton(body,text='授權每次將本版指定資料傳給列出的助理',variable=consent).pack(anchor='w')
        def save():
            if not consent.get():raise ValueError('請確認持續資料傳送授權。')
            self.workflows.schedule(record['id'],record['revision'],name.get(),{'每日':'daily','每週':'weekly'}[frequency.get()],time.get(),weekday=['星期一','星期二','星期三','星期四','星期五','星期六','星期日'].index(weekday.get()),consent=True)
            w.destroy();self.refresh_workflow_view();self.status.set('已啟用，尚未立即執行；可到自動工作按「立即執行」測試。')
        self.button(w,'確認啟用',save,'Primary.TButton').pack(side='bottom',pady=8);self.appearance.apply(w)

    def open_workflow_list(self):
        w,body=self.workflow_window('多助理流程紀錄')
        for conversation in self.store.conversations():
            for record in self.workflows.list(conversation['id']):
                self.button(body,record['goal'][:70]+' · '+STATES.get(record['state'],record['state']),lambda r=record:self.open_workflow_record(r,w),'Compact.TButton').pack(fill='x',pady=3)
        self.appearance.apply(w)

    def build_activity(self):
        super().build_activity()
        self.button(self.tabs['activity'],'多助理計畫與討論紀錄',self.open_workflow_list,'Compact.TButton').pack(anchor='w',pady=3)

    def open_workflow_record(self,record,window=None):
        if record['conversation_id']!=self.conversation:
            self.stash_draft();self.conversation=record['conversation_id'];self.restore_draft();self.show_chat()
        self.workflow_selected[self.conversation]=record['id'];self.workflow_mode.set('workflow')
        self.change_workflow_mode();self.book.select(self.tabs['chat'])
        if window:window.destroy()

    def show_workflow_result(self,tid):
        task=self.store.task(tid);w,body=self.workflow_window('多助理執行結果')
        steps=self.workflows.get_task_steps(tid)
        notebook=ttk.Notebook(body);notebook.pack(fill='both',expand=True)
        presenter=WorkflowPresenter(notebook,self,self.show_workflow_step)
        notebook.add(presenter,text='分工與成果')
        spec=task['payload']['workflow']
        presenter.update_record(dict(spec,task=task,steps_status=steps))
        full=ttk.Frame(notebook);notebook.add(full,text='完整成果文字')
        text=tk.Text(full,wrap='word',height=12);text.pack(side='left',fill='both',expand=True)
        scrollbar=ttk.Scrollbar(full,command=text.yview);scrollbar.pack(side='right',fill='y')
        text.configure(yscrollcommand=scrollbar.set)
        lines=[STATES.get(task['state'],task['state']),task.get('error') or '',(task.get('result') or {}).get('report','')]
        for step in steps:
            lines.extend(['\n步驟 '+step['step_id']+' · '+STATES.get(step['state'],step['state']),
                          (step.get('output') or {}).get('text',''),step.get('error') or '',
                          '本步輸入：'+self.workflow_output(step.get('input'))])
            if (step.get('output') or {}).get('query_result'):
                self.button(w,'查看 '+step['step_id']+' 原始表格',lambda s=step:self.show_workflow_table(s['output']['query_result']),'Compact.TButton').pack(side='bottom',pady=3)
        text.insert('1.0','\n'.join(lines))
        self.button(w,'複製成果',lambda:self.clipboard((task.get('result') or {}).get('report') or text.get('1.0','end-1c')),'Compact.TButton').pack(side='bottom',pady=3)
        text.configure(state='disabled');self.appearance.apply(w);w.workflow_steps_view=presenter
        return w

    def show_workflow_table(self,result):
        """Render a retained snapshot; use the same safe CSV/TSV exporters as ordinary queries."""
        from tkinter import filedialog
        from .files import render_csv,render_tsv
        result=copy.deepcopy(result)
        names=[c['name'] for c in result['columns']]
        result['rows']=[[r[n] for n in names] if isinstance(r,dict) else r for r in result['rows']]
        w=tk.Toplevel(self.root);apply_child_icons(w);w.title('流程原始表格 · 固定快照');w.transient(self.root)
        self.display.size_window(w,800,540,(500,350))
        footer=ttk.Frame(w,padding=8);footer.pack(side='bottom',fill='x')
        ttk.Label(w,text='資料時間：'+str(result.get('fetched_at_utc',''))+' · 共 '+str(len(result['rows']))+' 列\n條件：'+json.dumps(result.get('parameters',{}),ensure_ascii=False),wraplength=650).pack(fill='x',padx=8,pady=6)
        body=ttk.Frame(w);body.pack(fill='both',expand=True,padx=8)
        cols=[str(i) for i in range(len(names))];table=ttk.Treeview(body,columns=cols,show='headings',selectmode='extended')
        table.grid(row=0,column=0,sticky='nsew');body.rowconfigure(0,weight=1);body.columnconfigure(0,weight=1)
        vs=ttk.Scrollbar(body,command=table.yview);vs.grid(row=0,column=1,sticky='ns')
        hs=ttk.Scrollbar(body,orient='horizontal',command=table.xview);hs.grid(row=1,column=0,sticky='ew')
        table.configure(yscrollcommand=vs.set,xscrollcommand=hs.set)
        for c,column in zip(cols,result['columns']):table.heading(c,text=column.get('label',column['name']));table.column(c,width=150,minwidth=80)
        page=[0];selection=set();label=ttk.Label(footer)
        def render(delta=0):
            visible={int(i) for i in table.get_children()};selection.difference_update(visible);selection.update(int(i) for i in table.selection())
            total=max(1,(len(result['rows'])+99)//100);page[0]=max(0,min(total-1,page[0]+delta))
            table.delete(*table.get_children())
            for index in range(page[0]*100,min((page[0]+1)*100,len(result['rows']))):table.insert('','end',iid=str(index),values=result['rows'][index])
            table.selection_set([str(i) for i in selection if str(i) in table.get_children()])
            label.configure(text=f'{page[0]+1} / {total}')
        def copy_rows(selected=False):
            if selected:
                visible={int(i) for i in table.get_children()};selection.difference_update(visible);selection.update(int(i) for i in table.selection())
                if not selection:raise ValueError('請先選取資料列。')
            self.clipboard(render_tsv(result,sorted(selection) if selected else None)[0])
        def export():
            path=filedialog.asksaveasfilename(parent=w,defaultextension='.csv',filetypes=[('CSV','*.csv')])
            if path:
                from pathlib import Path
                data=render_csv(result)
                self.background(lambda:Path(path).write_text(data,encoding='utf-8-sig',newline=''),lambda _:self.status.set('流程表格已匯出。'))
        self.button(footer,'上一頁',lambda:render(-1),'Compact.TButton').pack(side='left')
        label.pack(side='left',padx=4)
        self.button(footer,'下一頁',lambda:render(1),'Compact.TButton').pack(side='left')
        self.button(footer,'複製全部',copy_rows,'Compact.TButton').pack(side='left',padx=4)
        self.button(footer,'複製選取',lambda:copy_rows(True),'Compact.TButton').pack(side='left')
        self.button(footer,'匯出 CSV',export,'Compact.TButton').pack(side='left',padx=4)
        render();self.appearance.apply(w);w.workflow_table=table;w.workflow_copy=copy_rows;w.workflow_page=render
        return w

    def edit_workflow_capability(self):
        self.require_profile_edit();pid=self.selected_profile()
        item=next(p for p in self.profiles.items() if p['id']==pid);current=item.get('workflow',{})
        w,body=self.workflow_window('助理分工能力');variables={}
        ttk.Label(body,text='角色是用途宣告，不代表已驗證能力。修改後需公司重新完成能力驗證，才可參與自動流程。',wraplength=560).pack(anchor='w',pady=8)
        for role,label in ROLES.items():
            var=tk.BooleanVar(value=role in current.get('roles',[]));variables[role]=var
            ttk.Checkbutton(body,text=label,variable=var).pack(anchor='w',pady=3)
        ttk.Label(body,text='目前狀態：'+('已驗證' if current.get('verified') else '待公司驗證'),style='Muted.TLabel').pack(anchor='w',pady=8)
        def save():
            self.require_profile_edit();self.profiles.set_workflow_capability(pid,[role for role,var in variables.items() if var.get()],verified=False)
            self.refresh_workflow_catalog();self.refresh_profiles();w.destroy()
        self.button(w,'保存角色（需要重新驗證）',save,'Primary.TButton').pack(side='bottom',pady=8);self.appearance.apply(w)
