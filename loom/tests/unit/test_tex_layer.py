"""TeX layer on the shim: aux parsing, compile, linearize, bundles with --with and --draft, check."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from loom.cli import main
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from loom.tex.assemble import assemble, shift_sectioning
from loom.tex.aux import parse_aux
from loom.tex.bundle import apply_unified_diff, build_bundle, unified_diff

REPO = Path(__file__).resolve().parents[2]


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def demo(tmp_path: Path) -> Path:
    r = run("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    assert r.exit_code == 0, r.output
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
    r = run("compile", cwd=d)
    assert r.exit_code == 0, r.output
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
    r = run("linearize", "drafting/main.tex", "--to", "drafting/flat.tex", "--no-check", cwd=root)
    assert r.exit_code == 0, r.output
    flat = (root / "drafting" / "flat.tex").read_text()
    assert "\\input{" not in flat and "\\subsection{Two}" in flat
    assert run("linearize", "drafting/main.tex", "--to", "drafting/flat.tex", "--no-check", cwd=root).exit_code == 2
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
    c = run("compile", "dm-0003", cwd=d)
    assert c.exit_code == 0, c.output
    assert (d / "build" / "bundles" / "dm-0003" / "dm-0003.pdf").exists()


def test_source_prints_a_key_and_its_closure(tmp_path: Path) -> None:
    """`loom source` replaced `loom bundle` as the way to read a result: it prints, so there is no file to go stale."""
    d = demo(tmp_path)
    run_dir = d / run("ai", "start", "Reading dm-0002", cwd=d).output.strip()
    r = run("source", "dm-0002", "--run", str(run_dir), cwd=d)
    assert r.exit_code == 0, r.output
    assert r.output.startswith("\\begin{lemma}[Orbits]\\label{dm-0002}")
    assert "% id:" not in r.output  # the key alone, not the closure document
    assert not list(run_dir.glob("*.tex"))  # nothing written into the run
    assert "loom source dm-0002" in (run_dir / "run.log").read_text()

    # the theorem's own closure is empty -- its dependency is declared inside the proof, so the proof key is the one
    # with something to gather, which is also what a referee reads
    c = run("source", "dm-0003/proof", "--closure", cwd=d)
    assert c.exit_code == 0, c.output
    assert c.output.index("% id: dm-0002") < c.output.index("% id: dm-0003") < c.output.index("% proof: dm-0003/proof")
    assert "\\usepackage{loom}" in c.output


def test_source_prints_a_whole_document_flattened(tmp_path: Path) -> None:
    """An agent asked about a paper rather than a result needs the document; `loom linearize` would do it by superseding the master, and is denied to agents, so `loom source` takes a path (DR-155)."""
    d = demo(tmp_path)
    run_dir = d / run("ai", "start", "Reading the paper", cwd=d).output.strip()
    r = run("source", "drafting/main.tex", "--run", str(run_dir), cwd=d)
    assert r.exit_code == 0, r.output
    assert "\\documentclass" in r.output  # the document, preamble and all
    assert "\\input{" not in r.output  # every inclusion expanded in place
    assert "\\begin{lemma}[Orbits]\\label{dm-0002}" in r.output  # including the node files it pulls in
    assert "loom source drafting/main.tex" in (run_dir / "run.log").read_text()

    before = sorted(p.relative_to(d) for p in d.rglob("*.tex"))
    assert run("source", "drafting/main.tex", cwd=d).exit_code == 0
    assert sorted(p.relative_to(d) for p in d.rglob("*.tex")) == before  # nothing written, nothing superseded

    c = run("source", "drafting/main.tex", "--closure", cwd=d)
    assert c.exit_code != 0
    assert "already carries what it includes" in c.output  # --closure is a key's option

    assert run("source", "ai/runs/t/nope.tex", cwd=d).exit_code != 0  # a path loom does not scan is not a document


def test_compile_with_diff_does_not_touch_quilt(tmp_path: Path) -> None:
    d = demo(tmp_path)
    node = d / "nodes" / "dm-0002.tex"
    original = node.read_text()
    proposed = original.replace("Every orbit of a widget has one or two points", "Orbits have at most two points")
    diff = unified_diff(original, proposed, "nodes/dm-0002.tex")
    (tmp_path / "proposal.diff").write_text(diff)
    assert apply_unified_diff(original, diff) == proposed
    r = run("compile", "dm-0002", "--with", str(tmp_path / "proposal.diff"), cwd=d)
    assert r.exit_code == 0, r.output
    text = (d / "build" / "bundles" / "dm-0002.tex").read_text()
    assert "Orbits have at most two points" in text and "Every orbit of a widget" not in text
    assert node.read_text() == original
    (tmp_path / "replacement.tex").write_text(
        "\\begin{lemma}[Orbits]\\label{dm-0002}\nReplaced statement.\n\\end{lemma}\n"
    )
    r2 = run("compile", "dm-0002", "--with", str(tmp_path / "replacement.tex"), cwd=d)
    assert r2.exit_code == 0 and "Replaced statement." in (d / "build" / "bundles" / "dm-0002.tex").read_text()


def test_compile_with_bad_diff_exit_1(tmp_path: Path) -> None:
    d = demo(tmp_path)
    (tmp_path / "bad.diff").write_text(
        "--- a/nodes/dm-0002.tex\n+++ b/nodes/dm-0002.tex\n@@ -1,1 +1,1 @@\n-this line is not in the file\n+replacement\n"
    )
    r = run("compile", "dm-0002", "--with", str(tmp_path / "bad.diff"), cwd=d)
    assert r.exit_code == 1 and "does not match" in r.output


def test_compile_draft_unpromoted_node(tmp_path: Path) -> None:
    d = demo(tmp_path)
    draft = tmp_path / "draft-dm-0019.tex"
    draft.write_text(
        "\\begin{lemma}[Drafted]\\label{dm-0019}\nUses Lemma~\\ref{lem:orbits}.\n\\end{lemma}\n\\begin{proof}\n\\uses{dm-0001}\nP\n\\end{proof}\n"
    )
    r = run("compile", "--draft", str(draft), cwd=d)
    assert r.exit_code == 0, r.output
    out = d / "build" / "bundles" / "draft-draft-dm-0019.tex"
    text = out.read_text()
    assert "% id: dm-0002" in text and "% id: dm-0001" in text and "Drafted" in text
    draft.write_text("\\begin{lemma}\\label{dm-0019}\nSee \\ref{nope}.\n\\end{lemma}\n")
    assert run("compile", "--draft", str(draft), cwd=d).exit_code == 1


def test_check_lints_and_compiles(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = run("check", cwd=d)
    assert r.exit_code == 0, r.output
    assert "ok      drafting/main.tex" in r.output and r.output.strip().endswith("check: ok")
    r2 = run("check", "--bundles", "all", cwd=d)
    assert r2.exit_code == 0 and "bundle dm-0003" in r2.output
    (d / "nodes" / "dup.tex").write_text("\\begin{lemma}\\label{dm-0001}\n\\end{lemma}\n")
    assert run("check", "--no-compile", cwd=d).exit_code == 1


def test_compile_failure_reports_first_error(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    d = demo(tmp_path)
    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    r = run("compile", cwd=d)
    assert r.exit_code == 1 and "! LaTeX Error" in r.output


def test_search_json_still_single_document(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = run("search", "widget", "--json", cwd=d)
    json.loads(r.output)


def test_a_statements_closure_covers_the_proof_it_prints(tmp_path: Path) -> None:
    """The bundle printed the proof and excluded the lemmas that proof invokes, so an agent told the bundle was complete context saw undefined references (F2)."""
    d = demo(tmp_path)
    r = run("source", "dm-0003", "--closure", cwd=d)
    assert r.exit_code == 0, r.output
    ids = [ln.split()[-1] for ln in r.output.splitlines() if ln.startswith("% id:") or ln.startswith("% proof:")]
    assert "dm-0002" in ids  # used by dm-0003's proof, which this bundle prints
    assert ids[-1] == "dm-0003/proof" and ids.index("dm-0002") < ids.index("dm-0003")


def test_with_names_a_file_first_and_then_an_annotation(tmp_path: Path) -> None:
    """`--with` gave a bare FileNotFoundError traceback, and an annotation's payload is the proposal it could not take (F15)."""
    d = demo(tmp_path)
    missing = run("compile", "dm-0002", "--with", "nope.tex", cwd=d)
    assert missing.exit_code != 0
    assert "no such file, and no annotation has that id" in missing.output
    assert "Traceback" not in missing.output

    text = (d / "nodes" / "dm-0002.tex").read_text().replace("one or two points", "at most two points")
    c = run("comment", "dm-0002", "Tighten it", "--payload", text, "--author", "Tom", cwd=d)
    assert c.exit_code == 0, c.output
    ann = c.output.split()[0]
    r = run("compile", "dm-0002", "--with", ann, cwd=d)
    assert r.exit_code == 0, r.output
    assert "at most two points" in (d / "build" / "bundles" / "dm-0002.tex").read_text()

    wrong = run("compile", "dm-0003", "--with", ann, cwd=d)
    assert wrong.exit_code != 0 and "is on dm-0002, not dm-0003" in wrong.output


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


def test_id_and_new_log_themselves_to_the_run(tmp_path: Path) -> None:
    """The orientation lists both among an agent's commands and says every command that takes --run logs the call (F7)."""
    d = demo(tmp_path)
    rel = run("ai", "start", "Drafting", cwd=d).output.strip()
    run_dir = d / rel
    assert run("id", "--next", "--run", rel, cwd=d).exit_code == 0
    assert run("new", "lemma", "Rigidity", "--run", rel, cwd=d).exit_code == 0
    log = (run_dir / "run.log").read_text()
    assert "loom id --next" in log and "loom new lemma" in log


def test_citation_labels_come_from_the_compile() -> None:
    """BibTeX's `\\bibcite` (plain and natbib), and biblatex's `labelalpha` with `extraalpha` as a letter."""
    from loom.tex.aux import parse_cite_labels

    aux = "\\bibcite{b}{1}\n\\bibcite{nat}{{7}{2008}{{Manolache}}{{}}}\n\\bibcite{al}{ABC{\\etalchar{+}}99}\n"
    bbl = "\\entry{gp}{article}{}\n\\field{labelalpha}{GP99}\n\\field{extraalpha}{2}\n\\endentry\n\\entry{x}{book}{}\n\\endentry\n"
    assert parse_cite_labels(aux, bbl) == {"b": "1", "nat": "7", "al": "ABC+99", "gp": "GP99b"}
