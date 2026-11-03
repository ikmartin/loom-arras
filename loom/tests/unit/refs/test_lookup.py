"""Looking a pasted identifier up for a work added by hand, against services faked here: what is found, what names nothing, what could not be asked, and what loom does not look up."""

from __future__ import annotations

import json
from typing import Any

import pytest

from loom.refs.lookup import key_for, look_up
from loom.refs.resolve import NothingFound, ResolveRefused
from loom.scan.bib import BibEntry

LIBRARY = {
    "Man12": BibEntry(
        "Man12",
        "article",
        {
            "author": "Manolache, Cristina",
            "title": "Virtual pull-backs",
            "year": "2012",
            "eprint": "0805.2065v2",
            "archiveprefix": "arXiv",
        },
    ),
    "Kre99": BibEntry(
        "Kre99", "article", {"author": "Kresch, Andrew", "title": "Cycle groups for Artin stacks", "year": "1999"}
    ),
}

CSL = {
    "type": "article-journal",
    "title": "Widget categories and their duals",
    "author": [{"family": "Ostrander", "given": "D."}, {"family": "Vale", "given": "E."}],
    "issued": {"date-parts": [[2018, 3]]},
    "container-title": "J. Widget Theory",
    "DOI": "10.5555/widget.2018.031",
}
ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/0805.2065v2</id>
    <published>2008-05-14T00:00:00Z</published>
    <title>Virtual
      pull-backs</title>
    <author><name>Cristina Manolache</name></author>
    <arxiv:doi>10.1090/S1056-3911-2011-00606-1</arxiv:doi>
  </entry>
</feed>"""
ATOM_ERROR = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#incorrect_id_format</id><title>Error</title></entry></feed>"""


def fake(answers: dict[str, Any]) -> Any:
    """An `http` answering each URL whose start it matches with bytes, a JSON-able value, or an exception to raise."""
    asked: list[tuple[str, dict[str, str]]] = []

    def http(url: str, headers: dict[str, str]) -> bytes:
        asked.append((url, headers))
        for start, answer in answers.items():
            if url.startswith(start):
                if isinstance(answer, Exception):
                    raise answer
                return answer if isinstance(answer, bytes) else json.dumps(answer).encode()
        raise AssertionError(f"unexpected request {url}")

    http.asked = asked  # type: ignore[attr-defined]
    return http


def test_a_doi_is_asked_of_doi_org_and_found() -> None:
    http = fake({"https://doi.org/10.5555/widget.2018.031": CSL})
    got = look_up("https://doi.org/10.5555/widget.2018.031", LIBRARY, online=True, http=http)
    assert got.state == "found" and got.kind == "doi"
    assert got.entry["title"] == "Widget categories and their duals" and got.entry["year"] == "2018"
    assert got.entry["author"] == "Ostrander, D. and Vale, E." and got.entry["journal"] == "J. Widget Theory"
    assert got.key == "Ost18" and got.digest == "lookup" and got.duplicates == []
    # content negotiation, so every registry's DOIs answer
    assert http.asked[0][1]["Accept"] == "application/vnd.citationstyles.csl+json"


def test_a_doi_that_names_nothing_did_not_resolve() -> None:
    http = fake({"https://doi.org/": NothingFound("https://doi.org/10.9999/x")})
    got = look_up("10.9999/not.a.real.doi", LIBRARY, online=True, http=http)
    assert got.state == "missing" and "did not resolve" in got.message and "10.9999/not.a.real.doi" in got.message


def test_an_arxiv_id_is_found_digestible_and_a_duplicate_of_its_other_version() -> None:
    got = look_up("arXiv:0805.2065", LIBRARY, online=True, http=fake({"https://export.arxiv.org/api/query": ATOM}))
    assert got.state == "found" and got.digest == "source"
    assert got.entry["title"] == "Virtual pull-backs" and got.entry["author"] == "Manolache, Cristina"
    assert got.entry["eprint"] == "0805.2065" and got.entry["year"] == "2008"
    # the library holds v2 of the same preprint
    assert got.duplicates == ["Man12"] and got.key == "Man08"


def test_an_arxiv_id_arxiv_does_not_have_is_missing() -> None:
    got = look_up("2499.99999", LIBRARY, online=True, http=fake({"https://export.arxiv.org/api/query": ATOM_ERROR}))
    assert got.state == "missing" and "arXiv has no paper" in got.message


def test_a_service_that_cannot_be_reached_says_why() -> None:
    http = fake(
        {"https://doi.org/": ResolveRefused("https://doi.org/10.5555/x: [Errno 8] nodename nor servname provided")}
    )
    got = look_up("10.5555/x", LIBRARY, online=True, http=http)
    assert got.state == "unreachable" and "nodename" in got.message


def test_without_the_network_an_identifier_is_not_looked_up_and_an_entry_still_is() -> None:
    def never(url: str, headers: dict[str, str]) -> bytes:
        raise AssertionError("asked the network offline")

    assert look_up("10.5555/x", LIBRARY, online=False, http=never).state == "offline"
    got = look_up(
        "@article{Kre99,\n author = {Kresch, A.},\n title = {Cycle groups for {A}rtin stacks},\n year = {1999},\n loom-added = {someone}\n}",
        LIBRARY,
        online=False,
        http=never,
    )
    # the entry is what it says; its own key is taken, so it gets a letter; loom's fields are never a paste's
    assert got.state == "found" and got.key == "Kre99A" and "loom-added" not in got.entry
    assert got.duplicates == ["Kre99"]


@pytest.mark.parametrize(
    ("text", "kind"), [("ISBN 978-0-387-98549-7", "isbn"), ("MR1667326", "mr"), ("widgets, somewhere", "unknown")]
)
def test_what_loom_does_not_look_up_asks_for_more(text: str, kind: str) -> None:
    got = look_up(text, LIBRARY, online=True, http=fake({}))
    assert got.state == "cannot" and got.kind == kind and "DOI" in got.message


def test_a_key_is_the_surname_and_year_and_never_one_taken() -> None:
    assert key_for({"author": "Ångström, A. and Euler, L.", "year": "1999"}, set()) == "Ang99"
    assert key_for({"author": "Kresch, Andrew", "year": "1999"}, {"Kre99"}) == "Kre99A"
    assert key_for({"author": "", "year": ""}, set()) == "Wor"
    assert key_for({}, {"Hal21"}, wanted="Hal21") == "Hal21A"
