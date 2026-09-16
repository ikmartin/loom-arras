"""TeX layer on the shim: aux parsing, compile, assemble, bundles with --with and --draft, check."""

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
    r = run("init", str(tmp_path / "demo"), "--demo", "--no-git", cwd=tmp_path)
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
    assert "-outdir=" in log and "drafts/main.tex" in log


def test_assemble_flattens_with_nest_shift(tmp_path: Path) -> None:
    root = tmp_path / "q"
    (root / "drafts").mkdir(parents=True)
    (root / "sections").mkdir()
    (root / "config.toml").write_text('[quilt]\nmain = "drafts/main.tex"\n')
    (root / "drafts" / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\\section{A}\n\\input{sections/one}\n\\nest{sections/two}\n\\end{document}\n"
    )
    (root / "sections" / "one.tex").write_text("one % comment kept\n")
    (root / "sections" / "two.tex").write_text("\\section{Two}\n\\subsection{Deeper}\n")
    text = assemble(root, "drafts/main.tex")
    assert "\\input{" not in text and "\\nest{" not in text
    assert "one % comment kept" in text
    assert "\\subsection{Two}" in text and "\\subsubsection{Deeper}" in text
    assert shift_sectioning("\\subparagraph{x}", 1) == "\\subparagraph{x}"
    r = run("assemble", "drafts/main.tex", str(tmp_path / "flat.tex"), cwd=root)
    assert r.exit_code == 0 and (tmp_path / "flat.tex").exists()
    assert run("assemble", "drafts/main.tex", str(tmp_path / "flat.tex"), cwd=root).exit_code == 2


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
    r = run("bundle", "dm-0003", cwd=d)
    assert r.exit_code == 0 and r.output.strip() == "build/bundles/dm-0003.tex"
    c = run("compile", "dm-0003", cwd=d)
    assert c.exit_code == 0, c.output
    assert (d / "build" / "bundles" / "dm-0003" / "dm-0003.pdf").exists()


def test_bundle_run_copy_and_log(tmp_path: Path) -> None:
    d = demo(tmp_path)
    run_dir = d / "ai" / "runs" / "t"
    r = run("bundle", "dm-0002", "--run", str(run_dir), cwd=d)
    assert r.exit_code == 0, r.output
    assert (run_dir / "bundle-dm-0002.tex").exists()
    assert "loom bundle dm-0002" in (run_dir / "run.log").read_text()


def test_bundle_with_diff_does_not_touch_quilt(tmp_path: Path) -> None:
    d = demo(tmp_path)
    node = d / "nodes" / "dm-0002.tex"
    original = node.read_text()
    proposed = original.replace("Every orbit of a widget has one or two points", "Orbits have at most two points")
    diff = unified_diff(original, proposed, "nodes/dm-0002.tex")
    (tmp_path / "proposal.diff").write_text(diff)
    assert apply_unified_diff(original, diff) == proposed
    r = run("bundle", "dm-0002", "--with", str(tmp_path / "proposal.diff"), cwd=d)
    assert r.exit_code == 0, r.output
    text = (d / "build" / "bundles" / "dm-0002.tex").read_text()
    assert "Orbits have at most two points" in text and "Every orbit of a widget" not in text
    assert node.read_text() == original
    (tmp_path / "replacement.tex").write_text(
        "\\begin{lemma}[Orbits]\\label{dm-0002}\nReplaced statement.\n\\end{lemma}\n"
    )
    r2 = run("bundle", "dm-0002", "--with", str(tmp_path / "replacement.tex"), cwd=d)
    assert r2.exit_code == 0 and "Replaced statement." in (d / "build" / "bundles" / "dm-0002.tex").read_text()


def test_bundle_with_bad_diff_exit_1(tmp_path: Path) -> None:
    d = demo(tmp_path)
    (tmp_path / "bad.diff").write_text(
        "--- a/nodes/dm-0002.tex\n+++ b/nodes/dm-0002.tex\n@@ -1,1 +1,1 @@\n-this line is not in the file\n+replacement\n"
    )
    r = run("bundle", "dm-0002", "--with", str(tmp_path / "bad.diff"), cwd=d)
    assert r.exit_code == 1 and "does not match" in r.output


def test_bundle_draft_unpromoted_node(tmp_path: Path) -> None:
    d = demo(tmp_path)
    draft = tmp_path / "draft-dm-0019.tex"
    draft.write_text(
        "\\begin{lemma}[Drafted]\\label{dm-0019}\nUses Lemma~\\ref{lem:orbits}.\n\\end{lemma}\n\\begin{proof}\n\\uses{dm-0001}\nP\n\\end{proof}\n"
    )
    r = run("bundle", "--draft", str(draft), cwd=d)
    assert r.exit_code == 0, r.output
    out = d / "build" / "bundles" / "draft-draft-dm-0019.tex"
    text = out.read_text()
    assert "% id: dm-0002" in text and "% id: dm-0001" in text and "Drafted" in text
    draft.write_text("\\begin{lemma}\\label{dm-0019}\nSee \\ref{nope}.\n\\end{lemma}\n")
    assert run("bundle", "--draft", str(draft), cwd=d).exit_code == 1


def test_check_lints_and_compiles(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = run("check", cwd=d)
    assert r.exit_code == 0, r.output
    assert "ok      drafts/main.tex" in r.output and r.output.strip().endswith("check: ok")
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
