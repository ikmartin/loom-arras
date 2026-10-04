"""The quilt's reference layer (plan 0.12): which identifier a work is fetched on, the arrival check, and what `refs build` reports."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from loom.refs.fetch import ARRIVAL, arrival_score, arxiv_id, identifier_for, source_title
from loom.refs.resolve import Candidate, query_for, save
from loom.scan.bib import BibEntry, parse_bib
from tests.helpers import edit, exits, json_of, ok, refused, the
from tests.unit._quilts import SHOWCASE, demo, mapped, new_session, open_session, propose, showcase, work_home


def entry(**fields: str) -> BibEntry:
    return BibEntry(key=fields.pop("key", "X"), type="article", fields=fields)


def test_a_jstor_eprint_is_not_an_arxiv_id() -> None:
    """Two of relloc's four `eprint` fields are JSTOR stable ids, so a reader that takes `eprint` at face value doubles the arXiv coverage it reports."""
    assert arxiv_id(entry(eprint="0805.2065")) == "0805.2065"
    assert arxiv_id(entry(eprint="arXiv:0805.2065v2")) == "0805.2065v2"
    assert arxiv_id(entry(eprint="2205.11114", archiveprefix="arXiv")) == "2205.11114"
    assert arxiv_id(entry(eprint="25098611", eprinttype="jstor")) is None
    assert arxiv_id(entry(eprint="10.1000/x", eprinttype="doi")) is None
    assert arxiv_id(entry()) is None


def test_a_candidate_is_enough_to_fetch_with_and_never_the_identity(tmp_path: Path) -> None:
    """DR-122 keeps identity with the author; §4.3 lets a recorded candidate name what to download anyway."""
    q = demo(tmp_path)
    bare = entry(key="Unknown", title="Virtual pull-backs", author="Manolache, C.", year="2012")
    assert identifier_for(q, bare) == (None, "")
    save(
        q,
        bare,
        [
            Candidate(
                id="doi:10.1/x",
                source="crossref",
                confidence=0.97,
                title="Virtual pull-backs",
                also=["arxiv:0805.2065"],
            )
        ],
    )
    assert identifier_for(q, bare) == ("0805.2065", "candidate")
    # a declared identifier always wins: the author's own entry is the declaration (DR-122)
    declared_entry = entry(key="Unknown", title="Virtual pull-backs", eprint="1111.2222")
    assert identifier_for(q, declared_entry)[1] == "declared"


def test_the_arrival_check_reads_the_papers_own_title(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "ms.tex").write_text(
        "\\documentclass{article}\n\\title[short]{Virtual pull-backs of {G}romov--{W}itten classes}\n\\begin{document}\n"
    )
    assert source_title(src) == "Virtual pull-backs of {G}romov--{W}itten classes"
    q = query_for(entry(title="Virtual pull-backs of Gromov-Witten classes", author="Manolache, C.", year="2012"))
    got = arrival_score(q, src)
    assert got is not None and got >= ARRIVAL
    # the wrong paper under the right identifier is what the check exists to catch
    other = query_for(entry(title="The intrinsic normal cone", author="Behrend, K.", year="1997"))
    wrong = arrival_score(other, src)
    assert wrong is not None and wrong < ARRIVAL


def test_a_source_with_no_title_is_kept_not_rejected(tmp_path: Path) -> None:
    """None is not a failure: the check rejects a mismatch, it does not demand a match."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.tex").write_text("\\documentclass{amsart}\n\\begin{document}\nNo title here.\n")
    assert source_title(src) == ""
    assert arrival_score(query_for(entry(title="Anything")), src) is None


def test_build_json_orders_by_how_often_a_work_is_cited(tmp_path: Path) -> None:
    """Most of a real bibliography is cited rarely or not at all, so the report leads with the most-cited works; ties are alphabetical."""
    q = demo(tmp_path)
    # a work cited by two keys and named after every other, so only the counts can put it first
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write("\n@article{Zed20, title={Zeds}, author={Zed, A.}, year={2020}}\n")
    edit(q / "nodes" / "dm-0001.tex", "\\end{definition}", "See \\cite{Zed20}.\n\\end{definition}")
    edit(q / "nodes" / "dm-0002.tex", "\\end{lemma}", "See \\cite{Zed20} and \\cite[Theorem 1]{Zed20}.\n\\end{lemma}")
    works = json_of("library", "update", "--json", cwd=q)["works"]
    assert [(w["citekey"], w["cited_by"]) for w in works] == [
        ("Zed20", 2),
        ("Calloway14", 1),
        ("Har77", 0),
        ("Man12", 0),
    ]
    assert [w["citekey"] for w in works if w["digest"]] == ["Calloway14"], "the demo ships one digest"


def test_the_library_lists_only_what_a_person_must_look_at(tmp_path: Path) -> None:
    """A work with a document on disk is not a person's problem; a cited one with neither a document nor an identifier is, and one with an identifier needs only the network. Each cause names the command that clears it."""
    q = demo(tmp_path)
    node = q / "nodes" / "dm-0003.tex"
    node.write_text(node.read_text() + "\nCompare \\cite{Har77} and \\cite{Man12}.\n")
    rows = {w["citekey"]: w["needs"] for w in json_of("library", "--json", cwd=q)["works"]}
    assert rows == {"Calloway14": "", "Har77": "unidentified", "Man12": "offline"}
    said = ok("library", cwd=q).output
    assert "loom library add FILE --for WORK" in said and "loom library update --online" in said, said
    # and once every work has a document, it says so rather than printing nothing
    for ck in ("Har77", "Man12"):
        src = work_home(q, ck) / "src"
        src.mkdir(parents=True, exist_ok=True)
        (src / "main.tex").write_text("\\documentclass{article}\\begin{document}\\end{document}\n")
    got = json_of("library", "--json", cwd=q)
    assert got["need_you"] == 0 and [w["needs"] for w in got["works"]] == ["", "", ""]
    assert "; 0 need you" in ok("library", cwd=q).stdout.splitlines()[0]


def test_an_agent_may_run_the_mechanical_pass_and_not_the_authors_verbs() -> None:
    from loom.ai.layout import AGENT_COMMANDS

    assert {"library", "library update", "library read", "library check"} <= AGENT_COMMANDS
    assert not {"library add", "library verify", "library discard", "library ignore"} & AGENT_COMMANDS
    assert "accept" not in AGENT_COMMANDS


def test_a_contents_page_is_skipped_whole(tmp_path: Path) -> None:
    """Manolache's contents page lists every heading, so a line-by-line pass put a fifty-page paper entirely on page 1."""
    from loom.refs.pages import find_sections

    toc = "Contents\n1 Introduction . . . . . . . . . . 2\n2 Preliminaries . . . . . . . . . 4\n3 Results . . . . . . . . . . . . 9\n4 Applications . . . . . . . . . 14\n5 Appendix . . . . . . . . . . . 20\n"
    pages = [toc, "1 Introduction\nWe study widgets.", "", "2 Preliminaries\nLet X be a scheme."]
    secs = find_sections(pages)
    assert [(s.n, s.page) for s in secs] == [("1", 2), ("2", 4)]


def test_a_run_in_heading_is_cut_at_its_first_sentence() -> None:
    """Edidin and Graham set headings run-in, so a title taken whole swallowed the paragraph after it."""
    from loom.refs.pages import find_sections

    pages = [
        "1 Introduction. The purpose of this paper is to prove the localization theorem for equivariant Chow groups."
    ]
    assert [(s.n, s.title) for s in find_sections(pages)] == [("1", "Introduction")]


def test_mathematics_is_not_a_heading() -> None:
    """`C (F ) = Spec Sym(F )` and `E = C x_D X` are lines from this corpus that a bare-capital rule read as appendices."""
    from loom.refs.pages import find_sections

    pages = ["C (F ) = Spec Sym(F )\nE = C ×D,0 X ; then the sequence\n2 the diagram\n3 g is a DM-type morphism;"]
    assert find_sections(pages) == []


def test_section_numbers_do_not_go_backwards() -> None:
    from loom.refs.pages import find_sections

    pages = ["1 Introduction", "2 Setup", "9 Not a section here", "3 Results"]
    assert [s.n for s in find_sections(pages)] == ["1", "2", "3"]


def test_a_numbered_bibliography_is_not_a_section_list() -> None:
    """Behrend and Fantechi's reference list is numbered, and read as sections 8 through 20."""
    from loom.refs.pages import find_sections

    pages = [
        "1 Introduction",
        "2 Cones",
        "3 The intrinsic normal cone",
        "References",
        "8 Harris, J.: Algebraic Geometry\n9 Hartshorne, R.: Residues and Duality",
    ]
    got = [s.n or s.title for s in find_sections(pages)]
    assert got == ["1", "2", "3", "References"]


def test_map_and_coverage_need_no_pdf_to_be_useful(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = ok("library", "update", "--only", "map", cwd=q)
    assert "nothing new this run" in r.stdout.splitlines()[0] and "mapped  1  works from PDF text" in r.stdout
    c = json_of("library", "--json", cwd=q)
    assert sum(1 for w in c["works"] if w["pages"]) == 1, "the shipped page text is read with no PDF"


def test_the_page_text_is_committed_and_the_pdf_is_not(tmp_path: Path) -> None:
    """Plan 0.12 §4.2: an anchor is re-checkable by a coauthor who holds no PDF, which only works if the text is in the repository. The demo ships its own `.gitignore`, which must carry every store and seed-space rule `loom init` writes."""
    from importlib import resources

    q = demo(tmp_path)
    ignored = (q / ".gitignore").read_text()
    assert "digests/storage/**/paper.pdf" in ignored and "digests/storage/**/src/" in ignored
    assert "\nrefs/\n" in ignored, "the seed space is the author's pile of other people's PDFs"
    rules = [ln for ln in ignored.splitlines() if ln and not ln.startswith("#")]
    assert not any("pages" in ln for ln in rules), "the page text an anchor is checked against is committed"
    assert "refs/pdf/" not in ignored, "the store is digests/storage/<work-id>/, and refs/ is ignored whole"

    assets = resources.files("loom").joinpath("assets")
    canonical = assets.joinpath("init", "gitignore").read_text(encoding="utf-8")
    shipped = assets.joinpath("demo", ".gitignore").read_text(encoding="utf-8").splitlines()
    wanted = [ln for ln in canonical.splitlines() if ln.startswith(("refs/", "digests/storage"))]
    assert wanted, "init's .gitignore names the seed space and the store"
    assert [ln for ln in wanted if ln not in shipped] == [], "the demo's copy has drifted from init's"


def test_normalisation_joins_hyphenation_and_folds_ligatures() -> None:
    """Digest contract §9.5: this is the only sense in which a quotation "appears at" an anchor."""
    from loom.refs.search import find_in_page, normalize

    assert normalize("a perfect ob-\nstruction theory") == "a perfect obstruction theory"
    assert normalize("the ﬁrst ﬂat aﬃne") == "the first flat affine"
    assert normalize("X →  Y\n\n  Z") == "X → Y Z"
    assert normalize("morphism­") == "morphism"
    # case is kept: "let X be Finite" must not pass as the paper's words
    assert normalize("Let X Be") != normalize("let x be")
    assert find_in_page("...a perfect ob-\nstruction theory E...", "a perfect obstruction theory")


def test_locate_reads_bbox_output_that_is_not_valid_xml() -> None:
    """Every page of every paper in this corpus failed to parse: a math glyph lands on U+000F, which no XML parser accepts."""
    from loom.refs.search import locate_span

    page = (
        '<html xmlns="http://www.w3.org/1999/xhtml"><body><page>'
        '<word xMin="10.0" yMin="20.0" xMax="30.0" yMax="28.0">perfect</word>'
        '<word xMin="32.0" yMin="20.0" xMax="60.0" yMax="28.0">obstruction</word>'
        '<word xMin="62.0" yMin="20.0" xMax="80.0" yMax="28.0">theory.</word>'
        '<word xMin="82.0" yMin="20.0" xMax="88.0" yMax="28.0">\x0f</word>'
        "</page></body></html>"
    )
    got = locate_span(page, "perfect obstruction theory", 5)
    assert got is not None
    # the trailing period belongs to the word box, and a word-sequence match failed on exactly that
    assert got.quad == (10.0, 20.0, 80.0, 28.0) and got.words == 3
    assert locate_span(page, "not on this page", 5) is None


def test_a_page_search_searches_every_work_before_truncating(tmp_path: Path) -> None:
    """Stopping at the limit made the answer depend on citation order: the first papers filled it and the rest looked empty. Every work is searched, then the hits are cut taking each work's best page first, and the summary says how much of the corpus could be searched."""
    q, ck = mapped(tmp_path)
    # Calloway14 is cited and Vir12 is not, so Calloway14 is searched first; each holds more hits than the limit
    for home in (work_home(q, "Calloway14"), work_home(q, ck)):
        for n in (3, 4, 5):
            (home / "pages" / f"{n:04d}.txt").write_text("The zebra lemma holds here.\n")
    got = json_of("library", "search", "zebra lemma", "--pages", "--limit", "2", "--json", cwd=q)
    assert got["searched"] == 2 and got["truncated"] is True
    assert sorted(h["work"] for h in got["hits"]) == ["Calloway14", ck], got["hits"]
    said = ok("library", "search", "Zebra LEMMA", "--pages", "--limit", "2", cwd=q).stdout
    assert said.startswith("6 hits in 2 of 2 works with page text, showing 2"), said
    assert "3 pages  Calloway14" in said and f"3 pages  {ck}" in said, said
    assert f"loom library search 'Zebra LEMMA' --pages --work {ck} --limit 3" in said, said


def test_a_quotation_that_is_not_on_the_page_is_refused_with_the_page(tmp_path: Path) -> None:
    """Nothing is stored on failure and the page comes back, so the agent corrects itself in the turn it failed."""
    q, ck = mapped(tmp_path)
    propose(
        q, ck, "thm-4.1", 12, "Every widget is a doohickey", "X", code=1, match="Every widget is a gadget"
    )  # the page's own text must come back with the refusal
    assert not (q / "digests" / f"{ck}.results.json").exists()


def test_the_level_one_gate_is_about_order_not_derived_data(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "X", level="3", code=1, match="no level-1 result yet")
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "X", level="3")


def test_a_proposal_is_in_no_bundle_and_no_closure(tmp_path: Path) -> None:
    """The guarantee is structural: the file exists, loom scans it, and nothing inputs it (plan 0.12 §4.1)."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    shadow = q / "digests" / f"{ck}.proposed.tex"
    assert shadow.is_file() and not (q / "digests" / f"{ck}.tex").exists()
    for tex in q.rglob("*.tex"):
        if tex != shadow:
            assert shadow.name not in tex.read_text(), f"{tex} inputs the proposals file"


def test_verifying_moves_it_into_the_digest_and_records_both_parties(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", session="run:A")
    rid = f"{ck}-thm-1.1"
    r = ok("library", "verify", rid, "--statement", "Z", "--as", "isaac", "--yes", cwd=q)
    assert "faithful transcription" in r.output and "with your own rendering" in r.output
    assert not (q / "digests" / f"{ck}.proposed.tex").exists(), "the shadow file goes when nothing is proposed"
    assert "Z" in (q / "digests" / f"{ck}.tex").read_text()
    acts = [o["act"] for o in json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"][0]["origin"]]
    assert acts == ["proposed", "edited", "verified"], (
        "a record that credits an agent with your sentence cannot be audited"
    )


def test_an_edit_never_touches_the_anchor(tmp_path: Path) -> None:
    """The author edits `statement`; `source_text` and the anchor it names are untouched, so the node stays re-checkable."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    before = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"][0]
    ok("library", "verify", f"{ck}-thm-1.1", "--statement", "rewritten", "--as", "isaac", "--yes", cwd=q)
    after = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"][0]
    assert after["statement"] == "rewritten" and after["source_text"] == before["source_text"]
    assert after["anchor"] == before["anchor"]


def test_a_discard_is_returned_to_whatever_proposes_it_again(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    ok(
        "library",
        "discard",
        f"{ck}-thm-1.1",
        "--why",
        "that is the hypothesis, not the theorem",
        "--as",
        "i",
        cwd=q,
    )
    again = propose(
        q,
        ck,
        "thm-1.1",
        1,
        "Let $f$ be a DM-type morphism",
        "Y2",
        code=1,
        match="that is the hypothesis, not the theorem",
    )
    assert "--supersedes" in again.output
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y2", supersedes=f"{ck}-thm-1.1")


def test_the_manifest_keeps_the_digest_and_its_proposals_apart(tmp_path: Path) -> None:
    """Both files claim one citekey, and a `{ck: f}` comprehension keeps whichever came last — so the viewer could have rendered unverified statements as the digest."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    ok("library", "verify", f"{ck}-thm-1.1", "--as", "i", "--yes", cwd=q)
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3")
    ok("build", cwd=q)
    ref = json.loads((q / "build" / "manifest.json").read_text())["references"][ck]
    assert ref["digest"]["file"].endswith(f"{ck}.tex") and not ref["digest"]["file"].endswith(".proposed.tex")
    assert ref["proposed"]["file"].endswith(".proposed.tex")
    assert ref["proposed"]["nodes"] == [f"{ck}-thm-4.1"]
    # `statement` travels only for a proposal: that is the one claim a person is being asked to make
    assert "statement" in ref["results"][f"{ck}-thm-4.1"]
    assert "statement" not in ref["results"][f"{ck}-thm-1.1"]
    # `source_text` travels for both, because a verified transcription is exactly what a link's two ends are
    # compared by eye against (§7), and a page is the only thing either of them can be read against
    assert ref["results"][f"{ck}-thm-4.1"]["source_text"] and ref["results"][f"{ck}-thm-1.1"]["source_text"]
    assert ref["results"][f"{ck}-thm-1.1"]["state"] == "verified"


def test_proposed_is_a_state_the_whole_viewer_can_read(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    ok("build", cwd=q)
    m = json.loads((q / "build" / "manifest.json").read_text())
    assert "proposed" in m["states"]["labels"]
    assert m["keys"][f"{ck}-thm-1.1"]["state"] == "proposed"


def test_a_link_needs_a_kind_from_the_vocabulary_two_ends_and_a_reason(tmp_path: Path) -> None:
    """A closed vocabulary because a viewer can only draw what it can name; a sentence because an unexplained edge is noise."""
    from loom.refs.links import KINDS, add_link, read_links, remove_link

    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3")
    a, b = f"{ck}-thm-1.1", f"{ck}-thm-4.1"
    for bad, why in [("reminds-me-of", "x"), ("same-notion", "   ")]:
        try:
            add_link(q, a, b, bad, why, "isaac")
            raise AssertionError(f"{bad!r} with why={why!r} should have been refused")
        except ValueError:
            pass
    try:
        add_link(q, a, a, "same-notion", "itself", "isaac")
        raise AssertionError("a link to itself should have been refused")
    except ValueError:
        pass
    made = add_link(q, a, b, "generalises", "The first is stated for every DM-type morphism.", "isaac")
    assert made.id == "link-0001" and read_links(q)[0].why.startswith("The first")
    assert set(KINDS) == {"same-notion", "generalises", "specialises", "depends-on", "contradicts"}
    assert remove_link(q, made.id).id == made.id and read_links(q) == []


def test_links_are_never_citable_and_never_in_a_digest(tmp_path: Path) -> None:
    """Tier 3: navigation, not mathematics. Nothing about a link may reach a document."""
    from loom.refs.links import add_link

    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3")
    add_link(q, f"{ck}-thm-1.1", f"{ck}-thm-4.1", "depends-on", "Because.", "isaac")
    for tex in q.rglob("*.tex"):
        assert "link-0001" not in tex.read_text(), f"{tex} names a link"
    ok("build", cwd=q)
    m = json.loads((q / "build" / "manifest.json").read_text())
    assert [x["kind"] for x in m["links"]] == ["depends-on"]
    # a link is not an edge: it must not appear where the graph and the closure look
    assert not any(e.get("via") == "link" for e in m["edges"])


def test_the_link_cli_refuses_an_end_that_is_not_a_result(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    refused(
        "library",
        "relate",
        f"{ck}-thm-1.1",
        "nope-0001",
        "--kind",
        "same-notion",
        "--why",
        "w",
        code=2,
        match="no result nope-0001",
        cwd=q,
    )
    assert not (q / "digests" / "links.jsonl").exists()


def test_recheck_makes_transcription_verified_falsifiable(tmp_path: Path) -> None:
    """DR-172 gave the label; this gives it something to be wrong about (plan 0.12 §5.7)."""
    from loom.refs.fetch import work_dir
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    ok("library", "verify", f"{ck}-thm-1.1", "--as", "i", "--yes", cwd=q)
    clean = ok("library", "check", ck, cwd=q)
    assert clean.stdout.startswith("nothing wrong in 1 work; 1 verified anchor re-read")

    home = work_dir(q, scan(load_quilt(q)).bib[ck])
    page = home / "pages" / "0001.txt"
    page.write_text(page.read_text().replace("DM-type morphism", "DM-type map"))
    moved = exits(1, "library", "check", ck, cwd=q)
    assert "verified results whose page no longer reads that way (1)" in moved.output
    assert moved.stdout.startswith("1 problem in 1 work; 1 verified anchor re-read")


def test_recheck_never_re_reads_a_verified_rendering(tmp_path: Path) -> None:
    """A verified node's LaTeX was judged by a person once; re-judging it mechanically would claim a check that does not exist."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    ok("library", "verify", f"{ck}-thm-1.1", "--statement", "utterly different prose", "--as", "i", "--yes", cwd=q)
    r = ok("library", "check", ck, cwd=q)
    assert r.stdout.startswith("nothing wrong"), "the rendering may differ from the page and that is the author's call"


def test_every_search_says_how_much_of_the_corpus_it_could_search(tmp_path: Path) -> None:
    """A search over a partly digested corpus is a search over silence, and a result set that does not say so reads like a finding."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    hit = ok("library", "search", "DM-type", cwd=q)
    assert f"{ck}-thm-1.1" in hit.output
    assert "works digested" in hit.output.splitlines()[0]
    miss = ok("library", "search", "quantum cohomology of a gerbe", cwd=q)
    assert miss.stdout.startswith("0 results") and "works digested" in miss.output.splitlines()[0]
    assert "loom library search 'quantum cohomology of a gerbe' --pages" in miss.output, "a miss must name the fallback"


def test_a_more_specific_title_is_not_the_same_paper() -> None:
    """ "The Intrinsic Normal Cone" and "The Intrinsic Normal Cone for Artin Stacks" are two papers 27 years apart, and an unconditional prefix rule scored them as one."""
    from loom.refs.fetch import title_ratio

    assert title_ratio("The Intrinsic Normal Cone", "The Intrinsic Normal Cone for Artin Stacks") < 0.85
    # what the prefix rule is actually for: a subtitle one side omits
    assert title_ratio("Virtual pull-backs", "Virtual pull-backs.") == 1.0
    assert title_ratio("Cycle groups for Artin stacks", "Cycle groups for Artin stacks, I") == 1.0


def test_the_title_block_is_not_the_whole_page() -> None:
    """A paper that cites another paper's title was filed as that paper: Khan 2019 became Behrend-Fantechi 1997."""
    from loom.refs.ingest import TOP_LINES, title_lines

    page = "\n".join(
        ["Virtual fundamental classes", "Adeel Khan", "", "Abstract."]
        + [f"filler {i}" for i in range(40)]
        + ["The Intrinsic Normal Cone"]
    )
    found = title_lines(page)
    assert any("Virtual fundamental classes" in x for x in found)
    assert not any("Intrinsic Normal Cone" in x for x in found), f"the title block is the first {TOP_LINES} lines"


def test_a_filename_is_author_year_title() -> None:
    from loom.refs.ingest import filename_title

    assert filename_title("Behrend and Fantechi - 1997 - The intrinsic normal cone") == "The intrinsic normal cone"
    assert filename_title("Manolache - 2011 - Virtual pull-backs") == "Virtual pull-backs"
    assert filename_title("Virtual_classes") == "Virtual_classes"


def test_a_near_tie_is_a_question_not_an_answer() -> None:
    """Filing the wrong PDF confidently is the failure this command exists to avoid."""
    from loom.refs.ingest import Candidate, Signal

    clear = Candidate(
        path=Path("x.pdf"), sha256="a", signals=[Signal("title-on-page", "A", 0.95), Signal("first-author", "A", 0.5)]
    )
    assert clear.attachable and not clear.ambiguous
    tie = Candidate(
        path=Path("x.pdf"),
        sha256="a",
        signals=[
            Signal("title-on-page", "A", 0.9),
            Signal("first-author", "A", 0.5),
            Signal("title-on-page", "B", 0.88),
            Signal("first-author", "B", 0.5),
        ],
    )
    assert tie.ambiguous and not tie.attachable
    # an identifier read off the page is near-certain and does not need a second opinion
    ident = Candidate(path=Path("x.pdf"), sha256="a", signals=[Signal("doi", "A", 1.0)])
    assert ident.attachable


def test_a_pdf_on_disk_does_not_stop_loom_looking_for_the_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ingesting PDFs first made loom skip every work that had one, so on the real seed 13 works waited for an agent to read them when 12 of them had a source a machine could have extracted. A work with only a PDF is still looked up and still fetched, and the report keeps the PDF a fetch did not bring."""
    from loom.cli._quilt import open_scan
    from loom.refs import build
    from loom.refs.fetch import Fetched

    q, ck = mapped(tmp_path)  # Vir12 states no identifier
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write("\n@article{Dec13, title={Declared}, author={Dee, A.}, year={2013}, eprint={1301.00001}}\n")
    for key in (ck, "Dec13"):
        home = work_home(q, key)
        home.mkdir(parents=True, exist_ok=True)
        (home / "paper.pdf").write_bytes(b"%PDF-1.4\n")
    edit(q / "config.toml", "online = false", "online = true")

    asked: list[str] = []
    fetched: list[str] = []

    class Resolver:
        requests = 0

        def __init__(self, **_: object) -> None:
            pass

        def candidates(self, query: object) -> list[object]:
            asked.append(query.title)  # type: ignore[attr-defined]
            return []

    def fetch_work(quilt: object, citekey: str, entry: object, **_: object) -> Fetched:
        fetched.append(citekey)
        return Fetched(citekey, files=[Path("src/main.tex")], source=True, pdf=False, ident="arxiv:1301.00001")

    monkeypatch.setattr(build, "Resolver", Resolver)
    monkeypatch.setattr(build, "fetch_work", fetch_work)
    report = build.build_refs(open_scan(str(q)), only=(ck, "Dec13"), steps=("resolve", "fetch"))
    assert asked == ["Virtual pull-backs"], "a PDF is not a reason to stop looking for an identifier"
    assert fetched == ["Dec13"], "a PDF is not a reason to stop fetching the source"
    dec = the(report.works, lambda w: w.citekey == "Dec13", "work Dec13")
    assert dec.source and dec.pdf, "the PDF on disk is kept, though this fetch did not bring one"


def test_an_agent_cannot_vouch_for_its_own_reading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The first study run: an agent verified its own proposal and loom recorded the author as the verifier, because the author's name comes from git and an agent's shell shares it."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    monkeypatch.setenv("AI_AGENT", "1")
    for args in (
        ["library", "verify", f"{ck}-thm-1.1", "--yes"],
        ["library", "discard", f"{ck}-thm-1.1", "--why", "r"],
    ):
        r = refused(*args, code=2, match="AI_AGENT", cwd=q)
        assert "the author's" in r.output, r.output
    # with nothing declared, the marker refuses rather than guessing
    refused("accept", "dm-0002", code=2, match="AI_AGENT", cwd=q)
    # a declared agent is refused whatever shell it is in: the guard is on the identity, not the door
    refused("accept", "dm-0002", "--as", "Referee Agent", code=2, match="is an agent", cwd=q)
    # and under the marker the author's name is refused too: a name cannot be checked, and an agent typing it is the case to stop (DR-325-ikmartin)
    refused("accept", "dm-0002", "--as", "A. Author", code=2, match="whatever --author or --as says", cwd=q)
    # proposing is the agent's, and still works
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3")
    # and nothing was recorded as verified by anyone
    states = {r["id"]: r["state"] for r in json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"]}
    assert "verified" not in states.values()


def test_verifying_on_a_terminal_shows_both_texts_first(tmp_path: Path) -> None:
    """§5.3: a surface that offers verify without showing both texts is a bug, and a terminal is a surface."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "Every widget is a gadget.", level="1")
    r = ok("library", "verify", f"{ck}-thm-4.1", "--yes", "--as", "x", cwd=q)
    assert "--- the page" in r.output and "Theorem 4.1. Every widget is a gadget" in r.output
    assert "--- rendered as ---" in r.output
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    refused("library", "verify", f"{ck}-thm-1.1", "--as", "x", code=2, match="pass --yes", cwd=q)  # not a tty, no --yes


def test_the_page_around_the_quote_is_what_a_rendering_is_judged_against(tmp_path: Path) -> None:
    """An agent quotes only what the anchor needs; a ten-line rendering stood beside one clause and could not be judged."""
    from loom.refs.proposals import load_results, page_context

    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type", "A long rendering with much more in it.")
    r = load_results(q, ck)[f"{ck}-thm-1.1"]
    ctx, found = page_context(q, r)
    assert found and "perfect obstruction theory" in ctx, "the page carries the rest of the statement the quote cut off"


def test_a_result_stated_under_two_numbers_is_citable_by_either(tmp_path: Path) -> None:
    """Brion states Theorems 3.2 and 3.3 together; recorded as `thm-3.2-3.3` a citation to either matched nothing."""
    from loom.refs.proposals import numbers_of

    assert numbers_of("3.2, 3.3") == numbers_of("3.2-3.3") == ["3.2", "3.3"]
    assert numbers_of("3.2.1") == ["3.2.1"], "a dotted number is one number"
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", number="1.1, 1.2")
    tex = (q / "digests" / f"{ck}.proposed.tex").read_text()
    assert f"\\label{{{ck}-thm-1.1}}\\label{{{ck}-thm-1.2}}" in tex, (
        "the id is the first number and the rest are aliases"
    )


def test_coverage_finds_a_work_by_author_and_refuses_what_it_cannot(tmp_path: Path) -> None:
    """Agents grepped refs.bib for an author twice; with two Edidin-Graham 1998 papers, guessing chose between them."""
    q, ck = mapped(tmp_path)
    # two works share the author, so a report of one is refused naming both rather than guessed
    refused("library", "manolache", code=2, match=f"'manolache' names 2 works: Man12, {ck}", cwd=q)
    by_author = ok("library", "search", "perfect obstruction", "--pages", "--work", "manolache", cwd=q)
    assert ck in by_author.output
    refused("library", "FixedLocusRomagny", code=2, match="names no work", cwd=q)


def test_a_pdf_link_in_the_bibliography_is_fetchable() -> None:
    """Alper's lecture notes have no DOI and no arXiv id, only a URL; an agent asked for them, and drafts are where numbering drifts."""
    from loom.refs.fetch import pdf_url

    assert pdf_url(entry(url="https://sites.math.washington.edu/~jarod/moduli.pdf")).endswith("moduli.pdf")
    assert pdf_url(entry(url="https://example.org/paper.PDF?v=2"))
    assert pdf_url(entry(url="https://example.org/landing-page")) == "", "a landing page is not a PDF"
    assert pdf_url(entry(url="file:///etc/passwd.pdf")) == "", "only the web"
    assert pdf_url(entry()) == ""


def test_the_session_is_named_the_same_way_in_every_record(tmp_path: Path) -> None:
    """Provenance showed one run under two spellings, `ai/runs/X` and `X`; the id is one string and has no other form."""
    q, ck = mapped(tmp_path)
    sid = ok("session", "new", "--name", "fixed stacks", cwd=q).stdout.split()[0]
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", session=sid)
    origin = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"][0]["origin"]
    assert origin[0]["by"] == sid


def test_a_statement_that_brings_its_own_environment_is_refused(tmp_path: Path) -> None:
    """Thirteen of thirteen first attempts by two agents wrapped the statement in its own environment -- one had read a note about exactly this -- and loom wrapped it again."""
    q, ck = mapped(tmp_path)
    for bad in (
        r"\begin{theorem}Let $f$ be.\end{theorem}",
        r"Let $f$ be.\label{mine}",
        r"\begin{definition*}X\end{definition*}",
    ):
        propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", bad, code=1, match="body only")
    assert not (q / "digests" / f"{ck}.proposed.tex").exists()
    # an enumerate inside the body is the body, and is fine
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", r"Let $f$: \begin{enumerate}\item a\end{enumerate}")


def test_an_agents_link_is_the_runs_never_the_authors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Eleven links in the second study run were recorded as the author's, by way of git."""
    from loom.refs.links import read_links

    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3")
    a, b = f"{ck}-thm-1.1", f"{ck}-thm-4.1"
    monkeypatch.setenv("AI_AGENT", "1")
    link = ("library", "relate", a, b, "--kind", "depends-on", "--why", "w")
    refused(*link, code=2, match="--session", cwd=q)
    ok(*link, "--session", "2026-x", cwd=q)
    assert read_links(q)[0].by == "2026-x"


def test_a_statement_over_a_page_break_is_anchored_to_both_pages(tmp_path: Path) -> None:
    """A clause dropped from the continuation page was invisible on the surface built to catch it, because the anchor was one page."""
    from loom.refs.proposals import load_results, page_context

    q, ck = mapped(tmp_path)
    pages = work_home(q, ck) / "pages"
    (pages / "0012.txt").write_text("Theorem 4.1. Every widget is a gadget when\n")
    (pages / "0013.txt").write_text("the theory is perfect, and every gadget is a widget.\nProof. Clear.\n")
    # the quotation runs onto the next page, so one page cannot hold it
    propose(
        q,
        ck,
        "thm-4.1",
        12,
        "Every widget is a gadget when the theory is perfect",
        "X",
        code=1,
        match="that text is not on Vir12 p.12",
    )
    both = propose(q, ck, "thm-4.1", "12-13", "Every widget is a gadget when the theory is perfect", "X")
    assert "pp.12-13" in both.output, both.output
    r = load_results(q, ck)[f"{ck}-thm-4.1"]
    assert r.anchor.page == 12 and r.anchor.last == 13
    ctx, found = page_context(q, r)
    assert found and "every gadget is a widget" in ctx, "the continuation is on screen, where a dropped clause shows"
    assert "p.~12--13" in (q / "digests" / f"{ck}.proposed.tex").read_text()


def test_a_run_may_correct_its_own_unverified_proposal(tmp_path: Path) -> None:
    """Unable to withdraw its own mistake, an agent re-proposed under `-clean` ids: eleven results became twenty-two."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "first", session="R1")
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "second", session="R1", supersedes=f"{ck}-thm-1.1")
    rs = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"]
    assert len(rs) == 1 and rs[0]["statement"] == "second", "the same id, corrected -- not a second proposal"
    # another run may not overwrite it: that is not a correction, it is a disagreement for the author
    propose(
        q,
        ck,
        "thm-1.1",
        1,
        "Let $f$ be a DM-type morphism",
        "third",
        session="R2",
        supersedes=f"{ck}-thm-1.1",
        code=1,
        match="is already recorded",
    )


def test_an_authors_edit_is_kept_and_shown(tmp_path: Path) -> None:
    """ "edited by isaac" said an edit happened, not what it was; the edit was a dropped clause, the one thing worth learning from."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Let $f$ be DM.")
    ok(
        "library",
        "verify",
        f"{ck}-thm-1.1",
        "--statement",
        "Let $f$ be DM-type with a perfect theory.",
        "--yes",
        "--as",
        "i",
        cwd=q,
    )
    why = ok("library", "why", f"{ck}-thm-1.1", cwd=q)
    assert "the author's edit" in why.output
    assert "-Let $f$ be DM." in why.output and "+Let $f$ be DM-type with a perfect theory." in why.output
    # a second correction: the diff is still from what was proposed, never from the author's own first try
    ok("library", "verify", f"{ck}-thm-1.1", "--statement", "Let $f$ be DM-type.", "--yes", "--as", "i", cwd=q)
    why = ok("library", "why", f"{ck}-thm-1.1", cwd=q).output
    assert why.count("the author's edit") == 1
    assert "-Let $f$ be DM." in why and "+Let $f$ be DM-type." in why and "-Let $f$ be DM-type with" not in why
    # and the document has it: a re-verify once changed the record and left the digest -- and so `loom source` -- as it was
    digest = (q / "digests" / f"{ck}.tex").read_text()
    assert "Let $f$ be DM-type.\n" in digest and "perfect theory" not in digest
    assert "Let $f$ be DM-type." in ok("source", f"{ck}-thm-1.1", cwd=q).output


def test_a_book_length_map_with_almost_no_sections_says_it_is_a_guess() -> None:
    from loom.refs.pages import PageMap, Section

    book = PageMap(sha256="x", pages=679, sections=[Section("1", "See", 3), Section("2", "Grothendieck", 9)])
    paper = PageMap(sha256="x", pages=44, sections=[Section("1", "Introduction", 1)])
    assert book.suspect and not paper.suspect


def test_a_folio_number_at_a_page_join_is_not_part_of_the_text(tmp_path: Path) -> None:
    """Alper's book: a quotation over pp.353-354 matched only once the agent typed the printed page number "345" into it."""
    from loom.refs.pages import read_pages

    q, ck = mapped(tmp_path)
    home = work_home(q, ck)
    (home / "pages" / "0005.txt").write_text("Definition 5.1. A morphism is good\nif\n345\n")
    (home / "pages" / "0006.txt").write_text("346\n(1) it is exact, and\nso on\n7\nand on\n(2) widgets exist.\nend\n")
    text = read_pages(home, 5, 6) or ""
    assert "345" not in text and "346" not in text
    assert "\n7\n" in text, "a lone number inside a page is content, not a folio"
    propose(q, ck, "def-5.1", "5-6", "A morphism is good if (1) it is exact", "S")
    assert read_pages(home, 5, 5) == (home / "pages" / "0005.txt").read_text(), "one page is returned as it is"


def test_words_the_page_does_not_have_are_named(tmp_path: Path) -> None:
    """Five of thirteen Brion statements in the third study run carried the agent's own gloss, two of them word for word the second run's, after the orientation said "the paper's words only" -- and the author let one through."""
    from loom.refs.search import words_not_on_page

    q, ck = mapped(tmp_path)
    r = propose(
        q,
        ck,
        "thm-1.1",
        1,
        "Let $f$ be a DM-type morphism with a perfect obstruction theory.",
        r"Let $f$ be a DM-type morphism (where DM means Deligne--Mumford) with a perfect obstruction theory $E^\bullet$.",
    )
    assert "not in the quoted page text" in r.output and "Deligne" in r.output and "Mumford" in r.output
    # math, commands and the paper's own words are never flagged
    assert words_not_on_page(r"Let $\mathcal{X}$ be a \emph{DM-type} morphism.", "Let X be a DM-type morphism.") == []
    assert words_not_on_page("Every widget is a gadget.", "Every  wid-\nget is a gadget.") == []


def test_a_pending_proposal_carries_the_words_its_page_does_not_have(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Let $f$ be a nice DM-type morphism")
    ok("build", cwd=q)
    manifest = json.loads((q / "build" / "manifest.json").read_text())
    _, row = the(
        manifest["references"][ck]["results"].items(), lambda kv: kv[0].endswith("thm-1.1"), "result ending thm-1.1"
    )
    assert row["not_on_page"] == ["nice"]
    assert not row.get("page_images"), "no PDF on this machine: no image, and the viewer says so"


def test_a_work_with_no_pdf_gets_no_geometry(tmp_path: Path) -> None:
    """A page is drawn from the document that is there, or not at all: no document, no rectangles, and the viewer says so rather than drawing somewhere plausible. The sidecar is computed from the PDF on disk at build time, so there is no cache to go stale."""
    from loom.render.build import _attach_spans

    q, ck = mapped(tmp_path)
    home = work_home(q, ck)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "S")
    manifest = {"references": {ck: {"artifacts": {"dir": home.relative_to(q).as_posix(), "pdf": False}}}}
    files: dict[str, object] = {}
    _attach_spans(q, manifest, files)
    assert "spans" not in manifest["references"][ck]
    assert not files


def test_local_names_are_the_papers_numbering(tmp_path: Path) -> None:
    """Brion numbers corollaries within a subsection; the agent split 2.3's two and invented `cor-2.3-quotient`, which no citation by number can find (contract §3.2)."""
    q, ck = mapped(tmp_path)
    bad = propose(q, ck, "cor-2.3-quotient", 1, "Let $f$ be a DM-type morphism", "S", code=1, match="cor-2.3.1")
    assert "star-" in bad.output
    propose(
        q, ck, "thm-quotient", 1, "Let $f$ be a DM-type morphism", "S", code=1, match="is not the paper's own number"
    )
    for local in ("cor-2.3.1", "thm-A", "prop-A.2", "lem-star-1", "thm-7.5.11"):
        propose(q, ck, local, 1, "Let $f$ be a DM-type morphism", "S")


def test_propose_does_not_hand_an_agent_the_authors_verb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ "All 13 verified and are waiting": the agent reported the anchor check to the author in the author's own word (§5.6)."""
    q, ck = mapped(tmp_path)
    with monkeypatch.context() as agent:
        agent.setenv("AI_AGENT", "1")
        r = propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "S")
        assert "waiting for the author" in r.output and "loom library verify" not in r.output
    helptext = ok("library", "propose", "--help", cwd=q).output
    assert "verified against" not in helptext and "this is what is verified" not in helptext


def test_the_author_can_correct_the_locator_when_verifying(tmp_path: Path) -> None:
    """Brion's "Theorem 3.2" was the paper's Corollary 3.2.1; the author could fix the statement at verify time and not the name."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "S")
    ok(
        "library",
        "verify",
        f"{ck}-thm-1.1",
        "--local",
        "cor-1.1.1",
        "--taxon",
        "corollary",
        "--yes",
        "--as",
        "i",
        cwd=q,
    )
    recs = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"]
    assert [x["id"] for x in recs] == [f"{ck}-cor-1.1.1"] and recs[0]["taxon"] == "corollary"
    assert any(o.get("act") == "renamed" and o.get("was") == f"{ck}-thm-1.1" for o in recs[0]["origin"])
    assert f"{ck}-cor-1.1.1" in (q / "digests" / f"{ck}.tex").read_text()


def test_the_ingest_mode_says_one_thing_about_a_work_with_no_source() -> None:
    """Two sections of that name, one telling the agent to stop and one to propose: an agent reconciled them by guessing (CLAUDE.md passes 5 and 6)."""
    from importlib import resources

    text = (resources.files("loom") / "assets" / "ai" / "modes" / "ingest.md").read_text(encoding="utf-8")
    assert text.count("## When there is no source") == 1


def test_the_write_api_verifies_renames_and_discards_a_proposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The digest view's three verbs, through the functions the CLI calls; a click in the browser is the author's, so no agent marker stops it."""
    from loom.render.api import ApiError, handle

    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "S")
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3")
    with monkeypatch.context() as agent:
        agent.setenv("AI_AGENT", "1")
        got = handle(
            q, "library-verify", {"node": f"{ck}-thm-1.1", "statement": "S'", "local": "cor-1.1.1", "author": "i"}
        )
        assert got["ok"] and "renamed from" in got["result"]
        gone = handle(
            q,
            "library-discard",
            {"session": open_session(q), "node": f"{ck}-thm-4.1", "why": "not the paper's", "author": "i"},
        )
        assert gone["ok"]
    recs = {x["id"]: x for x in json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"]}
    assert recs[f"{ck}-cor-1.1.1"]["state"] == "verified" and recs[f"{ck}-cor-1.1.1"]["statement"] == "S'"
    assert recs[f"{ck}-thm-4.1"]["state"] == "discarded"
    with pytest.raises(ApiError):
        handle(q, "library-verify", {"session": open_session(q), "node": f"{ck}-thm-9.9", "author": "i"})


def test_a_work_with_a_source_is_quoted_from_its_source(tmp_path: Path) -> None:
    """Graber and Pandharipande's formula is control bytes in the PDF's text layer; the quotation stopped before it and the formula was written from memory. Their source has it verbatim."""
    q, ck = mapped(tmp_path)
    src = work_home(q, ck) / "src"
    src.mkdir(exist_ok=True)
    (src / "main.tex").write_text(
        "The localization formula is then:\n\\begin{equation}\n\\label{exloc} \\Xvir =\n\\iota_* \\sum  \\frac{\\Xivir}{e(N^{\\it{vir}}_i)}\n\\end{equation}\nin $A_*(X)$.\n",
        encoding="latin-1",
    )
    quote = "\\Xvir = \\iota_* \\sum \\frac{\\Xivir}{e(N^{\\it{vir}}_i)}"
    ok(
        "library", "propose", ck, "--local", "eq-1", "--source-file", "main.tex", "--level", "1",
        "--source-text", quote, "--statement", "[X]^{vir} = \\iota_* \\sum \\frac{[X_i]^{vir}}{e(N_i^{vir})}", cwd=q,
    )  # fmt: skip
    rec = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"][0]
    a = rec["anchor"]
    assert a["kind"] == "tex" and a["path"].endswith("src/main.tex") and "page" not in a
    raw = (q / a["path"]).read_bytes()
    assert raw[a["bytes"][0] : a["bytes"][1]].decode().split() == quote.split()
    assert rec["taxon"] == "equation" and rec["id"].endswith("-eq-1")
    shadow = (q / "digests" / f"{ck}.proposed.tex").read_text()
    assert "\\begin{theorem}[{\\cite[Equation (1)]{" in shadow, "a display is named as the paper names it"
    refused(
        "library", "propose", ck, "--local", "eq-2", "--source-file", "main.tex",
        "--source-text", "a formula the file does not have", "--statement", "x", code=1, match="not in", cwd=q,
    )  # fmt: skip
    refused("library", "propose", ck, "--local", "eq-3", "--source-file", "main.tex", "--page", "1",
            "--source-text", "x", "--statement", "x", code=2, match="one of them", cwd=q)  # fmt: skip


def test_search_is_literal_words_and_says_so(tmp_path: Path) -> None:
    """ "Localization in equivariant\\|Edidin.*Graham" found nothing, and the agent took the silence for an answer."""
    q, _ck = mapped(tmp_path)
    pattern = "Localization in equivariant\\|Edidin.*Graham"
    refused("library", "search", pattern, code=2, match="matches words literally", cwd=q)
    refused("library", "search", pattern, "--pages", code=2, match="matches words literally", cwd=q)
    ok("library", "search", "widget", "--pages", cwd=q)


def test_a_source_fetched_on_a_preprint_id_says_so_in_the_digest(tmp_path: Path) -> None:
    """Chang, Kiem and Li's source came from arXiv into the work's DOI directory, and the digest claimed the DOI: DR-109's version warning never fired, while the preprint's Theorem 3.4 is the published Theorem 3.5 and its conclusion differs."""
    from loom.refs.fetch import record_source

    q, ck = mapped(tmp_path)
    home = work_home(q, ck)
    (home / "src").mkdir(exist_ok=True)
    (home / "src" / "main.tex").write_text(
        "\\documentclass{article}\n\\newtheorem{theorem}{Theorem}\n\\begin{document}\n\\begin{theorem}\\label{t}A.\\end{theorem}\n\\end{document}\n"
    )
    record_source(home, "arxiv:1607.00001", "candidate")
    ok("library", "update", ck, "--only", "extract", cwd=q)
    head = (q / "digests" / f"{ck}.tex").read_text().splitlines()[:5]
    assert "% !LOOM extracted-from: arxiv:1607.00001" in head
    # the entry declares no identifier, so what it cites is the work itself, which a lookup's preprint may not be (audit §5)
    from loom.refs.identity import synthetic
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    work = str(synthetic(scan(load_quilt(q)).bib[ck]))
    assert f"% !LOOM published-as: {work}" in head
    row = json_of("library", ck, "--json", cwd=q)["work"]
    assert row["digest_version"] == {"extracted_from": "arxiv:1607.00001", "cited_as": work}
    assert (
        "read from arxiv:1607.00001; the bibliography cites a version it does not identify"
        in ok("library", "why", f"{ck}-thm-1", cwd=q).stdout
    )


def test_a_read_command_logs_to_the_session_it_is_given(tmp_path: Path) -> None:
    """`loom refs page ... --run` was refused twice in one study run; the orientation says to pass --session wherever it is accepted, and the log is the record of what an agent read."""
    q, ck = mapped(tmp_path)
    runname = ok("session", "new", "--name", "r", cwd=q).stdout.split()[0]
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    for args in (["library", "read", ck, "12"], ["library", "why", f"{ck}-thm-1.1"], ["library", "search", "widget"]):
        ok(*args, "--session", runname, cwd=q)
    log = (q / ".loom" / "sessions" / runname / "run.log").read_text()
    assert f"loom library read {ck} 12" in log and f"loom library why {ck}-thm-1.1" in log
    assert "loom library search widget" in log


def test_locate_matches_across_the_two_extractions_of_one_page() -> None:
    """`pages/NNNN.txt` is plain `pdftotext` and the boxes are `-bbox-layout`: two readings of one page that disagree about spacing around mathematics and about a hyphen a line break left behind. Measured over five documents, matching under `normalize` alone placed 81% of quotations and 47% on a real arXiv paper; dropping spaces and hyphens from both sides placed 100%."""
    from loom.refs.search import locate_span

    page = (
        "<html><body><page>"
        '<word xMin="10.0" yMin="20.0" xMax="30.0" yMax="28.0">polytope</word>'
        '<word xMin="32.0" yMin="20.0" xMax="44.0" yMax="28.0">M (D)</word>'
        '<word xMin="46.0" yMin="20.0" xMax="52.0" yMax="28.0">⊆</word>'
        '<word xMin="54.0" yMin="20.0" xMax="58.0" yMax="28.0">R</word>'
        '<word xMin="58.0" yMin="16.0" xMax="62.0" yMax="22.0">A</word>'
        '<word xMin="64.0" yMin="20.0" xMax="78.0" yMax="28.0">cut</word>'
        '<word xMin="10.0" yMin="40.0" xMax="36.0" yMax="48.0">denom-</word>'
        '<word xMin="38.0" yMin="40.0" xMax="70.0" yMax="48.0">inators</word>'
        "</page></body></html>"
    )
    # the superscript is its own word box, so the page text's `RA` is `R A` here
    assert locate_span(page, "polytope M (D) ⊆ RA cut", 2) is not None
    # and the line break leaves a hyphen the plain extraction has already joined
    assert locate_span(page, "denominators", 2) is not None
    assert locate_span(page, "a phrase this page does not carry", 2) is None


def test_a_quotation_over_two_lines_is_one_rectangle_per_line() -> None:
    """A union box over three lines swallows the column between them, so a highlight is drawn from one rectangle per line; the subscript on the first line stays with it rather than becoming a line of its own."""
    from loom.refs.search import locate_span

    page = (
        "<html><body><page>"
        '<word xMin="10.0" yMin="20.0" xMax="30.0" yMax="28.0">the</word>'
        '<word xMin="32.0" yMin="22.0" xMax="36.0" yMax="26.0">rank</word>'
        '<word xMin="10.0" yMin="40.0" xMax="48.0" yMax="48.0">is</word>'
        '<word xMin="50.0" yMin="40.0" xMax="70.0" yMax="48.0">free</word>'
        "</page></body></html>"
    )
    got = locate_span(page, "the rank is free", 1)
    assert got is not None
    assert got.quad == (10.0, 20.0, 70.0, 48.0)  # the union is still there for a caller that wants one number
    assert got.lines == [(10.0, 20.0, 36.0, 28.0), (10.0, 40.0, 70.0, 48.0)]


def test_the_anchor_check_stays_strict_while_geometry_is_loose() -> None:
    """Looseness is for drawing only: a highlight two lines off is visible, and a transcription wrongly called faithful is not."""
    from loom.refs.search import find_in_page

    assert find_in_page("the rank of the kernel", "rank of the")
    assert not find_in_page("the rank of the kernel", "rankofthe")


def test_offsets_and_box_text_come_from_the_page_as_committed() -> None:
    """A reader's selection arrives from the viewer's own text layer, a third extraction after the committed page text and the word boxes, so the offsets are found under the same tolerance the geometry is; and they index the raw text, which is what a coauthor with no PDF checks against."""
    from loom.refs.search import locate_offsets, words_in_boxes

    page = "Let Q be a quiver whose\nunderlying graph has c connected components, and let W(Q)\n"
    got = locate_offsets(page, "underlying graph has c connected components")
    assert got is not None
    assert page[got[0] : got[1]] == "underlying graph has c connected components"
    # spacing around mathematics differs between extractions, and the offsets are still the raw ones
    spaced = locate_offsets(page, "hasc connected")
    assert spaced is not None and page[spaced[0] : spaced[1]] == "has c connected"
    assert locate_offsets(page, "a phrase this page does not carry") is None

    boxes = (
        "<html><body><page>"
        '<word xMin="10.0" yMin="20.0" xMax="30.0" yMax="28.0">inside</word>'
        '<word xMin="32.0" yMin="20.0" xMax="50.0" yMax="28.0">the</word>'
        '<word xMin="10.0" yMin="90.0" xMax="30.0" yMax="98.0">outside</word>'
        "</page></body></html>"
    )
    assert words_in_boxes(boxes, [[8.0, 18.0, 52.0, 30.0]]) == "inside the"


def test_locate_refuses_what_it_cannot_answer(tmp_path: Path) -> None:
    """The endpoint writes nothing, so its whole contract is the answer and the refusals: a work nobody cites, a work with no copy here, and a request that selected neither text nor a region."""
    from loom.render.api import ApiError, handle

    q, ck = mapped(tmp_path)  # page text on disk, no PDF beside it
    for body, code in (
        ({"citekey": "Nope", "page": 1, "text": "x"}, "no-such-work"),
        ({"citekey": ck, "page": 1}, "missing-field"),
        ({"citekey": ck, "page": 0, "text": "x"}, "bad-field"),
        ({"citekey": ck, "page": 1, "text": "x"}, "not-readable"),
    ):
        with pytest.raises(ApiError) as exc:
            handle(q, "locate", body)
        assert exc.value.code == code, body


@pytest.mark.poppler
def test_a_selection_on_a_real_page_becomes_an_anchor(tmp_path: Path) -> None:
    """The whole of plan 0.13's slice on the loom side: what a reader selected, mapped against the committed page text and the word boxes of the one PDF this repository carries.

    On a copy, because reading a page caches its word boxes inside the quilt, and the checked-in one is compared to the generator's output file by file.
    """
    from loom.render.api import handle

    q = showcase(tmp_path)
    text = "The median orders of a weighted digraph are in bijection with the vertices"
    got = handle(q, "locate", {"citekey": "Bellamy19", "page": 2, "text": text})
    a = got["anchor"]
    assert a["basis"] == "text" and a["page"] == 2 and a["quads"], got["result"]
    page_text = (q / "digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt").read_text()
    assert page_text[a["start"] : a["end"]] == text
    assert got["page_box"] == {"width": 612.0, "height": 792.0}  # US Letter, in points

    # a region the reader drew: geometry of record, and the words under it as an unreliable hint
    box = handle(q, "locate", {"citekey": "Bellamy19", "page": 2, "rects": [[82.0, 278.0, 530.0, 292.0]]})
    assert box["anchor"]["basis"] == "box" and "start" not in box["anchor"]
    assert "quasi-polynomial" in box["text"]


# --- The artifact invariant (plan 0.13 §4) -------------------------------------------------------------------
#
# The demo quilt holds a digest and a real document behind it, so each state the invariant is about is made here by
# taking something away. Constructing it rather than borrowing it is what keeps these tests from moving when the demo
# does.


def _no_copy(tmp_path: Path) -> Path:
    """The demo quilt with its cited work's document removed: a digest with nothing behind it."""
    import shutil

    q = demo(tmp_path)
    shutil.rmtree(q / "digests" / "storage" / "doi" / "10.4171_demo_14-1")
    return q


def _source_only(tmp_path: Path) -> Path:
    """The demo quilt with the PDF and page text removed, and the paper's LaTeX left in place."""
    import shutil

    (tmp_path / "b").mkdir(exist_ok=True)
    q = demo(tmp_path / "b")
    home = q / "digests" / "storage" / "doi" / "10.4171_demo_14-1"
    source = (
        Path(__file__).resolve().parents[2] / "tests" / "quilts" / "sources" / "demo-works" / "calloway-fixed-loci.tex"
    )
    (home / "src").mkdir(exist_ok=True)
    shutil.copy2(source, home / "src" / source.name)
    (home / "paper.pdf").unlink()
    (home / "sections.json").unlink()
    shutil.rmtree(home / "pages")
    return q


def test_extract_reads_the_store_alone(tmp_path: Path) -> None:
    """A digest made from a file on the author's desktop cites pages nobody else can open, so extraction reads only what the store holds, and a source the author holds reaches it through `library add`."""
    q = _no_copy(tmp_path)
    (q / "digests" / "Calloway14.tex").unlink()
    loose = tmp_path / "paper.tex"
    loose.write_text("\\documentclass{article}\\begin{document}\\end{document}\n", encoding="utf-8")
    r = ok("library", "update", "Calloway14", "--only", "extract", cwd=q)
    assert not (q / "digests" / "Calloway14.tex").exists() and "loom library add FILE --for CITEKEY" in r.stdout
    ok("library", "add", loose, "--for", "Calloway14", cwd=q)
    ok("library", "update", "Calloway14", "--only", "extract", cwd=q)
    assert (q / "digests" / "Calloway14.tex").is_file()


def test_extract_with_no_source_says_how_to_get_one(tmp_path: Path) -> None:
    """A work with no source names both routes: fetching where an identifier serves it, and adding source already held."""
    q = _no_copy(tmp_path)
    (q / "digests" / "Calloway14.tex").unlink()
    r = ok("library", "update", "Calloway14", "--only", "extract", cwd=q)
    said = " ".join(r.stdout.split())
    assert "blocked: no arXiv id to fetch a source on (1) Calloway14" in said, r.stdout
    assert "loom library update --online looks for the preprint" in said
    assert "loom library add FILE --for CITEKEY with its LaTeX source" in said


def test_a_digest_with_no_readable_copy_warns_and_never_errors(tmp_path: Path) -> None:
    """Loom cannot fetch without consent, so renderable content nothing can back is reported and never fatal."""
    q = _no_copy(tmp_path)
    said = [d for d in json_of("lint", "--json", cwd=q)["diagnostics"] if d["code"] == "loom:no-readable-copy"]
    assert [d["severity"] for d in said] == ["warning"]
    assert "loom library ignore Calloway14" in said[0]["message"]
    # and source alone is an info, not a warning: the paper's own LaTeX is what a statement is checked against
    quieter = [
        d
        for d in json_of("lint", "--json", cwd=_source_only(tmp_path))["diagnostics"]
        if d["code"] == "loom:no-readable-copy"
    ]
    assert [d["severity"] for d in quieter] == ["info"]
    assert "no PDF" in quieter[0]["message"]


def test_declaring_a_work_unreadable_suppresses_the_lint_and_undo_restores_it(tmp_path: Path) -> None:
    """Impossible is declared, never inferred: nothing in a bibliography entry says a work has no fixed document."""
    q = _no_copy(tmp_path)
    ok(
        "library",
        "ignore",
        "Calloway14",
        "--as",
        "A. Author",
        "--why",
        "a living work with no fixed version",
        cwd=q,
    )
    codes = [d["code"] for d in json_of("lint", "--json", cwd=q)["diagnostics"]]
    assert "loom:no-readable-copy" not in codes
    ok(
        "library",
        "ignore",
        "Calloway14",
        "--as",
        "A. Author",
        "--undo",
        "--why",
        "a version was published after all",
        cwd=q,
    )
    codes = [d["code"] for d in json_of("lint", "--json", cwd=q)["diagnostics"]]
    assert "loom:no-readable-copy" in codes


def test_the_declaration_is_appended_and_never_edited(tmp_path: Path) -> None:
    """Every record loom keeps is appended; the standing claim is the fold, so the reversal is still readable."""
    from loom.refs.unreadable import declarations, load_events

    q = _no_copy(tmp_path)
    ok("library", "ignore", "Calloway14", "--as", "A. Author", "--why", "no fixed version", cwd=q)
    ok("library", "ignore", "Calloway14", "--as", "A. Author", "--undo", "--why", "wrong", cwd=q)
    assert len(load_events(q)) == 2
    assert declarations(q, "unreadable") == {}


def test_unreadable_refuses_under_an_agent_and_without_a_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whether a work can be obtained at all is a claim about the world, which is the author's to make (DR-185).

    Under an agent marker the act refuses whatever name is declared, since a name cannot be checked (DR-325-ikmartin); a name that calls itself an agent is refused whatever shell it came from.
    """
    q = demo(tmp_path)
    refused("library", "ignore", "Calloway14", code=2, match="Missing option '--why'", cwd=q)
    monkeypatch.setenv("AI_AGENT", "1")
    # nothing declared: the marker is all there is to go on, and it refuses rather than guessing
    refused(
        "library",
        "ignore",
        "Calloway14",
        "--why",
        "no fixed version",
        code=2,
        match="agent is running this shell",
        cwd=q,
    )
    # nor does the author's name pass under the marker
    refused(
        "library", "ignore", "Calloway14", "--as", "A. Author", "--why", "no fixed version",
        code=2, match="whatever --author or --as says", cwd=q,
    )  # fmt: skip
    # and a declared agent is refused whichever surface it came through
    refused(
        "library",
        "ignore",
        "Kre99",
        "--as",
        "Agent",
        "--why",
        "could not fetch",
        code=2,
        match="is an agent",
        cwd=q,
    )


def test_ignore_sets_a_document_aside_by_citekey_or_by_a_prefix_of_a_stored_hash(tmp_path: Path) -> None:
    """The tombstone stops the store re-offering an entry; a document with no entry is named by its content."""
    from loom.refs.scan import record_copy
    from loom.refs.unreadable import declarations

    q = demo(tmp_path)
    sha = "9f2c" + "0" * 60
    record_copy(q, sha, "refs/whatever.pdf", "digests/storage/file/9f2c/paper.pdf")
    ok("library", "ignore", "9f2c00", "--as", "A. Author", "--why", "a duplicate scan", cwd=q)
    ok("library", "ignore", "Calloway14", "--as", "A. Author", "--why", "deliberately not cited", cwd=q)
    assert set(declarations(q, "forget")) == {f"sha256:{sha}", "Calloway14"}
    refused(
        "library",
        "ignore",
        "nothing-like-this",
        "--as",
        "A. Author",
        "--why",
        "x",
        code=2,
        match="names no work",
        cwd=q,
    )


def test_source_alone_is_enough_to_extract_from_and_a_work_with_neither_is_blocked(tmp_path: Path) -> None:
    """Source is the paper's own LaTeX and better evidence than a page image; what it cannot give is pagination."""
    from loom.cli._quilt import open_scan
    from loom.refs.build import survey
    from loom.refs.fetch import work_dir

    q = _no_copy(tmp_path)
    (q / "digests" / "Calloway14.tex").unlink()
    result = open_scan(str(q))
    src = work_dir(q, result.bib["Calloway14"]) / "src"
    src.mkdir(parents=True)
    (src / "main.tex").write_text("\\documentclass{article}\\begin{document}\\end{document}\n", encoding="utf-8")
    work = the(survey(open_scan(str(q))), lambda w: w.citekey == "Calloway14", "surveyed work Calloway14")
    assert work.source and not work.pdf
    assert work.blocked == ("", "")  # source is enough to extract from; the missing page is the lint's business


def test_an_extracted_result_is_located_on_the_page_it_is_printed_on() -> None:
    """**A digest node points into the paper, not only at its own source** (plan 0.13.2).

    The page is found in the work's committed page text, so it holds whether or not the paper compiled: the showcase extracts with `--no-compile`, and every result still carries the page it is printed on. What is recorded is a page whose text carries the result, never the `.aux`'s claim taken on trust.
    """
    results = json.loads((SHOWCASE / "digests" / "Arden24.results.json").read_text())["results"]
    by_id = {r["id"]: r for r in results}

    # the locator a reader sees, and the anchor a viewer follows, agree
    prop = by_id["Arden24-prop-2.1"]
    assert "p.~1" in prop["locator"], prop["locator"]
    assert prop["anchor"]["kind"] == "pdf" and prop["anchor"]["page"] == 1

    # a result later in the paper is on a later page: the page is located, not defaulted
    assert by_id["Arden24-cor-3.2"]["anchor"]["page"] == 2

    # the anchor says where the statement is, not merely which sheet it is on
    assert prop["anchor"]["basis"] == "text"
    assert prop["anchor"]["end"] > prop["anchor"]["start"]
    page_text = (SHOWCASE / "digests" / "storage" / "arxiv" / "2504.01234v1" / "pages" / "0001.txt").read_text()
    said = page_text[prop["anchor"]["start"] : prop["anchor"]["end"]]
    assert said.startswith("Proposition 2.1"), said[:60]
    assert "quiver whose underlying graph" in said, said[:120]

    # and every located page really carries the result's printed label
    for r in results:
        page = r["anchor"].get("page") or 0
        if not page:
            continue
        text = (SHOWCASE / "digests" / "storage" / "arxiv" / "2504.01234v1" / "pages" / f"{page:04d}.txt").read_text()
        label = r["locator"].split("[", 1)[1].split(",", 1)[0]
        assert label in text, f"{r['id']} claims {label} on page {page}"


def test_a_work_with_no_filed_copy_keeps_its_source_anchor(tmp_path: Path) -> None:
    """Extraction still works with no document at all (DR-198): what it cannot locate it does not invent."""
    from loom.refs.proposals import _extracted_anchor

    a = _extracted_anchor(
        tmp_path,
        "Nobody12",
        None,
        "{\\cite[Theorem 1.1, p.~4]{Nobody12}}",
        "Let X be a scheme.",
        "digests/Nobody12.tex",
        "abc",
    )
    assert a.kind == "tex" and a.page == 0  # a page in the locator is not a page anybody can open


def test_an_anchor_round_trips_in_both_bases() -> None:
    """`Result.to_json` strips keys by name per kind, so a field added to `Anchor` and not named there lands in both kinds: a LaTeX anchor claiming a `basis`, or a page anchor carrying a byte range. Each kind carries exactly its own keys, and reads back equal."""
    from loom.refs.proposals import Anchor, Result

    cases = [
        (
            Anchor(kind="pdf", sha256="a" * 64, page=3, quads=[[1.0, 2.0, 3.0, 4.0]], basis="text", start=10, end=42),
            {"kind", "sha256", "page", "quads", "basis", "start", "end"},
        ),
        # a box records geometry and no offsets
        (
            Anchor(kind="pdf", sha256="b" * 64, page=7, quads=[[5.0, 6.0, 7.0, 8.0]], basis="box"),
            {"kind", "sha256", "page", "quads", "basis"},
        ),
        # a file anchor has no page, no geometry and no basis
        (
            Anchor(kind="tex", sha256="c" * 64, path="src/main.tex", bytes=[100, 200]),
            {"kind", "sha256", "path", "bytes"},
        ),
        (Anchor(kind="tex", sha256="d" * 64, path="digests/X.tex"), {"kind", "sha256", "path"}),
    ]
    for a, keys in cases:
        out = Result(id="x", local="l", anchor=a).to_json()["anchor"]
        assert set(out) == keys, (a, sorted(out))
        assert Result.from_json({"id": "x", "local": "l", "anchor": out}).anchor == a


def test_a_hyphenated_line_and_a_ligature_both_place() -> None:
    """The two extractions of a page disagree about hyphens a line break left behind and about ligatures: the word boxes carry `ﬃ` as one glyph where a selection or the page text spells `ffi`."""
    from loom.refs.search import locate_span

    # one word broken across a line, as `-bbox-layout` reports it, and a ligature the two readings spell differently
    words = [
        ("Let", 72.0, 100.0, 90.0, 112.0),
        ("the", 94.0, 100.0, 112.0, 112.0),
        ("denom-", 116.0, 100.0, 160.0, 112.0),
        ("inators", 72.0, 114.0, 110.0, 126.0),
        ("be", 114.0, 114.0, 128.0, 126.0),
        ("a\ufb03ne", 132.0, 114.0, 164.0, 126.0),
    ]
    xml = "".join(f'<word xMin="{a}" yMin="{b}" xMax="{c}" yMax="{d}">{w}</word>' for w, a, b, c, d in words)
    span = locate_span(xml, "Let the denominators be affine", 1)
    assert span is not None, "a word split by a line break and a ligature must still place"
    assert span.words == 6 and len(span.lines) == 2, "one rectangle per line, because the quotation crosses one"
    assert locate_span(xml, "Let the denominators be afine", 1) is None, "the ligature folds to ffi, not to anything"


# ---- a page of a cited work as a target (plan 0.13 item 2, item 4) -------------------------------------------------


@pytest.mark.poppler
def test_a_note_on_a_page_is_written_by_citekey_or_identifier_and_refused_legibly(tmp_path: Path) -> None:
    """`loom annotate` on a cited work (plan 0.13 item 2): the target may be the citekey the agent knows or the identifier a `cited:` link carries, and the record stores the identifier and the artifact's hash. Text is mapped with `refs locate`'s tolerance and recorded with offsets; a box is recorded as drawn. Each way of getting it wrong says what to do instead."""

    q = showcase(tmp_path)
    who = ("--as", "A. Author")
    said = ok(
        "annotate",
        "Bellamy19",
        "Is this needed?",
        "--page",
        "2",
        "--quote",
        "totally unimodular",
        "--kind",
        "question",
        *who,
        cwd=q,
    )
    assert "Bellamy19 p.2 (text)  question" in said.output, said.output
    drawn = ok(
        "annotate",
        "Bellamy19",
        "the polytope",
        "--page",
        "2",
        "--box",
        "82,278,529,316",
        "--kind",
        "note",
        *who,
        cwd=q,
    )
    assert "p.2 (box)  note" in drawn.output, drawn.output
    ok(
        "annotate",
        "doi:10.4171/showcase/19-2",
        "by its identifier",
        "--page",
        "2",
        "--quote",
        "Boundedness holds",
        *who,
        cwd=q,
    )

    events = [json.loads(line) for line in (q / "annotations" / "log.jsonl").read_text().splitlines()]
    text, box, ident = events[-3], events[-2], events[-1]  # appended in order, after the showcase's own
    page_text = (q / "digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt").read_text()
    assert text["target"] == "doi:10.4171/showcase/19-2" and text["against"].startswith("sha256:")
    assert (
        text["anchor"]["basis"] == "text"
        and page_text[text["anchor"]["start"] : text["anchor"]["end"]] == "totally unimodular"
    )
    assert (
        text["anchor"]["exact"] == "totally unimodular" and text["anchor"]["prefix"] and "quads" not in text["anchor"]
    )
    assert box["anchor"]["basis"] == "box" and box["anchor"]["quads"] == [[82.0, 278.0, 529.0, 316.0]]
    assert "quasi-polynomial" in box["anchor"]["exact"]  # the words under the rectangle, as a hint
    assert ident["target"] == text["target"]  # the citekey and the identifier name one work

    # the refusals, each naming what to do
    refused("annotate", "Bellamy19", "no page", "--quote", "x", *who, code=2, match="say which page", cwd=q)
    refused(
        "annotate",
        "sh-0003",
        "page on a key",
        "--page",
        "2",
        "--quote",
        "x",
        *who,
        code=2,
        match="is a key in this quilt",
        cwd=q,
    )
    refused(
        "annotate",
        "doi:10.1/nothing",
        "unknown",
        "--page",
        "2",
        "--quote",
        "x",
        *who,
        code=2,
        match="names none",
        cwd=q,
    )
    refused(
        "annotate",
        "Bellamy19",
        "both",
        "--page",
        "2",
        "--quote",
        "x",
        "--box",
        "1,2,3,4",
        *who,
        code=2,
        match="not both",
        cwd=q,
    )
    refused(
        "annotate", "Bellamy19", "absent", "--page", "2", "--quote", "zebra crossing", *who,
        code=1, match="loom library read Bellamy19 2", cwd=q,
    )  # fmt: skip
    refused(
        "annotate", "Bellamy19", "bad box", "--page", "2", "--box", "1,2,3", *who, code=2, match="x0,y0,x1,y1", cwd=q
    )

    # a batch line carries the same two keys
    batched = ok(
        "annotate",
        "--batch",
        "--as",
        "A. Author",
        "--quilt",
        str(q),
        stdin='{"target":"Bellamy19","message":"batched","page":2,"box":"82,278,529,316","kind":"note"}\n',
    )
    assert "(box)" in batched.output, batched.output


@pytest.mark.poppler
def test_the_endpoint_and_the_record_map_a_place_the_same_way(tmp_path: Path) -> None:
    """`locate` answers and writes nothing; `comment` writes. Both call `anchor_on_page`, so what the viewer previewed is what the log says -- one function, one assertion."""

    from loom.render.api import handle

    q = showcase(tmp_path)
    text = "the constraint matrix is an incidence matrix"
    preview = handle(q, "locate", {"citekey": "Bellamy19", "page": 2, "text": text})["anchor"]
    written = handle(
        q,
        "annotate",
        {
            "session": open_session(q),
            "target": "Bellamy19",
            "message": "so it is integral",
            "page": 2,
            "quote": text,
            "kind": "note",
            "author": "A. Author",
        },
    )
    assert written["ok"], written
    event = json.loads((q / "annotations" / "log.jsonl").read_text().splitlines()[-1])
    recorded = {k: v for k, v in event["anchor"].items() if k not in ("exact", "prefix", "suffix")}
    # the preview carries derived quads so the viewer can draw before anything is written; the record does not
    assert recorded == {k: v for k, v in preview.items() if k != "quads"}
    # and a box over the API, rectangles and all
    drawn = handle(
        q,
        "annotate",
        {
            "session": open_session(q),
            "target": "Bellamy19",
            "message": "that display",
            "page": 2,
            "rects": [[82, 278, 529, 316]],
            "kind": "note",
            "author": "A. Author",
        },
    )
    assert drawn["ok"] and "(box)" in drawn["result"], drawn


@pytest.mark.poppler
def test_the_sidecar_carries_the_notes_on_a_page_and_the_reference_counts_them(tmp_path: Path) -> None:
    """Geometry beside the manifest, bodies in it (plan 0.13 item 2, the author's decision of 2026-09-21): a text note's rectangles are derived from the word boxes at build time, a box note's are the record read back, both under `marks` beside the results' `quads`; the page table carries a real rotation; and the reference says how many notes its pages carry, since they are in no key's row."""

    q = showcase(tmp_path)
    who = ("--as", "A. Author")
    # the showcase carries reading notes of its own; what is asserted is what these two add
    before = sum(1 for line in (q / "annotations" / "log.jsonl").read_text().splitlines() if '"basis"' in line)
    a = ok(
        "annotate",
        "Bellamy19",
        "why unimodular?",
        "--page",
        "2",
        "--quote",
        "totally unimodular",
        "--kind",
        "question",
        *who,
        cwd=q,
    ).stdout.split()[0]
    b = ok(
        "annotate",
        "Bellamy19",
        "this display",
        "--page",
        "2",
        "--box",
        "82,278,529,316",
        "--kind",
        "note",
        *who,
        cwd=q,
    ).stdout.split()[0]
    # exit 1 is a content problem, which the showcase carries on purpose (a duplicate id); the build still writes
    exits(1, "build", cwd=q)
    manifest = json.loads((q / "build" / "manifest.json").read_text())
    ref = manifest["references"]["Bellamy19"]
    assert ref["reading"]["total"] == before + 2 and ref["reading"]["open"] >= 2
    assert manifest["annotations"][a]["target"] == {
        "key": "doi:10.4171/showcase/19-2",
        "hash": manifest["annotations"][a]["target"]["hash"],
        "work": "Bellamy19",
        "page": 2,
    }
    assert manifest["annotations"][a]["basis"] == "text" and manifest["annotations"][b]["basis"] == "box"
    assert manifest["annotations"][a]["anchored"] and manifest["annotations"][b]["anchored"]
    side = json.loads((q / "build" / ref["spans"]["path"]).read_text())
    assert a in side["marks"] and len(side["marks"][a]) == 1  # one line
    assert side["marks"][b] == [[82.0, 278.0, 529.0, 316.0]]  # as drawn
    assert "Bellamy19-prop-3.1" in side["quads"]  # the results are still there beside them
    assert side["pages"]["2"]["rotate"] == 0.0 and side["pages"]["2"]["width"] == 612.0
    # and a work with no notes says so, rather than saying nothing
    assert manifest["references"]["Arden24"]["reading"] == {"total": 0, "open": 0}


@pytest.mark.poppler
def test_a_locator_by_offsets_lights_the_same_place_a_selection_would(tmp_path: Path) -> None:
    """`span=A-B` in a link names the page's committed text by offsets (plan 0.13 item 6); `locate` maps it to the rectangles a selection of that text would get, so a link and a selection light one place."""
    from loom.render.api import handle

    q = showcase(tmp_path)
    page_text = (q / "digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt").read_text()
    a = page_text.index("totally unimodular")
    by_span = handle(q, "locate", {"citekey": "Bellamy19", "page": 2, "span": [a, a + len("totally unimodular")]})
    by_text = handle(q, "locate", {"citekey": "Bellamy19", "page": 2, "text": "totally unimodular"})
    assert by_span["ok"] and by_span["anchor"]["quads"] == by_text["anchor"]["quads"]
    assert by_span["anchor"]["start"] == a and by_span["text"] == "totally unimodular"


# ---- What the reading study found (2026-09-21) ---------------------------------------------------------------


@pytest.mark.poppler
def test_locate_names_the_place_and_not_only_the_page(tmp_path: Path) -> None:
    """`locate` kept its own mapping, so its anchor had no `basis`, `start` or `end`, and the `open:` line could name only the page — design §6 specifies `?page=3&span=1043-1189`, and following what it printed left the quotation to be found by eye."""

    from loom.render.serve import write_serve_json

    q = showcase(tmp_path)
    got = json_of("library", "locate", "Bellamy19", "totally unimodular", "--page", "2", "--json", cwd=q)
    missing = json_of(
        "library", "locate", "Bellamy19", "no such words anywhere", "--page", "2", "--json", cwd=q, code=1
    )
    assert {k: missing[k] for k in ("found", "citekey", "page", "ok")} == {
        "found": False,
        "citekey": "Bellamy19",
        "page": 2,
        "ok": False,
    }
    assert got["basis"] == "text" and got["start"] > 0 and got["end"] > got["start"]
    page_text = (q / "digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt").read_text()
    assert page_text[got["start"] : got["end"]] == "totally unimodular"

    write_serve_json(q, 8791)  # this process is alive, so the link is offered
    said = ok("library", "locate", "Bellamy19", "totally unimodular", "--page", "2", cwd=q).output
    assert f"span={got['start']}-{got['end']}" in said, said
    # a quotation found on the word boxes and not in the committed text is a box, and names its rectangle instead
    edit(q / "digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt", "The function L is a", "The map L is a")
    drawn = ok("library", "locate", "Bellamy19", "The function L is a quasi-polynomial", "--page", "2", cwd=q).output
    assert "  box  " in drawn and "&box=" in drawn and "span=" not in drawn, drawn


@pytest.mark.poppler
def test_a_change_carries_an_address_its_reader_can_use(tmp_path: Path) -> None:
    """A page note's target is the work's identifier, which is what two quilts agree on and what no `loom refs` command accepts. The study watched an agent take the changed-annotation block, try `loom refs page arXiv:1809.02027v1 4`, be told it was not in the bibliography, and go hunting for the citekey. It travels with the change now."""
    from loom.mailbox import pending, render
    from loom.sessions import create, sessions

    q = showcase(tmp_path)
    sid = create(q, "reading", "A. Author").id
    ok(
        "annotate",
        "Bellamy19",
        "why unimodular?",
        "--page",
        "2",
        "--quote",
        "totally unimodular",
        "--kind",
        "question",
        "--session",
        sid,
        "--as",
        "A. Author",
        cwd=q,
    )
    ok(
        "annotate",
        "sh-0003",
        "and one on a key, which has no work",
        "--kind",
        "note",
        "--session",
        sid,
        "--as",
        "A. Author",
        cwd=q,
    )

    changed = pending(q, sessions(q)[sid], "A. Author")
    page_note = the(changed, lambda c: bool(c["page"]), "change on a page")
    assert page_note["work"] == "Bellamy19" and page_note["page"] == 2
    assert page_note["target"].startswith("doi:")  # the identifier is still what was recorded
    on_key = the(changed, lambda c: not c["page"], "change on a key")
    assert on_key["work"] is None and on_key["target"] == "sh-0003"
    # and what a parked agent reads names the paper and the page, not an address it must decode
    said = render(
        [type("E", (), {"who": "A. Author", "when": "now", "kind": "message", "body": "look", "changed": changed})()]
    )
    assert "Bellamy19 p.2" in said, said


# ---- refs path, add, ingest, drop, links, unlink (book 8.9, 8.14) ------------------------------------------


def _fake_pdf(path: Path, text: str) -> Path:
    """A PDF in the shape the fake toolchain's pdftotext reads (tests/fake_latex)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"%PDF-1.4\n%FAKE-LOOM\n%%Pages: 1\n{text}\n".encode())
    return path


def test_read_where_prints_where_an_artifact_would_go_and_says_when_nothing_is_there(tmp_path: Path) -> None:
    q = demo(tmp_path)
    home = work_home(q, "Calloway14")
    assert ok("library", "read", "Calloway14", "--where", "dir", cwd=q).stdout.strip() == str(home)
    assert ok("library", "read", "Calloway14", "--where", "pdf", cwd=q).stdout.strip() == str(home / "paper.pdf")
    # Git does not preserve empty source directories; file a source explicitly.
    (home / "src").mkdir(exist_ok=True)
    (home / "src" / "main.tex").write_text("Source text.\n")
    assert ok("library", "read", "Calloway14", "--where", "src", cwd=q).stdout.strip() == str(home / "src")
    r = refused(
        "library",
        "read",
        "Man12",
        "--where",
        "pdf",
        cwd=q,
        code=1,
        match="nothing there yet; loom library update Man12 --online",
    )
    assert r.stdout.strip() == str(work_home(q, "Man12") / "paper.pdf")  # printed anyway: it is where it would go
    refused("library", "read", "Nobody99", "--where", "dir", cwd=q, code=2, match="'Nobody99' names no work")
    # a document `refs scan` filed names its own directory, and `library read --where` looks where every other reader does
    from loom.refs.pages import storage_root

    bib = q / "digests" / "bibliography.bib"
    bib.write_text(
        bib.read_text()
        + "\n@misc{Filed20, title={A filed thing}, author={Doe, A.}, year={2020}, loom-file={file/0123abcd}}\n"
    )
    r = refused("library", "read", "Filed20", "--where", "dir", cwd=q, code=1, match="nothing there yet")
    assert r.stdout.strip() == str(storage_root(q) / "file" / "0123abcd")


def test_library_add_files_a_pdf_or_source_and_never_replaces_one(tmp_path: Path) -> None:
    q = demo(tmp_path)
    home = work_home(q, "Man12")
    notes = tmp_path / "notes.txt"
    notes.write_text("not a paper")
    refused(
        "library", "add", notes, "--for", "Man12", cwd=q, code=2, match="notes.txt is neither a PDF nor LaTeX source"
    )
    assert not home.exists()

    title = parse_bib((q / "digests" / "bibliography.bib").read_text())["Man12"].fields["title"]
    # a PDF whose first page carries another title is refused: filed under the wrong work, every anchor would read the wrong paper (CLI study, defect 9)
    wrong = _fake_pdf(tmp_path / "wrong.pdf", "Advanced Topics in the Arithmetic of Elliptic Curves")
    refused("library", "add", wrong, "--for", "Man12", cwd=q, code=2, match="does not show it is Man12")
    assert not (home / "paper.pdf").exists()
    one = _fake_pdf(tmp_path / "one.pdf", f"{title}\nCristina Manolache\nfirst copy")
    two = _fake_pdf(tmp_path / "two.pdf", f"{title}\nCristina Manolache\nsecond copy\fan appendix")
    said = ok("library", "add", one, "--for", "Man12", cwd=q).stdout
    assert "one.pdf as Man12's PDF, with its page text" in said and (home / "pages").is_dir()  # mapped at once
    said = " ".join(ok("library", "add", two, "--for", "Man12", cwd=q).stdout.split())
    assert "two.pdf as Man12's PDF, beside its first document as Man12A" in said, said
    assert b"first copy" in (home / "paper.pdf").read_bytes(), "a second document never replaces the first (book 8.16)"

    src = tmp_path / "eprint"
    (src / "sec").mkdir(parents=True)
    (src / "main.tex").write_text("\\documentclass{article}")
    (src / "sec" / "one.tex").write_text("\\section{One}")
    assert "eprint as Man12's LaTeX source" in ok("library", "add", src, "--for", "Man12", cwd=q).stdout
    assert sorted(p.relative_to(home / "src").as_posix() for p in (home / "src").rglob("*.tex")) == [
        "main.tex",
        "sec/one.tex",
    ]
    other = tmp_path / "other.tex"
    other.write_text("\\documentclass{amsart}")
    said = " ".join(ok("library", "add", other, "--for", "Man12", cwd=q).stdout.split())
    assert "other.tex as Man12's LaTeX source, beside its first document as Man12B" in said, said
    assert sorted(p.name for p in (home / "src").rglob("*.tex")) == [
        "main.tex",
        "one.tex",
    ]  # neither replaced nor merged


def test_library_add_files_what_a_document_shows_plainly_and_says_why_it_skipped_the_rest(tmp_path: Path) -> None:
    """Book 8.14: an identifier on the page files a document alone, and so does its whole title with the entry's first author leading its byline; anything weaker is skipped with its reason; a work that has a PDF gets the new one beside it; --dry-run files nothing."""
    q = demo(tmp_path)
    pile = tmp_path / "pile"
    _fake_pdf(pile / "a.pdf", "Virtual pull-backs\nCristina Manolache\narXiv:0805.2065v2 [math.AG]")
    _fake_pdf(pile / "Hartshorne - 1977 - Algebraic Geometry.pdf", "Some other text entirely\nnobody at all")
    _fake_pdf(pile / "b.pdf", "Algebraic Geometry\nRobin Hartshorne\nSpringer")
    _fake_pdf(
        pile / "c.pdf", "Fixed loci of involutions on separated spaces\nImogen Calloway\narXiv:1301.00001v1, a preprint"
    )
    _fake_pdf(pile / "d.pdf", "Lecture notes on something unrelated\nA. Stranger")
    (tmp_path / "empty").mkdir()
    refused("library", "add", tmp_path / "empty", cwd=q, code=2, match="holds no PDF and no LaTeX source")

    dry = json_of("library", "add", pile, "--dry-run", "--json", cwd=q)
    rows = {Path(r["file"]).name: r for r in dry["documents"]}
    assert (dry["filed"], dry["skipped"], dry["refused"]) == (3, 2, 0)
    assert (rows["a.pdf"]["citekey"], rows["a.pdf"]["outcome"]) == ("Man12", "filed")
    assert rows["a.pdf"]["strong"][0]["how"] == "arXiv:0805.2065v2 is on its first pages"
    hart = rows["Hartshorne - 1977 - Algebraic Geometry.pdf"]
    assert hart["outcome"] == "skipped" and hart["reason"].startswith("Har77 is the nearest entry, on first-author")
    assert (rows["b.pdf"]["citekey"], rows["b.pdf"]["outcome"]) == ("Har77", "filed")
    assert (rows["c.pdf"]["outcome"], rows["c.pdf"]["sibling"]) == ("filed", "Calloway14A")
    assert (rows["d.pdf"]["outcome"], rows["d.pdf"]["reason"]) == ("skipped", "nothing in the bibliography matches it")
    assert not (work_home(q, "Man12") / "paper.pdf").exists() and not (work_home(q, "Har77") / "paper.pdf").exists()

    r = ok("library", "add", pile, cwd=q)
    assert (work_home(q, "Man12") / "paper.pdf").read_bytes() == (pile / "a.pdf").read_bytes()
    assert (work_home(q, "Har77") / "paper.pdf").read_bytes() == (pile / "b.pdf").read_bytes()
    assert r.stdout.startswith("5 documents: 3 filed, 2 skipped, 0 refused"), r.output
    said = " ".join(r.stdout.split())
    assert (
        "d.pdf: nothing in the bibliography matches it" in said
        and "Hartshorne - 1977 - Algebraic Geometry.pdf: Har77" in said
    )
    assert b"Imogen" not in (work_home(q, "Calloway14") / "paper.pdf").read_bytes()  # the shipped copy is untouched


def test_library_drop_removes_records_by_work_session_or_state_and_never_the_digest(tmp_path: Path) -> None:
    from loom.refs.proposals import load_results

    q, ck = mapped(tmp_path)
    sid = new_session(q)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", session=sid)
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G")
    digest_before = (q / "digests" / "Calloway14.tex").read_text()
    refused("library", "drop", cwd=q, code=2, match="give exactly one of --work, --session or --proposed")
    refused("library", "drop", "--work", ck, "--proposed", cwd=q, code=2, match="give exactly one of")
    refused("library", "drop", "--proposed", cwd=q, code=2, match="dropping needs confirmation; pass --yes")
    assert len(load_results(q, ck)) == 2  # the refusal dropped nothing

    r = ok("library", "drop", "--session", sid, "--yes", cwd=q)
    assert r.stdout.startswith("dropped 1 record;") and list(load_results(q, ck)) == [f"{ck}-thm-4.1"]
    ok("library", "drop", "--proposed", "--yes", cwd=q)
    assert load_results(q, ck) == {} and len(load_results(q, "Calloway14")) == 5  # extracted results stay
    ok("library", "drop", "--work", "Calloway14", "--yes", cwd=q)
    assert load_results(q, "Calloway14") == {}
    assert (q / "digests" / "Calloway14.tex").read_text() == digest_before
    assert ok("library", "drop", "--proposed", "--yes", cwd=q).output.strip() == "nothing to drop"


def test_why_walks_relations_depth_hops_and_relate_undo_removes_one(tmp_path: Path) -> None:
    """Book 8.14: `why --depth` follows relations out from the result in one call; `relate --undo` removes one by id, records why, and refuses an unknown one."""
    q = demo(tmp_path)
    a, b, c, d = (f"Calloway14-{x}" for x in ("def-3.1", "prop-3.2", "prop-3.3", "thm-3.4"))
    for frm, to in ((a, b), (b, c), (c, d)):
        ok("library", "relate", frm, to, "--kind", "depends-on", "--why", "Because.", "--as", "isaac", cwd=q)

    def walk(*extra: str) -> list[str]:
        return [x["id"] for x in json_of("library", "why", *extra, "--json", cwd=q)["links"]]

    assert walk(a) == ["link-0001"]
    assert walk(a, "--depth", "2") == ["link-0001", "link-0002"]
    assert walk(a, "--depth", "5") == ["link-0001", "link-0002", "link-0003"]
    assert walk(c) == ["link-0002", "link-0003"]  # both directions
    every = [x["id"] for x in json_of("library", "--json", cwd=q)["links"]]
    assert every == ["link-0001", "link-0002", "link-0003"]
    undo = ("library", "relate", "--undo", "link-0002", "--why", "A misreading.", "--as", "A. Author")
    assert ok(*undo, cwd=q).output.strip() == f"removed link-0002: {b} depends-on {c}"
    removed = json.loads((q / "digests" / "links-removed.jsonl").read_text())
    assert (
        removed["link"]["id"] == "link-0002"
        and removed["why"] == "A misreading."
        and removed["removed_by"] == "A. Author"
    )
    assert walk(a, "--depth", "5") == ["link-0001"]  # the chain is cut
    refused(*undo, cwd=q, code=2, match="link-0002")
    assert ok("library", "why", "Calloway14-setup", cwd=q).stdout.splitlines()[0].endswith("; no relations")


def test_a_forced_rebuild_keeps_every_result_the_author_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`library update --redo` rewrites the digest from the paper's source, and keeps a node `library verify` put there while `results.json` says verified (CLI study, defect 3)."""
    q = demo(tmp_path)
    ck = "Calloway14"
    extracted = (q / "digests" / f"{ck}.tex").read_text()
    # the paper's source, extracted afresh: what the digest held before the author verified anything, without needing TeX
    monkeypatch.setattr("loom.digest.extract.extract_digest", lambda *_a, **_k: (extracted, None))
    # a source to extract from, which the store keeps out of git and so a checkout's demo does not carry
    src = q / "digests" / "storage" / "doi" / "10.4171_demo_14-1" / "src"
    shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    (src / "paper.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nCalloway.\n\\end{document}\n", encoding="utf-8"
    )
    propose(
        q,
        ck,
        "rem-4.1",
        2,
        "Let X = {a, b} carry the indiscrete topology",
        "The indiscrete pair is no counterexample.",
        level="1",
    )
    rid = f"{ck}-rem-4.1"
    ok("library", "verify", rid, "--as", "A. Author", "--yes", cwd=q)
    digest = q / "digests" / f"{ck}.tex"
    assert f"\\label{{{rid}}}" in digest.read_text()
    r = ok("library", "update", ck, "--redo", cwd=q)
    assert (
        f"\\label{{{rid}}}" in digest.read_text() and "The indiscrete pair is no counterexample." in digest.read_text()
    )
    assert f"verified results kept through the new extraction (1)\n  {rid}  {ck}" in r.output, r.output


def test_a_works_path_and_its_pages_are_read_without_a_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`library read --where` and `library read WORK PAGES` need a work's bibliography entry and its store, and nothing the documents say; a scan cost a second or more on a large quilt (plan 0.18.2)."""
    q = demo(tmp_path)

    def no_scan(_quilt: object) -> None:
        raise AssertionError("scanned")

    monkeypatch.setattr("loom.cli._quilt.scan", no_scan)
    assert ok("library", "read", "Calloway14", "--where", "dir", cwd=q).stdout.strip().endswith("10.4171_demo_14-1")
    assert ok("library", "read", "Calloway14", "1", cwd=q).stdout.strip()
