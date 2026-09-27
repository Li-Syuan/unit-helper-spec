"""User-confirmed local history cleanup; dispatch never occurs from this view."""
import tkinter as tk
from tkinter import ttk
from .branding import apply_child_icons


class ConversationViews:
    def history_context(self, event):
        index=self.history.nearest(event.y)
        bounds=self.history.bbox(index)
        if not bounds or event.y>bounds[1]+bounds[3] or index>=len(self.conversation_ids):return
        cid=self.conversation_ids[index]
        menu=tk.Menu(self.root,tearoff=False)
        menu.add_command(label='刪除此對話',command=lambda:self.safe(lambda:self.confirm_conversation_deletion([cid])))
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:menu.grab_release()

    def manage_conversations(self):
        previous=getattr(self,'conversation_manager',None)
        if previous is not None and previous.winfo_exists():previous.lift();return previous
        w=tk.Toplevel(self.root);apply_child_icons(w);w.title('QA agent · 管理對話');w.transient(self.root)
        self.display.size_window(w,820,570,(600,420))
        body=ttk.Frame(w,padding=16);body.pack(fill='both',expand=True)
        search=tk.StringVar();chosen=set()
        row=ttk.Frame(body);row.pack(fill='x')
        ttk.Label(row,text='搜尋標題').pack(side='left')
        entry=ttk.Entry(row,textvariable=search);entry.pack(side='left',fill='x',expand=True,padx=8)
        count=ttk.Label(body,style='Muted.TLabel');count.pack(anchor='w',pady=8)
        holder=ttk.Frame(body);holder.pack(fill='both',expand=True)
        tree=ttk.Treeview(holder,columns=('check','title','time'),show='headings',selectmode='browse')
        for key,label,width in [('check','勾選',65),('title','對話標題',410),('time','建立時間 UTC',180)]:
            tree.heading(key,text=label);tree.column(key,width=width,minwidth=50,stretch=key=='title')
        tree.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(holder,command=tree.yview);scroll.pack(side='right',fill='y');tree.configure(yscrollcommand=scroll.set)
        horizontal=ttk.Scrollbar(body,orient='horizontal',command=tree.xview)
        horizontal.pack(fill='x');tree.configure(xscrollcommand=horizontal.set)
        def render(*args):
            existing={c['id'] for c in self.store.conversations()};chosen.intersection_update(existing)
            rows=[c for c in self.store.conversations() if search.get().casefold() in c['title'].casefold()]
            # Filtering clears hidden selections so confirmation never surprises.
            chosen.intersection_update(c['id'] for c in rows)
            tree.delete(*tree.get_children())
            for c in rows:tree.insert('','end',iid=c['id'],values=('☑' if c['id'] in chosen else '☐',c['title'],c['created_at'][:19]))
            count.configure(text=f'顯示 {len(rows)} 筆 · 已勾選 {len(chosen)} 筆；只管理目前電腦的對話。')
            remove.configure(state='normal' if chosen else 'disabled')
        def toggle(cid):
            if not cid:return
            if cid in chosen:chosen.remove(cid)
            else:chosen.add(cid)
            render();tree.selection_set(cid);tree.focus(cid)
        def click(event):
            if tree.identify_column(event.x)=='#1':toggle(tree.identify_row(event.y));return 'break'
        tree.bind('<Button-1>',click)
        tree.bind('<space>',lambda e:(toggle(tree.focus()),'break')[-1])
        actions=ttk.Frame(body);actions.pack(fill='x',pady=(12,0))
        def all_visible():chosen.update(tree.get_children());render()
        self.button(actions,'全選搜尋結果',all_visible).pack(side='left')
        self.button(actions,'取消勾選',lambda:(chosen.clear(),render())).pack(side='left',padx=6)
        remove=self.button(actions,'刪除勾選對話',lambda:self.confirm_conversation_deletion(sorted(chosen)),'Danger.TButton');remove.pack(side='right')
        self.button(actions,'關閉',w.destroy,'Quiet.TButton').pack(side='right',padx=6)
        search.trace_add('write',render);render()
        w.history_search=search;w.history_tree=tree;w.history_chosen=chosen;w.history_refresh=render
        w.history_toggle=toggle;w.history_select_all=all_visible;w.history_delete=remove
        self.conversation_manager=w;self.appearance.apply(w);entry.focus_set();return w

    def confirm_conversation_deletion(self, ids):
        preview=self.engine.preview_conversation_deletion(ids)
        w=tk.Toplevel(self.root);apply_child_icons(w);w.title('永久刪除本機對話');w.transient(self.root)
        self.display.size_window(w,660,480,(520,360))
        body=ttk.Frame(w,padding=20);body.pack(fill='both',expand=True)
        ttk.Label(body,text='永久刪除後，無法由應用復原。',style='CardError.TLabel').pack(anchor='w')
        counts=preview['counts']
        ttk.Label(body,text=f"{counts['conversations']} 段對話 · {counts['messages']} 則訊息 · {counts['plans']} 份計畫\n{counts['tasks']} 項工作（含輸入／結果）· {counts['notifications']} 則通知",justify='left').pack(anchor='w',pady=10)
        holder=ttk.Frame(body);holder.pack(fill='both',expand=True)
        names=tk.Listbox(holder,height=4,exportselection=False)
        for c in preview['conversations']:names.insert('end',c['title'])
        names.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(holder,command=names.yview);scroll.pack(side='right',fill='y');names.configure(yscrollcommand=scroll.set)
        horizontal=ttk.Scrollbar(body,orient='horizontal',command=names.xview)
        horizontal.pack(fill='x');names.configure(xscrollcommand=horizontal.set)
        boundary=ttk.Label(body,text='原始附件、匯出、既有備份、獨立查詢與排程保留。\n其他對話的轉交副本與公司端歷史不會刪除。',wraplength=460,style='Muted.TLabel',justify='left')
        boundary.pack(anchor='w',pady=10)
        body.bind('<Configure>',lambda e:boundary.configure(wraplength=max(100,e.width-self.display.px(40))),add='+')
        row=ttk.Frame(body);row.pack(fill='x')
        cancel=self.button(row,'取消',w.destroy);cancel.pack(side='right')
        def remove():
            # Service rechecks the exact preview and live futures inside its lock.
            result=self.engine.delete_conversations(preview['token'])
            w.destroy();self.conversations_deleted(result)
        confirm=self.button(row,'永久刪除',remove,'Danger.TButton');confirm.pack(side='right',padx=8)
        w.delete_preview=preview;w.delete_confirm=confirm;w.delete_cancel=cancel
        w.bind('<Escape>',lambda e:w.destroy());w.grab_set();self.appearance.apply(w)
        w.update_idletasks();cancel.focus_set();return w

    def conversations_deleted(self, result):
        deleted=set(result['deleted_ids']);task_ids=set(result['task_ids']);plan_ids=set(result['plan_ids'])
        for cid in deleted:self.drafts.pop(cid,None)
        for tid in task_ids:self.seen.pop(tid,None)
        if self.editing_plan and self.editing_plan[0] in plan_ids:self.discard_edit()
        if self.preview_plan and self.preview_plan[0] in plan_ids:
            self.preview_plan=None
            self.plan_preview.configure(state='normal');self.plan_preview.delete('1.0','end');self.plan_preview.configure(state='disabled')
        if self.workspace_selection and self.workspace_selection[1] in task_ids|plan_ids:self.close_detail()
        # All open handoff previews are tracked (there can be more than one).
        for window in list(getattr(self,'handoff_windows',[])):
            if not window.winfo_exists():continue
            source=getattr(window,'handoff_source',{}) or {}
            if source.get('conversation_id') in deleted or source.get('task_id') in task_ids:window.destroy()
        for window in self.root.winfo_children():
            if isinstance(window,tk.Toplevel) and getattr(window,'conversation_source',None) in deleted:window.destroy()
        if self.result_task in task_ids:
            self.result_task=None;self.result=None;self.page=0;self.render_page()
            self.result_meta.set('所選對話的結果已刪除。')
            self.output.configure(state='normal');self.output.delete('1.0','end');self.output.configure(state='disabled')
            self.text_copy.configure(state='disabled');self.text_save.configure(state='disabled')
        if self.conversation in deleted:
            self.conversation=None;self.attachment=None
            self.input.delete('1.0','end');self.refresh_history()
            if self.conversation_ids:
                self.conversation=self.conversation_ids[0];self.restore_draft();self.history.selection_set(0);self.show_chat()
            else:self.new_chat()
        else:
            self.refresh_history()
            if self.conversation in self.conversation_ids:self.history.selection_set(self.conversation_ids.index(self.conversation))
            self.show_chat()
        self.refresh_lists()
        manager=getattr(self,'conversation_manager',None)
        if manager is not None and manager.winfo_exists():manager.history_refresh()
        self.status.set(f'已永久刪除 {len(deleted)} 段本機對話。其他對話與獨立查詢／排程保留。')

    def source_description(self, source):
        if isinstance(source,dict) and source.get('kind')=='conversation':
            try:self.store.conversation(source.get('conversation_id'))
            except ValueError:return '來源對話已刪除；此對話的已轉交副本保留。'
        return str(source)
