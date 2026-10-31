"""TeX tier: the real toolchain compiles a minimal amsart document in the isolated environment and yields the .aux the scanner reads and the text pdftotext reads back."""

from __future__ import annotations

import shutil
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
    if shutil.which("pdftotext") is None:
        pytest.skip("compiled; no pdftotext on PATH to read the PDF back")
    text = subprocess.run(
        ["pdftotext", "-layout", "out/main.pdf", "-"], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout
    assert "Every widget has a fixed point" in text, text


@pytest.mark.tex
@pytest.mark.skipif(shutil.which("biber") is None, reason="biber is not installed")
def test_loom_compiles_beside_an_editor_s_leftovers_without_reading_or_writing_them(tmp_path: Path) -> None:
    """relloc's case: a document's directory holds the `.bcf`, `.bbl` and `.aux` its author's editor left from an older version, and latexmk run there read the `.bcf`, ran biber in that directory over the author's `.bbl`, and left references undefined. loom compiles a clean copy instead."""
    from loom.reshape.linearize import with_macro_block
    from tests.helpers import ok

    q = tmp_path / "q"
    paper = q / "paper"
    paper.mkdir(parents=True)
    (q / "config.toml").write_text('[quilt]\nname = "q"\nprefix = "qq"\nmain = "paper/main.tex"\n', encoding="utf-8")
    (paper / "refs.bib").write_text(
        "@book{knuth, author={Knuth, Donald}, title={The TeXbook}, year={1984}}\n"
        "@book{lamport, author={Lamport, Leslie}, title={LaTeX: a document preparation system}, year={1994}}\n",
        encoding="utf-8",
    )
    doc = (
        "\\documentclass{article}\n\\usepackage[backend=biber]{biblatex}\n\\addbibresource{refs.bib}\n\\begin{document}\n"
        "\\section{Start}\\label{sec:start}\nSee Section~\\ref{sec:start} and \\cite{CITE}.\n\\printbibliography\n\\end{document}\n"
    )
    # the editor compiled an older version in place, citing another book
    (paper / "main.tex").write_text(with_macro_block(doc.replace("CITE", "lamport"))[0], encoding="utf-8")
    subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "main.tex"], cwd=paper, capture_output=True, check=False
    )
    (paper / "main.tex").write_text(with_macro_block(doc.replace("CITE", "knuth"))[0], encoding="utf-8")
    leftovers = {p.name: p.read_bytes() for p in paper.iterdir() if p.suffix in (".bcf", ".bbl", ".aux", ".toc")}
    assert ".bcf" in {Path(n).suffix for n in leftovers}, sorted(leftovers)

    ok("compile", "paper/main.tex", cwd=q)
    log = (q / "build" / "paper" / "main" / "main.log").read_text(encoding="utf-8", errors="replace")
    assert "undefined" not in log, [ln for ln in log.splitlines() if "undefined" in ln][:5]
    assert {name: (paper / name).read_bytes() for name in leftovers} == leftovers  # neither read over nor written
    text = subprocess.run(
        ["pdftotext", str(q / "build/paper/main/main.pdf"), "-"], capture_output=True, text=True
    ).stdout
    assert "TeXbook" in text and "preparation system" not in text
