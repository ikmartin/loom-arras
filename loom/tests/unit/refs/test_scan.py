"""Gathering (`loom library update --only gather`): the quilt's bibliography gathered from the documents and the landmarks, and only ever appended to, and the store's documents no entry names adopted."""

from __future__ import annotations

from pathlib import Path

from loom.refs.scan import bibitem_fields, bibitems, scan_bibliography
from loom.scan.bib import BIBLIOGRAPHY, parse_bib
from loom.scan.quilt import load_quilt
from tests.helpers import ok

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
    assert "note = {kept as written}" in text and "% from landmark paper (@1) via refs.bib" in text
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
    assert report.conflicts == [("GP99", "landmark a (@1)", "landmark b (@2)")]  # as the author names them
    assert not (quilt.root / BIBLIOGRAPHY).exists()
    said = "\n".join(report.lines())
    assert "conflicts: two sources disagree, and the first is kept (1)" in said
    assert "  landmark a (@1) (kept) and landmark b (@2)  GP99" in said, said


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


def test_entries_naming_one_stored_document_are_reported_once_with_the_fix(tmp_path: Path) -> None:
    """Earlier scans left the author's quilt with several entries naming one document; the scan names them and the edit, and removes nothing, since the file is the author's to change."""
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    (quilt.root / ".loom/digests").mkdir()
    twice = "".join(
        f"@misc{{Siebert{suffix},\n  title = {{Punctured}},\n  loom-file = {{file/0972338306d22915}},\n  loom-source = {{refs/Siebert.pdf}},\n}}\n"
        for suffix in ("", "A", "B")
    )
    (quilt.root / BIBLIOGRAPHY).write_text(twice)
    lines = "\n".join(scan_bibliography(quilt).lines())
    assert "entries naming one document (1)" in lines
    assert "loom library ignore DUP --why '…' sets the copy aside" in " ".join(lines.split())
    assert "  refs/Siebert.pdf  Siebert, SiebertA, SiebertB" in lines, lines
    assert sorted(k for k in parse_bib((quilt.root / BIBLIOGRAPHY).read_text()) if k.startswith("Siebert")) == [
        "Siebert",
        "SiebertA",
        "SiebertB",
    ]


def _files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _fake(path: Path, text: str) -> None:
    """A PDF in the shape the fake toolchain's pdftotext reads (tests/fake_latex)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"%PDF-1.4\n%FAKE-LOOM\n%%Pages: 1\n{text}\n".encode())


def _filed(quilt, name: str = "Manolache - 2012 - Virtual pull-backs.pdf") -> Path:  # type: ignore[no-untyped-def]
    """A PDF from outside the quilt filed with `loom library add --for` against an entry written by hand, as a person files a paper that states no identifier; the entry is then deleted, leaving the document in the store with nothing naming it."""
    path = quilt.root / BIBLIOGRAPHY
    path.parent.mkdir(parents=True, exist_ok=True)
    before = path.read_text() if path.is_file() else ""
    path.write_text(
        before + "\n@misc{Mano12,\n  title = {Virtual pull-backs},\n  year = {2012},\n}\n", encoding="utf-8"
    )
    pdf = quilt.root.parent / name
    _pdf(pdf)
    ok("library", "add", str(pdf), "--for", "Mano12", "--force", "--as", "A. Author", cwd=quilt.root)
    path.write_text(before, encoding="utf-8")
    return pdf


def test_a_document_the_store_holds_and_no_entry_names_is_adopted_once(tmp_path: Path) -> None:
    """The store outlives the bibliography (plan 0.13 §12). An entry deleted by hand leaves a directory holding a PDF and its page text that nothing can reach: the viewer lists works by entry, and the ledger will not offer the file again because it remembers copying it. The scan offers an entry for it -- and **once**, which is the half that is easy to get wrong: a scan that checked identifiers alone would adopt the same directory again under a new key every time it ran. A name with doubled spaces is the same name the next time."""
    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    _filed(quilt, "Manolache - 2012 -  Virtual pull-backs.pdf")
    path = quilt.root / BIBLIOGRAPHY

    report = scan_bibliography(quilt)
    assert len(report.adopted) == 1, report.lines()
    key, where = report.adopted[0]
    assert where.startswith(".loom/digests/storage/")
    entry = parse_bib(path.read_text())[key]
    # what the entry says comes from the document and from the ledger's record of where it came from, never a lookup
    assert entry.fields["title"] == "Virtual pull-backs"
    assert (
        entry.fields["loom-source"] == "Manolache - 2012 - Virtual pull-backs.pdf"
    )  # as the bibliography reader collapses it
    assert "which the bibliography no longer named" in "\n".join(report.lines())

    # and having adopted it, the scan leaves it alone
    assert scan_bibliography(quilt).adopted == []
    assert scan_bibliography(quilt).adopted == []


def test_a_forgotten_document_is_not_offered_again(tmp_path: Path) -> None:
    """`loom library ignore` on a stored document is the tombstone that stops the store undoing a deletion (plan 0.13 §9): it is honoured by the citekey the author typed, and `--undo` restores the offer."""
    from loom.refs.unreadable import declare

    quilt = _quilt(tmp_path, {landmark(1, "paper"): PAPER})
    _filed(quilt)
    path = quilt.root / BIBLIOGRAPHY
    key = scan_bibliography(quilt, write=False).adopted[0][0]
    declare(quilt.root, "forget", key, "not worth an entry", "A. Author")

    report = scan_bibliography(quilt)
    assert report.adopted == [], "a forgotten document was offered an entry again"
    assert report.forgotten == 1
    assert "not offered: forgotten" in "\n".join(report.lines())
    assert "Manolache" not in path.read_text()

    # and withdrawing the tombstone brings the offer back, because nothing was ever removed
    declare(quilt.root, "forget", key, "changed my mind", "A. Author", undo=True)
    assert len(scan_bibliography(quilt).adopted) == 1


def test_a_bibliography_a_document_names_is_gathered_before_any_landmark(tmp_path: Path) -> None:
    """A bibliography is wherever a document's `\\bibliography` names it, read from the document's own directory, so a quilt with no landmark gathers its entries too."""
    quilt = _quilt(
        tmp_path,
        {
            "paper/main.tex": "\\documentclass{article}\n\\begin{document}\n\\cite{Mine}\n\\bibliography{theirs}\n\\end{document}\n",
            "paper/theirs.bib": "@book{Mine, title={Written by hand}}\n",
        },
    )
    report = scan_bibliography(quilt)
    assert [(c.key, c.source) for c in report.added] == [("Mine", "paper/main.tex via paper/theirs.bib")]
    assert report.canon == 0 and report.documents == 1
    assert parse_bib((quilt.root / BIBLIOGRAPHY).read_text())["Mine"].fields["title"] == "Written by hand"
