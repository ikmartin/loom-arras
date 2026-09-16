"""Paper tier (book 14.2): the two arXiv conversion fixtures go through import, atomize, and the identity test with the real toolchain. Gated by LOOM_PAPER_FIXTURES, a directory holding 0805.2065/ (Manolache, virtual6.tex) and 1709.09864/ (ACGS, decomposition-formula.tex); every test copies the sources so nothing outside the copy is read or written."""

from __future__ import annotations

import os
import shutil
import time
import tracemalloc
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

pytestmark = [pytest.mark.paper, pytest.mark.tex]

# Hand edits the ACGS source needs before the identity test passes, each with the reason; the same list is in tests/fixtures/NOTES.md. Empty means none were needed.
ACGS_EDITS: list[tuple[str, str, str, str]] = []


def fixtures() -> Path:
    root = os.environ.get("LOOM_PAPER_FIXTURES")
    if not root:
        pytest.skip("LOOM_PAPER_FIXTURES is not set")
    return Path(root)


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def copy_fixture(tmp_path: Path, name: str) -> Path:
    src = fixtures() / name
    if not src.is_dir():
        pytest.skip(f"{src} is missing")
    dest = tmp_path / name
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("*.gz", "build", "out"))
    return dest


def import_paper(tmp_path: Path, name: str, master: str, prefix: str, *flags: str) -> tuple[Path, str]:
    paper = copy_fixture(tmp_path, name)
    q = tmp_path / "q"
    r = run("init", str(q), "--from", str(paper / master), "--prefix", prefix, "--yes", *flags, cwd=tmp_path)
    assert r.exit_code == 0, r.output[-3000:]
    return q, r.output


def test_paper_manolache_import(tmp_path: Path) -> None:
    paper = copy_fixture(tmp_path, "0805.2065")
    refused = run(
        "init",
        str(tmp_path / "q0"),
        "--from",
        str(paper / "virtual6.tex"),
        "--prefix",
        "man",
        "--yes",
        cwd=tmp_path,
    )
    assert refused.exit_code == 1 and "51 line-anchoring violation(s)" in refused.output
    shutil.rmtree(tmp_path / "q0")
    q = tmp_path / "q"
    r = run(
        "init",
        str(q),
        "--from",
        str(paper / "virtual6.tex"),
        "--prefix",
        "man",
        "--yes",
        "--fix-anchoring",
        cwd=tmp_path,
    )
    assert r.exit_code == 0, r.output[-3000:]
    out = r.output
    assert "Identity test: pass" in out
    assert "5 by enclosure, 0 unattached" in out and "0 dangling" in out
    text = (q / "drafts" / "virtual6.tex").read_text()
    assert (
        text.count("\\label{man-") == 96 + 16
    )  # 96 theorem-like environments and 16 headings through subsubsection (paragraphs are not labelled by default)
    lint = run("lint", cwd=q).output
    assert "dangling-link" not in lint and "unattached-proof" not in lint


def test_paper_manolache_atomize_sections(tmp_path: Path) -> None:
    q, _ = import_paper(tmp_path, "0805.2065", "virtual6.tex", "man", "--fix-anchoring")
    r = run("atomize", "drafts/virtual6.tex", "drafts/virtual6-atomized.tex", "--sections", cwd=q)
    assert r.exit_code == 0, r.output[-3000:]
    assert "Identity test: pass" in r.output
    files = {f.name for f in (q / "nodes").glob("*.tex")}
    assert len(files) >= 96 and "man-0002.tex" in files  # the Preliminaries section moved too
    spine = (q / "drafts" / "virtual6-atomized.tex").read_text()
    assert "\\begin{theorem}" not in spine and spine.count("\\input{nodes/") >= 5


def test_paper_acgs_import_with_documented_edits(tmp_path: Path) -> None:
    paper = copy_fixture(tmp_path, "1709.09864")
    for rel, old, new, _why in ACGS_EDITS:
        f = paper / rel
        assert old in f.read_text(), (rel, old)
        f.write_text(f.read_text().replace(old, new, 1))
    q = tmp_path / "q"
    r = run(
        "init",
        str(q),
        "--from",
        str(paper / "decomposition-formula.tex"),
        "--prefix",
        "acgs",
        "--yes",
        "--fix-anchoring",
        cwd=tmp_path,
    )
    assert r.exit_code == 0, r.output[-3000:]
    assert "Identity test: pass" in r.output
    assert "0 dangling" in r.output
    assert len(list((q / "figures").glob("*"))) >= 1 or any(q.rglob("*.pspdftex"))  # the closure brought the figures


def test_paper_acgs_scan_time_and_memory(tmp_path: Path) -> None:
    q, _ = import_paper(tmp_path, "1709.09864", "decomposition-formula.tex", "acgs", "--fix-anchoring")
    quilt = load_quilt(q)
    tracemalloc.start()
    t0 = time.perf_counter()
    result = scan(quilt)
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(result.assembly.nodes) > 100
    assert elapsed < 10.0, elapsed  # measured 2026-09-15: see docs/demonstrations/M4.md for the numbers
    assert peak < 300 * 1024 * 1024, peak
