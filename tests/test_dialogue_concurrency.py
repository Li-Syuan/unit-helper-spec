"""Slow provider calls must not freeze the bridge or survive application close."""
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
from desktop_app.dialogue_store import DialogueStore
from desktop_app.dialogue_service import DialogueService
from desktop_app.web_session import WebSession
from desktop_app.web_bridge import WebBridge


class DelayedProvider:
    def __init__(self):
        self.entered=threading.Event();self.release=threading.Event();self.context=None

    def respond_context(self,history,mode,current,assistant_id,context):
        self.context=context;self.entered.set()
        if not self.release.wait(4):raise ValueError('synthetic wait expired')
        return {'text':'合成晚到回覆','answers':{}}


class DialogueConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.provider=DelayedProvider();self.errors=[]
        self.service=DialogueService(DialogueStore(Path(self.tmp.name)/'dialogue.sqlite'),self.provider)
        self.tid=self.service.start()['id'];self.workers=[]

    def tearDown(self):
        self.provider.release.set()
        for worker in self.workers:worker.join(5)
        self.service.close();self.tmp.cleanup()

    def start_send(self):
        def work():
            try:self.service.send(self.tid,'合成問題','request-one')
            except Exception as exc:self.errors.append(exc)
        worker=threading.Thread(target=work);self.workers.append(worker);worker.start()
        self.assertTrue(self.provider.entered.wait(2))
        return worker

    def test_state_and_new_thread_usable_while_request_waits(self):
        self.start_send()
        self.assertTrue(self.service.has_inflight())
        self.assertEqual(self.service.state(self.tid)['messages'],[])
        self.assertNotEqual(self.service.start()['id'],self.tid)
        with self.assertRaisesRegex(ValueError,'處理中'):
            self.service.send(self.tid,'合成問題','request-one')
        self.provider.release.set();self.workers[0].join(2)
        self.assertFalse(self.errors)
        self.assertEqual(len(self.service.state(self.tid)['messages']),2)

    def test_cancel_fences_late_result_and_does_not_claim_remote_stopped(self):
        self.start_send()
        status=self.service.stop(self.tid)
        self.assertTrue(status['cancel_requested']);self.assertFalse(status['remote_stopped'])
        self.assertTrue(self.provider.context['cancelled']())
        self.assertTrue(self.service.has_inflight())
        self.provider.release.set();self.workers[0].join(2)
        self.assertEqual(len(self.errors),1)
        self.assertEqual(self.service.state(self.tid)['messages'],[])
        self.assertEqual(self.service.list_saved(),[])

    def test_close_fences_and_drains_before_returning(self):
        self.start_send();closed=threading.Event()
        def close():self.service.close();closed.set()
        worker=threading.Thread(target=close);self.workers.append(worker);worker.start()
        self.assertFalse(closed.wait(.05))
        self.assertTrue(self.provider.context['cancelled']())
        with self.assertRaisesRegex(ValueError,'關閉'):self.service.start()
        self.provider.release.set();self.assertTrue(closed.wait(2))
        self.assertEqual(self.service.state(self.tid)['messages'],[])

    def test_bridge_allows_state_and_cancel_during_main_send(self):
        session=WebSession(directory=Path(self.tmp.name)/'app')
        try:
            session.dialogue.provider=self.provider
            bridge=WebBridge(session)
            tid=session.dialogue.start()['id'];result=[]
            worker=threading.Thread(target=lambda:result.append(bridge.call('dialogue_send',{'id':tid,'text':'合成','request_id':'r'})))
            self.workers.append(worker);worker.start()
            self.assertTrue(self.provider.entered.wait(2))
            self.assertTrue(bridge.call('dialogue_state',{'id':tid})['ok'])
            self.assertFalse(bridge.call('connection_save',{'endpoint':'https://fixture.example.test'})['ok'])
            self.assertTrue(bridge.call('dialogue_stop',{'id':tid})['ok'])
            self.provider.release.set();worker.join(2)
            self.assertFalse(result[0]['ok'])
            self.assertEqual(session.dialogue.state(tid)['messages'],[])
        finally:
            self.provider.release.set();session.close()

    def test_finishing_request_retains_guard_until_cleanup(self):
        # Pause immediately before the finally block acquires its condition.
        # A subsequent send/delete must still see the original request in flight.
        for operation in ('send','inspect'):
            with self.subTest(operation=operation):
                service=DialogueService(DialogueStore(Path(self.tmp.name)/(operation+'.sqlite')))
                tid=service.start()['id']
                if operation=='inspect':
                    with patch.object(service.provider,'respond',side_effect=ValueError('synthetic')):
                        with self.assertRaises(ValueError):service.send(tid,'first','first')
                entered=threading.Event();release=threading.Event();actual=service._condition;result=[]
                class PauseCondition:
                    def __enter__(self):
                        entered.set()
                        if not release.wait(3):raise AssertionError('cleanup pause expired')
                        return actual.__enter__()
                    def __exit__(self,*args):return actual.__exit__(*args)
                    def notify_all(self):return actual.notify_all()
                def work():
                    try:result.append(service.send(tid,'first','first') if operation=='send' else service.inspect(tid))
                    except Exception as exc:result.append(exc)
                worker=threading.Thread(target=work)
                try:
                    with patch.object(service,'_condition',PauseCondition()):
                        worker.start();self.assertTrue(entered.wait(2))
                        self.assertTrue(service.has_inflight())
                        with self.assertRaisesRegex(ValueError,'處理中'):service.send(tid,'second','second')
                        with self.assertRaisesRegex(ValueError,'處理中'):service.preview_delete('threads',[tid])
                        release.set();worker.join(2)
                    self.assertIsInstance(result[0],dict)
                    self.assertFalse(service.has_inflight())
                finally:
                    release.set();worker.join(3);service.close()

    def test_profile_delete_serializes_idle_check_with_new_request(self):
        session=WebSession(directory=Path(self.tmp.name)/'profile-race')
        worker=None;started=threading.Event();entered=threading.Event();results=[]
        try:
            session.profiles.set_endpoint('https://synthetic.example.test/v1')
            session.profiles.set_wire_mode('assistants')
            pid=session.profiles.save('合成助理','asst_synthetic')
            revision=session.profiles.snapshot(pid)['revision']
            tid=session.dialogue.start('chat',f'company:{pid}:{revision}')['id']
            original=session.profiles.remove
            def request():
                started.set()
                try:session.dialogue.send(tid,'合成測試','race')
                except Exception as exc:results.append(exc)
            def remove(*args):
                nonlocal worker
                worker=threading.Thread(target=request);worker.start();self.assertTrue(started.wait(1))
                self.assertFalse(entered.wait(.1))
                return original(*args)
            def remote(*args,**kwargs):entered.set();return 'unexpected'
            with patch.object(session.profiles,'remove',side_effect=remove),patch.object(session.profiles,'respond',side_effect=remote):
                result=WebBridge(session).call('profile_delete',{'id':pid,'revision':revision})
                self.assertTrue(result['ok'],result);worker.join(2)
            self.assertFalse(entered.is_set());self.assertEqual(len(results),1)
        finally:
            if worker:worker.join(3)
            session.close()


if __name__=='__main__':unittest.main()
