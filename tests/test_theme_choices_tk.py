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
from desktop_app.theme import palette
from desktop_app.ui import App, ChoiceDialog


class ThemeStylePaletteTests(unittest.TestCase):
    def test_only_action_colors_change_and_unknown_styles_are_rejected(self):
        for mode in ('dark', 'light'):
            original = palette(mode)
            for style in ('violet', 'forest'):
                colors = palette(mode, style)
                self.assertNotEqual(colors.ACCENT, original.ACCENT)
                for name in ('WARNING', 'RUNNING', 'ERROR', 'SUCCESS', 'INFO', 'TINT_INFO', 'TEAM'):
                    self.assertEqual(getattr(colors, name), getattr(original, name))
        with self.assertRaises(ValueError):
            palette('dark', 'unknown')


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

    def test_style_changes_preserve_draft_and_open_dialog_without_dispatch(self):
        app = self.app
        app.input.insert('1.0', '保留草稿\n下一行')
        app.input.mark_set('insert', '2.2')
        app.input.tag_add('sel', '1.0', '1.2')
        app.attachment = {'name': 'sample.txt', 'text': 'synthetic', 'kind': 'txt'}
        before = (str(app.input), app.input.get('1.0', 'end'), app.input.index('insert'),
                  app.input.tag_ranges('sel'), app.attachment)
        form = app.forms.create([{'id': 'q', 'title': '確認？', 'type': 'yes_no',
            'options': [{'id': 'yes', 'label': '是'}, {'id': 'no', 'label': '否'}]}])
        dialog = ChoiceDialog(app, form, lambda _: None)
        dialog.variables['q'].set('yes')
        for mode in ('light', 'dark'):
            app.change_theme(mode)
            for style in ('violet', 'forest', 'ocean'):
                app.change_color_style(style)
                after = (str(app.input), app.input.get('1.0', 'end'), app.input.index('insert'),
                         app.input.tag_ranges('sel'), app.attachment)
                self.assertEqual(before, after)
                self.assertEqual(app.appearance.color_style, style)
                self.assertEqual(load_color_style(app.preferences_path), style)
                self.assertEqual(dialog.variables['q'].get(), 'yes')
                self.assertEqual(dialog.cget('background'), app.palette.BG)
                self.assertEqual(app.style.lookup('NotificationBadge.TLabel', 'foreground'), app.palette.INFO)
                self.assertEqual(app.store.tasks(), [])
        dialog.destroy()

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
