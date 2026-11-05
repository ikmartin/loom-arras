"""The raw HTML of a Markdown file as the viewer may draw it.

A file's body lands in the viewer's own page, which holds the write token, and agents write Markdown files, so no byte of it reaches the page as written. `clean` parses what was written and writes out only allowlisted tags and attributes, every value and every run of text escaped, so the browser reads exactly what was checked here whatever it would have made of the input, and a difference between this parser and a browser's can change how a file looks but never what runs.

No element whose contents a browser parses as something other than HTML comes out open: `<iframe>` is written shut, and `<script>`, `<style>`, `<svg>`, `<math>`, `<textarea>` and the like are refused. A refused tag is shown as the text it is, so nothing goes silently missing and a word in angle brackets stays a word.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

#: What a Markdown file's HTML may use: the elements GitHub keeps in a README, with `audio`, `video` and `iframe` beside them. None of the viewer's own landmarks (`nav`, `aside`, `main`), which its layout and styles address by name.
TAGS = frozenset(
    "a abbr audio b bdi bdo big blockquote br caption center cite code col colgroup dd del details dfn div dl dt em figcaption figure "
    "h1 h2 h3 h4 h5 h6 hr i iframe img ins kbd li mark ol p pre q rp rt ruby s samp section small source span strike strong sub summary sup "
    "table tbody td tfoot th thead time tr track tt u ul var video wbr".split()
)
VOID = frozenset({"br", "col", "hr", "img", "source", "track", "wbr"})
#: Attributes every kept tag may carry. No `class` or `style`, which would let a file dress as the viewer or draw over it, and no `name`, which overrides `document.NAME`.
EVERYWHERE = frozenset({"id", "title", "lang", "dir"})
_ALIGNED = frozenset({"align"})
ATTRIBUTES: dict[str, frozenset[str]] = {
    "a": frozenset({"href"}),
    "audio": frozenset({"src", "loop", "muted", "preload"}),
    "blockquote": frozenset({"cite"}),
    "col": frozenset({"span"}),
    "colgroup": frozenset({"span"}),
    "del": frozenset({"cite", "datetime"}),
    "details": frozenset({"open"}),
    "div": _ALIGNED,
    "h1": _ALIGNED,
    "h2": _ALIGNED,
    "h3": _ALIGNED,
    "h4": _ALIGNED,
    "h5": _ALIGNED,
    "h6": _ALIGNED,
    "iframe": frozenset({"src", "width", "height"}),
    "img": frozenset({"src", "alt", "width", "height", "align"}),
    "ins": frozenset({"cite", "datetime"}),
    "li": frozenset({"value"}),
    "ol": frozenset({"start", "reversed", "type"}),
    "p": _ALIGNED,
    "q": frozenset({"cite"}),
    "source": frozenset({"src", "type", "media"}),
    "table": _ALIGNED,
    "td": frozenset({"colspan", "rowspan", "align"}),
    "th": frozenset({"colspan", "rowspan", "align", "scope"}),
    "time": frozenset({"datetime"}),
    "tr": _ALIGNED,
    "track": frozenset({"src", "kind", "srclang", "label", "default"}),
    "video": frozenset({"src", "poster", "width", "height", "loop", "muted", "preload"}),
}
#: The schemes a kept URL may name; a URL with none is relative. A link takes what Markdown's own links are for, and anything fetched as a resource is on the web or relative.
LINK_SCHEMES = frozenset({"http", "https", "mailto", "quilt", "cited", "app"})
RESOURCE_SCHEMES = frozenset({"http", "https"})
_NUMERIC = frozenset({"width", "height", "span", "start", "value", "colspan", "rowspan"})
#: What a frame is always given, whatever the file asked for. The sandbox grants what an embedded player needs and no navigation of the viewer; `allow-same-origin` is the frame's own origin, never the viewer's, since only an `https:` address is drawn and `loom serve` answers on `http:`. No `autoplay`, so a page does not start talking when opened.
FRAME = (
    ' sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms allow-presentation"'
    ' allow="fullscreen; encrypted-media; picture-in-picture" allowfullscreen'
    ' referrerpolicy="strict-origin-when-cross-origin" loading="lazy"'
)
#: What a browser drops from a URL before it reads the scheme, or ignores within it.
_CONTROLS = re.compile(r"[\x00-\x20\x7f-\x9f]+")
_SCHEME = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*):")
_DATA_IMAGE = re.compile(r"data:image/(?:gif|png|jpeg|webp);", re.I)
_NUMBER = re.compile(r"\d{1,5}%?")
_ID = re.compile(r"[\w:.-]{1,128}")
_HOST = re.compile(r"[A-Za-z0-9.-]+")


def frame_address(value: str) -> str | None:
    """The address a frame may load, or None: `https:` on a named host, a protocol-relative address taken as `https:`."""
    url = _CONTROLS.sub("", value)
    if url.startswith("//"):
        url = "https:" + url
    if "\\" in url:
        return None
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
    except ValueError:
        return None
    return url if parts.scheme.lower() == "https" and _HOST.fullmatch(host) else None


def _url(tag: str, name: str, value: str, resolve: Callable[[str, str], str]) -> str | None:
    """A URL attribute as it may be written, or None to drop it; a relative one is `resolve`d against the file."""
    compact = _CONTROLS.sub("", value)
    scheme = _SCHEME.match(compact)
    if scheme is None:
        return resolve(name, value)
    if tag == "img" and _DATA_IMAGE.match(compact):
        return value
    allowed = LINK_SCHEMES if name == "href" else RESOURCE_SCHEMES
    return value if scheme.group(1).lower() in allowed else None


class _Cleaner(HTMLParser):
    """One piece of raw HTML, written back out through the allowlist into `out`. Markup outside the allowlist goes out as text."""

    def __init__(self, resolve: Callable[[str, str], str], words: Callable[[str], str]) -> None:
        super().__init__(convert_charrefs=True)
        self.resolve = resolve
        self.words = words
        self.out: list[str] = []

    def _attributes(self, tag: str, attrs: list[tuple[str, str | None]]) -> dict[str, str] | None:
        """The attributes `tag` keeps, or None when the tag cannot stand without one it was refused."""
        kept: dict[str, str] = {}
        allowed = EVERYWHERE | ATTRIBUTES.get(tag, frozenset())
        for name, written in attrs:
            if name in kept or name not in allowed:
                continue
            value: str | None = self.words(written or "")
            if name == "src" and tag == "iframe":
                value = frame_address(value or "")
            elif name in ("href", "src", "poster", "cite"):
                value = _url(tag, name, value or "", self.resolve)
            elif (name in _NUMERIC and not _NUMBER.fullmatch(value or "")) or (
                name == "id" and not _ID.fullmatch(value or "")
            ):
                value = None
            if value is not None:
                kept[name] = value
        if tag == "iframe" and "src" not in kept:
            return None
        return kept

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        kept = self._attributes(tag, attrs) if tag in TAGS else None
        if kept is None:
            self.out.append(escape(self.get_starttag_text() or "", quote=False))
            return
        if tag == "iframe":
            kept.setdefault("title", urlsplit(kept["src"]).hostname or "")
        written = "".join(f' {name}="{escape(value, quote=True)}"' for name, value in kept.items())
        if tag == "iframe":
            self.out.append(f"<iframe{written}{FRAME}></iframe>")
        else:
            self.out.append(f"<{tag}{written}{' controls' if tag in ('audio', 'video') else ''}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag in TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag not in TAGS:
            self.out.append(escape(f"</{tag}>", quote=False))
        elif tag not in VOID and tag != "iframe":
            self.out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.out.append(escape(data, quote=False))


def clean(raw: str, resolve: Callable[[str, str], str], words: Callable[[str], str]) -> str:
    """Raw HTML as the viewer may draw it: allowlisted tags and attributes, everything escaped, and anything refused shown as its own text.

    Parameters
    ----------
    raw : str
        One piece of raw HTML as Markdown parsed it: a block, or a single inline tag. It need not balance, and what opens in one piece closes in another.
    resolve : callable
        Given a URL attribute's name and a relative value, what to write instead; a file's relative links and images are resolved this way (`loom.files`).
    words : callable
        Given an attribute's value, the same value with any lifted mathematics back in the words it was written in, since a formula cannot be typeset there.

    Returns
    -------
    str
        HTML to write into the body. Comments and declarations are dropped.
    """
    cleaner = _Cleaner(resolve, words)
    cleaner.feed(raw)
    cleaner.close()
    return "".join(cleaner.out)
