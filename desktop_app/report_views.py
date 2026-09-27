"""An explicit editable confirmation card for recurring external-AI data transfer."""
from datetime import datetime,timedelta
import tkinter as tk
from tkinter import ttk
from .branding import apply_child_icons
from .display import scroll_frame
from .gateways import GatewayError
from .core import TAIPEI
from .report_drafts import extract_draft


class ReportViews:
    def open_report_schedule(self, text=None):
        if not self.groq_trial:raise GatewayError('日報測試目前只在 Groq 試用入口提供。')
        if self.editing_plan:raise GatewayError('請先保存或退出目前的 Plan 修改。')
        cid=self.conversation
        for existing in self.root.winfo_children():
            if isinstance(existing,tk.Toplevel) and hasattr(existing,'report_controls') and getattr(existing,'handoff_source',{}).get('conversation_id')==cid:
                existing.lift();return existing
        w=tk.Toplevel(self.root);apply_child_icons(w);w.title('建立日報排程 · 合成資料')
        w.transient(self.root);self.display.size_window(w,850,700,(650,500))
        w.handoff_source={'kind':'conversation','conversation_id':cid}
        footer=ttk.Frame(w,padding=(18,10));footer.pack(side='bottom',fill='x')
        body=scroll_frame(w,padding=18);body.pack(fill='both',expand=True)
        ttk.Label(body,text='說出需求 → 核對條件 → 確認啟用',style='Section.TLabel').pack(anchor='w')
        ttk.Label(body,text='解析需求會呼叫 Groq；確認啟用前不查資料、不建立排程。',wraplength=730).pack(anchor='w',pady=6)
        request=tk.Text(body,height=3,wrap='word');request.pack(fill='x')
        request.insert('1.0',text if text is not None else '每天早上八點查昨天的 A 類數量合計，整理成日報。')
        request.edit_modified(False)
        message=tk.StringVar(value='可解析需求，也可直接填下方條件。只支援每日查前一日。')
        ttk.Label(body,textvariable=message,wraplength=700,style='Muted.TLabel').pack(fill='x',pady=6)
        values={'query_id':tk.StringVar(value=''),'time_hhmm':tk.StringVar(value=''),
                'category':tk.StringVar(value='all'),'name':tk.StringVar(value='每日合成資料日報')}
        labels={q['name']:q['id'] for q in self.queries.catalog()}; query_name=tk.StringVar()
        state={'token':None,'busy':False,'revision':0,'saved':False}
        def invalidate(*args):
            state['revision']+=1
            consent.set(False) if args and consent.get() else None
            if state['token']:self.engine.cancel_report(state['token']);state['token']=None
            if not state['saved']:confirm.configure(state='disabled')
        def edited(event=None):
            if request.edit_modified():request.edit_modified(False);invalidate('request')
        request.bind('<<Modified>>',edited)
        def parse():
            if state['busy'] or state['saved']:return
            raw=request.get('1.0','end-1c').strip()
            if not raw or len(raw)>2000:raise GatewayError('請提供 1～2,000 字需求。')
            invalidate();revision=state['revision'];state['busy']=True;parse_button.configure(state='disabled')
            message.set('Groq 正在整理條件；尚未啟用排程…')
            def work():
                try:return extract_draft(raw),None
                except GatewayError as exc:return None,str(exc)
                except Exception:return None,'解析未完成；請手動填寫，沒有建立排程。'
            def done(outcome):
                if not w.winfo_exists():return
                state['busy']=False;parse_button.configure(state='normal')
                if state['revision']!=revision:message.set('需求已改變，舊解析結果不套用。');return
                result,error=outcome
                if error:message.set(error);return
                self.store.conversation(cid)
                query_name.set(next((n for n,i in labels.items() if i==result['query_id']),''))
                values['query_id'].set(result['query_id'] or '')
                values['time_hhmm'].set(result['time_hhmm'] or '')
                values['category'].set(result['category'] or '')
                questions=result['questions'][:6]
                if result['frequency']!='daily' or result['date_mode']!='previous_day':
                    questions.append('目前僅支援每日查前一日；請確認是否改用這個範圍。')
                message.set('請補充／核對：'+'；'.join(questions) if questions else '條件已整理。請核對後按「預覽排程」。')
            self.background(work,done)
        parse_button=self.button(body,'解析需求',parse);parse_button.pack(anchor='w',pady=(0,8))
        form=ttk.Frame(body);form.pack(fill='x');form.columnconfigure(1,weight=1)
        for row,(key,label) in enumerate([('name','排程名稱'),('query_id','合成查詢'),('category','類別'),('time_hhmm','台北時間 HH:MM')]):
            ttk.Label(form,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=4)
            if key=='query_id':
                control=ttk.Combobox(form,textvariable=query_name,values=list(labels),state='readonly')
                control.bind('<<ComboboxSelected>>',lambda e:values['query_id'].set(labels[query_name.get()]))
            elif key=='category':control=ttk.Combobox(form,textvariable=values[key],values=['all','A','B'],state='readonly')
            else:control=ttk.Entry(form,textvariable=values[key])
            control.grid(row=row,column=1,sticky='ew')
        consent=tk.BooleanVar(value=False)
        ttk.Checkbutton(body,text='我確認每天查前一日，並允許每次將彙總資料交給 Groq 整理。',variable=consent).pack(anchor='w',pady=8)
        ttk.Label(body,text='僅傳查詢條件、資料時間、筆數與程式計算的數值合計，不傳逐筆明細。\n日報與原始結果保存在本機；每次完成／失敗會通知。App 必須開啟。',wraplength=730,style='Muted.TLabel').pack(anchor='w')
        preview=tk.Text(body,height=6,wrap='word',state='disabled');preview.pack(fill='both',expand=True,pady=8)
        def prepare():
            if state['busy']:raise GatewayError('請等解析完成再預覽。')
            if not consent.get():raise GatewayError('請先確認每日範圍與資料傳送授權。')
            self.store.conversation(cid);invalidate()
            day=datetime.now(TAIPEI).date()
            spec={k:v.get().strip() for k,v in values.items() if k!='category'}
            spec['parameters']={'from_date':(day-timedelta(days=1)).isoformat(),'to_date':day.isoformat(),'category':values['category'].get()}
            proposal=self.engine.preview_report(spec,{'profile_id':'groq-trial','revision':1})
            state['token']=proposal['token']
            preview.configure(state='normal');preview.delete('1.0','end')
            preview.insert('1.0',f"{spec['name']}\n每天 {spec['time_hhmm']}（台北），查執行日前一天\n查詢：{query_name.get()}；類別：{values['category'].get()}\n整理助理：Groq 試用助理 · 固定連線版本 1\n每次僅傳送上述彙總資料，不含本段對話。\n目前尚未啟用；確認卡 10 分鐘內有效。")
            preview.configure(state='disabled');confirm.configure(state='normal')
        def approve():
            if not consent.get() or not state['token'] or state['saved']:raise GatewayError('請重新預覽。')
            self.store.conversation(cid)
            sid=self.engine.confirm_report(state['token']);state['saved']=True;confirm.configure(state='disabled')
            self.refresh_lists();self.book.select(self.tabs['schedule']);self.schedules.selection_set(sid)
            self.status.set('日報排程已啟用；可按「立即執行」先測試一次。');w.destroy()
        self.button(footer,'預覽排程',prepare).pack(side='left')
        confirm=self.button(footer,'確認啟用',approve,'Primary.TButton');confirm.pack(side='right');confirm.configure(state='disabled')
        self.button(footer,'取消',w.destroy,'Quiet.TButton').pack(side='right',padx=8)
        for variable in values.values():variable.trace_add('write',invalidate)
        consent.trace_add('write',lambda *args:invalidate())
        def destroyed(event):
            if event.widget==w and state['token'] and not state['saved']:self.engine.cancel_report(state['token'])
        w.bind('<Destroy>',destroyed)
        self.appearance.apply(w)
        w.report_controls={'request':request,'values':values,'query_name':query_name,'consent':consent,
                           'parse':parse,'preview':prepare,'approve':approve,'state':state,'confirm':confirm,'message':message}
        return w
