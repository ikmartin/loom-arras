"""Annotation marks in fragments (book 9.5): a resolved quote becomes `<mark class="annotation" data-annotation="ID">` inside the block whose data-src covers its source span.

The quote is TeX and the block is HTML, so both are compared as a projection: inline math reads as `$tex$`, `\\emph{..}` and its kind read as their text, other tags read as nothing. A formula is never cut: a mark takes a whole `span.math` or none of it, and a quote inside a displayed formula marks the display as a block, since a tag inside TeX stops MathJax from reading it. A quote that still cannot be found marks its whole block.
"""

from __future__ import annotations

import html as htmllib
import re
from dataclasses import dataclass
from html.parser import HTMLParser

@dataclass
class MarkEntry:
    ann_id: str
    quote: str
    file: str
    start: int
    end: int


@dataclass
class _Block:
    tag: str
    file: str
    start: int
    end: int
    open_start: int
    open_end: int
    close_start: int = -1


class _Index(HTMLParser):
    VOID = {"br", "img", "hr", "meta", "input", "link"}

    def __init__(self, html: str) -> None:
        super().__init__()
        self.html = html
        self.line_starts = [0] + [i + 1 for i, ch in enumerate(html) if ch == "\n"]
        self.blocks: list[_Block] = []
        self.stack: list[_Block | None] = []

    def _off(self) -> int:
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        start = self._off()
        end = self.html.index(">", start) + 1
        blk: _Block | None = None
        src = a.get("data-src")
        m = re.match(r"^(.*):(\d+):(\d+)$", src) if src else None
        if m:
            blk = _Block(tag, m.group(1), int(m.group(2)), int(m.group(3)), start, end)
            self.blocks.append(blk)
        if tag not in self.VOID and not self.html[start:end].endswith("/>"):
            self.stack.append(blk)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        pass

    def handle_endtag(self, tag: str) -> None:
        while self.stack:
            blk = self.stack.pop()
            if blk is not None:
                blk.close_start = self._off()
            break


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def place_marks(html: str, entries: list[MarkEntry]) -> str:
    """Return the fragment with marks inserted; entries whose block cannot be found are left unmarked (the manifest still lists them)."""
    if not entries:
        return html
    idx = _Index(html)
    idx.feed(html)
    edits: list[tuple[int, int, str]] = []
    block_level: dict[int, list[str]] = {}
    spans: dict[tuple[int, int], list[str]] = {}
    for e in entries:
        candidates = [
            b
            for b in idx.blocks
            if b.file == e.file
            and b.start <= e.start
            and e.end <= b.end
            and b.close_start > 0
            and b.tag not in ("section", "details", "div")
            or (
                b.file == e.file
                and b.start <= e.start
                and e.end <= b.end
                and b.close_start > 0
                and b.tag == "div"
                and "math" in html[b.open_start : b.open_end]
            )
        ]
        if not candidates:
            candidates = [
                b
                for b in idx.blocks
                if b.file == e.file and b.start <= e.start and e.end <= b.end and b.close_start > 0
            ]
        if not candidates:
            continue
        blk = min(candidates, key=lambda b: b.end - b.start)
        placed = False
        if not _is_math(html[blk.open_start : blk.open_end]):
            for a_, b_ in _locate(html, blk.open_end, blk.close_start, e.quote):
                spans.setdefault((a_, b_), []).append(e.ann_id)
                placed = True
        if not placed:
            block_level.setdefault(blk.open_start, []).append(e.ann_id)
    # Two comments on the same words are one mark carrying both ids, which is the shape the viewer already reads; two edits over one range would otherwise be applied one inside the other and emit the tag as text. A span that overlaps a kept one without matching it joins that mark rather than cutting it.
    kept: list[tuple[int, int, list[str]]] = []
    for (a_, b_), ids in sorted(spans.items()):
        hit = next((k for k in kept if a_ < k[1] and k[0] < b_), None)
        if hit is None:
            kept.append((a_, b_, list(ids)))
        else:
            hit[2].extend(ids)
    for a_, b_, ids in kept:
        joined_ids = " ".join(dict.fromkeys(ids))
        edits.append((a_, b_, f'<mark class="annotation" data-annotation="{joined_ids}">{html[a_:b_]}</mark>'))
    for open_start, ids in block_level.items():
        tag_end = html.index(">", open_start)
        open_tag = html[open_start:tag_end]
        joined = " ".join(ids)
        existing = re.search(r'data-annotation="([^"]*)"', open_tag)
        if existing:
            new_tag = (
                open_tag[: existing.start()]
                + f'data-annotation="{existing.group(1)} {joined}"'
                + open_tag[existing.end() :]
            )
        else:
            new_tag = open_tag + f' data-annotation="{joined}"'
        cls = re.search(r'class="([^"]*)"', new_tag)
        if cls:
            new_tag = new_tag[: cls.start()] + f'class="{cls.group(1)} annotation-block"' + new_tag[cls.end() :]
        else:
            new_tag += ' class="annotation-block"'
        edits.append((open_start, tag_end, new_tag))
    out = html
    for a, b, rep in sorted(edits, key=lambda x: x[0], reverse=True):
        out = out[:a] + rep + out[b:]
    return out


def _norm_positions(text: str) -> tuple[str, list[int]]:
    out: list[str] = []
    idx: list[int] = []
    in_space = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not in_space and out:
                out.append(" ")
                idx.append(i)
            in_space = True
        else:
            out.append(ch)
            idx.append(i)
            in_space = False
    while out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


_MATH_OPEN = re.compile(r'^<(span|div)\b[^>]*\bclass="[^"]*\bmath\b')
_TEXT_MACRO = re.compile(r"\\(?:emph|textit|textbf|texttt|textrm|textsf|textsc|textup)\{([^{}]*)\}")
_ENTITY = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[A-Za-z]+);")


def _is_math(open_tag: str) -> bool:
    return bool(_MATH_OPEN.match(open_tag))


def project_tex(tex: str) -> str:
    """TeX as the reader sees it: math delimiters as `$`, the simple text macros unwrapped, whitespace collapsed."""
    t = tex.replace("\\(", "$").replace("\\)", "$").replace("\\[", "$$").replace("\\]", "$$")
    prev = None
    while prev != t:
        prev, t = t, _TEXT_MACRO.sub(r"\1", t)
    return _norm(t)


def _units(html: str, a: int, b: int) -> list[tuple[int, int, str, bool]]:
    """The block's content between `a` and `b` as (start, end, projected text, atomic): text runs, and each math element whole."""
    out: list[tuple[int, int, str, bool]] = []
    pos = a
    while pos < b:
        if html.startswith("<", pos):
            end = html.index(">", pos) + 1
            tag = html[pos:end]
            if _is_math(tag):
                name = _MATH_OPEN.match(tag).group(1)  # type: ignore[union-attr]
                close = _close_of(html, end, b, name)
                inner = re.sub(r"<[^>]+>", "", html[end:close])
                tex = htmllib.unescape(inner).strip()
                display = name == "div" or tex.startswith("\\[")
                if tex[:2] in ("\\(", "\\["):
                    tex = tex[2:]
                if tex[-2:] in ("\\)", "\\]"):
                    tex = tex[:-2]
                tex = tex.strip()
                d = "$$" if display else "$"
                stop = html.index(">", close) + 1
                out.append((pos, stop, f"{d}{tex}{d}", True))
                pos = stop
            else:
                pos = end
            continue
        nxt = html.find("<", pos, b)
        nxt = b if nxt < 0 else nxt
        out.append((pos, nxt, html[pos:nxt], False))
        pos = nxt
    return out


def _close_of(html: str, start: int, limit: int, name: str) -> int:
    """Where the element opened just before `start` closes: the offset of its closing tag."""
    depth = 1
    for m in re.finditer(rf"<(/?){name}\b[^>]*>", html[start:limit]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return start + m.start()
    return limit


def _locate(html: str, a: int, b: int, quote: str) -> list[tuple[int, int]]:
    """Where `quote` falls in html[a:b], as the ranges to wrap: one range when it is balanced markup, else one per run of text or formula."""
    target = project_tex(quote)
    if not target:
        return []
    chars: list[str] = []
    where: list[tuple[int, int]] = []
    units = _units(html, a, b)
    for u0, u1, text, atomic in units:
        if atomic:
            for ch in text:
                chars.append(ch)
                where.append((u0, u1))
            continue
        i = 0
        while i < len(text):
            m = _ENTITY.match(text, i)
            if m:
                chars.append(htmllib.unescape(m.group(0)))
                where.append((u0 + i, u0 + m.end()))
                i = m.end()
            else:
                chars.append(text[i])
                where.append((u0 + i, u0 + i + 1))
                i += 1
    flat, idx = _norm_positions("".join(chars))
    k = flat.find(target)
    if k < 0:
        return []
    lo = where[idx[k]][0]
    hi = where[idx[k + len(target) - 1]][1]
    lo, hi = _widen(html, lo, hi)
    if _balanced(html[lo:hi]):
        return [(lo, hi)]
    return [(max(lo, u0), min(hi, u1)) for u0, u1, text, _ in units if u0 < hi and lo < u1 and text.strip()]


def _widen(html: str, lo: int, hi: int) -> tuple[int, int]:
    """Take in the tags at either edge that the range opens or closes, so `open</em>` becomes `<em>open</em>` inside the mark."""
    while True:
        opened, stray = _imbalance(html[lo:hi])
        if opened and (m := re.match(r"</[^>]+>", html[hi:])):
            hi += m.end()
        elif stray and (m := re.search(r"<[^/!][^>]*>$", html[:lo])):
            lo = m.start()
        else:
            return lo, hi


def _imbalance(s: str) -> tuple[int, int]:
    """(elements opened and not closed, closes with no open) within `s`."""
    depth = stray = 0
    for m in re.finditer(r"<(/?)([A-Za-z][\w-]*)[^>]*?(/?)>", s):
        if m.group(1):
            if depth:
                depth -= 1
            else:
                stray += 1
        elif not m.group(3) and m.group(2).lower() not in _Index.VOID:
            depth += 1
    return depth, stray


def _balanced(s: str) -> bool:
    return _imbalance(s) == (0, 0)
