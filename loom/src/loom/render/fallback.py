"""Exact rendering of a LaTeX block as SVG through a standalone document (book 9.4.2), the route the site generator's tikz pipeline used.

`latex` twice (tikz-cd forward references) then `dvisvgm --no-fonts --exact-bbox`; results are cached by content hash; ids inside the SVG are namespaced so several fit on one page; width is expressed in em so the viewer scales it with the text. Failures never raise: they return a `figure.fallback` with the error in a `pre`.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

_ID_DEF_RE = re.compile(r"""id=(['"])([^'"]+)\1""")
_SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>", re.S)
_WIDTH_RE = re.compile(r"""\swidth=['"]([\d.]+)(pt|px)['"]""")
_HEIGHT_RE = re.compile(r"""\sheight=['"]([\d.]+)(pt|px)['"]""")
_BASE_PT = 10.0
MINIMAL_PREAMBLE = "\\usepackage{amsmath,amssymb,amsthm}\n\\usepackage{tikz}\n\\usetikzlibrary{cd}\n"


@dataclass
class SvgResult:
    svg: str | None
    key: str
    cached: bool
    error: str | None = None


def _hash(preamble: str, body: str, border: str) -> str:
    return hashlib.sha1((preamble + "\x00" + border + "\x00" + body).encode("utf-8")).hexdigest()[:16]


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
    cached = cache_dir / f"{key}.svg"
    if cached.exists():
        return SvgResult(cached.read_text(encoding="utf-8"), key, True)
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
        for _ in range(2):
            try:
                proc = subprocess.run(
                    [latex, "-interaction=nonstopmode", "d.tex"],
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
            return SvgResult(
                None,
                key,
                False,
                "latex failed: " + (err.group(0) + (" " + detail if detail else "") if err else out[-500:]),
            )
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
            return SvgResult(None, key, False, "dvisvgm failed: " + (proc.stderr or "")[-500:])
        svg = _strip_prolog((d / "d.svg").read_text(encoding="utf-8"))
    svg = resize_svg(namespace_ids(svg, f"lm{key}-"))
    cached.write_text(svg, encoding="utf-8")
    return SvgResult(svg, key, False)


def fallback_figure(latex: str, svg: SvgResult, css_class: str, data_src: str) -> str:
    """`figure.fallback` (or `figure.diagram`) holding the inline SVG, or a `pre` with the error when rendering failed."""
    src_text = html.escape(latex, quote=True)
    if svg.svg is None:
        return f'<figure class="{css_class} failed" data-src="{data_src}" data-src-text="{src_text}"><pre>{html.escape(latex)}</pre></figure>'
    return f'<figure class="{css_class}" data-src="{data_src}" data-src-text="{src_text}">{svg.svg}</figure>'
