"""Environments written inline in a master render as HTML, and a fallback that cannot compile is remembered rather than retried (book 9.4.2)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main

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


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def quilt(tmp_path: Path) -> Path:
    q = tmp_path / "q"
    assert run("init", str(q), "--prefix", "pp", "--no-git", "--yes", cwd=tmp_path).exit_code == 0
    (q / "drafts" / "main.tex").write_text(MASTER, encoding="utf-8")
    return q


def test_inline_environment_renders_as_html_not_a_picture(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    assert run("build", cwd=q).exit_code in (0, 1)
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
    node = q / "drafts" / "main.tex"
    node.write_text(
        MASTER.replace("\\section{Setup}", "\\section{Setup}\n\\begin{oddity}\nx\n\\end{oddity}"), encoding="utf-8"
    )
    log = tmp_path / "tex.log"
    monkeypatch.setenv("FAKE_TEX_LOG", str(log))
    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    assert run("build", cwd=q).exit_code in (0, 1)
    first = log.read_text(encoding="utf-8").count("\n") if log.exists() else 0
    assert first, "the unknown environment should have reached the fallback"
    assert list((q / "build" / "cache" / "svg").glob("*.failed")), "the failure is remembered"
    log.write_text("", encoding="utf-8")
    import shutil

    shutil.rmtree(q / "build" / "cache" / "fragments.json", ignore_errors=True)
    (q / "build" / "cache" / "fragments.json").unlink(missing_ok=True)
    assert run("build", cwd=q).exit_code in (0, 1)
    assert log.read_text(encoding="utf-8").strip() == "", "a remembered failure costs no further latex runs"
