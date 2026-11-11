"""Text that is never compiled, made HTML by TeX: each text runs through TeX4ht under the preamble of the document that owns it.

One run takes every text of one preamble, each in a group of its own between marks, so a run pays for the preamble once; a long list is cut into as many runs as there are workers, which run at once. A text with a TeX error on its own lines fails in that run and the others keep theirs. A text that breaks the run (an unclosed environment, a runaway argument, an `\\end{document}`) is the first whose output does not stand whole between its marks: it runs again alone and the texts after it run again without it, so a bad text costs only itself; a run that makes no page at all is halved. Each text's output is normalised as a document's page is (`normalise`), so nothing TeX4ht wrote reaches a page as written, and cached by everything it was made from.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from loom.render.normalise import normalise
from loom.tex.tex4ht import make_html, repair_displays

#: The document a run compiles, written beside the owning document so its local files resolve.
NAME = "loom-snippets"
#: Part of every cache key, for a change to how texts are made that `salt` does not see.
VERSION = "1"
#: Where a text's pictures go, under the cache directory; a picture's `src` is relative to the cache directory.
PICTURES = "pictures"
#: The fewest texts worth a run of their own: below this a list is not cut, since each run pays for the preamble.
SHARE = 50

_MARK = re.compile(r'<span class="loom-snippet" data-snippet="(\d+|end)"></span>')
_TAG = re.compile(r"<(/?)([A-Za-z][\w-]*)[^>]*?(/?)>")
_VOID = frozenset({"br", "hr", "img"})
_ERROR = re.compile(r"^! (.*)$")
_AT = re.compile(r"^l\.(\d+)")


@dataclass
class Snippet:
    """One text made HTML: `html` its normalised markup, None when TeX could not make it, `error` the first thing TeX said against it."""

    html: str | None
    error: str = ""
    cached: bool = False


@dataclass
class Snippets:
    """Every text asked for, in order, and what making them cost: TeX4ht runs and seconds."""

    made: list[Snippet] = field(default_factory=list)
    runs: int = 0
    seconds: float = 0.0


@dataclass
class _Run:
    pieces: dict[int, Snippet]  # by text id, the texts before the first that broke the run
    broke: int | None  # the position of the first text whose output does not stand whole
    page: bool  # whether TeX4ht made a page at all
    fatal: str = ""  # why no text of this preamble can be made: the preamble itself, or a run that ran out of time


def snippet_key(preamble: str, base: str, text: str, *, engine: str, envs: Sequence[str], salt: str) -> str:
    """A text's cache key: everything its HTML is made from."""
    said = json.dumps([VERSION, salt, engine, base, sorted(set(envs)), preamble, text])
    return hashlib.sha256(said.encode("utf-8")).hexdigest()[:32]


def render_snippets(
    root: Path,
    base: str,
    preamble: str,
    texts: Sequence[str],
    cache_dir: Path,
    *,
    envs: Sequence[str] = (),
    engine: str = "pdflatex",
    aux: Path | None = None,
    salt: str = "",
    workers: int | None = None,
    timeout: int = 600,
) -> Snippets:
    """Make each of `texts` HTML under `preamble`, from the cache where it was made before.

    Parameters
    ----------
    root : Path
        The quilt root.
    base : str
        The owning document's directory, quilt-relative ('' at the root), where its local files resolve.
    preamble : str
        The owning document's text before `\\begin{document}`, its `\\documentclass` included.
    texts : sequence of str
        The texts, each a run of a document's body.
    cache_dir : Path
        Where each text's HTML is kept, `<key>.html`, or why it could not be made, `<key>.failed`; its pictures go in `pictures/`, which a picture's `src` names.
    envs : sequence of str, default ()
        The environments stamped as nodes, as a document's page stamps them.
    engine : str, default 'pdflatex'
    aux : Path, optional
        The owning document's aux, read so a reference or a citation prints what the document prints.
    salt : str, default ''
        loom's code, so a change to how pages are read makes every text again.
    workers : int, optional
        TeX4ht runs at once; default half the machine's cores, at most four.
    timeout : int, default 600
        Seconds for each run.

    Returns
    -------
    Snippets
        One `Snippet` per text, in order.
    """
    began = time.monotonic()
    out = Snippets(made=[Snippet(None) for _ in texts])
    keys = [snippet_key(preamble, base, t, engine=engine, envs=envs, salt=salt) for t in texts]
    first: dict[str, int] = {}  # a text asked for twice is made once
    for i, k in enumerate(keys):
        made, failed = cache_dir / f"{k}.html", cache_dir / f"{k}.failed"
        if made.is_file():
            out.made[i] = Snippet(made.read_text(encoding="utf-8"), cached=True)
        elif failed.is_file():
            out.made[i] = Snippet(None, failed.read_text(encoding="utf-8"), cached=True)
        else:
            first.setdefault(k, i)
    batch = sorted(first.values())
    if batch and shutil.which("make4ht") is None:
        # the machine's, not the text's: nothing is remembered
        for i in batch:
            out.made[i] = Snippet(None, "make4ht is not installed")
        batch = []
    lock = threading.Lock()
    remember = True

    def run(ids: list[int]) -> None:
        nonlocal remember
        with lock:
            out.runs += 1
        r = _one_run(root, base, preamble, [(i, texts[i]) for i in ids], cache_dir, envs, engine, aux, timeout)
        if r.fatal:
            remember = remember and "timed out" not in r.fatal
            for i in ids:
                out.made[i] = Snippet(None, r.fatal)
            return
        if not r.page:
            if len(ids) == 1:
                out.made[ids[0]] = Snippet(None, "TeX made no page of it")
                return
            run(ids[: len(ids) // 2])
            run(ids[len(ids) // 2 :])
            return
        for i in ids if r.broke is None else ids[: r.broke]:
            out.made[i] = r.pieces[i]
        if r.broke is None:
            return
        rest = ids[r.broke :]
        if len(rest) == 1:
            out.made[rest[0]] = r.pieces.get(rest[0]) or Snippet(None, "its output does not stand whole")
            return
        # the first text whose output is not whole: alone, it breaks again and is the one, or its neighbours harmed it
        run(rest[:1])
        run(rest[1:])

    if batch:
        n = max(1, min(workers or min(4, (os.cpu_count() or 2) // 2), len(batch) // SHARE or 1))
        parts = [batch[k * len(batch) // n : (k + 1) * len(batch) // n] for k in range(n)]
        with ThreadPoolExecutor(max_workers=n, thread_name_prefix="loom-snippets") as pool:
            list(pool.map(run, parts))
        if remember:
            cache_dir.mkdir(parents=True, exist_ok=True)
            for i in batch:
                s = out.made[i]
                if s.html is not None:
                    (cache_dir / f"{keys[i]}.html").write_text(s.html, encoding="utf-8")
                else:
                    (cache_dir / f"{keys[i]}.failed").write_text(s.error or "TeX made nothing of it", encoding="utf-8")
    for i, k in enumerate(keys):
        if k in first and first[k] != i:
            out.made[i] = out.made[first[k]]
    out.seconds = time.monotonic() - began
    return out


def _one_run(
    root: Path,
    base: str,
    preamble: str,
    texts: list[tuple[int, str]],
    cache_dir: Path,
    envs: Sequence[str],
    engine: str,
    aux: Path | None,
    timeout: int,
) -> _Run:
    """One TeX4ht run over `texts`, each in a group between marks; an error on a text's lines, or on the mark after it, is that text's."""
    lines = preamble.rstrip("\n").split("\n") + ["\\begin{document}"]
    body = len(lines)
    spans: list[tuple[int, int, int]] = []
    displays: dict[str, str] = {}
    for i, text in texts:
        lines += [f"\\loomsnippet{{{i}}}", "\\begingroup"]
        fixed, found = repair_displays(text, len(displays))
        displays.update({str(n): tex for n, (_line, tex) in enumerate(found, start=len(displays))})
        start = len(lines) + 1
        lines += [*fixed.split("\n"), "\\par\\endgroup"]
        spans.append((i, start, len(lines) + 1))
    lines += ["\\loomsnippet{end}", "\\end{document}", ""]
    page, log = make_html(
        root,
        base,
        NAME,
        "\n".join(lines),
        envs=envs,
        engine=engine,
        aux=aux,
        timeout=timeout,
        pictures=(cache_dir / PICTURES, PICTURES),
    )
    errors: dict[int, str] = {}
    early = ""
    said = log.split("\n")
    for n, ln in enumerate(said):
        m = _ERROR.match(ln)
        if m is None:
            continue
        if "timed out" in m.group(1):
            return _Run({}, None, False, m.group(1))
        at = next((int(a.group(1)) for x in said[n + 1 : n + 12] if (a := _AT.match(x)) is not None), None)
        if at is not None and at <= body:
            early = early or f"the preamble: {m.group(1).strip()}"
        hit = next((i for i, a, b in spans if at is not None and a <= at <= b), None)
        if hit is not None:
            errors.setdefault(hit, m.group(1).strip())
    if page is None:
        return _Run({}, None, False, early)
    html = normalise(page, displays).html
    expected = [str(i) for i, _ in texts] + ["end"]
    marks = _top_marks(html)
    pieces: dict[int, Snippet] = {}
    for p, (i, _text) in enumerate(texts):
        if p + 1 >= len(marks) or marks[p][0] != expected[p] or marks[p + 1][0] != expected[p + 1]:
            if i in errors:
                pieces[i] = Snippet(None, errors[i])
            return _Run(pieces, p, True)
        pieces[i] = Snippet(None, errors[i]) if i in errors else Snippet(html[marks[p][2] : marks[p + 1][1]].strip())
    return _Run(pieces, None, True)


def _top_marks(html: str) -> list[tuple[str, int, int]]:
    """The marks that stand at the top level of `html`, in order: each its text's id, where it starts and where it ends. A mark inside an element is in a text another left open."""
    found: list[tuple[str, int, int]] = []
    depth = 0
    pos = 0
    for m in _MARK.finditer(html):
        for t in _TAG.finditer(html, pos, m.start()):
            if t.group(1):
                depth -= 1
            elif not t.group(3) and t.group(2).lower() not in _VOID:
                depth += 1
        pos = m.end()
        if depth == 0:
            found.append((m.group(1), m.start(), m.end()))
    return found
