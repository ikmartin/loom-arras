"""`loom refs scan`: the quilt's bibliography gathered from the canon documents, and only ever appended to (book 8.15)."""

from __future__ import annotations

from pathlib import Path

from loom.refs.scan import bibitem_fields, bibitems, scan_bibliography
from loom.scan.bib import BIBLIOGRAPHY, parse_bib
from loom.scan.quilt import load_quilt

CANON = r"""\documentclass{amsart}
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


def _quilt(tmp_path: Path, files: dict[str, str]):  # type: ignore[no-untyped-def]
    root = tmp_path / "q"
    root.mkdir()
    (root / "config.toml").write_text('[quilt]\nmain = "drafting/main.tex"\nprefix = "ab"\n', encoding="utf-8")
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return load_quilt(root)


def test_a_bibitem_yields_its_identifiers_and_a_heuristic_title_author_and_year() -> None:
    items = bibitems(CANON)
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
            "canon/paper.tex": CANON,
            "refs.bib": "@article{Kre99,\n  author = {Kresch, A.},\n  title = {Cycle groups},\n  note = {kept as written},\n}\n",
        },
    )
    report = scan_bibliography(quilt)
    assert [c.key for c in report.added] == ["Kre99", "GP99", "Inline"]
    text = (quilt.root / BIBLIOGRAPHY).read_text()
    assert "note = {kept as written}" in text and "% from canon/paper.tex via refs.bib" in text
    assert set(parse_bib(text)) == {"Kre99", "GP99", "Inline"}


def test_scan_only_appends_and_never_rewrites_a_corrected_entry(tmp_path: Path) -> None:
    quilt = _quilt(tmp_path, {"canon/paper.tex": CANON})
    scan_bibliography(quilt)
    path = quilt.root / BIBLIOGRAPHY
    path.write_text(path.read_text().replace("Localization of virtual classes", "Localization of Virtual Classes"))
    corrected = path.read_text()
    again = scan_bibliography(quilt)
    assert again.added == [] and again.present == 2 and path.read_text() == corrected

    (quilt.root / "canon" / "paper.tex").unlink()  # a canon document gone removes nothing
    assert scan_bibliography(quilt).added == [] and path.read_text() == corrected


def test_two_canon_documents_disagreeing_on_a_key_keep_the_first_and_say_so(tmp_path: Path) -> None:
    other = CANON.replace("Localization of virtual classes", "Something else entirely")
    quilt = _quilt(tmp_path, {"canon/a.tex": CANON, "canon/b.tex": other, "canon/c.tex": CANON})
    report = scan_bibliography(quilt, write=False)
    assert report.conflicts == [("GP99", "canon/a.tex", "canon/b.tex")]
    assert not (quilt.root / BIBLIOGRAPHY).exists()
    assert any("conflict: GP99" in line for line in report.lines())


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
    quilt = _quilt(tmp_path, {"canon/paper.tex": CANON})
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


def test_a_bib_file_in_the_seed_space_is_read_like_one_a_document_names(tmp_path: Path) -> None:
    quilt = _quilt(
        tmp_path, {"canon/paper.tex": CANON, "refs/theirs.bib": "@book{Dropped, title={Dropped in by hand}}\n"}
    )
    report = scan_bibliography(quilt)
    assert "Dropped" in {c.key for c in report.added}
    assert parse_bib((quilt.root / BIBLIOGRAPHY).read_text())["Dropped"].fields["title"] == "Dropped in by hand"
