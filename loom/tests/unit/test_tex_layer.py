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
        "Man12-setup",
        "Man12-prop-3.2",
    }  # the proof cites Man12 by postnote (book 8.11)
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
    run_dir = d / "ai" / "runs" / "t"
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
    run_dir = d / "ai" / "runs" / "t"
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
