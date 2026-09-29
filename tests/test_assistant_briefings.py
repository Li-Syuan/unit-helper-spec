import threading
import time
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from tests import test_company_journey as journey
from desktop_app.assistant_briefings import DEFAULT_PROMPT


class AssistantBriefingTests(unittest.TestCase):
    def setUp(self):
        self.f=journey.CompanyJourneyTests();self.f.setUp();self.s=self.f.s;self.b=self.s.briefings
        self.pid=self.f.ids['analysis'];self.s.profiles.set_workflow_capability(self.pid,['analysis'])
    def tearDown(self):self.f.tearDown()
    def run_trial(self):
        preview=self.b.preview(self.pid)
        tid=self.b.run(preview['token'])['task_id'];self.f.wait()
        self.assertEqual(self.b.status(tid)['state'],'succeeded')
        return tid
    def test_preview_no_calls_and_confirmation_idempotent_without_four_roles(self):
        p=self.b.preview(self.pid);self.assertFalse(self.f.mock.requests);self.assertFalse(self.s.store.tasks())
        tid=self.b.run(p['token'])['task_id'];self.f.wait()
        self.assertEqual(self.b.run(p['token'])['task_id'],tid)
        self.assertEqual(len(self.f.mock.runs),1);self.assertFalse(self.s.store.schedules())
        self.assertEqual(self.b.status(tid)['result']['search'],'not_tested')
    def test_daily_consent_idempotency_immediate_test_and_taipei_clock(self):
        tid=self.run_trial()
        with self.assertRaises(ValueError):self.b.schedule(tid,True,False)
        now=datetime(2026,9,29,23,59,tzinfo=timezone.utc)
        with patch('desktop_app.assistant_briefings.utcnow',return_value=now):
            result=self.b.schedule(tid,True,True)
        sid=result['schedule_id'];s=self.s.store.schedule(sid)
        self.assertIs(self.b.status(tid)['schedule']['enabled'],True)
        self.assertEqual(s['next_fire'],'2026-09-30T00:00:00+00:00')
        self.assertEqual(self.b.schedule(tid,True,True)['schedule_id'],sid)
        self.assertEqual(len(self.f.mock.runs),1)
        first=self.s.engine.run_schedule_now(sid,'same');self.f.wait()
        self.assertIsNone(self.s.engine.run_schedule_now(sid,'same'))
        self.assertEqual(self.s.store.schedule(sid)['next_fire'],s['next_fire'])
        self.assertEqual(len(self.f.mock.threads),2)
        self.assertTrue(any(n['task_id']==first for n in self.s.store.notifications()))
        self.s.engine.tick(datetime(2026,9,30,0,0,tzinfo=timezone.utc));self.f.wait()
        self.s.engine.tick(datetime(2026,9,30,0,0,tzinfo=timezone.utc));self.f.wait()
        self.assertEqual(len(self.f.mock.runs),3)
        self.s.engine.set_schedule_enabled(sid,False)
        self.assertIs(self.b.status(tid)['schedule']['enabled'],False)
    def test_reopen_keeps_schedule_and_receipts_without_replay(self):
        from desktop_app.web_session import WebSession
        tid=self.run_trial();sid=self.b.schedule(tid,True,True)['schedule_id']
        when=datetime.fromisoformat(self.s.store.schedule(sid)['next_fire'])
        self.s.engine.tick(when);self.f.wait();count=len(self.f.mock.runs)
        self.s.close();self.s=WebSession(directory=self.f.tmp.name);self.f.s=self.s
        self.s.engine.tick(when)
        self.assertEqual(len(self.f.mock.runs),count)
        self.assertEqual(len(self.s.store.schedule_runs(sid)),1)
        self.assertEqual(self.s.briefings.status(tid)['schedule_id'],sid)
        self.s.engine.set_schedule_enabled(sid,False)
    def test_expired_preview_bad_clock_and_changed_binding_do_not_send(self):
        for value in ('8:00','24:00','08:99'):
            with self.assertRaises(ValueError):self.b.preview(self.pid,time_hhmm=value)
        p=self.b.preview(self.pid);self.b.previews[p['token']]['expires']=0
        with self.assertRaises(ValueError):self.b.run(p['token'])
        p=self.b.preview(self.pid);self.s.profiles.set_endpoint('https://other.example.test/v1')
        with self.assertRaises(ValueError):self.b.run(p['token'])
        self.assertFalse(self.f.mock.requests)
    def test_failed_or_tools_blocked_cannot_enable_and_never_calls_plugin(self):
        self.f.mock.statuses=['requires_action']
        p=self.b.preview(self.pid);tid=self.b.run(p['token'])['task_id'];self.f.wait()
        self.assertEqual(self.b.status(tid)['state'],'failed')
        with self.assertRaises(ValueError):self.b.schedule(tid,True,True)
        self.assertFalse(any('pluginapi' in path for _,path,_ in self.f.mock.requests))
    def test_failure_on_schedule_pauses_and_notifies(self):
        tid=self.run_trial();sid=self.b.schedule(tid,True,True)['schedule_id']
        self.f.mock.statuses=['failed']
        task=self.s.engine.run_schedule_now(sid,'failure');self.f.wait()
        self.assertEqual(self.s.store.task(task)['state'],'failed')
        self.assertFalse(self.s.store.schedule(sid)['enabled'])
        self.assertTrue(any(n['task_id']==task for n in self.s.store.notifications()))
    def test_cancelled_late_reply_not_success_and_overlap_waits_real_worker(self):
        tid=self.run_trial();sid=self.b.schedule(tid,True,True)['schedule_id']
        entered=threading.Event();release=threading.Event();raw=self.s.profiles.respond
        def delayed(*args,**kwargs):
            entered.set();release.wait(5);return 'late reply'
        with patch.object(self.s.engine,'assistant_router',side_effect=delayed):
            task=self.s.engine.run_schedule_now(sid,'first');self.assertTrue(entered.wait(2))
            try:
                self.s.engine.cancel_task(task)
                self.assertIsNone(self.s.engine.run_schedule_now(sid,'overlap'))
            finally:release.set()
            self.f.wait()
        self.assertEqual(self.s.store.task(task)['state'],'cancelled')
        self.assertIsNone(self.s.store.task(task)['result'])
        self.assertFalse(self.s.store.schedule(sid)['enabled'])
    def test_bridge_cannot_schedule_demo_or_unsuccessful_run(self):
        api=self.f.api
        self.assertFalse(api.call('briefing_preview',{'profile_id':'demo','prompt':DEFAULT_PROMPT})['ok'])
        self.assertFalse(api.call('briefing_schedule',{'task_id':'missing','consent':True,'reviewed':True})['ok'])
