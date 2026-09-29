"""Check readable local web tokens, including actual filled control backgrounds."""
from pathlib import Path
import re
import unittest

from tests.test_theme_semantics import contrast


class WebPaletteTests(unittest.TestCase):
    def test_text_and_status_contrast_in_both_themes(self):
        css = (Path(__file__).resolve().parents[1] / 'desktop_app/web_assets/app.css').read_text('utf-8')
        for selector in (':root', 'body[data-theme=light]'):
            declaration = css.split(selector + '{', 1)[1].split('}', 1)[0]
            colors = dict(re.findall(r'--([a-z-]+):(#[a-fA-F0-9]{6})(?:;|})', declaration + '}'))
            for foreground in ('text', 'muted', 'subtle'):
                for background in ('bg', 'side', 'surface', 'raised'):
                    with self.subTest(theme=selector, foreground=foreground, background=background):
                        self.assertGreaterEqual(contrast(colors[foreground], colors[background]), 4.5)
            for semantic in ('accent', 'team', 'warning', 'info', 'danger', 'success'):
                with self.subTest(theme=selector, status=semantic):
                    self.assertGreaterEqual(contrast(colors[semantic], colors[semantic + '-bg']), 4.5)
                    self.assertGreaterEqual(contrast(colors[semantic], colors['surface']), 4.5)
            self.assertGreaterEqual(contrast(colors['on-accent'], colors['accent']), 4.5)

