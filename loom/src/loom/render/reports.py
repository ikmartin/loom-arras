"""An agent's report, parsed into the blocks it was already written in (plan 0.11 Part A, specs/manifest.md §10).

Nothing about how an agent writes changes here. `ai/rules.md` has always said *"Write each block under a heading with its name in brackets"*, every finding has always ended with its annotation's id, and every annotation has always carried a quote selector. The structure was written down from the start; nothing was reading it. This reads it, so that a finding in a report is an object a viewer can scroll to and a quote a viewer can highlight in the draft beside it.

A file that does not parse is not an error. It becomes one unnamed block holding the whole rendered document, which is what the terminal gave you anyway.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from loom.records.store import render_markdown

#: A block heading: any level, the block's name in brackets, and whatever the agent wrote after it.
HEADING = re.compile(r"^#{1,6}[ \t]*\[(?P<name>[a-z][a-z0-9-]*)\][ \t]*(?P<rest>.*)$", re.M)

#: The elements a finding can be: a list item or a paragraph, with whatever attributes the renderer gave it.
OPENING = re.compile(r"<(li|p)(\s[^>]*)?>")

#: The annotation id a finding ends with, as `loom comment` prints it.
ANNOTATION = re.compile(r"\(\s*(a-\d{4}-\d{2}-\d{2}-\d+)\s*\)")


@dataclass
class Block:
    """One bracketed section of a report: its name, the heading as written, and the findings inside it."""

    name: str
    title: str
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name, "title": self.title}
        if self.findings:
            out["findings"] = self.findings
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
    return html, [marks[pos][1] for pos in sorted(marks)]


def _section(name: str, body_html: str, src: str, start: int, end: int) -> str:
    # `data-block` and no class: the dialect's class vocabulary is fixed, and a name is what this needs to carry.
    attr = f' data-block="{name}"' if name else ""
    return f'<section{attr} data-src="{src}:{start}:{end}">{body_html}</section>'


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
        pieces.append(_section("", html, src, 0, cut))

    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        name = m.group("name")
        title = (m.group("rest") or "").strip() or name
        # The heading is rendered with the body so the agent's own wording survives; only the name is lifted out.
        chunk = text[m.start() : end]
        html, found = _anchor_findings(render_markdown(chunk.rstrip(), src=src or None, offset=m.start()))
        blocks.append(Block(name=name, title=title, findings=found))
        pieces.append(_section(name, html, src, m.start(), end))

    attr = f' data-run="{run}"' if run else ""
    root = f'<section data-fragment="report"{attr} data-src="{src}:0:{len(text)}">{"".join(pieces)}</section>'
    return Report(html=root, blocks=blocks)
