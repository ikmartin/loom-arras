"""Plan 0.5: the global identity of a cited work, and the migration into the current reference layout."""

from __future__ import annotations

from pathlib import Path

from loom.refs.identity import WorkId, declared, identify, parse, primary, sanitise, synthetic
from loom.refs.migrate import migrate
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


def test_migrate_moves_digests_and_splits_provenance(tmp_path: Path) -> None:
    q = tmp_path / "q"
    (q / "refs" / "src" / "Ar22").mkdir(parents=True)
    (q / "refs" / "pdf").mkdir(parents=True)
    (q / "refs.bib").write_text(ENTRY + PREPRINT, encoding="utf-8")
    (q / "refs" / "src" / "Ar22" / "main.tex").write_text("x", encoding="utf-8")
    (q / "refs" / "pdf" / "Ar22.pdf").write_bytes(b"%PDF-1.4\n")
    (q / "refs" / "Man12.tex").write_text(
        "% !LOOM digest: Man12\n% !LOOM source: doi:10.1090/S1056-3911-2011-00606-1\n% !LOOM method: extract\n",
        encoding="utf-8",
    )
    (q / "refs" / "Ar22.tex").write_text(
        "% !LOOM digest: Ar22\n% !LOOM source: arXiv:2207.01652\n% !LOOM method: extract\n", encoding="utf-8"
    )

    rep = migrate(q)
    assert rep.done and not (q / "refs" / "Man12.tex").exists()

    # a published identifier is not something statements can be extracted from, so the migration records only what it
    # knows and leaves the artifact for the author to state; loom:unverified-locators asks for it
    man = (q / "digests" / "Man12.tex").read_text()
    assert "% !LOOM published-as: doi:10.1090/S1056-3911-2011-00606-1" in man
    assert "extracted-from" not in man and rep.unknown == ["Man12"]

    # a preprint identifier is one, so that split is certain
    ar = (q / "digests" / "Ar22.tex").read_text()
    assert "% !LOOM extracted-from: arXiv:2207.01652" in ar

    # every digest gains a declared prefix, so its ids survive a citekey rename
    assert "% !LOOM prefix: Man12" in man and "% !LOOM prefix: Ar22" in ar

    # fetched artifacts are filed under the work's identifier, not the citekey
    assert (q / "refs" / "arxiv" / "2207.01652" / "src" / "main.tex").is_file()
    assert (q / "refs" / "arxiv" / "2207.01652" / "paper.pdf").is_file()
    assert not (q / "refs" / "src").exists() and not (q / "refs" / "pdf").exists()

    assert not migrate(q).done  # idempotent


def test_migrate_drops_retired_config_and_keeps_the_comments(tmp_path: Path) -> None:
    """`[ai] runner` (WQ-15) and the whole `[crawl]` table (DR-144) go; everything the author wrote around them stays."""
    q = tmp_path / "q"
    q.mkdir(parents=True)
    (q / "config.toml").write_text(
        "[quilt]\n"
        'name = "Q"                  # the project\n'
        'prefix = "q"\n'
        "\n"
        "[refs]\n"
        "fetch = false               # may loom fetch from arXiv\n"
        "\n"
        "[crawl]\n"
        "# the library this paper draws on\n"
        "depth = 3\n"
        'subjects = [\n  "14N",\n  "14D",\n]\n'
        "cap = 50\n"
        "\n"
        "[ai]\n"
        'agent = "claude"            # command loom ai start launches\n'
        'runner = "make"\n',
        encoding="utf-8",
    )
    rep = migrate(q)
    assert rep.retired == ["[ai] runner", "[crawl]"]

    out = (q / "config.toml").read_text(encoding="utf-8")
    assert "[crawl]" not in out and "subjects" not in out and "14N" not in out and "runner" not in out
    # the tables around it, their values and their trailing comments are untouched
    assert "# may loom fetch from arXiv" in out and "# command loom ai start launches" in out
    assert '[ai]\nagent = "claude"' in out and "[refs]" in out and "[quilt]" in out
    assert "\n\n\n" not in out

    assert not migrate(q).done  # idempotent


def test_primary_is_none_without_an_entry() -> None:
    assert primary(None) is None and identify(None) == []
