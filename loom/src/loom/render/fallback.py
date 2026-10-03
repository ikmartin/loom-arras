"""Exact rendering of a LaTeX block as SVG through a standalone document (book 9.4.2), the route the site generator's tikz pipeline used.

`latex` twice (tikz-cd forward references) then `dvisvgm --no-fonts --exact-bbox`; results are cached by content hash; ids inside the SVG are namespaced so several fit on one page; width is expressed in em so the viewer scales it with the text. Failures never raise: they return a `figure.fallback` with the error in a `pre`.

A figure met while converting compiles on one pool shared by every render in the process (`defer`), and the outermost conversion substitutes the finished figures for their placeholders (`resolve`), so the figures of one document compile at once rather than one after another; one figure asked for twice at the same moment is compiled once (`compile_svg` holds a lock per cache key).
"""

from __future__ import annotations

import hashlib
import html
import itertools
import os
import re
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

_ID_DEF_RE = re.compile(r"""id=(['"])([^'"]+)\1""")
_SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>", re.S)
_WIDTH_RE = re.compile(r"""\swidth=['"]([\d.]+)(pt|px)['"]""")
_HEIGHT_RE = re.compile(r"""\sheight=['"]([\d.]+)(pt|px)['"]""")
_BASE_PT = 10.0
MINIMAL_PREAMBLE = "\\usepackage{amsmath,amssymb,amsthm,amscd}\n\\usepackage{tikz}\n\\usetikzlibrary{cd}\n"


@dataclass
class SvgResult:
    svg: str | None
    key: str
    cached: bool
    error: str | None = None


def _hash(preamble: str, body: str, border: str) -> str:
    return hashlib.sha1((preamble + "\x00" + border + "\x00" + body).encode("utf-8")).hexdigest()[:16]


_POOL = ThreadPoolExecutor(max_workers=os.cpu_count() or 4, thread_name_prefix="loom-figure")
_PENDING: dict[int, Future[str]] = {}
_PENDING_LOCK = threading.Lock()
_IDS = itertools.count()
_PLACEHOLDER = re.compile(r"<!--loom-figure-(\d+)-->")
_DEPTH = threading.local()
_KEY_LOCKS: dict[str, threading.Lock] = {}
_KEY_LOCKS_LOCK = threading.Lock()


@contextmanager
def converting() -> Iterator[bool]:
    """Mark one conversion on this thread; yields whether it is the outermost, which is the one that `resolve`s.

    `Converter.render_range` wraps itself in this, so a document's nested conversions (its included nodes) leave their figures pending and the document's own conversion waits for all of them at once.
    """
    depth = getattr(_DEPTH, "n", 0)
    _DEPTH.n = depth + 1
    try:
        yield depth == 0
    finally:
        _DEPTH.n = depth


def defer(render: Callable[[], str]) -> str:
    """Start a figure's `render` on the shared pool and return the placeholder `resolve` replaces; outside any conversion, render it here and now."""
    if not getattr(_DEPTH, "n", 0):
        return render()
    n = next(_IDS)
    future = _POOL.submit(render)
    with _PENDING_LOCK:
        _PENDING[n] = future
    return f"<!--loom-figure-{n}-->"


def resolve(markup: str) -> str:
    """`markup` with each placeholder replaced by its figure, waiting for those still compiling."""

    def one(m: re.Match[str]) -> str:
        with _PENDING_LOCK:
            future = _PENDING.pop(int(m.group(1)))
        return future.result()

    return _PLACEHOLDER.sub(one, markup)


def _key_lock(path: Path) -> threading.Lock:
    with _KEY_LOCKS_LOCK:
        return _KEY_LOCKS.setdefault(str(path), threading.Lock())


def _build_doc(preamble: str, body: str, border: str) -> str:
    # a fixed-width minipage puts the body in vertical mode (lists and paragraphs are allowed) and gives displays a finite width; dvisvgm crops to the ink
    return (
        f"\\documentclass[dvisvgm,border={border}]{{standalone}}\n{preamble}\n\\begin{{document}}\n"
        f"\\begin{{minipage}}{{16cm}}\n{body}\n\\end{{minipage}}\n\\end{{document}}\n"
    )


def namespace_ids(svg: str, prefix: str) -> str:
    ids = sorted({m.group(2) for m in _ID_DEF_RE.finditer(svg)}, key=len, reverse=True)
    for old in ids:
        esc = re.escape(old)

        def repl(m: re.Match[str], old: str = old) -> str:
            return f"id={m.group(1)}{prefix}{old}{m.group(1)}"

        svg = re.sub(r"""id=(['"])""" + esc + r"""\1""", repl, svg)
        svg = re.sub(r"#" + esc + r"(?![\w.:-])", f"#{prefix}{old}", svg)
    return svg


def resize_svg(svg: str, base_pt: float = _BASE_PT) -> str:
    m = _SVG_OPEN_RE.search(svg)
    if not m:
        return svg
    tag = m.group(0)
    w = _WIDTH_RE.search(tag)
    if not w:
        return svg
    width_pt = float(w.group(1))
    new_tag = _WIDTH_RE.sub("", tag)
    new_tag = _HEIGHT_RE.sub("", new_tag)
    new_tag = new_tag[:-1] + f" width='{width_pt / base_pt:.4f}em'>"
    return svg[: m.start()] + new_tag + svg[m.end() :]


def _strip_prolog(svg: str) -> str:
    svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)
    svg = re.sub(r"<!--.*?-->\s*", "", svg, flags=re.S)
    return svg.strip()


_RERUN = re.compile(r"Rerun to get|There were undefined references|Label\(s\) may have changed")


def compile_svg(
    body: str,
    preamble: str,
    cache_dir: Path,
    *,
    border: str = "2pt",
    latex_bin: str = "latex",
    dvisvgm_bin: str = "dvisvgm",
    timeout: int = 120,
    texinputs: Path | None = None,
) -> SvgResult:
    key = _hash(preamble, body, border)
    cache_dir.mkdir(parents=True, exist_ok=True)
    # one compile per figure: a second request for it, from another fragment or a preview, waits and then reads the cache
    with _key_lock(cache_dir / key):
        cached = cache_dir / f"{key}.svg"
        if cached.exists():
            return SvgResult(cached.read_text(encoding="utf-8"), key, True)
        failed = cache_dir / f"{key}.failed"
        if failed.exists():
            # a block that could not be compiled is remembered, so a later cold build does not pay for it again; `loom build --force` tries it again
            return SvgResult(None, key, True, failed.read_text(encoding="utf-8"))
        return _compile_svg(body, preamble, cache_dir, key, border, latex_bin, dvisvgm_bin, timeout, texinputs)


def _compile_svg(
    body: str,
    preamble: str,
    cache_dir: Path,
    key: str,
    border: str,
    latex_bin: str,
    dvisvgm_bin: str,
    timeout: int,
    texinputs: Path | None,
) -> SvgResult:
    """Compile one figure that is not in the cache, and write the cache entry: its SVG, or `.failed` with why."""
    cached = cache_dir / f"{key}.svg"
    failed = cache_dir / f"{key}.failed"
    latex = shutil.which(latex_bin)
    dvisvgm = shutil.which(dvisvgm_bin)
    if latex is None or dvisvgm is None:
        return SvgResult(None, key, False, "latex or dvisvgm is not installed")
    env = dict(os.environ)
    if texinputs is not None:
        # the quilt root first, then the distribution's trees (the trailing separator keeps them), so loom.sty and the author's .sty files resolve
        env["TEXINPUTS"] = f"{texinputs}{os.pathsep}{env.get('TEXINPUTS', '')}"
    with tempfile.TemporaryDirectory(prefix="loom-svg-") as tmp:
        d = Path(tmp)
        (d / "d.tex").write_text(_build_doc(preamble, body, border), encoding="utf-8")
        out = ""
        # one pass, and a second only when the log asks for it: a snippet that defines and uses its own label needs two, and nothing else does
        for attempt in range(2):
            try:
                proc = subprocess.run(
                    [latex, "-interaction=nonstopmode", "-halt-on-error", "d.tex"],
                    cwd=d,
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=timeout,
                    check=False,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                return SvgResult(None, key, False, "latex timed out")
            out = proc.stdout or ""
            if attempt == 0 and not _RERUN.search(out):
                break
        if not (d / "d.dvi").exists() or re.search(r"(?m)^! ", out):
            keep = os.environ.get("LOOM_SVG_KEEP")  # debugging: copy the failing document and its log here
            if keep:
                kd = Path(keep) / key
                kd.mkdir(parents=True, exist_ok=True)
                for name in ("d.tex", "d.log"):
                    if (d / name).exists():
                        shutil.copy(d / name, kd / name)
            err = re.search(r"(?m)^! .*$", out)
            detail = ""
            if err:
                after = out[err.end() : err.end() + 300].strip().splitlines()
                detail = " ".join(
                    ln.strip() for ln in after[:2] if ln.strip()
                )  # the `<recently read> \\foo` and `l.N` lines
            message = "latex failed: " + (err.group(0) + (" " + detail if detail else "") if err else out[-500:])
            _atomic_write(failed, message, encoding="utf-8")
            return SvgResult(None, key, False, message)
        try:
            proc = subprocess.run(
                [dvisvgm, "--no-fonts", "--exact-bbox", "--output=d.svg", "d.dvi"],
                cwd=d,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return SvgResult(None, key, False, "dvisvgm timed out")
        if not (d / "d.svg").exists():
            message = "dvisvgm failed: " + (proc.stderr or "")[-500:]
            _atomic_write(failed, message, encoding="utf-8")
            return SvgResult(None, key, False, message)
        svg = _strip_prolog((d / "d.svg").read_text(encoding="utf-8"))
    svg = resize_svg(namespace_ids(svg, f"lm{key}-"))
    _atomic_write(cached, svg, encoding="utf-8")
    return SvgResult(svg, key, False)


def fallback_figure(latex: str, svg: SvgResult, css_class: str, data_src: str) -> str:
    """`figure.fallback` (or `figure.diagram`) holding the inline SVG, or a `pre` with the error when rendering failed."""
    src_text = html.escape(latex, quote=True)
    if svg.svg is None:
        # the source is kept so nothing is lost, and data-error marks it as a fault rather than as the paper's text
        error = html.escape(svg.error or "the block could not be compiled", quote=True)
        return f'<figure class="{css_class} failed" data-src="{data_src}" data-src-text="{src_text}" data-error="{error}"><pre>{html.escape(latex)}</pre></figure>'
    return f'<figure class="{css_class}" data-src="{data_src}" data-src-text="{src_text}">{svg.svg}</figure>'


def _atomic_write(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write a cache entry so no reader sees it half-written: fragments are rendered on a pool, and one thread can find a
    cache file by `exists()` while another is still writing it."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{id(text)}.tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)
