"""The shim behaves like a toolchain: aux numbering, placeholder PDF, pdftotext round trip, invocation log, failure injection."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

MAIN = r"""
\documentclass{amsart}
\usepackage{amsthm}
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\begin{document}
\section{Setup}\label{sec:setup}
\begin{lemma}\label{lem:a}
Alpha.
\end{lemma}
\input{part}
\end{document}
"""
PART = r"""
\section{Results}\label{sec:results}
\begin{theorem}\label{thm:b}
Beta \ref{lem:a}.
\end{theorem}
\begin{equation}\label{eq:c} x = y \end{equation}
"""


def _write(tmp_path: Path) -> None:
    (tmp_path / "main.tex").write_text(MAIN, encoding="utf-8")
    (tmp_path / "part.tex").write_text(PART, encoding="utf-8")


def test_fake_latex_emits_aux(tmp_path: Path) -> None:
    _write(tmp_path)
    proc = subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "-outdir=out", "main.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    aux = (tmp_path / "out" / "main.aux").read_text(encoding="utf-8")
    assert "\\newlabel{sec:setup}{{1}{1}}" in aux
    assert "\\newlabel{lem:a}{{1.1}{1}}" in aux
    assert "\\newlabel{sec:results}{{2}{1}}" in aux
    assert "\\newlabel{thm:b}{{2.1}{1}}" in aux
    assert "\\newlabel{eq:c}{{2.1}{1}}" in aux
    assert (tmp_path / "out" / "main.pdf").exists()
    log = Path(os.environ["FAKE_TEX_LOG"]).read_text(encoding="utf-8")
    assert log.startswith("latexmk -pdf")


def test_fake_pdftotext_round_trip(tmp_path: Path) -> None:
    _write(tmp_path)
    subprocess.run(["pdflatex", "-output-directory=out", "main.tex"], cwd=tmp_path, check=True, capture_output=True)
    proc = subprocess.run(["pdftotext", "-layout", "out/main.pdf", "-"], cwd=tmp_path, capture_output=True, text=True)
    assert "Alpha." in proc.stdout and "Beta" in proc.stdout
    assert "\\input" not in proc.stdout and "\\begin" not in proc.stdout
    info = subprocess.run(["pdfinfo", "out/main.pdf"], cwd=tmp_path, capture_output=True, text=True)
    assert info.stdout.startswith("Pages:")


def test_fake_latex_failure_injection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path)
    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    proc = subprocess.run(["latexmk", "-pdf", "-outdir=out", "main.tex"], cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 12
    assert "! LaTeX Error" in (tmp_path / "out" / "main.log").read_text(encoding="utf-8")


def test_fake_dvisvgm_and_kpsewhich(tmp_path: Path) -> None:
    subprocess.run(["dvisvgm", "--no-fonts", "--exact-bbox", "--output=d.svg", "d.dvi"], cwd=tmp_path, check=True)
    assert (tmp_path / "d.svg").read_text(encoding="utf-8").startswith("<?xml")
    found = subprocess.run(["kpsewhich", "xy.tex"], cwd=tmp_path, capture_output=True, text=True)
    assert found.returncode == 0 and found.stdout.strip().endswith("xy.tex")
    missing = subprocess.run(["kpsewhich", "nonexistent-thing.tex"], cwd=tmp_path, capture_output=True, text=True)
    assert missing.returncode == 1
