"""The two string helpers every fragment writer shares: text escaped for HTML, and a name made an anchor."""

from __future__ import annotations

import html
import re


def esc(s: str) -> str:
    """`s` escaped for HTML text, quotes left as they are."""
    return html.escape(s, quote=False)


def slug(s: str) -> str:
    """`s` as an anchor: runs of anything but letters and digits become one hyphen, lower-cased; 'x' when nothing is left."""
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower() or "x"
