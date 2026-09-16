"""Chapter 6 on the shim: id, import (with the closure, the diff, anchoring, in-place), init --from, atomize, inline, and the identity test."""

from __future__ import annotations

import os
from pathlib import Path

from click.testing import CliRunner

from loom.cli import main
from loom.reshape.anchoring import anchoring_violations, fix_anchoring
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

PAPER = r"""\documentclass{amsart}
\usepackage{amsthm}
\input{preamble}
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
\includegraphics{figures/fig.pdf}
\bibliography{refs}
\end{document}
"""
RESULTS = r"""\section{Results}\label{sec:results}
\begin{lemma}\label{lem:a}
Alpha, see Definition~\ref{def:widget}.
\end{lemma}
\begin{proof}
Obvious.
\end{proof}

Prose between, compare~\ref{thm:missing}.

\begin{theorem}[Main]\label{thm:main}
Beta uses Lemma~\ref{lem:a}.
\end{theorem}
\begin{proof}[Proof of Theorem~\ref{thm:main}]
Later.
\end{proof}
"""


def run(*args: str, cwd: Path, stdin: str | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), input=stdin)
    finally:
        os.chdir(old)


def paper_dir(tmp_path: Path, results: str = RESULTS) -> Path:
    p = tmp_path / "paper"
    (p / "sections").mkdir(parents=True)
    (p / "figures").mkdir()
    (p / "main.tex").write_text(PAPER)
    (p / "preamble.tex").write_text("\\usepackage{amsmath}\n")
    (p / "sections" / "results.tex").write_text(results)
    (p / "figures" / "fig.pdf").write_bytes(b"%PDF-1.4\n%fake\n")
    (p / "refs.bib").write_text("@misc{x, title={X}}\n")
    (tmp_path / "elsewhere.tex").write_text("outside\n")
    return p


def test_import_closure_layout_labels_main_and_identity(tmp_path: Path) -> None:
    p = paper_dir(tmp_path)
    r = run("init", str(tmp_path / "q"), "--from", str(p / "main.tex"), "--prefix", "pp", "--yes", cwd=tmp_path)
    assert r.exit_code == 0, r.output
    q = tmp_path / "q"
    for rel in (
        "drafts/main.tex",
        "preamble.tex",
        "sections/results.tex",
        "figures/fig.pdf",
        "refs.bib",
        "loom.sty",
        "config.toml",
    ):
        assert (q / rel).exists(), rel
    assert 'main = "drafts/main.tex"' in (q / "config.toml").read_text()
    master = (q / "drafts" / "main.tex").read_text()
    assert master.splitlines()[1] == "\\usepackage{loom}"
    assert "\\section{Setup}\\label{pp-0001}" in master  # ids follow document order: the section comes first
    assert "\\begin{definition}[Widget]\\label{pp-0002}\\label{def:widget}" in master
    results = (q / "sections" / "results.tex").read_text()
    assert (
        "\\begin{theorem}[Main]\\label{pp-" in results
        and "\\begin{lemma}\\label{pp-" in results
        and "\\label{lem:a}" in results
    )
    assert "\\section{Results}\\label{pp-" in results  # the id is the first label, ahead of the author's
    assert "Identity test: pass" in r.output
    assert "Nodes:" in r.output and "Proofs:" in r.output
    assert (p / "main.tex").read_text() == PAPER  # the original is untouched
    assert "loom.sty" not in (p / "main.tex").read_text()
    lint = run("lint", cwd=q)
    assert "dangling-link" in lint.output  # thm:missing was never defined in the paper


def test_import_shows_diff_and_asks(tmp_path: Path) -> None:
    p = paper_dir(tmp_path)
    assert run("init", str(tmp_path / "q"), "--prefix", "pp", "--yes", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    r = run("import", str(p / "main.tex"), cwd=q)
    assert r.exit_code == 2 and "needs confirmation" in r.output
    assert not (q / "sections").exists()
    r2 = run("import", str(p / "main.tex"), "--yes", cwd=q)
    assert r2.exit_code == 0, r2.output
    assert "+\\usepackage{loom}" in r2.output and "+++ sections/results.tex" in r2.output


def test_import_refuses_line_anchoring_and_fix_anchoring(tmp_path: Path) -> None:
    bad = RESULTS.replace("\\begin{lemma}\\label{lem:a}\nAlpha", "\\begin{lemma}\\label{lem:a} Alpha").replace(
        "Obvious.\n\\end{proof}", "Obvious. \\end{proof}"
    )
    p = paper_dir(tmp_path, bad)
    assert run("init", str(tmp_path / "q"), "--prefix", "pp", "--yes", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    r = run("import", str(p / "main.tex"), "--yes", cwd=q)
    assert r.exit_code == 1 and "line-anchoring" in r.output and not (q / "sections").exists()
    r2 = run("import", str(p / "main.tex"), "--yes", "--fix-anchoring", cwd=q)
    assert r2.exit_code == 0, r2.output
    fixed = (q / "sections" / "results.tex").read_text()
    assert "\\begin{lemma}\\label{pp-" in fixed and "\nAlpha" in fixed and "Obvious.\n\\end{proof}" in fixed
    assert anchoring_violations(fixed, {"lemma", "theorem", "definition"}) == []


def test_anchoring_violation_reports_the_authors_line(tmp_path: Path) -> None:
    """The master gains \\usepackage{loom} in loom's staged copy; the lines it reports are the author's, which that insertion must not shift."""
    p = paper_dir(tmp_path)
    bad = PAPER.replace("\\begin{definition}[Widget]\\label{def:widget}\nA widget", "\\begin{definition}[Widget]\\label{def:widget} A widget")
    (p / "main.tex").write_text(bad)
    expected = next(i for i, line in enumerate(bad.splitlines(), 1) if "\\begin{definition}" in line)
    assert run("init", str(tmp_path / "q"), "--prefix", "pp", "--yes", cwd=tmp_path).exit_code == 0
    r = run("import", str(p / "main.tex"), "--yes", cwd=tmp_path / "q")
    assert r.exit_code == 1, r.output
    assert f"line {expected}: \\begin{{definition}}" in r.output, r.output


def test_fix_anchoring_unit() -> None:
    text = (
        "Text \\begin{lemma}\\label{x} body\nmore \\end{lemma} tail\n\\begin{setting}\\label{y}one line\\end{setting}\n"
    )
    out = fix_anchoring(text, {"lemma", "setting"})
    assert (
        out
        == "Text\n\\begin{lemma}\\label{x}\nbody\nmore\n\\end{lemma}\ntail\n\\begin{setting}\\label{y}\none line\n\\end{setting}\n"
    )
    assert anchoring_violations(out, {"lemma", "setting"}) == []
    assert [v.line for v in anchoring_violations(text, {"lemma", "setting"})] == [1, 2, 3, 3]


def test_import_outside_tree_warning_and_in_place(tmp_path: Path) -> None:
    p = paper_dir(tmp_path)
    (p / "main.tex").write_text(PAPER.replace("\\input{preamble}", "\\input{preamble}\n\\input{../elsewhere}"))
    r = run("init", str(p), "--from", str(p / "main.tex"), "--prefix", "pp", "--yes", cwd=tmp_path)
    assert r.exit_code in (0, 1), r.output
    assert "loom:import-outside-tree" in r.output
    assert (p / "config.toml").exists() and (p / "drafts" / "main.tex").exists()
    assert (p / "main.tex").read_text().startswith("\\documentclass")  # the original still there, unmodified


def test_id_prints_patch_and_to_writes_copy(tmp_path: Path) -> None:
    p = paper_dir(tmp_path)
    assert (
        run(
            "init",
            str(tmp_path / "q"),
            "--from",
            str(p / "main.tex"),
            "--prefix",
            "pp",
            "--yes",
            cwd=tmp_path,
        ).exit_code
        == 0
    )
    q = tmp_path / "q"
    (q / "nodes" / "extra.tex").write_text(
        "\\begin{lemma}\\label{lem:extra}\nE\n\\end{lemma}\n\\subsection{Sub}\n\\paragraph{Par}\n"
    )
    r = run("id", "nodes/extra.tex", cwd=q)
    assert r.exit_code == 0, r.output
    assert (
        "+\\begin{lemma}\\label{pp-" in r.output
        and "+\\subsection{Sub}\\label{pp-" in r.output
        and "\\paragraph{Par}\\label" not in r.output
    )
    r2 = run("id", "nodes/extra.tex", "--all-levels", "--no-sections", cwd=q)
    assert "\\subsection{Sub}\\label" not in r2.output
    r3 = run("id", "nodes/extra.tex", "--to", str(tmp_path / "extra-labelled.tex"), cwd=q)
    assert r3.exit_code == 0 and "\\label{pp-" in (tmp_path / "extra-labelled.tex").read_text()
    assert "\\label{pp-" not in (q / "nodes" / "extra.tex").read_text()
    assert run("id", "nodes/extra.tex", "--to", str(tmp_path / "extra-labelled.tex"), cwd=q).exit_code == 2


def test_atomize_requires_dest_moves_nodes_and_identity(tmp_path: Path) -> None:
    p = paper_dir(tmp_path)
    assert (
        run(
            "init",
            str(tmp_path / "q"),
            "--from",
            str(p / "main.tex"),
            "--prefix",
            "pp",
            "--yes",
            cwd=tmp_path,
        ).exit_code
        == 0
    )
    q = tmp_path / "q"
    r = run("atomize", "drafts/main.tex", cwd=q)
    assert r.exit_code == 2 and "specify a destination file after the source, or with --to" in r.output
    r2 = run("atomize", "drafts/main.tex", "drafts/spine.tex", cwd=q)
    assert r2.exit_code == 0, r2.output
    spine = (q / "drafts" / "spine.tex").read_text()
    assert "\\input{nodes/pp-" in spine and "\\begin{definition}" not in spine
    node_files = sorted((q / "nodes").glob("pp-*.tex"))
    assert len(node_files) == 1 and "\\begin{definition}[Widget]" in node_files[0].read_text()
    assert not node_files[0].read_text().endswith("\n\n")
    assert "Identity test: pass" in r2.output
    assert (q / "drafts" / "main.tex").read_text().count("\\begin{definition}") == 1  # SRC untouched
    r3 = run("atomize", "sections/results.tex", "sections/results-spine.tex", cwd=q)
    assert r3.exit_code == 0, r3.output
    files = {f.name for f in (q / "nodes").glob("*.tex")}
    assert any(f.endswith(".proof.tex") for f in files), files  # the deferred proof of the theorem
    spine2 = (q / "sections" / "results-spine.tex").read_text()
    assert spine2.count("\\input{nodes/") == 3 and "Prose between" in spine2
    lemma = next(f for f in (q / "nodes").glob("pp-*.tex") if "Alpha" in f.read_text())
    assert "\\begin{proof}\nObvious." in lemma.read_text()  # adjacent proof travels with its statement
    assert run("atomize", "sections/results.tex", "sections/results-spine.tex", cwd=q).exit_code == 2  # exists
    assert run("atomize", "sections/results.tex", "sections/again.tex", cwd=q).exit_code == 1  # nodes/<id>.tex exists


def test_atomize_proofs_separate_directives_sections_and_all(tmp_path: Path) -> None:
    p = paper_dir(tmp_path)
    assert (
        run(
            "init",
            str(tmp_path / "q"),
            "--from",
            str(p / "main.tex"),
            "--prefix",
            "pp",
            "--yes",
            cwd=tmp_path,
        ).exit_code
        == 0
    )
    q = tmp_path / "q"
    results = q / "sections" / "results.tex"
    results.write_text(
        results.read_text().replace(
            "\\begin{lemma}\\label{pp-", "% !LOOM tags: moved-with-me\n\\begin{lemma}\\label{pp-"
        )
    )
    r = run("atomize", "sections/results.tex", "sections/spine.tex", "--proofs", "separate", cwd=q)
    assert r.exit_code == 0, r.output
    lemma = next(f for f in (q / "nodes").glob("pp-*.tex") if "Alpha" in f.read_text())
    assert lemma.read_text().startswith("% !LOOM tags: moved-with-me\n") and "\\begin{proof}" not in lemma.read_text()
    proof = next(f for f in (q / "nodes").glob("*.proof.tex") if "Obvious" in f.read_text())
    assert proof.exists()
    assert "\\label" not in proof.read_text().replace("\\label{", "", 0)
    r2 = run("atomize", "--all", "drafts/main.tex", "--to-dir", "atomized", cwd=q)
    assert r2.exit_code in (0, 1), r2.output
    assert (q / "atomized" / "drafts" / "main.tex").exists()


def test_atomize_sections_and_inline_round_trip(tmp_path: Path) -> None:
    p = paper_dir(tmp_path)
    assert (
        run(
            "init",
            str(tmp_path / "q"),
            "--from",
            str(p / "main.tex"),
            "--prefix",
            "pp",
            "--yes",
            cwd=tmp_path,
        ).exit_code
        == 0
    )
    q = tmp_path / "q"
    r = run("atomize", "sections/results.tex", "sections/spine.tex", "--sections", cwd=q)
    assert r.exit_code == 0, r.output
    spine = (q / "sections" / "spine.tex").read_text()
    assert spine.strip().startswith("\\input{nodes/pp-") and "\\section{Results}" not in spine
    section_file = next(f for f in (q / "nodes").glob("pp-*.tex") if "\\section{Results}" in f.read_text())
    assert "\\input{nodes/pp-" in section_file.read_text() and "Prose between" in section_file.read_text()
    r2 = run("inline", "sections/spine.tex", "sections/back.tex", "--all", cwd=q)
    assert r2.exit_code == 0, r2.output
    back = (q / "sections" / "back.tex").read_text()
    original = (q / "sections" / "results.tex").read_text()
    assert back.split() == original.split()
    assert run("inline", "sections/spine.tex", "sections/back.tex", cwd=q).exit_code == 2


def test_inline_nest_shifts_and_identity_on_master(tmp_path: Path) -> None:
    p = paper_dir(tmp_path)
    assert (
        run(
            "init",
            str(tmp_path / "q"),
            "--from",
            str(p / "main.tex"),
            "--prefix",
            "pp",
            "--yes",
            cwd=tmp_path,
        ).exit_code
        == 0
    )
    q = tmp_path / "q"
    (q / "sections" / "nested.tex").write_text("\\section{Nested}\\label{pp-0100}\nN\n")
    m = q / "drafts" / "main.tex"
    m.write_text(
        m.read_text().replace("\\input{sections/results}", "\\input{sections/results}\n\\nest{sections/nested}")
    )
    r = run("inline", "drafts/main.tex", "drafts/flat.tex", "--all", cwd=q)
    assert r.exit_code == 0, r.output
    flat = (q / "drafts" / "flat.tex").read_text()
    assert "\\subsection{Nested}" in flat and "\\nest{" not in flat and "\\input{sections/results}" not in flat
    assert "Identity test: pass" in r.output
    res = scan(load_quilt(q))
    assert "drafts/flat.tex" in res.masters


def test_selector_survives_atomize(tmp_path: Path) -> None:
    """A quote-anchored comment on a theorem stays attached after the theorem moves from its section file to nodes/<id>.tex: the key and the text are unchanged, only the file is."""
    p = paper_dir(tmp_path)
    assert (
        run(
            "init",
            str(tmp_path / "q"),
            "--from",
            str(p / "main.tex"),
            "--prefix",
            "pp",
            "--yes",
            cwd=tmp_path,
        ).exit_code
        == 0
    )
    q = tmp_path / "q"
    r = run("comment", "pp-0005", "Which lemma?", "--quote", "Beta uses", "--kind", "question", "--author", "R", cwd=q)
    assert r.exit_code == 0, r.output
    before = run("status", "--explain", "pp-0005", cwd=q).output
    assert "1 open question" in before and "detached" not in before
    assert run("atomize", "sections/results.tex", "sections/results-spine.tex", cwd=q).exit_code == 0
    (q / "sections" / "results-spine.tex").replace(q / "sections" / "results.tex")  # adopt the spine
    after = run("status", "--explain", "pp-0005", cwd=q).output
    assert "1 open question" in after and "detached" not in after, after
    assert "nodes/pp-0005.tex" in after
    assert "detached-annotation" not in run("lint", cwd=q).output
