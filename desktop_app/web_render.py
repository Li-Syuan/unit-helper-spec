"""Render untrusted Markdown as inert, local-only reading content."""
from functools import lru_cache
import bleach
from markdown_it import MarkdownIt

_parser = MarkdownIt('commonmark', {'html': False, 'linkify': False}).enable('table')
_tags = ['p','br','hr','strong','em','s','blockquote','pre','code','ul','ol','li',
         'h1','h2','h3','h4','h5','h6','table','thead','tbody','tr','th','td']


@lru_cache(maxsize=128)
def render_markdown(text):
    if not isinstance(text, str) or len(text) > 200000:
        raise ValueError('內容超過閱讀上限；請縮小資料。')
    # No images, anchors, attributes, forms, SVG or scripts cross the bridge.
    return bleach.clean(_parser.render(text), tags=_tags, attributes={}, protocols=[], strip=True)
