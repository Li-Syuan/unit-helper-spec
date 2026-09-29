"""Readable semantic colors in both Tk palettes; not a human visual acceptance."""
import unittest

from desktop_app.theme import palette


def contrast(first, second):
    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4
                  for value in channels]
        return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + .05) / (low + .05)


class SemanticPaletteTests(unittest.TestCase):
    def test_regular_text_and_status_labels_have_readable_contrast(self):
        for theme, color_style in ((theme, style) for theme in ('dark', 'light')
                                   for style in ('ocean', 'violet', 'forest')):
            colors = palette(theme, color_style)
            for background in ('BG', 'SURFACE'):
                for foreground in ('INK', 'MUTED', 'ACCENT', 'WARNING', 'ERROR',
                                   'SUCCESS', 'RUNNING', 'TEAM', 'INFO'):
                    with self.subTest(theme=theme, color_style=color_style, foreground=foreground, background=background):
                        self.assertGreaterEqual(contrast(getattr(colors, foreground),
                                                        getattr(colors, background)), 4.5)
            with self.subTest(theme=theme, color_style=color_style, control='unread badge'):
                self.assertGreaterEqual(contrast(colors.INFO, colors.TINT_INFO), 4.5)
            with self.subTest(theme=theme, color_style=color_style, control='primary button'):
                self.assertGreaterEqual(contrast(colors.BUTTON_INK, colors.ACCENT), 4.5)


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
