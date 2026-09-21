"""The quilt's reference layer (plan 0.12): which identifier a work is fetched on, the arrival check, and what `refs build` reports."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.refs.fetch import ARRIVAL, arrival_score, arxiv_id, identifier_for, source_title
from loom.refs.resolve import Candidate, query_for, save
from loom.render.api import CAPABILITIES
from loom.scan.bib import BibEntry


def _sid(root: Path) -> str:
    """A session to write into. Every write over the API names one (plan 0.13.1); only the CLI still has a default."""
    from loom.sessions import create, sessions

    have = [s for s in sessions(root).values() if s.state == "open"]
    return have[0].id if have else create(root, "test sitting", "tester").id



def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def quilt(tmp_path: Path) -> Path:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    return tmp_path / "q"


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
    q = quilt(tmp_path)
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


def test_build_says_what_is_off_and_what_is_left(tmp_path: Path) -> None:
    """A quilt that has opted into nothing still gets a report, and it names the two things a machine cannot do."""
    q = quilt(tmp_path)
    r = run("refs", "build", cwd=q)
    assert r.exit_code == 0, r.output
    assert "(lookup off)" in r.output and "(fetching off)" in r.output
    assert "needs you" in r.output and "needs an agent" in r.output


def test_build_json_orders_by_how_often_a_work_is_cited(tmp_path: Path) -> None:
    """15 of relloc's 22 entries are cited and the other 7 are not worth a page yet, so the report leads with the cited ones."""
    import json

    q = quilt(tmp_path)
    r = run("refs", "build", "--json", cwd=q)
    assert r.exit_code == 0, r.output
    works = json.loads(r.output)["works"]
    counts = [w["cited_by"] for w in works]
    assert counts == sorted(counts, reverse=True)
    assert any(w["digest"] for w in works), "the demo ships a digest, so something must be marked as having one"


def test_match_lists_only_what_a_person_must_look_at(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    r = run("refs", "match", cwd=q)
    assert r.exit_code == 0, r.output
    # the demo fetches nothing, so every cited work with no artifact is a person's problem
    assert "loom refs add" in r.output or "nothing needs you" in r.output


def test_an_agent_may_run_the_mechanical_pass_and_not_the_authors_verbs() -> None:
    from loom.ai.layout import AGENT_COMMANDS

    assert {"refs build", "refs fetch", "refs match", "refs path", "refs resolve"} <= AGENT_COMMANDS
    assert "digest fetch" not in AGENT_COMMANDS, "the command is withdrawn; refs fetch absorbed it"
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
    q = quilt(tmp_path)
    r = run("refs", "map", cwd=q)
    assert r.exit_code == 0 and "0 mapped" in r.output
    c = run("refs", "coverage", cwd=q)
    assert c.exit_code == 0 and "have page text" in c.output


def test_the_page_text_is_committed_and_the_pdf_is_not(tmp_path: Path) -> None:
    """Plan 0.12 §4.2: an anchor is re-checkable by a coauthor who holds no PDF, which only works if the text is in the repository."""
    q = quilt(tmp_path)
    ignored = (q / ".gitignore").read_text()
    assert "digests/storage/**/paper.pdf" in ignored and "digests/storage/**/src/" in ignored
    assert "\nrefs/\n" in ignored, "the seed space is the author's pile of other people's PDFs"
    rules = [ln for ln in ignored.splitlines() if ln and not ln.startswith("#")]
    assert not any("pages" in ln for ln in rules), "the page text an anchor is checked against is committed"
    assert "refs/pdf/" not in ignored, "DR-108 moved the artifacts into refs/<work-id>/ three plans ago"


def test_the_demo_gitignore_agrees_with_the_one_init_writes() -> None:
    """The demo shipped its own copy naming `refs/pdf/` for three plans after DR-108 moved the artifacts, so a demo quilt ignored two directories that no longer existed and committed the PDFs that did."""
    from importlib import resources

    assets = resources.files("loom").joinpath("assets")
    canonical = assets.joinpath("init", "gitignore").read_text(encoding="utf-8")
    demo = assets.joinpath("demo", ".gitignore")
    if demo.is_file():
        refs = [ln for ln in canonical.splitlines() if ln.startswith(("refs/", "digests/storage"))]
        assert refs and all(ln in demo.read_text(encoding="utf-8") for ln in refs), "the demo's copy has drifted"


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


def test_grep_searches_every_work_before_truncating(tmp_path: Path) -> None:
    """Stopping at the limit made the answer depend on citation order: the first two papers filled it and the rest looked empty."""
    import inspect

    from loom.cli.refs import grep_command

    src = inspect.getsource(grep_command.callback)  # type: ignore[arg-type]
    assert "break" not in src, "grep must not stop searching early; truncate the hits instead"
    assert "searched" in src and "shown" in src, "the summary must say how much of the corpus it could search"


def propose(
    q: Path, citekey: str, local: str, page: int | str, source: str, statement: str, level: str = "1", **kw: str
):  # type: ignore[no-untyped-def]
    args = [
        "refs",
        "propose",
        citekey,
        "--local",
        local,
        "--page",
        str(page),
        "--level",
        level,
        "--source-text",
        source,
        "--statement",
        statement,
    ]
    for k, v in kw.items():
        args += [f"--{k.replace('_', '-')}", v]
    return run(*args, cwd=q)


def mapped(tmp_path: Path) -> tuple[Path, str]:
    """A quilt with one cited work whose page text is on disk, written directly rather than extracted from a PDF."""
    from loom.refs.fetch import work_dir
    from loom.refs.pages import write_map

    q = quilt(tmp_path)
    ck = "Vir12"  # not Calloway14: the demo quilt already ships a digest under that key
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write("\n@article{Vir12, title={Virtual pull-backs}, author={Manolache, C.}, year={2012}}\n")
    home = work_dir(
        q,
        __import__("loom.scan.scan", fromlist=["scan"])
        .scan(__import__("loom.scan.quilt", fromlist=["load_quilt"]).load_quilt(q))
        .bib[ck],
    )
    pages = home / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    (pages / "0001.txt").write_text(
        "1 Introduction\nLet $f$ be a DM-type morphism with a perfect obstruction theory.\n"
    )
    (pages / "0012.txt").write_text("Theorem 4.1. Every widget is a gadget when the theory is perfect.\n")
    import json as _json

    (home / "sections.json").write_text(
        _json.dumps(
            {
                "sha256": "deadbeef" * 8,
                "pages": 12,
                "chars": 120,
                "sections": [{"n": "1", "title": "Introduction", "page": 1}],
            }
        )
    )
    _ = write_map
    return q, ck


def test_a_quotation_that_is_not_on_the_page_is_refused_with_the_page(tmp_path: Path) -> None:
    """Nothing is stored on failure and the page comes back, so the agent corrects itself in the turn it failed."""
    q, ck = mapped(tmp_path)
    r = propose(q, ck, "thm-4.1", 12, "Every widget is a doohickey", "X")
    assert r.exit_code == 1
    assert "Every widget is a gadget" in r.output, "the page's own text must come back with the refusal"
    assert not (q / "digests" / f"{ck}.results.json").exists()


def test_the_level_one_gate_is_about_order_not_derived_data(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    deep = propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "X", level="3")
    assert deep.exit_code == 1 and "no level-1 result yet" in deep.output
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    assert propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "X", level="3").exit_code == 0


def test_a_proposal_is_in_no_bundle_and_no_closure(tmp_path: Path) -> None:
    """The guarantee is structural: the file exists, loom scans it, and nothing inputs it (plan 0.12 §4.1)."""
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    shadow = q / "digests" / f"{ck}.proposed.tex"
    assert shadow.is_file() and not (q / "digests" / f"{ck}.tex").exists()
    for tex in q.rglob("*.tex"):
        if tex != shadow:
            assert shadow.name not in tex.read_text(), f"{tex} inputs the proposals file"


def test_verifying_moves_it_into_the_digest_and_records_both_parties(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", session="run:A").exit_code == 0
    rid = f"{ck}-thm-1.1"
    r = run("refs", "verify", rid, "--statement", "Z", "--author", "isaac", "--yes", cwd=q)
    assert r.exit_code == 0, r.output
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
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    before = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"][0]
    assert (
        run(
            "refs", "verify", f"{ck}-thm-1.1", "--statement", "rewritten", "--author", "isaac", "--yes", cwd=q
        ).exit_code
        == 0
    )
    after = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"][0]
    assert after["statement"] == "rewritten" and after["source_text"] == before["source_text"]
    assert after["anchor"] == before["anchor"]


def test_a_discard_is_returned_to_whatever_proposes_it_again(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    assert (
        run(
            "refs",
            "discard",
            f"{ck}-thm-1.1",
            "--reason",
            "that is the hypothesis, not the theorem",
            "--author",
            "i",
            cwd=q,
        ).exit_code
        == 0
    )
    again = propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y2")
    assert again.exit_code == 1 and "that is the hypothesis, not the theorem" in again.output
    assert "--supersedes" in again.output
    ok = propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y2", supersedes=f"{ck}-thm-1.1")
    assert ok.exit_code == 0, ok.output


def test_the_manifest_keeps_the_digest_and_its_proposals_apart(tmp_path: Path) -> None:
    """Both files claim one citekey, and a `{ck: f}` comprehension keeps whichever came last — so the viewer could have rendered unverified statements as the digest."""
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    assert run("refs", "verify", f"{ck}-thm-1.1", "--author", "i", "--yes", cwd=q).exit_code == 0
    assert propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3").exit_code == 0
    assert run("build", cwd=q).exit_code in (0, 1)
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
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    assert run("build", cwd=q).exit_code in (0, 1)
    m = json.loads((q / "build" / "manifest.json").read_text())
    assert "proposed" in m["states"]["labels"]
    assert m["keys"][f"{ck}-thm-1.1"]["state"] == "proposed"


def test_a_link_needs_a_kind_from_the_vocabulary_two_ends_and_a_reason(tmp_path: Path) -> None:
    """A closed vocabulary because a viewer can only draw what it can name; a sentence because an unexplained edge is noise."""
    from loom.refs.links import KINDS, add_link, read_links, remove_link

    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    assert propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3").exit_code == 0
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
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    assert propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3").exit_code == 0
    add_link(q, f"{ck}-thm-1.1", f"{ck}-thm-4.1", "depends-on", "Because.", "isaac")
    for tex in q.rglob("*.tex"):
        assert "link-0001" not in tex.read_text(), f"{tex} names a link"
    assert run("build", cwd=q).exit_code in (0, 1)
    m = json.loads((q / "build" / "manifest.json").read_text())
    assert [x["kind"] for x in m["links"]] == ["depends-on"]
    # a link is not an edge: it must not appear where the graph and the closure look
    assert not any(e.get("via") == "link" for e in m["edges"])


def test_the_link_cli_refuses_an_end_that_is_not_a_result(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    r = run(
        "refs", "link", "--from", f"{ck}-thm-1.1", "--to", "nope-0001", "--kind", "same-notion", "--why", "w", cwd=q
    )
    assert r.exit_code != 0 and "not a result" in r.output


def test_recheck_makes_transcription_verified_falsifiable(tmp_path: Path) -> None:
    """DR-172 gave the label; this gives it something to be wrong about (plan 0.12 §5.7)."""
    from loom.refs.fetch import work_dir
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    assert run("refs", "verify", f"{ck}-thm-1.1", "--author", "i", "--yes", cwd=q).exit_code == 0
    clean = run("refs", "recheck", cwd=q)
    assert clean.exit_code == 0 and "1 verified anchor(s) re-read; 0 moved" in clean.output

    home = work_dir(q, scan(load_quilt(q)).bib[ck])
    page = home / "pages" / "0001.txt"
    page.write_text(page.read_text().replace("DM-type morphism", "DM-type map"))
    moved = run("refs", "recheck", cwd=q)
    assert moved.exit_code != 0
    assert "transcription-changed" in moved.output and "1 moved" in moved.output


def test_recheck_never_re_reads_a_verified_rendering(tmp_path: Path) -> None:
    """A verified node's LaTeX was judged by a person once; re-judging it mechanically would claim a check that does not exist."""
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    assert (
        run(
            "refs", "verify", f"{ck}-thm-1.1", "--statement", "utterly different prose", "--author", "i", "--yes", cwd=q
        ).exit_code
        == 0
    )
    r = run("refs", "recheck", cwd=q)
    assert r.exit_code == 0 and "0 moved" in r.output, (
        "the rendering may differ from the page and that is the author's call"
    )


def test_every_search_says_how_much_of_the_corpus_it_could_search(tmp_path: Path) -> None:
    """A search over a partly digested corpus is a search over silence, and a result set that does not say so reads like a finding."""
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    hit = run("refs", "find", "DM-type", cwd=q)
    assert hit.exit_code == 0 and f"{ck}-thm-1.1" in hit.output
    assert "coverage:" in hit.output and "works digested" in hit.output
    miss = run("refs", "find", "quantum cohomology of a gerbe", cwd=q)
    assert "results: 0" in miss.output and "loom refs grep" in miss.output, "a miss must name the fallback"


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


def test_a_pdf_on_disk_does_not_stop_loom_looking_for_the_source(tmp_path: Path, monkeypatch: object) -> None:
    """Ingesting PDFs first made loom skip every work that had one, so on the real seed 13 works waited for an agent to read them when 12 of them had a source a machine could have extracted."""
    import inspect

    from loom.refs import build

    resolve_src = inspect.getsource(build._resolve_step)
    fetch_src = inspect.getsource(build._fetch_step)
    assert "w.pdf" not in resolve_src.split("continue")[0], "a PDF must not be a reason to stop resolving"
    assert "if w.source:" in fetch_src and "w.source or w.pdf" not in fetch_src
    # and the report must not forget a PDF because this run did not download one
    assert "w.pdf or got.pdf" in fetch_src


def test_an_agent_cannot_vouch_for_its_own_reading(tmp_path: Path, monkeypatch: object) -> None:
    """The first study run: an agent verified its own proposal and loom recorded the author as the verifier, because the author's name comes from git and an agent's shell shares it."""
    import pytest

    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("AI_AGENT", "1")
        for args in (
            ["refs", "verify", f"{ck}-thm-1.1", "--yes"],
            ["refs", "discard", f"{ck}-thm-1.1", "--reason", "r"],
        ):
            r = run(*args, cwd=q)
            assert r.exit_code != 0 and "the author's" in r.output and "AI_AGENT" in r.output, r.output
        # with nothing declared, the marker refuses rather than guessing
        bare = run("accept", "dm-0002", cwd=q)
        assert bare.exit_code != 0 and "AI_AGENT" in bare.output
        # a declared agent is refused whatever shell it is in: the guard is on the identity, not the door
        robot = run("accept", "dm-0002", "--author", "Referee Agent", cwd=q)
        assert robot.exit_code != 0 and "is an agent" in robot.output
        # and an author who says so is the author, even from a shell an agent happens to be running (plan 0.13 §8)
        assert run("accept", "dm-0002", "--author", "A. Author", cwd=q).exit_code == 0
        # proposing is the agent's, and still works
        assert propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3").exit_code == 0
    finally:
        mp.undo()
    # and nothing was recorded as verified by anyone
    states = {r["id"]: r["state"] for r in json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"]}
    assert "verified" not in states.values()


def test_verifying_on_a_terminal_shows_both_texts_first(tmp_path: Path) -> None:
    """§5.3: a surface that offers verify without showing both texts is a bug, and a terminal is a surface."""
    q, ck = mapped(tmp_path)
    assert (
        propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "Every widget is a gadget.", level="1").exit_code == 0
    )
    r = run("refs", "verify", f"{ck}-thm-4.1", "--yes", "--author", "x", cwd=q)
    assert r.exit_code == 0, r.output
    assert "--- the page" in r.output and "Theorem 4.1. Every widget is a gadget" in r.output
    assert "--- rendered as ---" in r.output
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    refused = run("refs", "verify", f"{ck}-thm-1.1", "--author", "x", cwd=q)  # not a tty, no --yes
    assert refused.exit_code != 0


def test_the_page_around_the_quote_is_what_a_rendering_is_judged_against(tmp_path: Path) -> None:
    """An agent quotes only what the anchor needs; a ten-line rendering stood beside one clause and could not be judged."""
    from loom.refs.proposals import load_results, page_context

    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type", "A long rendering with much more in it.").exit_code == 0
    r = load_results(q, ck)[f"{ck}-thm-1.1"]
    ctx, found = page_context(q, r)
    assert found and "perfect obstruction theory" in ctx, "the page carries the rest of the statement the quote cut off"


def test_a_result_stated_under_two_numbers_is_citable_by_either(tmp_path: Path) -> None:
    """Brion states Theorems 3.2 and 3.3 together; recorded as `thm-3.2-3.3` a citation to either matched nothing."""
    from loom.refs.proposals import node_tex, numbers_of

    assert numbers_of("3.2, 3.3") == numbers_of("3.2-3.3") == ["3.2", "3.3"]
    assert numbers_of("3.2.1") == ["3.2.1"], "a dotted number is one number"
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", number="1.1, 1.2").exit_code == 0
    tex = (q / "digests" / f"{ck}.proposed.tex").read_text()
    assert f"\\label{{{ck}-thm-1.1}}\\label{{{ck}-thm-1.2}}" in tex, (
        "the id is the first number and the rest are aliases"
    )
    _ = node_tex


def test_coverage_finds_a_work_by_author_and_refuses_what_it_cannot(tmp_path: Path) -> None:
    """Agents grepped refs.bib for an author twice; with two Edidin-Graham 1998 papers, guessing chose between them."""
    q, ck = mapped(tmp_path)
    by_author = run("refs", "coverage", "manolache", cwd=q)
    assert by_author.exit_code == 0 and ck in by_author.output
    unknown = run("refs", "coverage", "FixedLocusRomagny", cwd=q)
    assert unknown.exit_code != 0 and "not a citekey" in unknown.output


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
    sid = run("ai", "start", "fixed stacks", cwd=q).output.strip()
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", session=sid).exit_code == 0
    origin = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"][0]["origin"]
    assert origin[0]["by"] == sid


def test_a_fresh_digest_is_not_called_thin(tmp_path: Path) -> None:
    """Results were counted by the survey that opened the run, before extraction had written any, so every one of sixteen fresh digests was reported "too thin to trust" and sent to an agent."""
    q = quilt(tmp_path)
    r = run("refs", "build", "--only", "extract,map", cwd=q)
    assert r.exit_code == 0, r.output
    assert "too thin to trust" not in r.output, r.output


def test_a_statement_that_brings_its_own_environment_is_refused(tmp_path: Path) -> None:
    """Thirteen of thirteen first attempts by two agents wrapped the statement in its own environment -- one had read a note about exactly this -- and loom wrapped it again."""
    q, ck = mapped(tmp_path)
    for bad in (
        r"\begin{theorem}Let $f$ be.\end{theorem}",
        r"Let $f$ be.\label{mine}",
        r"\begin{definition*}X\end{definition*}",
    ):
        r = propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", bad)
        assert r.exit_code != 0 and "body only" in r.output, r.output
    assert not (q / "digests" / f"{ck}.proposed.tex").exists()
    # an enumerate inside the body is the body, and is fine
    ok = propose(
        q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", r"Let $f$: \begin{enumerate}\item a\end{enumerate}"
    )
    assert ok.exit_code == 0, ok.output


def test_an_agents_link_is_the_runs_never_the_authors(tmp_path: Path) -> None:
    """Eleven links in the second study run were recorded as the author's, by way of git."""
    import pytest

    from loom.refs.links import read_links

    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0
    assert propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3").exit_code == 0
    a, b = f"{ck}-thm-1.1", f"{ck}-thm-4.1"
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("AI_AGENT", "1")
        bare = run("refs", "link", "--from", a, "--to", b, "--kind", "depends-on", "--why", "w", cwd=q)
        assert bare.exit_code != 0 and "--session" in bare.output
        ok = run(
            "refs",
            "link",
            "--from",
            a,
            "--to",
            b,
            "--kind",
            "depends-on",
            "--why",
            "w",
            "--session",
            "2026-x",
            cwd=q,
        )
        assert ok.exit_code == 0, ok.output
    finally:
        mp.undo()
    assert read_links(q)[0].by == "2026-x"


def test_a_statement_over_a_page_break_is_anchored_to_both_pages(tmp_path: Path) -> None:
    """A clause dropped from the continuation page was invisible on the surface built to catch it, because the anchor was one page."""
    from loom.refs.proposals import load_results, page_context

    q, ck = mapped(tmp_path)
    pages = _home(q, ck) / "pages"
    (pages / "0012.txt").write_text("Theorem 4.1. Every widget is a gadget when\n")
    (pages / "0013.txt").write_text("the theory is perfect, and every gadget is a widget.\nProof. Clear.\n")
    one = propose(q, ck, "thm-4.1", 12, "Every widget is a gadget when the theory is perfect", "X")
    assert one.exit_code != 0, "the quotation runs onto the next page, so one page cannot hold it"
    both = propose(q, ck, "thm-4.1", "12-13", "Every widget is a gadget when the theory is perfect", "X")
    assert both.exit_code == 0 and "pp.12-13" in both.output, both.output
    r = load_results(q, ck)[f"{ck}-thm-4.1"]
    assert r.anchor.page == 12 and r.anchor.last == 13
    ctx, found = page_context(q, r)
    assert found and "every gadget is a widget" in ctx, "the continuation is on screen, where a dropped clause shows"
    assert "p.~12--13" in (q / "digests" / f"{ck}.proposed.tex").read_text()


def test_a_run_may_correct_its_own_unverified_proposal(tmp_path: Path) -> None:
    """Unable to withdraw its own mistake, an agent re-proposed under `-clean` ids: eleven results became twenty-two."""
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "first", session="R1").exit_code == 0
    again = propose(
        q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "second", session="R1", supersedes=f"{ck}-thm-1.1"
    )
    assert again.exit_code == 0, again.output
    rs = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"]
    assert len(rs) == 1 and rs[0]["statement"] == "second", "the same id, corrected -- not a second proposal"
    # another run may not overwrite it: that is not a correction, it is a disagreement for the author
    other = propose(
        q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "third", session="R2", supersedes=f"{ck}-thm-1.1"
    )
    assert other.exit_code != 0


def test_an_authors_edit_is_kept_and_shown(tmp_path: Path) -> None:
    """ "edited by isaac" said an edit happened, not what it was; the edit was a dropped clause, the one thing worth learning from."""
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Let $f$ be DM.").exit_code == 0
    assert (
        run(
            "refs",
            "verify",
            f"{ck}-thm-1.1",
            "--statement",
            "Let $f$ be DM-type with a perfect theory.",
            "--yes",
            "--author",
            "i",
            cwd=q,
        ).exit_code
        == 0
    )
    why = run("refs", "why", f"{ck}-thm-1.1", cwd=q)
    assert "the author's edit" in why.output
    assert "-Let $f$ be DM." in why.output and "+Let $f$ be DM-type with a perfect theory." in why.output
    # a second correction: the diff is still from what was proposed, never from the author's own first try
    again = run(
        "refs", "verify", f"{ck}-thm-1.1", "--statement", "Let $f$ be DM-type.", "--yes", "--author", "i", cwd=q
    )
    assert again.exit_code == 0, again.output
    why = run("refs", "why", f"{ck}-thm-1.1", cwd=q).output
    assert why.count("the author's edit") == 1
    assert "-Let $f$ be DM." in why and "+Let $f$ be DM-type." in why and "-Let $f$ be DM-type with" not in why
    # and the document has it: a re-verify once changed the record and left the digest -- and so `loom source` -- as it was
    digest = (q / "digests" / f"{ck}.tex").read_text()
    assert "Let $f$ be DM-type.\n" in digest and "perfect theory" not in digest
    assert "Let $f$ be DM-type." in run("source", f"{ck}-thm-1.1", cwd=q).output


def test_findings_for_a_run_include_what_the_author_decided(tmp_path: Path) -> None:
    """A reattaching agent learned the author's decisions by running `refs why` on each id it happened to know, three times over."""
    q, ck = mapped(tmp_path)
    runname = run("ai", "start", "r", cwd=q).output.strip()
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", session=runname).exit_code == 0
    assert run("refs", "discard", f"{ck}-thm-1.1", "--reason", "wrong theorem", "--author", "i", cwd=q).exit_code == 0
    out = run("ai", "findings", "--session", runname, cwd=q).output
    assert f"{ck}-thm-1.1" in out and "discarded -- wrong theorem" in out


def test_source_on_an_equation_label_prints_what_holds_it(tmp_path: Path) -> None:
    """An equation's label resolved to a region, which `source` indexed as a node: a KeyError on a digest's display equation."""
    q = quilt(tmp_path)
    digest = q / "digests" / "Calloway14.tex"
    digest.write_text(
        digest.read_text() + "\n\\section*{Overview}\nWe prove\n\\begin{equation}\\label{Calloway14-eqx}x=y\\end{equation}\n"
    )
    r = run("source", "Calloway14-eqx", cwd=q)
    assert r.exit_code == 0 and "KeyError" not in r.output and "inside" in r.output, r.output


def test_a_book_length_map_with_almost_no_sections_says_it_is_a_guess() -> None:
    from loom.refs.pages import PageMap, Section

    book = PageMap(sha256="x", pages=679, sections=[Section("1", "See", 3), Section("2", "Grothendieck", 9)])
    paper = PageMap(sha256="x", pages=44, sections=[Section("1", "Introduction", 1)])
    assert book.suspect and not paper.suspect


def _home(q: Path, ck: str = "Vir12") -> Path:
    """Where the store keeps one work; named rather than globbed, because the demo quilt ships a work of its own."""
    from loom.refs.fetch import work_dir
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    return work_dir(q, scan(load_quilt(q)).bib[ck])


def test_a_folio_number_at_a_page_join_is_not_part_of_the_text(tmp_path: Path) -> None:
    """Alper's book: a quotation over pp.353-354 matched only once the agent typed the printed page number "345" into it."""
    from loom.refs.pages import read_pages

    q, ck = mapped(tmp_path)
    home = _home(q, ck)
    (home / "pages" / "0005.txt").write_text("Definition 5.1. A morphism is good\nif\n345\n")
    (home / "pages" / "0006.txt").write_text("346\n(1) it is exact, and\nso on\n7\nand on\n(2) widgets exist.\nend\n")
    text = read_pages(home, 5, 6) or ""
    assert "345" not in text and "346" not in text
    assert "\n7\n" in text, "a lone number inside a page is content, not a folio"
    ok = propose(q, ck, "def-5.1", "5-6", "A morphism is good if (1) it is exact", "S")
    assert ok.exit_code == 0, ok.output
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
    assert r.exit_code == 0, r.output
    assert "not in the quoted page text" in r.output and "Deligne" in r.output and "Mumford" in r.output
    # math, commands and the paper's own words are never flagged
    assert words_not_on_page(r"Let $\mathcal{X}$ be a \emph{DM-type} morphism.", "Let X be a DM-type morphism.") == []
    assert words_not_on_page("Every widget is a gadget.", "Every  wid-\nget is a gadget.") == []


def test_a_pending_proposal_carries_the_words_its_page_does_not_have(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    assert (
        propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Let $f$ be a nice DM-type morphism").exit_code
        == 0
    )
    b = run("build", cwd=q)
    assert b.exit_code in (0, 1), b.output
    manifest = json.loads((q / "build" / "manifest.json").read_text())
    row = next(v for k, v in manifest["references"][ck]["results"].items() if k.endswith("thm-1.1"))
    assert row["not_on_page"] == ["nice"]
    assert not row.get("page_images"), "no PDF on this machine: no image, and the viewer says so"


@pytest.mark.tex
def test_a_work_with_no_pdf_gets_no_geometry(tmp_path: Path) -> None:
    """What `pdftoppm` used to guard, now guarded where geometry is made: a page is drawn from the document that is there, or not at all.

    The image pipeline it replaces rendered the anchor page to PNG and keyed the cache by artifact hash, so a replaced PDF could not show its page under the old name. The sidecar has no cache to go stale -- it is computed from the PDF on disk at build time -- so the property to pin is the other half: no document, no rectangles, and the viewer says so rather than drawing somewhere plausible.
    """
    from loom.render.build import _attach_spans

    q, ck = mapped(tmp_path)
    home = _home(q, ck)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "S").exit_code == 0
    manifest = {"references": {ck: {"artifacts": {"dir": home.relative_to(q).as_posix(), "pdf": False}}}}
    files: dict[str, object] = {}
    _attach_spans(q, manifest, files)
    assert "spans" not in manifest["references"][ck]
    assert not files


def test_local_names_are_the_papers_numbering(tmp_path: Path) -> None:
    """Brion numbers corollaries within a subsection; the agent split 2.3's two and invented `cor-2.3-quotient`, which no citation by number can find (contract §3.2)."""
    q, ck = mapped(tmp_path)
    bad = propose(q, ck, "cor-2.3-quotient", 1, "Let $f$ be a DM-type morphism", "S")
    assert bad.exit_code != 0 and "cor-2.3.1" in bad.output and "star-" in bad.output
    assert propose(q, ck, "thm-quotient", 1, "Let $f$ be a DM-type morphism", "S").exit_code != 0
    for ok in ("cor-2.3.1", "thm-A", "prop-A.2", "lem-star-1", "thm-7.5.11"):
        r = propose(q, ck, ok, 1, "Let $f$ be a DM-type morphism", "S")
        assert r.exit_code == 0, (ok, r.output)


def test_propose_does_not_hand_an_agent_the_authors_verb(tmp_path: Path) -> None:
    """ "All 13 verified and are waiting": the agent reported the anchor check to the author in the author's own word (§5.6)."""
    import pytest

    q, ck = mapped(tmp_path)
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("AI_AGENT", "1")
        r = propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "S")
        assert r.exit_code == 0, r.output
        assert "waiting for the author" in r.output and "loom refs verify" not in r.output
    finally:
        mp.undo()
    helptext = run("refs", "propose", "--help", cwd=q).output
    assert "verified against" not in helptext and "this is what is verified" not in helptext


def test_the_author_can_correct_the_locator_when_verifying(tmp_path: Path) -> None:
    """Brion's "Theorem 3.2" was the paper's Corollary 3.2.1; the author could fix the statement at verify time and not the name."""
    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "S").exit_code == 0
    r = run(
        "refs",
        "verify",
        f"{ck}-thm-1.1",
        "--local",
        "cor-1.1.1",
        "--taxon",
        "corollary",
        "--yes",
        "--author",
        "i",
        cwd=q,
    )
    assert r.exit_code == 0, r.output
    recs = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"]
    assert [x["id"] for x in recs] == [f"{ck}-cor-1.1.1"] and recs[0]["taxon"] == "corollary"
    assert any(o.get("act") == "renamed" and o.get("was") == f"{ck}-thm-1.1" for o in recs[0]["origin"])
    assert f"{ck}-cor-1.1.1" in (q / "digests" / f"{ck}.tex").read_text()


def test_the_ingest_mode_says_one_thing_about_a_work_with_no_source() -> None:
    """Two sections of that name, one telling the agent to stop and one to propose: an agent reconciled them by guessing (CLAUDE.md passes 5 and 6)."""
    from importlib import resources

    text = (resources.files("loom") / "assets" / "ai" / "modes" / "ingest.md").read_text(encoding="utf-8")
    assert text.count("## When there is no source") == 1


def test_the_write_api_verifies_renames_and_discards_a_proposal(tmp_path: Path) -> None:
    """The digest view's three verbs, through the functions the CLI calls; a click in the browser is the author's, so no agent marker stops it."""
    from loom.render.api import ApiError, handle

    q, ck = mapped(tmp_path)
    assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "S").exit_code == 0
    assert propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G", level="3").exit_code == 0
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("AI_AGENT", "1")
        got = handle(
            q, "digest-verify", {"node": f"{ck}-thm-1.1", "statement": "S'", "local": "cor-1.1.1", "author": "i"}
        )
        assert got["ok"] and "renamed from" in got["result"]
        gone = handle(q, "digest-discard", {"session": _sid(q), "node": f"{ck}-thm-4.1", "reason": "not the paper's", "author": "i"})
        assert gone["ok"]
    finally:
        mp.undo()
    recs = {x["id"]: x for x in json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"]}
    assert recs[f"{ck}-cor-1.1.1"]["state"] == "verified" and recs[f"{ck}-cor-1.1.1"]["statement"] == "S'"
    assert recs[f"{ck}-thm-4.1"]["state"] == "discarded"
    with pytest.raises(ApiError):
        handle(q, "digest-verify", {"session": _sid(q), "node": f"{ck}-thm-9.9", "author": "i"})


def test_a_work_with_a_source_is_quoted_from_its_source(tmp_path: Path) -> None:
    """Graber and Pandharipande's formula is control bytes in the PDF's text layer; the quotation stopped before it and the formula was written from memory. Their source has it verbatim."""
    q, ck = mapped(tmp_path)
    src = _home(q, ck) / "src"
    src.mkdir(exist_ok=True)
    (src / "main.tex").write_text(
        "The localization formula is then:\n\\begin{equation}\n\\label{exloc} \\Xvir =\n\\iota_* \\sum  \\frac{\\Xivir}{e(N^{\\it{vir}}_i)}\n\\end{equation}\nin $A_*(X)$.\n",
        encoding="latin-1",
    )
    quote = "\\Xvir = \\iota_* \\sum \\frac{\\Xivir}{e(N^{\\it{vir}}_i)}"
    r = run(
        "refs", "propose", ck, "--local", "eq-1", "--source-file", "main.tex", "--level", "1",
        "--source-text", quote, "--statement", "[X]^{vir} = \\iota_* \\sum \\frac{[X_i]^{vir}}{e(N_i^{vir})}", cwd=q,
    )  # fmt: skip
    assert r.exit_code == 0, r.output
    rec = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"][0]
    a = rec["anchor"]
    assert a["kind"] == "tex" and a["path"].endswith("src/main.tex") and "page" not in a
    raw = (q / a["path"]).read_bytes()
    assert raw[a["bytes"][0] : a["bytes"][1]].decode().split() == quote.split()
    assert rec["taxon"] == "equation" and rec["id"].endswith("-eq-1")
    shadow = (q / "digests" / f"{ck}.proposed.tex").read_text()
    assert "\\begin{theorem}[{\\cite[Equation (1)]{" in shadow, "a display is named as the paper names it"
    bad = run(
        "refs", "propose", ck, "--local", "eq-2", "--source-file", "main.tex",
        "--source-text", "a formula the file does not have", "--statement", "x", cwd=q,
    )  # fmt: skip
    assert bad.exit_code != 0 and "not in" in bad.output
    both = run("refs", "propose", ck, "--local", "eq-3", "--source-file", "main.tex", "--page", "1",
               "--source-text", "x", "--statement", "x", cwd=q)  # fmt: skip
    assert both.exit_code != 0 and "one of them" in both.output


def test_grep_is_a_phrase_and_says_so(tmp_path: Path) -> None:
    """ "Localization in equivariant\\|Edidin.*Graham" found nothing, and the agent took the silence for an answer."""
    q, _ck = mapped(tmp_path)
    r = run("refs", "grep", "Localization in equivariant\\|Edidin.*Graham", cwd=q)
    assert r.exit_code != 0 and "literal phrase" in r.output
    assert run("refs", "grep", "widget", cwd=q).exit_code == 0


def test_a_source_fetched_on_a_preprint_id_says_so_in_the_digest(tmp_path: Path) -> None:
    """Chang, Kiem and Li's source came from arXiv into the work's DOI directory, and the digest claimed the DOI: DR-109's version warning never fired, while the preprint's Theorem 3.4 is the published Theorem 3.5 and its conclusion differs."""
    from loom.refs.fetch import record_source

    q, ck = mapped(tmp_path)
    home = _home(q, ck)
    (home / "src").mkdir(exist_ok=True)
    (home / "src" / "main.tex").write_text(
        "\\documentclass{article}\n\\newtheorem{theorem}{Theorem}\n\\begin{document}\n\\begin{theorem}\\label{t}A.\\end{theorem}\n\\end{document}\n"
    )
    record_source(home, "arxiv:1607.00001", "candidate")
    r = run("digest", "extract", ck, str(home / "src" / "main.tex"), "--no-compile", cwd=q)
    assert r.exit_code == 0, r.output
    head = (q / "digests" / f"{ck}.tex").read_text().splitlines()[:4]
    assert "% !LOOM extracted-from: arxiv:1607.00001" in head


def test_a_read_command_logs_to_the_session_it_is_given(tmp_path: Path) -> None:
    """`loom refs page ... --run` was refused twice in one study run; the orientation says to pass --session wherever it is accepted, and the log is the record of what an agent read."""
    q, ck = mapped(tmp_path)
    runname = run("ai", "start", "r", cwd=q).output.strip()
    for args in (["refs", "page", ck, "12"], ["refs", "coverage"], ["refs", "grep", "widget"]):
        got = run(*args, "--session", runname, cwd=q)
        assert got.exit_code == 0, got.output
    log = (q / ".loom" / "sessions" / runname / "run.log").read_text()
    assert f"loom refs page {ck} 12" in log and "loom refs coverage" in log and "loom refs grep widget" in log


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


def test_an_anchor_carries_only_its_own_kind_of_keys() -> None:
    """`to_json` strips by name, so a field added to `Anchor` and not named there lands in both kinds: a LaTeX anchor claiming a `basis`, or a page anchor carrying a byte range. Plan 0.13 item 2 adds three such fields at once."""
    from loom.refs.proposals import Anchor, Result

    pdf = Result(
        id="X-thm-1",
        local="thm-1",
        anchor=Anchor(
            kind="pdf", sha256="a" * 64, page=7, basis="text", start=1043, end=1189, quads=[[1.0, 2.0, 3.0, 4.0]]
        ),
    ).to_json()["anchor"]
    assert set(pdf) == {"kind", "sha256", "page", "quads", "basis", "start", "end"}

    tex = Result(
        id="X-thm-2", local="thm-2", anchor=Anchor(kind="tex", sha256="b" * 64, path="digests/X.tex")
    ).to_json()["anchor"]
    assert set(tex) == {"kind", "sha256", "path"}, "a file anchor has no page, no geometry and no basis"

    # a box-basis anchor records geometry and no offsets, and survives the round trip
    box = Anchor(kind="pdf", sha256="c" * 64, page=2, basis="box", quads=[[10.0, 20.0, 30.0, 28.0]])
    back = Result.from_json(Result(id="X-thm-3", local="thm-3", anchor=box).to_json()).anchor
    assert back == box and "start" not in Result(id="X-thm-3", local="thm-3", anchor=box).to_json()["anchor"]


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


@pytest.mark.tex
def test_a_selection_on_a_real_page_becomes_an_anchor(tmp_path: Path) -> None:
    """The whole of plan 0.13's slice on the loom side: what a reader selected, mapped against the committed page text and the word boxes of the one PDF this repository carries.

    On a copy, because reading a page caches its word boxes inside the quilt, and the checked-in one is compared to the generator's output file by file.
    """
    import shutil

    from loom.render.api import handle

    q = tmp_path / "showcase"
    shutil.copytree(Path(__file__).resolve().parents[2] / "tests" / "quilts" / "showcase", q)
    text = "The median orders of a weighted digraph are in bijection with the vertices"
    got = handle(q, "locate", {"citekey": "Bellamy19", "page": 2, "text": text})
    a = got["anchor"]
    assert a["basis"] == "text" and a["page"] == 2 and a["quads"], got["result"]
    page_text = (q / "digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt").read_text()
    assert page_text[a["start"] : a["end"]] == text
    assert got["page_box"] == {"width": 612.0, "height": 792.0}

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

    q = quilt(tmp_path)
    shutil.rmtree(q / "digests" / "storage" / "doi" / "10.4171_demo_14-1")
    return q


def _source_only(tmp_path: Path) -> Path:
    """The demo quilt with the PDF and page text removed, and the paper's LaTeX left in place."""
    import shutil

    (tmp_path / "b").mkdir(exist_ok=True)
    q = quilt(tmp_path / "b")
    home = q / "digests" / "storage" / "doi" / "10.4171_demo_14-1"
    (home / "paper.pdf").unlink()
    (home / "sections.json").unlink()
    shutil.rmtree(home / "pages")
    return q


def test_extract_refuses_a_source_outside_the_store(tmp_path: Path) -> None:
    """A digest made from a file on the author's desktop cites pages nobody else can open, so the obligation starts where the digest is born."""
    q = quilt(tmp_path)
    loose = tmp_path / "paper.tex"
    loose.write_text("\\documentclass{article}\\begin{document}\\end{document}\n", encoding="utf-8")
    r = run("digest", "extract", "Ref20", str(loose), cwd=q)
    assert r.exit_code != 0
    assert "not in loom's store" in r.output and "loom refs add" in r.output


def test_extract_with_no_source_says_how_to_get_one(tmp_path: Path) -> None:
    """The refusal names both routes: fetching where an identifier serves it, and adding source already held."""
    q = _no_copy(tmp_path)
    (q / "digests" / "Calloway14.tex").unlink()
    r = run("digest", "extract", "Calloway14", cwd=q)
    assert r.exit_code != 0
    assert "holds no source" in r.output and "loom refs fetch Calloway14" in r.output and "loom refs add Calloway14" in r.output


def test_a_digest_with_no_readable_copy_warns_and_never_errors(tmp_path: Path) -> None:
    """Loom cannot fetch without consent, so renderable content nothing can back is reported and never fatal."""
    q = _no_copy(tmp_path)
    r = run("lint", "--json", cwd=q)
    said = [d for d in json.loads(r.output) if d["code"] == "loom:no-readable-copy"]
    assert [d["severity"] for d in said] == ["warning"]
    assert r.exit_code == 0
    assert "loom refs unreadable Calloway14" in said[0]["message"]
    # and source alone is an info, not a warning: the paper's own LaTeX is what a statement is checked against
    quieter = [d for d in json.loads(run("lint", "--json", cwd=_source_only(tmp_path)).output) if d["code"] == "loom:no-readable-copy"]
    assert [d["severity"] for d in quieter] == ["info"]
    assert "no PDF" in quieter[0]["message"]


def test_declaring_a_work_unreadable_suppresses_the_lint_and_undo_restores_it(tmp_path: Path) -> None:
    """Impossible is declared, never inferred: nothing in a bibliography entry says a work has no fixed document."""
    q = _no_copy(tmp_path)
    said = run(
        "refs", "unreadable", "Calloway14", "--author", "A. Author", "--why", "a living work with no fixed version", cwd=q
    )
    assert said.exit_code == 0, said.output
    codes = [d["code"] for d in json.loads(run("lint", "--json", cwd=q).output)]
    assert "loom:no-readable-copy" not in codes
    back = run(
        "refs",
        "unreadable",
        "Calloway14",
        "--author",
        "A. Author",
        "--undo",
        "--why",
        "a version was published after all",
        cwd=q,
    )
    assert back.exit_code == 0, back.output
    codes = [d["code"] for d in json.loads(run("lint", "--json", cwd=q).output)]
    assert "loom:no-readable-copy" in codes


def test_the_declaration_is_appended_and_never_edited(tmp_path: Path) -> None:
    """Every record loom keeps is appended; the standing claim is the fold, so the reversal is still readable."""
    from loom.refs.unreadable import declarations, load_events

    q = _no_copy(tmp_path)
    run("refs", "unreadable", "Calloway14", "--author", "A. Author", "--why", "no fixed version", cwd=q)
    run("refs", "unreadable", "Calloway14", "--author", "A. Author", "--undo", "--why", "wrong", cwd=q)
    assert len(load_events(q)) == 2
    assert declarations(q, "unreadable") == {}


def test_unreadable_refuses_under_an_agent_and_without_a_reason(tmp_path: Path) -> None:
    """Whether a work can be obtained at all is a claim about the world, which is the author's to make (DR-185).

    **The guard is on the identity, not the door** (plan 0.13 §8). This test asserted the opposite until 2026-09-21: it required that `--author "A. Author"` be refused under `AI_AGENT`, which is the author unable to use their own verb from the terminal their agent happens to be running in. The marker is a safety net for a writer who declared nothing, and an explicit name wins over it -- in both directions, since a name that calls itself an agent is refused whatever shell it came from.
    """
    q = quilt(tmp_path)
    assert "--why is required" in run("refs", "unreadable", "Calloway14", cwd=q).output
    os.environ["AI_AGENT"] = "1"
    try:
        bare = run("refs", "unreadable", "Calloway14", "--why", "no fixed version", cwd=q)
        named = run("refs", "unreadable", "Calloway14", "--author", "A. Author", "--why", "no fixed version", cwd=q)
        robot = run("refs", "unreadable", "Kre99", "--author", "Agent", "--why", "could not fetch", cwd=q)
    finally:
        del os.environ["AI_AGENT"]
    # nothing declared: the marker is all there is to go on, and it refuses rather than guessing
    assert bare.exit_code != 0 and "agent is running this shell" in bare.output
    # a person who named themselves is a person, whatever shell they are in
    assert named.exit_code == 0, named.output
    # and a declared agent is refused whichever surface it came through
    assert robot.exit_code != 0 and "is an agent" in robot.output


def test_forget_is_keyed_by_citekey_or_by_a_prefix_of_a_stored_hash(tmp_path: Path) -> None:
    """The tombstone stops the store re-offering an entry; a document with no entry is named by its content."""
    from loom.refs.scan import record_copy
    from loom.refs.unreadable import declarations

    q = quilt(tmp_path)
    sha = "9f2c" + "0" * 60
    record_copy(q, sha, "refs/whatever.pdf", "digests/storage/file/9f2c/paper.pdf")
    assert run("refs", "forget", "9f2c00", "--author", "A. Author", "--why", "a duplicate scan", cwd=q).exit_code == 0
    assert (
        run("refs", "forget", "Calloway14", "--author", "A. Author", "--why", "deliberately not cited", cwd=q).exit_code == 0
    )
    assert set(declarations(q, "forget")) == {f"sha256:{sha}", "Calloway14"}
    unknown = run("refs", "forget", "nothing-like-this", "--author", "A. Author", "--why", "x", cwd=q)
    assert unknown.exit_code != 0 and "neither a citekey" in unknown.output


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
    work = next(w for w in survey(open_scan(str(q))) if w.citekey == "Calloway14")
    assert work.source and not work.pdf
    assert work.blocked == ("", "")  # source is enough to extract from; the missing page is the lint's business


def test_the_viewer_can_switch_retitle_and_tombstone_a_session(tmp_path: Path) -> None:
    """The panel's selector writes through the same functions `loom session` calls, so the two surfaces cannot spell an event differently."""
    from loom.render.api import handle
    from loom.sessions import active, sessions

    q = quilt(tmp_path)
    first = run("session", "new", "morning", "--author", "A. Author", cwd=q).output.split()[0]
    second = run("session", "new", "afternoon", "--author", "A. Author", cwd=q).output.split()[0]
    assert active(q) == second

    assert handle(q, "session-use", {"session": "morning", "author": "A. Author"})["ok"]
    assert active(q) == first
    assert handle(q, "session-rename", {"session": first, "title": "early pass", "author": "A. Author"})["ok"]
    assert sessions(q)[first].title == "early pass"

    # a tombstone leaves the log alone and stops being the write target
    assert handle(q, "session-delete", {"session": first, "author": "A. Author"})["ok"]
    assert first not in sessions(q)
    assert active(q) is None
    # and purging is not reachable from here at all
    assert "session-purge" not in CAPABILITIES


# --- Dispatch: the mailbox, presence and the guard (plan 0.13 §8) ---------------------------------------------


def test_a_message_lands_with_nobody_listening_and_is_read_not_consumed(tmp_path: Path) -> None:
    """Refusing a message because nobody is attached would lose what the author typed, for a reason the browser cannot fix."""
    from loom.mailbox import attached, cursor, post, read_events, set_cursor

    q = quilt(tmp_path)
    sid = run("session", "new", "referee pass", "--author", "A. Author", cwd=q).output.split()[0]
    assert attached(q, sid) == []
    post(q, sid, "Have a look at dm-0003.", "A. Author")

    # read, never consumed: a cursor moves and the message stays, so a second reader sees it and a crashed one resumes
    first = read_events(q, sid, cursor(q, sid, "Referee Agent"))
    assert [e.body for e in first] == ["Have a look at dm-0003."]
    set_cursor(q, sid, "Referee Agent", first[-1].seq)
    assert read_events(q, sid, cursor(q, sid, "Referee Agent")) == []
    assert [e.body for e in read_events(q, sid, cursor(q, sid, "Tutor Agent"))] == ["Have a look at dm-0003."]


def test_presence_goes_stale_rather_than_being_believed_forever(tmp_path: Path) -> None:
    """A reader that was killed writes no farewell; a list that believed it would tell the composer somebody is there when nobody is."""
    import json as _json

    from loom.mailbox import ATTACHED, attach, attached, detach, session_dir

    q = quilt(tmp_path)
    sid = run("session", "new", "r", "--author", "A. Author", cwd=q).output.split()[0]
    attach(q, sid, "Referee Agent", "agent")
    assert [r["who"] for r in attached(q, sid)] == ["Referee Agent"]

    old = _json.loads((session_dir(q, sid) / ATTACHED).read_text())
    old[0]["beat"] = "2020-01-01T00:00:00Z"
    (session_dir(q, sid) / ATTACHED).write_text(_json.dumps(old))
    assert attached(q, sid) == []

    attach(q, sid, "Referee Agent", "agent")
    detach(q, sid, "Referee Agent")
    assert attached(q, sid) == []


def test_an_agent_that_has_not_said_who_it_is_is_refused_rather_than_guessed_at(tmp_path: Path) -> None:
    """Identity is declared, not sniffed: a marker distinguishes well today and an author may ask an agent to run a command."""
    from loom.cli._common import writer

    q = quilt(tmp_path)
    assert writer(q, "Referee Agent") == ("Referee Agent", "agent")
    assert writer(q, "A. Author") == ("A. Author", "person")
    os.environ["AI_AGENT"] = "1"
    try:
        with pytest.raises(Exception, match="has not said who it is"):
            writer(q, None)
        # and an explicit identity wins over the marker
        assert writer(q, "A. Author")[1] == "person"
    finally:
        del os.environ["AI_AGENT"]


def test_the_write_api_refuses_a_post_from_another_page(tmp_path: Path) -> None:
    """A browser blocks a cross-origin response and never the request, so a page the author is merely reading could otherwise write into their quilt."""
    from loom.render.serve import LoomHandler

    checks = LoomHandler._csrf

    class Fake:
        token = "right"
        server = type("S", (), {"server_address": ("127.0.0.1", 8791)})()

        def __init__(self, headers: dict[str, str]) -> None:
            self.headers = headers

    good = {"Content-Type": "application/json", "X-Loom-Token": "right", "Origin": "http://127.0.0.1:8791"}
    assert checks(Fake(good)) == ""  # type: ignore[arg-type]
    assert "not this server" in checks(Fake({**good, "Origin": "https://example.org"}))  # type: ignore[arg-type]
    # a cross-site form post can set neither a custom header nor a JSON content type
    assert "application/json" in checks(Fake({**good, "Content-Type": "application/x-www-form-urlencoded"}))  # type: ignore[arg-type]
    assert "X-Loom-Token" in checks(Fake({"Content-Type": "application/json"}))  # type: ignore[arg-type]


def test_the_composer_posts_and_says_whether_anyone_heard(tmp_path: Path) -> None:
    """The viewer's composer and `loom session send` are the same mechanism: both append, and both say who was listening."""
    from loom.mailbox import attach, read_events
    from loom.render.api import handle

    q = quilt(tmp_path)
    sid = run("session", "new", "referee pass", "--author", "A. Author", cwd=q).output.split()[0]
    said = handle(q, "message", {"session": sid, "text": "Look at the proof.", "author": "A. Author"})
    assert said["ok"] and said["session"] == sid and said["attached"] == []
    assert [e.body for e in read_events(q, sid)] == ["Look at the proof."]

    attach(q, sid, "Referee Agent", "agent")
    again = handle(q, "message", {"session": sid, "text": "And the hypothesis.", "author": "A. Author"})
    assert [r["who"] for r in again["attached"]] == ["Referee Agent"]


def test_an_anchor_round_trips_in_both_bases(tmp_path: Path) -> None:
    """`Result.to_json` strips keys by a literal tuple per kind, so a field added to one basis lands silently in the other."""
    from loom.refs.proposals import Anchor, Result

    text = Anchor(kind="pdf", sha256="a" * 64, page=3, quads=[[1.0, 2.0, 3.0, 4.0]], basis="text", start=10, end=42)
    box = Anchor(kind="pdf", sha256="b" * 64, page=7, quads=[[5.0, 6.0, 7.0, 8.0]], basis="box")
    src = Anchor(kind="tex", sha256="c" * 64, path="src/main.tex", bytes=[100, 200])
    for a in (text, box, src):
        out = Result(id="x", local="l", anchor=a).to_json()["anchor"]
        back = Result.from_json({"id": "x", "local": "l", "anchor": out}).anchor
        assert (back.kind, back.sha256, back.page, back.quads, back.basis) == (a.kind, a.sha256, a.page, a.quads, a.basis)
        assert (back.start, back.end, back.path, back.bytes) == (a.start, a.end, a.path, a.bytes)
    # and a pdf anchor never carries a tex anchor's fields, nor the other way round
    assert "path" not in Result(id="x", local="l", anchor=text).to_json()["anchor"]
    assert "quads" not in Result(id="x", local="l", anchor=src).to_json()["anchor"]
    assert "basis" not in Result(id="x", local="l", anchor=src).to_json()["anchor"]


def test_a_hyphenated_line_and_a_ligature_both_place(tmp_path: Path) -> None:
    """The two extractions of a page disagree about hyphens a line break left behind and about spacing around mathematics."""
    from loom.refs.search import locate_span

    # one word broken across a line, as `-bbox-layout` reports it, and a ligature the two readings spell differently
    words = [
        ("Let", 72.0, 100.0, 90.0, 112.0),
        ("the", 94.0, 100.0, 112.0, 112.0),
        ("denom-", 116.0, 100.0, 160.0, 112.0),
        ("inators", 72.0, 114.0, 110.0, 126.0),
        ("be", 114.0, 114.0, 128.0, 126.0),
        ("affine", 132.0, 114.0, 164.0, 126.0),
    ]
    xml = "".join(
        f'<word xMin="{a}" yMin="{b}" xMax="{c}" yMax="{d}">{w}</word>' for w, a, b, c, d in words
    )
    span = locate_span(xml, "Let the denominators be affine", 1)
    assert span is not None, "a word split by a line break must still place"
    assert len(span.lines) == 2, "one rectangle per line, because the quotation crosses one"


def test_a_resumed_session_starts_a_new_round(tmp_path: Path) -> None:
    """A round is what "changed since last time" is measured from, so resuming must open one rather than continue the last."""
    from loom.sessions import close, create, resume, sessions

    q = quilt(tmp_path)
    s = create(q, "morning", "A. Author")
    assert len(sessions(q)[s.id].rounds) == 1
    close(q, s.id, "A. Author")
    assert sessions(q)[s.id].state == "closed" and sessions(q)[s.id].rounds[-1].closed
    resume(q, s.id, "A. Author")
    again = sessions(q)[s.id]
    assert again.state == "open" and len(again.rounds) == 2
    assert again.last_opened == again.rounds[-1].opened


def test_a_kind_is_named_by_any_unambiguous_prefix_and_severity_only_grades_a_fault(tmp_path: Path) -> None:
    """`confirmation` is longer than `ok` was, and the extra letters should cost nothing."""
    from loom.records.annotations import full_kind

    assert full_kind("conf") == "confirmation"
    assert full_kind("n") == "note"
    assert full_kind("objection") == "objection"
    assert full_kind("c") is None, "citation and confirmation both start with c, so it must refuse rather than guess"
    assert full_kind("zzz") is None

    q = quilt(tmp_path)
    ok = run("comment", "dm-0002", "Fine.", "--kind", "conf", "--author", "A. Author", cwd=q)
    assert ok.exit_code == 0, ok.output
    bad = run("comment", "dm-0002", "Why?", "--kind", "question", "--severity", "major", "--author", "A. Author", cwd=q)
    assert bad.exit_code != 0 and "belongs on objection or suggestion" in bad.output


def test_a_post_carries_what_changed_since_the_last_one(tmp_path: Path) -> None:
    """A post says what changed and not only what was typed, so a parked agent needs no second call to learn what it is being asked about."""
    from loom.mailbox import read_events
    from loom.render.api import handle

    q = quilt(tmp_path)
    sid = run("session", "new", "referee pass", "--author", "A. Author", cwd=q).output.split()[0]
    assert run("comment", "dm-0002", "Orbits may be empty.", "--author", "A. Author", cwd=q).exit_code == 0
    handle(q, "message", {"session": sid, "text": "Have another look.", "author": "A. Author"})

    first = read_events(q, sid)[-1]
    assert [c["target"] for c in first.changed] == ["dm-0002"]
    assert first.changed[0]["by"] == "A. Author" and first.changed[0]["act"] == "created"

    # and the next post carries only what changed after it, rather than repeating itself
    handle(q, "message", {"session": sid, "text": "Anything?", "author": "A. Author"})
    assert read_events(q, sid)[-1].changed == []


# ---- a page of a cited work as a target (plan 0.13 item 2, item 4) -------------------------------------------------


def _note_on_page(q: Path, session: str, **fields: Any) -> str:
    """Append one `created` event for a note on a page of `Calloway14`, whose demo store is `doi/10.4171_demo_14-1`."""
    import json as _json

    from loom.records.log import append
    from loom.records.store import Records

    ann_id = fields.pop("id")
    anchor = {"kind": "pdf", "sha256": fields.pop("sha256"), "page": fields.pop("page", 2), **fields.pop("anchor", {})}
    append(
        q,
        {
            "when": "2026-09-21T10:00:00Z",
            "author": "A. Author",
            "kind": "human",
            "session": session,
            "event": "created",
            "id": ann_id,
            "target": "doi:10.4171/demo/14-1",
            "against": "sha256:" + anchor["sha256"],
            "anchor": anchor,
            "annotation_kind": fields.pop("kind", "question"),
            "body": fields.pop("body", "Is this the balanced case?"),
            **fields,
        },
    )
    Records(q)  # replays: a malformed event would be reported here, and the assertion below is on the shape
    return _json.dumps(anchor)


def test_a_note_on_a_page_round_trips_through_the_log(tmp_path: Path) -> None:
    """The log's `anchor` is two shapes under one name: the text triple every annotation carries, and -- on a note against a page -- the page anchor beside it, told apart by `kind`. `Selector.from_dict` used to swallow the page fields without a word."""
    from loom.records.annotations import load_records

    q = quilt(tmp_path)
    sid = run("session", "new", "reading", cwd=q).output.split()[0]
    _note_on_page(
        q, sid, id="a-2026-09-21-0001", sha256="feed" * 16,
        anchor={"basis": "text", "start": 12, "end": 36, "exact": "balanced at every vertex", "prefix": "locus is ", "suffix": " of the"},
    )
    _note_on_page(
        q, sid, id="a-2026-09-21-0002", sha256="feed" * 16, kind="note",
        anchor={"basis": "box", "quads": [[82.8, 278.1, 529.2, 315.7]], "exact": "", "prefix": "", "suffix": ""},
    )
    plain_out = run("comment", "dm-0003", "on a key, as ever", "--kind", "note", "--session", sid, "--author", "A. Author", cwd=q)
    assert plain_out.exit_code == 0, plain_out.output

    records, problems = load_records(q)
    assert problems == []
    by_id = {a.id: a for r in records for a in r.annotations}
    text = by_id["a-2026-09-21-0001"]
    assert text.anchor is not None and (text.anchor.kind, text.anchor.page, text.anchor.basis) == ("pdf", 2, "text")
    assert (text.anchor.start, text.anchor.end) == (12, 36) and text.anchor.quads is None
    assert text.selector is not None and text.selector.exact == "balanced at every vertex"
    assert text.target_key == "doi:10.4171/demo/14-1"
    box = by_id["a-2026-09-21-0002"]
    assert box.anchor is not None and box.anchor.basis == "box" and box.anchor.quads == [[82.8, 278.1, 529.2, 315.7]]
    # and a note on a key is exactly what it was: a selector and no page anchor
    plain = next(a for a in by_id.values() if a.target_key == "dm-0003")
    assert plain.anchor is None
    # the shape survives the dict form the manifest and the API hand around
    assert text.to_dict()["anchor"]["basis"] == "text" and "quads" not in text.to_dict()["anchor"]
    assert box.to_dict()["anchor"]["quads"] == [[82.8, 278.1, 529.2, 315.7]]


def test_a_note_on_a_page_resolves_against_the_store_and_not_against_a_key(tmp_path: Path) -> None:
    """`recorded` is whether the artifact the anchor names is the one in the store; `detached` is a quotation that no longer locates in the page's committed text; a box is never detached. The target is the work's identifier and the citekey is found through the bibliography, so a renamed citekey changes nothing. None of it touches a key's own text."""
    import json as _json

    from loom.records.store import Records

    q = quilt(tmp_path)
    home = q / "digests" / "storage" / "doi" / "10.4171_demo_14-1"
    sha = "feed" * 16
    (home / "sections.json").write_text(_json.dumps({"sha256": sha, "pages": 2, "chars": 60, "sections": []}))
    (home / "pages").mkdir(exist_ok=True)
    (home / "pages" / "0002.txt").write_text("the fixed locus is balanced at every vertex of the widget\n")
    sid = run("session", "new", "reading", cwd=q).output.split()[0]
    _note_on_page(q, sid, id="a-2026-09-21-0001", sha256=sha, anchor={"basis": "text", "start": 19, "end": 43, "exact": "balanced at every vertex", "prefix": "", "suffix": ""})
    _note_on_page(q, sid, id="a-2026-09-21-0002", sha256=sha, anchor={"basis": "text", "start": 0, "end": 5, "exact": "nowhere on this page", "prefix": "", "suffix": ""})
    _note_on_page(q, sid, id="a-2026-09-21-0003", sha256="dead" * 16, kind="note", anchor={"basis": "box", "quads": [[1, 2, 3, 4]], "exact": "", "prefix": "", "suffix": ""})

    from loom.cli._quilt import open_scan

    result = open_scan(str(q))
    by_id = {r.annotation.id: r for r in Records(q).resolved(result)}
    found = by_id["a-2026-09-21-0001"]
    assert found.work == "Calloway14" and found.recorded and not found.detached and found.span == (19, 43)
    lost = by_id["a-2026-09-21-0002"]
    assert lost.work == "Calloway14" and lost.recorded and lost.detached
    box = by_id["a-2026-09-21-0003"]
    assert box.work == "Calloway14" and not box.recorded and not box.detached  # a stale artifact, but the rectangles are the record

    # status: no row, no count, listed by work on request (design §4)
    j = _json.loads(run("status", "--json", cwd=q).output)
    assert not any("a-2026-09-21" in _json.dumps(e) for e in j["keys"].values())
    assert [r["id"] for r in j["reading"]] == ["a-2026-09-21-0001", "a-2026-09-21-0002", "a-2026-09-21-0003"]
    assert j["reading"][0]["work"] == "Calloway14" and j["reading"][0]["page"] == 2
    listed = run("status", "--reading", cwd=q).output
    assert "Calloway14" in listed and "a-2026-09-21-0002" in listed and "detached" in listed and "p.2 (box)" in listed
    assert "a-2026-09-21" not in run("status", cwd=q).output
    # and the agent's own list carries the citekey and the page, which is what it can act on
    mine = _json.loads(run("ai", "findings", "--session", sid, "--json", cwd=q).output)["findings"]
    assert {(f["work"], f["page"]) for f in mine} == {("Calloway14", 2)}


def _showcase(tmp_path: Path) -> Path:
    """A copy of the one quilt in the repository that carries a PDF; a copy because reading a page caches its word boxes inside it."""
    import shutil

    q = tmp_path / "showcase"
    shutil.copytree(Path(__file__).resolve().parents[2] / "tests" / "quilts" / "showcase", q)
    return q


@pytest.mark.tex
def test_a_note_on_a_page_is_written_by_citekey_or_identifier_and_refused_legibly(tmp_path: Path) -> None:
    """`loom comment` on a cited work (plan 0.13 item 2): the target may be the citekey the agent knows or the identifier a `cited:` link carries, and the record stores the identifier and the artifact's hash. Text is mapped with `refs locate`'s tolerance and recorded with offsets; a box is recorded as drawn. Each way of getting it wrong says what to do instead."""
    import json as _json

    q = _showcase(tmp_path)
    who = ("--author", "A. Author")
    said = run("comment", "Bellamy19", "Is this needed?", "--page", "2", "--quote", "totally unimodular", "--kind", "question", *who, cwd=q)
    assert said.exit_code == 0 and "Bellamy19 p.2 (text)  question" in said.output, said.output
    drawn = run("comment", "Bellamy19", "the polytope", "--page", "2", "--box", "82,278,529,316", "--kind", "note", *who, cwd=q)
    assert drawn.exit_code == 0 and "p.2 (box)  note" in drawn.output, drawn.output
    by_id = run("comment", "doi:10.4171/showcase/19-2", "by its identifier", "--page", "2", "--quote", "Boundedness holds", *who, cwd=q)
    assert by_id.exit_code == 0, by_id.output

    events = [_json.loads(line) for line in (q / "annotations" / "log.jsonl").read_text().splitlines()]
    text, box, ident = events[-3], events[-2], events[-1]  # appended in order, after the showcase's own
    page_text = (q / "digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt").read_text()
    assert text["target"] == "doi:10.4171/showcase/19-2" and text["against"].startswith("sha256:")
    assert text["anchor"]["basis"] == "text" and page_text[text["anchor"]["start"] : text["anchor"]["end"]] == "totally unimodular"
    assert text["anchor"]["exact"] == "totally unimodular" and text["anchor"]["prefix"] and "quads" not in text["anchor"]
    assert box["anchor"]["basis"] == "box" and box["anchor"]["quads"] == [[82.0, 278.0, 529.0, 316.0]]
    assert "quasi-polynomial" in box["anchor"]["exact"]  # the words under the rectangle, as a hint
    assert ident["target"] == text["target"]  # the citekey and the identifier name one work

    # the refusals, each naming what to do
    assert "say which page" in run("comment", "Bellamy19", "no page", "--quote", "x", *who, cwd=q).output
    assert "is a key in this quilt" in run("comment", "sh-0003", "page on a key", "--page", "2", "--quote", "x", *who, cwd=q).output
    assert "names none" in run("comment", "doi:10.1/nothing", "unknown", "--page", "2", "--quote", "x", *who, cwd=q).output
    assert "not both" in run("comment", "Bellamy19", "both", "--page", "2", "--quote", "x", "--box", "1,2,3,4", *who, cwd=q).output
    assert "loom refs page Bellamy19 2" in run("comment", "Bellamy19", "absent", "--page", "2", "--quote", "zebra crossing", *who, cwd=q).output
    assert "x0,y0,x1,y1" in run("comment", "Bellamy19", "bad box", "--page", "2", "--box", "1,2,3", *who, cwd=q).output

    # a batch line carries the same two keys
    batched = CliRunner().invoke(
        main,
        ["comment", "--batch", "--author", "A. Author", "--quilt", str(q)],
        input='{"target":"Bellamy19","message":"batched","page":2,"box":"82,278,529,316","kind":"note"}\n',
    )
    assert batched.exit_code == 0 and "(box)" in batched.output, batched.output


@pytest.mark.tex
def test_the_endpoint_and_the_record_map_a_place_the_same_way(tmp_path: Path) -> None:
    """`locate` answers and writes nothing; `comment` writes. Both call `anchor_on_page`, so what the viewer previewed is what the log says -- one function, one assertion."""
    import json as _json

    from loom.render.api import handle

    q = _showcase(tmp_path)
    text = "the constraint matrix is an incidence matrix"
    preview = handle(q, "locate", {"citekey": "Bellamy19", "page": 2, "text": text})["anchor"]
    written = handle(q, "comment", {"session": _sid(q), "target": "Bellamy19", "message": "so it is integral", "page": 2, "quote": text, "kind": "note", "author": "A. Author"})
    assert written["ok"], written
    event = _json.loads((q / "annotations" / "log.jsonl").read_text().splitlines()[-1])
    recorded = {k: v for k, v in event["anchor"].items() if k not in ("exact", "prefix", "suffix")}
    # the preview carries derived quads so the viewer can draw before anything is written; the record does not
    assert recorded == {k: v for k, v in preview.items() if k != "quads"}
    # and a box over the API, rectangles and all
    drawn = handle(q, "comment", {"session": _sid(q), "target": "Bellamy19", "message": "that display", "page": 2, "rects": [[82, 278, 529, 316]], "kind": "note", "author": "A. Author"})
    assert drawn["ok"] and "(box)" in drawn["result"], drawn


@pytest.mark.tex
def test_the_sidecar_carries_the_notes_on_a_page_and_the_reference_counts_them(tmp_path: Path) -> None:
    """Geometry beside the manifest, bodies in it (plan 0.13 item 2, the author's decision of 2026-09-21): a text note's rectangles are derived from the word boxes at build time, a box note's are the record read back, both under `marks` beside the results' `quads`; the page table carries a real rotation; and the reference says how many notes its pages carry, since they are in no key's row."""
    import json as _json

    q = _showcase(tmp_path)
    who = ("--author", "A. Author")
    # the showcase carries reading notes of its own; what is asserted is what these two add
    before = sum(1 for line in (q / "annotations" / "log.jsonl").read_text().splitlines() if '"basis"' in line)
    a = run("comment", "Bellamy19", "why unimodular?", "--page", "2", "--quote", "totally unimodular", "--kind", "question", *who, cwd=q).output.split()[0]
    b = run("comment", "Bellamy19", "this display", "--page", "2", "--box", "82,278,529,316", "--kind", "note", *who, cwd=q).output.split()[0]
    # exit 1 is a content problem, which the showcase carries on purpose (a duplicate id); the build still writes
    assert run("build", cwd=q).exit_code in (0, 1)
    manifest = _json.loads((q / "build" / "manifest.json").read_text())
    ref = manifest["references"]["Bellamy19"]
    assert ref["reading"]["total"] == before + 2 and ref["reading"]["open"] >= 2
    assert manifest["annotations"][a]["target"] == {"key": "doi:10.4171/showcase/19-2", "hash": manifest["annotations"][a]["target"]["hash"], "work": "Bellamy19", "page": 2}
    assert manifest["annotations"][a]["basis"] == "text" and manifest["annotations"][b]["basis"] == "box"
    assert manifest["annotations"][a]["anchored"] and manifest["annotations"][b]["anchored"]
    side = _json.loads((q / "build" / ref["spans"]["path"]).read_text())
    assert a in side["marks"] and len(side["marks"][a]) == 1  # one line
    assert side["marks"][b] == [[82.0, 278.0, 529.0, 316.0]]  # as drawn
    assert "Bellamy19-prop-3.1" in side["quads"]  # the results are still there beside them
    assert side["pages"]["2"]["rotate"] == 0.0 and side["pages"]["2"]["width"] == 612.0
    # and a work with no notes says so, rather than saying nothing
    assert manifest["references"]["Arden24"]["reading"] == {"total": 0, "open": 0}


def test_a_session_is_named_on_the_spot_and_closed_from_the_page(tmp_path: Path) -> None:
    """§16: the author names a session where they are and closes it when done, through the same functions `loom session` calls. Closing takes it out of the active slot; a closed one refuses to close again."""
    from loom.render.api import handle
    from loom.sessions import active, sessions

    q = quilt(tmp_path)
    made = handle(q, "session-new", {"title": "reading Calloway", "author": "A. Author"})
    assert made["ok"] and "(active)" in made["result"], made
    sid = made["result"].split()[0]
    assert active(q) == sid and sessions(q)[sid].title == "reading Calloway"
    shut = handle(q, "session-close", {"session": sid, "author": "A. Author"})
    assert shut["ok"] and sessions(q)[sid].state == "closed" and active(q) is None
    from loom.render.api import ApiError

    with pytest.raises(ApiError, match="is closed"):
        handle(q, "session-close", {"session": sid, "author": "A. Author"})


@pytest.mark.tex
def test_a_locator_by_offsets_lights_the_same_place_a_selection_would(tmp_path: Path) -> None:
    """`span=A-B` in a link names the page's committed text by offsets (plan 0.13 item 6); `locate` maps it to the rectangles a selection of that text would get, so a link and a selection light one place."""
    from loom.render.api import handle

    q = _showcase(tmp_path)
    page_text = (q / "digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt").read_text()
    a = page_text.index("totally unimodular")
    by_span = handle(q, "locate", {"citekey": "Bellamy19", "page": 2, "span": [a, a + len("totally unimodular")]})
    by_text = handle(q, "locate", {"citekey": "Bellamy19", "page": 2, "text": "totally unimodular"})
    assert by_span["ok"] and by_span["anchor"]["quads"] == by_text["anchor"]["quads"]
    assert by_span["anchor"]["start"] == a and by_span["text"] == "totally unimodular"


def test_an_agent_parked_on_session_next_wakes_when_a_message_lands_with_what_changed(tmp_path: Path) -> None:
    """The dispatch round trip against a fake agent (plan 0.13 §11): a real `loom session next --wait` process parked in the background, a post through the mailbox, and the process returning at once with the message and the changed-annotation block -- not when its wait runs out. The repository's first backgrounded-process test, because the thing under test is that a parked process wakes."""
    import json as _json
    import subprocess
    import sys
    import time

    from loom.mailbox import changed_since, post
    from loom.sessions import sessions

    q = quilt(tmp_path)
    sid = run("session", "new", "reading", cwd=q).output.split()[0]
    assert run("comment", "dm-0003", "Is this the balanced case?", "--kind", "question", "--session", sid, "--author", "A. Author", cwd=q).exit_code == 0
    env = {**os.environ, "LOOM_FIXED_TIME": "2026-09-21T12:00:00Z"}
    env.pop("AI_AGENT", None)
    agent = subprocess.Popen(
        [sys.executable, "-m", "loom", "session", "next", "--wait", "20", "--json", "--as", "Referee (Agent)", "--session", sid, "--quilt", str(q)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=q,
    )
    try:
        time.sleep(1.5)  # long enough to be parked; the wait above is what would end it otherwise
        assert agent.poll() is None, "the agent returned before anything landed: " + (agent.stdout.read() if agent.stdout else "")
        t0 = time.monotonic()
        post(q, sid, "Have another look at the balanced case.", "A. Author", kind="message", changed=changed_since(q, sessions(q)[sid]))
        out, err = agent.communicate(timeout=15)
    finally:
        if agent.poll() is None:
            agent.kill()
    woke = time.monotonic() - t0
    assert agent.returncode == 0, err
    assert woke < 5, f"a parked agent took {woke:.1f}s to wake"
    got = _json.loads(out)
    assert "Have another look" in got["text"]
    event = got["events"][-1] if isinstance(got.get("events"), list) else got
    changed = event.get("changed") or []
    assert any("Is this the balanced case" in (c.get("body") or "") for c in changed), got


# ---- What the reading study found (2026-09-21) ---------------------------------------------------------------


def test_a_declared_agent_is_an_agent_however_its_name_is_punctuated() -> None:
    """`is_agent` split a name on whitespace and hyphens, so `(agent)` was a different word from `agent` — and `Referee (Agent)` is the form the orientation asks for and the showcase writes.

    Two things followed, both seen in the study: a parked agent showed in the session picker as `⟨person⟩`, and DR-185's guard let that name run the author's own verbs.
    """
    from loom.cli._common import is_agent

    for name in ("Referee (Agent)", "Claude (AI)", "Referee [Agent]", "Referee Agent", "referee-agent", "AI", "bot"):
        assert is_agent(name), name
    for name in ("A. Author", "Wren Halloway", "Aiden Pearce", "Aimee"):
        assert not is_agent(name), name


@pytest.mark.tex
def test_the_authors_verbs_refuse_a_declared_agent_whatever_shell_it_is_in(tmp_path: Path) -> None:
    """The guard is on the identity, not the door (plan 0.13 §8), so the declared name alone must refuse — the markers are unset here to prove it is the name doing the work. In the study `--author "Referee (Agent)"` ran `refs unreadable` and exited 0."""
    q = _showcase(tmp_path)
    env = {m: None for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CODEX_SANDBOX")}
    for verb in (
        ["refs", "unreadable", "Bellamy19", "--why", "no"],
        ["refs", "verify", "Bellamy19-prop-3.1"],
    ):
        r = CliRunner().invoke(main, [*verb, "--author", "Referee (Agent)", "--quilt", str(q)], env=env)
        assert r.exit_code != 0, (verb, r.output)
        assert "is an agent" in r.output, (verb, r.output)
    # and the author, named, is not refused for the shell they happen to be in
    ok = CliRunner().invoke(
        main,
        ["refs", "unreadable", "Bellamy19", "--why", "a study", "--author", "A. Author", "--quilt", str(q)],
        env={"AI_AGENT": "1"},
    )
    assert ok.exit_code == 0, ok.output


def test_a_browser_write_is_the_person_at_the_browser_not_the_servers_shell(tmp_path: Path) -> None:
    """`_writer` resolved `declared → marker → config`, so with `loom serve` started in an agent's terminal every note written in the author's own browser was recorded `author: "agent"` and shown as such beside the text."""
    import json as _json

    from loom.render.api import handle

    q = quilt(tmp_path)
    (q / "config.toml").write_text(
        (q / "config.toml").read_text() + '\n[author]\nname = "Wren Halloway"\n', encoding="utf-8"
    )
    os.environ["AI_AGENT"] = "1"
    try:
        said = handle(q, "comment", {"session": _sid(q), "target": "dm-0003", "message": "from the browser", "kind": "note"})
        assert said["ok"], said
        written = _json.loads((q / "annotations" / "log.jsonl").read_text().splitlines()[-1])
        assert written["author"] != "agent" and written["kind"] == "human", written
        # an agent posting to the same endpoint still says so, and is believed by its name
        handle(q, "comment", {"session": _sid(q), "target": "dm-0003", "message": "from an agent", "kind": "note", "author": "Referee (Agent)"})
        robot = _json.loads((q / "annotations" / "log.jsonl").read_text().splitlines()[-1])
        assert robot["author"] == "Referee (Agent)" and robot["kind"] == "agent", robot
        assert written["author"] == "Wren Halloway", written
    finally:
        del os.environ["AI_AGENT"]


def test_a_reader_who_is_working_is_not_a_reader_who_was_never_here(tmp_path: Path) -> None:
    """The heartbeat is written only while `session next` is parked, so for the whole time an agent is doing what it was asked it reads as absent. The composer told an author whose agent was mid-task to go and start a watcher."""
    from loom.mailbox import attach, waiting_on
    from loom.sessions import create

    q = quilt(tmp_path)
    sid = create(q, "reading", "A. Author").id
    never = waiting_on(q, sid, "A. Author")
    assert "nobody is attached" in never and f"loom session watch {sid}" in never

    attach(q, sid, "Referee (Agent)", "agent")
    assert waiting_on(q, sid, "A. Author") == ""  # somebody is listening; there is nothing to say

    # the beat goes quiet while they work: still here, not listening this second
    p = q / ".loom" / "sessions" / sid / "attached.json"
    rows = json.loads(p.read_text())
    rows[0]["beat"] = "2020-01-01T00:00:00Z"
    p.write_text(json.dumps(rows))
    busy = waiting_on(q, sid, "A. Author")
    assert "Referee (Agent)" in busy and "probably working" in busy
    assert "session watch" not in busy  # the advice that was wrong


@pytest.mark.tex
def test_refs_locate_names_the_place_and_not_only_the_page(tmp_path: Path) -> None:
    """`refs locate` kept its own mapping, so its anchor had no `basis`, `start` or `end`, and the `open:` line could name only the page — design §6 specifies `?page=3&span=1043-1189`, and following what it printed left the quotation to be found by eye."""
    import json as _json

    from loom.render.serve import write_serve_json

    q = _showcase(tmp_path)
    got = _json.loads(run("refs", "locate", "Bellamy19", "totally unimodular", "--page", "2", "--json", cwd=q).output)
    assert got["basis"] == "text" and got["start"] > 0 and got["end"] > got["start"]
    page_text = (q / "digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt").read_text()
    assert page_text[got["start"] : got["end"]] == "totally unimodular"

    write_serve_json(q, 8791)  # this process is alive, so the link is offered
    said = run("refs", "locate", "Bellamy19", "totally unimodular", "--page", "2", cwd=q).output
    assert f"span={got['start']}-{got['end']}" in said, said
    # a box anchor names its rectangle instead
    drawn = run("refs", "locate", "Bellamy19", "Proposition 3.1", "--page", "2", cwd=q).output
    assert "span=" in drawn or "box=" in drawn, drawn


@pytest.mark.tex
def test_a_change_carries_an_address_its_reader_can_use(tmp_path: Path) -> None:
    """A page note's target is the work's identifier, which is what two quilts agree on and what no `loom refs` command accepts. The study watched an agent take the changed-annotation block, try `loom refs page arXiv:1809.02027v1 4`, be told it was not in the bibliography, and go hunting for the citekey. It travels with the change now."""
    from loom.mailbox import changed_since, render
    from loom.sessions import create, sessions

    q = _showcase(tmp_path)
    sid = create(q, "reading", "A. Author").id
    run("comment", "Bellamy19", "why unimodular?", "--page", "2", "--quote", "totally unimodular", "--kind", "question", "--session", sid, "--author", "A. Author", cwd=q)
    run("comment", "sh-0003", "and one on a key, which has no work", "--kind", "note", "--session", sid, "--author", "A. Author", cwd=q)

    changed = changed_since(q, sessions(q)[sid])
    page_note = next(c for c in changed if c["page"])
    assert page_note["work"] == "Bellamy19" and page_note["page"] == 2
    assert page_note["target"].startswith("doi:")  # the identifier is still what was recorded
    on_key = next(c for c in changed if not c["page"])
    assert on_key["work"] is None and on_key["target"] == "sh-0003"
    # and what a parked agent reads names the paper and the page, not an address it must decode
    said = render([type("E", (), {"who": "A. Author", "when": "now", "kind": "message", "body": "look", "changed": changed})()])
    assert "Bellamy19 p.2" in said, said
