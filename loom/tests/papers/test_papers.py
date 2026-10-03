"""Paper tier (book 14.2): the two arXiv conversion fixtures go through import, atomize, a landmark stamp, and the identity test with the real toolchain. Gated by LOOM_PAPER_FIXTURES, a directory holding 0805.2065/ (Manolache, virtual6.tex) and 1709.09864/ (ACGS, decomposition-formula.tex); every test copies the sources so nothing outside the copy is read or written."""

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


def rejoined(text: str) -> str:
    """What a command said, its lines rejoined: the report wraps a long verdict at 100 columns."""
    return " ".join(text.split())


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
    """Manolache imported with init --from --fix-anchoring, made once: the paper as received kept as a landmark and the working document drafted. Read only; the copied sources, the quilt, and what init said."""

    def make(base: Path) -> tuple[Path, Path, str]:
        paper = copy_fixture(base, "0805.2065")
        r = ok(
            "init",
            str(base / "q"),
            "--from",
            str(paper / "virtual6.tex"),
            "--prefix",
            "man",
            "--fix-anchoring",
            "--yes",
            cwd=base,
        )
        return paper, base / "q", r.output

    return once.get("manolache", make)


def manolache_atomized(once: Once) -> tuple[Path, str]:
    """The imported Manolache atomized by sections into drafting/main-atomic.tex, made once. Read only; the quilt and what atomize said."""

    def make(base: Path) -> tuple[Path, str]:
        q = copy(manolache(once)[1], base / "q")
        r = ok("atomize", "drafting/virtual6.tex", "drafting/main-atomic.tex", "--sections", cwd=q)
        return q, r.output

    return once.get("manolache-atomized", make)


def acgs(once: Once) -> tuple[Path, str]:
    """ACGS with its documented edits, imported with --fix-anchoring, made once. Read only; the quilt and what init said."""

    def make(base: Path) -> tuple[Path, str]:
        paper = copy_fixture(base, "1709.09864")
        for rel, old, new, _why in ACGS_EDITS:
            f = paper / rel
            assert old in f.read_text(), (rel, old)
            f.write_text(f.read_text().replace(old, new, 1))
        q = base / "q"
        i = ok(
            "init",
            str(q),
            "--from",
            str(paper / "decomposition-formula.tex"),
            "--prefix",
            "acgs",
            "--fix-anchoring",
            "--yes",
            cwd=base,
        )
        return q, i.output

    return once.get("acgs", make)


def test_paper_manolache_import_is_a_verbatim_landmark(once: Once) -> None:
    """The paper as received is the landmark of step 0001: the flat text, which typesets as the original and carries nothing loom added."""
    paper, q, said = manolache(once)
    assert "typesets to the same text as the original" in rejoined(said), said
    received = (q / ".loom" / "history" / "0001-virtual6" / "virtual6.tex").read_text()
    assert received == (paper / "virtual6.tex").read_text()  # one file to begin with, so the flat text is the paper
    assert "\\usepackage{loom}" not in received and "\\label{man-" not in received
    ledger = [json.loads(x) for x in (q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()]
    assert len(ledger) == 1 and ledger[0]["action"] == "import" and ledger[0]["step"] == 1
    assert ledger[0]["drafted"]["path"] == "drafting/virtual6.tex"


def test_paper_manolache_import_refuses_anchoring_and_labels_the_working_document(once: Once, tmp_path: Path) -> None:
    paper = copy_fixture(tmp_path, "0805.2065")
    refused(
        "init",
        str(tmp_path / "q"),
        "--from",
        str(paper / "virtual6.tex"),
        "--prefix",
        "man",
        "--yes",
        cwd=tmp_path,
        code=1,
        match="51 line-anchoring violations",
    )
    assert not (tmp_path / "q").exists()
    _, q, said = manolache(once)
    assert "5 by enclosure, 0 unattached" in said and "never defines" not in said, said
    text = (q / "drafting" / "virtual6.tex").read_text()
    assert (
        text.count("\\label{man-") == 96 + 16
    )  # 96 theorem-like environments and 16 headings through subsubsection (paragraphs are not labelled by default)
    lint = run("lint", cwd=copy(q, tmp_path / "drafted")).output
    assert "dangling-link" not in lint and "unattached-proof" not in lint


def test_paper_manolache_atomize_sections(once: Once, tmp_path: Path) -> None:
    q, said = manolache_atomized(once)
    assert "typesets to the same text as drafting/virtual6.tex" in rejoined(said), said
    files = {f.name for f in (q / "nodes").glob("*.tex")}
    assert len(files) >= 96 and "man-0002.tex" in files  # the Preliminaries section moved too
    spine = (q / "drafting" / "main-atomic.tex").read_text()
    assert "\\begin{theorem}" not in spine and spine.count("\\input{nodes/") >= 5

    # the spine superseded the source, so every node is defined once although two files hold its text
    line = json.loads((q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()[-1])
    assert line["action"] == "atomize" and line["superseded"] == ["drafting/virtual6.tex"]
    diags = json.loads(run("lint", "--json", cwd=copy(q, tmp_path / "q")).stdout)["diagnostics"]
    assert [d["code"] for d in diags if d["code"] == "loom:superseded-file"] == ["loom:superseded-file"]
    assert not [d for d in diags if d["code"] == "duplicate-id"]


def test_paper_manolache_landmark_shown_plain_is_self_contained(once: Once, tmp_path: Path) -> None:
    """A landmark of an atomized paper, shown `--plain`, compiles in a directory holding nothing but itself and the figures."""
    q = copy(manolache_atomized(once)[0], tmp_path / "q")
    ok("stamp", "drafting/main-atomic.tex", "-m", "virtual6-v1", cwd=q)
    step = json.loads((q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()[-1])
    statements = [k for k in step["froze"] if "/proof" not in k]
    assert len(statements) >= 96, len(statements)
    alone = tmp_path / "alone"
    alone.mkdir()
    (alone / "virtual6-v1.tex").write_text(
        ok("history", "show", "virtual6-v1", "--plain", cwd=q).stdout, encoding="utf-8"
    )
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
    q, imported = acgs(once)
    assert "typesets to the same text as the original" in rejoined(imported), imported
    assert any(q.rglob("*.pspdftex"))  # the closure brought the figures, which are not .tex and stay as inclusions
    assert "never defines" not in imported, imported


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
