"""Catalog contracts, service gating and Tk flows with non-demo field names."""
import copy
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from desktop_app.core import Engine, Store
from desktop_app.gateways import DemoQueries
from desktop_app.query_schema import validate_template, parameters, initial_values, date_mapping, find_template


def catalog():
    return [{'id':'CUSTOM','name':'自訂測試','description':'合成測試資料','parameters':{
        'search':{'label':'關鍵字','type':'text','max_length':20,'default':'樣本'},
        'count':{'label':'筆數','type':'integer','min':1,'max':100,'default':10},
        'amount':{'label':'精確金額','type':'decimal','min':'0','default':'123456789012345678.0010'},
        'active':{'label':'啟用','type':'boolean','default':False},
        'group':{'label':'部門','type':'single_choice','options':['甲','乙'],'default':'甲'},
        'note':{'label':'備註','type':'text','required':False}}},
        {'id':'DATES','name':'不同日期欄位','parameters':{
        'begin':{'label':'起日','type':'date','default':'2026-09-25'},
        'until':{'label':'迄日','type':'date','default':'2026-09-26'}},'date_range':{'start':'begin','end':'until'}}]


class QuerySchemaTests(unittest.TestCase):
    def test_types_precision_defaults_and_optional(self):
        template=catalog()[0]; raw=initial_values(template)
        self.assertEqual(parameters(template,raw)['amount'],'123456789012345678.0010')
        raw.update(count='12',active='否',note='')
        parsed=parameters(template,raw,from_ui=True)
        self.assertEqual(parsed['count'],12); self.assertIs(parsed['active'],False); self.assertNotIn('note',parsed)
        for key,value in [('count',True),('amount',1.5),('active','false'),('group','丙'),('search','x'*21)]:
            values=initial_values(template); values[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): parameters(template,values)
        with self.assertRaises(ValueError): parameters(template,{**initial_values(template),'unexpected':1})
        values=initial_values(template); values.pop('search')
        with self.assertRaises(ValueError): parameters(template,values)
    def test_bounds_and_invalid_definitions(self):
        for field in [{'label':'a','type':'decimal','default':'NaN'},
                      {'label':'a','type':'integer','min':2,'max':1},
                      {'label':'a','type':'text','min_length':3,'max_length':2},
                      {'label':'a','type':'unsupported'},
                      {'label':'a','type':'single_choice','options':['a','a']},
                      {'label':'a','type':'boolean','required':'yes'},
                      {'label':'a','type':'text','secret_instruction':'execute'}]:
            with self.subTest(field=field), self.assertRaises(ValueError): validate_template({'id':'x','name':'x','parameters':{'a':field}})
        template=catalog()[1]
        with self.assertRaises(ValueError): parameters(template,{'begin':'2026-02-30','until':'2026-03-01'})
        broken=copy.deepcopy(template); broken['date_range']['start']='missing'
        with self.assertRaises(ValueError): validate_template(broken)
        self.assertIsNone(date_mapping(catalog()[0]))
        with self.assertRaises(ValueError): find_template(catalog(),'missing')
        with self.assertRaises(ValueError): find_template(catalog()+catalog(),'CUSTOM')
    def test_decimal_date_and_integer_limits(self):
        for kind,low,high,inside,outside in [('decimal','1.00000000000000001','2','1.00000000000000002','1.0'),
                                             ('integer',2,5,3,6),('date','2026-01-01','2026-12-31','2026-06-01','2027-01-01')]:
            t={'id':'x','name':'x','parameters':{'v':{'label':'v','type':kind,'min':low,'max':high}}}
            self.assertEqual(parameters(t,{'v':inside})['v'],inside)
            with self.assertRaises(ValueError): parameters(t,{'v':outside})


class CatalogServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.store=Store(Path(self.tmp.name)/'test.db'); self.calls=[]; self.templates=catalog()
        def run(q,p):
            self.calls.append((q,p)); return {'rows':[[p.get('amount','1')]],'columns':[{'name':'value','label':'數值','type':'decimal'}],
                'parameters':p,'source_label':'合成','row_count':1,'truncated':False,'fetched_at_utc':'2026-09-26T00:00:00+00:00'}
        self.engine=Engine(self.store,run,lambda *args:'測試',query_catalog=lambda:self.templates)
    def tearDown(self): self.engine.close(wait=True); self.tmp.cleanup()
    def finish(self,tid):
        end=time.monotonic()+3
        while time.monotonic()<end:
            task=self.store.task(tid)
            if task['state'] in {'succeeded','failed','cancelled'}: return task
            time.sleep(.01)
        self.fail('task timeout')
    def schedule(self,key):
        template=find_template(self.templates,key); tid=self.engine.run_query(key,parameters(template,initial_values(template)))
        self.assertEqual(self.finish(tid)['state'],'succeeded')
        return self.engine.create_schedule(tid,'測試','daily','09:00')
    def test_plan_revision_validation_and_no_dispatch_before_confirmation(self):
        vals=parameters(self.templates[0],initial_values(self.templates[0]))
        pid=self.engine.create_plan('query',{'query_id':'CUSTOM','parameters':vals}); self.assertEqual(self.calls,[])
        vals=dict(vals,count=12); self.engine.edit_plan(pid,1,'query',{'query_id':'CUSTOM','parameters':vals})
        with self.assertRaises(ValueError): self.engine.confirm_plan(pid,1,'old')
        tid=self.engine.confirm_plan(pid,2,'new'); self.assertEqual(self.finish(tid)['state'],'succeeded'); self.assertEqual(len(self.calls),1)
        self.assertEqual(self.engine.confirm_plan(pid,2,'again'),tid)
        with self.assertRaises(ValueError): self.engine.run_query('MISSING',{})
        with self.assertRaises(ValueError): self.engine.run_query('CUSTOM',dict(vals,count='12'))
    def test_rolling_mapping_literal_and_removed_template(self):
        plain=self.schedule('CUSTOM')
        with self.assertRaises(ValueError): self.engine.set_schedule_date_mode(plain,'previous_day')
        self.engine.set_schedule_date_mode(plain,'literal')
        self.assertEqual(self.engine.schedule_preview(plain)[0]['parameters']['amount'],'123456789012345678.0010')
        dated=self.schedule('DATES'); self.engine.set_schedule_date_mode(dated,'previous_day')
        p=self.engine.schedule_preview(dated,datetime(2026,9,26,tzinfo=timezone.utc))[0]['parameters']
        self.assertEqual(p,{'begin':'2026-09-25','until':'2026-09-26'})
        self.templates=[]
        with self.assertRaises(ValueError): self.engine.set_schedule_enabled(dated,True)
        self.assertIsNone(self.engine.run_schedule_now(dated,'removed'))
        self.assertEqual(self.store.schedule_runs(dated)[0]['state'],'failed'); self.assertTrue(self.store.notifications())
        self.assertEqual(len(self.calls),2)
    def test_legacy_demo_mapping_only_and_invalid_saved_mode(self):
        self.templates=DemoQueries().catalog()
        for t in self.templates: t.pop('date_range')
        sid=self.schedule('DEMO01')
        with self.assertRaises(ValueError): self.engine.set_schedule_date_mode(sid,'previous_day')
        # Simulate an existing pre-catalog schedule; only exact old DEMO IDs map.
        import json
        values=self.store.schedule(sid)['parameters']; values['_date_mode']='previous_day'
        with self.store.connection() as db: db.execute('UPDATE schedules SET parameters=? WHERE id=?',(json.dumps(values),sid))
        self.assertIn('from_date',self.engine.schedule_preview(sid)[0]['parameters'])
        with self.store.connection() as db:
            db.execute('UPDATE schedules SET parameters=? WHERE id=?',('{"_date_mode":"unknown"}',sid))
        with self.assertRaises(ValueError): self.engine.schedule_preview(sid)
    def test_catalog_change_blocks_ready_plan_without_running(self):
        pid=self.engine.create_plan('query',{'query_id':'DATES','parameters':initial_values(self.templates[1])})
        self.templates[1]['parameters']['begin']['type']='unsupported'
        with self.assertRaises(ValueError): self.engine.confirm_plan(pid,1,'no')
        self.assertEqual(self.calls,[]); self.assertEqual(self.store.tasks(),[])
