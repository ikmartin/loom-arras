"""Text shown as its source, where TeX has made nothing of it: a document not yet compiled, a node its page lacks, a text TeX refused.

Each node keeps its identity and its label, so it can still be found, linked and annotated, and every run of source is a `pre.source` whose text is exactly the span its `data-src` names, so a selection in it is a selection in the file. Nothing is interpreted: an approximation of what TeX would print is what this replaces.
"""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from loom.render.markup import esc, slug
from loom.scan.model import SourceFile

if TYPE_CHECKING:
    from loom.render.fragments import FragmentRenderer, Owner

_BEGIN = re.compile(r"\s*\\begin\s*\{([^}]*)\}")
_SECTION = re.compile(r"\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\s*")


def source_block(file: str, start: int, end: int, text: str) -> str:
    """`text[start:end]`, trimmed of the blank lines at its edges, as `pre.source`; '' when nothing but space is there."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start >= end:
        return ""
    return f'<pre class="source" data-src="{file}:{start}:{end}">{esc(text[start:end])}</pre>'


def source_env(src: SourceFile, start: int, end: int, named: str, line: int, envs: set[str]) -> str | None:
    """A statement or proof TeX refused, its body as `pre.source` inside the stamp TeX4ht would have set, so a page shapes it as the node, or the landmark's statement, it is; None for text that opens no such environment."""
    m = _BEGIN.match(src.clean, start)
    if m is None or m.group(1) not in envs:
        return None
    from loom.scan.tokenize import read_args

    _args, _spans, body = read_args(src.clean, m.end(), "o")
    close = src.clean.rfind("\\end", body, end)
    shown = source_block(src.path, body, close if close > body else end, src.text)
    return (
        f'<div class="node" data-env="{_attr(m.group(1))}" data-file="{_attr(named)}" data-line="{line}">{shown}</div>'
    )


def source_node(
    r: FragmentRenderer, key: str, *, proofs: bool = True, stop: int | None = None, owner: Owner | None = None
) -> str:
    """A node as its source: a statement with its label and, with `proofs`, its proofs; a proof with its head; a section with its heading and the source of its body, to `stop` where the text shown ends first (a document's last section, at `\\end{document}`). Numbered as `owner` numbers it, by default the document the node is read in."""
    from loom.render.fromhtml import html_of, inline_kids, label_el

    n = r.asm.nodes[key]
    src = r.result.files[n.file]
    owner = owner if owner is not None else r.owner_of(n)
    if n.kind == "section":
        clean = src.clean
        m = _SECTION.match(clean, n.start)
        from loom.scan.sections import starred_at
        from loom.scan.tokenize import read_args

        (_short, title), _spans, heading_end = read_args(clean, m.end() if m else n.start, "om")
        level = n.level if n.level is not None else 1
        number = None if starred_at(clean, n.start) else _number(owner.numbers, [n.id, *n.labels])
        shown = "".join(html_of(k) for k in inline_kids(title or "", owner.numbers, owner.macros))
        head = (f'<span class="number">{esc(number)}</span> ' if number else "") + shown
        h = min(max(level, 1), 6)
        ident = f'data-id="{_attr(n.id)}"' if n.id else f'data-key="{_attr(key)}"'
        body = source_body(r, n.file, heading_end, min(n.end, stop) if stop is not None else n.end, owner=owner)
        return (
            f'<section id="{slug(key)}" {ident} data-level="{level}" data-src="{n.file}:{n.start}:{n.end}">'
            f'<h{h} data-src="{n.file}:{n.start}:{heading_end}">{head}</h{h}>{body}</section>'
        )
    env = r.env_at.get((n.file, n.start))
    body_start, body_end = (env.body_start, env.body_end) if env is not None else (n.start, n.end)
    body = source_block(n.file, body_start, body_end, src.text)
    pairs = " ".join(r._pair_attrs(n))
    pairs = f" {pairs}" if pairs else ""
    if n.kind == "proof":
        head = esc(n.title) if n.title else "Proof"
        attrs = f'class="env env-proof" id="{slug(key)}"'
        if n.id:
            attrs += f' data-id="{_attr(n.id)}"'
        attrs += f' data-key="{_attr(key)}"'
        if n.of:
            attrs += f' data-of="{_attr(n.of)}"'
        return f'<details {attrs} data-src="{n.file}:{n.start}:{n.end}"{pairs} open><summary class="env-label">{head}</summary>{body}</details>'
    if n.kind != "environment":
        return source_body(r, n.file, n.start, n.end, owner=owner)
    attrs = f'class="env env-{slug(n.taxon or n.env or "env")}" id="{slug(key)}"'
    if n.id:
        attrs += f' data-id="{_attr(n.id)}"'
    attrs += f' data-key="{_attr(key)}" data-taxon="{_attr(n.taxon or "")}" data-style="{_attr(n.style or "plain")}"'
    attrs += f' data-src="{n.file}:{n.start}:{n.end}"{pairs}'
    if n.digest:
        attrs += f' data-macros="{_attr(n.digest)}"'
    label = html_of(label_el(n, owner.numbers, None, owner.macros))
    out = f"<div {attrs}>{label}{body}</div>"
    if proofs:
        out += "".join(source_node(r, p, owner=owner) for p in n.proofs if p in r.asm.nodes)
    return out


def source_body(
    r: FragmentRenderer,
    file: str,
    start: int,
    end: int,
    *,
    seen: tuple[str, ...] = (),
    owner: Owner | None = None,
) -> str:
    """`file[start:end]` as its source, each node in it as `source_node`, each file it includes in place as `div.included`, and the prose between as `pre.source`."""
    claims = sorted(
        (n.start, -min(n.end, end), k)
        for k, n in r.asm.nodes.items()
        if n.file == file
        and n.kind in ("environment", "proof", "section")
        and start <= n.start < end
        and (n.kind == "section" or n.end <= end)
    )
    out: list[str] = []
    pos = start
    for a, neg_b, key in claims:
        if a < pos:
            continue
        out.append(_prose(r, file, pos, a, seen, owner))
        out.append(source_node(r, key, proofs=False, stop=end, owner=owner))
        pos = -neg_b
    out.append(_prose(r, file, pos, end, seen, owner))
    return "".join(out)


def _prose(r: FragmentRenderer, file: str, start: int, end: int, seen: tuple[str, ...], owner: Owner | None) -> str:
    """Prose as `pre.source`, cut at each inclusion the scan read there, `\\input` or a macro of the author's that wraps one, which is shown in place with the included file's source."""
    src = r.result.files[file]
    out: list[str] = []
    pos = start
    for a, b, child in _inclusions(r).get(file, ()):
        if a < pos or a >= end or child not in r.result.files or child in seen or child == file:
            continue
        out.append(source_block(file, pos, b, src.text))
        size = len(r.result.files[child].text)
        inner = source_body(r, child, 0, size, seen=(*seen, file), owner=owner)
        out.append(
            f'<div class="included" data-key="{_attr(child)}" data-file="{_attr(child)}" data-src="{child}:0:{size}">{inner}</div>'
        )
        pos = b
    out.append(source_block(file, pos, end, src.text))
    return "".join(out)


def _inclusions(r: FragmentRenderer) -> dict[str, list[tuple[int, int, str]]]:
    """Every inclusion the scan read, by the file it stands in: where it stands and the file it includes, in order; read once per renderer."""
    known: dict[str, list[tuple[int, int, str]]] | None = getattr(r, "_source_inclusions", None)
    if known is not None:
        return known
    found: dict[str, set[tuple[int, int, str]]] = {}
    for exp in r.result.expansions.values():
        for inc in exp.inclusions:
            if inc.child is not None and not inc.problem:
                found.setdefault(inc.parent, set()).add((inc.site_start, inc.site_end, inc.child))
    known = {f: sorted(v) for f, v in found.items()}
    r._source_inclusions = known  # type: ignore[attr-defined]
    return known


def _number(numbers: dict, labels: list[str | None]) -> str | None:  # type: ignore[type-arg]
    return next((numbers[lab].number for lab in labels if lab and lab in numbers), None)


def _attr(value: str) -> str:
    return html.escape(value, quote=True)
