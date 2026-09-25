"""Fixture quilts: expected diagnostics, the demo equals `loom init --demo`, edge cases, and the author-file invariance property (book 4.8, 14.3, 14.7)."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from loom.scan.diagnostics import all_codes
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.helpers import describe, ok, run, same_tree

REPO = Path(__file__).resolve().parents[2]
QUILTS_DIR = REPO / "tests" / "quilts"
QUILTS = sorted(p for p in [*QUILTS_DIR.iterdir(), *(QUILTS_DIR / "edge").iterdir()] if (p / "config.toml").is_file())


def _copy(quilt: Path, tmp_path: Path) -> Path:
    dest = tmp_path / quilt.name
    shutil.copytree(quilt, dest)
    return dest


REGENERATE = "cd loom && uv run python scripts/gen_quilts.py"


def _tree(root: Path, skip: set[str]) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file() and p.name not in skip
    }


@pytest.mark.parametrize("quilt", QUILTS, ids=[q.name for q in QUILTS])
def test_lint_fixture_expected_codes(quilt: Path, tmp_path: Path) -> None:
    q = _copy(quilt, tmp_path)
    expected = (quilt / "EXPECTED-LINT.txt").read_text(encoding="utf-8").split()
    expected_lines = sorted(" ".join(pair) for pair in zip(expected[0::2], expected[1::2], strict=True))
    r = run("lint", "--json", cwd=q)
    got = sorted(f"{d['severity']} {d['code']}" for d in json.loads(r.stdout))
    assert got == expected_lines
    code = 1 if any(line.startswith("error") for line in got) else 0
    assert r.exit_code == code, f"expected exit {code}" + describe(("lint", "--json"), r)


def test_all_emitted_codes_are_known() -> None:
    known = set(all_codes())
    for quilt in QUILTS:
        for line in (quilt / "EXPECTED-LINT.txt").read_text(encoding="utf-8").splitlines():
            assert line.split()[1] in known, line


def test_init_demo_matches_fixture(tmp_path: Path) -> None:
    ok("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    fixture = QUILTS_DIR / "demo"
    # `.gitignore` is written from `assets/init/` and never from the demo's own copy: the fixture negates the store's
    # PDF so this repository can commit the invented paper behind the demo's digest, and a quilt an author makes must
    # not inherit that (DR-194, as amended).
    # `ai/ai-config.toml` is the person's own command, never the quilt's, and init writes it for whoever runs init.
    skip = {"EXPECTED-LINT.txt", ".gitignore", "ai-config.toml"}
    same_tree(
        _tree(tmp_path / "demo", skip), _tree(fixture, skip), "`loom init --demo` against tests/quilts/demo", REGENERATE
    )


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
        # the verdict is not this test's subject, only what the command leaves on disk; it differs by quilt and command (a lint with errors exits 1, `live` on a live master 2), and a crash raises out of `run`
        run(*cmd, cwd=q)
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
