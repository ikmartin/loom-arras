"""TeX tier: import, atomize, and inline keep the compiled text identical under the real toolchain, and the identity test reports what changed when it fails (book 6.6)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from loom.tex.identity import identity_test
from tests.helpers import Once, copy, ok

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


def paper(tmp_path: Path) -> Path:
    p = tmp_path / "paper"
    (p / "sections").mkdir(parents=True)
    (p / "main.tex").write_text(PAPER)
    (p / "sections" / "results.tex").write_text(RESULTS)
    return p


@pytest.fixture(scope="module")
def once(tmp_path_factory: pytest.TempPathFactory) -> Once:
    return Once(tmp_path_factory)


def imported(once: Once) -> tuple[Path, str]:
    """init --from, made once: one flat canon document that typesets as the original. Read only; the quilt and what init said."""

    def make(base: Path) -> tuple[Path, str]:
        p = paper(base)
        r = ok("init", str(base / "q"), "--from", str(p / "main.tex"), "--prefix", "pp", "--yes", cwd=base)
        assert "Identity test: pass" in r.output, r.output
        return base / "q", r.output

    return once.get("imported", make)


def drafted(once: Once) -> tuple[Path, str]:
    """The imported quilt drafted, made once. Read only; the quilt and what draft said."""

    def make(base: Path) -> tuple[Path, str]:
        q = copy(imported(once)[0], base / "q")
        r = ok("draft", "canon/main.tex", "--yes", cwd=q)
        assert "Identity test: pass" in r.output, r.output
        return q, r.output

    return once.get("drafted", make)


def atomized(once: Once) -> tuple[Path, str]:
    """The drafted quilt atomized into drafting/spine.tex, made once. Read only; the quilt and what atomize said."""

    def make(base: Path) -> tuple[Path, str]:
        q = copy(drafted(once)[0], base / "q")
        r = ok("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q)
        return q, r.output

    return once.get("atomized", make)


@pytest.mark.tex
def test_import_is_flat_and_draft_labels_it(once: Once) -> None:
    q, _ = imported(once)
    canon = (q / "canon" / "main.tex").read_text()
    assert "\\input{sections/results}" not in canon and "Beta uses Lemma" in canon
    assert "\\label{pp-" not in canon and not (q / "sections").exists()
    q, said = drafted(once)
    assert "Identity test: pass" in said, said
    assert (q / "drafting" / "main.tex").read_text().count("\\label{pp-") == 5


@pytest.mark.tex
def test_atomize_identity_and_inline_identity(once: Once, tmp_path: Path) -> None:
    atomic, said = atomized(once)
    assert "Identity test: pass" in said, said
    assert {f.name for f in (atomic / "nodes").glob("*.tex")} == {
        "pp-0002.tex",
        "pp-0004.tex",
        "pp-0005.tex",
        "pp-0005.proof.tex",
    }
    q = copy(atomic, tmp_path / "q")
    r2 = ok("inline", "drafting/spine.tex", "drafting/flat.tex", "--all", cwd=q)
    assert "Identity test: pass" in r2.output, r2.output
    flat = (q / "drafting" / "flat.tex").read_text()
    assert "\\input{nodes/" not in flat and flat.count("\\begin{proof}") == 2


@pytest.mark.tex
def test_canonize_writes_a_landmark_that_compiles_alone(once: Once, tmp_path: Path) -> None:
    """A canon document carries loom.sty's macros inline, so it compiles in a directory holding nothing else."""
    q = copy(atomized(once)[0], tmp_path / "q")
    r = ok("canonize", "drafting/spine.tex", "--to", "canon/main-v1.tex", "-m", "First landmark", cwd=q)
    assert "Identity test: pass" in r.output, r.output
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
def test_inline_nest_shifts(once: Once, tmp_path: Path) -> None:
    q = copy(drafted(once)[0], tmp_path / "q")
    (q / "sections").mkdir(exist_ok=True)
    (q / "sections" / "nested.tex").write_text("\\section{Nested}\\label{pp-0100}\nNested text.\n")
    m = q / "drafting" / "main.tex"
    m.write_text(m.read_text().replace("\\end{document}", "\\nest{sections/nested}\n\\end{document}"))
    r = ok("inline", "drafting/main.tex", "drafting/flat.tex", "--all", cwd=q)
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


BIBLATEX_PAPER = r"""\documentclass{article}
\usepackage[backend=biber]{biblatex}
\addbibresource{refs.bib}
\begin{document}
See \cite{x}.
\printbibliography
\end{document}
"""


@pytest.mark.tex
def test_import_neither_reads_nor_writes_the_authors_build_files(tmp_path: Path) -> None:
    """latexmk under -outdir still reads and rewrites the .bbl its working directory holds, so an editor's leftovers decided the import check and were rewritten in the author's directory."""
    if shutil.which("biber") is None:
        pytest.skip("TeX tier: no biber on PATH")
    p = tmp_path / "paper"
    p.mkdir()
    (p / "main.tex").write_text(BIBLATEX_PAPER)
    (p / "refs.bib").write_text("@misc{x, title={X}, author={A. Author}, year={2000}}\n")
    subprocess.run(["latexmk", "-dvi", "-interaction=nonstopmode", "main.tex"], cwd=p, capture_output=True, check=False)
    (p / "main.bbl").write_text("")  # what a failed bibliography run leaves behind
    before = {f.name: f.read_bytes() for f in p.iterdir()}
    assert "main.fdb_latexmk" in before

    ok("init", str(tmp_path / "q"), "--from", str(p / "main.tex"), "--prefix", "pp", "--yes", cwd=tmp_path)
    assert {f.name: f.read_bytes() for f in p.iterdir()} == before
