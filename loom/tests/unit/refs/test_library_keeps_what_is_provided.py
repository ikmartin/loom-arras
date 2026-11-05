"""Adding a PDF keeps it, whatever is known about it: the author's Zotero library holds revision notes with no DOI, books whose metadata resolves and scans with no text layer, and each must be copied in and read as a work."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loom.cli.library.add import _is_pdf
from loom.refs.add import file_new, file_under, identify, own_entry
from loom.refs.fetch import work_dir
from loom.refs.lookup import look_up
from loom.scan.bib import BibEntry, parse_bib
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.helpers import edit, json_of, ok
from tests.unit._quilts import demo, work_home

BIB = ".loom/digests/bibliography.bib"
AS = ("--as", "A. Author")
#: The author's report: revision notes that no catalogue knows, under the name a site gave the download.
NOTES = "Stats_for_Quants__1753634802.pdf"
NOTES_TEXT = "Statistics For Quants : Revision Notes\nAmit Kumar Jha\nJuly 26, 2025\n1\nFoundational Proportional Relationships\n"
#: The author's report: a book, under the name Zotero gave it, with no year in that name.
BOOK = "Shreve - Stochastic Calculus for Finance II.pdf"
BOOK_TEXT = "Stochastic Calculus for Finance II\nContinuous-Time Models\nSteven E. Shreve\nPreface\n"


def _fake_pdf(path: Path, text: str) -> Path:
    """A PDF in the shape the fake toolchain's pdftotext reads (tests/fake_latex)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"%PDF-1.4\n%FAKE-LOOM\n%%Pages: 1\n{text}\n".encode())
    return path


def _entries(q: Path) -> dict[str, BibEntry]:
    return parse_bib((q / BIB).read_text(encoding="utf-8"))


def _cites(q: Path, key: str) -> None:
    """The demo's main document cites `key`, which is what `loom lint` asks after."""
    edit(q / "drafting" / "main.tex", "\\end{document}", f"\\cite{{{key}}}\n\\end{{document}}")


def test_a_pdf_with_no_identifier_that_is_no_published_work_is_copied_in_and_reads_as_a_work(tmp_path: Path) -> None:
    q = demo(tmp_path)
    pdf = _fake_pdf(tmp_path / NOTES, NOTES_TEXT)
    said = " ".join(ok("library", "add", pdf, *AS, cwd=q).stdout.split())
    assert 'as the new work Sta, titled "Statistics For Quants : Revision Notes", with its page text' in said, said
    entry = _entries(q)["Sta"]
    home = work_dir(q, entry)
    assert (home / "paper.pdf").read_bytes() == pdf.read_bytes()
    assert (home / "pages" / "0001.txt").is_file()
    assert entry.fields["loom-source"] == NOTES and entry.fields["loom-added"].endswith("A. Author")

    _cites(q, "Sta")
    lint = json_of("lint", "--json", cwd=q)
    codes = {d["code"] for d in lint["diagnostics"] if "Sta" in d.get("keys", [])}
    assert not codes & {"loom:unresolved-work", "loom:no-readable-copy"}, codes
    assert "Statistics For Quants" in ok("library", "read", "Sta", "1", cwd=q).stdout
    assert ok("library", "check", "Sta", cwd=q).stdout.startswith("nothing wrong")


def test_a_book_whose_entry_resolves_keeps_its_pdf_and_gets_its_author_from_the_file_name(tmp_path: Path) -> None:
    q = demo(tmp_path)
    pdf = _fake_pdf(tmp_path / BOOK, BOOK_TEXT)
    ok("library", "add", pdf, *AS, cwd=q)
    entry = _entries(q)["Shr"]
    assert entry.fields["author"] == "Shreve" and entry.fields["title"] == "Stochastic Calculus for Finance II"
    assert (work_dir(q, entry) / "paper.pdf").read_bytes() == pdf.read_bytes()


def test_the_entry_a_failed_add_left_behind_takes_the_pdf_when_it_is_given_again(tmp_path: Path) -> None:
    """The viewer wrote `@misc{Wor, title = {Stochastic Calculus for Finance II}}` and then refused the PDF as not showing it, which is how the author's quilt stands."""
    q = demo(tmp_path)
    with (q / BIB).open("a", encoding="utf-8") as fh:
        fh.write(
            "\n@misc{Wor,\n  title = {Stochastic Calculus for Finance II},\n  loom-added = {2026-11-04T23:43:32Z, The author},\n}\n"
        )
    pdf = _fake_pdf(tmp_path / BOOK, BOOK_TEXT)
    row = json_of("library", "add", pdf, *AS, "--json", cwd=q)["documents"][0]
    assert (row["citekey"], row["outcome"]) == ("Wor", "filed"), row
    assert (work_home(q, "Wor") / "paper.pdf").read_bytes() == pdf.read_bytes()
    assert set(_entries(q)) >= {"Wor"} and "Shr" not in _entries(q)


def test_naming_the_work_files_a_pdf_that_shows_nothing_of_it(tmp_path: Path) -> None:
    """The work's own upload: the person says what it is, and a page that does not say so stops nothing."""
    q = demo(tmp_path)
    pdf = _fake_pdf(tmp_path / "scan.pdf", "Some scan\n")
    said = " ".join(ok("library", "add", pdf, "--for", "Man12", *AS, cwd=q).stdout.split())
    assert "scan.pdf as Man12's PDF" in said and "on your word, though it does not show it is Man12" in said, said
    assert (work_home(q, "Man12") / "paper.pdf").read_bytes() == pdf.read_bytes()
    ledger = json.loads((q / ".loom/digests/storage/copied.json").read_text())
    row = next(v for v in ledger.values() if v["from"] == "scan.pdf")
    assert row["forced"].startswith("it does not show it is Man12") and row["by"] == "A. Author"
    assert "may not be their work" not in ok("library", "check", "Man12", cwd=q).stdout


def test_a_pdf_held_under_one_work_is_filed_under_another_the_person_names(tmp_path: Path) -> None:
    q = demo(tmp_path)
    pdf = _fake_pdf(tmp_path / NOTES, NOTES_TEXT)
    ok("library", "add", pdf, *AS, cwd=q)
    said = " ".join(ok("library", "add", pdf, "--for", "Man12", *AS, cwd=q).stdout.split())
    assert "as Man12's PDF" in said, said
    assert (work_home(q, "Man12") / "paper.pdf").read_bytes() == pdf.read_bytes()


def test_the_same_bytes_are_kept_once_and_two_documents_of_one_title_are_both_kept(tmp_path: Path) -> None:
    q = demo(tmp_path)
    pile = tmp_path / "pile"
    one = _fake_pdf(pile / "a.pdf", "Lecture notes on widgets\nfirst edition\n")
    (pile / "again.pdf").write_bytes(one.read_bytes())
    two = _fake_pdf(pile / "b.pdf", "Lecture notes on widgets\nsecond edition\n")
    data = json_of("library", "add", pile, *AS, "--json", cwd=q)
    assert data["filed"] == 2, data
    made = {k: e for k, e in _entries(q).items() if e.fields.get("title") == "Lecture notes on widgets"}
    assert len(made) == 2
    held = {(work_dir(q, e) / "paper.pdf").read_bytes() for e in made.values()}
    assert held == {one.read_bytes(), two.read_bytes()}


def test_a_title_corrected_by_hand_keeps_the_pdf(tmp_path: Path) -> None:
    q = demo(tmp_path)
    pdf = _fake_pdf(tmp_path / NOTES, NOTES_TEXT)
    ok("library", "add", pdf, *AS, cwd=q)
    edit(q / BIB, "Statistics For Quants : Revision Notes", "Statistics for Quants")
    assert (work_dir(q, _entries(q)["Sta"]) / "paper.pdf").read_bytes() == pdf.read_bytes()


def test_a_work_taken_out_and_given_again_is_filed_again(tmp_path: Path) -> None:
    from loom.refs.added import remove_entry
    from loom.refs.unreadable import declarations

    q = demo(tmp_path)
    pdf = _fake_pdf(tmp_path / NOTES, NOTES_TEXT)
    ok("library", "add", pdf, *AS, cwd=q)
    remove_entry(scan(load_quilt(q)), "Sta", "A. Author")
    assert "Sta" not in _entries(q) and "Sta" in declarations(q, "forget")
    said = " ".join(ok("library", "add", pdf, *AS, cwd=q).stdout.split())
    assert "as the new work Sta" in said, said
    assert (work_dir(q, _entries(q)["Sta"]) / "paper.pdf").read_bytes() == pdf.read_bytes()
    assert "Sta" not in declarations(q, "forget")
    # and gathering offers nothing for it
    assert "Sta" not in {
        a["key"] for a in json_of("library", "update", "--only", "gather", "--json", cwd=q)["scan"]["added"]
    }


def test_a_file_that_is_no_pdf_is_refused_by_name_and_the_rest_are_kept(tmp_path: Path) -> None:
    q = demo(tmp_path)
    pile = tmp_path / "pile"
    (pile).mkdir()
    (pile / "broken.pdf").write_text("<html>a login page</html>")
    _fake_pdf(pile / NOTES, NOTES_TEXT)
    assert not _is_pdf(pile / "broken.pdf")
    data = json_of("library", "add", pile, *AS, "--json", cwd=q)
    rows = {Path(r["file"]).name: r for r in data["documents"]}
    assert (rows["broken.pdf"]["outcome"], rows["broken.pdf"]["reason"]) == ("refused", "it is not a PDF")
    assert rows[NOTES]["outcome"] == "filed"


def _doi_says(title: str):
    """A transport standing in for doi.org: every DOI is the work `title`."""

    def http(url: str, headers: dict[str, str]) -> bytes:
        return json.dumps(
            {"title": title, "author": [{"family": "Writer", "given": "A."}], "DOI": "10.5555/x.1"}
        ).encode()

    return http


def _unreachable(url: str, headers: dict[str, str]) -> bytes:
    from loom.refs.resolve import ResolveRefused

    raise ResolveRefused(f"{url}: no route to host")


@pytest.mark.parametrize(
    ("http", "title", "doi"),
    [
        (_doi_says("Widget towers"), "Widget towers", "10.5555/x.1"),
        # the DOI its first pages carry is a citation: the record is another work's, so it says nothing about this one
        (_doi_says("A paper it merely cites"), "Widget towers", ""),
        (_unreachable, "Widget towers", "10.5555/x.1"),
    ],
)
def test_a_lookup_only_adds_what_it_can(tmp_path: Path, http, title: str, doi: str) -> None:
    q = demo(tmp_path)
    pdf = _fake_pdf(tmp_path / "towers.pdf", "Widget towers\nA. Writer\ndoi:10.5555/x.1\n")
    result = scan(load_quilt(q))
    filed = file_new(load_quilt(q), result.bib, pdf, "A. Author", came_from=pdf.name, online=True, http=http)
    assert filed["filed"] is True
    entry = _entries(q)[filed["citekey"]]
    assert entry.fields["title"] == title and entry.fields.get("doi", "") == doi
    assert (work_dir(q, entry) / "paper.pdf").read_bytes() == pdf.read_bytes()


def test_a_lookup_offline_is_not_asked_and_the_pdf_is_kept_with_what_it_shows(tmp_path: Path) -> None:
    q = demo(tmp_path)
    pdf = _fake_pdf(tmp_path / "towers.pdf", "Widget towers\nA. Writer\ndoi:10.5555/x.1\n")
    result = scan(load_quilt(q))
    seen = identify(q, result.bib, pdf)
    assert seen.offer == {"title": "Widget towers", "doi": "10.5555/x.1"} and not seen.best
    assert look_up("10.5555/x.1", result.bib, online=False).state == "offline"


def test_file_under_never_refuses_a_work_the_library_holds(tmp_path: Path) -> None:
    q = demo(tmp_path)
    pdf = _fake_pdf(tmp_path / "scan.pdf", "Nothing of it\n")
    result = scan(load_quilt(q))
    filed = file_under(load_quilt(q), result.bib, pdf, "Man12", "A. Author", came_from="scan.pdf")
    assert filed["filed"] is True and filed["citekey"] == "Man12" and "does not show it is" in filed["note"]
    assert (work_home(q, "Man12") / "paper.pdf").read_bytes() == pdf.read_bytes()


def test_a_title_comes_from_the_file_name_when_the_pdf_gives_none(tmp_path: Path) -> None:
    assert own_entry(_fake_pdf(tmp_path / NOTES, "\n"))["title"] == "Stats for Quants"
    assert own_entry(_fake_pdf(tmp_path / "1753634802.pdf", "\n"))["title"].startswith("Untitled PDF ")
    fields = own_entry(_fake_pdf(tmp_path / "Chapter 3 - Options.pdf", "\n"))
    assert fields["title"] == "Options" and "author" not in fields
    fields = own_entry(_fake_pdf(tmp_path / "Archak and Ipeirotis - Modeling Volatility.pdf", "\n"))
    assert fields["author"] == "Archak and Ipeirotis" and fields["title"] == "Modeling Volatility"


@pytest.mark.poppler
def test_a_scan_with_no_text_layer_is_kept_under_what_its_document_information_says(tmp_path: Path) -> None:
    """Casella and Berger's *Statistical Inference*, as the author's Zotero holds it: images of pages, no text at all, its title and authors in the PDF's own information."""
    q = demo(tmp_path)
    pdf = tmp_path / "casella_berger_statistical_inference1.pdf"
    pdf.write_bytes(
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
        b"4 0 obj<</Title(Statistical Inference)/Author(George Casella, Roger L. Berger)>>endobj\n"
        b"trailer<</Root 1 0 R/Info 4 0 R>>\n%%EOF\n"
    )
    said = " ".join(ok("library", "add", pdf, *AS, cwd=q).stdout.split())
    assert 'as the new work Cas, titled "Statistical Inference", without page text' in said, said
    entry = _entries(q)["Cas"]
    assert entry.fields["author"] == "George Casella and Roger L. Berger"
    assert (work_dir(q, entry) / "paper.pdf").read_bytes() == pdf.read_bytes()
    _cites(q, "Cas")
    codes = {d["code"] for d in json_of("lint", "--json", cwd=q)["diagnostics"] if "Cas" in d.get("keys", [])}
    assert not codes & {"loom:unresolved-work", "loom:no-readable-copy"}, codes
