"""TeX4ht's HTML as loom's fragment markup (plan 0.29.2): every element rebuilt from an allowlist, every value escaped.

TeX decides what a document says, so this reinterprets nothing it can avoid: it keeps TeX4ht's structure, renames its classes into the dialect's, and marks what loom needs to place the text. Nothing of the input reaches the output as written, since `\\HCode` lets a document write any HTML and the viewer's page holds the write token: an element off the allowlist is unwrapped to its text, or dropped with its contents where they are code, and an attribute off it is dropped.

A block carries `data-at="FILE:LINE"`, where TeX4ht said it began (its `<!-- l. N -->`, the file from loom's last `<!-- loom-file -->` marker, '' for the master), for `tex.align` to place it. Text TeX made rather than read (a theorem's head, a list's label, a section's number, a reference's number) sits in an element marked `data-made`, which alignment leaves out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

#: Elements dropped with everything inside them: their contents are code, or a document's own head.
DROPPED = frozenset(
    {
        "script",
        "style",
        "iframe",
        "object",
        "embed",
        "svg",
        "math",
        "template",
        "noscript",
        "textarea",
        "title",
        "head",
        "select",
        "button",
        "form",
        "input",
        "link",
        "meta",
        "base",
        "frame",
        "frameset",
        "applet",
        "audio",
        "video",
        "canvas",
    }
)
#: Elements kept as they are, with no attributes beyond those `_attrs` allows.
KEPT = frozenset(
    {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "dl",
        "dt",
        "dd",
        "ol",
        "ul",
        "li",
        "table",
        "tr",
        "td",
        "th",
        "figure",
        "figcaption",
        "sup",
        "sub",
        "br",
        "hr",
        "pre",
        "blockquote",
        "img",
        "em",
        "strong",
        "code",
    }
)
VOID = frozenset({"br", "hr", "img"})
#: The blocks a reader reads and loom places: each carries `data-at`.
BLOCKS = frozenset({"p", "h1", "h2", "h3", "h4", "h5", "h6", "dd", "li", "figcaption", "td", "th", "pre", "blockquote"})
#: TeX4ht names a span by the font it was set in, Computer Modern's, Latin Modern's (`ec-lm…`) or Times's; the style is what is kept.
_FONT = (
    (re.compile(r"^(?:ec-|t1-)?(?:cmbx|cmb|lmbx|lmb|ptmb|bold|cmssbx|ecbx|ecbi|ecrb|ecsx)"), "strong"),
    (re.compile(r"^(?:ec-|t1-)?(?:cmtt|lmtt|pcrr|cmvtt|verb|ectt|ecvt|ecit|ecst)"), "code"),
)
#: Italic and upright text, which say emphasis only against what surrounds them: a theorem's body is italic and a word emphasized in it upright, so the reshaper, which knows the theorem's style, decides.
_ITALIC = re.compile(r"^(?:ec-|t1-)?(?:cmti|cmsl|cmmi|lmri|lmro|lmsl|ptmri|ptmro|italic|cmssi|ecti|ecsl|ecsi|ecui)")
_UPRIGHT = re.compile(r"^(?:ec-|t1-)?(?:cmr|lmr|ptmr|cmss|lmss|ecrm|ecss)(?![a-z])")
_SMALLCAPS = re.compile(r"^(?:ec-|t1-)?(?:cmcsc|lmcsc|small-caps|ptmrc|eccc|ecsc)")
_LINE = re.compile(r"^\s*l\.\s*(\d+)\s*$")
_FILE = re.compile(r"^\s*loom-file\s+(.*?)\s*$")
_FILE_END = re.compile(r"^\s*loom-file-end\s*$")
#: Where one text of a run of texts begins (`render.snippets`), or `end` after the last.
_SNIPPET = re.compile(r"^\s*loomsnippet\s+(\d+|end)\s*$")
_INLINE = re.compile(r"\\\((.*?)\\\)", re.S)
#: The shapes a node's stamp has when loom's configuration wrote it; anything else is a document's own, and is emptied.
_ENV = re.compile(r"[A-Za-z@*]+")
_PATH = re.compile(r"[\w./ +-]*")
_DIGITS = re.compile(r"\d+")


@dataclass
class Normalised:
    """The rebuilt fragment and what the rebuilding left out, which a hostile document shows up in."""

    html: str
    dropped: list[str] = field(default_factory=list)
    nodes: int = 0


@dataclass
class _Formula:
    """A formula being read: displayed or inline, where it began, how deep inside it the parser is, and its TeX."""

    display: bool
    at: str
    depth: int = 1
    text: list[str] = field(default_factory=list)
    repaired: str | None = None  # a placeholder's number: the TeX is the author's as written, held beside the page
    in_text: bool = False  # a display written inside its paragraph, as TeX4ht since TeX Live 2026 writes it


class _Rebuild(HTMLParser):
    def __init__(self, displays: dict[str, str]) -> None:
        super().__init__(convert_charrefs=True)
        self.displays = displays
        self.out: list[str] = []
        self.stack: list[str | None] = []  # what each open input element became: a tag, or None for one unwrapped
        self.skip = 0  # depth inside a dropped element
        self.body = False
        self.file = ""
        self.line: int | None = None
        self.outer: list[tuple[str, int | None]] = []  # the files that input the one being read, each with its place
        self.dropped: list[str] = []
        self.nodes = 0
        self.math: list[str] | None = None  # an inline formula still open across pieces of text
        self.formula: _Formula | None = None  # a formula TeX4ht wrapped, taken whole as TeX whatever tags it holds
        self.cites = 0  # citations open around the parser
        self.loose = 0  # paragraphs closed at a mark whose own `</p>` is still to come

    # -- the parser's events --------------------------------------------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "body":
            self.body = True
            return
        if not self.body:
            return
        if self.formula is not None:
            self.formula.depth += tag not in VOID
            return
        cls = (dict(attrs).get("class") or "").split()
        # a display is a `div` between paragraphs, or a `span` inside one (TeX4ht since TeX Live 2026)
        display = tag in ("div", "span") and cls[:1] in (["mathjax-block"], ["mathjax-env"])
        if not self.skip and ((tag == "span" and cls[:1] == ["mathjax-inline"]) or display):
            self.formula = _Formula(
                display,
                f"{self.file}:{self.line or 0}",
                repaired=dict(attrs).get("data-loom-display"),
                in_text=display and tag == "span",
            )
            return
        if self.skip or tag in DROPPED:
            if tag not in VOID:
                self.skip += 1
            if tag in DROPPED:
                self.dropped.append(tag)
            return
        a = {k: (v or "") for k, v in attrs}
        made = self._open(tag, a)
        if tag not in VOID:
            self.stack.append(made)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self.body or self.formula is not None or self.skip or tag in DROPPED:
            if self.body and tag in DROPPED:
                self.dropped.append(tag)
            return
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.body or tag in VOID:
            return
        if (f := self.formula) is not None:
            f.depth -= 1
            if f.depth == 0:
                said = self.displays.get(f.repaired, "") if f.repaired is not None else "".join(f.text)
                tex = escape(said.strip(), quote=False)
                if f.display:
                    # a display inside a paragraph ends it, and what follows begins another, as a display between paragraphs is written
                    split = f.in_text and bool(self.stack) and self.stack[-1] == "p"
                    if split:
                        self.out.append("</p>")
                    self.out.append(f'<div class="math display" data-at="{f.at}">{tex}</div>')
                    if split:
                        self._emit("p", {})
                else:
                    # TeX4ht writes the space after a formula inside its span, where it would be lost
                    before = " " if said[:1].isspace() else ""
                    after = " " if said[-1:].isspace() else ""
                    self.out.append(f'{before}<span class="math inline">{tex}</span>{after}')
                self.formula = None
            return
        if self.skip:
            self.skip -= 1
            return
        if tag == "body":
            self.body = False
            return
        if tag == "p" and self.loose and (not self.stack or self.stack[-1] != "p"):
            self.loose -= 1
            return
        if not self.stack:
            return
        made = self.stack.pop()
        if made == "span cite":
            self.cites -= 1
        if made:
            self.out.append(f"</{made.split()[0]}>")

    def handle_comment(self, data: str) -> None:
        if (m := _LINE.match(data)) is not None:
            self.line = int(m.group(1))
        elif (m := _SNIPPET.match(data)) is not None:
            if self.body and not self.skip and self.formula is None:
                # a paragraph still open at a mark is the last text's, which TeX4ht closes only later when it ends in a display (TeX Live 2026); closed here, its own `</p>` then finds nothing open
                while self.stack and self.stack[-1] in ("p", None):
                    if self.stack.pop() == "p":
                        self.out.append("</p>")
                        self.loose += 1
                self.out.append(f'<span class="loom-snippet" data-snippet="{m.group(1)}"></span>')
        elif _FILE_END.match(data):
            # back in the file that input this one, where it was
            if self.outer:
                self.file, self.line = self.outer.pop()
            if self.body and not self.skip and self.formula is None:
                self.out.append('<span class="loom-file-end"></span>')
        elif (m := _FILE.match(data)) is not None:
            # a file's first paragraph says no line of its own, so until one does the place is its start
            self.outer.append((self.file, self.line))
            self.file, self.line = m.group(1), None
            # where an included file starts and ends, for its content to be wrapped as the inclusion it is
            if self.body and not self.skip and self.formula is None and _PATH.fullmatch(self.file):
                self.out.append(f'<span class="loom-file" data-file="{escape(self.file, quote=True)}"></span>')

    def handle_data(self, data: str) -> None:
        if self.formula is not None:
            self.formula.text.append(data)
            return
        if not self.body or self.skip:
            return
        if self.math is not None:
            end = data.find("\\)")
            if end < 0:
                self.math.append(data)
                return
            self.math.append(data[:end])
            self.out.append(_inline("".join(self.math)))
            self.math = None
            data = data[end + 2 :]
        at = 0
        for m in _INLINE.finditer(data):
            self.out.append(escape(data[at : m.start()], quote=False))
            self.out.append(_inline(m.group(1)))
            at = m.end()
        rest = data[at:]
        cut = rest.find("\\(")
        if cut >= 0:
            self.out.append(escape(rest[:cut], quote=False))
            self.math = [rest[cut + 2 :]]
        else:
            self.out.append(escape(rest, quote=False))

    # -- what an element becomes ----------------------------------------------------------------------------------
    def _open(self, tag: str, a: dict[str, str]) -> str | None:
        """Write the opening of what `tag` becomes and return its name, or None where it is unwrapped."""
        cls = a.get("class", "").split()
        first = cls[0] if cls else ""
        if tag == "div" and first == "loom-node":
            self.nodes += 1
            stamp = {"data-env": _ENV, "data-file": _PATH, "data-line": _DIGITS}
            return self._emit(
                "div",
                {"class": "node", **{k: v if (v := a.get(k, "")) and p.fullmatch(v) else "" for k, p in stamp.items()}},
            )
        if tag == "div" and first in ("newtheorem", "proof", "center", "quote", "quotation", "verse"):
            return self._emit(
                "blockquote" if first in ("quote", "quotation", "verse") else "div",
                {"class": {"newtheorem": "env"}.get(first, first)},
                block=first in ("quote", "quotation", "verse"),
            )
        if tag == "div" and first in ("author", "date"):
            # beneath the title: what `\\author` and `\\date` print, `\\today` a date TeX made
            return self._emit("p", {"class": first, "data-made": ""}, block=False)
        if tag == "span" and first == "loom-ref":
            return self._emit("a", {"class": "ref", "data-label": a.get("data-label", ""), "data-made": ""})
        if tag == "span" and re.fullmatch(r"(?:like)?(?:sub)*(?:section|paragraph|chapter|part)Head", first):
            # a heading run in at the head of a paragraph, as amsart sets a subsection
            return self._emit("span", {"data-head": first})
        if tag == "span" and first in ("head", "titlemark", "id", "title"):
            # a theorem's head, a section's number, a float's, an abstract's own title: what TeX printed rather than read
            return self._emit(
                "span", {"class": {"titlemark": "number", "id": "number"}.get(first, first), "data-made": ""}
            )
        if tag == "span" and first == "cite":
            # a citation is what TeX made of a key and a note, `[AKLPR, Thm. B]`, and alignment reads it as such on both sides
            self.cites += 1
            self._emit("span", {"class": "cite", "data-made": ""})
            return "span cite"
        if tag == "span" and first == "footnote-mark":
            return self._emit("sup", {"class": "footnote-mark", "data-made": ""})
        if tag in ("span", "b", "i", "tt", "u"):
            for pattern, name in _FONT:
                if pattern.match(first):
                    return self._emit(name, {})
            if _SMALLCAPS.match(first):
                return self._emit("span", {"class": "smallcaps"})
            if _ITALIC.match(first) or tag == "i":
                return self._emit("span", {"data-font": "it"})
            if _UPRIGHT.match(first):
                return self._emit("span", {"data-font": "rm"})
            if tag in ("b", "tt"):
                return self._emit({"b": "strong", "tt": "code"}[tag], {})
            return None
        if tag == "a":
            href = a.get("href", "")
            if urlsplit(href).scheme in ("http", "https", "mailto"):
                return self._emit("a", {"class": "url", "href": href})
            if self.cites and href.startswith("#X"):
                # the label TeX printed for a cited work, which TeX4ht links to the bibliography's entry `X<key>`
                return self._emit("span", {"class": "cite-label", "data-citekey": href[2:], "data-made": ""})
            return None
        if tag == "img":
            src = a.get("src", "")
            if src and not urlsplit(src).scheme and not src.startswith(("/", "\\")) and ".." not in src.split("/"):
                self._emit("img", {"src": src, "alt": a.get("alt", "")})
            return None
        if tag == "dt":
            return self._emit("dt", {"data-made": ""})
        if tag in ("td", "th"):
            align = re.search(r"text-align:\s*(left|right|center)", a.get("style", ""))
            keep = {k: a[k] for k in ("colspan", "rowspan") if a.get(k, "").isdigit()}
            return self._emit(tag, {**keep, **({"data-align": align.group(1)} if align else {})}, block=True)
        if tag == "tr":
            return self._emit("tr", {"class": "rule"} if first == "hline" else {})
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            # which heading TeX made, `sectionHead`, `likesectionHead`, `titleHead`, which says what it heads
            return self._emit(tag, {"data-head": first} if re.fullmatch(r"[A-Za-z]{1,40}", first) else {})
        if tag == "p" and first == "noindent":
            # TeX set it with no indent: it opens a section or an item, continues after a display, or stands in a list
            return self._emit("p", {"class": "noindent"})
        if tag in KEPT:
            return self._emit(tag, {}, block=tag in BLOCKS)
        if tag not in ("span", "div", "a", "colgroup", "col", "tbody", "thead"):
            self.dropped.append(tag)
        return None

    def _emit(self, tag: str, attrs: dict[str, str], *, block: bool | None = None) -> str:
        if block if block is not None else tag in BLOCKS:
            attrs["data-at"] = f"{self.file}:{self.line or 0}"
        said = "".join(
            f' {k}="{escape(v, quote=True)}"' if v != "" or k == "data-made" else f' {k}=""' for k, v in attrs.items()
        )
        self.out.append(f"<{tag}{said}>")
        return tag


@dataclass
class Block:
    """A block of a normalised fragment as alignment reads it: where TeX4ht said it began, and the text TeX read rather than made."""

    file: str
    line: int
    text: str


class _Blocks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[bool, bool, bool]] = []  # (opened a block, quiet: made or mathematics, stands apart)
        self.open: list[Block] = []
        self.found: list[Block] = []

    def _apart(self) -> None:
        """A block or a display inside a block stands apart from the words either side of it."""
        if self.open:
            self.open[-1].text += " "

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in VOID:
            if tag == "br":
                self._apart()
            return
        a = dict(attrs)
        quiet = "data-made" in a or "math" in (a.get("class") or "").split()
        at = a.get("data-at")
        # what TeX made, a formula, and a block each stand apart from the words around them: a footnote's mark sits between a word and the note
        apart = at is not None or quiet
        if apart:
            self._apart()
        if at is not None and not quiet:
            file, _, line = at.rpartition(":")
            b = Block(file, int(line) if line.isdigit() else 0, "")
            self.found.append(b)
            self.open.append(b)
        self.stack.append((at is not None and not quiet, quiet, apart))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID or not self.stack:
            return
        opened, _, apart = self.stack.pop()
        if opened:
            self.open.pop()
        if apart:
            self._apart()

    def handle_data(self, data: str) -> None:
        if self.open and not any(q for _, q, _ in self.stack):
            self.open[-1].text += data


def blocks(fragment: str) -> list[Block]:
    """The blocks of a normalised fragment, each with its own text: none of a block nested in it, of what TeX made, or of its mathematics."""
    p = _Blocks()
    p.feed(fragment)
    p.close()
    return p.found


def _inline(tex: str) -> str:
    return f'<span class="math inline">\\({escape(tex, quote=False)}\\)</span>'


def normalise(html: str, displays: dict[str, str] | None = None) -> Normalised:
    """Rebuild TeX4ht's page `html` as fragment markup.

    Parameters
    ----------
    html : str
        A whole page as TeX4ht wrote it.
    displays : dict, optional
        The TeX of each display the page holds as a placeholder, by its number (`tex4ht.repair_displays`).

    Returns
    -------
    Normalised
        The body rebuilt, the elements it dropped by name, and how many nodes loom's configuration stamped.
    """
    p = _Rebuild(displays or {})
    p.feed(html)
    p.close()
    if p.math is not None:
        p.out.append(escape("\\(" + "".join(p.math), quote=False))
    while p.stack:
        made = p.stack.pop()
        if made:
            p.out.append(f"</{made}>")
    text = re.sub(r"<p[^>]*>\s*</p>", "", "".join(p.out))
    return Normalised(text, p.dropped, p.nodes)
