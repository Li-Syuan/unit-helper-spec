"""Outcome-first Tk views. Local reads and feedback only."""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from .core import TAIPEI
from .outcomes import OutcomeService


def local_time(value):
    try:
        return datetime.fromisoformat(value).astimezone(TAIPEI).strftime('%Y-%m-%d %H:%M:%S 台北時間')
    except (ValueError, TypeError):
        return '尚無完成時間'


def build_outcome(parent, app, tid):
    service = OutcomeService(app.workflows)
    outcome = service.read(tid)
    task = outcome['task']
    frame = ttk.Frame(parent, padding=8)
    state = {'succeeded':'已完成', 'failed':'未完成', 'cancelled':'已取消', 'running':'執行中', 'queued':'等待執行'}.get(task['state'], task['state'])
    ttk.Label(frame, text=state+' · '+local_time(task.get('finished_at')), style='Section.TLabel').pack(anchor='w')
    ttk.Label(frame, text=outcome['review']+' · AI 整理，請核對來源', style='Muted.TLabel').pack(anchor='w', pady=4)
    book = ttk.Notebook(frame); book.pack(fill='both', expand=True)
    result = ttk.Frame(book); book.add(result, text='成果內容')
    text = tk.Text(result, wrap='word', height=9,width=1)
    text.pack(side='left', fill='both', expand=True)
    scroll = ttk.Scrollbar(result, command=text.yview); scroll.pack(side='right', fill='y',before=text)
    text.configure(yscrollcommand=scroll.set)
    prefix = ('未完成：以下僅為已取得的部分成果。\n' if outcome['partial'] else '')
    if task.get('error'): prefix += task['error']+'\n\n'
    text.insert('1.0', prefix+(outcome['text'] or '尚無成果文字。'))
    text.configure(state='disabled')
    comparison = ttk.Frame(book); book.add(comparison, text='與上次比較')
    view = tk.Text(comparison, wrap='word', height=9,width=1)
    view.pack(side='left', fill='both', expand=True)
    bar = ttk.Scrollbar(comparison, command=view.yview); bar.pack(side='right', fill='y',before=view); view.configure(yscrollcommand=bar.set)
    comp = service.compare(tid)
    lines = [comp['reason']] if comp['reason'] else ['數值變化不代表改善或惡化。', '基準工作：'+comp['baseline_id']]
    for group in comp['groups']:
        lines += ['', '查詢步驟 '+group['step_id']]
        if group.get('previous'):
            for label, key in [('上次','previous'), ('本次','current')]:
                item = group[key]
                lines += [label+'條件：'+str(item['parameters']), label+'資料時間：'+local_time(item['fetched_at_utc'])]
            if group['same_period']: lines += ['同期間比較（重跑）']
        if group['reason']: lines += [group['reason']]
        else:
            lines += ['指標｜上次｜本次｜差值']
            lines += ['｜'.join(row) for row in group['rows']]
    view.insert('1.0', '\n'.join(lines)); view.configure(state='disabled')
    if outcome['can_rate']:
        feedback = ttk.LabelFrame(frame, text='這份成果有幫助嗎？僅保存於本機', padding=6)
        feedback.pack(side='bottom',fill='x', pady=(8,0),before=book)
        existing = service.feedback(tid) or {}
        rating = tk.StringVar(value=existing.get('rating',''))
        note = tk.StringVar(value=existing.get('note',''))
        status = tk.StringVar(value='已保存評價' if existing else '尚未評價')
        pending = [False]
        requested = [rating.get()]
        def save(value=None):
            if pending[0]: return
            chosen = value or requested[0] or rating.get()
            requested[0]=chosen
            content=note.get(); pending[0]=True; status.set('儲存中…')
            def work():
                try: service.save_feedback(tid,chosen,content); return True
                except Exception: return False
            def done(ok):
                pending[0]=False
                if not frame.winfo_exists(): return
                if not ok: status.set('保存失敗，內容已保留；請按重試保存。'); return
                rating.set(chosen); status.set('已保存：'+{'usable':'可採用','revise':'需修改','unhelpful':'無幫助'}[chosen])
            app.background(work,done)
        def clear():
            if pending[0]: return
            pending[0]=True
            def work():
                try: service.clear_feedback(tid); return True
                except Exception: return False
            def done(ok):
                pending[0]=False
                if not frame.winfo_exists(): return
                if not ok: status.set('清除失敗，請重試。'); return
                rating.set(''); requested[0]=''; note.set(''); status.set('已清除評價')
            app.background(work,done)
        buttons = ttk.Frame(feedback); buttons.pack(fill='x')
        for label,value in [('可採用','usable'),('需修改','revise'),('無幫助','unhelpful')]:
            app.button(buttons,label,lambda v=value:save(v),'Compact.TButton').pack(side='left',padx=2)
        app.button(buttons,'清除',clear,'Compact.TButton').pack(side='right')
        ttk.Entry(feedback,textvariable=note).pack(fill='x',pady=4)
        ttk.Label(feedback,text='選填備註，最多 2,000 字；修改備註後請保存。',style='Muted.TLabel').pack(anchor='w')
        app.button(feedback,'保存備註／重試保存',save,'Compact.TButton').pack(anchor='e')
        ttk.Label(feedback,textvariable=status,style='Muted.TLabel').pack(anchor='w')
        frame.feedback_controls = dict(save=save,clear=clear,rating=rating,note=note,status=status)
    frame.outcome_text = text
    return frame
