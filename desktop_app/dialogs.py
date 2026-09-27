"""Theme-aware app messages. Native fallback only before appearance is available."""
import tkinter as tk
from tkinter import ttk, messagebox as native
from .branding import apply_child_icons, APP_NAME
from .display import Display, work_area
from .theme import FONT


class MessageDialog(tk.Toplevel):
    def __init__(self,parent,title,message,kind='info',question=False):
        super().__init__(parent)
        self.withdraw();self.result=False if question else 'ok'
        self.parent=parent;self.previous_grab=parent.grab_current();self.previous_focus=parent.focus_get()
        self.title(APP_NAME+' · '+title)
        if parent.winfo_viewable():self.transient(parent.winfo_toplevel())
        apply_child_icons(self)
        appearance=parent._root()._qa_appearance
        display=getattr(parent._root(),'_qa_display',None) or Display(parent._root())
        body=ttk.Frame(self,padding=20);body.pack(fill='both',expand=True)
        heading=ttk.Frame(body);heading.pack(fill='x',pady=(0,10))
        symbol='?' if question else '!' if kind in ('error','warning') else 'i'
        mark_style='DialogMark.TLabel'
        if not question and kind in ('error','warning'):
            mark_style=kind.title()+'.DialogMark.TLabel'
        ttk.Label(heading,text=symbol,style=mark_style,font=(FONT,20,'bold'),width=3,anchor='center').pack(side='left',padx=(0,10))
        ttk.Label(heading,text=title,style='Section.TLabel',wraplength=440).pack(side='left',fill='x',expand=True)
        buttons=ttk.Frame(body);buttons.pack(side='bottom',fill='x',pady=(14,0))
        self.copy_status=tk.StringVar(value='')
        ttk.Label(body,textvariable=self.copy_status,style='Muted.TLabel').pack(side='bottom',anchor='w')
        if kind=='error':ttk.Label(body,text='請依訊息檢查輸入或設定；關閉此提示不會自動重試。',wraplength=510,style='Muted.TLabel').pack(side='bottom',anchor='w',pady=(10,0))
        content=ttk.Frame(body);content.pack(fill='both',expand=True)
        self.message_text=tk.Text(content,wrap='word',width=48,height=6,spacing1=0,spacing3=3)
        self.message_text.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(content,command=self.message_text.yview);scroll.pack(side='right',fill='y')
        self.message_text.configure(yscrollcommand=scroll.set)
        self.message_text.insert('1.0',str(message));self.message_text.configure(state='disabled')
        self.copy_button=ttk.Button(buttons,text='複製訊息',command=self.copy_message)
        self.copy_button.pack(side='left')
        self.close_button=ttk.Button(buttons,text='取消' if question else '關閉',command=self.dismiss)
        self.close_button.pack(side='right')
        if question:
            self.accept_button=ttk.Button(buttons,text='確認',style='Primary.TButton',command=lambda:self.dismiss(True))
            self.accept_button.pack(side='right',padx=8)
        else:self.close_button.configure(style='Primary.TButton')
        self.protocol('WM_DELETE_WINDOW',self.dismiss);self.bind('<Escape>',lambda e:self.dismiss())
        self.bind('<Return>',self.enter)
        display.size_window(self,600,360,(420,260));appearance.apply(self)
        self.update_idletasks()
        x,y,width,height=work_area(parent)
        px=parent.winfo_rootx()+(parent.winfo_width()-self.winfo_width())//2
        py=parent.winfo_rooty()+(parent.winfo_height()-self.winfo_height())//2
        self.geometry(f'+{max(x,min(px,x+width-self.winfo_width()))}+{max(y,min(py,y+height-self.winfo_height()-display.px(40)))}')
        self.deiconify();self.wait_visibility();self.grab_set();self.close_button.focus_set()

    def enter(self,event):
        if isinstance(event.widget,ttk.Button):event.widget.invoke()
        else:self.dismiss()
        return 'break'

    def copy_message(self):
        try:
            self.clipboard_clear();self.clipboard_append(self.message_text.get('1.0','end-1c'))
            self.copy_status.set('訊息已複製。')
        except tk.TclError:self.copy_status.set('無法使用剪貼簿，請選取文字後手動複製。')

    def dismiss(self,accepted=False):
        self.result=bool(accepted) if hasattr(self,'accept_button') else 'ok'
        self.destroy()

    def destroy(self):
        try:
            if self.grab_current()==self:self.grab_release()
            super().destroy()
            if self.previous_grab is not None and self.previous_grab.winfo_exists():self.previous_grab.grab_set()
            if self.previous_focus is not None and self.previous_focus.winfo_exists():self.previous_focus.focus_set()
        except tk.TclError:pass


def _show(kind,title,message,parent=None,question=False,**options):
    if parent is None or not hasattr(parent._root(),'_qa_appearance'):
        method=native.askyesno if question else getattr(native,'show'+kind)
        return method(title,message,parent=parent,**options)
    dialog=MessageDialog(parent,title,message,kind,question)
    parent.wait_window(dialog)
    return dialog.result


def showerror(title,message,**options):return _show('error',title,message,**options)
def showwarning(title,message,**options):return _show('warning',title,message,**options)
def showinfo(title,message,**options):return _show('info',title,message,**options)
def askyesno(title,message,**options):return _show('info',title,message,question=True,**options)
