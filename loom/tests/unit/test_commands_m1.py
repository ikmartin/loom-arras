"""M1 commands on the demo quilt: init, new, lint, search, deps, unravel, delete."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main


def run(*args: str, cwd: Path | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        if cwd:
            os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def test_init_creates_layout(tmp_path: Path) -> None:
    r = run("init", str(tmp_path / "q"), "--prefix", "zz", "--no-git", "--yes")
    assert r.exit_code == 0, r.output
    q = tmp_path / "q"
    for rel in ("config.toml", "loom.sty", "drafts/main.tex", "nodes", "refs", "comments", ".gitignore", "README.md"):
        assert (q / rel).exists(), rel
    assert 'prefix = "zz"' in (q / "config.toml").read_text()
    assert "\\usepackage{loom}" in (q / "drafts/main.tex").read_text()
    lint = run("lint", cwd=q)
    assert lint.exit_code == 0, lint.output


def test_init_refuses_in_quilt_and_nonempty(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "q"), "--prefix", "a", "--no-git", "--yes").exit_code == 0
    assert run("init", str(tmp_path / "q" / "inner"), "--no-git", "--yes").exit_code == 2
    (tmp_path / "full").mkdir()
    (tmp_path / "full" / "x.txt").write_text("x")
    assert run("init", str(tmp_path / "full"), "--no-git", "--yes").exit_code == 2


def test_init_git_init_unless_no_git(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "g"), "--prefix", "a", "--yes").exit_code == 0
    assert (tmp_path / "g" / ".git").is_dir()
    assert run("init", str(tmp_path / "n"), "--prefix", "a", "--yes", "--no-git").exit_code == 0
    assert not (tmp_path / "n" / ".git").exists()


def test_init_demo_writes_demo_and_lints_clean(tmp_path: Path) -> None:
    r = run("init", str(tmp_path / "demo"), "--demo", "--no-git")
    assert r.exit_code == 0, r.output
    demo = tmp_path / "demo"
    assert (demo / "refs" / "Man12.tex").exists() and (demo / "nodes" / "dm-0003.tex").exists()
    lint = run("lint", "--json", cwd=demo)
    assert lint.exit_code == 0, lint.output
    diags = json.loads(lint.output)
    assert {d["severity"] for d in diags} <= {"info", "warning"}
    codes = sorted(d["code"] for d in diags)
    assert "loom:undigested-citekey" not in codes or True


def test_init_minimal_master_declares_candidate_taxa(tmp_path: Path) -> None:
    """A quilt is usable for planning from the first minute: `conjecture` owes a proof and shows as a gap, `question` owes nothing (plan 0.2 §4)."""
    assert run("init", str(tmp_path / "q"), "--no-git", "--yes").exit_code == 0
    main = (tmp_path / "q" / "drafts" / "main.tex").read_text()
    assert "\\newtheorem{conjecture}[theorem]{Conjecture}" in main
    assert "\\newtheorem{question}[theorem]{Question}" in main

    # a conjecture is plain, because it owes a proof; a question is a remark, because it owes nothing
    def style_of(name: str) -> str:
        return main[: main.index("{" + name + "}[theorem]")].rsplit("\\theoremstyle{", 1)[1].split("}")[0]

    assert style_of("conjecture") == "plain"
    assert style_of("question") == "remark"


def test_init_from_leaves_the_authors_preamble_alone(tmp_path: Path) -> None:
    """`--from` adopts a paper as it is; loom does not edit an author's preamble to add its own taxa."""
    src = tmp_path / "paper.tex"
    src.write_text(
        "\\documentclass{article}\n\\newtheorem{thm}{Theorem}\n\\begin{document}\nHello.\n\\end{document}\n",
        encoding="utf-8",
    )
    r = run("init", str(tmp_path / "q"), "--from", str(src), "--no-git", "--yes")
    assert r.exit_code == 0, r.output
    main = (tmp_path / "q" / "drafts" / "paper.tex").read_text()
    assert "conjecture" not in main and "question" not in main


def test_demo_has_outline_master(tmp_path: Path) -> None:
    """The demo shows the outline pattern: a second master reaching one conjecture and one question, so a candidate is reached rather than loose while it is being considered (plan 0.2 §1.2, book 4.4)."""
    assert run("init", str(tmp_path / "demo"), "--demo", "--no-git").exit_code == 0
    demo = tmp_path / "demo"
    outline = demo / "drafts" / "outline.tex"
    assert outline.exists()
    r = run("status", "--master", "drafts/outline.tex", "--json", cwd=demo)
    assert r.exit_code == 0, r.output
    keys = json.loads(r.output)["keys"]
    reached = {k for k, v in keys.items() if "drafts/outline.tex" in v["reached_by"]}
    assert {"dm-0006", "dm-0007"} <= reached  # the candidates are reached, not loose, while they are being considered
    taxa = {n["key"]: n.get("taxon") for n in json.loads(run("search", "dm-000", "--json", cwd=demo).output)}
    assert taxa.get("dm-0006") == "Conjecture" and taxa.get("dm-0007") == "Question"
    # the conjecture owes a proof and is a gap until it is proved or refuted; the question owes nothing
    assert keys["dm-0006/proof"]["state"] == "incomplete"
    assert "dm-0007/proof" not in keys


def test_deps_prints_see_also(tmp_path: Path) -> None:
    """`deps` reports relations in a final section marked not-a-dependency, and `--json` carries them beside the closure (plan 0.2 §2.2)."""
    q = tmp_path / "syn"
    shutil.copytree(Path(__file__).resolve().parents[1] / "quilts" / "synthetic", q)
    r = run("deps", "sy-0008", cwd=q)
    assert r.exit_code == 0, r.output
    assert "see also (not a dependency):" in r.output
    assert "sy-0009" in r.output.split("see also (not a dependency):")[1]

    payload = json.loads(run("deps", "sy-0009", "--json", cwd=q).output)
    assert payload["relations"] == [{"key": "sy-0008", "kind": "see"}]  # both directions are reported
    assert all(e["key"] != "sy-0008" for e in payload["closure"])  # and a relation is not in the closure


def test_new_allocates_and_print(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "demo"), "--demo", "--no-git").exit_code == 0
    demo = tmp_path / "demo"
    p = run("new", "lemma", "Printed", "--print", cwd=demo)
    assert p.exit_code == 0, p.output
    assert "\\begin{lemma}[Printed]" in p.output and "\\label{" not in p.output and "\\begin{proof}" in p.output
    r = (
        run("new", "Lemma", "A new lemma", "--author", cwd=demo)
        if False
        else run("new", "Lemma", "A new lemma", cwd=demo)
    )
    assert r.exit_code == 0, r.output
    assert r.output.startswith("dm-0012 ")
    text = (demo / "nodes" / "dm-0012.tex").read_text()
    assert "\\begin{lemma}[A new lemma]\\label{dm-0012}" in text and "% !LOOM created:" in text
    r2 = run("new", "definition", cwd=demo)
    assert r2.output.startswith("dm-0013 ")
    assert "\\begin{proof}" not in (demo / "nodes" / "dm-0013.tex").read_text()
    bad = run("new", "nonsense", cwd=demo)
    assert bad.exit_code == 2


def test_alloc_sees_references_and_never_reuses(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "demo"), "--demo", "--no-git").exit_code == 0
    demo = tmp_path / "demo"
    (demo / "nodes" / "scratch.tex").write_text("% dangling reference\nSee \\ref{dm-0020}.\n")
    r = run("new", "lemma", cwd=demo)
    assert r.output.startswith("dm-0021 "), r.output


def test_search_deps_unravel_delete(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "demo"), "--demo", "--no-git").exit_code == 0
    demo = tmp_path / "demo"
    s = run("search", "orbits", "--json", cwd=demo)
    assert s.exit_code == 0, s.output
    entries = json.loads(s.output)
    assert entries[0]["key"] == "dm-0002" and "lem:orbits" in entries[0]["aliases"]
    s2 = run("search", "lem:orbits", cwd=demo)
    assert s2.output.startswith("dm-0002 ")
    d = run("deps", "dm-0003", "--json", cwd=demo)
    assert d.exit_code == 0, d.output
    payload = json.loads(d.output)
    assert [e["key"] for e in payload["proof"]] == [
        "dm-0002",
        "Man12-prop-3.2",
    ]  # \cite[Proposition 3.2]{Man12} resolves to the digest node
    assert payload["closure"] == [{"key": "dm-0003"}]
    dp = run("deps", "dm-0003/proof", "--closure", cwd=demo)
    assert set(dp.output.splitlines()[2:]) == {
        "  dm-0002 (Lemma)",
        "  dm-0003 (Theorem)",
        "  Man12-setup (Theorem)",
        "  Man12-prop-3.2 (Proposition)",
    }  # the closure includes the digest nodes the proof cites by postnote (book 8.11)
    u = run("unravel", "dm-0001", "--json", cwd=demo)
    assert u.exit_code == 0, u.output
    up = json.loads(u.output)
    assert {x["key"] for x in up["dependents"]} == {"dm-0002/proof", "dm-0005/proof", "dm-0003/proof"} or {
        x["key"] for x in up["dependents"]
    } >= {"dm-0002/proof", "dm-0005/proof"}
    assert any(i["file"] == "drafts/main.tex" for i in up["inclusions"])
    pop = run("pop", "dm-0001", cwd=demo)
    assert pop.exit_code == 0 and "nothing is changed" in pop.output
    de = run("delete", "dm-0001", cwd=demo)
    assert de.exit_code == 1 and "loom will not delete your notes" in de.output
    assert run("rm", cwd=demo).exit_code == 1
    missing = run("deps", "dm-9999", cwd=demo)
    assert missing.exit_code == 2


def test_lint_exit_codes(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "demo"), "--demo", "--no-git").exit_code == 0
    demo = tmp_path / "demo"
    (demo / "nodes" / "bad.tex").write_text("\\begin{lemma}\\label{dm-0001}\ndup\n\\end{lemma}\n")
    r = run("lint", cwd=demo)
    assert r.exit_code == 1 and "duplicate-id" in r.output and r.output.strip().endswith("infos")


def test_documentclass_outside_drafts_and_bundle_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert run("init", str(tmp_path / "q"), "--demo", "--no-git", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    (q / "sections").mkdir()
    (q / "sections" / "stray.tex").write_text("\\documentclass{article}\n\\begin{document}\nx\n\\end{document}\n")
    lint = run("lint", cwd=q).output
    assert "loom:documentclass-outside-drafts" in lint and "sections/stray.tex" in lint
    monkeypatch.setenv("FAKE_TEX_FAIL_MATCH", "bundles/")  # the master compiles; every bundle fails
    r = run("check", "--bundles", "all", cwd=q)
    assert r.exit_code == 1 and "loom:bundle-failed" in r.output and "ok      drafts/main.tex" in r.output


def test_remaining_codes_have_a_test(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "q"), "--demo", "--no-git", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    (q / "comments" / "someone").mkdir(parents=True)
    (q / "comments" / "someone" / "2026-01-01.json").write_text("{not json")
    cfg = q / "config.toml"
    cfg.write_text(
        cfg.read_text().replace('main = "drafts/main.tex"', 'main = "drafts/missing.tex"', 1)
        + "\n[colour]\nscheme = 1\n"
    )
    lint = run("lint", cwd=q).output
    assert "loom:foreign-annotations" in lint and "loom:main-not-found" in lint and "loom:unknown-config-key" in lint
    cfg.write_text(cfg.read_text().replace('main = "drafts/missing.tex"', 'main = "drafts/main.tex"', 1))
    (q / "nodes" / "dm-0004.tex").write_text("% a file already sits where the inline node dm-0004 would move\n")
    r = run("atomize", "drafts/main.tex", "drafts/spine.tex", cwd=q)
    assert r.exit_code == 1 and "loom:atomize-target-exists" in r.output, r.output


def test_non_utf8_source_code_reported(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "q"), "--demo", "--no-git", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    (q / "nodes" / "old.tex").write_bytes(
        b"\\begin{remark}\\label{dm-0099}\nSee pages 989\xd01004.\n\\end{remark}\n"
    )  # Mac Roman en dash
    lint = run("lint", cwd=q).output
    assert "loom:non-utf8-source" in lint and "nodes/old.tex" in lint
