"""Theme selections preserve local work and semantic colors; no company requests."""
import copy
import gc
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop_app.config import DEFAULT
from desktop_app.preferences import load_color_style, load_theme, save_appearance
from desktop_app.ui import App


class ThemeChoiceTkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root, config=copy.deepcopy(DEFAULT), directory=self.directory)
        self.root.update()

    def tearDown(self):
        self.root.update_idletasks()
        self.app.close(force=True)
        self.app = self.root = None
        gc.collect()
        self.temp.cleanup()

    def test_startup_preference_save_failure_and_reset(self):
        app = self.app
        app.change_theme('light', 'forest')
        self.assertEqual(load_theme(app.preferences_path), 'light')
        with patch('desktop_app.ui.save_appearance', side_effect=OSError('denied')), \
                patch('desktop_app.ui.messagebox.showwarning') as warning:
            app.change_color_style('violet')
        self.assertEqual(app.appearance.color_style, 'violet')
        self.assertEqual(load_color_style(app.preferences_path), 'forest')
        self.assertIn('無法保存', app.status.get())
        warning.assert_called_once()
        app.change_theme('dark')
        self.assertEqual((load_theme(app.preferences_path), load_color_style(app.preferences_path)), ('dark', 'violet'))
        app.reset_appearance()
        self.assertEqual((load_theme(app.preferences_path), load_color_style(app.preferences_path)), ('dark', 'ocean'))
        save_appearance(app.preferences_path, 'light', 'violet')
        self.root.update_idletasks()
        app.close(force=True)
        self.app = self.root = None
        del app
        gc.collect()
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root, config=copy.deepcopy(DEFAULT), directory=self.directory)
        self.assertEqual((self.app.appearance.name, self.app.appearance.color_style), ('light', 'violet'))
