"""Plan 0.5: the global identity of a cited work, and the migration into the current reference layout."""

from __future__ import annotations

from loom.refs.identity import WorkId, declared, identify, parse, primary, sanitise, synthetic
from loom.scan.bib import parse_bib

ENTRY = """@article{Man12,
  author = {Manolache, Cristina},
  title = {Virtual pull-backs},
  journal = {J. Algebraic Geom.},
  year = {2012},
  doi = {10.1090/S1056-3911-2011-00606-1},
}
"""
PREPRINT = """@article{Ar22,
  author = {Aranha, Dhyan and Khan, Adeel},
  title = {Virtual localization revisited},
  year = {2022},
  doi = {10.48550/arXiv.2207.01652},
  eprint = {2207.01652},
}
"""
BOOK = """@book{Sil99,
  author = {Silverman, Joseph H.},
  title = {Advanced Topics in the Arithmetic of Elliptic Curves},
  year = {1999},
}
"""


def _one(text: str):  # type: ignore[no-untyped-def]
    return next(iter(parse_bib(text).values()))


def test_resolution_order_and_paths() -> None:
    ids = identify(_one(ENTRY))
    assert [str(w) for w in ids] == ["doi:10.1090/S1056-3911-2011-00606-1"]
    assert ids[0].published and not ids[0].preprint
    assert ids[0].path == "doi/10.1090_S1056-3911-2011-00606-1"  # a slash would make a directory of its own


def test_arxiv_doi_is_a_preprint_not_a_publication() -> None:
    """arXiv mints DOIs under 10.48550, so such a DOI names the preprint. Treating it as published would file one artifact under two names and tell loom:unverified-locators the work is in print when it is not."""
    ids = identify(_one(PREPRINT))
    assert [str(w) for w in ids] == ["arXiv:2207.01652"]
    assert ids[0].preprint and not ids[0].published


def test_synthetic_id_is_deterministic_across_machines() -> None:
    """The property that lets two corpora merge on a book with no DOI: the same work, normalised independently, yields one id."""
    a = synthetic(_one(BOOK))
    spaced = BOOK.replace("Joseph H.", "  Joseph   H. ").replace("Advanced", "Advanced")
    b = synthetic(_one(spaced))
    assert a == b and a.scheme == "work" and len(a.value) == 8
    assert synthetic(_one(BOOK.replace("1999", "2000"))) != a
    assert not declared(_one(BOOK)) and identify(_one(BOOK)) == [a]


def test_identifier_round_trips_through_its_written_form() -> None:
    for w in (WorkId("arxiv", "0805.2065v2"), WorkId("doi", "10.1090/X"), WorkId("work", "ab12cd34")):
        assert parse(str(w)) == w
    assert parse("not an identifier") is None and parse("nope:1") is None


def test_sanitise_is_path_safe() -> None:
    assert "/" not in sanitise("10.1090/S1056-3911-2011-00606-1")
    assert sanitise("math/0605234") == "math_0605234"


def test_primary_is_none_without_an_entry() -> None:
    assert primary(None) is None and identify(None) == []
