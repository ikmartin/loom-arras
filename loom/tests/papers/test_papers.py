"""Paper tier (book 14.2): the two arXiv conversion fixtures go through import, draft, atomize, canonize, and the identity test with the real toolchain. Gated by LOOM_PAPER_FIXTURES, a directory holding 0805.2065/ (Manolache, virtual6.tex) and 1709.09864/ (ACGS, decomposition-formula.tex); every test copies the sources so nothing outside the copy is read or written."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import tracemalloc
from pathlib import Path

import pytest

from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.helpers import Once, copy, ok, refused, run

pytestmark = [pytest.mark.paper, pytest.mark.tex]

# Hand edits the ACGS source needs before the identity test passes, each with the reason; the same list is in tests/fixtures/NOTES.md. Empty means none were needed.
ACGS_EDITS: list[tuple[str, str, str, str]] = []


def fixtures() -> Path:
    root = os.environ.get("LOOM_PAPER_FIXTURES")
    if not root:
        pytest.skip("LOOM_PAPER_FIXTURES is not set")
    return Path(root)


def copy_fixture(tmp_path: Path, name: str) -> Path:
    src = fixtures() / name
    if not src.is_dir():
        pytest.skip(f"{src} is missing")
    dest = tmp_path / name
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("*.gz", "build", "out"))
    return dest


@pytest.fixture(scope="module")
def once(tmp_path_factory: pytest.TempPathFactory) -> Once:
    return Once(tmp_path_factory)


def manolache(once: Once) -> tuple[Path, Path, str]:
    """Manolache imported with init --from, made once. Read only; the copied sources, the quilt, and what init said."""

    def make(base: Path) -> tuple[Path, Path, str]:
        paper = copy_fixture(base, "0805.2065")
        r = ok("init", str(base / "q"), "--from", str(paper / "virtual6.tex"), "--prefix", "man", "--yes", cwd=base)
        return paper, base / "q", r.output

    return once.get("manolache", make)


def manolache_drafted(once: Once) -> tuple[Path, str]:
    """The imported Manolache drafted with --fix-anchoring, made once. Read only; the quilt and what draft said."""

    def make(base: Path) -> tuple[Path, str]:
        q = copy(manolache(once)[1], base / "q")
        d = ok("draft", "canon/virtual6.tex", "--to", "drafting/main.tex", "--yes", "--fix-anchoring", cwd=q)
        return q, d.output

    return once.get("manolache-drafted", make)


def manolache_atomized(once: Once) -> tuple[Path, str]:
    """The drafted Manolache atomized by sections into drafting/main-atomic.tex, made once. Read only; the quilt and what atomize said."""

    def make(base: Path) -> tuple[Path, str]:
        q = copy(manolache_drafted(once)[0], base / "q")
        r = ok("atomize", "drafting/main.tex", "drafting/main-atomic.tex", "--sections", cwd=q)
        return q, r.output

    return once.get("manolache-atomized", make)


def acgs(once: Once) -> tuple[Path, str, str]:
    """ACGS with its documented edits, imported and drafted with --fix-anchoring, made once. Read only; the quilt and what init and draft said."""

    def make(base: Path) -> tuple[Path, str, str]:
        paper = copy_fixture(base, "1709.09864")
        for rel, old, new, _why in ACGS_EDITS:
            f = paper / rel
            assert old in f.read_text(), (rel, old)
            f.write_text(f.read_text().replace(old, new, 1))
        q = base / "q"
        i = ok(
            "init", str(q), "--from", str(paper / "decomposition-formula.tex"), "--prefix", "acgs", "--yes", cwd=base
        )
        d = ok(
            "draft", "canon/decomposition-formula.tex", "--to", "drafting/main.tex", "--yes", "--fix-anchoring", cwd=q
        )
        return q, i.output, d.output

    return once.get("acgs", make)


def test_paper_manolache_import_is_a_verbatim_landmark(once: Once) -> None:
    """The paper arrives as one flat canon document that typesets as the original and carries nothing loom added."""
    paper, q, said = manolache(once)
    assert "Identity test: pass" in said, said
    canon = (q / "canon" / "virtual6.tex").read_text()
    assert canon == (paper / "virtual6.tex").read_text()  # one file to begin with, so the flat copy is the paper
    assert "\\usepackage{loom}" not in canon and "\\label{man-" not in canon
    assert not list((q / "drafting").iterdir())  # work begins with loom draft
    ledger = [json.loads(x) for x in (q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()]
    assert len(ledger) == 1 and ledger[0]["action"] == "import" and ledger[0]["step"] == 1


def test_paper_manolache_draft_labels_the_working_copy(once: Once, tmp_path: Path) -> None:
    q = copy(manolache(once)[1], tmp_path / "imported")
    refused(
        "draft",
        "canon/virtual6.tex",
        "--to",
        "drafting/main.tex",
        "--yes",
        cwd=q,
        code=1,
        match="51 line-anchoring violation(s)",
    )
    assert not (q / "drafting" / "main.tex").exists()
    drafted, out = manolache_drafted(once)
    assert "Identity test: pass" in out, out
    assert "5 by enclosure, 0 unattached" in out and "0 dangling" in out, out
    text = (drafted / "drafting" / "main.tex").read_text()
    assert (
        text.count("\\label{man-") == 96 + 16
    )  # 96 theorem-like environments and 16 headings through subsubsection (paragraphs are not labelled by default)
    lint = run("lint", cwd=copy(drafted, tmp_path / "drafted")).output
    assert "dangling-link" not in lint and "unattached-proof" not in lint


def test_paper_manolache_atomize_sections(once: Once, tmp_path: Path) -> None:
    q, said = manolache_atomized(once)
    assert "Identity test: pass" in said, said
    files = {f.name for f in (q / "nodes").glob("*.tex")}
    assert len(files) >= 96 and "man-0002.tex" in files  # the Preliminaries section moved too
    spine = (q / "drafting" / "main-atomic.tex").read_text()
    assert "\\begin{theorem}" not in spine and spine.count("\\input{nodes/") >= 5

    # the spine superseded the source, so every node is defined once although two files hold its text
    line = json.loads((q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()[-1])
    assert line["action"] == "atomize" and line["superseded"] == ["drafting/main.tex"]
    diags = json.loads(run("lint", "--json", cwd=copy(q, tmp_path / "q")).stdout)
    assert [d["code"] for d in diags if d["code"] == "loom:superseded-file"] == ["loom:superseded-file"]
    assert not [d for d in diags if d["code"] == "duplicate-id"]


def test_paper_manolache_canonize_is_self_contained(once: Once, tmp_path: Path) -> None:
    """A landmark of an atomized paper compiles in a directory holding nothing but itself and the figures."""
    q = copy(manolache_atomized(once)[0], tmp_path / "q")
    r = ok("canonize", "drafting/main-atomic.tex", "--to", "canon/virtual6-v1.tex", "-m", "Atomized", cwd=q)
    assert "Identity test: pass" in r.output
    step = json.loads((q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()[-1])
    statements = [k for k in step["froze"] if "/proof" not in k]
    assert len(statements) >= 96, len(statements)
    alone = tmp_path / "alone"
    alone.mkdir()
    shutil.copy(q / "canon" / "virtual6-v1.tex", alone / "virtual6-v1.tex")
    for extra in list(q.glob("*.sty")) + list(q.glob("*.bib")) + list(q.glob("*.bst")):
        shutil.copy(extra, alone / extra.name)
    proc = subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "virtual6-v1.tex"],
        cwd=alone,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (alone / "virtual6-v1.pdf").is_file(), proc.stdout[-3000:]


def test_paper_acgs_import_with_documented_edits(once: Once) -> None:
    q, imported, drafted = acgs(once)
    assert "Identity test: pass" in imported, imported
    assert any(q.rglob("*.pspdftex"))  # the closure brought the figures, which are not .tex and stay as inclusions
    assert "Identity test: pass" in drafted and "0 dangling" in drafted, drafted


def test_paper_acgs_scan_time_and_memory(once: Once, tmp_path: Path) -> None:
    quilt = load_quilt(copy(acgs(once)[0], tmp_path / "q"))
    tracemalloc.start()
    t0 = time.perf_counter()
    result = scan(quilt)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(result.assembly.nodes) > 100
    assert elapsed < 10.0, elapsed  # measured 2026-09-15: see docs/demonstrations/M4.md for the numbers
    assert peak < 300 * 1024 * 1024, peak
