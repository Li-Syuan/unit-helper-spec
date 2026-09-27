"""Nonmodal in-app toast and unread badge; never create or dispatch work."""
import tkinter as tk
from tkinter import ttk
from .display import work_area
from .theme import FONT


class NotificationPresenter:
    DURATION_MS=8000

    def __init__(self,app):
        self.app=app;self.root=app.root
        self.seen={n['id'] for n in app.store.notifications()}
        self.pending=[];self.toast=None;self.timer=None
        # Use a sibling overlay: native Windows Button painting can cover child labels.
        self.badge=ttk.Label(app.nav_buttons['notice'].master,style='NotificationBadge.TLabel',
                             font=(FONT,10,'bold'),cursor='hand2',takefocus=False)
        self.badge.bind('<Button-1>',lambda e:self.open_inbox())
        self.badge_count=0

    def update(self,notices):
        unread=[n for n in notices if not n['is_read']]
        self.badge_count=len(unread)
        if unread:
            count=str(len(unread)) if len(unread)<=99 else '99+'
            compact=getattr(getattr(self.app,'navigation',None),'collapsed',False)
            self.badge.configure(text=count if compact else count+' 未讀',padding=(3,1) if compact else (7,3))
            self.badge.place(in_=self.app.nav_buttons['notice'],relx=1,rely=0 if compact else .5,anchor='ne' if compact else 'e',x=-self.app.display.px(2 if compact else 10))
            self.badge.lift()
        else:self.badge.place_forget()
        self.app.notices.tag_configure('unread_notice',font=(FONT,11,'bold'),foreground=self.app.palette.INK)
        for n in notices:
            if self.app.notices.exists(n['id']):
                self.app.notices.item(n['id'],tags=('unread_notice',) if not n['is_read'] else ())
        fresh=[n for n in reversed(notices) if n['id'] not in self.seen and not n['is_read']]
        self.seen.update(n['id'] for n in notices)
        ids={n['id'] for n in unread}
        self.pending=[n for n in self.pending if n['id'] in ids]
        if fresh:
            self.pending.extend(fresh);self.show()
        elif self.toast is not None:
            if not self.pending:self.dismiss()
            elif len(self.pending)!=self.toast_count:self.show()

    def severity(self,notice):
        if notice.get('task_id'):
            try:
                state=self.app.store.task(notice['task_id'])['state']
                if state=='failed':return 'error','!','需要處理'
                if state=='cancelled':return 'warning','!','工作已取消'
                if state=='succeeded':return 'success','✓','工作已完成'
            except ValueError:pass
        return 'info','i','新通知'

    def show(self):
        if self.app.closed or not self.pending:return
        self.dismiss(clear=False)
        latest=self.pending[-1];kind,symbol,title=self.severity(latest)
        self.toast_count=len(self.pending)
        w=self.toast=tk.Toplevel(self.root);w.withdraw();w.overrideredirect(True)
        w.attributes('-topmost',True)
        w.title('QA agent 通知')
        # No grab, transient ownership, lift, focus_set or focus_force:
        # display independently when the app is minimized without taking keyboard input.
        border=ttk.Frame(w,style=kind.title()+'.ToastBorder.TFrame');border.pack(fill='both',expand=True)
        body=ttk.Frame(border,style='Surface.TFrame',padding=14);body.pack(fill='both',expand=True,padx=2,pady=2)
        head=ttk.Frame(body,style='Surface.TFrame');head.pack(fill='x')
        self.symbol=ttk.Label(head,text=symbol,style=kind.title()+'.ToastMark.TLabel',font=(FONT,20,'bold'))
        self.symbol.pack(side='left',padx=(0,10))
        self.title=ttk.Label(head,text=title,style='Surface.TLabel',font=(FONT,12,'bold'));self.title.pack(side='left')
        self.close_button=ttk.Button(head,text='關閉',style='Compact.TButton',command=self.dismiss,takefocus=True)
        self.close_button.pack(side='right')
        self.message=ttk.Label(body,text=latest['text'][:180]+('…' if len(latest['text'])>180 else ''),
                               style='Surface.TLabel',wraplength=330,justify='left')
        self.message.pack(fill='x',pady=(10,8))
        caption=('另有 '+str(self.toast_count-1)+' 則新通知 · ' if self.toast_count>1 else '')+'QA agent · 未讀通知會保留'
        ttk.Label(body,text=caption,style='CardMuted.TLabel',wraplength=330).pack(anchor='w')
        self.view_button=ttk.Button(body,text='查看 '+str(self.toast_count)+' 則通知' if self.toast_count>1 else '查看通知與結果',
                                   style='Primary.TButton',command=lambda:self.app.safe(self.open_pending))
        self.view_button.pack(fill='x',pady=(12,0))
        w.bind('<Escape>',lambda e:self.dismiss())
        self.app.appearance.apply(w)
        x,y,width,height=work_area(self.root);margin=self.app.display.px(16)
        usable=max(180,width-2*margin);toast_width=min(self.app.display.px(390),usable)
        self.message.configure(wraplength=max(100,toast_width-self.app.display.px(36)))
        w.geometry(f'{toast_width}x1');w.update_idletasks()
        toast_height=min(w.winfo_reqheight(),height-2*margin)
        w.geometry(f'{toast_width}x{toast_height}+{x+width-toast_width-margin}+{y+height-toast_height-margin}')
        w.deiconify()
        for widget in self.descendants(w):
            widget.bind('<Enter>',self.pause,add='+');widget.bind('<Leave>',self.resume,add='+')
        self.resume()

    @staticmethod
    def descendants(w):
        yield w
        for child in w.winfo_children():yield from NotificationPresenter.descendants(child)

    def pause(self,event=None):
        if self.timer is not None:
            self.root.after_cancel(self.timer);self.timer=None

    def resume(self,event=None):
        self.pause()
        if self.toast is None:return
        if event is not None:
            hovered=self.root.winfo_containing(*self.root.winfo_pointerxy())
            if hovered is not None and str(hovered).startswith(str(self.toast)):return
        self.timer=self.root.after(self.DURATION_MS,self.dismiss)

    def dismiss(self,clear=True):
        self.pause()
        if self.toast is not None:
            self.toast.destroy();self.toast=None
        if clear:self.pending=[]

    def open_inbox(self):
        self.root.deiconify();self.app.book.select(self.app.tabs['notice'])

    def open_pending(self):
        notices=list(self.pending);self.dismiss();self.open_inbox()
        if len(notices)==1:self.app.open_notice(notices[0]['id'])

    def close(self):self.dismiss()
