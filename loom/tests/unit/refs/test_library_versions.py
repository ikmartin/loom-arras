"""One work, several documents (plan 0.18.5b item 2): a work is a primary entry and the siblings `loom-copy-of` names, filed once per document, digested once, cited through, and listed as one."""

from __future__ import annotations

import json
from pathlib import Path

from loom.refs.scan import versions_of
from loom.scan.bib import parse_bib
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.helpers import json_of, ok
from tests.unit._quilts import demo, work_home

BIB = "digests/bibliography.bib"
CK, V = "Calloway14", "Calloway14A"
OLSSON = "Logarithmic geometry and algebraic stacks\nMartin C. Olsson\nAnn. Sci. Ecole Norm. Sup.\n"
OLSSON_BIB = "\n@article{olsson03, author={Olsson, Martin C.}, title={Logarithmic geometry and algebraic stacks}, year={2003}, doi={10.1016/olsson.03}}\n"
#: A preprint of Calloway14: its Definition 3.1, its Proposition 3.2 as the journal states it, and a Theorem 5.1 the journal dropped.
PREPRINT = (
    f"% !LOOM digest: {V}\n% !LOOM prefix: {V}\n% !LOOM extracted-from: arXiv:1301.00001v1\n% !LOOM method: extract\n"
    "\\section*{Overview}\nThe preprint.\n"
    f"\\begin{{definition}}[{{\\cite[Definition 3.1, p.~1]{{{V}}}}}]\\label{{{V}-def-3.1}}\n"
    "An involution of a space is a self-map whose square is the identity.\n"
    "\\end{definition}\n"
    f"\\begin{{proposition}}[{{\\cite[Proposition 3.2, p.~1]{{{V}}}}}]\\label{{{V}-prop-3.2}}\n"
    f"Let $X$ be a Hausdorff space and $\\sigma$ an involution of $X$ in the sense of Definition~\\ref{{{V}-def-3.1}}. "
    "Then $\\operatorname{Fix}(\\sigma)$ is closed in $X$.\n"
    "\\end{proposition}\n"
    f"\\begin{{theorem}}[{{\\cite[Theorem 5.1, p.~9]{{{V}}}}}]\\label{{{V}-thm-5.1}}\n"
    "Every involution of a compact space has a compact fixed locus.\n"
    "\\end{theorem}\n"
)


def _fake_pdf(path: Path, text: str) -> Path:
    """A PDF in the shape the fake toolchain's pdftotext reads (tests/fake_latex); a form feed in `text` starts a page."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"%PDF-1.4\n%FAKE-LOOM\n%%Pages: 1\n{text}\n".encode())
    return path


def _versioned(tmp_path: Path) -> Path:
    """The demo with a preprint of Calloway14 as its sibling, digested, with its results recorded."""
    q = demo(tmp_path)
    with (q / BIB).open("a", encoding="utf-8") as fh:
        fh.write(
            f"\n@article{{{V},\n  author = {{Calloway, Imogen}},\n  title = {{Fixed loci of involutions on separated spaces}},\n"
            f"  year = {{2014}},\n  eprint = {{1301.00001v1}},\n  archiveprefix = {{arXiv}},\n"
            f"  loom-copy-of = {{{CK}}},\n  loom-file = {{file/0123456789abcdef}},\n}}\n"
        )
    (q / "digests" / f"{V}.tex").write_text(PREPRINT, encoding="utf-8")
    ok("library", "update", V, "--only", "extract", cwd=q)
    assert (q / "digests" / f"{V}.results.json").is_file()
    return q


def _cite(q: Path, text: str) -> None:
    """Append a sentence citing something to the demo's node dm-0003, which is in its document."""
    node = q / "nodes" / "dm-0003.tex"
    body = node.read_text(encoding="utf-8")
    node.write_text(body.replace("\\end{proof}", f"{text}\n\\end{{proof}}", 1), encoding="utf-8")


def test_versions_of_reads_loom_copy_of_and_follows_a_chain_to_its_primary() -> None:
    bib = parse_bib(
        "@misc{P, title={T}}\n@misc{PA, title={T}, loom-copy-of={P}}\n@misc{PB, title={T}, loom-copy-of={PA}}\n"
        "@misc{Q, title={U}}\n@misc{QA, title={U}, loom-copy-of={Gone}}\n"
    )
    assert versions_of(bib) == {"P": ["PA", "PB"]}


def test_an_identical_document_is_recorded_as_a_duplicate_and_not_filed(tmp_path: Path) -> None:
    """Same title, authors and page count as the stored document, or the work's own identifier: a copy in the ledger, never a sibling; a document with another page is another version, filed beside the first."""
    q = demo(tmp_path)
    (q / BIB).open("a", encoding="utf-8").write(OLSSON_BIB)
    one = _fake_pdf(tmp_path / "one.pdf", OLSSON + "first copy")
    ok("library", "add", one, "--for", "olsson03", cwd=q)
    same = _fake_pdf(tmp_path / "same.pdf", OLSSON + "a second download")
    stated = _fake_pdf(tmp_path / "stated.pdf", OLSSON + "doi:10.1016/olsson.03\fand a page the first lacks")
    r = ok("library", "add", same, stated, "--for", "olsson03", "--as", "A. Author", cwd=q)
    said = " ".join(r.stdout.split())
    assert said.startswith("2 documents: 0 filed, 2 skipped"), said
    assert "same.pdf: the same document as olsson03's: same title, authors and 1 page" in said, said
    assert (
        "stated.pdf: the same document as olsson03's: it states doi:10.1016/olsson.03, olsson03's own identifier"
        in said
    )
    assert "olsson03A" not in (q / BIB).read_text()
    ledger = json.loads((q / "digests" / "storage" / "copied.json").read_text())
    copies = {v["from"]: v for v in ledger.values() if v.get("duplicate-of")}
    assert set(copies) == {"same.pdf", "stated.pdf"} and {v["duplicate-of"] for v in copies.values()} == {"olsson03"}
    home = work_home(q, "olsson03").relative_to(q).as_posix()
    assert {v["to"] for v in copies.values()} == {home}
    # another version: the same title and byline over two pages
    other = _fake_pdf(tmp_path / "other.pdf", OLSSON + "preprint\fan appendix the journal dropped")
    r = ok("library", "add", other, "--for", "olsson03", cwd=q)
    assert "beside its first document as olsson03A" in " ".join(r.stdout.split())
    # a copy of that version is a duplicate of the work, not a third version
    again = _fake_pdf(tmp_path / "again.pdf", OLSSON + "preprint, downloaded twice\fan appendix the journal dropped")
    r = ok("library", "add", again, "--for", "olsson03", cwd=q)
    assert "the same document as olsson03A's: same title, authors and 2 pages" in " ".join(r.stdout.split())
    assert "olsson03B" not in (q / BIB).read_text()


def test_gathering_records_an_identical_document_as_a_duplicate(tmp_path: Path) -> None:
    """Gathering's own sibling branch keeps the same rule as `library add`: a copy is recorded and reported, and offers no entry."""
    from loom.refs.scan import scan_bibliography

    q = demo(tmp_path)
    (q / BIB).open("a", encoding="utf-8").write(OLSSON_BIB)
    seed = q / "refs"
    _fake_pdf(seed / "olsson.pdf", OLSSON + "first copy")
    scan_bibliography(load_quilt(q))
    _fake_pdf(seed / "olsson again.pdf", OLSSON + "a second download")
    _fake_pdf(seed / "olsson preprint.pdf", OLSSON + "preprint\fan appendix")
    report = scan_bibliography(load_quilt(q))
    assert report.copies == [("refs/olsson again.pdf", "olsson03", "same title, authors and 1 page")], report.lines()
    assert [of for _key, of in report.siblings] == ["olsson03"], report.lines()
    assert "copies of a filed document, recorded and not filed again" in "\n".join(report.lines())
    entries = parse_bib((q / BIB).read_text())
    assert [k for k, e in entries.items() if e.fields.get("loom-copy-of")] == ["olsson03A"]
    ledger = json.loads((q / "digests" / "storage" / "copied.json").read_text())
    assert any(v["from"] == "refs/olsson again.pdf" and v.get("duplicate-of") == "olsson03" for v in ledger.values())
    assert scan_bibliography(load_quilt(q)).copies == [], "recorded once: the ledger has seen those bytes"


def test_a_version_is_not_extracted_unless_cited_or_named(tmp_path: Path) -> None:
    """A second document of a work brings no second digest: `update` skips an uncited version with a source, and extracts it when the author names it or cites it."""
    q = _versioned(tmp_path)
    (q / "digests" / f"{V}.tex").unlink()
    (q / "digests" / f"{V}.results.json").unlink()
    src = work_home(q, V) / "src"
    src.mkdir(parents=True)
    (src / "paper.tex").write_text("\\documentclass{article}\n\\begin{document}\nPreprint.\n\\end{document}\n")

    def plan(*args: str) -> list[str]:
        out = json_of("library", "update", *args, "--only", "extract", "--dry-run", "--json", cwd=q)
        return [i["key"] for g in out["groups"] if g["heading"].startswith("would extract") for i in g["items"]]

    assert V not in plan()
    assert V in plan(V)
    _cite(q, f"Compare \\cite{{{V}}}.")
    assert V in plan()


def test_a_postnote_resolves_through_a_version_with_the_info_diagnostic(tmp_path: Path) -> None:
    """`\\cite[Theorem 5.1]{Calloway14}` names a result only the preprint states: the edge goes to the version's node, and lint says so as info rather than warning `loom:unmatched-postnote`."""
    q = _versioned(tmp_path)
    _cite(q, f"The compact case is \\cite[Theorem 5.1]{{{CK}}}.")
    result = scan(load_quilt(q))
    edges = [e for e in result.edges.edges if e.to == f"{V}-thm-5.1"]
    assert [(e.src, e.via) for e in edges] == [("dm-0003/proof", "postnote")]
    codes = {d.code: d for d in result.lint}
    assert "loom:unmatched-postnote" not in codes
    info = [d for d in result.lint if d.code == "loom:postnote-from-another-version"]
    assert len(info) == 1 and info[0].severity == "info", result.lint
    assert (
        info[0].message
        == f"\\cite[Theorem 5.1]{{{CK}}} names {V}-thm-5.1, from the digest of {V}, another version of {CK}"
    )
    # the work's own digest still wins where it has the result
    _cite(q, f"Closedness is \\cite[Proposition 3.2]{{{CK}}}.")
    result = scan(load_quilt(q))
    assert {e.to for e in result.edges.edges if e.src == "dm-0003/proof" and e.via == "postnote"} == {
        f"{CK}-prop-3.2",
        f"{V}-thm-5.1",
    }


def test_a_key_counts_as_digested_when_a_version_is(tmp_path: Path) -> None:
    """With no digest of its own, a key's postnote matches its version's digest, and neither lint nor `review` calls it undigested."""
    from loom.cli.review import status_payload
    from loom.records.store import Records

    q = _versioned(tmp_path)
    (q / "digests" / f"{CK}.tex").unlink()
    (q / "digests" / f"{CK}.results.json").unlink()
    result = scan(load_quilt(q))
    assert not [d for d in result.lint if d.code == "loom:undigested-citekey"], result.lint
    assert [e.to for e in result.edges.edges if e.via == "postnote"] == [f"{V}-prop-3.2"]
    assert [d.code for d in result.lint if d.code.startswith("loom:postnote")] == ["loom:postnote-from-another-version"]
    assert status_payload(result, Records(q))["undigested"] == []


def test_the_manifest_names_a_work_s_versions_and_a_version_s_work(tmp_path: Path) -> None:
    q = _versioned(tmp_path)
    ok("build", cwd=q)
    refs = json.loads((q / "build" / "manifest.json").read_text())["references"]
    assert refs[CK]["versions"] == [
        {
            "citekey": V,
            "work": "arXiv:1301.00001v1",
            "artifacts": {"dir": "digests/storage/file/0123456789abcdef", "pdf": False, "source": False},
        }
    ]
    assert refs[V]["version_of"] == CK
    assert "version_of" not in refs[CK] and "versions" not in refs[V]
    assert "loom-copy-of" not in refs[V]["bib"]


def test_the_library_lists_one_row_per_work_and_search_one_hit(tmp_path: Path) -> None:
    """`library` folds a version into its work's row, naming it; search reports a result once, naming the versions that also hold it; a fragment matching only a work and its versions names the work."""
    q = _versioned(tmp_path)
    works = json_of("library", "--json", cwd=q)["works"]
    assert V not in {w["citekey"] for w in works}
    row = next(w for w in works if w["citekey"] == CK)
    assert row["versions"] == [V] and row["extracted"] == 5 + 3
    hits = json_of("library", "search", "Hausdorff closed", "--json", cwd=q)["hits"]
    closed = [h for h in hits if h["locator"] == "Proposition 3.2"]
    assert [(h["work"], h["versions"]) for h in closed] == [(CK, [V])], hits
    assert f"{CK}  Proposition 3.2" in ok("library", "search", "Hausdorff closed", cwd=q).stdout
    assert f"also in {V}" in ok("library", "search", "Hausdorff closed", cwd=q).stdout
    only = json_of("library", "search", "compact", "--json", cwd=q)["hits"]
    assert [(h["work"], h["versions"]) for h in only] == [(V, [])]
    r = ok("library", "Callow", cwd=q)
    assert r.stdout.startswith(f"{CK}: cited by"), r.output
    assert f"versions {V}" in r.output
    assert ok("library", "read", V, cwd=q).stdout.strip(), "a version still resolves by its own key"


def test_check_reports_existing_duplicates_once_per_work(tmp_path: Path) -> None:
    """Versions filed before 0.18.5b that are one document: `library check` names them once for the work, with every key."""
    q = demo(tmp_path)
    (q / BIB).open("a", encoding="utf-8").write(OLSSON_BIB)
    ok("library", "add", _fake_pdf(tmp_path / "one.pdf", OLSSON + "first"), "--for", "olsson03", cwd=q)
    for n, name in enumerate(("two.pdf", "three.pdf")):
        pages = OLSSON + "\f".join(["x"] * (n + 2))
        ok("library", "add", _fake_pdf(tmp_path / name, pages), "--for", "olsson03", cwd=q)
    entries = parse_bib((q / BIB).read_text())
    assert versions_of(entries)["olsson03"] == ["olsson03A", "olsson03B"]
    # what an earlier loom filed: both versions' stored documents become copies of the first
    first = (work_home(q, "olsson03") / "paper.pdf").read_bytes()
    for v in ("olsson03A", "olsson03B"):
        (work_home(q, v) / "paper.pdf").write_bytes(first + f"%{v}\n".encode())
    out = json_of("library", "check", "--json", cwd=q, code=1)
    dups = [p for p in out["problems"] if p["problem"] == "duplicate-document"]
    assert [(p["work"], p["key"]) for p in dups] == [("olsson03", "olsson03, olsson03A, olsson03B")], dups
