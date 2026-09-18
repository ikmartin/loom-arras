"""Identity candidates (book 8.4.2): scoring, the two services' answers as recorded, the order they are asked in, the cache, the consent gate, and what lint and the manifest say. Nothing here touches the network."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.refs import resolve as R
from loom.refs.identity import identify
from loom.scan.bib import BibEntry

RESPONSES = json.loads((Path(__file__).parent / "resolve_responses.json").read_text(encoding="utf-8"))

EDIDIN = BibEntry(
    "edidin-graham_LocalizationEquivariantIntersection1998",
    "article",
    {
        "title": "Localization in Equivariant Intersection Theory and the {{Bott}} Residue Formula",
        "author": "Edidin, Dan and Graham, William",
        "year": "1998",
    },
)
SILVERMAN = BibEntry(
    "silverman_AdvancedTopicsArithmetic1999",
    "book",
    {"title": "Advanced Topics in the Arithmetic of Elliptic Curves", "author": "Silverman, Joseph H.", "year": "1999"},
)


class Recorded:
    """An injected transport answering from the recorded responses, counting what it was asked."""

    def __init__(self, zbmath: str | None, crossref: str | None = None, fail: set[str] | None = None) -> None:
        self.answers = {"zbmath": zbmath, "crossref": crossref}
        self.fail = fail or set()
        self.urls: list[str] = []

    def __call__(self, url: str, headers: dict[str, str]) -> bytes:
        self.urls.append(url)
        service = "zbmath" if "zbmath" in url else "crossref"
        if service in self.fail:
            raise R.ResolveRefused(f"{service}: HTTP 503")
        name = self.answers[service]
        data: dict[str, Any] = (
            RESPONSES[name] if name else ({"result": []} if service == "zbmath" else {"message": {"items": []}})
        )
        return json.dumps(data).encode("utf-8")


@pytest.fixture(autouse=True)
def no_spacing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(R, "SPACING", 0.0)


def test_a_query_is_the_entry_without_its_markup() -> None:
    q = R.query_for(EDIDIN)
    assert q.title == "Localization in Equivariant Intersection Theory and the Bott Residue Formula"
    assert q.surnames == ("Edidin", "Graham") and q.year == "1998"
    assert R.query_for(
        BibEntry("x", "misc", {"title": "Sch\\'emas en groupes", "author": "Demazure, M. and others"})
    ).surnames == ("Demazure",)


def test_scoring_is_by_title_then_author_then_year() -> None:
    q = R.query_for(EDIDIN)
    exact = R.score(
        q, "Localization in equivariant intersection theory and the Bott residue formula", ["Edidin, Dan"], "1998"
    )
    assert exact == 1.0
    # a record that drops the subtitle still matches strongly
    assert R.score(q, "Localization in equivariant intersection theory", ["Dan Edidin"], "1998") >= R.STRONG
    # the right title alone is only possible: a different book can share a title
    assert (
        R.POSSIBLE
        <= R.score(q, "Localization in equivariant intersection theory and the Bott residue formula", [], "")
        < R.STRONG
    )
    assert R.score(q, "Equivariant intersection theory", ["Edidin, Dan"], "1998") < R.POSSIBLE


def test_a_formatted_reference_is_scored_by_what_it_contains() -> None:
    text = "A. Arabia, Cycles de Schubert et cohomologie equivariante de K/T, Invent. Math. 85 (1986), 39-52."
    q = R.Query(text, (), "1986", text)
    assert R.score(q, "Cycles de Schubert et cohomologie équivariante de K/T", ["Arabia, Alberto"], "1986") == 1.0
    assert R.score(q, "Equivariant cohomology", ["Brion, M."], "1986") < R.POSSIBLE


def test_zbmath_answers_with_a_doi_and_the_preprint_it_knows() -> None:
    http = Recorded("zbmath_edidin_graham")
    found = R.Resolver(http=http).candidates(R.query_for(EDIDIN))
    assert [c.id for c in found] == ["doi:10.1353/ajm.1998.0020"]
    assert found[0].also == [
        "arxiv:alg-geom/9508001",
        "zbl:0980.14004",
    ]  # the fetchable preprint before the review number
    assert found[0].strength == "strong" and found[0].source == "zbMATH Open"
    # a strong match with a DOI needs nothing from Crossref
    assert len(http.urls) == 1 and "ti%3ALocalization" in http.urls[0]


def test_crossref_is_asked_for_a_doi_when_zbmath_has_none_and_picks_the_book_not_its_chapters() -> None:
    http = Recorded("zbmath_silverman", "crossref_silverman")
    found = R.Resolver(http=http).candidates(R.query_for(SILVERMAN))
    ids = [c.id for c in found]
    assert ids == [
        "doi:10.1007/978-1-4612-0851-8"
    ]  # the book; its chapters rank above it at Crossref and are discarded here
    assert found[0].also == ["zbl:0911.14015"]  # zbMATH's record of the same book, pooled into one candidate
    assert found[0].source == "zbMATH Open, Crossref"
    assert len(http.urls) == 2


def test_a_404_is_no_match_rather_than_a_failure() -> None:
    def http(url: str, headers: dict[str, str]) -> bytes:
        if "zbmath" in url:
            raise R.NothingFound(url)
        return json.dumps({"message": {"items": []}}).encode("utf-8")

    assert R.Resolver(http=http).candidates(R.Query("Stacks Project", ("The Stacks project authors",))) == []


def test_biblatex_dates_count_as_years() -> None:
    assert R.query_for(BibEntry("x", "article", {"title": "T", "date": "1998-06"})).year == "1998"


def test_one_service_failing_is_not_a_failed_lookup_but_both_are() -> None:
    found = R.Resolver(http=Recorded("zbmath_silverman", "crossref_silverman", fail={"zbmath"})).candidates(
        R.query_for(SILVERMAN)
    )
    assert found and found[0].source == "Crossref"
    with pytest.raises(R.ResolveRefused):
        R.Resolver(http=Recorded(None, None, fail={"zbmath", "crossref"})).candidates(R.query_for(SILVERMAN))


def test_an_answer_is_cached_and_not_asked_for_twice(tmp_path: Path) -> None:
    http = Recorded("zbmath_edidin_graham")
    R.Resolver(cache=tmp_path, http=http).candidates(R.query_for(EDIDIN))
    again = R.Resolver(cache=tmp_path, http=http)
    again.candidates(R.query_for(EDIDIN))
    assert len(http.urls) == 1 and again.requests == 0
    R.Resolver(cache=tmp_path, http=http, refresh=True).candidates(R.query_for(EDIDIN))
    assert len(http.urls) == 2


def test_contact_goes_to_crossref_only_when_set() -> None:
    http = Recorded("zbmath_silverman", "crossref_silverman")
    R.Resolver(http=http, contact="author@example.org").candidates(R.query_for(SILVERMAN))
    assert "mailto=author%40example.org" in http.urls[1] and "mailto" not in http.urls[0]
    http2 = Recorded("zbmath_silverman", "crossref_silverman")
    R.Resolver(http=http2).candidates(R.query_for(SILVERMAN))
    assert all("mailto" not in u for u in http2.urls)


def test_candidates_are_kept_with_the_entry_they_answer_and_forgotten_when_it_changes(tmp_path: Path) -> None:
    found = R.Resolver(http=Recorded("zbmath_edidin_graham")).candidates(R.query_for(EDIDIN))
    path = R.save(tmp_path, EDIDIN, found)
    assert path == tmp_path / "refs" / identify(EDIDIN)[0].path / "resolved.json"
    assert [c.id for c in R.load(tmp_path, EDIDIN)] == ["doi:10.1353/ajm.1998.0020"]
    edited = BibEntry(EDIDIN.key, EDIDIN.type, {**EDIDIN.fields, "year": "1999"})
    assert R.load(tmp_path, edited) == []
    assert R.as_workid(found[0]).provenance == "resolved"


# --- the command, lint and the manifest ---------------------------------------------------------------


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def demo(tmp_path: Path) -> Path:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    with (q / "refs.bib").open("a") as fh:
        fh.write(
            "\n@article{Edi98,\n  title = {Localization in Equivariant Intersection Theory and the Bott Residue Formula},\n  author = {Edidin, Dan and Graham, William},\n  year = {1998},\n}\n"
        )
    node = q / "nodes" / "dm-0001.tex"
    node.write_text(node.read_text().replace("\\end{definition}", "See \\cite{Edi98}.\n\\end{definition}", 1))
    return q


def test_resolving_is_refused_until_the_author_allows_it(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("refs", "resolve", cwd=q)
    assert r.exit_code == 2 and "resolve = true" in r.output
    assert not list((q / "refs").rglob("resolved.json")) if (q / "refs").exists() else True


def test_the_command_proposes_lint_names_the_proposal_and_the_manifest_carries_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    q = demo(tmp_path)
    cfg = q / "config.toml"
    cfg.write_text(cfg.read_text().replace("fetch = false", "fetch = false\nresolve = true"))
    before = (q / "refs.bib").read_text()
    lint = run("lint", cwd=q)
    assert "Edi98 states no identifier" in lint.output and "loom refs resolve" in lint.output

    monkeypatch.setattr(R, "http_get", Recorded("zbmath_edidin_graham"))
    r = run("refs", "resolve", cwd=q)
    assert r.exit_code == 0, r.output
    assert "Edi98: doi:10.1353/ajm.1998.0020" in r.output and "strong" in r.output
    assert (q / "refs.bib").read_text() == before  # the bibliography is the author's, and is never written

    r = run("refs", "resolve", "--json", cwd=q)
    data = json.loads(r.output[r.output.index("{") :])
    assert data["lookups"] == 0  # answered from the cache
    assert data["works"]["Edi98"]["candidates"][0]["strength"] == "strong"

    lint = run("lint", cwd=q)
    assert "a lookup found doi:10.1353/ajm.1998.0020 (strong match, zbMATH Open)" in lint.output
    assert "add doi = {10.1353/ajm.1998.0020}" in lint.output

    assert run("build", cwd=q).exit_code == 0
    ref = json.loads((q / "build" / "manifest.json").read_text())["references"]["Edi98"]
    assert ref["candidates"][0] == {
        "id": "doi:10.1353/ajm.1998.0020",
        "source": "zbMATH Open",
        "confidence": 1.0,
        "strength": "strong",
        "title": "Localization in equivariant intersection theory and the Bott residue formula",
    }
    assert ref["work"].startswith("work:")  # a candidate is never the work's identity
