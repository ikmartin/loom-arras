"""TeX tier: the real toolchain compiles a minimal amsart document in the isolated environment and yields the .aux and text the scanner will read."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

MINIMAL = r"""
\documentclass{amsart}
\usepackage{amsthm}
\newtheorem{lemma}{Lemma}[section]
\begin{document}
\section{Setup}\label{sec:setup}
\begin{lemma}[Fixed point]\label{lem:fixed}
Every widget has a fixed point.
\end{lemma}
\begin{proof}
Take the orbit decomposition.
\end{proof}
\end{document}
"""


@pytest.mark.tex
def test_real_latexmk_compiles_minimal_document(tmp_path: Path) -> None:
    (tmp_path / "main.tex").write_text(MINIMAL, encoding="utf-8")
    proc = subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-outdir=out", "main.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    aux = (tmp_path / "out" / "main.aux").read_text(encoding="utf-8")
    assert "\\newlabel{lem:fixed}{{1.1}{1}" in aux
    assert "\\newlabel{sec:setup}{{1}{1}" in aux
    assert (tmp_path / "out" / "main.pdf").stat().st_size > 1000


@pytest.mark.tex
def test_real_pdftotext_extracts_text(tmp_path: Path) -> None:
    pytest.importorskip("shutil")
    import shutil

    if shutil.which("pdftotext") is None:
        pytest.skip("pdftotext not installed")
    (tmp_path / "main.tex").write_text(MINIMAL, encoding="utf-8")
    subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "-outdir=out", "main.tex"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    text = subprocess.run(
        ["pdftotext", "-layout", "out/main.pdf", "-"], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout
    assert "Every widget has a fixed point" in text
