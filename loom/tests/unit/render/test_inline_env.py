"""Environments written inline in a master render as HTML, and a fallback that cannot compile is remembered rather than retried (book 9.4.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import ok

MASTER = r"""\documentclass{amsart}
\usepackage{amsthm}
\usepackage{loom}
\newtheorem{theorem}{Theorem}[section]
\theoremstyle{definition}
\newtheorem{definition}[theorem]{Definition}
\begin{document}
\section{Setup}\label{pp-0001}
\begin{definition}[Widget]\label{pp-0002}
A widget is a pair $(X,\sigma)$.
\end{definition}
\begin{theorem}[Parity]\label{pp-0003}
Every widget has a fixed point.
\end{theorem}
\begin{proof}
By the orbit decomposition.
\end{proof}
\end{document}
"""


def quilt(tmp_path: Path) -> Path:
    q = tmp_path / "q"
    ok("init", str(q), "--prefix", "pp", "--yes", cwd=tmp_path)
    (q / "drafting" / "main.tex").write_text(MASTER, encoding="utf-8")
    return q


def test_inline_environment_renders_as_html_not_a_picture(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("build", cwd=q)
    master = (q / "build" / "fragments" / "masters" / "main.html").read_text(encoding="utf-8")
    assert "figure" not in master and "<pre>" not in master  # never an SVG picture of a theorem, never verbatim LaTeX
    assert '<div class="env env-definition"' in master and 'data-style="definition"' in master
    assert '<div class="env env-theorem"' in master and 'data-style="plain"' in master
    assert '<p class="env-label"><span class="taxon">Theorem</span>' in master
    assert '<span class="title">(Parity)</span>' in master
    assert "A widget is a pair" in master and "orbit decomposition" in master
    assert '<details class="env env-proof"' in master and '<summary class="env-label">Proof</summary>' in master


def test_failed_fallback_is_cached_and_not_recompiled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    q = quilt(tmp_path)
    node = q / "drafting" / "main.tex"
    node.write_text(
        MASTER.replace("\\section{Setup}", "\\section{Setup}\n\\begin{oddity}\nx\n\\end{oddity}"), encoding="utf-8"
    )
    log = tmp_path / "tex.log"
    monkeypatch.setenv("FAKE_TEX_LOG", str(log))
    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    ok("build", cwd=q)
    first = log.read_text(encoding="utf-8").count("\n") if log.exists() else 0
    assert first, "the unknown environment should have reached the fallback"
    assert list((q / "build" / "cache" / "svg").glob("*.failed")), "the failure is remembered"
    log.write_text("", encoding="utf-8")
    (q / "build" / "cache" / "fragments.json").unlink(missing_ok=True)
    ok("build", cwd=q)
    assert log.read_text(encoding="utf-8").strip() == "", "a remembered failure costs no further latex runs"
    # the failure may have been the machine's: --force tries once more, and works once the TeX installation does
    monkeypatch.delenv("FAKE_TEX_FAIL")
    ok("build", "--force", cwd=q)
    assert log.read_text(encoding="utf-8").strip(), "--force compiles a remembered failure again"
    assert not list((q / "build" / "cache" / "svg").glob("*.failed"))
