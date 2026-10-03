"""Figures the converter cannot draw compile once each, on one shared pool, and the review previews share them with the fragments (plan 0.18.2, book 9.3)."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from loom.render import fallback
from loom.render.fallback import SvgResult
from tests.helpers import ok

PREAMBLE = r"""\documentclass{amsart}
\usepackage{amsthm}
\usepackage{tikz-cd}
\usepackage{loom}
\newtheorem{lemma}{Lemma}
"""


def diagram(n: int) -> str:
    return f"\\begin{{tikzcd}} A_{n} \\arrow[r] & B_{n} \\end{{tikzcd}}"


def quilt(tmp_path: Path, body: str, nodes: dict[str, str] | None = None) -> Path:
    q = tmp_path / "q"
    ok("init", str(q), "--prefix", "pp", "--yes", cwd=tmp_path)
    (q / "drafting" / "main.tex").write_text(
        PREAMBLE + "\\begin{document}\n" + body + "\n\\end{document}\n", encoding="utf-8"
    )
    for name, text in (nodes or {}).items():
        (q / "nodes" / name).write_text(text, encoding="utf-8")
    return q


def latex_runs(log: Path) -> int:
    return (
        sum(1 for line in log.read_text(encoding="utf-8").splitlines() if line.startswith("latex ") and "d.tex" in line)
        if log.exists()
        else 0
    )


def test_each_figure_compiles_once_though_a_node_its_document_and_its_review_preview_all_show_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A node's diagram is drawn in the node's page, in the document that includes it, and in the review preview of the unaccepted node: one figure, one compile, and the preview compiled against the document's own preamble rather than a copy of every file it loads."""
    q = quilt(
        tmp_path,
        "\\section{One}\n\\input{nodes/pp-0001}\n\\input{nodes/pp-0002}",
        {
            "pp-0001.tex": f"\\begin{{lemma}}\\label{{pp-0001}}\nA square: {diagram(1)}\n\\end{{lemma}}\n",
            "pp-0002.tex": f"\\begin{{lemma}}\\label{{pp-0002}}\nTwo more: {diagram(2)} and {diagram(3)}\n\\end{{lemma}}\n",
        },
    )
    log = tmp_path / "tex.log"
    monkeypatch.setenv("FAKE_TEX_LOG", str(log))
    ok("build", cwd=q)
    assert latex_runs(log) == 3, log.read_text(encoding="utf-8")
    manifest = (q / "build" / "manifest.json").read_text(encoding="utf-8")
    assert "review_fragment" in manifest  # the previews were drawn, from the cache
    preview = next((q / "build" / "fragments" / "review").glob("*-block.html")).read_text(encoding="utf-8")
    assert 'class="diagram"' in preview and "failed" not in preview


def test_the_figures_of_one_document_compile_at_the_same_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A whole paper is one fragment, and its figures compiled one after another: a cold build of the author's quilt spent most of fifteen minutes so."""
    q = quilt(tmp_path, "Some prose.\n\n" + "\n\n".join(f"Figure {n}: {diagram(n)}" for n in range(4)))
    running = 0
    most = 0
    lock = threading.Lock()

    def slow(body: str, preamble: str, cache_dir: Path, key: str, *_args: object) -> SvgResult:
        nonlocal running, most
        with lock:
            running += 1
            most = max(most, running)
        time.sleep(0.3)
        with lock:
            running -= 1
        return SvgResult("<svg/>", key, False)

    monkeypatch.setattr(fallback, "_compile_svg", slow)
    started = time.perf_counter()
    ok("build", cwd=q)
    assert most >= 4, most
    assert time.perf_counter() - started < 4 * 0.3 + 1.0
    master = (q / "build" / "fragments" / "masters" / "main.html").read_text(encoding="utf-8")
    assert master.count("<svg/>") == 4 and "loom-figure" not in master


def test_a_figure_outside_any_conversion_is_drawn_at_once() -> None:
    """A placeholder is only ever left where a conversion will substitute it."""
    assert fallback.defer(lambda: "<figure/>") == "<figure/>"
    with fallback.converting() as outermost:
        assert outermost
        held = fallback.defer(lambda: "<figure/>")
        assert held.startswith("<!--loom-figure-")
        assert fallback.resolve("a" + held + "b") == "a<figure/>b"


def test_an_xy_diagram_is_compiled_with_xy_though_the_preamble_does_not_load_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cited paper's `\\xymatrix` in a quilt that draws with tikz-cd failed every attempt for want of the package: 290 of the 1,110 failed compiles of the author's cold build."""
    from loom.render import fragments

    q = quilt(tmp_path, "Prose.\n\n$$\\xymatrix{A \\ar[r] & B}$$\n")
    preambles: list[str] = []
    real = fragments.compile_svg

    def seen(latex: str, preamble: str, *args: object, **kwargs: object) -> SvgResult:
        preambles.append(preamble)
        return real(latex, preamble, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(fragments, "compile_svg", seen)
    ok("build", cwd=q)
    assert preambles and all("\\usepackage[all]{xy}" in p for p in preambles), preambles
