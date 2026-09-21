"""Fixture quilts: expected diagnostics, the demo equals `loom init --demo`, edge cases, and the author-file invariance property (book 4.8, 14.3, 14.7)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.scan.diagnostics import all_codes
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

REPO = Path(__file__).resolve().parents[2]
QUILTS_DIR = REPO / "tests" / "quilts"
QUILTS = sorted(p for p in [*QUILTS_DIR.iterdir(), *(QUILTS_DIR / "edge").iterdir()] if (p / "config.toml").is_file())


def _copy(quilt: Path, tmp_path: Path) -> Path:
    dest = tmp_path / quilt.name
    shutil.copytree(quilt, dest)
    return dest


def _run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


@pytest.mark.parametrize("quilt", QUILTS, ids=[q.name for q in QUILTS])
def test_lint_fixture_expected_codes(quilt: Path, tmp_path: Path) -> None:
    q = _copy(quilt, tmp_path)
    expected = (quilt / "EXPECTED-LINT.txt").read_text(encoding="utf-8").split()
    expected_lines = sorted(" ".join(pair) for pair in zip(expected[0::2], expected[1::2], strict=True))
    r = _run("lint", "--json", cwd=q)
    got = sorted(f"{d['severity']} {d['code']}" for d in json.loads(r.output))
    assert got == expected_lines
    assert r.exit_code == (1 if any(line.startswith("error") for line in got) else 0)


def test_all_emitted_codes_are_known() -> None:
    known = set(all_codes())
    for quilt in QUILTS:
        for line in (quilt / "EXPECTED-LINT.txt").read_text(encoding="utf-8").splitlines():
            assert line.split()[1] in known, line


def test_init_demo_matches_fixture(tmp_path: Path) -> None:
    r = _run("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    assert r.exit_code == 0, r.output
    fixture = QUILTS_DIR / "demo"
    # `.gitignore` is written from `assets/init/` and never from the demo's own copy: the fixture negates the store's
    # PDF so this repository can commit the invented paper behind the demo's digest, and a quilt an author makes must
    # not inherit that (DR-194, as amended).
    skip = {"EXPECTED-LINT.txt", ".gitignore"}
    expected = {
        p.relative_to(fixture).as_posix(): p.read_bytes()
        for p in fixture.rglob("*")
        if p.is_file() and p.name not in skip
    }
    got = {
        p.relative_to(tmp_path / "demo").as_posix(): p.read_bytes()
        for p in (tmp_path / "demo").rglob("*")
        if p.is_file() and p.name not in skip
    }
    assert got == expected


def test_nested_nest_levels() -> None:
    r = scan(load_quilt(QUILTS_DIR / "edge" / "nested-nest"))
    levels = {k: n.level for k, n in r.nodes.items() if n.kind == "section"}
    assert levels == {"ed-0100": 1, "ed-0101": 2, "ed-0102": 3, "ed-0103": 1}
    assert r.nodes["ed-0102"].parent["drafting/main.tex"] == "ed-0101"
    assert r.nodes["ed-0101"].parent["drafting/main.tex"] == "ed-0100"
    assert r.nodes["ed-0001"].reached_by == ["drafting/main.tex"]


def test_begin_not_alone_tolerated() -> None:
    r = scan(load_quilt(QUILTS_DIR / "edge" / "begin-not-alone"))
    assert r.nodes["ed-0001"].proofs == ["ed-0001/proof"]
    assert r.nodes["ed-0002"].proofs == [] and r.nodes["ed-0002"].title == "T"
    unattached = [d for d in r.lint if d.code == "loom:unattached-proof"]
    assert len(unattached) == 1


def test_synthetic_structure() -> None:
    r = scan(load_quilt(QUILTS_DIR / "synthetic"))
    n = r.nodes
    assert n["sy-0300"].level == 2 and n["sy-0300"].parent["drafting/main.tex"] == "sy-0200"
    assert n["sy-0201"].parent["drafting/main.tex"] == "sy-0200"
    assert n["sy-0007"].proofs == ["sy-0007/proof"] and n["sy-0007/proof"].attach_via == "ref"
    assert n["sy-0003"].proofs == ["sy-0004", "sy-0005"]
    assert n["sy-0006"].proofs == ["sy-0006/proof", "sy-0006/proof/2"]
    assert n["sy-0008"].aliases == ["def:gadget", "defn:gadget-old"]
    assert set(n["sy-0002"].reached_by) == {"drafting/main.tex", "drafting/talk.tex"}
    assert n["sy-0009"].reached_by == []
    assert n["sy-000C/proof"].incomplete and n["sy-000C/proof"].directives == {}
    assert (
        n["sy-0202"].directives["author"] == "A Coauthor" and n["sy-0003"].directives["author"] == "The synthetic quilt"
    )
    assert n["sy-000B"].taxon == "Main Theorem"
    assert n["Kre99-thm-2.1"].digest == "Kre99" and n["Kre99-thm-2.1"].external
    assert "drafting/old.tex" not in n and r.files["drafting/old.tex"].ignored
    assert r.taxa["lemma"].style == "plain"


def _snapshot(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


@pytest.mark.parametrize("quilt", QUILTS, ids=[q.name for q in QUILTS])
def test_never_modifies_author_files(quilt: Path, tmp_path: Path) -> None:
    q = _copy(quilt, tmp_path)
    before = _snapshot(q)
    r = scan(load_quilt(q))
    key = next((k for k, n in r.nodes.items() if n.kind == "environment"), None)
    env = next(iter(r.taxa), None)
    master = r.default_master
    canon = next(iter(r.canon_files), None)
    drafting = r.quilt.config.drafting
    commands: list[list[str]] = [
        ["lint"],
        ["lint", "--json"],
        ["lint", "--nodes"],
        ["search", "a"],
        ["search", "a", "--json"],
        ["delete", "x"],
        ["doctor"],
        ["history"],
        ["history", "verify"],
        ["stamp", "-m", "written by the invariance test"],
    ]
    if key:
        commands += [
            ["deps", key],
            ["deps", key, "--closure", "--json"],
            ["unravel", key],
            ["unravel", key, "--json"],
            ["history", key],
            ["revert", f"{key}@1"],
            ["fork", key, "--in", master or "nothing.tex"],
        ]
    if env:
        commands += [["new", env, "--print"], ["new", env, "Written by the invariance test"]]
    if master:
        commands += [
            ["canonize", master, "--to", "canon/invariance.tex", "-m", "written by the invariance test"],
            ["linearize", master, "--to", f"{drafting}/invariance-flat.tex", "--no-check"],
            ["live", master],
        ]
    if canon:
        commands += [["draft", canon, "--to", f"{drafting}/invariance-draft.tex", "--yes", "--no-check"]]
    for cmd in commands:
        res = _run(*cmd, cwd=q)
        assert res.exit_code in (0, 1, 2), (cmd, res.output)
    after = _snapshot(q)
    for rel, digest in before.items():
        if rel == "config.toml" or rel.startswith(".loom/"):
            continue  # loom's own files, checked below: [quilt] main may move, and the ledgers are appended to
        assert after.get(rel) == digest, f"{rel} was modified or deleted by a command"
    was = (quilt / "config.toml").read_text(encoding="utf-8").splitlines()
    now = (q / "config.toml").read_text(encoding="utf-8").splitlines()
    assert [ln for ln in was if not ln.startswith("main")] == [ln for ln in now if not ln.startswith("main")], (
        "config.toml changed in something other than [quilt] main"
    )
    ledger = ".loom/history/ledger.jsonl"
    if ledger in before:
        old = (quilt / ledger).read_text(encoding="utf-8")
        assert (q / ledger).read_text(encoding="utf-8").startswith(old), "the history ledger is append-only"
    new_files = set(after) - set(before)
    # everything loom writes goes into nodes/, the drafting directory it was told to write in, the canon it was told to write, or its own record
    allowed = ("nodes/", f"{drafting}/", "canon/", ".loom/")
    assert all(rel.startswith(allowed) for rel in new_files), new_files


def test_two_masters_share_one_set_of_nodes(tmp_path: Path) -> None:
    """Several masters are arrangements over one set of patches: including the same node file twice is not a duplicate (book 4.1)."""
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    q = tmp_path / "q"
    dest = q / "drafting"
    dest.mkdir(parents=True)
    (q / "nodes").mkdir()
    (q / "config.toml").write_text('[quilt]\nname = "q"\nmain = "drafting/main.tex"\nprefix = "sh"\n', encoding="utf-8")
    (q / "loom.sty").write_text(
        (REPO / "src" / "loom" / "assets" / "loom.sty").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (q / "nodes" / "sh-0001.tex").write_text(
        "\\begin{lemma}\\label{sh-0001}\nShared.\n\\end{lemma}\n", encoding="utf-8"
    )
    preamble = (
        "\\documentclass{amsart}\n\\usepackage{amsthm}\n\\usepackage{loom}\n"
        "\\newtheorem{lemma}{Lemma}[section]\n\\begin{document}\n"
    )
    (dest / "main.tex").write_text(
        preamble + "\\section{One}\\label{sh-0100}\n\\input{nodes/sh-0001}\n\\end{document}\n", encoding="utf-8"
    )
    (dest / "talk.tex").write_text(
        preamble + "\\section{Two}\\label{sh-0200}\n\\input{nodes/sh-0001}\n\\end{document}\n", encoding="utf-8"
    )
    result = scan(load_quilt(q))
    codes = [d.code for d in result.lint]
    assert "duplicate-id" not in codes and "loom:duplicate-label" not in codes
    assert set(result.nodes["sh-0001"].reached_by) == {"drafting/main.tex", "drafting/talk.tex"}
