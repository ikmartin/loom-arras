"""An agent's report, parsed into the blocks it was already written in (plan 0.11 Part A, specs/manifest.md §10).

Nothing about how an agent writes changes here. `ai/rules.md` has always said *"Write each block under a heading with its name in brackets"*, every finding has always ended with its annotation's id, and every annotation has always carried a quote selector. The structure was written down from the start; nothing was reading it. This reads it, so that a finding in a report is an object a viewer can scroll to and a quote a viewer can highlight in the draft beside it.

A file that does not parse is not an error. It becomes one unnamed block holding the whole rendered document, which is what the terminal gave you anyway.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import escape
from typing import Any

from loom.records.store import render_markdown

#: A block heading: any level, the block's name in brackets, and whatever the agent wrote after it.
HEADING = re.compile(r"^(?P<hashes>#{1,6})[ \t]*\[(?P<name>[a-z][a-z0-9-]*)\][ \t]*(?P<rest>.*)$", re.M)

#: A declared symbol: a list item whose first inline math is the symbol and whose remainder says what it means.
DECLARATION = re.compile(r"^[ \t]*[-*][ \t]+\$(?P<tex>[^$]+)\$(?P<means>.*)$", re.M)

#: The elements a finding can be: a list item or a paragraph, with whatever attributes the renderer gave it.
OPENING = re.compile(r"<(li|p)(\s[^>]*)?>")

#: The annotation id a finding ends with, as `loom comment` prints it.
ANNOTATION = re.compile(r"\(\s*(a-\d{4}-\d{2}-\d{2}-\d+)\s*\)")


@dataclass
class Symbol:
    """A symbol an agent declared in its `[notation]` block: the TeX as written, and what it was said to mean."""

    tex: str
    means: str

    def to_dict(self) -> dict[str, str]:
        return {"tex": self.tex, "means": self.means}


@dataclass
class Block:
    """One bracketed section of a report: its name, the heading as written, and the findings inside it."""

    name: str
    title: str
    findings: list[str] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name, "title": self.title}
        if self.findings:
            out["findings"] = self.findings
        if self.symbols:
            out["symbols"] = [s.to_dict() for s in self.symbols]
        return out


@dataclass
class Report:
    """A parsed report: the fragment a viewer renders, and the index it navigates by."""

    html: str
    blocks: list[Block]

    @property
    def findings(self) -> list[str]:
        return [f for b in self.blocks for f in b.findings]


def _anchor_findings(html: str) -> tuple[str, list[str]]:
    """Give every element that ends in an annotation id an anchor a viewer can scroll to.

    The id is at the end of the finding, so the element it belongs to is the nearest `<li>` or `<p>` that opens before it. Marking the element rather than wrapping the id keeps the report's own structure -- a finding is a list item, and it should still be one afterwards.
    """
    opens = [(m.start(), m.end(), m.group(1), m.group(2) or "") for m in OPENING.finditer(html)]
    marks: dict[int, tuple[tuple[int, int, str, str], str]] = {}
    for m in ANNOTATION.finditer(html):
        before = [o for o in opens if o[0] < m.start()]
        if before and before[-1][0] not in marks:
            marks[before[-1][0]] = (before[-1], m.group(1))
    for pos in sorted(marks, reverse=True):
        (start, stop, tag, attrs), aid = marks[pos]
        html = html[:start] + f'<{tag} id="finding-{aid}" data-annotation-id="{aid}"{attrs}>' + html[stop:]
    # The trailing `(a-...-0001)` is how an agent says which annotation a finding is; the element now carries that as an
    # attribute, so leaving the id in the prose shows the reader a machine's bookkeeping.
    html = ANNOTATION.sub("", html)
    return re.sub(r"[ \t]+(?=</(?:li|p)>)", "", html), [marks[pos][1] for pos in sorted(marks)]


def _symbols(body: str) -> list[Symbol]:
    """The symbols a `[notation]` block declares, read from the markdown rather than the rendering.

    A declaration is one list item that opens with the symbol in inline math; everything after it is what the symbol was said to mean. Reading the source and not the HTML is what keeps this out of the viewer: MathJax turns math into SVG, so by the time a browser has it the TeX is gone.
    """
    out: list[Symbol] = []
    for m in DECLARATION.finditer(body):
        means = m.group("means").strip().lstrip("-\u2014:").strip()
        out.append(Symbol(tex=m.group("tex").strip(), means=means or ""))
    return out


def _section(name: str, heading: str, body_html: str, src: str, start: int, end: int) -> str:
    # `data-block` and no class: the dialect's class vocabulary is fixed, and a name is what this needs to carry.
    attr = f' data-block="{name}"' if name else ""
    return f'<section{attr} data-src="{src}:{start}:{end}">{heading}{body_html}</section>'


def parse_report(text: str, run: str = "", src: str = "") -> Report:
    """Parse one `<mode>-<target>.notes.md` into a report fragment and its block index.

    Parameters
    ----------
    text : str
        The notes file as the agent wrote it.
    run : str, default ''
        The run the report belongs to, recorded on the fragment's root element.
    src : str, default ''
        The notes file's quilt-relative path, so every block says where in it it came from.

    Returns
    -------
    Report
        `html`, a dialect fragment of `data-fragment="report"`; `blocks`, the index.
    """
    pieces: list[str] = []
    blocks: list[Block] = []
    matches = list(HEADING.finditer(text))

    cut = matches[0].start() if matches else len(text)
    preamble = text[:cut]
    if preamble.strip():
        html, found = _anchor_findings(render_markdown(preamble.rstrip(), src=src or None))
        blocks.append(Block(name="", title="", findings=found))
        pieces.append(_section("", "", html, src, 0, cut))

    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        name = m.group("name")
        title = (m.group("rest") or "").strip() or name
        # The heading is rendered with the body so the agent's own wording survives; only the name is lifted out.
        # The brackets are the agent's way of naming a block, and the name is carried as `data-block`; a reader should
        # see the heading, not the syntax that classified it. Whatever the agent wrote after the brackets wins, because
        # it is the more specific thing they chose to say.
        level = len(m.group("hashes"))
        body = text[m.end() : end]
        # The offset moves with what `strip` removes, or every element after a blank line points a line too early.
        lead = len(body) - len(body.lstrip())
        html, found = _anchor_findings(render_markdown(body.strip(), src=src or None, offset=m.end() + lead))
        head = f'<h{level} data-src="{src}:{m.start()}:{m.end()}">{escape(title)}</h{level}>'
        blocks.append(
            Block(name=name, title=title, findings=found, symbols=_symbols(body) if name == "notation" else [])
        )
        pieces.append(_section(name, head, html, src, m.start(), end))

    attr = f' data-run="{run}"' if run else ""
    root = f'<section data-fragment="report"{attr} data-src="{src}:0:{len(text)}">{"".join(pieces)}</section>'
    return Report(html=root, blocks=blocks)
