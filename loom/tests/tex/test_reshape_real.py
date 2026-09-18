"""TeX tier: import, atomize, and inline keep the compiled text identical under the real toolchain, and the identity test reports what changed when it fails (book 6.6)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.tex.identity import identity_test

PAPER = r"""\documentclass{amsart}
\usepackage{amsthm}
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\theoremstyle{definition}
\newtheorem{definition}[theorem]{Definition}
\begin{document}
\section{Setup}
\begin{definition}[Widget]\label{def:widget}
A widget is a pair.
\end{definition}
\input{sections/results}
\end{document}
"""
RESULTS = r"""\section{Results}\label{sec:results}
\begin{lemma}\label{lem:a}
Alpha, see Definition~\ref{def:widget}.
\end{lemma}
\begin{proof}
Obvious.
\end{proof}

Prose between.

\begin{theorem}[Main]\label{thm:main}
Beta uses Lemma~\ref{lem:a}.
\end{theorem}
\begin{proof}[Proof of Theorem~\ref{thm:main}]
Later.
\end{proof}
"""


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def paper(tmp_path: Path) -> Path:
    p = tmp_path / "paper"
    (p / "sections").mkdir(parents=True)
    (p / "main.tex").write_text(PAPER)
    (p / "sections" / "results.tex").write_text(RESULTS)
    return p


def imported(tmp_path: Path) -> Path:
    """init --from: one flat canon document that typesets as the original."""
    p = paper(tmp_path)
    r = run("init", str(tmp_path / "q"), "--from", str(p / "main.tex"), "--prefix", "pp", "--yes", cwd=tmp_path)
    assert r.exit_code == 0, r.output
    assert "Identity test: pass" in r.output
    return tmp_path / "q"


def drafted(tmp_path: Path) -> Path:
    q = imported(tmp_path)
    r = run("draft", "canon/main.tex", "--yes", cwd=q)
    assert r.exit_code == 0, r.output
    assert "Identity test: pass" in r.output
    return q


@pytest.mark.tex
def test_import_is_flat_and_draft_labels_it(tmp_path: Path) -> None:
    q = imported(tmp_path)
    canon = (q / "canon" / "main.tex").read_text()
    assert "\\input{sections/results}" not in canon and "Beta uses Lemma" in canon
    assert "\\label{pp-" not in canon and not (q / "sections").exists()
    r = run("draft", "canon/main.tex", "--yes", cwd=q)
    assert r.exit_code == 0 and "Identity test: pass" in r.output, r.output
    assert (q / "drafting" / "main.tex").read_text().count("\\label{pp-") == 5


@pytest.mark.tex
def test_atomize_identity_and_inline_identity(tmp_path: Path) -> None:
    q = drafted(tmp_path)
    r = run("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q)
    assert r.exit_code == 0 and "Identity test: pass" in r.output, r.output
    assert {f.name for f in (q / "nodes").glob("*.tex")} == {
        "pp-0002.tex",
        "pp-0004.tex",
        "pp-0005.tex",
        "pp-0005.proof.tex",
    }
    r2 = run("inline", "drafting/spine.tex", "drafting/flat.tex", "--all", cwd=q)
    assert r2.exit_code == 0 and "Identity test: pass" in r2.output, r2.output
    flat = (q / "drafting" / "flat.tex").read_text()
    assert "\\input{nodes/" not in flat and flat.count("\\begin{proof}") == 2


@pytest.mark.tex
def test_canonize_writes_a_landmark_that_compiles_alone(tmp_path: Path) -> None:
    """A canon document carries loom.sty's macros inline, so it compiles in a directory holding nothing else."""
    import shutil
    import subprocess

    q = drafted(tmp_path)
    assert run("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q).exit_code == 0
    r = run("canonize", "drafting/spine.tex", "--to", "canon/main-v1.tex", "-m", "First landmark", cwd=q)
    assert r.exit_code == 0 and "Identity test: pass" in r.output, r.output
    alone = tmp_path / "alone"
    alone.mkdir()
    shutil.copy(q / "canon" / "main-v1.tex", alone / "main-v1.tex")
    proc = subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main-v1.tex"],
        cwd=alone,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout[-3000:]
    assert (alone / "main-v1.pdf").is_file()


@pytest.mark.tex
def test_inline_nest_shifts(tmp_path: Path) -> None:
    q = drafted(tmp_path)
    (q / "sections").mkdir(exist_ok=True)
    (q / "sections" / "nested.tex").write_text("\\section{Nested}\\label{pp-0100}\nNested text.\n")
    m = q / "drafting" / "main.tex"
    m.write_text(m.read_text().replace("\\end{document}", "\\nest{sections/nested}\n\\end{document}"))
    r = run("inline", "drafting/main.tex", "drafting/flat.tex", "--all", cwd=q)
    assert r.exit_code == 0, r.output
    flat = (q / "drafting" / "flat.tex").read_text()
    assert "\\subsection{Nested}\\label{pp-0100}" in flat and "\\nest{" not in flat
    assert "Identity test: pass" in r.output  # loom.sty shifted the heading in the original exactly as inline did


@pytest.mark.tex
def test_identity_reports_first_diff_and_label_numbers(tmp_path: Path) -> None:
    p = paper(tmp_path)
    changed = tmp_path / "changed"
    shutil.copytree(p, changed)
    (changed / "sections" / "results.tex").write_text(RESULTS.replace("Prose between.", "Prose changed."))
    res = identity_test(p, "main.tex", changed, "main.tex", tmp_path / "scratch1")
    assert not res.passed and res.first_difference is not None
    assert "Prose between" in res.first_difference[0] and "Prose changed" in res.first_difference[1]
    assert "Identity test: FAIL" in res.summary() and "before:" in res.summary()
    renumbered = tmp_path / "renumbered"
    shutil.copytree(p, renumbered)
    (renumbered / "main.tex").write_text(PAPER.replace("\\section{Setup}", "\\section{Extra}\n\\section{Setup}"))
    res2 = identity_test(p, "main.tex", renumbered, "main.tex", tmp_path / "scratch2")
    assert not res2.passed and res2.changed_numbers.get("lem:a") == ("2.1", "3.1")
    assert "lem:a: 2.1 -> 3.1" in res2.summary()
