"""TeX tier: what a compile runs, what it keeps, and how it ends (plan 0.29.1): latexmk reads no rc file, a failed run leaves the last good PDF and aux, and a run that never ends is killed whole."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from loom.tex.runner import compile_document

GOOD = "\\documentclass{article}\\begin{document}\\section{One}\\label{s}Hello, see~\\ref{s}.%s\\end{document}\n"


def _doc(q: Path, body: str = "") -> Path:
    q.mkdir(parents=True, exist_ok=True)
    (q / "main.tex").write_text(GOOD % body, encoding="utf-8")
    return q


@pytest.mark.tex
def test_neither_a_quilt_s_latexmkrc_nor_a_write18_runs_with_shell_escape_in_the_home_rc(
    tmp_path: Path, isolated_env: Path
) -> None:
    """A `latexmkrc` is a Perl program, and a home one that adds `-shell-escape` lets any document's `\\write18` run a command: loom's compile reads neither."""
    marker = tmp_path / "ran"
    (isolated_env / ".latexmkrc").write_text("$pdflatex = 'pdflatex -shell-escape %O %S';\n", encoding="utf-8")
    q = _doc(tmp_path / "q", f"\\immediate\\write18{{touch {marker}-tex}}")
    (q / "latexmkrc").write_text(f'system("touch {marker}-rc");\n', encoding="utf-8")
    (q / ".latexmkrc").write_text(f'system("touch {marker}-dotrc");\n', encoding="utf-8")
    res = compile_document(q, "", "main.tex", q / ".loom/build/main")
    assert res.pdf is not None, res.first_error
    assert not list(tmp_path.glob("ran*"))


@pytest.mark.tex
def test_a_failed_run_leaves_the_last_good_pdf_and_aux_and_reports_its_own_log(tmp_path: Path) -> None:
    q = _doc(tmp_path / "q")
    out = q / ".loom/build/main"
    good = compile_document(q, "", "main.tex", out)
    assert good.pdf is not None and good.ok, good.first_error
    pdf, aux = good.pdf.read_bytes(), (out / "main.aux").read_text()
    (q / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}\\section{Two}\\label{s}\\input{missing}\\end{document}\n"
    )
    bad = compile_document(q, "", "main.tex", out)
    assert not bad.ok and bad.pdf is None and bad.aux is None
    assert (out / "main.pdf").read_bytes() == pdf and (out / "main.aux").read_text() == aux
    assert bad.log is not None and "missing" in bad.log.read_text(errors="replace")
    assert not [p for p in out.parent.iterdir() if p.name.startswith(".main.run-")]


@pytest.mark.tex
def test_a_recoverable_error_still_makes_a_pdf_when_the_run_carries_on(tmp_path: Path) -> None:
    q = _doc(tmp_path / "q", "\\hlind{x}")
    res = compile_document(q, "", "main.tex", q / ".loom/build/main", halt_on_error=False)
    assert res.pdf is not None and res.errors and res.errors[0].startswith("! Undefined control sequence")
    halted = compile_document(q, "", "main.tex", tmp_path / "halted")
    assert halted.pdf is None


@pytest.mark.tex
def test_a_run_that_never_ends_is_killed_with_everything_it_started(tmp_path: Path) -> None:
    q = _doc(tmp_path / "q", "\\def\\x{\\x}\\x")
    held = []
    res = compile_document(q, "", "main.tex", q / ".loom/build/main", timeout=3, started=held.append)
    assert res.returncode == 124 and "timed out" in res.first_error
    with pytest.raises(ProcessLookupError):
        os.killpg(held[0].pid, 0)
