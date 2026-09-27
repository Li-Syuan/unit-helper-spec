import copy
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from desktop_app.choices import ChoiceForms
from desktop_app.config import DEFAULT,load_config,save_config,InstanceLock

class ChoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/'forms.sqlite'; self.forms=ChoiceForms(self.path)
        self.questions=[{'id':'yes','title':'確認？','type':'yes_no','options':[{'id':'yes','label':'是'},{'id':'no','label':'否'}]}, {'id':'many','title':'多選','type':'multi_choice','min':1,'max':2,'options':[{'id':'a','label':'A'},{'id':'b','label':'B'}]}]
    def tearDown(self): self.tmp.cleanup()
    def test_persistent_answers_owner_and_idempotency(self):
        form=self.forms.create(self.questions); fid=form['id']; answers={'yes':['no'],'many':['a','b']}
        with self.assertRaises(ValueError): self.forms.get(fid,'other')
        with self.assertRaises(ValueError): self.forms.submit(fid,1,answers,'k',owner='other')
        self.assertEqual(self.forms.submit(fid,1,answers,'k'),answers)
        self.assertEqual(ChoiceForms(self.path).submit(fid,1,answers,'k'),answers)
        with self.assertRaises(ValueError): self.forms.submit(fid,1,answers,'different')
        self.assertEqual(self.forms.open_forms(),[])
    def test_invalid_stale_expired_answers(self):
        form=self.forms.create(self.questions); fid=form['id']
        for answer in [{'yes':['yes'],'many':[]},{'yes':['yes','no'],'many':['a']},{'yes':['yes'],'many':['z']},{'yes':['yes'],'many':['a','a']},{'yes':['yes']}]:
            with self.assertRaises(ValueError): self.forms.submit(fid,1,answer,'x')
        with self.assertRaises(ValueError): self.forms.submit(fid,2,{'yes':['yes'],'many':['a']},'x')
        with self.assertRaises(ValueError): self.forms.submit(fid,1,{'yes':['yes'],'many':['a']},'x',now=datetime.now(timezone.utc)+timedelta(days=2))
        self.assertEqual(self.forms.get(fid)['state'],'open')

    def test_cancelled_form_cannot_submit(self):
        form=self.forms.create(self.questions); self.forms.cancel(form['id'],1)
        with self.assertRaises(ValueError): self.forms.submit(form['id'],1,{'yes':['yes'],'many':['a']},'x')
        self.assertEqual(self.forms.open_forms(),[])

class ConfigTests(unittest.TestCase):
    def test_roundtrip_no_secret_keys_and_company_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'config.json'; config=copy.deepcopy(DEFAULT); config['assistant']['header_env']={'X-Unit':'UNIT_ID'}
            save_config(config,p); self.assertEqual(load_config(p),config)
            before=p.read_bytes(); config['assistant']['api_key']='secret'
            with self.assertRaises(ValueError): save_config(config,p)
            self.assertEqual(p.read_bytes(),before)
            self.assertFalse(p.with_suffix('.tmp').exists())
    def test_single_instance_and_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock=InstanceLock(tmp)
            with self.assertRaises(ValueError): InstanceLock(tmp)
            lock.close(); again=InstanceLock(tmp); again.close()
