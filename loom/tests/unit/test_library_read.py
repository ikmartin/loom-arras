"""The library's report and its reading commands (plan 0.18.5): advice that names commands which exist, a work with no PDF never told to map, and the ranked, case-insensitive search (WQ-41)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import click

from loom.cli import main
from tests.helpers import json_of, ok, refused
from tests.output_cases.library_read import cited_all, proposed, related
from tests.unit._quilts import demo, mapped, propose, work_home

#: A command named on a `next:` or `fix:` line: `loom` and the lowercase words after it.
NAMED = re.compile(r"\bloom((?: [a-z][a-z-]*)*)")


def advice(text: str, doc: dict) -> list[str]:
    """Every `next:` and `fix:` line of a report, from its text and from its JSON groups."""
    lines = [ln.split(":", 1)[1] for ln in text.splitlines() if ln.strip().startswith(("next:", "fix:", "… and"))]
    for g in doc.get("groups", []):
        lines += [g.get("next", "")] + [f for i in g["items"] for f in i.get("fixes", [])]
    return [ln for ln in lines if ln]


def resolves(words: list[str]) -> bool:
    """Whether `loom WORDS…` is a command: each word a subcommand of the group before it, until a command that is not a group."""
    cmd: click.Command = main
    if not words:
        return False
    for w in words:
        if not isinstance(cmd, click.Group):
            return True
        if w not in cmd.commands:
            return False
        cmd = cmd.commands[w]
    return not isinstance(cmd, click.Group) or bool(cmd.invoke_without_command)


def test_every_command_the_library_advises_exists(tmp_path: Path) -> None:
    """A `next:` line naming a command that is not there sends its reader to an error; each is resolved against the command tree."""
    q = demo(tmp_path)
    cited_all(q)
    proposed(q)
    related(q)
    named: set[str] = set()
    for args in (("library",), ("library", "Calloway14"), ("library", "Har77"), ("library", "Man12")):
        text = ok(*args, cwd=q).output
        for line in advice(text, json_of(*args, "--json", cwd=q)):
            named |= {m.group(1).strip() for m in NAMED.finditer(line)}
    for args in (
        ("library", "search", "involution"),
        ("library", "search", "nothing-like-this"),
        ("library", "why", "Calloway14-rem-9.1"),
    ):
        text = ok(*args, cwd=q).output
        for line in advice(text, json_of(*args, "--json", cwd=q)):
            named |= {m.group(1).strip() for m in NAMED.finditer(line)}
    assert {"library add", "library update", "library review", "library ignore"} <= named, named
    assert sorted(n for n in named if not resolves(n.split())) == [], "advice naming no command"


def test_a_work_with_no_pdf_is_never_told_to_map(tmp_path: Path) -> None:
    """Study D1–D5: a work with nothing to map was told to map it. A PDF with no page text is told to map; a work with no PDF is told to get one."""
    q = demo(tmp_path)
    cited_all(q)
    said = [ok("library", cwd=q).output, ok("library", "Har77", cwd=q).output, ok("library", "Man12", cwd=q).output]
    said.append(refused("library", "read", "Man12", "1", cwd=q, code=1, match="has no PDF").output)
    said.append(refused("library", "locate", "Man12", "x", "--page", "1", cwd=q, code=1, match="has no PDF").output)
    said.append(
        refused(
            "library", "propose", "Man12", "--local", "thm-1", "--level", "1", "--page", "1",
            "--source-text", "x", "--statement", "x", cwd=q, code=1, match="has no PDF",
        ).output
    )  # fmt: skip
    assert [s for s in said if "map" in s.replace("mapped", "")] == [], said
    # a PDF whose page text is gone is told to map it, and nothing else
    (work_home(q, "Calloway14") / "sections.json").unlink()
    r = refused("library", "read", "Calloway14", "1", cwd=q, code=1, match="--only map")
    assert "library add" not in r.output


def test_search_ignores_case_and_needs_every_word(tmp_path: Path) -> None:
    """`refs grep` kept case, so "fixed locus" missed "Fixed locus"; and a search is for every word given, not the phrase as typed."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y")
    assert [h["id"] for h in json_of("library", "search", "MORPHISM dm-type", "--json", cwd=q)["hits"]] == [
        f"{ck}-thm-1.1"
    ]
    assert json_of("library", "search", "morphism gerbe", "--json", cwd=q)["hits"] == []
    pages = json_of("library", "search", "PERFECT dm-type", "--pages", "--work", ck, "--json", cwd=q)["hits"]
    assert [(h["work"], h["page"]) for h in pages] == [(ck, 1)]


def test_a_result_is_ranked_by_where_its_words_fall_its_level_and_its_citations() -> None:
    """WQ-41: a word in the locator, local name or title counts three, one in the body one; a main result two more, and each citation of it one more."""
    from loom.refs.search import score_result

    def score(head: str, body: str, level: int = 3, citations: int = 0) -> int | None:
        return score_result(["widget"], head, body, level=level, citations=citations)

    assert score("Widget Lemma", "") == 3
    assert score("Lemma 2", "every WIDGET") == 1
    assert score("Widget Lemma", "every widget") == 4
    assert score("Lemma 2", "every widget", level=1) == 3
    assert score("Lemma 2", "every widget", citations=2) == 3
    assert score("Lemma 2", "a gadget") is None
    assert score_result(["widget", "gadget"], "Widget", "a widget", level=3, citations=0) is None, (
        "every word must match"
    )


def test_the_search_puts_a_cited_result_first_and_breaks_ties_by_id(tmp_path: Path) -> None:
    """The demo's documents cite Proposition 3.2 of Calloway14; every other result scores the same and follows in id order, each with its id in full."""
    q = demo(tmp_path)
    got = json_of("library", "search", "involution", "--json", cwd=q)["hits"]
    assert [h["id"] for h in got] == [
        "Calloway14-prop-3.2",
        "Calloway14-def-3.1",
        "Calloway14-prop-3.3",
        "Calloway14-setup",
        "Calloway14-thm-3.4",
    ]
    assert got[0]["citations"] == 1 and got[0]["score"] == got[1]["score"] + 1
    said = ok("library", "search", "involution", "--limit", "1", cwd=q).stdout
    assert said.startswith("5 results in 1 work, showing 1;") and "Calloway14-prop-3.2" in said.split()
    assert "loom library search involution --limit 5" in said


def test_why_tells_a_citation_suggestion_apart_from_a_result(tmp_path: Path) -> None:
    """An ID is a result's or a citation suggestion's; `why` says where either came from."""
    from loom.scan.quilt import save_author

    save_author("A. Author")
    q = demo(tmp_path)
    sid = ok("session", "new", "--name", "r", "--as", "A. Author", cwd=q).stdout.split()[0]
    made = ok(
        "annotate", "dm-0002", "Kreck 1999 proves this.", "--quote", "Every orbit", "--kind", "citation",
        "--payload", "K. Kreck, Surgery and duality (1999).", "--session", sid, cwd=q, env={"AI_AGENT": "1"},
    )  # fmt: skip
    ann = made.output.split()[0]
    doc = json_of("library", "why", ann, "--json", cwd=q)
    assert doc["verdict"] == f"{ann}, a citation suggestion, open" and doc["annotation"]["payload"].startswith(
        "K. Kreck"
    )
    assert "loom library review" in ok("library", "why", ann, cwd=q).output
    note = ok("annotate", "dm-0002", "Not a citation.", "--quote", "Every orbit", "--session", sid, cwd=q)
    refused("library", "why", note.output.split()[0], cwd=q, code=1, match="not a citation suggestion")


def test_a_relation_dry_run_writes_nothing_and_says_what_it_would(tmp_path: Path) -> None:
    q = demo(tmp_path)
    args = ("library", "relate", "Calloway14-prop-3.2", "Calloway14-prop-3.3", "--kind", "depends-on", "--why", "w")
    r = json_of(*args, "--as", "Tester", "--dry-run", "--json", cwd=q)
    assert r["dry_run"] is True and r["link"]["id"] == "link-0001" and r["link"]["by"] == "Tester"
    assert not (q / "digests" / "links.jsonl").exists()
    ok(*args, "--as", "Tester", cwd=q)
    refused(*args, "--as", "Tester", "--dry-run", cwd=q, code=2, match="link-0001 already says that")
    refused(*args, "--undo", "link-0001", cwd=q, code=2, match="not both")
    lines = (q / "digests" / "links.jsonl").read_text().splitlines()
    assert [json.loads(ln)["id"] for ln in lines] == ["link-0001"]


def test_search_reads_a_hyphenated_word_whole_and_never_the_citation_apparatus(tmp_path: Path) -> None:
    """Manolache writes "pull-back", which a search for "pullback" missed, and so with any word a paper hyphenates; and every result's own `\\cite` title holds its citekey, which matched every result of a work whose citekey held a searched word."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Then $f$ has a push-forward.")
    propose(q, ck, "thm-1.2", 1, "Let $f$ be a DM-type morphism", "Then $f$ is proper.")
    hits = json_of("library", "search", "pushforward", "--json", cwd=q)["hits"]
    assert [h["id"] for h in hits] == [f"{ck}-thm-1.1"]
    assert "pushforward" in hits[0]["snippet"]
    from loom.cli.library.read import _prose

    tex = f"\\begin{{theorem}}[{{\\cite[Theorem 1.1, p.~2]{{{ck}}}}}]\\label{{x-thm-1.1}}\\uses{{x-def-1}}Every widget.\\end{{theorem}}"
    assert ck not in _prose(tex) and "Every widget." in _prose(tex)


def test_a_quilt_already_online_is_never_told_to_pass_online(tmp_path: Path) -> None:
    """A work with an identifier and no document waits on the network; where `[library] online = true` it waits only on the next update, which needs nothing from the person."""
    q = demo(tmp_path)
    cited_all(q)
    offline = json_of("library", "--json", cwd=q)
    told = ok("library", "Man12", cwd=q).output
    assert "--online" in told
    config = q / "config.toml"
    text = config.read_text()
    assert "online = false" in text
    config.write_text(re.sub(r"online = false", "online = true", text, count=1))
    online = json_of("library", "--json", cwd=q)
    told = ok("library", "Man12", cwd=q).output
    assert "--online" not in told and "loom library update" in told
    assert online["need_you"] == offline["need_you"] - 1
