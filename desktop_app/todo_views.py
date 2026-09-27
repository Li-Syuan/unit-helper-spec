"""Local personal todo board. No model calls, dispatch or schedule creation."""
from datetime import date, datetime, timedelta, timezone
import tkinter as tk
from tkinter import ttk
import uuid

from .branding import apply_child_icons
from .display import scroll_frame
from .preferences import load_preferences, update_preferences


TODO_STATES = {'todo': '待處理', 'ongoing': '進行中', 'done': '已完成'}


def taipei_today(now=None):
    """Use Taipei's calendar date even when Windows uses another time zone."""
    current = datetime.now(timezone.utc) if now is None else now
    if current.tzinfo is None:
        raise ValueError('待辦時鐘必須包含時區。')
    return current.astimezone(timezone(timedelta(hours=8))).date()


class TodoViews:
    def todo_today(self):
        # A small injectable seam for midnight and local-time-zone tests.
        return taipei_today()

    def build_todos(self):
        page = self.tabs['todo']
        self.todo_search = tk.StringVar(master=self.root)
        saved = load_preferences(self.preferences_path).get('todo_show_done', True)
        self.todo_show_done = tk.BooleanVar(master=self.root, value=saved if type(saved) is bool else True)
        self.todo_active_state = 'todo'
        self.todo_selected_id = None
        self._todo_signature = None
        self._todo_wide = None
        self.todo_cards = {}
        self.todo_columns = {}
        toolbar = ttk.Frame(page)
        toolbar.pack(fill='x', pady=(0, 8))
        self.button(toolbar, '新增待辦', self.open_todo, 'Primary.TButton').pack(side='right')
        ttk.Label(toolbar, text='搜尋待辦').pack(side='left')
        self.todo_search_entry = ttk.Entry(toolbar, textvariable=self.todo_search, width=16)
        self.todo_search_entry.pack(side='left', fill='x', expand=True, padx=8)
        ttk.Checkbutton(toolbar, text='顯示已完成', variable=self.todo_show_done,
                        command=self._todo_done_changed).pack(side='left', padx=(0, 8))
        self.todo_summary = ttk.Label(page, style='Muted.TLabel')
        self.todo_summary.pack(anchor='w', pady=(0, 8))
        self.todo_state_tabs = ttk.Frame(page)
        self.todo_tab_buttons = {}
        for state, label in TODO_STATES.items():
            button = self.button(self.todo_state_tabs, label,
                                 lambda state=state: self._todo_select_state(state), 'Compact.TButton')
            button.pack(side='left', padx=(0, 8))
            self.todo_tab_buttons[state] = button
        self.todo_board = ttk.Frame(page)
        self.todo_board.pack(fill='both', expand=True)
        self.todo_board.rowconfigure(0, weight=1)
        for state, label in TODO_STATES.items():
            column = ttk.Frame(self.todo_board)
            column.columnconfigure(0, weight=1)
            column.rowconfigure(1, weight=1)
            heading = ttk.Label(column, text=label, style='Section.TLabel')
            heading.grid(row=0, column=0, sticky='w', pady=(0, 8))
            canvas = tk.Canvas(column, width=1, height=1, highlightthickness=0)
            canvas.grid(row=1, column=0, sticky='nsew')
            scrollbar = ttk.Scrollbar(column, command=canvas.yview)
            scrollbar.grid(row=1, column=1, sticky='ns')
            canvas.configure(yscrollcommand=scrollbar.set)
            inner = ttk.Frame(canvas)
            item = canvas.create_window(0, 0, window=inner, anchor='nw')
            inner.bind('<Configure>', lambda e, c=canvas: c.configure(scrollregion=c.bbox('all')))
            canvas.bind('<Configure>', lambda e, c=canvas, i=item: c.itemconfigure(i, width=max(1, e.width)))
            canvas.bind('<MouseWheel>', lambda e, c=canvas: self._todo_wheel(e, c))
            self.todo_columns[state] = {'frame': column, 'canvas': canvas, 'body': inner, 'heading': heading}
        self.todo_board.bind('<Configure>', self._todo_layout)
        self.todo_search.trace_add('write', lambda *args: self.refresh_todos())
        self.refresh_todos()

    @staticmethod
    def _todo_wheel(event, canvas):
        if event.delta:
            canvas.yview_scroll(-1 if event.delta > 0 else 1, 'units')
        return 'break'

    def _todo_done_changed(self):
        try:
            update_preferences(self.preferences_path, {'todo_show_done': self.todo_show_done.get()})
        except OSError:
            self.status.set('已套用待辦顯示方式，但無法保存偏好；下次開啟可能恢復原設定。')
        self.refresh_todos()

    def _todo_select_state(self, state):
        if state == 'done' and not self.todo_show_done.get():
            return
        self.todo_active_state = state
        self._todo_layout(force=True)

    def _todo_layout(self, event=None, force=False):
        width = event.width if event is not None else self.todo_board.winfo_width()
        wide = width >= self.display.px(900)
        if wide == self._todo_wide and not force:
            return
        self._todo_wide = wide
        states = [s for s in TODO_STATES if s != 'done' or self.todo_show_done.get()]
        if self.todo_active_state not in states:
            self.todo_active_state = 'todo'
        if wide:
            self.todo_state_tabs.pack_forget()
        else:
            self.todo_state_tabs.pack(fill='x', pady=(0, self.display.px(8)), before=self.todo_board)
        for index in range(3):
            self.todo_board.columnconfigure(index, weight=0, uniform='')
        for state, column in self.todo_columns.items():
            column['frame'].grid_remove()
            button = self.todo_tab_buttons[state]
            button.configure(style='Primary.TButton' if state == self.todo_active_state else 'Compact.TButton')
            if state in states:
                button.pack(side='left', padx=(0, self.display.px(8)))
            else:
                button.pack_forget()
        visible = states if wide else [self.todo_active_state]
        for index, state in enumerate(visible):
            self.todo_board.columnconfigure(index, weight=1, uniform='todo-columns')
            self.todo_columns[state]['frame'].grid(row=0, column=index, sticky='nsew',
                padx=(0, self.display.px(8) if index < len(visible) - 1 else 0))

    def _todo_source(self, cid):
        if not cid:
            return '手動新增'
        try:
            return '來源對話：' + self.store.conversation(cid)['title']
        except ValueError:
            return '來源對話已刪除'

    def open_todo_source(self, cid):
        # Recheck before navigation: source deletion never deletes this todo.
        self.store.conversation(cid)
        self.stash_draft()
        self.editing_plan = None
        self.conversation = cid
        self.restore_draft()
        self.refresh_history()
        self.history.selection_clear(0, 'end')
        if cid in self.conversation_ids:
            self.history.selection_set(self.conversation_ids.index(cid))
        self.show_chat()
        self.book.select(self.tabs['chat'])

    def _refresh_todo_sources(self):
        for window in list(getattr(self, 'todo_windows', {}).values()):
            if not window.winfo_exists():
                continue
            cid = window.todo_source_conversation_id
            source = self._todo_source(cid)
            window.todo_source.configure(text=source)
            window.todo_source_button.configure(state='normal' if cid and source != '來源對話已刪除' else 'disabled')

    def refresh_todos(self):
        if not hasattr(self, 'todo_board'):
            return
        self._refresh_todo_sources()
        rows = self.store.todos(search=self.todo_search.get())
        sources = {item['id']: self._todo_source(item.get('source_conversation_id')) for item in rows}
        # Polling callers may refresh often: never rebuild an unchanged board.
        signature = (repr(rows), tuple(sources.items()), self.todo_show_done.get(), self.todo_today().isoformat())
        if signature == self._todo_signature:
            return
        self._todo_signature = signature
        views = {state: col['canvas'].yview()[0] for state, col in self.todo_columns.items()}
        for column in self.todo_columns.values():
            for child in column['body'].winfo_children():
                child.destroy()
        self.todo_cards = {}
        for state, column in self.todo_columns.items():
            entries = [item for item in rows if item['state'] == state]
            if state == 'todo':
                entries.sort(key=lambda item: (item.get('due_date') is None, item.get('due_date') or '',
                                                item['created_at'], item['id']))
            else:
                order_key = 'updated_at' if state == 'ongoing' else 'completed_at'
                entries.sort(key=lambda item: (item.get(order_key) or '', item['created_at'], item['id']), reverse=True)
            column['heading'].configure(text=f'{TODO_STATES[state]} · {len(entries)}')
            self.todo_tab_buttons[state].configure(text=f'{TODO_STATES[state]} {len(entries)}')
            for item in entries:
                self._todo_card(column, item, sources[item['id']])
            if not entries:
                ttk.Label(column['body'], text='目前沒有符合條件的待辦。', style='Muted.TLabel',
                          wraplength=220).pack(anchor='w', pady=12)
            column['body'].update_idletasks()
            column['canvas'].yview_moveto(views[state])
        hidden = sum(item['state'] == 'done' for item in rows) if not self.todo_show_done.get() else 0
        self.todo_summary.configure(text=f'共 {len(rows)} 筆' + (f' · 隱藏 {hidden} 筆已完成' if hidden else '') + ' · 待辦僅記錄事項，不會自動執行。')
        self._todo_layout(force=True)
        self.appearance.apply(self.tabs['todo'])

    def _todo_card(self, column, item, source):
        tid = item['id']
        card = ttk.Frame(column['body'], style='Card.TFrame', padding=12, takefocus=True)
        card.pack(fill='x', pady=(0, 8))
        title = ttk.Label(card, text=item['title'], style='CardTitle.TLabel', wraplength=220, cursor='hand2')
        title.pack(fill='x')
        due = item.get('due_date')
        overdue = bool(due and due < self.todo_today().isoformat() and item['state'] != 'done')
        due_label = ttk.Label(card, text=('已逾期 · ' if overdue else '期限 · ') + due if due else '未設定期限',
                              style='CardError.TLabel' if overdue else 'CardMuted.TLabel')
        due_label.pack(anchor='w', pady=(8, 4))
        source_label = ttk.Label(card, text=source, style='CardMuted.TLabel', wraplength=220)
        source_label.pack(fill='x')
        actions = ttk.Frame(card, style='CardBody.TFrame')
        actions.pack(fill='x', pady=(8, 0))
        self.button(actions, '查看／編輯', lambda: self.open_todo(tid), 'Compact.TButton').pack(side='left')
        if item['state'] == 'todo':
            label, target = '開始', 'ongoing'
        elif item['state'] == 'ongoing':
            label, target = '完成', 'done'
        else:
            label, target = '重新開啟', 'todo'
        action = self.button(actions, label, lambda: self._todo_transition(tid, target), 'Compact.TButton')
        action.pack(side='right')
        def select(event=None):
            self.todo_selected_id = tid
            self.todo_active_state = item['state']
        card.bind('<FocusIn>', select)
        card.bind('<Button-1>', lambda e: (select(), card.focus_set()))
        card.bind('<Return>', lambda e: self.safe(lambda: self.open_todo(tid)))
        title.bind('<Button-1>', lambda e: (select(), self.safe(lambda: self.open_todo(tid))))
        def resize(event):
            width = max(self.display.px(60), event.width - self.display.px(26))
            title.configure(wraplength=width)
            source_label.configure(wraplength=width)
        card.bind('<Configure>', resize)
        def wheel_bind(widget):
            widget.bind('<MouseWheel>', lambda e: self._todo_wheel(e, column['canvas']), add='+')
            for child in widget.winfo_children():
                wheel_bind(child)
        wheel_bind(card)
        self.todo_cards[tid] = card
        card.todo_action = action
        card.todo_title = title
        card.todo_due = due_label
        card.todo_source = source_label

    def _todo_transition(self, tid, state):
        self.store.set_todo_state(tid, state)
        self.todo_selected_id = tid
        self.refresh_todos()
        self.status.set('待辦已更新為「' + TODO_STATES[state] + '」。')

    def add_selected_todo(self):
        selected = self.transcript.tag_ranges('sel')
        if not selected:
            raise ValueError('請先在對話中選取要加入待辦的文字。')
        text = self.transcript.get(selected[0], selected[-1])
        if not text.strip():
            raise ValueError('選取內容只有空白，請選取需要處理的事項。')
        return self.open_todo(text=text, source_conversation_id=self.conversation)

    def _todo_saved_notice(self, tid):
        self.status.set('已保存待辦；不會自動執行或送給助理。')
        previous = getattr(self, 'todo_saved_notice', None)
        if previous is not None and previous.winfo_exists():
            previous.destroy()
        parent = getattr(self, 'chat_column', self.tabs.get('chat'))
        if parent is None:
            return
        row = ttk.Frame(parent, style='Card.TFrame', padding=6)
        options = {'before': self.composer} if getattr(self, 'composer', None) is not None else {}
        row.pack(side='bottom', fill='x', pady=(4, 0), **options)
        ttk.Label(row, text='已加入我的待辦', style='CardMuted.TLabel').pack(side='left')
        self.button(row, '查看待辦', lambda: self.show_todo(tid), 'Compact.TButton').pack(side='right')
        self.button(row, '關閉', row.destroy, 'Quiet.TButton').pack(side='right', padx=4)
        self.todo_saved_notice = row
        self.appearance.apply(row)

    def show_todo(self, tid):
        item = self.store.todo(tid)
        self.todo_search.set('')
        if item['state'] == 'done' and not self.todo_show_done.get():
            self.todo_show_done.set(True)
            self._todo_done_changed()
        self.todo_selected_id = tid
        self.todo_active_state = item['state']
        self.refresh_todos()
        self._todo_layout(force=True)
        self.book.select(self.tabs['todo'])
        self.open_todo(tid)

    def open_todo(self, todo_id=None, text='', source_conversation_id=None):
        windows = getattr(self, 'todo_windows', {})
        self.todo_windows = windows
        if todo_id in windows and windows[todo_id].winfo_exists():
            windows[todo_id].lift()
            return windows[todo_id]
        item = self.store.todo(todo_id) if todo_id else None
        if item:
            source_conversation_id = item.get('source_conversation_id')
        initial_title = item['title'] if item else next((line.strip() for line in text.splitlines() if line.strip()), '')
        w = tk.Toplevel(self.root)
        apply_child_icons(w)
        w.title('QA agent · ' + ('編輯待辦' if item else '新增待辦'))
        w.transient(self.root)
        self.display.size_window(w, 680, 620, (480, 400))
        body = scroll_frame(w, padding=16)
        body.pack(fill='both', expand=True)
        title = tk.StringVar(master=w, value=initial_title)
        due = tk.StringVar(master=w, value=item.get('due_date') or '' if item else '')
        state = tk.StringVar(master=w, value=TODO_STATES[item['state']] if item else TODO_STATES['todo'])
        error = tk.StringVar(master=w)
        ttk.Label(body, text='標題（必填，最多 120 字）').pack(anchor='w')
        title_entry = ttk.Entry(body, textvariable=title, width=30)
        title_entry.pack(fill='x', pady=(4, 10))
        ttk.Label(body, text='說明（最多 50,000 字，選取的原文完整保留）').pack(anchor='w')
        holder = ttk.Frame(body)
        holder.pack(fill='both', expand=True, pady=(4, 10))
        description = tk.Text(holder, height=7, width=36, wrap='word', undo=True)
        description.pack(side='left', fill='both', expand=True)
        bar = ttk.Scrollbar(holder, command=description.yview)
        bar.pack(side='right', fill='y')
        description.configure(yscrollcommand=bar.set)
        description.insert('1.0', item['description'] if item else text)
        row = ttk.Frame(body)
        row.pack(fill='x', pady=(0, 6))
        ttk.Label(row, text='期限 YYYY-MM-DD').pack(side='left')
        ttk.Entry(row, textvariable=due, width=12).pack(side='left', padx=8)
        row = ttk.Frame(body)
        row.pack(fill='x', pady=(0, 10))
        today_button = self.button(row, '今天', lambda: due.set(self.todo_today().isoformat()), 'Compact.TButton')
        today_button.pack(side='left')
        tomorrow_button = self.button(row, '明天', lambda: due.set((self.todo_today() + timedelta(days=1)).isoformat()), 'Compact.TButton')
        tomorrow_button.pack(side='left', padx=8)
        self.button(row, '清除期限', lambda: due.set(''), 'Compact.TButton').pack(side='left')
        state_row = ttk.Frame(body)
        state_row.pack(fill='x', pady=(0, 8))
        ttk.Label(state_row, text='狀態').pack(side='left')
        picker = ttk.Combobox(state_row, textvariable=state, values=list(TODO_STATES.values()), state='readonly', width=12)
        picker.pack(side='left', padx=8)
        # New records always begin in todo; transitions happen after creation.
        if not item:
            picker.configure(state='disabled')
        source_label = ttk.Label(body, text=self._todo_source(source_conversation_id), wraplength=400, style='Muted.TLabel')
        source_label.pack(fill='x', pady=(0, 8))
        source_button = self.button(body, '查看來源對話', lambda: self.open_todo_source(source_conversation_id), 'Quiet.TButton')
        source_button.pack(anchor='w', pady=(0, 8))
        if not source_conversation_id or self._todo_source(source_conversation_id) == '來源對話已刪除':
            source_button.configure(state='disabled')
        ttk.Label(body, textvariable=error, style='CardError.TLabel', wraplength=400).pack(fill='x', pady=(0, 8))
        actions = ttk.Frame(body)
        actions.pack(fill='x')
        cancel = self.button(actions, '取消', w.destroy, 'Quiet.TButton')
        cancel.pack(side='right')
        request_id = uuid.uuid4().hex
        saved = {'id': None}
        def validate():
            if not title.get().strip():
                raise ValueError('請填寫待辦標題。')
            if len(title.get().strip()) > 120:
                raise ValueError('標題超過 120 字，請自行調整；原文仍完整保留於說明。')
            if len(description.get('1.0', 'end-1c')) > 50000:
                raise ValueError('說明超過 50,000 字，請自行調整後保存。')
            raw = due.get().strip()
            if raw:
                try:
                    parsed = date.fromisoformat(raw)
                except ValueError:
                    raise ValueError('期限請填有效日期 YYYY-MM-DD。') from None
                if parsed.isoformat() != raw:
                    raise ValueError('期限請填 YYYY-MM-DD。')
            return raw or None
        def save():
            if saved['id'] is not None:
                return
            try:
                deadline = validate()
                if item:
                    updated = self.store.update_todo(todo_id, title.get().strip(), description.get('1.0', 'end-1c'),
                        deadline, next(key for key, value in TODO_STATES.items() if value == state.get()))
                else:
                    updated = self.store.create_todo(title.get().strip(), description.get('1.0', 'end-1c'),
                        deadline, source_conversation_id=source_conversation_id, request_id=request_id)
            except (ValueError, OSError) as exc:
                error.set(str(exc))
                return
            saved['id'] = updated['id']
            self.todo_selected_id = updated['id']
            w.destroy()
            self.refresh_todos()
            if item:
                self.status.set('待辦已更新。')
            else:
                self._todo_saved_notice(updated['id'])
        save_button = self.button(actions, '保存待辦', save, 'Primary.TButton')
        save_button.pack(side='right', padx=8)
        if item:
            self.button(actions, '刪除待辦', lambda: self.confirm_todo_deletion(todo_id), 'Danger.TButton').pack(side='left')
        if len(initial_title) > 120:
            error.set('標題超過 120 字，請自行調整；原文完整保留於說明。')
        w.todo_title = title
        w.todo_description = description
        w.todo_due = due
        w.todo_today_button = today_button
        w.todo_tomorrow_button = tomorrow_button
        w.todo_state = state
        w.todo_error = error
        w.todo_save = save_button
        w.todo_save_action = save
        w.todo_request_id = request_id
        w.todo_source = source_label
        w.todo_source_button = source_button
        w.todo_source_conversation_id = source_conversation_id
        windows[todo_id or request_id] = w
        def forget(event):
            if event.widget is w and windows.get(todo_id or request_id) is w:
                windows.pop(todo_id or request_id, None)
        w.bind('<Destroy>', forget, add='+')
        self.appearance.apply(w)
        title_entry.focus_set()
        return w

    def confirm_todo_deletion(self, todo_id):
        item = self.store.todo(todo_id)
        w = tk.Toplevel(self.root)
        apply_child_icons(w)
        w.title('永久刪除待辦')
        w.transient(self.root)
        self.display.size_window(w, 540, 300, (400, 260))
        body = scroll_frame(w, padding=20)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='永久刪除此待辦，無法由應用復原。', wraplength=350, style='CardError.TLabel').pack(fill='x')
        ttk.Label(body, text=item['title'], wraplength=350).pack(fill='x', pady=12)
        ttk.Label(body, text='來源對話及其他待辦不受影響。', style='Muted.TLabel').pack(anchor='w')
        actions = ttk.Frame(body)
        actions.pack(fill='x', pady=(16, 0))
        cancel = self.button(actions, '取消', w.destroy, 'Quiet.TButton')
        cancel.pack(side='right')
        def remove():
            self.store.delete_todo(todo_id)
            w.destroy()
            editor = getattr(self, 'todo_windows', {}).get(todo_id)
            if editor is not None and editor.winfo_exists():
                editor.destroy()
            if self.todo_selected_id == todo_id:
                self.todo_selected_id = None
            self.refresh_todos()
            self.status.set('待辦已永久刪除；來源對話保留。')
        confirm = self.button(actions, '永久刪除', remove, 'Danger.TButton')
        confirm.pack(side='right', padx=8)
        w.todo_delete_cancel = cancel
        w.todo_delete_confirm = confirm
        w.bind('<Escape>', lambda event: w.destroy())
        self.appearance.apply(w)
        w.grab_set()
        w.update_idletasks()
        cancel.focus_set()
        return w
