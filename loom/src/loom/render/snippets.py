"""Text that is never compiled, made HTML by TeX: each text runs through TeX4ht under the preamble of the document that owns it.

One run takes every text of one preamble, each in a group of its own between marks, so a run pays for the preamble once; a long list is cut into as many runs as there are workers, which run at once. A text with a TeX error on its own lines fails in that run and the others keep theirs. A text that breaks the run (an unclosed environment, a runaway argument, an `\\end{document}`) is the first whose output does not stand whole between its marks: it runs again alone, as does every later text TeX complained about in that run, and the texts after it run again together without them, so a bad text costs only itself and a list with many costs a run for each, not a run of the rest for each. A run that makes no page at all, TeX having stopped, sets apart the texts TeX complained about in the same way, and is halved only when it named none. Each text's output is normalised as a document's page is (`normalise`), so nothing TeX4ht wrote reaches a page as written, with its lines counted from its own first line, so a text made once serves wherever it stands; and cached by everything it was made from, loom's code that makes and reads it included.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import re
import shutil
import threading
import time
import tokenize
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from loom.render.normalise import normalise
from loom.tex.tex4ht import _balanced, _blank_comments, make_html, repair_displays

#: The document a run compiles, written beside the owning document so its local files resolve.
NAME = "loom-snippets"
#: Part of every cache key, beside the code that makes and reads a text (`_code`).
VERSION = "2"
#: Where a text's pictures go, under the cache directory; a picture's `src` is relative to the cache directory.
PICTURES = "pictures"
#: The fewest texts worth a run of their own: below this a list is not cut, since each run pays for the preamble.
SHARE = 50

_MARK = re.compile(r'<span class="loom-snippet" data-snippet="(\d+|end)"></span>')
_TAG = re.compile(r"<(/?)([A-Za-z][\w-]*)[^>]*?(/?)>")
_VOID = frozenset({"br", "hr", "img"})
_ERROR = re.compile(r"^! (.*)$")
_AT = re.compile(r"^l\.(\d+)")
#: A block's line and a node's, in the run's own document, whose file TeX4ht names ''.
_LINE_AT = re.compile(r'(data-at=":)(\d+)(")')
_NODE_LINE = re.compile(r'(data-file="" data-line=")(\d+)(")')


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
    complained: frozenset[int] = frozenset()  # the texts TeX said something against, anywhere in the run


def _code() -> str:
    """The code a text's HTML comes from: the configuration TeX4ht runs under, the normaliser, and this module, as code: their comments and docstrings left out, so a reworded comment makes nothing again."""
    if not _CODE:
        from loom.render import normalise as n
        from loom.tex import tex4ht as t

        h = hashlib.sha256()
        for mod in (t.__file__, n.__file__, __file__):
            h.update(_as_code(Path(mod).read_text(encoding="utf-8")).encode())
        _CODE.append(h.hexdigest())
    return _CODE[0]


def _as_code(source: str) -> str:
    """`source` without its comments, docstrings and blank lines, as text: an AST's dump differs from one Python to the next, and a key from it would never meet a cache made under another."""
    tree = ast.parse(source)
    lines = source.split("\n")
    gone: set[int] = set()
    cut: dict[int, int] = {}
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (
            isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            doc = body[0]
            first = doc.lineno - 1
            if lines[first][: doc.col_offset].strip():
                cut[first] = doc.col_offset
                first += 1
            gone.update(range(first, doc.end_lineno or doc.lineno))
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            cut[tok.start[0] - 1] = min(tok.start[1], cut.get(tok.start[0] - 1, tok.start[1]))
    kept = (line[: cut[n]] if n in cut else line for n, line in enumerate(lines) if n not in gone)
    return "\n".join(line.rstrip() for line in kept if line.strip())


_CODE: list[str] = []


def snippet_key(
    preamble: str,
    base: str,
    text: str,
    *,
    engine: str,
    envs: Sequence[str],
    salt: str,
    math: str = "mathjax",
    aux: str = "",
) -> str:
    """A text's cache key: everything its HTML is made from, the aux's digest among it, since the aux is what its references and citations print."""
    said = json.dumps([VERSION, _code(), salt, engine, math, base, sorted(set(envs)), aux, preamble, text])
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
    math: str = "mathjax",
    tex: bool = True,
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
        Anything else the texts' HTML depends on.
    workers : int, optional
        TeX4ht runs at once; default half the machine's cores, at most four.
    timeout : int, default 600
        Seconds for each run.
    math : str, default 'mathjax'
        'svg' draws each display as a picture, for a diagram (`tex4ht.configuration`).
    tex : bool, default True
        False reads the cache and runs nothing: a text not made before fails, and nothing is remembered.

    Returns
    -------
    Snippets
        One `Snippet` per text, in order.
    """
    began = time.monotonic()
    out = Snippets(made=[Snippet(None) for _ in texts])
    said = hashlib.sha256(aux.read_bytes()).hexdigest() if aux is not None and aux.is_file() else ""
    keys = [snippet_key(preamble, base, t, engine=engine, envs=envs, salt=salt, math=math, aux=said) for t in texts]
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
    absent = (
        "TeX is not run here" if not tex else ("make4ht is not installed" if shutil.which("make4ht") is None else "")
    )
    if batch and absent:
        # the machine's, not the text's: nothing is remembered
        for i in batch:
            out.made[i] = Snippet(None, absent)
        batch = []
    lock = threading.Lock()
    remember = True

    def run(ids: list[int]) -> None:
        nonlocal remember
        with lock:
            out.runs += 1
        r = _one_run(root, base, preamble, [(i, texts[i]) for i in ids], cache_dir, envs, engine, aux, timeout, math)
        if r.fatal:
            remember = remember and "timed out" not in r.fatal and not r.fatal.startswith("TeX4ht made no page")
            for i in ids:
                out.made[i] = Snippet(None, r.fatal)
            return
        if not r.page:
            if len(ids) == 1:
                out.made[ids[0]] = Snippet(None, "TeX made no page of it")
                return
            suspects = [i for i in ids if i in r.complained]
            if suspects and len(suspects) < len(ids):
                # TeX stopped on a text it named, a file it could not find: that one apart, the rest again without it
                for i in suspects:
                    run([i])
                run([i for i in ids if i not in r.complained])
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
        # the first text whose output is not whole, and every later one TeX complained about, are suspects: each runs apart, since a run they share breaks again at the next, and the clean rest runs once together
        suspects = [rest[0], *(i for i in rest[1:] if i in r.complained)]
        clean = [i for i in rest if i not in suspects]
        for i in suspects:
            run([i])
        if clean:
            run(clean)

    if batch:
        # a text that would stop the run runs alone from the start: an argument it leaves open (an unclosed `\\footnote{`) reads on to the end of the run, and TeX names no line to set it apart by; an `\\input` of a file the document's directory lacks stops TeX outright, and a run of the rest would stop again at the next
        lone = [i for i in batch if not _balanced(_blank_comments(texts[i])) or _missing_input(root / base, texts[i])]
        shared = [i for i in batch if i not in lone]
        cap = workers or min(4, (os.cpu_count() or 2) // 2)
        n = max(1, min(cap, len(shared) // SHARE or 1))
        parts = [shared[k * len(shared) // n : (k + 1) * len(shared) // n] for k in range(n)] if shared else []
        parts += [[i] for i in lone]
        with ThreadPoolExecutor(max_workers=max(1, min(len(parts), cap)), thread_name_prefix="loom-snippets") as pool:
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
    math: str = "mathjax",
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
        math=math,
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
        if not early and not any(_ERROR.match(ln) for ln in said):
            # TeX said nothing against any text: the tool, not a text, failed, and halving would only fail again
            return _Run(
                {}, None, False, "TeX4ht made no page: " + next((ln for ln in said if ln.strip()), "it said nothing")
            )
        return _Run({}, None, False, early, complained=frozenset(errors))
    html = normalise(page, displays).html
    expected = [str(i) for i, _ in texts] + ["end"]
    marks = _top_marks(html)
    pieces: dict[int, Snippet] = {}
    for p, (i, _text) in enumerate(texts):
        if p + 1 >= len(marks) or marks[p][0] != expected[p] or marks[p + 1][0] != expected[p + 1]:
            if i in errors:
                pieces[i] = Snippet(None, errors[i])
            return _Run(pieces, p, True, complained=frozenset(errors))
        first_line = next(a for j, a, _b in spans if j == i)
        piece = _from_line(html[marks[p][2] : marks[p + 1][1]].strip(), first_line)
        pieces[i] = Snippet(None, errors[i]) if i in errors else Snippet(piece)
    return _Run(pieces, None, True)


def _from_line(html: str, first: int) -> str:
    """`html` with every line in the run's own document counted from `first`, its text's first line, as line 1."""

    def shift(m: re.Match[str]) -> str:
        return f"{m.group(1)}{max(1, int(m.group(2)) - first + 1)}{m.group(3)}"

    return _NODE_LINE.sub(shift, _LINE_AT.sub(shift, html))


_INPUT = re.compile(r"\\(?:input|include)\s*\{([^}]*)\}")


def _missing_input(here: Path, text: str) -> bool:
    """Whether `text` reads with `\\input` or `\\include` a file `here` does not hold, which stops TeX in its tracks."""
    for m in _INPUT.finditer(_blank_comments(text)):
        name = m.group(1).strip()
        if name and not (here / name).is_file() and not (here / f"{name}.tex").is_file():
            return True
    return False


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
