"""Debounced, local-only composer recovery with stale-write fences."""
import copy
from concurrent.futures import ThreadPoolExecutor
from tkinter import ttk
from . import dialogs as messagebox


class DraftViews:
    def editing_chat_draft(self):
        if not self.editing_plan:
            return False
        try: plan=self.store.plan(self.editing_plan[0])
        except ValueError: return False
        return plan['kind'] not in ('query','query_summarize') and plan['conversation_id']==self.conversation

    def init_draft_saving(self):
        self.draft_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='local-draft')
        self.draft_futures = []
        self.draft_timer = None
        self.draft_loading = False
        self.draft_snapshots = {}
        self.draft_versions = {}
        self.draft_saved_versions = {}
        self.draft_attachment_hints = set()
        row = ttk.Frame(self.composer, style='CardBody.TFrame')
        row.pack(fill='x', pady=(3, 0))
        self.draft_notice = ttk.Label(row, text='文字草稿只保存在本機', style='CardMuted.TLabel')
        self.draft_notice.pack(side='left', fill='x', expand=True)
        self.draft_retry = self.button(row, '重試保存', lambda: self.queue_draft(force=True), 'Compact.TButton')
        self.draft_retry.pack(side='right'); self.draft_retry.pack_forget()
        self.input.bind('<<Modified>>', lambda e: self.draft_changed(), add='+')
        self.purpose.trace_add('write', lambda *a: self.draft_changed())
        self.plan_mode.trace_add('write', lambda *a: self.draft_changed())

    def draft_changed(self):
        if not hasattr(self, 'draft_pool') or self.draft_loading or self.closed or not self.conversation:
            return
        if self.editing_chat_draft():
            self.draft_notice.configure(text='正在修改 Plan，請按「保存計畫修改」；不會自動保存修訂')
            return
        if self.draft_timer:
            self.root.after_cancel(self.draft_timer)
        self.draft_notice.configure(text='儲存中…')
        self.draft_timer = self.root.after(1000, self.queue_draft)

    def draft_snapshot(self):
        return (self.input.get('1.0', 'end-1c'), self.purpose.get(), bool(self.plan_mode.get()),
                bool(self.attachment) or self.conversation in self.draft_attachment_hints)

    def queue_draft(self, force=False):
        if not hasattr(self, 'draft_pool') or self.draft_loading or self.closed or not self.conversation:
            return
        if self.draft_timer:
            self.root.after_cancel(self.draft_timer); self.draft_timer = None
        if self.editing_chat_draft():
            self.draft_notice.configure(text='正在修改 Plan，請按「保存計畫修改」；不會自動保存修訂')
            return
        cid, snapshot = self.conversation, self.draft_snapshot()
        if not force and self.draft_snapshots.get(cid) == snapshot:
            if self.draft_versions.get(cid) == self.draft_saved_versions.get(cid):
                self.draft_notice.configure(text='草稿已保存於本機' if self.store.draft(cid) else '文字草稿只保存在本機')
            return
        revision = self.store.reserve_draft(cid)
        self.draft_versions[cid] = revision
        self.draft_snapshots[cid] = snapshot
        self.draft_notice.configure(text='儲存中…')
        self.draft_retry.pack_forget()
        store = self.store
        def work():
            try:
                return (cid, revision, store.save_draft(cid, revision, *snapshot), False)
            except Exception:
                return (cid, revision, False, True)
        future = self.draft_pool.submit(work)
        self.draft_futures = [f for f in self.draft_futures if not f.done()]
        self.draft_futures.append(future)
        events, callback = self.events, self.draft_saved
        future.add_done_callback(lambda f: events.put((callback, f.result(), None, False)))

    def draft_saved(self, result):
        cid, revision, saved, failed = result
        if self.closed or self.draft_versions.get(cid) != revision:
            return
        if failed:
            self.draft_snapshots.pop(cid, None)
        elif saved:
            self.draft_saved_versions[cid] = revision
        if self.conversation == cid and not self.editing_chat_draft():
            if failed:
                self.draft_notice.configure(text='保存失敗；畫面內容仍保留')
                self.draft_retry.pack(side='right')
            elif saved:
                self.draft_notice.configure(text='草稿已保存於本機')
                self.draft_retry.pack_forget()

    def stash_draft(self):
        if self.conversation and hasattr(self, 'input') and not self.editing_chat_draft():
            self.drafts[self.conversation] = (self.input.get('1.0', 'end-1c'), copy.deepcopy(self.attachment),
                                               self.purpose.get(), self.plan_mode.get())
            self.queue_draft()

    def restore_draft(self):
        self.draft_loading = True
        try:
            saved = self.store.draft(self.conversation)
            if self.conversation in self.drafts:
                value, attachment, purpose, planned = self.drafts[self.conversation]
            elif saved:
                value, attachment, purpose, planned = saved['text'], None, saved['purpose'], bool(saved['planned'])
                if saved['had_attachment']:
                    self.draft_attachment_hints.add(self.conversation)
            else:
                value, attachment, purpose, planned = '', None, '一般對話', False
            self.input.delete('1.0', 'end'); self.input.insert('1.0', value)
            self.attachment = copy.deepcopy(attachment)
            self.purpose.set(purpose); self.plan_mode.set(planned)
            self.attachment_label.configure(text=attachment['name']+' · 已附加' if attachment else
                '請重新選取附件' if self.conversation in self.draft_attachment_hints else '可先預覽，再送出')
            self.draft_snapshots[self.conversation] = self.draft_snapshot()
            self.draft_notice.configure(text='已恢復本機草稿；附件需重新選取' if saved and saved['had_attachment'] and not attachment else
                                        '草稿已保存於本機' if saved else '文字草稿只保存在本機')
            self.draft_retry.pack_forget()
            self.input.edit_modified(False)
        finally:
            self.draft_loading = False

    def clear_saved_draft(self, cid, consumed=False):
        if self.draft_timer:
            self.root.after_cancel(self.draft_timer); self.draft_timer = None
        if not consumed:
            self.store.clear_draft(cid)
        self.draft_versions.pop(cid, None); self.draft_snapshots.pop(cid, None)
        self.draft_saved_versions.pop(cid, None)
        self.draft_attachment_hints.discard(cid); self.drafts.pop(cid, None)

    def drafts_deleted(self, ids):
        if self.conversation in ids and self.draft_timer:
            self.root.after_cancel(self.draft_timer); self.draft_timer = None
        for cid in ids:
            self.store.reserve_draft(cid)
            self.draft_versions.pop(cid, None); self.draft_snapshots.pop(cid, None)
            self.draft_saved_versions.pop(cid, None)
            self.draft_attachment_hints.discard(cid)

    def flush_drafts_for_close(self, force=False):
        # Final small SQLite writes, serialized with background saves before shutdown.
        # Do not cancel unsaved writers or hide a failed save behind window destruction.
        self.stash_draft()
        pending = {}
        for cid, (text, attachment, purpose, planned) in self.drafts.items():
            pending[cid] = (text, purpose, bool(planned), bool(attachment) or cid in self.draft_attachment_hints)
        if self.conversation and not self.editing_chat_draft():
            pending[self.conversation] = self.draft_snapshot()
        try:
            for cid, snapshot in pending.items():
                revision = self.store.reserve_draft(cid)
                self.draft_versions[cid] = revision
                self.store.save_draft(cid, revision, *snapshot)
        except Exception:
            self.draft_notice.configure(text='保存失敗；畫面內容仍保留')
            self.draft_retry.pack(side='right')
            if not force and not messagebox.askyesno('草稿尚未保存', '草稿保存失敗。仍要關閉並放棄未保存內容？',
                                                    default='no', parent=self.root):
                return False
        if self.draft_timer:
            self.root.after_cancel(self.draft_timer); self.draft_timer = None
        self.draft_pool.shutdown(wait=False)
        return True

    def flush_deletion_drafts(self, ids):
        self.stash_draft()
        for cid in ids:
            cached=self.drafts.get(cid)
            if cached is None:
                continue
            text,attachment,purpose,planned=cached
            snapshot=(text,purpose,bool(planned),bool(attachment) or cid in self.draft_attachment_hints)
            revision=self.store.reserve_draft(cid)
            self.store.save_draft(cid,revision,*snapshot)
            self.draft_versions[cid]=revision;self.draft_saved_versions[cid]=revision
            self.draft_snapshots[cid]=snapshot
