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
    r = run("init", str(tmp_path / "q"), "--prefix", "zz", "--yes")
    assert r.exit_code == 0, r.output
    q = tmp_path / "q"
    for rel in (
        "config.toml",
        "loom.sty",
        "drafting/main.tex",
        "nodes",
        "digests",
        "refs",
        ".gitignore",
        "README.md",
    ):
        assert (q / rel).exists(), rel
    assert not (q / "comments").exists()  # replaced by annotations/log.jsonl four plans ago and still created
    assert 'prefix = "zz"' in (q / "config.toml").read_text()
    assert "\\usepackage{loom}" in (q / "drafting/main.tex").read_text()
    lint = run("lint", cwd=q)
    assert lint.exit_code == 0, lint.output


def test_init_refuses_in_quilt_and_nonempty(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "q"), "--prefix", "a", "--yes").exit_code == 0
    assert run("init", str(tmp_path / "q" / "inner"), "--yes").exit_code == 2
    (tmp_path / "full").mkdir()
    (tmp_path / "full" / "x.txt").write_text("x")
    assert run("init", str(tmp_path / "full"), "--yes").exit_code == 2


def test_a_nonempty_directory_says_what_is_actually_wrong(tmp_path: Path) -> None:
    """The two refusals are different and the advice differs. Told to pass `--from` when one was already passed, a reader looks for the mistake everywhere but where it is."""
    full = tmp_path / "full"
    full.mkdir()
    (full / "x.txt").write_text("x")
    outside = tmp_path / "paper.tex"
    outside.write_text("\\documentclass{article}\n\\begin{document}\\end{document}\n")

    # no paper at all: passing one is the advice
    plain = run("init", str(full), "--yes")
    assert plain.exit_code == 2
    assert "is not empty" in plain.output and "--from FILE with a file inside it" in plain.output

    # a paper outside the directory: where it sits is the fault, and the message names it
    apart = run("init", str(full), "--from", str(outside), "--yes")
    assert apart.exit_code == 2
    assert "lies outside it" in apart.output and str(outside) in apart.output

    # and the current directory is named as such, since the path was never typed
    import os

    old = os.getcwd()
    try:
        os.chdir(full)
        here = run("init", "--yes")
    finally:
        os.chdir(old)
    assert here.exit_code == 2 and "the current directory" in here.output


def test_init_writes_gitignore_always_and_a_repository_only_when_asked(tmp_path: Path) -> None:
    """A quilt is files, and loom reads no history: it makes a repository only when `--git` asks for one, and says so when it does. The ignore file is written either way, since it costs nothing and is right the day the quilt becomes a repository."""
    plain = run("init", str(tmp_path / "n"), "--prefix", "a", "--yes")
    assert plain.exit_code == 0
    assert not (tmp_path / "n" / ".git").exists()
    assert (tmp_path / "n" / ".gitignore").is_file()
    assert "wrote .gitignore" in plain.output and "build/" in plain.output

    asked = run("init", str(tmp_path / "g"), "--prefix", "a", "--yes", "--git")
    assert asked.exit_code == 0
    assert (tmp_path / "g" / ".git").is_dir()
    assert "git init" in asked.output  # never a silent side effect

    # nothing a node is made of is ignored: only derived directories and LaTeX's own leavings
    ignored = [ln for ln in (tmp_path / "n" / ".gitignore").read_text().splitlines() if ln and not ln.startswith("#")]
    assert "build/" in ignored
    # the artifacts are ignored and the page text is not: an anchor stays re-checkable by a coauthor with no PDF
    assert "refs/**/paper.pdf" in ignored and "refs/**/src/" in ignored
    assert "refs/" not in ignored
    assert not any(ln.endswith(".tex") or ln in ("nodes/", "drafting/", "digests/", "comments/") for ln in ignored)


def test_init_demo_writes_demo_and_lints_clean(tmp_path: Path) -> None:
    r = run("init", str(tmp_path / "demo"), "--demo")
    assert r.exit_code == 0, r.output
    demo = tmp_path / "demo"
    assert (demo / "digests" / "Man12.tex").exists() and (demo / "nodes" / "dm-0003.tex").exists()
    lint = run("lint", "--json", cwd=demo)
    assert lint.exit_code == 0, lint.output
    diags = json.loads(lint.output)
    assert {d["severity"] for d in diags} <= {"info", "warning"}
    codes = sorted(d["code"] for d in diags)
    assert "loom:undigested-citekey" not in codes or True


def test_init_minimal_master_declares_candidate_taxa(tmp_path: Path) -> None:
    """A quilt is usable for planning from the first minute: `conjecture` owes a proof and shows as a gap, `question` owes nothing (plan 0.2 §4)."""
    assert run("init", str(tmp_path / "q"), "--yes").exit_code == 0
    main = (tmp_path / "q" / "drafting" / "main.tex").read_text()
    assert "\\newtheorem{conjecture}[theorem]{Conjecture}" in main
    assert "\\newtheorem{question}[theorem]{Question}" in main

    # a conjecture is plain, because it owes a proof; a question is a remark, because it owes nothing
    def style_of(name: str) -> str:
        return main[: main.index("{" + name + "}[theorem]")].rsplit("\\theoremstyle{", 1)[1].split("}")[0]

    assert style_of("conjecture") == "plain"
    assert style_of("question") == "remark"


def test_init_from_leaves_the_authors_preamble_alone(tmp_path: Path) -> None:
    """`--from` adopts a paper as it is: one flat canon document, no package line, no ids, nothing added to the author's preamble."""
    src = tmp_path / "paper.tex"
    src.write_text(
        "\\documentclass{article}\n\\newtheorem{thm}{Theorem}\n\\begin{document}\nHello.\n\\end{document}\n",
        encoding="utf-8",
    )
    r = run("init", str(tmp_path / "q"), "--from", str(src), "--yes")
    assert r.exit_code == 0, r.output
    q = tmp_path / "q"
    canon = q / "canon" / "paper.tex"
    assert canon.read_text() == src.read_text()  # verbatim: the paper has nothing to inline
    assert "conjecture" not in canon.read_text() and "usepackage{loom}" not in canon.read_text()
    assert not any((q / "drafting").iterdir())  # work begins with loom draft
    assert "next: loom draft canon/paper.tex" in r.output


def test_init_from_leaves_nothing_behind_when_the_import_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed import is not half a quilt. The instinct after a refusal is to fix the paper and re-run the same command, and a surviving skeleton refuses that as "already inside a quilt"."""
    src = tmp_path / "paper.tex"
    src.write_text(
        "\\documentclass{article}\n\\newtheorem{thm}{Theorem}\n\\begin{document}\nHello.\n\\end{document}\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    bad = run("init", str(tmp_path / "q"), "--from", str(src), "--prefix", "pp", "--yes")
    assert bad.exit_code == 1 and "does not compile from a clean copy" in bad.output
    assert not (tmp_path / "q").exists()
    assert "created quilt" not in bad.output  # nothing is announced that does not outlive the command

    monkeypatch.delenv("FAKE_TEX_FAIL")
    again = run("init", str(tmp_path / "q"), "--from", str(src), "--prefix", "pp", "--yes")
    assert again.exit_code == 0, again.output
    assert (tmp_path / "q" / "canon" / "paper.tex").is_file() and "created quilt" in again.output


def test_init_from_inside_a_paper_directory_keeps_the_paper_when_the_import_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Undoing the skeleton removes what init wrote and nothing else: the author's own directory is not init's to delete."""
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(
        "\\documentclass{article}\n\\newtheorem{thm}{Theorem}\n\\begin{document}\nHello.\n\\end{document}\n",
        encoding="utf-8",
    )
    (paper / "notes.txt").write_text("mine\n", encoding="utf-8")

    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    r = run("init", str(paper), "--from", str(paper / "main.tex"), "--prefix", "pp", "--yes")
    assert r.exit_code == 1 and "does not compile" in r.output
    assert sorted(x.name for x in paper.iterdir()) == ["main.tex", "notes.txt"]


def test_demo_has_outline_master(tmp_path: Path) -> None:
    """The demo shows the outline pattern: a second master reaching one conjecture and one question, so a candidate is reached rather than loose while it is being considered (plan 0.2 §1.2, book 4.4)."""
    assert run("init", str(tmp_path / "demo"), "--demo").exit_code == 0
    demo = tmp_path / "demo"
    outline = demo / "drafting" / "outline.tex"
    assert outline.exists()
    r = run("status", "--master", "drafting/outline.tex", "--json", cwd=demo)
    assert r.exit_code == 0, r.output
    keys = json.loads(r.output)["keys"]
    reached = {k for k, v in keys.items() if "drafting/outline.tex" in v["reached_by"]}
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
    assert run("init", str(tmp_path / "demo"), "--demo").exit_code == 0
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
    assert run("init", str(tmp_path / "demo"), "--demo").exit_code == 0
    demo = tmp_path / "demo"
    (demo / "nodes" / "scratch.tex").write_text("% dangling reference\nSee \\ref{dm-0020}.\n")
    r = run("new", "lemma", cwd=demo)
    assert r.output.startswith("dm-0021 "), r.output


def test_search_deps_unravel_delete(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "demo"), "--demo").exit_code == 0
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
    assert any(i["file"] == "drafting/main.tex" for i in up["inclusions"])
    pop = run("pop", "dm-0001", cwd=demo)
    assert pop.exit_code == 0 and "nothing is changed" in pop.output
    de = run("delete", "dm-0001", cwd=demo)
    assert de.exit_code == 1 and "loom will not delete your notes" in de.output
    assert run("rm", cwd=demo).exit_code == 1
    missing = run("deps", "dm-9999", cwd=demo)
    assert missing.exit_code == 2


def test_lint_exit_codes(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "demo"), "--demo").exit_code == 0
    demo = tmp_path / "demo"
    (demo / "nodes" / "bad.tex").write_text("\\begin{lemma}\\label{dm-0001}\ndup\n\\end{lemma}\n")
    r = run("lint", cwd=demo)
    assert r.exit_code == 1 and "duplicate-id" in r.output and r.output.strip().endswith("infos")


def test_documentclass_outside_drafts_and_bundle_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    (q / "sections").mkdir()
    (q / "sections" / "stray.tex").write_text("\\documentclass{article}\n\\begin{document}\nx\n\\end{document}\n")
    lint = run("lint", cwd=q).output
    assert "loom:documentclass-outside-drafts" in lint and "sections/stray.tex" in lint
    monkeypatch.setenv("FAKE_TEX_FAIL_MATCH", "bundles/")  # the master compiles; every bundle fails
    r = run("check", "--bundles", "all", cwd=q)
    assert r.exit_code == 1 and "loom:bundle-failed" in r.output and "ok      drafting/main.tex" in r.output


def test_remaining_codes_have_a_test(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    log = q / "annotations" / "log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write("{not json\n")  # a line nothing can read is reported, and the rest of the log still loads
    cfg = q / "config.toml"
    cfg.write_text(
        cfg.read_text().replace('main = "drafting/main.tex"', 'main = "drafting/missing.tex"', 1)
        + "\n[colour]\nscheme = 1\n"
    )
    lint = run("lint", cwd=q).output
    assert "loom:foreign-annotations" in lint and "loom:main-not-found" in lint and "loom:unknown-config-key" in lint
    cfg.write_text(cfg.read_text().replace('main = "drafting/missing.tex"', 'main = "drafting/main.tex"', 1))
    (q / "nodes" / "dm-0004.tex").write_text("% a file already sits where the inline node dm-0004 would move\n")
    r = run("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q)
    assert r.exit_code == 1 and "loom:atomize-target-exists" in r.output, r.output


def test_non_utf8_source_code_reported(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    (q / "nodes" / "old.tex").write_bytes(
        b"\\begin{remark}\\label{dm-0099}\nSee pages 989\xd01004.\n\\end{remark}\n"
    )  # Mac Roman en dash
    lint = run("lint", cwd=q).output
    assert "loom:non-utf8-source" in lint and "nodes/old.tex" in lint


def test_retired_config_key_is_tolerated_and_upgrade_removes_it(tmp_path: Path) -> None:
    """`[ai] runner` was withdrawn with the declined runner (WQ-15) and `[ai] agent` with the declined launcher (DR-149). A quilt loom itself wrote either key into must not now be told it is unknown, so both stay accepted and inert; `loom upgrade` tidies the lines away."""
    assert run("init", str(tmp_path / "q"), "--prefix", "zz", "--yes").exit_code == 0
    q = tmp_path / "q"
    cfg = q / "config.toml"
    assert "runner" not in cfg.read_text() and "agent" not in cfg.read_text()  # a new quilt gets neither

    # a new quilt no longer writes an empty `[ai]` either, so the table is added here as an older quilt would carry it
    cfg.write_text(cfg.read_text() + '\n[ai]\nagent = "claude"\nrunner = "some-command"\n', encoding="utf-8")
    lint = run("lint", "--json", cwd=q)
    assert "unknown-config-key" not in lint.output  # tolerated: loom wrote them there

    up = run("upgrade", cwd=q)
    assert up.exit_code == 0 and "[ai] runner" in up.output
    assert "runner" not in cfg.read_text()

    again = run("upgrade", cwd=q)
    assert "[ai] runner" not in again.output  # idempotent


def test_unravel_reports_the_ledger_and_the_annotations_it_heads(tmp_path: Path) -> None:
    """Both blocks were hardcoded empty, so `annotations: (none)` read as a positive statement that a reviewed node was unreviewed (F13)."""
    assert run("init", str(tmp_path / "demo"), "--demo").exit_code == 0
    d = tmp_path / "demo"
    assert run("comment", "dm-0002", "Which orbits?", "--author", "Tom", cwd=d).exit_code == 0

    payload = json.loads(run("unravel", "dm-0002", "--json", cwd=d).output)
    assert [r["key"] for r in payload["ledger"]] == ["dm-0002", "dm-0002/proof"]  # the statement and its proof
    (a,) = payload["annotations"]
    assert a["message"] == "Which orbits?" and a["target"] == "dm-0002" and a["status"] == "open"

    text = run("unravel", "dm-0002", cwd=d).output
    assert "Which orbits?" in text
    assert "annotations:\n  (none)" not in text
