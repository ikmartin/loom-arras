"""Annotation marks in fragments (book 9.5): a resolved quote becomes `<mark class="annotation" data-annotation="ID">` inside the block whose data-src covers its source span; a quote that crosses converted markup marks the whole block instead."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

_TAG_SPLIT = re.compile(r"(<[^>]+>)")


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
        inner = html[blk.open_end : blk.close_start]
        parts = _TAG_SPLIT.split(inner)
        texts: list[tuple[int, int, str]] = []  # (inner_offset, index in parts, text)
        pos = 0
        for i, p in enumerate(parts):
            if i % 2 == 0:
                texts.append((pos, i, p))
            pos += len(p)
        placed = False
        target = _norm(e.quote)
        if target:
            for off, _, text in texts:
                nt = _norm_positions(text)
                k = nt[0].find(target)
                if k >= 0:
                    a = nt[1][k]
                    b = nt[1][k + len(target) - 1] + 1
                    abs_a = blk.open_end + off + a
                    abs_b = blk.open_end + off + b
                    edits.append(
                        (
                            abs_a,
                            abs_b,
                            f'<mark class="annotation" data-annotation="{e.ann_id}">{html[abs_a:abs_b]}</mark>',
                        )
                    )
                    placed = True
                    break
        if not placed:
            block_level.setdefault(blk.open_start, []).append(e.ann_id)
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
