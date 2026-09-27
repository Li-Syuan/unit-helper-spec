from unittest import TestCase
from desktop_app.keyboard import ChatKeyboard


class Widget:
    def __init__(self,text='hello'):
        self.text=text;self.bindings={};self.pending={};self.counter=0
    def bind(self,sequence,callback):self.bindings[sequence]=callback;return sequence
    def unbind(self,sequence,binding):self.bindings.pop(sequence,None)
    def get(self,*args):return self.text
    def insert(self,index,text):self.text+=text
    def see(self,index):pass
    def after_idle(self,callback):
        self.counter+=1;self.pending[self.counter]=callback;return self.counter
    def after_cancel(self,key):self.pending.pop(key,None)
    def idle(self):
        pending=list(self.pending.values());self.pending.clear()
        for callback in pending:callback()


class Guard:
    def __init__(self):self.active=False;self.closed=False
    def blocked(self):return self.active
    def close(self):self.closed=True


class KeyboardTests(TestCase):
    def setup_keyboard(self,text='hello'):
        widget=Widget(text);guard=Guard();calls=[];clock=[1.0]
        keyboard=ChatKeyboard(widget,lambda:calls.append(widget.text),guard,lambda:clock[0])
        return keyboard,widget,guard,calls,clock
    def test_enter_ctrl_and_shift_newline(self):
        k,w,g,c,clock=self.setup_keyboard()
        self.assertEqual(w.bindings['<Return>'](),'break');self.assertEqual(c,['hello'])
        k.release();w.idle();clock[0]+=1
        w.bindings['<Control-Return>']();self.assertEqual(len(c),2)
        w.bindings['<Shift-Return>']();self.assertEqual(w.text,'hello\n')
        self.assertEqual(len(c),2);k.close();self.assertTrue(g.closed);self.assertEqual(w.bindings,{})
    def test_ime_empty_and_repeat_guard(self):
        k,w,g,c,clock=self.setup_keyboard('   ')
        k.press();self.assertEqual(c,[]);k.release();w.idle()
        w.text='測試';g.active=True;k.press();self.assertEqual(c,[])
        k.release();w.idle();g.active=False;k.press();self.assertEqual(c,['測試'])
        clock[0]+=1;k.press();self.assertEqual(len(c),1)  # held key even beyond debounce
        k.release();k.press();w.idle();self.assertEqual(len(c),1)  # OS repeat release/press pair
        k.release();w.idle();k.press();self.assertEqual(len(c),2)
        k.release();w.idle();clock[0]+=.1;k.press();self.assertEqual(len(c),2)
        k.close()
    def test_ime_shift_does_not_insert_and_focus_loss_releases(self):
        k,w,g,c,clock=self.setup_keyboard()
        g.active=True;k.newline();self.assertEqual(w.text,'hello')
        k.press();g.active=False;k.blur();k.press();self.assertEqual(len(c),1);k.close()
