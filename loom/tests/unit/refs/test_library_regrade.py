"""What the CLI re-grade found in `loom library` (plan 0.18.6): each finding's reproduction, as the appendix gives it."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.helpers import exits, json_of, ok, refused, run
from tests.unit._quilts import demo, mapped, new_session, propose, work_home

CK = "Calloway14"
RID = "Calloway14-prop-3.2"
AS = ("--as", "A. Author")
AGENT = {"AI_AGENT": "1"}


def _without_prop_3_2(q: Path) -> str:
    """The demo's digest with Proposition 3.2 cut out: what a fresh extraction that no longer states it would write."""
    text = (q / "digests" / f"{CK}.tex").read_text()
    start = text.index("\\begin{proposition}[{\\cite[Proposition 3.2")
    end = text.index("\\end{proposition}", start) + len("\\end{proposition}\n")
    return text[:start] + text[end:]


def _with_source(q: Path) -> None:
    src = work_home(q, CK) / "src"
    shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    (src / "paper.tex").write_text("\\documentclass{article}\n\\begin{document}\nCalloway.\n\\end{document}\n")


# --- 1.2: drop keeps what the author verified


def test_drop_then_redo_keeps_the_authors_verified_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The re-grade's reproduction: verify with an edit, drop the work, redo; the verified record and its text survive, and drop says it kept it."""
    from loom.refs.proposals import VERIFIED, load_results, state_of

    q = demo(tmp_path)
    without = _without_prop_3_2(q)
    monkeypatch.setattr("loom.digest.extract.extract_digest", lambda *_a, **_k: (without, None))
    _with_source(q)
    ok("library", "verify", RID, "--yes", "--statement", "Edited by the author: Fix is closed.", *AS, cwd=q)
    r = ok("library", "drop", "--work", CK, "--yes", cwd=q)
    assert r.stdout.startswith("dropped 4 records; kept 1 verified"), r.output
    left = load_results(q, CK)
    assert list(left) == [RID] and state_of(left[RID]) == VERIFIED
    assert ok("library", "why", RID, cwd=q).stdout.startswith(f"{RID}, verified by A. Author")
    ok("library", "update", CK, "--redo", "--only", "extract", cwd=q)
    assert "Edited by the author" in (q / "digests" / f"{CK}.tex").read_text()


def test_drop_session_keeps_a_verified_proposal_of_that_session(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    sid = new_session(q)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", session=sid)
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", session=sid)
    ok("library", "verify", f"{ck}-thm-1.1", "--yes", *AS, cwd=q)
    data = json_of("library", "drop", "--session", sid, "--yes", "--json", cwd=q)
    assert [d["id"] for d in data["dropped"]] == [f"{ck}-thm-4.1"] and data["kept"] == {"verified": 1}


# --- 1.9: --session resolved before anything prints or writes


@pytest.mark.parametrize(
    "args",
    [
        ("library",),
        ("library", "--json"),
        ("library", CK),
        ("library", "review"),
        ("library", "search", "involution"),
        ("library", "read", CK),
        ("library", "check"),
        ("library", "why", RID),
    ],
)
def test_an_unknown_session_is_refused_before_a_reader_prints(tmp_path: Path, args: tuple[str, ...]) -> None:
    q = demo(tmp_path)
    r = refused(*args, "--session", "nosuchsession", code=2, match="no session matches 'nosuchsession'", cwd=q)
    assert r.stdout == ""


def test_relate_records_its_actor_never_the_session(tmp_path: Path) -> None:
    q = demo(tmp_path)
    a, b = f"{CK}-def-3.1", RID
    r = refused(
        "library", "relate", a, b, "--kind", "same-notion", "--why", "x", "--session", "nosuchsession",
        code=2, match="no session matches", cwd=q,
    )  # fmt: skip
    assert r.stdout == "" and not (q / "digests" / "links.jsonl").exists()
    sid = new_session(q)
    made = json_of(
        "library", "relate", a, b, "--kind", "same-notion", "--why", "x", "--session", sid, *AS, "--json", cwd=q
    )
    assert made["link"]["by"] == "A. Author"
    # without --as, the reviewer; with none configured, refused by name rather than recorded as nobody
    third = f"{CK}-prop-3.3"
    refused("library", "relate", b, third, "--kind", "same-notion", "--why", "y", code=2, match="--as", cwd=q)
    import os

    config = Path(os.environ["XDG_CONFIG_HOME"]) / "loom" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('[author]\nname = "R. Reviewer"\n')
    other = json_of(
        "library", "relate", b, third, "--kind", "same-notion", "--why", "y", "--session", sid, "--json", cwd=q
    )
    assert other["link"]["by"] == "R. Reviewer"


def test_propose_records_who_proposed_it_with_as(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    sid = new_session(q)
    r = refused(
        "library", "propose", ck, "--local", "thm-1.1", "--page", "1", "--source-text", "Let $f$ be a DM-type morphism",
        "--statement", "Y", "--session", "nosuchsession", code=2, match="no session matches", cwd=q,
    )  # fmt: skip
    assert r.stdout == "" and not (q / "digests" / f"{ck}.results.json").exists()
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", session=sid, **{"as": "Reader Agent"})
    rec = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"][0]
    act = rec["origin"][0]
    assert act["act"] == "proposed" and act["by"] == "Reader Agent" and act["session"] == sid
    assert "proposed  Reader Agent" in ok("library", "why", f"{ck}-thm-1.1", cwd=q).stdout
    # a drop by session still finds it
    assert json_of("library", "drop", "--session", sid, "--yes", "--json", cwd=q)["dropped"]


# --- 4, K3


def test_locate_past_the_last_page_is_refused_by_name(tmp_path: Path) -> None:
    from tests.unit._quilts import showcase

    q = showcase(tmp_path)
    ck = next(p.name[: -len(".tex")] for p in (q / "digests").glob("*.tex") if p.name != "bibliography.tex")
    _ = ck
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    result = scan(load_quilt(q))
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map

    with_pdf = [
        k for k, e in result.bib.items() if (work_dir(q, e) / "paper.pdf").is_file() and read_map(work_dir(q, e))
    ]
    assert with_pdf
    ck = with_pdf[0]
    pages = read_map(work_dir(q, result.bib[ck])).pages  # type: ignore[union-attr]
    refused(
        "library", "locate", ck, "anything", "--page", str(pages + 900), code=2,
        match=f"{ck} has {pages} page", cwd=q,
    )  # fmt: skip


def test_import_refuses_a_name_that_is_not_a_citekey(tmp_path: Path) -> None:
    q = demo(tmp_path)
    src = tmp_path / "elsewhere.tex"
    src.write_text((q / "digests" / f"{CK}.tex").read_text())
    refused("library", "import", str(src), "--name", "bad name!", code=2, match="'bad name!' is not a citekey", cwd=q)
    assert not (q / "digests" / "bad name!.tex").exists()


@pytest.mark.parametrize(("typed", "meant"), [(("verfy",), "verify"), (("serch", "pullback"), "search")])
def test_a_mistyped_subcommand_naming_no_work_says_so(tmp_path: Path, typed: tuple[str, ...], meant: str) -> None:
    q = demo(tmp_path)
    refused("library", *typed, code=2, match=f"no such command or work: {typed[0]}; did you mean {meant}?", cwd=q)


def test_a_word_naming_a_work_is_still_that_works_report(tmp_path: Path) -> None:
    q = demo(tmp_path)
    assert ok("library", "callow", cwd=q).stdout.startswith(f"{CK}: cited by")


# --- 2: the byline reading

#: Page one of the Behrend–Fantechi PDF in the author's refs/, as its text layer reads: affiliation marks inline, and a stray comma before the second name.
BEHREND = (
    "Invent. math. 128, 45–88 (1997)\nc Springer-Verlag 1997\nThe intrinsic normal cone\nK. Behrend1 , B. Fantechi2\n"
    "1 University of British Columbia, Mathematics Department, 121–1984 Mathematics Road,\n"
    "2 Dipartimento di Matematica, Università di Trento, Via Sommarive 14, 38050 Povo, Italy\n"
    "Abstract. Let X be an algebraic stack in the sense of Deligne-Mumford.\n"
)
BEHREND_BIB = (
    "\n@article{behrend-fantechi_IntrinsicNormalCone1997, author={Behrend, K. and Fantechi, B.}, "
    "title={The intrinsic normal cone}, year={1997}}\n"
)
#: Page one of `Handbook of Moduli.pdf`, which the author's quilt stores under Olsson's entry: another work's, rightly refused.
HANDBOOK = (
    "Logarithmic Geometry and Moduli\nDan Abramovich, Qile Chen, Danny Gillam, Yuhao Huang,\n"
    "Martin Olsson, Matthew Satriano, and Shenghao Sun\nAbstract. We discuss the role played by logarithmic structures.\n"
)
OLSSON_BIB = (
    "\n@article{olsson03, author={Olsson, M}, title={Logarithmic Geometry and Algebraic Stacks}, year={2003}, "
    "doi={10.1016/j.ansens.2002.11.001}}\n"
)
OLSSON = "Logarithmic geometry and algebraic stacks\nMartin C. Olsson\nAnn. Sci. Ecole Norm. Sup.\n"


def _fake_pdf(path: Path, text: str) -> Path:
    """A PDF in the shape the fake toolchain's pdftotext reads (tests/fake_latex)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"%PDF-1.4\n%FAKE-LOOM\n%%Pages: 1\n{text}\n".encode())
    return path


@pytest.mark.parametrize(
    "byline",
    [
        "K. Behrend1 , B. Fantechi2",
        "K. Behrend*, B. Fantechi†",
        "K. Behrend¹, B. Fantechi²",
        ", K. Behrend‡ , B. Fantechi",
    ],
)
def test_a_byline_leads_with_its_first_name_whatever_marks_it(byline: str) -> None:
    from loom.refs.ingest import _leader

    assert _leader(byline) == "k behrend"


def test_add_files_the_behrend_fantechi_pdf_its_byline_marked_for_affiliations(tmp_path: Path) -> None:
    q = demo(tmp_path)
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write(BEHREND_BIB + OLSSON_BIB)
    pile = tmp_path / "pile"
    _fake_pdf(pile / "Behrend and Fantechi - 1997 - The intrinsic normal cone.pdf", BEHREND)
    _fake_pdf(pile / "Handbook of Moduli.pdf", HANDBOOK)
    r = run("library", "add", str(pile), "--dry-run", cwd=q)
    said = " ".join(r.stdout.split())
    assert "1 would be filed" in said, r.output
    assert "The intrinsic normal cone.pdf as behrend-fantechi_IntrinsicNormalCone1997's PDF" in said
    assert (
        "Handbook of Moduli.pdf: olsson03 is the nearest entry" in said
        and "its title is not olsson03's in full" in said
    )
    behrend = pile / "Behrend and Fantechi - 1997 - The intrinsic normal cone.pdf"
    ok("library", "add", str(behrend), "--for", "behrend-fantechi_IntrinsicNormalCone1997", cwd=q)


# --- 1.5: ignore holds, and a duplicate is cleared with it


def _olsson_with_a_second_version(tmp_path: Path) -> tuple[Path, str]:
    """The demo with olsson03 filed, and a second document of it dropped in refs/ and gathered as its version `olsson03A`: the shape of the Manolache entries in the author's quilt."""
    q = demo(tmp_path)
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write(OLSSON_BIB)
    ok(
        "library",
        "add",
        str(_fake_pdf(tmp_path / "one.pdf", OLSSON + "the journal's copy")),
        "--for",
        "olsson03",
        cwd=q,
    )
    _fake_pdf(
        q / "refs" / "Olsson - 2003 - Logarithmic geometry and algebraic stacks.pdf",
        OLSSON + "a preprint\fwith a page more",
    )
    r = ok("library", "update", "--only", "gather", cwd=q)
    assert "olsson03A" in r.stdout, r.output
    return q, "olsson03A"


def _delete_entry(q: Path, key: str) -> None:
    from loom.scan.bib import raw_entries

    bib = q / "digests" / "bibliography.bib"
    text = bib.read_text()
    bib.write_text(text.replace(raw_entries(text)[key], ""))


def test_a_version_set_aside_and_deleted_is_never_offered_again(tmp_path: Path) -> None:
    """The re-grade's Manolache reproduction: ignore the version, delete its entry, update; nothing comes back under any key."""
    q, dup = _olsson_with_a_second_version(tmp_path)
    ok("library", "ignore", dup, "--why", "the same paper as olsson03", *AS, cwd=q)
    _delete_entry(q, dup)
    before = (q / "digests" / "bibliography.bib").read_text()
    r = ok("library", "update", cwd=q)
    assert "new entries" not in r.stdout and "entries for stored documents" not in r.stdout, r.output
    assert (q / "digests" / "bibliography.bib").read_text() == before
    assert not list((q / "digests").glob("Olsson*.tex"))


def test_check_advises_ignore_for_a_duplicate_entry_and_ignore_clears_it(tmp_path: Path) -> None:
    q = demo(tmp_path)
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write("\n@misc{DupA, title={One}, loom-file={file/abc}}\n@misc{DupB, title={Two}, loom-file={file/abc}}\n")
    from loom.refs.pages import storage_root

    _fake_pdf(storage_root(q) / "file" / "abc" / "paper.pdf", "One\nA. Writer\n")
    out = exits(1, "library", "check", "DupA", cwd=q).stdout
    assert "entries that name one document (1)" in out
    assert "fix: loom library ignore DUP --why '…' sets the copy aside" in " ".join(out.split())
    ok("library", "ignore", "DupB", "--why", "DupA names it", *AS, cwd=q)
    after = run("library", "check", "DupA", "DupB", cwd=q)
    assert "entries that name one document" not in after.stdout, after.output
    _delete_entry(q, "DupB")
    r = ok("library", "update", "--only", "gather", cwd=q)
    assert "new entries" not in r.stdout and "entries for stored documents" not in r.stdout, r.output


# --- 2: a wrong document found by the strong rule, replaced by ignore then add


def _olsson_holding_the_handbook(tmp_path: Path) -> Path:
    """The demo with olsson03 holding *Logarithmic Geometry and Moduli*, as the old `refs add` filed it in the author's quilt."""
    q = demo(tmp_path)
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write(OLSSON_BIB)
    wrong = _fake_pdf(tmp_path / "Handbook of Moduli.pdf", HANDBOOK)
    ok("library", "add", str(wrong), "--for", "olsson03", "--force", *AS, cwd=q)
    return q


def test_check_names_a_stored_document_that_is_not_its_work_by_the_strong_rule(tmp_path: Path) -> None:
    """The handbook's first page shares enough words with Olsson's title to pass a fuzzy test; it fails the strong one, and check names it with the ignore-then-add pair."""
    q = _olsson_holding_the_handbook(tmp_path)
    out = " ".join(exits(1, "library", "check", "olsson03", cwd=q).stdout.split())
    assert "documents that may not be their work (1)" in out, out
    assert "its title is not olsson03's in full and Olsson does not lead its byline olsson03" in out
    assert (
        "loom library ignore WORK --why '…' sets it aside, then loom library add FILE --for WORK files the right one"
        in out
    )


def test_ignore_then_add_replaces_a_wrong_document(tmp_path: Path) -> None:
    from loom.refs.pages import read_page
    from loom.refs.unreadable import declarations

    q = _olsson_holding_the_handbook(tmp_path)
    right = _fake_pdf(q / "refs" / "Olsson - 2003 - Logarithmic geometry and algebraic stacks.pdf", OLSSON)
    # without the ignore, the right document goes beside the wrong one, never over it (book 8.16)
    dry = " ".join(ok("library", "add", str(right), "--for", "olsson03", "--dry-run", cwd=q).stdout.split())
    assert "beside its first document as olsson03A" in dry
    ok("library", "ignore", "olsson03", "--why", "it is Abramovich et al.'s survey", *AS, cwd=q)
    r = ok("library", "add", str(right), "--for", "olsson03", *AS, cwd=q)
    assert "in place of the document you set aside" in " ".join(r.stdout.split()), r.output
    home = work_home(q, "olsson03")
    assert (home / "paper.pdf").read_bytes() == right.read_bytes()
    assert (read_page(home, 1) or "").startswith("Logarithmic geometry and algebraic stacks")
    assert "olsson03" not in declarations(q, "forget")  # the work is no longer set aside; the handbook is
    assert ok("library", "check", "olsson03", cwd=q).stdout.startswith("nothing wrong")
    # and gathering does not offer the handbook, or the copy of the right one in refs/, an entry
    r = ok("library", "update", "--only", "gather", cwd=q)
    assert "new entries" not in r.stdout, r.output


# --- 2: add's next lines name a command that works for the case shown


def test_add_says_what_entry_a_document_naming_an_unknown_identifier_needs(tmp_path: Path) -> None:
    q = demo(tmp_path)
    pdf = _fake_pdf(tmp_path / "pile" / "new.pdf", "A paper nobody cites\nA. Writer\narXiv:2504.01234v1\n")
    said = " ".join(ok("library", "add", str(pdf.parent), "--dry-run", cwd=q).stdout.split())
    assert "it names arXiv:2504.01234v1, which no entry states" in said, said
    assert "eprint = {2504.01234v1}" in said and "--for WORK" not in said


def test_add_for_a_work_names_the_version_a_document_is(tmp_path: Path) -> None:
    """The Manolache preprint given `--for` the work: refused as its version's, naming `--for` that version."""
    q = demo(tmp_path)
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write(OLSSON_BIB + "\n@article{olsson03A, author={Olsson, M}, title={Logarithmic Geometry and Algebraic Stacks}, "
                 "year={2003}, eprint={0301.00001v1}, archiveprefix={arXiv}, loom-copy-of={olsson03}}\n")  # fmt: skip
    pdf = _fake_pdf(tmp_path / "preprint.pdf", OLSSON + "arXiv:0301.00001v1\n")
    r = refused("library", "add", str(pdf), "--for", "olsson03", code=2, match="it is olsson03A's", cwd=q)
    assert "loom library add FILE --for olsson03A" in " ".join(r.output.split()), r.output


def test_add_names_the_nearest_entry_with_force_for_a_document_it_cannot_confirm(tmp_path: Path) -> None:
    q = demo(tmp_path)
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write(OLSSON_BIB)
    pdf = _fake_pdf(
        tmp_path / "pile" / "Olsson - 2003 - Logarithmic geometry and algebraic stacks.pdf", "Some scan\nno byline\n"
    )
    said = " ".join(ok("library", "add", str(pdf.parent), "--dry-run", cwd=q).stdout.split())
    assert "olsson03 is the nearest entry" in said, said
    assert "loom library add FILE --for olsson03 --force files it there, if you know it is" in said


# --- 1.6: update reports this run's acts, and closes on library's counts


def test_an_offline_update_reports_what_it_did_and_not_what_is_on_disk(tmp_path: Path) -> None:
    """The demo holds a source, a PDF and a digest; an offline run fetched, extracted and looked up nothing, and says so."""
    q = demo(tmp_path)
    import re

    out = ok("library", "update", cwd=q).stdout
    for row in (
        "looked up  0  nothing looked up: offline",
        "fetched  0  nothing fetched: offline",
        "extracted  0",
        "mapped  0",
    ):
        assert re.search(row.replace("  ", r"\s+"), out), out
    assert "resolved" not in out and "1 source and 1 PDF" not in out, out


def test_update_closes_on_the_counts_library_reports(tmp_path: Path) -> None:
    """Two uncited works need the person in the demo, and `library` counts cited works only: update's last group says what `library` will list."""
    q = demo(tmp_path)
    lib = json_of("library", "--json", cwd=q)
    out = ok("library", "update", cwd=q).stdout
    assert f"{lib['need_you']} need you, {lib['need_an_agent']} an agent" in out.splitlines()[0], out
    assert "left for you and for an agent" not in out or (
        f"{lib['need_you']} works need you, {lib['need_an_agent']} an agent" in out
    )


# --- 4: check's moved-anchor fix clears when followed


def test_reverifying_a_moved_anchor_clears_the_finding(tmp_path: Path) -> None:
    """The re-grade's tampered page: check names the result, the author reads the page and verifies again, and the next check passes."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G")
    ok("library", "verify", f"{ck}-thm-4.1", "--yes", *AS, cwd=q)
    assert ok("library", "check", ck, cwd=q).stdout.startswith("nothing wrong")
    page = work_home(q, ck) / "pages" / "0012.txt"
    page.write_text("Theorem 4.1. Every widget is, under a perfect theory, a gadget.\n")
    out = exits(1, "library", "check", ck, cwd=q).stdout
    assert (
        f"verified results whose page no longer reads that way (1)\n  p.12 no longer reads that way  {ck}-thm-4.1"
        in out
    )
    ok("library", "verify", f"{ck}-thm-4.1", "--yes", *AS, cwd=q)
    assert ok("library", "check", ck, cwd=q).stdout.startswith("nothing wrong")
    # and a later change to the page is found again
    page.write_text("Theorem 4.1. Nothing of the kind.\n")
    exits(1, "library", "check", ck, cwd=q)


# --- 4: search says a state and a work's versions once per group


def test_search_says_extracted_by_loom_and_the_versions_once(tmp_path: Path) -> None:
    from tests.unit.refs.test_library_versions import _versioned

    q = _versioned(tmp_path)
    out = ok("library", "search", "involution", cwd=q).stdout
    assert "(extracted by loom)" not in out and "(also in" not in out, out
    assert "extracted by loom, best match first" in out, out
    assert (
        "also stated in another version (1)\n  " in out
        and "Calloway14A" in out.split("also stated in another version")[1]
    ), out


def test_search_pages_folds_a_works_versions(tmp_path: Path) -> None:
    """A work and its version holding the same page are one hit, under the work, with the version named once."""
    q, ck = mapped(tmp_path)
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write(
            f"\n@article{{{ck}A, title={{Virtual pull-backs}}, author={{Manolache, C.}}, year={{2012}}, loom-copy-of={{{ck}}}, loom-file={{file/v}}}}\n"
        )
    home, version = work_home(q, ck), work_home(q, f"{ck}A")
    shutil.copytree(home, version)
    out = ok("library", "search", "widget", "--pages", cwd=q).stdout
    assert out.startswith("1 hit in 1 of 2 works with page text"), out
    assert f"also on a version's page (1)\n  1 page in {ck}A  {ck}" in out, out


# --- 4, T6: check shows that it is alive


def test_check_names_its_stages_on_stderr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """13.6–16.9 s of silence on the author's quilt, nearly all of it comparing versions' PDFs. A clock that moves ten seconds a reading stands in for it."""
    import importlib
    import io
    import itertools

    from loom.cli.report import Progress

    said: list[str] = []
    ticks = itertools.count(0, 10)

    class Slow(Progress):
        def __init__(self, stage, total=None, **kw):  # type: ignore[no-untyped-def]
            self.out = io.StringIO()
            super().__init__(stage, total, stream=self.out, tty=False, clock=lambda: float(next(ticks)), ticking=False)

        def __exit__(self, *exc):  # type: ignore[no-untyped-def]
            super().__exit__(*exc)
            said.append(self.out.getvalue())

    monkeypatch.setattr(importlib.import_module("loom.cli.library.upkeep"), "Progress", Slow)
    q, _dup = _olsson_with_a_second_version(tmp_path)
    run("library", "check", cwd=q)
    for stage in ("re-reading verified anchors", "checking documents", "comparing versions", "linting"):
        assert stage in said[-1], said


def test_a_document_whose_entry_names_no_author_says_so(tmp_path: Path) -> None:
    """Li and Tian's gathered entry has a title and no author: the skip said "its first author is not in its byline", about an author nobody named."""
    q = demo(tmp_path)
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write(
            "\n@article{LiandTian1998Virtualmodu, title={Virtual moduli cycles and Gromov-Witten invariants of algebraic varieties}}\n"
        )
    pdf = _fake_pdf(
        tmp_path / "pile" / "Li and Tian - 1998.pdf",
        "VIRTUAL MODULI CYCLES AND GROMOV-WITTEN\nINVARIANTS OF ALGEBRAIC VARIETIES\nJUN LI AND GANG TIAN\nIntroduction\n",
    )
    said = " ".join(ok("library", "add", str(pdf.parent), "--dry-run", cwd=q).stdout.split())
    assert "LiandTian1998Virtualmodu names no author to look for in its byline" in said, said
    assert "first author is not in its byline" not in said


#: First pages from the author's refs/ and store, as their text layers read, each the work named; every one was refused or reported with a false reason.
BYLINES = [
    pytest.param(
        "@article{G17, author={Gross, Philipp}, title={Tensor Generators on Schemes and Stacks}}",
        "TENSOR GENERATORS ON SCHEMES AND STACKS\narXiv:1306.5418v2 [math.AG] 19 Jul 2015\nPHILIPP GROSS\nAbstract. We show.\n",
        id="an arXiv stamp between title and byline",
    ),
    pytest.param(
        "@book{ACGS25, author={Abramovich, Dan and Chen, Qile and Gross, Mark and Siebert, Bernd}, title={Punctured Logarithmic Maps}}",
        "MEMOIRS OF THE EUROPEAN MATHEMATICAL SOCIETY\nDan Abramovich\nQile Chen\nMark Gross\nBernd Siebert\nPunctured Logarithmic Maps\nMEMS Vol. 15 / 2025\n",
        id="one name a line above the title",
    ),
    pytest.param(
        "@article{HLP23, author={Halpern-Leistner, Daniel and Preygel, Anatoly}, title={Mapping stacks and categorical notions of properness}}",
        "MAPPING STACKS AND CATEGORICAL NOTIONS OF PROPERNESS\nDANIEL HALPERN-LEISTNER AND ANATOLY PREYGEL\nAbstract.\n",
        id="a surname of two words",
    ),
    pytest.param(
        "@article{Rom05, author={Romagny, Matthieu}, title={Group Actions on Stacks and Applications}}",
        "Michigan Math. J. 53 (2005)\nGroup Actions on Stacks and Applications\nM at th i e u Rom ag n y\nThe motivation.\n",
        id="letters spaced apart",
    ),
]


@pytest.mark.parametrize(("bib", "page"), BYLINES)
def test_a_byline_the_text_layer_sets_oddly_still_names_its_first_author(tmp_path: Path, bib: str, page: str) -> None:
    from loom.refs.ingest import identify_document
    from loom.scan.bib import parse_bib

    entries = parse_bib(bib)
    got = identify_document(_fake_pdf(tmp_path / "p.pdf", page), entries)
    assert [m.citekey for m in got.strong] == list(entries), got.weak


def test_the_session_log_holds_the_command_as_typed(tmp_path: Path) -> None:
    """`library search pullback --limit 1` was logged as `loom library search 1 pullback`; a relation's line put its reason before the results it relates."""
    from loom.sessions import files_dir, resolve

    q = demo(tmp_path)
    sid = new_session(q)
    ok("library", "search", "involution", "--limit", "1", "--session", sid, cwd=q)
    ok("library", "relate", f"{CK}-def-3.1", RID, "--kind", "same-notion", "--why", "x y", *AS, "--session", sid, cwd=q)
    log = (files_dir(q, resolve(q, sid)) / "run.log").read_text().splitlines()
    assert [line.split("  ", 1)[1] for line in log] == [
        "loom library search involution --limit 1",
        f"loom library relate {CK}-def-3.1 {RID} --kind same-notion --why 'x y' --as 'A. Author'",
    ]
