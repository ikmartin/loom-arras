"""Gathering (`loom library update --only gather`): the quilt's bibliography gathered from the landmarks, and only ever appended to (book 8.15)."""

from __future__ import annotations

from pathlib import Path

from loom.refs.scan import bibitem_fields, bibitems, scan_bibliography
from loom.scan.bib import BIBLIOGRAPHY, parse_bib
from loom.scan.quilt import load_quilt

PAPER = r"""\documentclass{amsart}
\begin{document}
Text \cite{GP99} and \cite{Kre99}.
\bibliographystyle{amsplain}
\bibliography{refs}
\begin{thebibliography}{9}
\bibitem[GP99]{GP99} T.~Graber and R.~Pandharipande, \emph{Localization of virtual classes}, Invent. Math. \textbf{135} (1999), no.~2, 487--518, arXiv:alg-geom/9708001.
\bibitem{Inline} A.~Author, {\it A title in the old style}, J. Math. (2003). doi:10.1000/xyz.123
\end{thebibliography}
\end{document}
"""


def landmark(n: int, name: str) -> str:
    """The quilt-relative path of the landmark `name` kept by step `n`, as `loom stamp DOCUMENT -m NAME` writes it."""
    return f".loom/history/{n:04d}-{name}/{name}.tex"


def _quilt(tmp_path: Path, files: dict[str, str]):  # type: ignore[no-untyped-def]
    """A quilt holding `files`; each under `.loom/history/` is a landmark, recorded by a step line as a stamp records one."""
    from loom.history.ledger import append_entry

    root = tmp_path / "q"
    root.mkdir()
    (root / "config.toml").write_text('[quilt]\nmain = "drafting/main.tex"\nprefix = "ab"\n', encoding="utf-8")
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
        if rel.startswith(".loom/history/"):
            step_dir, name = rel.split("/")[2], rel.split("/")[3]
            data = {"step": int(step_dir[:4]), "dir": step_dir, "landmark": name, "froze": {}}
            append_entry(root / ".loom" / "history", "stamp", data, "A. Author")
    return load_quilt(root)


def test_a_bibitem_yields_its_identifiers_and_a_heuristic_title_author_and_year() -> None:
    items = bibitems(PAPER)
    assert list(items) == ["GP99", "Inline"]
    gp = bibitem_fields(items["GP99"])
    assert gp["title"] == "Localization of virtual classes"
    assert gp["author"] == "T.~Graber and R.~Pandharipande"
    assert gp["year"] == "1999" and gp["eprint"] == "alg-geom/9708001" and gp["loom-parsed"] == "heuristic"
    old = bibitem_fields(items["Inline"])
    assert old["title"] == "A title in the old style" and old["doi"] == "10.1000/xyz.123" and old["year"] == "2003"


def test_an_entry_that_italicises_nothing_still_yields_author_title_and_year() -> None:
    """Manolache's bibliography is `K. Behrend, B. Fantechi, The intrinsic normal cone. Invent. Math. 127 (1997)`: the authors end where the initials stop, and the title at the first sentence break."""
    item = "K. Behrend, B. Fantechi, The intrinsic normal\ncone. Invent. Math. \\textbf{127} (1997), no.1, 45--88."
    fields = bibitem_fields(item)
    assert fields["author"] == "K. Behrend, B. Fantechi"
    assert fields["title"] == "The intrinsic normal cone" and fields["year"] == "1997"


def test_scan_copies_named_bib_entries_verbatim_and_converts_bibitems(tmp_path: Path) -> None:
    quilt = _quilt(
        tmp_path,
        {
            landmark(1, "paper"): PAPER,
            "refs.bib": "@article{Kre99,\n  author = {Kresch, A.},\n  title = {Cycle groups},\n  note = {kept as written},\n}\n",
        },
    )
    report = scan_bibliography(quilt)
    assert [c.key for c in report.added] == ["Kre99", "GP99", "Inline"]
    text = (quilt.root / BIBLIOGRAPHY).read_text()
    assert "note = {kept as written}" in text and f"% from {landmark(1, 'paper')} via refs.bib" in text
    assert set(parse_bib(text)) == {"Kre99", "GP99", "Inline"}


def test_scan_only_appends_and_never_rewrites_a_corrected_entry(tmp_path: Path) -> None:
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    scan_bibliography(quilt)
    path = quilt.root / BIBLIOGRAPHY
    path.write_text(path.read_text().replace("Localization of virtual classes", "Localization of Virtual Classes"))
    corrected = path.read_text()
    again = scan_bibliography(quilt)
    assert again.added == [] and again.present == 2 and path.read_text() == corrected

    (quilt.root / landmark(1, "paper")).unlink()  # a landmark gone removes nothing
    assert scan_bibliography(quilt).added == [] and path.read_text() == corrected


def test_two_landmarks_disagreeing_on_a_key_keep_the_first_and_say_so(tmp_path: Path) -> None:
    other = PAPER.replace("Localization of virtual classes", "Something else entirely")
    quilt = _quilt(tmp_path, {landmark(1, "a"): PAPER, landmark(2, "b"): other, landmark(3, "c"): PAPER})
    report = scan_bibliography(quilt, write=False)
    assert report.conflicts == [("GP99", landmark(1, "a"), landmark(2, "b"))]
    assert not (quilt.root / BIBLIOGRAPHY).exists()
    said = "\n".join(report.lines())
    assert "conflicts: the landmarks disagree, and the first is kept (1)" in said
    assert f"  {landmark(1, 'a')} (kept) and {landmark(2, 'b')}  GP99" in said, said


def _pdf(path: Path, text: str = "A paper about widgets") -> None:
    """A one-page PDF with a text layer, written by hand so the test needs no TeX."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    start = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def test_a_document_in_the_seed_space_is_copied_once_and_offered_an_entry(tmp_path: Path) -> None:
    """`refs/` is the author's: loom reads it, files what it has not seen before under `digests/storage`, and writes an entry for a document the bibliography does not name. A second scan copies nothing, and neither does a third after the author renames the file, because the ledger is keyed by content (DR-190)."""
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    seed = quilt.root / "refs"
    seed.mkdir()
    _pdf(seed / "Manolache - 2012 - Virtual pull-backs.pdf")

    report = scan_bibliography(quilt)
    assert len(report.copied) == 1 and report.already == 0
    filed = quilt.root / report.copied[0][1]
    assert (filed / "paper.pdf").is_file() and filed.is_relative_to(quilt.root / "digests" / "storage")
    entry = parse_bib((quilt.root / BIBLIOGRAPHY).read_text())["Manolache2012Virtualpull"]
    assert (
        entry.fields["title"] == "Virtual pull-backs"
        and entry.fields["loom-source"] == "refs/Manolache - 2012 - Virtual pull-backs.pdf"
    )

    again = scan_bibliography(quilt)
    assert again.copied == [] and again.already == 1

    (seed / "Manolache - 2012 - Virtual pull-backs.pdf").rename(seed / "renamed.pdf")
    assert scan_bibliography(quilt).copied == []

    (seed / "renamed.pdf").unlink()  # and what was filed stays, because the store is not a mirror
    assert scan_bibliography(quilt).copied == [] and (filed / "paper.pdf").is_file()


def test_a_document_the_store_holds_and_no_entry_names_is_adopted_once(tmp_path: Path) -> None:
    """The store outlives the bibliography (plan 0.13 §12). An entry deleted by hand leaves a directory holding a PDF and its page text that nothing can reach: the viewer lists works by entry, and the ledger will not offer the file again because it remembers copying it. The scan offers an entry for it -- and **once**, which is the half that is easy to get wrong: a hash-named home is not claimed by any identifier, so a scan that checked identifiers alone would adopt the same directory again under a new key every time it ran."""
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    seed = quilt.root / "refs"
    seed.mkdir()
    _pdf(seed / "Manolache - 2012 - Virtual pull-backs.pdf")
    scan_bibliography(quilt)
    path = quilt.root / BIBLIOGRAPHY

    # the second and third scans adopt nothing: the document already has its entry
    assert scan_bibliography(quilt).adopted == []
    assert scan_bibliography(quilt).adopted == []

    # now the author deletes the entry, and the document is in the store with nothing naming it
    kept = [block for block in path.read_text().split("\n@") if "Manolache" not in block]
    path.write_text("@".join(kept) if kept[0].startswith("@") else kept[0] + "@".join(kept[1:]))
    assert "Manolache" not in path.read_text()

    report = scan_bibliography(quilt)
    assert len(report.adopted) == 1, report.lines()
    key, where = report.adopted[0]
    assert where.startswith("digests/storage/")
    entry = parse_bib(path.read_text())[key]
    # what the entry says comes from the document and from the ledger's record of where it was dropped, never a lookup
    assert entry.fields["title"] == "Virtual pull-backs"
    assert entry.fields["loom-source"] == "refs/Manolache - 2012 - Virtual pull-backs.pdf"
    assert "which the bibliography no longer named" in "\n".join(report.lines())

    # and having adopted it, the scan leaves it alone
    assert scan_bibliography(quilt).adopted == []


def test_a_forgotten_document_is_not_offered_again(tmp_path: Path) -> None:
    """`loom library ignore` on a stored document is the tombstone that stops the store undoing a deletion (plan 0.13 §9).

    Without this the command was a report of success and nothing else: it wrote the declaration, nothing read it, and the next scan offered the deleted entry straight back. The tombstone is honoured by the citekey the author typed and by the document's own hash, and `--undo` restores the offer.
    """
    from loom.refs.unreadable import declare

    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    seed = quilt.root / "refs"
    seed.mkdir()
    _pdf(seed / "Manolache - 2012 - Virtual pull-backs.pdf")
    scan_bibliography(quilt)
    path = quilt.root / BIBLIOGRAPHY

    # the author deletes the entry the first scan offered, and says they meant it
    kept = [block for block in path.read_text().split("\n@") if "Manolache" not in block]
    path.write_text("@".join(kept) if kept[0].startswith("@") else kept[0] + "@".join(kept[1:]))
    declare(quilt.root, "forget", "Manolache2012Virtualpull", "not worth an entry", "A. Author")

    report = scan_bibliography(quilt)
    assert report.adopted == [], "a forgotten document was offered an entry again"
    assert report.forgotten == 1
    assert "not offered: forgotten" in "\n".join(report.lines())
    assert "Manolache" not in path.read_text()

    # and withdrawing the tombstone brings the offer back, because nothing was ever removed
    declare(quilt.root, "forget", "Manolache2012Virtualpull", "changed my mind", "A. Author", undo=True)
    assert len(scan_bibliography(quilt).adopted) == 1


def test_a_bib_file_in_the_seed_space_is_read_like_one_a_document_names(tmp_path: Path) -> None:
    quilt = _quilt(
        tmp_path, {landmark(1, "paper"): PAPER, "refs/theirs.bib": "@book{Dropped, title={Dropped in by hand}}\n"}
    )
    report = scan_bibliography(quilt)
    assert "Dropped" in {c.key for c in report.added}
    assert parse_bib((quilt.root / BIBLIOGRAPHY).read_text())["Dropped"].fields["title"] == "Dropped in by hand"


def test_a_document_that_states_no_identifier_is_reachable_from_its_own_entry(tmp_path: Path) -> None:
    """A PDF that prints no DOI or arXiv id — a scan, most older literature — is filed under its content hash, and the entry the scan offers states no identifier either, so `primary` answers with the *synthetic* identifier: a hash of author, title and year. The two disagreed, and the viewer told the reader "No copy of this paper on this machine" about a paper sitting in the store.

    Found in the reading study on an OCR'd 1988 journal scan, which is exactly the character of paper that states nothing about itself.
    """
    from loom.refs.fetch import work_dir
    from loom.refs.identity import primary
    from loom.scan.bib import parse_bib

    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    seed = quilt.root / "refs"
    seed.mkdir()
    _pdf(seed / "Ekedahl - 1988 - The order of the tautological ring.pdf", text="The order of the tautological ring")
    report = scan_bibliography(quilt)
    key = report.added[-1].key
    entry = parse_bib((quilt.root / BIBLIOGRAPHY).read_text())[key]

    filed = quilt.root / report.copied[-1][1]
    assert (filed / "paper.pdf").is_file()
    assert entry.fields["loom-file"] == f"{filed.parent.name}/{filed.name}"
    # the entry's own identifier names somewhere else entirely, and must not be what anyone looks under
    assert primary(entry) is not None and primary(entry).path != entry.fields["loom-file"]
    assert work_dir(quilt.root, entry) == filed

    # a document that does state an identifier is filed under it, and carries no `loom-file` to override it
    _pdf(seed / "stated.pdf", text="arXiv:2504.09999v1 A paper that names itself")
    again = scan_bibliography(quilt)
    named = parse_bib((quilt.root / BIBLIOGRAPHY).read_text())[again.added[-1].key]
    stated = primary(named)
    assert stated is not None and str(stated) == "arXiv:2504.09999v1", named.fields
    assert "loom-file" not in named.fields
    assert work_dir(quilt.root, named) == quilt.root / "digests" / "storage" / stated.path


def test_a_document_named_with_doubled_spaces_or_in_a_folder_is_offered_one_entry_however_often_the_scan_runs(
    tmp_path: Path,
) -> None:
    """The bibliography reader collapses whitespace, so a file named with two spaces never matched its own entry's `loom-source`, and every scan adopted it again under a new key: `SiebertPuncturedLogarith`, then `…A`, `…B` (CLI study, defect 4). A file in a subfolder was recorded under one path and ledgered under another, with the same result."""
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    seed = quilt.root / "refs"
    (seed / "older").mkdir(parents=True)
    _pdf(seed / "Siebert  -  Punctured logarithmic maps.pdf", text="Punctured logarithmic maps")
    _pdf(seed / "older" / "Wise - 2016 - Moduli of morphisms.pdf", text="Moduli of morphisms")
    scan_bibliography(quilt)
    path = quilt.root / BIBLIOGRAPHY
    entries = set(parse_bib(path.read_text()))
    for _ in range(3):
        again = scan_bibliography(quilt)
        assert again.adopted == [] and again.added == [], again.lines()
    assert set(parse_bib(path.read_text())) == entries


def test_a_dry_run_writes_copies_and_records_nothing(tmp_path: Path) -> None:
    """A dry run copied the document, mapped it and ledgered it, and the next real scan then adopted the copy as an orphan instead of offering its entry."""
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    seed = quilt.root / "refs"
    seed.mkdir()
    _pdf(seed / "Manolache - 2012 - Virtual pull-backs.pdf")
    report = scan_bibliography(quilt, write=False)
    assert report.copied and report.added
    assert not (quilt.root / BIBLIOGRAPHY).exists()
    assert not (quilt.root / "digests" / "storage").exists()
    first = scan_bibliography(quilt)
    assert first.adopted == [] and any("Manolache" in c.key for c in first.added)


def test_a_second_document_for_a_work_that_states_no_identifier_shows_its_own_pdf(tmp_path: Path) -> None:
    """A sibling entry was written without `loom-file`, so it was looked for under the synthetic home its author, title and year hash to -- the original's -- and showed the original's PDF, or none (the agent critique of 2026-10-02, §3)."""
    from loom.refs.fetch import work_dir

    bib = "@article{Eke88,\n  author = {Ekedahl, Torsten},\n  title = {The order of the tautological ring},\n  year = {1988},\n}\n"
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER, "refs/mine.bib": bib})
    seed = quilt.root / "refs"
    _fake(
        seed / "Ekedahl - 1988 - The order of the tautological ring.pdf",
        "The order of the tautological ring\nTorsten Ekedahl",
    )
    scan_bibliography(quilt)
    _fake(
        seed / "Ekedahl - 1988 - The order of the tautological ring, preprint.pdf",
        "The order of the tautological ring\nTorsten Ekedahl\npreprint",
    )
    report = scan_bibliography(quilt)
    assert report.siblings, report.lines()
    sibling, of = report.siblings[0]
    entries = parse_bib((quilt.root / BIBLIOGRAPHY).read_text())
    mine, theirs = work_dir(quilt.root, entries[sibling]), work_dir(quilt.root, entries[of])
    assert mine != theirs and (mine / "paper.pdf").is_file() and (theirs / "paper.pdf").is_file()
    assert (mine / "paper.pdf").read_bytes() != (theirs / "paper.pdf").read_bytes()


def test_entries_naming_one_stored_document_are_reported_once_with_the_fix(tmp_path: Path) -> None:
    """Earlier scans left the author's quilt with several entries naming one document; the scan names them and the edit, and removes nothing, since the file is the author's to change."""
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    (quilt.root / "digests").mkdir()
    twice = "".join(
        f"@misc{{Siebert{suffix},\n  title = {{Punctured}},\n  loom-file = {{file/0972338306d22915}},\n  loom-source = {{refs/Siebert.pdf}},\n}}\n"
        for suffix in ("", "A", "B")
    )
    (quilt.root / BIBLIOGRAPHY).write_text(twice)
    lines = "\n".join(scan_bibliography(quilt).lines())
    assert "entries naming one document: keep one and delete the others from digests/bibliography.bib (1)" in lines
    assert "  refs/Siebert.pdf  Siebert, SiebertA, SiebertB" in lines, lines
    assert sorted(k for k in parse_bib((quilt.root / BIBLIOGRAPHY).read_text()) if k.startswith("Siebert")) == [
        "Siebert",
        "SiebertA",
        "SiebertB",
    ]


def _files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_gathering_twice_changes_nothing_and_offers_one_document_one_entry(tmp_path: Path) -> None:
    """A document already offered an entry is not offered another (plan 0.18.5): one document dropped twice under two names, a second document for a work, a document that says nothing about itself, and a store directory no entry names, gathered twice, leave every file as the first gathering left it."""
    bib = "@article{Eke88,\n  author = {Ekedahl, Torsten},\n  title = {The order of the tautological ring},\n  year = {1988},\n}\n"
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER, "refs/mine.bib": bib})
    seed = quilt.root / "refs"
    _pdf(seed / "Ekedahl - 1988 - The order of the tautological ring.pdf", text="The order of the tautological ring")
    (seed / "copy").mkdir()
    _pdf(seed / "notes.pdf", text="Unrelated notes")
    _pdf(seed / "copy" / "notes again.pdf", text="Unrelated notes")  # the same bytes under another name
    orphan = quilt.root / "digests" / "storage" / "file" / "00ff00ff00ff00ff"
    orphan.mkdir(parents=True)
    _pdf(orphan / "paper.pdf", text="An orphan")
    first = scan_bibliography(quilt)
    offered = [c.key for c in first.added if "loom-source" in c.text]
    entries = parse_bib((quilt.root / BIBLIOGRAPHY).read_text())
    sources = [str(entries[k].fields.get("loom-source")) for k in offered]
    assert sum(1 for s in sources if "notes" in s) == 1, f"one document, one entry: {sources}"
    _pdf(seed / "Ekedahl - 1988 - The order of the tautological ring, v2.pdf", text="The order, a second copy")
    scan_bibliography(quilt)  # a second document for Eke88, filed beside the first
    before = _files(quilt.root)
    again = scan_bibliography(quilt)
    assert again.added == [] and again.copied == [] and again.adopted == [], again.lines()
    assert _files(quilt.root) == before


def _fake(path: Path, text: str) -> None:
    """A PDF in the shape the fake toolchain's pdftotext reads (tests/fake_latex)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"%PDF-1.4\n%FAKE-LOOM\n%%Pages: 1\n{text}\n".encode())


def test_gathering_files_a_document_against_an_entry_only_on_a_strong_match(tmp_path: Path) -> None:
    """The rule `library add` files on holds for `refs/` too: the handbook names Olsson fifth and shares half his 2003 title, so it is not filed as his paper; it is offered its own entry, and the report says why with the fix (audit §4)."""
    from loom.refs.fetch import work_dir

    bib = "@article{olsson03,\n  author = {Olsson, Martin C.},\n  title = {Logarithmic geometry and algebraic stacks},\n  year = {2003},\n}\n"
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER, "refs/mine.bib": bib})
    seed = quilt.root / "refs"
    _fake(
        seed / "Handbook of Moduli.pdf",
        "Logarithmic geometry and moduli\nDan Abramovich, Qile Chen, Danny Gillam, Martin Olsson, and Shenghao Sun",
    )
    _fake(seed / "olsson.pdf", "Logarithmic geometry and algebraic stacks\nMartin C. Olsson\nAnn. Sci. ENS")
    report = scan_bibliography(quilt)
    entries = parse_bib((quilt.root / BIBLIOGRAPHY).read_text())
    home = work_dir(quilt.root, entries["olsson03"])
    assert (home / "paper.pdf").read_bytes() == (seed / "olsson.pdf").read_bytes()
    assert not any(e.fields.get("loom-copy-of") == "olsson03" for e in entries.values()), "no sibling: it is not his"
    offered = [k for k, e in entries.items() if e.fields.get("loom-source") == "refs/Handbook of Moduli.pdf"]
    assert len(offered) == 1, "the handbook is offered its own entry"
    assert [name for name, _ in report.unmatched] == ["refs/Handbook of Moduli.pdf"]
    said = " ".join("\n".join(report.lines()).split())
    assert "olsson03 is the nearest entry" in said and "Olsson does not lead its byline" in said, said
    assert "loom library add FILE --for WORK" in said
