"""The reference crawl (book 8.13): formatted bibliographies, subjects, records, the three services as recorded, the plan on a synthetic citation graph, the capped fetch, and the commands. Nothing here touches the network."""

from __future__ import annotations

import gzip
import importlib
import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.refs.crawl import bibitem as B
from loom.refs.crawl import msc as M
from loom.refs.crawl import net
from loom.refs.crawl.arxiv import Arxiv
from loom.refs.crawl.fetch import fetch
from loom.refs.crawl.openalex import OaRecord, OpenAlex
from loom.refs.crawl.plan import (
    Clients,
    Planner,
    PlanRefused,
    Settings,
    fingerprint,
    load_plan,
    save_plan,
    summary,
    survey_summary,
)
from loom.refs.crawl.work import Reference, Work, load, load_all, norm, ranked, save
from loom.refs.crawl.zbmath import Zbmath, ZbRecord
from loom.refs.resolve import Candidate, Query
from loom.scan.bib import BibEntry
from loom.scan.quilt import QuiltConfig
from loom.scan.scan import find_bib_files

RECORDED = json.loads((Path(__file__).parent / "crawl_responses.json").read_text(encoding="utf-8"))["responses"]


# --- formatted bibliographies -------------------------------------------------------------------------

SOURCE = r"""
\begin{thebibliography}{99}
\bibitem[GP]{GraberPandharipande} T.~Graber, R.~Pandharipande, \textit{Localization of virtual classes}. Invent.~Math.~{\bf{135}} (1999), no.~2, 487--518.
\bibitem{AHR21} {\sc Jarod Alper, Jack Hall, David Rydh}, {\it The \'etale local structure of algebraic stacks}, \url{https://arxiv.org/abs/1912.06162}, 2021.
%\bibitem{Gone} {\sc Nobody}, {\it Commented out}, 2020.
\bibitem{Joyce} D.~Joyce, \textit{Enumerative invariants}. \arXiv{2111.04694} (2021).
\bibitem{Doi} A.~Author, \textit{A title}, J. Something 1 (2000), doi:10.1000/xyz.1.
\end{thebibliography}
Text after the bibliography.
"""


def test_bibitems_are_read_wherever_they_are_and_commented_ones_are_not() -> None:
    items = B.entries(SOURCE)
    assert [i.key for i in items] == ["GraberPandharipande", "AHR21", "Joyce", "Doi"]
    assert items[1].arxiv == "1912.06162" and items[2].arxiv == "2111.04694" and items[3].doi == "10.1000/xyz.1"
    assert items[0].arxiv is None and items[0].doi is None
    assert "Text after" not in items[-1].text


def test_a_formatted_entry_becomes_a_lookup_with_title_surnames_and_the_right_year() -> None:
    gp, ahr = B.entries(SOURCE)[:2]
    q = B.query(gp)
    assert (q.title, q.surnames, q.year) == ("Localization of virtual classes", ("Graber", "Pandharipande"), "1999")
    q = B.query(ahr)
    assert q.surnames == ("Alper", "Hall", "Rydh")  # first names first, surnames still found
    assert q.year == "2021"  # not 1912, which is the arXiv number


def test_bibitems_come_from_every_file_of_a_source_once(tmp_path: Path) -> None:
    (tmp_path / "a.tex").write_text(SOURCE)
    (tmp_path / "b.bbl").write_text(SOURCE)
    assert len(B.from_source(tmp_path)) == 4


# --- subjects --------------------------------------------------------------------------------------------


def test_subjects_judge_works_with_codes_and_categories_works_without() -> None:
    assert M.family("14N35") == "14N" and M.family("14-02") == "14-" and M.family("55") == "55-"
    assert M.families(["14N35", "14N10", "14D23"]) == ["14D", "14N"]
    assert M.passes(["55N91", "14C17"], "", ["14C"], []) is True  # any code of the work
    assert M.passes(["55N91"], "math.AG", ["14C"], ["math.AG"]) is False  # codes decide when there are any
    assert M.passes([], "math.AG", ["14C"], ["math.AG"]) is True
    assert M.passes([], "math.AG", ["14C"], []) is False  # loom supplies no categories of its own
    assert M.passes([], "", ["14C"], ["math.AG"]) is None


def test_a_tally_counts_primary_families_any_family_categories_and_neither() -> None:
    t = M.tally([(["14N35", "14L30"], "math.AG"), (["14L24"], ""), ([], "math.AT"), ([], "")])
    assert t["primary"] == {"14N": 1, "14L": 1} and t["any"] == {"14N": 1, "14L": 2}
    assert t["categories"] == {"math.AT": 1} and t["neither"] == {"works": 1}


# --- records ---------------------------------------------------------------------------------------------


def test_identifiers_have_one_spelling_and_a_rank() -> None:
    assert norm("DOI:10.1007/S002220050293") == "doi:10.1007/s002220050293"
    assert norm("arXiv:2207.01652v2") == "arxiv:2207.01652"
    assert norm("doi:10.48550/arXiv.2207.01652") == "arxiv:2207.01652"
    assert ranked(
        ["zbl:0953.14035", "arxiv:alg-geom/9708001", "doi:10.1007/s002220050293", "arXiv:alg-geom/9708001v2"]
    ) == [
        "doi:10.1007/s002220050293",
        "arxiv:alg-geom/9708001",
        "zbl:0953.14035",
    ]


def test_a_record_merges_sources_and_round_trips(tmp_path: Path) -> None:
    w = Work(ids=["doi:10.1/a"], depth=1)
    w.add_ids(["zbl:1234.56789", "arxiv:2101.00001"])
    w.add_references([Reference(id="doi:10.1/x"), Reference(text="Some book, 1970")])
    w.add_references([Reference(id="DOI:10.1/X"), Reference(text="Some book, 1970"), Reference(id="doi:10.1/y")])
    assert [r.id for r in w.references] == ["doi:10.1/x", None, "doi:10.1/y"]
    assert w.references_known and w.downloadable == "source"
    path = save(tmp_path, w)
    assert path == tmp_path / "refs" / "doi" / "10.1_a" / "work.json"
    back = load(path)
    assert back is not None and back.ids == w.ids and back.references[1].text == "Some book, 1970"
    assert set(load_all(tmp_path)) == {"doi:10.1/a"}


# --- the services, as recorded ---------------------------------------------------------------------------


def replay(url: str, headers: dict[str, str]) -> bytes:
    if url not in RECORDED:
        raise net.NotFound(url)
    return str(RECORDED[url]).encode("utf-8")


def service(name: str, tmp: Path | None = None) -> net.Service:
    return net.Service(name, 0.0, tmp, replay)


def test_zbmath_gives_identifiers_subjects_and_resolved_references() -> None:
    zb = Zbmath(service("zbmath"))
    gp = zb.by_id("doi:10.1007/s002220050293")
    assert gp is not None and gp.msc == ["14N35", "14L30", "14N10"] and not gp.references
    assert set(gp.ids) == {"zbl:0953.14035", "doi:10.1007/s002220050293", "arxiv:alg-geom/9708001"}
    ar = zb.by_id("arxiv:2207.01652")
    assert ar is not None and len(ar.references) == 46 and "doi:10.1016/j.aim.2025.110434" in ar.ids
    doc = zb.by_document(1112315)
    assert doc is not None and doc.title.startswith("Equivariant Chow groups") and len(doc.references) == 41
    assert zb.by_id("doi:10.9999/nothing") is None


def test_openalex_gives_reference_lists_and_open_copies() -> None:
    oa = OpenAlex(service("openalex"))
    gp = oa.by_id("doi:10.1007/s002220050293")
    assert gp is not None and len(gp.references) == 19 and gp.openalex == "W2034404907"
    listed = oa.batch(gp.references)
    assert len(listed) == 18 and sum(1 for r in listed if r.open_pdf) == 5
    pre = oa.by_id("arxiv:2207.01652")
    assert pre is not None and pre.ids == ["arxiv:2207.01652"] and not pre.references


def test_openalex_sends_its_key_as_a_header_never_in_the_url() -> None:
    seen: list[tuple[str, dict[str, str]]] = []

    def capture(url: str, headers: dict[str, str]) -> bytes:
        seen.append((url, headers))
        return replay(url, headers)

    OpenAlex(net.Service("openalex", 0.0, None, capture), key="secret").by_id("doi:10.1007/s002220050293")
    assert seen[0][1] == {"Authorization": "Bearer secret"} and "secret" not in seen[0][0]


def test_arxiv_gives_primary_categories_in_one_request() -> None:
    assert Arxiv(service("arxiv")).categories(["2207.01652", "2205.11114", "alg-geom/9708001"]) == {
        "2207.01652": "math.AG",
        "2205.11114": "math.AG",
        "alg-geom/9708001": "math.AG",
    }


def test_a_service_caches_answers_and_absences_and_can_be_refreshed(tmp_path: Path) -> None:
    calls: list[str] = []

    def transport(url: str, headers: dict[str, str]) -> bytes:
        calls.append(url)
        if "missing" in url:
            raise net.NotFound(url)
        return b'{"ok": true}'

    s = net.Service("x", 0.0, tmp_path, transport)
    assert s.get_json("https://e/1") == {"ok": True}
    assert s.get_json("https://e/1") == {"ok": True}
    for _ in range(2):
        with pytest.raises(net.NotFound):
            s.get("https://e/missing")
    assert calls == ["https://e/1", "https://e/missing"] and s.cached == 2
    net.Service("x", 0.0, tmp_path, transport, refresh=True).get("https://e/1")
    assert calls[-1] == "https://e/1"


def test_a_service_counts_its_failures_so_a_plan_can_say_what_it_lacks() -> None:
    def refuse(url: str, headers: dict[str, str]) -> bytes:
        raise net.ServiceError(f"{url}: HTTP 403 Forbidden")

    s = net.Service("openalex", 0.0, None, refuse)
    for _ in range(2):
        with pytest.raises(net.ServiceError):
            s.get("https://e/w")
    assert s.failures == 2 and "403" in s.last_failure


# --- the plan, on a synthetic citation graph -------------------------------------------------------------


class FakeZb:
    """zbMATH for a small invented literature."""

    def __init__(self) -> None:
        self.records = {
            "doi:10.1/a": ZbRecord(
                1,
                ["doi:10.1/a", "arxiv:2001.00001"],
                "Paper A",
                ["Alpha, A."],
                2020,
                ["14N35", "55N91"],
                [
                    Reference(id="doi:10.1/x", msc=["14N35"]),
                    Reference(id="doi:10.1/y", msc=["55N91"]),
                    Reference(text="Z. Zeta, The Zeta paper, 2021."),
                    Reference(zbmath=77, text="P. Pi, Pi, 2019."),
                ],
            ),
            "doi:10.1/b": ZbRecord(
                2,
                ["doi:10.1/b"],
                "Paper B",
                ["Beta, B."],
                2019,
                ["14D20"],
                [
                    Reference(id="doi:10.1/x"),
                    Reference(id="doi:10.1/w"),
                ],
            ),
            "doi:10.1/x": ZbRecord(
                3,
                ["doi:10.1/x", "arxiv:1901.00001"],
                "Paper X",
                ["Xi, X."],
                2019,
                ["14N35"],
                [Reference(id="doi:10.1/deep")],
            ),
        }
        self.documents = {77: ZbRecord(77, ["doi:10.1/p"], "Paper P", ["Pi, P."], 2019, ["14D23"], [])}

    def by_id(self, ident: str) -> ZbRecord | None:
        return self.records.get(norm(ident))

    def by_document(self, n: int) -> ZbRecord | None:
        return self.documents.get(n)


class FakeOa:
    def by_id(self, ident: str) -> OaRecord | None:
        if norm(ident) == "doi:10.1/p":
            return OaRecord("W1", ["doi:10.1/p"], "Paper P", [], 2019, [], "https://journal.example/p.pdf")
        return None

    def batch(self, ids: list[str]) -> list[OaRecord]:
        return []


class FakeArxiv:
    def categories(self, ids: list[str]) -> dict[str, str]:
        return {"2101.00009": "math.AG"}


class FakeResolver:
    def candidates(self, q: Query) -> list[Candidate]:
        text = q.text or q.title
        if "Zeta" in text:
            return [Candidate("arxiv:2101.00009", "Crossref", 0.95, "The Zeta paper")]
        if "Paper B" in text:
            return [Candidate("doi:10.1/b", "zbMATH Open", 1.0, "Paper B")]
        return []


BIB = {
    "A20": BibEntry("A20", "article", {"title": "Paper A", "author": "Alpha, A.", "doi": "10.1/a"}),
    "B19": BibEntry("B19", "article", {"title": "Paper B", "author": "Beta, B.", "year": "2019"}),
    "C00": BibEntry("C00", "misc", {"title": "Unfindable", "author": "Gamma, C."}),
}


def planner(root: Path) -> Planner:
    return Planner(root, Clients(FakeZb(), FakeOa(), FakeArxiv(), FakeResolver()))


def keep(**kw: object) -> Settings:
    """Depth 2, keeping 14D and 14N, and math.AG for works with no MSC code."""
    return Settings(**{"depth": 2, "subjects": ["14D", "14N"], "categories": ["math.AG"], **kw})  # type: ignore[arg-type]


def test_the_plan_follows_references_within_the_subjects_and_orders_by_depth_then_citations(tmp_path: Path) -> None:
    plan = planner(tmp_path).run(keep(), BIB, ["A20", "B19", "C00"], ["bib"])
    assert plan.subjects == ["14D", "14N"] and plan.categories == ["math.AG"]
    assert plan.order[:2] == ["doi:10.1/a", "doi:10.1/b"]
    assert plan.order[2] == "doi:10.1/x"  # cited by both A and B
    assert set(plan.order) == {"doi:10.1/a", "doi:10.1/b", "doi:10.1/x", "doi:10.1/p", "arxiv:2101.00009"}
    excluded = {e["id"]: e["why"] for e in plan.excluded}
    assert excluded == {"doi:10.1/y": "outside the subjects", "doi:10.1/w": "no MSC code and no arXiv category"}
    assert [u["citekey"] for u in plan.unidentified] == ["C00"]
    c = plan.counts
    assert (c["works"], c["excluded"], c["from_arxiv"], c["open_copies"], c["metadata_only"]) == (5, 2, 3, 1, 1)
    assert c["strong_by_lookup"] == 2  # B by its entry, Z by its text
    records = load_all(tmp_path)
    assert records["doi:10.1/x"].reached_from == ["doi:10.1/a", "doi:10.1/b"]
    assert records["arxiv:2101.00009"].arxiv_category == "math.AG"  # no MSC code, kept by its category
    assert records["doi:10.1/p"].downloadable == "pdf"
    assert records["doi:10.1/b"].citekeys == ["B19"] and records["doi:10.1/b"].reached_by == "lookup"
    assert not any("deep" in k for k in records)  # depth 2 stops there


def test_depth_one_needs_no_subjects_and_other_subjects_keep_other_works(tmp_path: Path) -> None:
    one = planner(tmp_path).run(Settings(depth=1), BIB, ["A20", "B19"], ["bib"])
    assert set(one.order) == {"doi:10.1/a", "doi:10.1/b"} and not one.excluded
    other = planner(tmp_path / "o").run(Settings(depth=2, subjects=["55N91"]), BIB, ["A20", "B19"], ["bib"])
    assert other.subjects == ["55N"] and other.categories == []
    assert "doi:10.1/y" in other.order and "doi:10.1/x" not in other.order
    why = {e["id"]: e["why"] for e in other.excluded}
    assert why["arxiv:2101.00009"] == "arXiv category not in categories"
    assert any(line == "  excluded, no MSC code and a category not listed: math.AG 1" for line in summary(other))


def test_the_cap_selects_in_order_and_the_fingerprint_names_what_the_plan_was_made_from(tmp_path: Path) -> None:
    plan = planner(tmp_path).run(keep(cap=2), BIB, ["A20", "B19"], ["bib"])
    downloadable = [k for k in plan.order if load_all(tmp_path)[k].downloadable]
    assert plan.selected == downloadable[:2] and plan.counts["over_cap"] == 2
    assert plan.fingerprint == fingerprint(keep(cap=2), ["bib"])
    assert plan.fingerprint != fingerprint(keep(cap=3), ["bib"])
    assert plan.fingerprint != fingerprint(keep(cap=2, categories=[]), ["bib"])
    assert plan.fingerprint != fingerprint(keep(cap=2), ["bib edited"])
    assert any("over the cap" in line for line in summary(plan))


class LinkingZb(FakeZb):
    """zbMATH that also finds A and X by their arXiv numbers, and whose B cites both under the other scheme."""

    def __init__(self) -> None:
        super().__init__()
        self.records["arxiv:2001.00001"] = self.records["doi:10.1/a"]
        self.records["arxiv:1901.00001"] = self.records["doi:10.1/x"]
        self.records["doi:10.1/b"].references.extend([Reference(id="arxiv:1901.00001"), Reference(id="doi:10.1/a")])


def test_one_work_under_two_identifiers_is_one_record(tmp_path: Path) -> None:
    bib = {
        **BIB,
        "A20": BibEntry("A20", "article", {"title": "Paper A", "eprint": "2001.00001", "archiveprefix": "arXiv"}),
    }
    plan = Planner(tmp_path, Clients(LinkingZb(), FakeOa(), FakeArxiv(), FakeResolver())).run(
        keep(), bib, ["A20", "B19"], ["bib"]
    )
    records = load_all(tmp_path)
    assert (
        set(records) == set(plan.order) == {"doi:10.1/a", "doi:10.1/b", "doi:10.1/x", "doi:10.1/p", "arxiv:2101.00009"}
    )
    a = records["doi:10.1/a"]  # declared by its arXiv number, keyed by the DOI zbMATH linked it to
    assert a.home == "refs/arxiv/2001.00001" and a.citekeys == ["A20"]
    assert a.reached_from == ["doi:10.1/b"]  # B cites it by DOI
    assert records["doi:10.1/x"].reached_from == ["doi:10.1/a", "doi:10.1/b"]  # by DOI from A, by arXiv number from B


class BookZb(FakeZb):
    """zbMATH that knows a book B cites only by title, not by the DOI B cites it under."""

    def __init__(self) -> None:
        super().__init__()
        self.records["doi:10.1/b"].references.append(Reference(id="doi:10.1/book-2nd-ed"))
        self.book = ZbRecord(
            9, ["zbl:0541.14005"], "Intersection theory", ["Fulton, William"], 1984, ["14C17", "14-02"], []
        )

    def by_title(self, title: str, authors: list[str], year: int | None) -> ZbRecord | None:
        return self.book if title == "Intersection Theory" and authors == ["William Fulton"] else None


class BookOa(FakeOa):
    def by_id(self, ident: str) -> OaRecord | None:
        if norm(ident) == "doi:10.1/book-2nd-ed":
            return OaRecord("W9", ["doi:10.1/book-2nd-ed"], "Intersection Theory", ["William Fulton"], 1998, [], "")
        return super().by_id(ident)


def test_a_work_zbmath_lacks_by_identifier_is_classified_by_title(tmp_path: Path) -> None:
    plan = Planner(tmp_path, Clients(BookZb(), BookOa(), FakeArxiv(), FakeResolver())).run(
        Settings(depth=2, subjects=["14N", "14C"]), BIB, ["A20", "B19"], ["bib"]
    )
    assert "doi:10.1/book-2nd-ed" in plan.order
    book = load_all(tmp_path)["doi:10.1/book-2nd-ed"]
    assert book.msc == ["14C17", "14-02"] and "zbl:0541.14005" in book.ids and book.title == "Intersection Theory"
    only_14d = Planner(tmp_path / "d", Clients(BookZb(), BookOa(), FakeArxiv(), FakeResolver())).run(
        Settings(depth=2, subjects=["14D"]), BIB, ["A20", "B19"], ["bib"]
    )
    gone = next(x for x in only_14d.excluded if x["id"] == "doi:10.1/book-2nd-ed")
    assert gone["why"] == "outside the subjects" and gone["msc"] == ["14C17", "14-02"]
    assert any(line.startswith("  excluded, outside the subjects:") and "14C 1" in line for line in summary(only_14d))


def test_zbmath_by_title_needs_an_author_and_a_strong_match() -> None:
    body = json.dumps(
        {
            "result": [
                {
                    "id": 1,
                    "identifier": "0541.14005",
                    "title": {"title": "Intersection theory"},
                    "year": "1984",
                    "contributors": {"authors": [{"name": "Fulton, William"}]},
                    "msc": [{"code": "14C17"}],
                }
            ]
        }
    )
    asked: list[str] = []

    def transport(url: str, headers: dict[str, str]) -> bytes:
        asked.append(url)
        return body.encode()

    zb = Zbmath(net.Service("zbmath", 0.0, None, transport))
    assert zb.by_title("Intersection Theory", [], 1998) is None and not asked
    found = zb.by_title("Intersection Theory: 2nd ed.", ["William Fulton"], 1984)
    assert found is not None and found.msc == ["14C17"]
    assert "ti%3AIntersection+Theory+2nd+ed+%26+au%3Afulton" in asked[0]
    assert (
        zb.by_title("Intersection Theory", ["William Fulton"], 1998) is not None
    )  # an exact title and author, any edition
    assert zb.by_title("Enumerative geometry", ["William Fulton"], 1984) is None
    body = json.dumps(
        {
            "result": [
                {
                    "id": 2,
                    "title": {"title": "Algebraic stacks", "original": "Champs algébriques"},
                    "year": "2000",
                    "contributors": {"authors": [{"name": "Laumon, Gérard"}]},
                    "msc": [{"code": "14A20"}],
                }
            ]
        }
    )
    assert (
        zb.by_title("Champs algébriques", ["Gérard Laumon"], 2000) is not None
    )  # zbMATH's English title is not the one cited


def test_a_plan_needs_subjects_to_go_deeper(tmp_path: Path) -> None:
    with pytest.raises(PlanRefused, match="set subjects"):
        planner(tmp_path).run(Settings(depth=2), BIB, ["A20"], ["bib"])


def test_a_survey_counts_what_the_cited_works_cite_and_keeps_nothing(tmp_path: Path) -> None:
    survey = planner(tmp_path).survey(BIB, ["A20", "B19", "C00"])
    assert survey.cited["primary"] == {"14N": 1, "14D": 1}
    refs = survey.references
    # A cites X (14N), Y (55N), Z (a math.AG preprint, found by its text) and P (14D, by zbMATH's number); B cites X again and W
    assert refs["primary"] == {"14N": 1, "55N": 1, "14D": 1}
    assert refs["categories"] == {"math.AG": 1} and refs["neither"] == {"works": 1}
    assert (survey.counts["cited"], survey.counts["references"], survey.counts["unidentified"]) == (2, 5, 1)
    assert survey_summary(survey)[1] == "the 5 works they cite, by primary MSC family: 14N 1 · 55N 1 · 14D 1"
    assert load_all(tmp_path) == {} and load_plan(tmp_path) is None


def test_a_replan_keeps_downloads_and_counts_what_was_already_on_disk(tmp_path: Path) -> None:
    (tmp_path / "refs" / "doi" / "10.1_x" / "src").mkdir(parents=True)
    plan = planner(tmp_path).run(keep(), BIB, ["A20", "B19"], ["bib"])
    assert load_all(tmp_path)["doi:10.1/x"].download["fetched"] == "before the crawl"
    assert plan.counts["already_fetched"] == 1


# --- fetching ------------------------------------------------------------------------------------------


def eprint(text: str) -> bytes:
    return gzip.compress(text.encode("utf-8"))


def test_fetch_downloads_in_order_under_the_cap_resumes_and_records_failures(tmp_path: Path) -> None:
    plan = planner(tmp_path).run(keep(cap=3), BIB, ["A20", "B19"], ["bib"])
    save_plan(tmp_path, plan)
    got: list[str] = []

    def arxiv_get(url: str) -> bytes:
        got.append(url)
        if "1901.00001" in url:
            raise net.ServiceError("arXiv: HTTP 503")
        return eprint(SOURCE)

    def web_get(url: str) -> bytes:
        got.append(url)
        return b"%PDF-1.4 fake"

    report = fetch(tmp_path, plan, 3, arxiv_get, web_get)
    # X fails and takes no place under the cap, so P, next in order, is fetched instead
    assert (report.fetched, report.failed, report.left_out) == (3, 1, 0)
    assert got == [
        "https://arxiv.org/e-print/2001.00001",
        "https://arxiv.org/e-print/1901.00001",
        "https://arxiv.org/e-print/2101.00009",
        "https://journal.example/p.pdf",
    ]
    records = load_all(tmp_path)
    a = records["doi:10.1/a"]
    assert a.download["fetched"] and (tmp_path / a.home / "src" / "main.tex").is_file()
    assert any(r.id == "arxiv:1912.06162" for r in a.references)  # its bibliography was read
    assert "HTTP 503" in records["doi:10.1/x"].download["error"]
    assert (tmp_path / records["doi:10.1/p"].home / "paper.pdf").read_bytes().startswith(b"%PDF")
    # a second run counts what is on disk first: the cap is full, so the failure waits
    again = fetch(tmp_path, load_plan(tmp_path) or plan, 3, lambda u: eprint(SOURCE), web_get)
    assert (again.already, again.fetched, again.left_out) == (3, 0, 1)
    more = fetch(tmp_path, plan, 4, lambda u: eprint(SOURCE), web_get)
    assert (more.already, more.fetched, more.left_out) == (3, 1, 0)


def test_a_replan_estimates_from_what_was_downloaded(tmp_path: Path) -> None:
    plan = planner(tmp_path).run(keep(cap=10), BIB, ["A20", "B19"], ["bib"])
    assert plan.estimate["bytes"] == 3 * 3_000_000 + 1_000_000  # nothing fetched yet: the assumed sizes
    fetch(tmp_path, plan, 1, lambda u: eprint(SOURCE), lambda u: b"%PDF-1.4")
    again = planner(tmp_path).run(keep(cap=10), BIB, ["A20", "B19"], ["bib"])
    assert again.estimate["bytes"] == 2 * len(eprint(SOURCE)) + 1_000_000


def test_fetch_stops_when_arxiv_keeps_refusing_and_an_interruption_keeps_what_was_fetched(tmp_path: Path) -> None:
    plan = planner(tmp_path).run(keep(), BIB, ["A20", "B19"], ["bib"])
    asked: list[str] = []

    def refuse(url: str) -> bytes:
        asked.append(url)
        raise net.ServiceError(f"{url}: HTTP 406 Not Acceptable")

    report = fetch(tmp_path, plan, 10, refuse, lambda u: b"%PDF-1.4")
    assert len(asked) == 3 and report.failed == 3 and "refused 3 downloads in a row" in report.stopped
    calls = 0

    def interrupted_on_the_second(url: str) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return eprint(SOURCE)

    report = fetch(tmp_path, plan, 10, interrupted_on_the_second, lambda u: b"%PDF-1.4")
    assert report.fetched == 1 and report.stopped.startswith("interrupted")
    again = fetch(tmp_path, plan, 10, lambda u: eprint(SOURCE), lambda u: b"%PDF-1.4")
    assert (again.already, again.fetched, again.stopped) == (1, 3, "")


def test_a_download_that_is_not_a_pdf_is_a_failure(tmp_path: Path) -> None:
    plan = planner(tmp_path).run(keep(), BIB, ["A20", "B19"], ["bib"])
    report = fetch(tmp_path, plan, 10, lambda u: eprint(SOURCE), lambda u: b"<html>paywall</html>")
    assert report.failed == 1 and "not a PDF" in report.errors[0]
    assert not (tmp_path / load_all(tmp_path)["doi:10.1/p"].home / "paper.pdf").exists()


# --- configuration, the bibliography, and the commands --------------------------------------------------


def test_the_crawl_table_is_read_and_bad_values_warned_about() -> None:
    cfg = QuiltConfig.from_dict(
        {"crawl": {"depth": 3, "subjects": ["14N", "14D"], "categories": ["math.AG"], "cap": 50}}
    )
    assert (cfg.crawl_depth, cfg.crawl_subjects, cfg.crawl_categories, cfg.crawl_cap) == (
        3,
        ["14N", "14D"],
        ["math.AG"],
        50,
    )
    bad = QuiltConfig.from_dict({"crawl": {"depth": 0, "subjects": "14N", "categories": "math.AG", "cap": -1}})
    assert (bad.crawl_depth, bad.crawl_subjects, bad.crawl_categories, bad.crawl_cap) == (2, [], [], 1000)
    assert len(bad.warnings) == 4 and not cfg.warnings


def test_a_bib_inside_a_fetched_source_is_not_the_quilts(tmp_path: Path) -> None:
    (tmp_path / "refs.bib").write_text("")
    (tmp_path / "refs" / "arxiv" / "1" / "src").mkdir(parents=True)
    (tmp_path / "refs" / "arxiv" / "1" / "src" / "theirs.bib").write_text("")
    (tmp_path / "ai" / "runs" / "r").mkdir(parents=True)
    (tmp_path / "ai" / "runs" / "r" / "draft.bib").write_text("")
    assert find_bib_files(tmp_path) == ["refs.bib"]


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def demo(tmp_path: Path, refs: str = "") -> Path:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    cfg = q / "config.toml"
    cfg.write_text(cfg.read_text().replace("fetch = false", refs or "fetch = false"))
    with (q / "refs.bib").open("a") as fh:
        fh.write(
            "\n@article{A20, title = {Paper A}, author = {Alpha, A.}, doi = {10.1/a}}\n@article{B19, title = {Paper B}, author = {Beta, B.}, year = {2019}}\n"
        )
    node = q / "nodes" / "dm-0001.tex"
    node.write_text(
        node.read_text().replace("\\end{definition}", "See \\cite{A20} and \\cite{B19}.\n\\end{definition}", 1)
    )
    return q


def test_the_commands_ask_for_consent_first(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("refs", "crawl", "plan", cwd=q)
    assert r.exit_code == 2 and "resolve = true" in r.output
    (tmp_path / "two").mkdir()
    q2 = demo(tmp_path / "two", "fetch = false\nresolve = true")
    r = run("refs", "crawl", "fetch", cwd=q2)
    assert r.exit_code == 2 and "fetch = true" in r.output


def test_plan_then_fetch_then_status_and_a_stale_plan_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli = importlib.import_module("loom.cli.refs")
    q = demo(tmp_path, "fetch = true\nresolve = true")
    monkeypatch.setattr(
        cli, "crawl_clients", lambda root, cfg, refresh: Clients(FakeZb(), FakeOa(), FakeArxiv(), FakeResolver())
    )
    monkeypatch.setattr(cli, "crawl_downloaders", lambda: (lambda u: eprint(SOURCE), lambda u: b"%PDF-1.4"))
    r = run("refs", "crawl", "plan", cwd=q)  # no subjects: a survey, and no plan
    assert r.exit_code == 0, r.output
    assert "the 2 works they cite" not in r.output and "by primary MSC family: 14N 1 · 55N 1 · 14D 1" in r.output
    assert "no plan was made" in r.output and load_plan(q) is None
    assert "no crawl plan" in run("refs", "crawl", "fetch", cwd=q).output
    cfg = q / "config.toml"
    cfg.write_text(cfg.read_text() + '\n[crawl]\nsubjects = ["14D", "14N"]\ncategories = ["math.AG"]\n')
    r = run("refs", "crawl", "plan", cwd=q)
    assert r.exit_code == 0, r.output
    assert "depth 2 · subjects 14D 14N · categories math.AG · cap 1000" in r.output
    assert "nothing was downloaded" in r.output
    r = run("refs", "crawl", "fetch", cwd=q)
    assert r.exit_code == 0, r.output
    assert "fetched 5 (" in r.output  # the demo's own Manolache citation, A, X, Z and P
    data = json.loads(run("refs", "crawl", "status", "--json", cwd=q).output)
    assert data["downloaded"] == 5 and data["plan"]["current"] is True
    assert (data["works"], data["to_fetch"], data["metadata_only"], data["outside_plan"]) == (6, 0, 1, 0)
    cfg.write_text(cfg.read_text() + "cap = 2\n")
    r = run("refs", "crawl", "fetch", cwd=q)
    assert r.exit_code == 2 and "plan again" in r.output
    assert "out of date" in run("refs", "crawl", "status", cwd=q).output


@pytest.mark.network
def test_a_depth_one_plan_against_the_services(tmp_path: Path) -> None:
    if not os.environ.get("LOOM_NETWORK"):
        pytest.skip("set LOOM_NETWORK=1 to ask zbMATH Open, OpenAlex and arXiv")
    q = demo(tmp_path, "fetch = false\nresolve = true")
    (q / "config.toml").write_text((q / "config.toml").read_text() + "\n[crawl]\ndepth = 1\n")
    bib = q / "refs.bib"
    bib.write_text(
        bib.read_text()
        .replace("doi = {10.1/a}", "doi = {10.1007/s002220050293}")
        .replace(
            "title = {Paper B}, author = {Beta, B.}, year = {2019}",
            "title = {Virtual localization revisited}, eprint = {2207.01652}",
        )
    )
    r = run("refs", "crawl", "plan", cwd=q)
    assert r.exit_code == 0, r.output
    records = load_all(q)
    assert "14N35" in records["doi:10.1007/s002220050293"].msc
    assert any("arxiv:2207.01652" in map(norm, w.ids) for w in records.values())
