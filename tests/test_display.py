"""DPI arithmetic/API mocks and real Tk layout; not Windows scale acceptance."""
import copy
import ctypes
import gc
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import font, ttk
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from desktop_app.config import DEFAULT
from desktop_app.display import Display, WorkspaceViewport, awareness, initialize_dpi, scroll_frame, work_area
from desktop_app.theme import Appearance
from desktop_app.ui import App


class DisplayPolicyTests(unittest.TestCase):
    def test_common_percentages_convert_logical_pixels_and_pick_exact_icon(self):
        for factor, expected in ((1, (24, 208, 32)), (1.25, (30, 260, 40)),
                                 (1.5, (36, 312, 48)), (2, (48, 416, 64))):
            with self.subTest(factor=factor):
                display = Display(SimpleNamespace(), factor=factor)
                self.assertEqual(display.px((24, 208, 32)), expected)
                self.assertEqual(display.px([0, 8, 16]), (0, round(8 * factor), round(16 * factor)))
                self.assertEqual(display.icon_size(), expected[0])

    def test_awareness_preserves_existing_context_without_setting_process(self):
        for current in ('system', 'per_monitor', 'unknown', 'not_windows'):
            with self.subTest(current=current), patch('desktop_app.display.awareness', return_value=current), patch('desktop_app.display.ctypes.WinDLL') as api:
                self.assertEqual(initialize_dpi(), {'before': current, 'after': current, 'changed': False})
                api.assert_not_called()

    def test_unaware_startup_requests_system_context_and_reports_failure(self):
        for success, final in ((True, 'system'), (False, 'unaware')):
            with self.subTest(success=success), patch('desktop_app.display.awareness', side_effect=['unaware', final]), patch('desktop_app.display.ctypes.WinDLL') as api:
                user = api.return_value
                user.SetProcessDpiAwarenessContext.return_value = success
                outcome = initialize_dpi()
                self.assertEqual(outcome, {'before': 'unaware', 'after': final, 'changed': success})
                requested = user.SetProcessDpiAwarenessContext.call_args.args[0]
                self.assertEqual(requested.value, ctypes.c_void_p(-2).value)

    def test_older_api_fallback_and_total_failure_are_explicit(self):
        for success in (True, False):
            with self.subTest(success=success), patch('desktop_app.display.awareness', side_effect=['unaware', 'system' if success else 'unaware']), patch('desktop_app.display.ctypes.WinDLL', side_effect=AttributeError), patch('desktop_app.display.ctypes.windll') as legacy:
                legacy.user32.SetProcessDPIAware.return_value = success
                self.assertEqual(initialize_dpi()['changed'], success)
                legacy.user32.SetProcessDPIAware.assert_called_once_with()
        with patch('desktop_app.display.awareness', return_value='unaware'), patch('desktop_app.display.ctypes.WinDLL', side_effect=OSError), patch('desktop_app.display.ctypes.windll') as legacy:
            legacy.user32.SetProcessDPIAware.side_effect = OSError('unavailable')
            self.assertEqual(initialize_dpi(), {'before': 'unaware', 'after': 'unaware', 'changed': False})

    def test_awareness_read_mapping_and_unavailable_are_not_fabricated(self):
        for code, expected in ((0, 'unaware'), (1, 'system'), (2, 'per_monitor'), (99, 'unknown')):
            with self.subTest(code=code), patch('desktop_app.display.sys.platform', 'win32'), patch('desktop_app.display.ctypes.WinDLL') as api:
                api.return_value.GetAwarenessFromDpiAwarenessContext.return_value = code
                self.assertEqual(awareness(), expected)
        with patch('desktop_app.display.sys.platform', 'win32'), patch('desktop_app.display.ctypes.WinDLL', side_effect=OSError):
            self.assertEqual(awareness(), 'unknown')

    def test_small_work_area_clamps_size_and_minimum_at_each_factor(self):
        for factor in (1, 1.25, 1.5, 2):
            with self.subTest(factor=factor):
                display = Display(SimpleNamespace(), factor=factor)
                window = MagicMock()
                with patch('desktop_app.display.work_area', return_value=(100, 50, 800, 600)):
                    display.size_window(window, 1280, 860, (1050, 700))
                available = (800 - display.px(24), 600 - display.px(64))
                window.minsize.assert_called_once_with(*available)
                window.geometry.assert_called_once_with(
                    f'{available[0]}x{available[1]}+{100 + display.px(12)}+{50 + display.px(12)}')
                self.assertLessEqual(available[0] + display.px(12), 800)
                self.assertLessEqual(available[1] + display.px(12), 600)

    def test_work_area_api_failure_uses_screen_size(self):
        root = MagicMock()
        root.winfo_screenwidth.return_value = 1280
        root.winfo_screenheight.return_value = 720
        with patch('desktop_app.display.sys.platform', 'win32'), patch('desktop_app.display.ctypes.WinDLL', side_effect=OSError):
            self.assertEqual(work_area(root), (0, 0, 1280, 720))


class DisplayWidgetTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.tk.call('tk', 'scaling', 96 / 72)
        self.root.geometry('1100x780')
        self.root.deiconify()
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.root = None
        gc.collect()

    def test_scaling_existing_widgets_and_retheme_is_not_cumulative(self):
        display = Display(self.root, factor=1.5)
        appearance = Appearance(self.root)
        panel = ttk.Frame(self.root, padding=(8, 12))
        panel.pack(padx=10, pady=8)
        text = tk.Text(panel, width=30, height=3, padx=8, pady=6, font=('Microsoft JhengHei', 12))
        text.pack()
        text.tag_configure('sample', spacing1=4, lmargin1=10)
        text.insert('end', '草稿保持', 'sample')
        text.tag_add('sel', '1.0', '1.2')
        tree = ttk.Treeview(panel, columns=('value',), show='headings')
        tree.column('value', width=100, minwidth=40, stretch=False)
        tree.pack()
        appearance.apply(panel)
        self.root.update()
        self.assertEqual(text.winfo_pixels(text.cget('padx')), 12)
        self.assertEqual(text.winfo_pixels(text.tag_cget('sample', 'lmargin1')), 15)
        self.assertEqual(tree.column('value', 'width'), 150)
        self.assertEqual(tree.column('value', 'minwidth'), 60)
        self.assertEqual(int(appearance.style.lookup('Treeview', 'rowheight')), 48)
        before = (str(panel.cget('padding')), panel.pack_info()['padx'], str(text.cget('padx')),
                  text.tag_cget('sample', 'lmargin1'), tree.column('value', 'width'),
                  text.get('1.0', 'end-1c'), text.tag_ranges('sel'), str(text.cget('font')))
        for theme in ('light', 'dark', 'light'):
            appearance.configure(theme)
            self.root.update()
            after = (str(panel.cget('padding')), panel.pack_info()['padx'], str(text.cget('padx')),
                     text.tag_cget('sample', 'lmargin1'), tree.column('value', 'width'),
                     text.get('1.0', 'end-1c'), text.tag_ranges('sel'), str(text.cget('font')))
            self.assertEqual(after, before)
            self.assertEqual(int(appearance.style.lookup('Treeview', 'rowheight')), 48)
        self.assertEqual(display.px(32), 48)

    def test_fonts_remain_points_and_tk_scaling_is_not_multiplied(self):
        initial = float(self.root.tk.call('tk', 'scaling'))
        for factor in (1, 1.25, 1.5, 2):
            with self.subTest(factor=factor):
                Display(self.root, factor=factor)
                appearance = Appearance(self.root)
                text = tk.Text(self.root)
                self.assertEqual(font.Font(root=self.root, font=text.cget('font')).cget('size'), 12)
                for style, expected in (('TLabel', 11), ('Primary.TButton', 11), ('CardMuted.TLabel', 10), ('Status.TLabel', 10)):
                    spec = appearance.style.lookup(style, 'font')
                    self.assertEqual(font.Font(root=self.root, font=spec).cget('size'), expected)
                self.assertEqual(float(self.root.tk.call('tk', 'scaling')), initial)
                text.destroy()

    def test_all_packaged_action_icons_have_real_requested_dimensions(self):
        directory = Path(__file__).resolve().parents[1] / 'desktop_app' / 'assets' / 'ui'
        names = ('attach', 'chat', 'issue', 'notice', 'query', 'result', 'schedule', 'send', 'settings', 'work')
        for theme in ('dark', 'light'):
            for name in names:
                for size in (24, 30, 36, 48, 60, 72, 96):
                    path = directory / f'{name}-{theme}-{size}.png'
                    with self.subTest(path=path.name):
                        self.assertTrue(path.is_file())
                        icon = tk.PhotoImage(master=self.root, file=str(path))
                        self.assertEqual((icon.width(), icon.height()), (size, size))

    def test_small_viewport_reveals_focused_action_and_resets_when_large(self):
        display = Display(self.root, factor=1)
        view = WorkspaceViewport(self.root, display, minimum=(1050, 700))
        view.pack(fill='both', expand=True)
        button = ttk.Button(view.body, text='確認操作')
        button.place(x=850, y=620, width=150, height=40)
        self.root.bind('<FocusIn>', view.reveal, add='+')
        self.root.geometry('420x280')
        self.root.update()
        self.assertTrue(view.vbar.winfo_ismapped())
        self.assertTrue(view.hbar.winfo_ismapped())
        button.focus_force()
        self.root.update()
        self.assertGreater(view.canvas.xview()[0], 0)
        self.assertGreater(view.canvas.yview()[0], 0)
        self.assertGreaterEqual(button.winfo_rootx(), view.canvas.winfo_rootx() - 1)
        self.assertGreaterEqual(button.winfo_rooty(), view.canvas.winfo_rooty() - 1)
        self.assertLessEqual(button.winfo_rootx() + button.winfo_width(), view.canvas.winfo_rootx() + view.canvas.winfo_width() + 1)
        self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), view.canvas.winfo_rooty() + view.canvas.winfo_height() + 1)
        self.root.geometry('1100x780')
        self.root.update()
        self.assertFalse(view.vbar.winfo_ismapped())
        self.assertFalse(view.hbar.winfo_ismapped())
        self.assertEqual(view.canvas.xview(), (0.0, 1.0))
        self.assertEqual(view.canvas.yview(), (0.0, 1.0))

    def test_dialog_scroll_frame_uses_content_size_and_reveals_bottom_action(self):
        Display(self.root, factor=1)
        dialog = tk.Toplevel(self.root)
        dialog.geometry('450x280')
        body = scroll_frame(dialog, padding=8)
        body.pack(fill='both', expand=True)
        for index in range(24):
            ttk.Label(body, text=f'合成欄位 {index + 1}').pack(anchor='w', pady=3)
        button = ttk.Button(body, text='取消')
        button.pack(anchor='e', pady=8)
        self.root.update()
        view = next(w for w in dialog.winfo_children() if isinstance(w, WorkspaceViewport))
        self.assertTrue(view.vbar.winfo_ismapped())
        button.focus_force()
        self.root.update()
        self.assertGreater(view.canvas.yview()[0], 0)
        self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), view.canvas.winfo_rooty() + view.canvas.winfo_height() + 1)
        dialog.destroy()


class DisplayAppTests(unittest.TestCase):
    def test_simulated_multipliers_keep_chat_inside_page_and_send_reachable(self):
        # Tk point scaling is synthetic here, not a change to Windows display settings.
        for factor in (1, 1.25, 1.5, 2):
            with self.subTest(factor=factor), tempfile.TemporaryDirectory() as temp:
                root = tk.Tk()
                root.tk.call('tk', 'scaling', 96 * factor / 72)
                a = App(root, config=copy.deepcopy(DEFAULT), directory=Path(temp))
                try:
                    root.deiconify()
                    root.geometry('1050x700')
                    a.input.insert('end', '倍率切換測試草稿，保持原文')
                    root.update()
                    page = a.tabs['chat']
                    column = a.chat_column
                    for theme in ('dark', 'light'):
                        a.change_theme(theme)
                        root.update()
                        self.assertLessEqual(column.winfo_rootx() + column.winfo_width(), page.winfo_rootx() + page.winfo_width() + 1)
                        self.assertGreaterEqual(column.winfo_rootx(), page.winfo_rootx() - 1)
                        self.assertTrue(a.send_button.winfo_ismapped())
                        self.assertLessEqual(a.send_button.winfo_rootx() + a.send_button.winfo_width(), column.winfo_rootx() + column.winfo_width() + 1)
                        # At high synthetic DPI the whole workspace may scroll. Keyboard
                        # focus must bring the complete action into the actual viewport.
                        a.send_button.focus_force()
                        root.update()
                        canvas = a.viewport.canvas
                        button = a.send_button
                        self.assertGreaterEqual(button.winfo_rootx(), canvas.winfo_rootx() - 1)
                        self.assertGreaterEqual(button.winfo_rooty(), canvas.winfo_rooty() - 1)
                        self.assertLessEqual(button.winfo_rootx() + button.winfo_width(), canvas.winfo_rootx() + canvas.winfo_width() + 1)
                        self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), canvas.winfo_rooty() + canvas.winfo_height() + 1)
                        self.assertEqual(a.input.get('1.0', 'end-1c'), '倍率切換測試草稿，保持原文')
                        self.assertEqual(a.store.tasks(), [])
                finally:
                    a.close(force=True)
                    a = None
                    root = None
                    gc.collect()

    def test_normal_maximized_theme_switch_preserve_point_fonts_and_draft(self):
        with tempfile.TemporaryDirectory() as temp:
            root = tk.Tk()
            root.tk.call('tk', 'scaling', 96 / 72)
            a = App(root, config=copy.deepcopy(DEFAULT), directory=Path(temp))
            try:
                root.deiconify()
                root.geometry('1050x700')
                a.input.insert('end', '合成草稿，不送出')
                a.attachment = {'name': '合成.txt', 'text': '合成附件', 'kind': 'txt'}
                root.update()
                original = (a.input.get('1.0', 'end-1c'), copy.deepcopy(a.attachment), a.conversation)
                text_font = font.Font(root=root, font=a.transcript.cget('font')).actual()
                input_font = font.Font(root=root, font=a.input.cget('font')).actual()
                for state in ('zoomed', 'normal'):
                    root.state(state)
                    root.update()
                    for name in ('light', 'dark'):
                        a.change_theme(name)
                        root.update()
                        self.assertEqual(font.Font(root=root, font=a.transcript.cget('font')).actual(), text_font)
                        self.assertEqual(font.Font(root=root, font=a.input.cget('font')).actual(), input_font)
                        self.assertEqual((a.input.get('1.0', 'end-1c'), a.attachment, a.conversation), original)
                        self.assertEqual(a.store.tasks(), [])
                self.assertEqual(text_font['size'], 12)
                diagnostic = a.display.diagnostics()
                self.assertEqual(diagnostic['cross_monitor_live_scaling'], 'not_supported')
                self.assertNotIn('合成草稿', str(diagnostic))
                self.assertNotIn('合成附件', str(diagnostic))
            finally:
                a.close(force=True)
                a = None
                root = None
                gc.collect()


if __name__ == '__main__':
    unittest.main()
