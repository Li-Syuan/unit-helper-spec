"""Read-only, compact presentation of a WorkflowService snapshot."""
import json
import tkinter as tk
from tkinter import ttk


STEP_STATES = {
    'unapproved': ('○', '待批准'), 'queued': ('○', '等待執行'),
    'running': ('●', '處理中'), 'succeeded': ('✓', '已完成'),
    'failed': ('!', '需要處理'), 'blocked': ('—', '前置未完成'),
    'cancelled': ('—', '已取消'), 'interrupted': ('!', '執行已中斷'),
    'unknown': ('?', '尚無狀態紀錄'),
}


def step_rows(record, target):
    """Join declared steps and actual observations; never infer successful steps."""
    record = record or {}
    states = {row['step_id']: row for row in record.get('steps_status', [])}
    rows = []
    steps=record.get('steps', [])
    if (record.get('task') or {}).get('payload',{}).get('workflow',{}).get('agent',{}).get('version')==2:
        steps=[dict(r['input']['definition'],title=r['input']['definition'].get('title') or '決定下一步')
               for r in record.get('steps_status',[]) if (r.get('input') or {}).get('definition')]
    for number, step in enumerate(steps, 1):
        observed = states.get(step['id'], {})
        fallback = 'unknown' if record.get('task') else 'cancelled' if record.get('state') == 'cancelled' else 'unapproved'
        state = observed.get('state', fallback)
        mark, label = STEP_STATES.get(state, ('?', str(state)))
        if step['kind'] == 'query':
            actor = '查詢工具 · ' + step.get('query_id', '')
        else:
            actor = target(step.get('binding'))
        rows.append(dict(id=step['id'], number=number, title=step['title'], actor=actor,
                         state=state, label=mark + ' ' + label, step=step, observed=observed))
    return rows


def detail_text(row, record):
    """Full, selectable original content; only list cells use compact summaries."""
    step, observed = row['step'], row['observed']
    titles = {s['id']: s['title'] for s in record.get('steps', [])}
    sources = [source + ' · ' + titles.get(source, source) for source in step.get('inputs', [])]
    lines = [f'{row["number"]:02d}  {row["title"]}', row['label'], '', '負責：' + row['actor'],
             '指定來源：' + ('、'.join(sources) or '本次需求'), '', '工作指示',
             step.get('instruction') or '依核准查詢模板取得資料。']
    if step['kind'] == 'query':
        lines += ['', '查詢條件', json.dumps(step.get('parameters', {}), ensure_ascii=False, indent=2),
                  '每次使用前一日' if step.get('date_mode') == 'previous_day' else '固定日期範圍']
    for heading, key in [('實際輸入', 'input'), ('完整輸出', 'output')]:
        value = observed.get(key)
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) if value is not None else '尚無紀錄'
        lines += ['', heading, text]
    if observed.get('error'):
        lines += ['', '需要處理', str(observed['error'])]
    return '\n'.join(lines)


class WorkflowPresenter(ttk.Frame):
    """All updates are views only; callbacks open read-only details."""
    def __init__(self, parent, app, open_detail):
        super().__init__(parent)
        self.app, self.open_detail = app, open_detail
        self.record = {}; self.rows = {}; self.record_id = None
        self.goal=ttk.Label(self,text='',style='Section.TLabel',wraplength=650)
        self.goal.pack(fill='x',pady=(8,2))
        self.bind('<Configure>',lambda e:self.goal.configure(wraplength=max(200,e.width-20)),add='+')
        self.summary = ttk.Label(self, text='和主代理談完需求後，分工會顯示在這裡。', style='Muted.TLabel')
        self.summary.pack(fill='x', pady=(4, 6))
        box = ttk.Frame(self)
        box.rowconfigure(0, weight=1); box.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(box, columns=('number', 'title', 'actor', 'state'),
                                 show='headings', selectmode='browse', height=3)
        for key, heading, width, minimum, stretch in [
            ('number', '#', 40, 32, False), ('title', '工作步驟', 235, 120, True),
            ('actor', '負責助理／工具', 175, 100, True), ('state', '狀態', 128, 112, False),
        ]:
            self.table.heading(key, text=heading)
            self.table.column(key, width=width, minwidth=minimum, stretch=stretch,
                              anchor='center' if key == 'number' else 'w')
        self.table.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(box, command=self.table.yview); scroll.grid(row=0, column=1, sticky='ns')
        horizontal = ttk.Scrollbar(box, orient='horizontal', command=self.table.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        self.table.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        footer = ttk.Frame(self); footer.pack(side='bottom', fill='x', pady=(4, 0))
        self.source = ttk.Label(footer, text='選取一步，查看來源與完整內容。', style='Muted.TLabel')
        self.detail_button = app.button(footer, '查看這一步', self.show_selected, 'Compact.TButton')
        self.detail_button.pack(side='right')
        self.source.pack(side='left', fill='x', expand=True)
        self.table.bind('<<TreeviewSelect>>', self.selected)
        self.table.bind('<Double-1>', lambda event: self.show_selected())
        self.table.bind('<Return>', lambda event: self.show_selected())
        self.table.bind('<<ThemeChanged>>', self.recolor, add='+')
        box.pack(fill='both', expand=True)

    def recolor(self, event=None):
        # Also applies to retained result windows when the main workflow is hidden.
        colors = self.app.appearance.colors
        for state, color in [('running', colors.ACCENT), ('succeeded', colors.SUCCESS),
                             ('failed', colors.ERROR), ('interrupted', colors.ERROR),
                             ('blocked', colors.MUTED), ('cancelled', colors.MUTED)]:
            self.table.tag_configure(state, foreground=color)

    def show_selected(self):
        selected = self.table.selection()
        if selected and selected[0] in self.rows:
            self.open_detail(self.rows[selected[0]], self.record)

    def selected(self, event=None):
        selected = self.table.selection()
        row = self.rows.get(selected[0]) if selected else None
        if row:
            sources = row['step'].get('inputs', [])
            titles={s['id']:s['title'] for s in self.record.get('steps',[])}
            self.source.configure(text='來源：' + ('、'.join(titles.get(s,s) for s in sources) if sources else '本次需求'))
        else:
            self.source.configure(text='選取一步，查看來源與完整內容。')
        self.detail_button.configure(state='normal' if row else 'disabled')

    def update_record(self, record):
        record = record or {}
        identity = (record.get('id'), (record.get('task') or {}).get('id'))
        changed = identity != self.record_id
        rows = step_rows(record, self.app.workflow_target)
        self.rows = {row['id']: row for row in rows}; self.record = record; self.record_id = identity
        goal=record.get('goal','')
        self.goal.configure(text=goal[:100]+('…（完整內容見討論頁）' if len(goal)>100 else ''))
        for iid in self.table.get_children():
            if iid not in self.rows: self.table.delete(iid)
        for index, row in enumerate(rows):
            values = (f'{row["number"]:02d}', row['title'], row['actor'].split(' · 連線版 ')[0], row['label'])
            if self.table.exists(row['id']):
                if tuple(self.table.item(row['id'], 'values')) != values:
                    self.table.item(row['id'], values=values, tags=(row['state'],))
                self.table.move(row['id'], '', index)
            else:
                self.table.insert('', 'end', iid=row['id'], values=values, tags=(row['state'],))
        self.recolor()
        if rows and (changed or not self.table.selection()):
            focus = next((row for row in rows if row['state'] in ('running', 'failed', 'interrupted')), rows[0])
            self.table.selection_set(focus['id']); self.table.focus(focus['id']); self.table.see(focus['id'])
        task = record.get('task')
        if task:
            completed = sum(row['state'] == 'succeeded' for row in rows)
            self.summary.configure(text=f'{completed} / {len(rows)} 步已完成 · 依序執行 · 選取查看成果')
        elif rows:
            self.summary.configure(text=f'{len(rows)} 步分工 · 尚未執行 · 請核對負責助理與資料來源')
        else:
            self.summary.configure(text='和主代理談完需求後，分工會顯示在這裡。')
        self.selected()
