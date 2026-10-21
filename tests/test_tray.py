import unittest
from unittest.mock import Mock

from desktop_app.tray import TrayController


class TrayTests(unittest.TestCase):
    def test_icon_must_exist_before_hide_and_reused(self):
        backend = Mock()
        tray = TrayController(backend)
        self.assertTrue(tray.background())
        self.assertEqual([c[0] for c in backend.mock_calls], ['create', 'hide'])
        self.assertTrue(tray.background())
        backend.create.assert_called_once()
        tray.show()
        tray.close()
        self.assertFalse(tray.ready)
        backend.dispose.assert_called_once()

    def test_registration_failure_keeps_window_reachable(self):
        backend = Mock()
        backend.create.side_effect = RuntimeError('synthetic')
        tray = TrayController(backend)
        self.assertFalse(tray.background())
        backend.hide.assert_not_called()
        backend.show.assert_called_once()
        self.assertFalse(tray.ready)
