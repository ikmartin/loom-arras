"""Previews of a key's text, made by TeX under the preamble they are read in, with the words that changed marked afterwards.

A comparison shows the text a key had beside the text it has; each side is made as a snippet (`snippets`), shaped as a page is, and then each rendered word is aligned with the source word it came from (`tex.align`), so a word whose source changed is wrapped in `mark.review-changed`, a formula or display whose source changed takes the class, and a deletion leaves a `span.review-change-point`. A side TeX refused shows its source, its changed spans marked the same way.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import posixpath
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from loom.render.markup import esc
from loom.render.publish import write_atomic
from loom.scan.model import SourceFile
from loom.scan.source import blank_comments
from loom.tex.align import rendered_words, source_words

if TYPE_CHECKING:
    from loom.render.fragments import FragmentRenderer, Later, Owner
    from loom.render.fromhtml import El

_TOKEN = re.compile(r"[^\W_][\w'’]*", re.UNICODE)
_INLINE = re.compile(r"\\\((.*?)\\\)|(?<![\\$])\$(?!\$)((?:\\.|[^$\\])+?)\$", re.DOTALL)
_POINT = '<span class="review-change-point" aria-label="edit point"></span>'


def preview_html(r: FragmentRenderer, group: Sequence[Later]) -> list[str]:
    """Each preview of `group`, which share a document and a preamble, made in one batch: from `.loom/build/cache/previews/` where made before, else by TeX."""
    from loom.render.fragments import _preview_owner
    from loom.render.snippets import render_snippets

    if not group:
        return []
    owner = _preview_owner(r, group[0])
    preamble = group[0].preamble if group[0].preamble is not None else owner.preamble
    if "\\documentclass" not in preamble:
        preamble = "\\documentclass{amsart}\n" + preamble
    keys = [
        hashlib.sha256(json.dumps([r.salt, p.key, owner.key, p.text, preamble, p.spans]).encode()).hexdigest()[:32]
        for p in group
    ]
    cache = r.plan.cache / "previews"
    out: list[str | None] = [
        (cache / f"{k}.html").read_text(encoding="utf-8") if (cache / f"{k}.html").is_file() else None for k in keys
    ]
    todo = [i for i, o in enumerate(out) if o is None]
    if not todo:
        return [o or "" for o in out]
    made = render_snippets(
        r.result.quilt.root,
        owner.base,
        preamble,
        [group[i].text for i in todo],
        r.plan.cache / "snippets",
        envs=r.envs(owner),
        engine=owner.engine,
        aux=owner.aux,
        tex=r.plan.tex,
    )
    for i, s in zip(todo, made.made, strict=True):
        p = group[i]
        markup = (
            _shaped(r, owner, p, s.html) if s.html is not None else marked_source(_named(owner, p), p.text, p.spans)
        )
        # drawn beside a live document whose anchors carry the same labels
        markup = "\n".join(line.rstrip() for line in re.sub(r'(?<=\s)id="[^"]*"', "", markup).split("\n"))
        # a side TeX refused is remembered; one the machine could not make, with no TeX4ht, is made again next time
        if s.html is not None or not s.error.startswith(("TeX is not run", "make4ht", "TeX4ht made no page")):
            write_atomic(cache / f"{keys[i]}.html", markup)
        out[i] = markup
    return [o or "" for o in out]


def _shaped(r: FragmentRenderer, owner: Owner, p: Later, made: str) -> str:
    """One preview's snippet shaped as a page is, under a file of its own beside the owner's, and its changed words marked."""
    from loom.render.fragments import _from_tex, _lines_in
    from loom.render.fromhtml import DocumentHtml, Page, html_of

    file = _named(owner, p)
    clean = blank_comments(p.text)
    src = SourceFile(file, Path(file), p.text, clean, "utf-8", False)
    page = Page(
        _lines_in(made, posixpath.relpath(file, owner.base or "."), 1),
        {},
        "",
        where=r.plan.cache / "snippets",
        normalised=True,
    )
    doc = DocumentHtml(r, owner, page, only=[], files={file: src}, pairs={})
    macros = {m.name: m.body for m in owner.macros.values()}
    body = mark_changes(doc.body, file, clean, p.spans, macros)
    return _from_tex("".join(html_of(k) for k in body))


def _named(owner: Owner, p: Later) -> str:
    """The file a preview's text stands in, of its own, beside the owner's: what its `data-src` names."""
    return posixpath.join(owner.base, "review-" + hashlib.sha256(p.text.encode()).hexdigest()[:20] + ".tex")


def marked_source(file: str, text: str, spans: Sequence[Sequence[int]]) -> str:
    """`text`, standing in `file`, as `pre.source` with its changed spans marked: a side TeX refused."""
    cuts = sorted({0, len(text), *(x for a, b in spans for x in (a, b) if 0 <= x <= len(text))})
    out: list[str] = []
    for a, b in zip(cuts, cuts[1:], strict=False):
        if any(lo == hi == a for lo, hi in spans):
            out.append(_POINT)
        piece = esc(text[a:b])
        out.append(
            f'<mark class="review-changed">{piece}</mark>' if any(lo < b and hi > a for lo, hi in spans) else piece
        )
    if any(lo == hi == len(text) for lo, hi in spans):
        out.append(_POINT)
    return f'<pre class="source" data-src="{file}:0:{len(text)}">{"".join(out)}</pre>'


def mark_changes(
    body: list[El | str], file: str, clean: str, spans: Sequence[Sequence[int]], macros: Mapping[str, str]
) -> list[El | str]:
    """`body` with what changed in its source marked: each rendered word aligned with the source word it came from, a formula with the source formula it is, a display by its `data-src`."""
    from loom.render.fromhtml import El, _walk, text_of

    if not spans:
        return body

    def changed(a: int, b: int) -> bool:
        return any((lo < b and hi > a) or (lo == hi and a < lo < b) for lo, hi in spans)

    # the formulas, in order, against the source's
    formulas = [m for m in _INLINE.finditer(clean)]
    k = 0
    for top in body:
        for el in _walk(top) if isinstance(top, El) else ():
            if "math" not in el.classes:
                continue
            if "display" in el.classes or el.tag == "figure":
                at = el.attrs.get("data-src", "")
                f, _, rest = at.partition(":")
                a, _, b = rest.partition(":")
                if f == file and a.isdigit() and b.isdigit() and changed(int(a), int(b)):
                    el.attrs["class"] += " review-changed"
                continue
            want = re.sub(r"\s+", "", re.sub(r"^\\\(|\\\)$", "", text_of(el).strip()))
            while k < len(formulas) and re.sub(r"\s+", "", formulas[k].group(1) or formulas[k].group(2) or "") != want:
                k += 1
            if k < len(formulas):
                if changed(formulas[k].start(), formulas[k].end()):
                    el.attrs["class"] += " review-changed"
                k += 1
    # the words, in order, against the source's
    tokens: list[tuple[El, int, int, int, str]] = []  # parent, kid index, start, end in that string, folded word
    for top in body:
        if isinstance(top, El):
            _tokens(top, tokens)
    words = source_words(clean, macros)
    matcher = difflib.SequenceMatcher(None, [w.text for w in words], [t[4] for t in tokens], autojunk=False)
    found: list[tuple[int, int] | None] = [None] * len(tokens)
    for blk in matcher.get_matching_blocks():
        for d in range(blk.size):
            w = words[blk.a + d]
            found[blk.b + d] = (w.start, w.end)
    # an unmatched word stands for the source between the matched words around it
    lo = 0
    marked: list[bool] = []
    for i, t in enumerate(found):
        if t is not None:
            lo = t[1]
            marked.append(changed(*t))
            continue
        hi = next((x[0] for x in found[i + 1 :] if x is not None), len(clean))
        marked.append(changed(lo, max(lo + 1, hi)))
    points: dict[int, int] = {}  # token index after which an edit point stands -> how many
    for a, b in spans:
        if a != b:
            continue
        after = max((i for i, t in enumerate(found) if t is not None and t[1] <= a), default=-1)
        points[after] = points.get(after, 0) + 1
    by_string: dict[tuple[int, int], list[tuple[int, int, bool, int]]] = {}
    parents: dict[int, El] = {}
    for i, (parent, kid, a, b, _w) in enumerate(tokens):
        parents[id(parent)] = parent
        by_string.setdefault((id(parent), kid), []).append((a, b, marked[i], points.get(i, 0)))
    for (pid, kid), toks in sorted(by_string.items(), key=lambda x: (x[0][0], -x[0][1])):
        parent = parents[pid]
        s = parent.kids[kid]
        assert isinstance(s, str)
        parent.kids[kid : kid + 1] = _wrap(s, toks)
    if -1 in points and body:
        first = next((k for k in body if isinstance(k, El)), None)
        if first is not None:
            first.kids[0:0] = [El("span", {"class": "review-change-point", "aria-label": "edit point"}, [])] * points[
                -1
            ]
    return body


def _tokens(el: El, out: list[tuple[El, int, int, int, str]]) -> None:
    """Every word of `el`'s own strings, outside what TeX made and outside mathematics, with where it stands."""
    from loom.render.fromhtml import El

    if "data-made" in el.attrs or "math" in el.classes or "env-label" in el.classes or el.tag == "summary":
        return
    for i, k in enumerate(el.kids):
        if isinstance(k, El):
            _tokens(k, out)
            continue
        for m in _TOKEN.finditer(k):
            for w in rendered_words(m.group(0)):
                out.append((el, i, m.start(), m.end(), w))


def _wrap(s: str, toks: list[tuple[int, int, bool, int]]) -> list[El | str]:
    """`s` with each run of marked words, and the space between them, in `mark.review-changed`, and edit points after the words they follow."""
    from loom.render.fromhtml import El

    out: list[El | str] = []
    pos = 0
    run: tuple[int, int] | None = None

    def flush() -> None:
        nonlocal run
        if run is not None:
            out.append(El("mark", {"class": "review-changed"}, [s[run[0] : run[1]]]))
            run = None

    seen: set[tuple[int, int]] = set()
    for a, b, marked, points in toks:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        if marked:
            if run is None:
                if a > pos:
                    out.append(s[pos:a])
                run = (a, b)
            else:
                run = (run[0], b)
            pos = b
        else:
            flush()
            if b > pos:
                out.append(s[pos:b])
            pos = b
        if points:
            flush()
            out += [El("span", {"class": "review-change-point", "aria-label": "edit point"}, []) for _ in range(points)]
    flush()
    if pos < len(s):
        out.append(s[pos:])
    return [k for k in out if not (isinstance(k, str) and not k)]
