"""Real SQLite todos, upgrade rollback, and stale draft races; no company IO."""
import sqlite3
import tempfile
import threading
from pathlib import Path
from unittest import TestCase, mock

from desktop_app.core import Store, Engine
from desktop_app.local_work import initialize_work_schema


class LocalWorkTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'local.sqlite'
        self.store = Store(self.path)
        self.cid = self.store.create_conversation('來源')

    def tearDown(self):
        self.temp.cleanup()

    def save(self, text='草稿', cid=None, revision=None):
        cid = cid or self.cid
        revision = revision or self.store.reserve_draft(cid)
        return self.store.save_draft(cid, revision, text, '一般對話', False, False)

    def test_todo_lifecycle_search_literal_and_source(self):
        a = self.store.create_todo(' Report %_ ', '00123', '2028-02-29', self.cid, 'once')
        b = self.store.create_todo('Report %_', '00123', '2028-02-29', self.cid, 'once')
        self.assertEqual(a['id'], b['id'])
        self.assertEqual(len(self.store.todos('%_')), 1)
        self.assertEqual(self.store.todos('REPORT')[0]['description'], '00123')
        self.assertIsNone(self.store.set_todo_state(a['id'], 'ongoing')['completed_at'])
        completed = self.store.set_todo_state(a['id'], 'done')['completed_at']
        self.assertTrue(completed)
        self.assertEqual(self.store.set_todo_state(a['id'], 'done')['completed_at'], completed)
        self.assertIsNone(self.store.set_todo_state(a['id'], 'todo')['completed_at'])
        self.store.update_todo(a['id'], 'new', 'text', None, 'ongoing')
        self.assertEqual(Store(self.path).todo(a['id'])['title'], 'new')
        self.store.delete_todo(a['id'])
        with self.assertRaises(ValueError): self.store.todo(a['id'])
        self.assertEqual(self.store.conversation(self.cid)['title'], '來源')

    def test_validation_and_request_conflict_no_partial_insert(self):
        for title, text, due in [('', '', None), ('x'*121, '', None), ('ok', 'x'*50001, None),
                                 ('ok', '', '2027-02-29'), ('ok', '', '2026-1-1')]:
            with self.subTest(title=title[:3], due=due), self.assertRaises(ValueError):
                self.store.create_todo(title, text, due)
        with self.assertRaises(ValueError): self.store.create_todo('x', source_conversation_id='missing')
        self.assertEqual(self.store.todos(), [])
        item = self.store.create_todo('x', request_id='same')
        with self.assertRaises(ValueError): self.store.create_todo('y', request_id='same')
        with self.assertRaises(ValueError): self.store.set_todo_state(item['id'], 'running')
        self.assertEqual(len(self.store.todos()), 1)

    def test_parallel_create_is_one_record(self):
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.store.create_todo('x', request_id='r')['id'])) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(results), 5); self.assertEqual(len(set(results)), 1)

    def test_drafts_reopen_isolation_and_latest_reservation_wins(self):
        c2 = self.store.create_conversation('other')
        r1 = self.store.reserve_draft(self.cid); r2 = self.store.reserve_draft(self.cid)
        self.assertTrue(self.save('new', revision=r2))
        self.assertFalse(self.save('old', revision=r1))
        self.save('other', cid=c2)
        reopened = Store(self.path)
        self.assertEqual(reopened.draft(self.cid)['text'], 'new')
        self.assertEqual(reopened.draft(c2)['text'], 'other')
        self.assertGreater(reopened.reserve_draft(self.cid), r2)

    def test_clear_fences_queued_writer(self):
        self.save()
        stale = self.store.reserve_draft(self.cid)
        self.store.clear_draft(self.cid)
        self.assertFalse(self.save('late', revision=stale))
        self.assertIsNone(self.store.draft(self.cid))

    def test_draft_cleanup_failure_rolls_back_dispatch_and_plan(self):
        calls=[]
        engine=Engine(self.store,lambda *a:None,lambda *a:calls.append(a))
        try:
            self.save('not yet accepted')
            with self.store.connection() as db:
                db.execute("CREATE TRIGGER refuse_draft BEFORE DELETE ON drafts BEGIN SELECT RAISE(ABORT,'injected'); END")
            for planned in (False,True):
                revision=self.store.reserve_draft(self.cid)
                with self.assertRaises(sqlite3.IntegrityError):
                    if planned:engine.create_plan('chat',{'text':'x'},self.cid,draft_revision=revision)
                    else:engine.run_chat(self.cid,'x',draft_revision=revision)
            self.assertEqual(self.store.tasks(),[]);self.assertEqual(self.store.plans(),[])
            self.assertEqual(self.store.messages(self.cid),[]);self.assertEqual(calls,[])
            self.assertEqual(self.store.draft(self.cid)['text'],'not yet accepted')
        finally:engine.close(wait=True)

    def test_invalid_save_keeps_last_saved_text(self):
        self.save('kept')
        with self.assertRaises(ValueError): self.save('x'*50001)
        self.assertEqual(self.store.draft(self.cid)['text'], 'kept')

    def test_delete_preview_tracks_drafts_and_preserves_todo_copy(self):
        engine = Engine(self.store, lambda *a: None, lambda *a: None)
        try:
            item = self.store.create_todo('keep', 'selected content', source_conversation_id=self.cid)
            self.save('first')
            preview = engine.preview_conversation_deletion([self.cid])
            self.assertEqual(preview['counts']['drafts'], 1)
            self.save('changed')
            with self.assertRaisesRegex(ValueError, '變更'): engine.delete_conversations(preview['token'])
            preview = engine.preview_conversation_deletion([self.cid])
            stale = self.store.reserve_draft(self.cid)
            engine.delete_conversations(preview['token'])
            self.assertFalse(self.save('late', revision=stale))
            self.assertIsNone(self.store.draft(self.cid))
            self.assertEqual(self.store.todo(item['id'])['description'], 'selected content')
        finally:
            engine.close(wait=True)

    def test_delete_transaction_failure_restores_drafts_and_conversation(self):
        engine = Engine(self.store, lambda *a: None, lambda *a: None)
        try:
            self.save()
            with self.store.connection() as db:
                db.execute("CREATE TRIGGER refuse BEFORE DELETE ON conversations BEGIN SELECT RAISE(ABORT,'injected'); END")
            preview = engine.preview_conversation_deletion([self.cid])
            with self.assertRaises(sqlite3.IntegrityError): engine.delete_conversations(preview['token'])
            self.assertEqual(self.store.draft(self.cid)['text'], '草稿')
            self.assertEqual(self.store.conversation(self.cid)['title'], '來源')
        finally:
            engine.close(wait=True)

    def make_v2(self):
        with self.store.connection() as db:
            db.execute('DROP TABLE drafts'); db.execute('DROP TABLE todos'); db.execute('PRAGMA user_version=2')

    def test_v2_backup_and_upgrade_is_repeatable_without_extra_backup(self):
        self.store.add_message(self.cid, 'user', 'history')
        self.make_v2()
        migrated = Store(self.path)
        backups = list(self.path.parent.glob('*.pre-v4-*.bak'))
        self.assertEqual(len(backups), 1)
        with sqlite3.connect(backups[0]) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT text FROM messages').fetchone()[0], 'history')
        self.assertEqual(migrated.messages(self.cid)[0]['text'], 'history')
        Store(self.path)
        self.assertEqual(len(list(self.path.parent.glob('*.pre-v4-*.bak'))), 1)

    def test_migration_failure_rolls_back_new_tables_and_version(self):
        self.make_v2()
        def fail(db):
            initialize_work_schema(db)
            raise sqlite3.OperationalError('injected')
        with mock.patch('desktop_app.core.initialize_work_schema', side_effect=fail):
            with self.assertRaises(sqlite3.OperationalError): Store(self.path)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE name IN ('todos','drafts')").fetchall(), [])
            self.assertEqual(db.execute('SELECT title FROM conversations').fetchone()[0], '來源')
        Store(self.path)
