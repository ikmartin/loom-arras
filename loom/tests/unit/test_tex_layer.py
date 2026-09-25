"""TeX layer on the shim: aux parsing, compile, linearize, bundles with --with and --draft, check."""

from __future__ import annotations

import os
from pathlib import Path

from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from loom.tex.assemble import assemble, shift_sectioning
from loom.tex.aux import parse_aux
from loom.tex.bundle import apply_unified_diff, build_bundle, unified_diff
from tests.helpers import exits, ok, refused

REPO = Path(__file__).resolve().parents[2]


def demo(tmp_path: Path) -> Path:
    ok("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    return tmp_path / "demo"


def test_aux_read_plain_and_hyperref() -> None:
    text = "\\relax\n\\newlabel{lem:a}{{1.1}{1}}\n\\newlabel{lem:a@cref}{{[lemma][1][1]1.1}{[1][1][]1}}\n\\newlabel{thm:b}{{2.1}{12}{Main theorem}{theorem.2.1}{}}\n\\newlabel{eq:c}{{3}{4}}\n\\newlabel{sec:s}{{2}{12}{Results}{section.2}{}}\n"
    n = parse_aux(text)
    assert n["lem:a"].number == "1.1" and n["lem:a"].page == 1
    assert n["thm:b"].number == "2.1" and n["thm:b"].page == 12
    assert n["eq:c"].number == "3" and n["sec:s"].number == "2"
    assert "lem:a@cref" not in n


def test_compile_master_and_numbers_from_aux(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("compile", cwd=d)
    aux = d / "build" / "main" / "main.aux"
    assert aux.exists()
    n = parse_aux(aux.read_text())
    assert n["dm-0001"].number == "1.1" and n["dm-0003"].number == "2.1"
    log = Path(os.environ["FAKE_TEX_LOG"]).read_text()
    assert "-outdir=" in log and "drafting/main.tex" in log


def test_linearize_flattens_with_nest_shift(tmp_path: Path) -> None:
    root = tmp_path / "q"
    (root / "drafting").mkdir(parents=True)
    (root / "sections").mkdir()
    (root / "config.toml").write_text('[quilt]\nmain = "drafting/main.tex"\n')
    (root / "drafting" / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\\section{A}\n\\input{sections/one}\n\\nest{sections/two}\n\\end{document}\n"
    )
    (root / "sections" / "one.tex").write_text("one % comment kept\n")
    (root / "sections" / "two.tex").write_text("\\section{Two}\n\\subsection{Deeper}\n")
    text = assemble(root, "drafting/main.tex")
    assert "\\input{" not in text and "\\nest{" not in text
    assert "one % comment kept" in text
    assert "\\subsection{Two}" in text and "\\subsubsection{Deeper}" in text
    assert shift_sectioning("\\subparagraph{x}", 1) == "\\subparagraph{x}"
    r = ok("linearize", "drafting/main.tex", "--to", "drafting/flat.tex", "--no-check", cwd=root)
    flat = (root / "drafting" / "flat.tex").read_text()
    assert "\\input{" not in flat and "\\subsection{Two}" in flat
    refused(
        "linearize",
        "drafting/main.tex",
        "--to",
        "drafting/flat.tex",
        "--no-check",
        cwd=root,
        code=2,
        match="exists; linearize never overwrites",
    )
    # the spine and everything it inlined are now superseded: they define nothing until loom live
    assert "superseded" in r.output


def test_bundle_contents_and_order(tmp_path: Path) -> None:
    d = demo(tmp_path)
    result = scan(load_quilt(d))
    b = build_bundle(result, "dm-0003/proof")
    assert set(b.closure) == {
        "dm-0002",
        "Calloway14-def-3.1",
        "Calloway14-prop-3.2",
    }  # the proof cites Calloway14 by postnote (book 8.11)
    text = b.text
    assert text.index("\\usepackage{loom}") < text.index("\\begin{document}")
    assert text.index("% id: dm-0002") < text.index("% id: dm-0003") < text.index("% proof: dm-0003/proof")
    assert "\\begin{lemma}[Orbits]\\label{dm-0002}" in text and "\\begin{theorem}[Main]\\label{dm-0003}" in text
    assert "Take" not in text  # dm-0002's proof is not part of the closure
    ok("compile", "dm-0003", cwd=d)
    assert (d / "build" / "bundles" / "dm-0003" / "dm-0003.pdf").exists()


def test_compile_with_diff_does_not_touch_quilt(tmp_path: Path) -> None:
    d = demo(tmp_path)
    node = d / "nodes" / "dm-0002.tex"
    original = node.read_text()
    proposed = original.replace("Every orbit of a widget has one or two points", "Orbits have at most two points")
    diff = unified_diff(original, proposed, "nodes/dm-0002.tex")
    (tmp_path / "proposal.diff").write_text(diff)
    assert apply_unified_diff(original, diff) == proposed
    ok("compile", "dm-0002", "--with", str(tmp_path / "proposal.diff"), cwd=d)
    text = (d / "build" / "bundles" / "dm-0002.tex").read_text()
    assert "Orbits have at most two points" in text and "Every orbit of a widget" not in text
    assert node.read_text() == original
    (tmp_path / "replacement.tex").write_text(
        "\\begin{lemma}[Orbits]\\label{dm-0002}\nReplaced statement.\n\\end{lemma}\n"
    )
    ok("compile", "dm-0002", "--with", str(tmp_path / "replacement.tex"), cwd=d)
    assert "Replaced statement." in (d / "build" / "bundles" / "dm-0002.tex").read_text()


def test_compile_with_bad_diff_exit_1(tmp_path: Path) -> None:
    d = demo(tmp_path)
    (tmp_path / "bad.diff").write_text(
        "--- a/nodes/dm-0002.tex\n+++ b/nodes/dm-0002.tex\n@@ -1,1 +1,1 @@\n-this line is not in the file\n+replacement\n"
    )
    refused("compile", "dm-0002", "--with", str(tmp_path / "bad.diff"), cwd=d, code=1, match="does not match")


def test_compile_draft_unpromoted_node(tmp_path: Path) -> None:
    d = demo(tmp_path)
    draft = tmp_path / "draft-dm-0019.tex"
    draft.write_text(
        "\\begin{lemma}[Drafted]\\label{dm-0019}\nUses Lemma~\\ref{lem:orbits}.\n\\end{lemma}\n\\begin{proof}\n\\uses{dm-0001}\nP\n\\end{proof}\n"
    )
    ok("compile", "--draft", str(draft), cwd=d)
    out = d / "build" / "bundles" / "draft-draft-dm-0019.tex"
    text = out.read_text()
    assert "% id: dm-0002" in text and "% id: dm-0001" in text and "Drafted" in text
    draft.write_text("\\begin{lemma}\\label{dm-0019}\nSee \\ref{nope}.\n\\end{lemma}\n")
    refused("compile", "--draft", str(draft), cwd=d, code=1, match="the draft references unknown labels: nope")


def test_check_lints_and_compiles(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = ok("check", cwd=d)
    assert "ok      drafting/main.tex" in r.output and r.output.strip().endswith("check: ok")
    assert "bundle dm-0003" in ok("check", "--bundles", "all", cwd=d).output
    (d / "nodes" / "dup.tex").write_text("\\begin{lemma}\\label{dm-0001}\n\\end{lemma}\n")
    assert "duplicate-id" in exits(1, "check", "--no-compile", cwd=d).output


def test_compile_failure_reports_first_error(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    d = demo(tmp_path)
    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    assert "! LaTeX Error" in exits(1, "compile", cwd=d).output


def test_with_names_a_file_first_and_then_an_annotation(tmp_path: Path) -> None:
    """`--with` gave a bare FileNotFoundError traceback, and an annotation's payload is the proposal it could not take (F15)."""
    d = demo(tmp_path)
    missing = refused(
        "compile", "dm-0002", "--with", "nope.tex", cwd=d, code=2, match="no such file, and no annotation has that id"
    )
    assert "Traceback" not in missing.output

    text = (d / "nodes" / "dm-0002.tex").read_text().replace("one or two points", "at most two points")
    c = ok("comment", "dm-0002", "Tighten it", "--payload", text, "--author", "Tom", cwd=d)
    ann = c.stdout.split()[0]
    ok("compile", "dm-0002", "--with", ann, cwd=d)
    assert "at most two points" in (d / "build" / "bundles" / "dm-0002.tex").read_text()

    refused("compile", "dm-0003", "--with", ann, cwd=d, code=1, match="is on dm-0002, not dm-0003")


def test_a_readable_pdf_is_not_a_failure(tmp_path: Path) -> None:
    """latexmk exits nonzero on an undefined reference and still writes a PDF; FAILED there is a verdict an agent has to ignore (F16)."""
    from loom.tex.runner import CompileResult

    pdf = tmp_path / "b.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    log = tmp_path / "b.log"
    log.write_text("LaTeX Warning: Reference `rl-000D' on page 1 undefined on input line 12.\n")

    warned = CompileResult(False, "pdflatex", tmp_path, 12, "", [], pdf, None, log, ["LaTeX Warning: ..."])
    assert warned.usable == "warnings"
    assert CompileResult(True, "pdflatex", tmp_path, 0, "", [], pdf, None, log).usable == "ok"
    broken = CompileResult(False, "pdflatex", tmp_path, 12, "", ["! Undefined control sequence."], None, None, log)
    assert broken.usable == "failed" and broken.first_error == "! Undefined control sequence."

    # the old fallback took the last line of latexmk's closing advice, which reads as a mangled sentence
    quiet = CompileResult(
        False, "pdflatex", tmp_path, 12, "latexmk after you've corrected the files.", [], None, None, log
    )
    assert quiet.first_error == "latexmk exited 12 with no error line in b.log"

    # a failing biber leaves no `! ` line; latexmk's own summary names it
    stdout = "Collected error summary (may duplicate other messages):\n  biber out/b: Command for 'biber out/b' gave return code 2\n\nLatexmk: Sometimes, the -f option can be used\n"
    biber = CompileResult(False, "pdflatex", tmp_path, 12, stdout, [], pdf, None, log)
    assert biber.first_error == "latexmk exited 12: biber out/b: Command for 'biber out/b' gave return code 2"


def test_stage_sources_leaves_the_build_products_behind(tmp_path: Path) -> None:
    """A compile of the author's directory reads their editor's .bbl and .fdb_latexmk and rewrites them; the staged copy carries sources only."""
    from loom.tex.runner import stage_sources

    p = tmp_path / "shared" / "paper"
    (p / "figs").mkdir(parents=True)
    (p / ".git").mkdir()
    for name in (
        "main.tex",
        "refs.bib",
        "figs/a.pdf",
        "main.aux",
        "main.bbl",
        "main.fdb_latexmk",
        "main.synctex.gz",
        ".git/HEAD",
    ):
        (p / name).write_text("x")
    (tmp_path / "shared" / "macros.sty").write_text("x")

    root = stage_sources(p, tmp_path / "stage", [str(p / ".." / "macros.sty")])
    assert root == tmp_path / "stage" / "paper"
    assert sorted(f.relative_to(root).as_posix() for f in root.rglob("*") if f.is_file()) == [
        "figs/a.pdf",
        "main.tex",
        "refs.bib",
    ]
    assert (root / ".." / "macros.sty").is_file()  # ../macros still resolves from the copy

    (p / "refs.bib").unlink()  # an arXiv-style source ships its .bbl and no .bib
    assert (stage_sources(p, tmp_path / "stage2") / "main.bbl").is_file()


def test_citation_labels_come_from_the_compile() -> None:
    """BibTeX's `\\bibcite` (plain and natbib), and biblatex's `labelalpha` with `extraalpha` as a letter."""
    from loom.tex.aux import parse_cite_labels

    aux = "\\bibcite{b}{1}\n\\bibcite{nat}{{7}{2008}{{Manolache}}{{}}}\n\\bibcite{al}{ABC{\\etalchar{+}}99}\n"
    bbl = "\\entry{gp}{article}{}\n\\field{labelalpha}{GP99}\n\\field{extraalpha}{2}\n\\endentry\n\\entry{x}{book}{}\n\\endentry\n"
    assert parse_cite_labels(aux, bbl) == {"b": "1", "nat": "7", "al": "ABC+99", "gp": "GP99b"}
