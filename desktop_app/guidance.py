"""Read-only, contextual page hints; never dispatches work or edits drafts."""
from tkinter import ttk

from .gateways import GatewayError
from .core import stamp
from .preferences import load_page_hints, save_page_hint

CHAPTERS = {
    'todo': '我的待辦', 'chat': '對話與鍵盤', 'query': '查資料與匯出', 'work': 'Plan 與選項確認',
    'result': '將資料交給助理', 'schedule': '我的排程與通知',
    'notice': '我的排程與通知', 'settings': '設定公司助理', 'issue': '問題回報',
}


def work_hint(kind, record):
    if not record:
        return None
    state = record['state']
    if kind == 'plan':
        if state == 'ready' and record.get('expires_at', '9999') <= stamp():
            state = 'expired'
        return {
            'ready': '計畫尚未執行。\n到「計畫與任務」核對內容，再自行批准。',
            'expired': '計畫已過期，不能批准。\n請重新建立計畫並核對內容。',
            'executing': '計畫已批准，正在處理。\n可查看工作紀錄，不必重複送出。',
            'cancelled': '計畫已取消。\n如仍有需要，請重新建立計畫。',
            'succeeded': '此計畫已執行完成，不需再次批准。\n選取對應的工作紀錄查看結果。',
            'failed': '此計畫執行失敗。\n請查看對應工作紀錄的失敗原因。',
        }.get(state)
    return {
        'queued': '工作正在排隊，不必重複送出。\n可查看詳情，或按「取消工作」。',
        'running': '工作正在執行，不必重複送出。\n取消不保證遠端請求停止。',
        'succeeded': '工作已完成。\n查看結果並核對內容，再決定如何使用。',
        'failed': '工作未完成，請查看失敗原因。\n可前往「問題回報」保存紀錄。',
        'cancelled': '工作已取消。\n已送出的遠端請求仍可能繼續處理。',
    }.get(state)


class GuidanceViews:
    def build_page_guidance(self, header):
        self.page_hints = load_page_hints(self.preferences_path)
        row = ttk.Frame(header)
        row.pack(fill='x', pady=(5, 0))
        row.columnconfigure(0, weight=1)
        self.page_hint = ttk.Label(row, style='Muted.TLabel', justify='left', wraplength=540)
        self.page_hint.grid(row=0, column=0, sticky='w')
        self.hint_toggle = ttk.Button(row, text='收合提示', style='Compact.TButton', command=self.toggle_page_hint)
        self.hint_toggle.grid(row=0, column=1, sticky='ne', padx=(8, 4))
        self.hint_manual = ttk.Button(row, text='本頁手冊', style='Compact.TButton', command=self.open_page_help)
        self.hint_manual.grid(row=0, column=2, sticky='ne')
        row.bind('<Configure>', lambda e: self.page_hint.configure(
            wraplength=max(200, e.width - self.hint_toggle.winfo_reqwidth() - self.hint_manual.winfo_reqwidth() - 20)))

    def current_page(self):
        current = self.book.select()
        return next((key for key, tab in self.tabs.items() if str(tab) == current), 'chat')

    def toggle_page_hint(self):
        page = self.current_page()
        visible = not self.page_hints.get(page, True)
        self.page_hints[page] = visible
        self.refresh_page_hint()
        try:
            save_page_hint(self.preferences_path, page, visible)
        except OSError:
            self.status.set('提示已切換，但無法保存偏好；下次開啟可能恢復原設定。')

    def open_page_help(self):
        return self.show_help(CHAPTERS[self.current_page()])

    def select_hint_work(self, kind):
        self.hint_work_kind = kind
        self.refresh_page_hint()

    def refresh_page_hint(self):
        # Construction-time field events can precede the rest of the eight pages.
        if not hasattr(self, 'theme_choice'):
            return
        page = self.current_page()
        text = self.page_hint_content(page)
        if self.page_hint.cget('text') != text:
            self.page_hint.configure(text=text)
        visible = self.page_hints.get(page, True)
        if visible:
            self.page_hint.grid()
        else:
            self.page_hint.grid_remove()
        self.hint_toggle.configure(text='收合提示' if visible else '展開提示')

    def page_hint_content(self, page):
        if page == 'todo':
            return '新增待辦，或從對話選取文字加入。\n開始處理按「開始」，完成後按「完成」；只保存在本機，不會自動執行。'
        if page in ('chat', 'query') and self.editing_plan:
            plan = self.store.plan(self.editing_plan[0])
            if plan['state'] != 'ready' or plan['expires_at'] <= stamp() or plan['revision'] != self.editing_plan[1]:
                return '正在修改的計畫已失效。\n請到「計畫與任務」退出修改，重新建立。'
            is_query = plan['kind'] in ('query', 'query_summarize')
            if (page == 'query') != is_query or (not is_query and plan['conversation_id'] != self.conversation):
                return '正在修改另一項計畫。\n請返回原操作頁，或到計畫頁退出修改。'
            if is_query:
                return '正在修改查詢計畫。\n核對條件後保存修改，再重新批准。'
            return '正在修改此對話的計畫。\n核對草稿後按「保存計畫修改」，再重新批准。'
        if page == 'chat':
            if self.conversation:
                binding = self.store.conversation(self.conversation)['binding']
                try:
                    profile = self.profiles.validate(binding)
                except GatewayError:
                    return '此對話目前唯讀，不能繼續送出。\n請選可用助理另開對話，或預覽轉交內容。'
                if profile['id'] != 'demo' and not profile.get('legacy'):
                    if not self.profiles.data['endpoint']:
                        return '公司連線尚未設定。\n請到「設定」填入 endpoint 與 API key。'
                    if self.profiles.data['wire_mode'] == 'unconfigured':
                        return '公司請求格式尚待確認，不能呼叫。\n請依「本頁手冊」交由公司完成接線。'
            kind, record = self.chat_work()  # Already scoped to the current conversation.
            hint = work_hint(kind, record)
            if hint:
                return hint
            if self.plan_mode.get():
                return '輸入需求後按 Enter 建立計畫。\n計畫需另行批准，現在不會執行。'
            return '輸入需求後按 Enter 送出。\nShift+Enter 換行；可附上單一 TXT／CSV。'
        if page == 'query':
            if self.query_submit.instate(['disabled']):
                return '查詢條件尚未就緒。\n請依欄位下方提示補齊或修正。'
            if self.query_plan.get():
                return '選查詢並填條件，再按「建立查詢計畫」。\n先核對計畫並批准，才會查資料。'
            return '選查詢並填條件，再按「開始查詢」。\n若想先確認內容，請勾選「先規劃」。'
        if page == 'work':
            # Task and plan tables have independent selections. Use the latest
            # user-selected table, never infer a target from all pending work.
            kind = getattr(self, 'hint_work_kind', 'plan')
            tree = self.tasks if kind == 'task' else self.plans
            if tree.selection():
                record = (self.store.task if kind == 'task' else self.store.plan)(tree.selection()[0])
                hint = work_hint(kind, record)
                if hint:
                    return hint.replace('到「計畫與任務」核對內容', '閱讀右側預覽並核對內容')
            return '選取計畫看預覽，再決定批准或修改。\n選取工作後，可查看結果或失敗原因。'
        if page == 'result':
            if self.result is not None:
                if not self.result['rows']:
                    return '這次查詢沒有符合條件的資料。\n可回「查資料」調整條件後重新查詢。'
                count = len(self.table.selection())
                if count:
                    return f'已選取 {count} 列，可複製或交給助理整理。\n轉交前會先預覽，確認後才送出。'
                return '先核對欄位、條件與資料時間。\n可選取列、匯出，或預覽後交給助理。'
            if self.result_task and self.store.task(self.result_task)['result'] is not None:
                return '目前顯示文字結果。\n核對內容後，可複製或另存文字。'
            return '目前還沒有顯示查詢結果。\n先查資料，或選取已完成工作查看結果。'
        if page == 'schedule':
            if self.schedules.selection():
                record = self.store.schedule(self.schedules.selection()[0])
                if not record['enabled']:
                    return '此排程目前停用，不會自動查詢。\n確認條件與時間後，可預覽並啟用。'
                return '此排程已啟用，請保持程式開啟。\n可查看歷史結果，或按「停用」。'
            return '先從成功的查詢結果按「設為排程」。\n排程只在本程式開啟時執行。'
        if page == 'notice':
            if self.store.notifications():
                return '選取通知，按「已讀並查看結果」。\n有結果時可檢視；失敗請查看原因。'
            return '目前沒有通知，無需額外操作。\n排程符合條件或執行失敗時會提醒。'
        if page == 'settings':
            profiles = [p for p in self.profiles.items() if p['id'] != 'demo' and p['enabled']]
            if not profiles:
                return '設定共用 endpoint、API key，再新增助理。\n沒有公司資訊時，仍可使用本機示範助理。'
            if self.profiles.data['wire_mode'] == 'unconfigured' and any(not p.get('legacy') for p in profiles):
                return '助理已建立，公司請求格式仍待確認。\n完成接線後，再明確啟動測試連線。'
            return '在這裡管理助理、共用連線與外觀。\n修改連線後，請另開對話使用新版本。'
        if page == 'issue':
            if self.issue_id:
                return '目前正在編輯已保存的回報。\n補充操作步驟後保存；仍只存本機。'
            return '填寫問題、操作步驟與預期結果。\n保存後取得編號；目前不會自動送出。'
        raise ValueError('不支援的提示頁面。')
