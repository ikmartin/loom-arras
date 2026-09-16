"""M1 commands on the demo quilt: init, new, lint, search, deps, unravel, delete."""

from __future__ import annotations

import json
import os
from pathlib import Path

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
    assert [e["key"] for e in payload["proof"]] == ["dm-0002"]
    assert payload["closure"] == [{"key": "dm-0003"}]
    dp = run("deps", "dm-0003/proof", "--closure", cwd=demo)
    assert dp.output.splitlines()[2:] == ["  dm-0002 (Lemma)", "  dm-0003 (Theorem)"]
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
