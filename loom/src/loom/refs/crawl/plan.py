"""Planning a crawl from metadata alone (book 8.13.5).

The plan identifies the quilt's cited works, reads their reference lists from zbMATH Open, OpenAlex and any source already on disk, identifies each reference, keeps the works in the author's subjects and categories, and repeats to the chosen depth. Without subjects it surveys instead: it counts what the cited works cite, by MSC family and arXiv category, so the author chooses from what is there. Nothing is downloaded. It writes a record per work and `refs/crawl/plan.json`, and says what a fetch would do: how many works can be downloaded, in what order, within the cap, and at what cost.

The count is exact wherever an index lists a work's references and a floor where none does: a preprint's references are known only once its source is on disk, and the plan counts the works in that state.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loom.refs.crawl import msc as M
from loom.refs.crawl.bibitem import from_source
from loom.refs.crawl.bibitem import query as bib_query
from loom.refs.crawl.net import ServiceError
from loom.refs.crawl.work import Reference, Work, home_of, norm, ranked
from loom.refs.crawl.work import load as load_work
from loom.refs.crawl.work import save as save_work
from loom.refs.identity import declared, primary
from loom.refs.resolve import Query, ResolveRefused, _plain, _surname, query_for
from loom.render.publish import write_atomic
from loom.scan.bib import BibEntry

PLAN = 1
# what a download is assumed to cost until the library has some of its own to average
AVG_SOURCE = 3_000_000
AVG_PDF = 1_000_000
SOURCE_SECONDS = 3.0
PDF_SECONDS = 1.0
_YEAR = re.compile(r"\b(1[89]\d\d|20\d\d)\b")


class PlanRefused(Exception):
    """A plan cannot be made as asked, for a reason the author can fix."""


@dataclass
class Settings:
    """The `[crawl]` table: how deep, which subjects and categories, how many downloads."""

    depth: int = 2
    subjects: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    cap: int = 1000

    def as_dict(self) -> dict[str, Any]:
        return {"depth": self.depth, "subjects": self.subjects, "categories": self.categories, "cap": self.cap}


@dataclass
class Clients:
    """The services a plan asks; tests pass fakes with the same methods."""

    zbmath: Any
    openalex: Any
    arxiv: Any
    resolver: Any


@dataclass
class Plan:
    record: int
    made: str
    fingerprint: str
    settings: dict[str, Any]
    subjects: list[str]
    categories: list[str]
    order: list[str]
    homes: dict[str, str]
    selected: list[str]
    counts: dict[str, int]
    estimate: dict[str, float]
    excluded: list[dict[str, Any]] = field(default_factory=list)
    possible: list[dict[str, Any]] = field(default_factory=list)
    unidentified: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Survey:
    """What the cited works cite, counted, for an author choosing subjects and categories."""

    cited: dict[str, dict[str, int]]
    references: dict[str, dict[str, int]]
    counts: dict[str, int]


def fingerprint(settings: Settings, bib_texts: list[str]) -> str:
    """What a plan was made from: the `[crawl]` settings and the bibliography, so a fetch can refuse a plan that no longer describes the quilt."""
    h = hashlib.sha256(json.dumps(settings.as_dict(), sort_keys=True).encode("utf-8"))
    for text in bib_texts:
        h.update(b"\0" + text.encode("utf-8"))
    return "sha256:" + h.hexdigest()


def plan_path(root: Path) -> Path:
    return root / "refs" / "crawl" / "plan.json"


def save_plan(root: Path, plan: Plan) -> Path:
    path = plan_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, json.dumps(asdict(plan), indent=1, ensure_ascii=False) + "\n")
    return path


def load_plan(root: Path) -> Plan | None:
    try:
        return Plan(**json.loads(plan_path(root).read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return None


def _average(works: list[Work], kind: str, default: int) -> float:
    """The mean size of this kind of download among works already fetched, or the default before there are any."""
    sizes = [w.download["bytes"] for w in works if w.download.get("kind") == kind and w.download.get("bytes")]
    return sum(sizes) / len(sizes) if sizes else float(default)


def _text_query(text: str) -> Query:
    """A lookup for a reference known only as text: the whole text stands for the title, and loom's scoring reads the title and a surname out of it."""
    years = _YEAR.findall(text)
    return Query(text, (), years[-1] if years else "", text)


class Planner:
    """One plan's walk. `log` receives a line per step, for a terminal to show progress."""

    def __init__(self, root: Path, clients: Clients, log: Callable[[str], None] = lambda _: None) -> None:
        self.root = root
        self.c = clients
        self.log = log
        self.alias: dict[str, Work] = {}  # every identifier of every work kept, to the one record of it
        self.excluded: list[dict[str, Any]] = []
        self._excluded_by: dict[str, dict[str, Any]] = {}
        self.possible: list[dict[str, Any]] = []
        self.unidentified: list[dict[str, Any]] = []
        self.lookups = 0
        self._queries: dict[str, Query] = {}

    # --- identification ---------------------------------------------------------------------------

    def _known(self, ids: list[str]) -> Work | None:
        return next((self.alias[norm(i)] for i in ids if norm(i) in self.alias), None)

    def _remember(self, work: Work) -> Work:
        """Index a work by each of its identifiers, merging it with any work already indexed under one of them; returns the record that remains.

        A work's identifiers grow as sources are read, so the same work reached by its arXiv number and by its DOI becomes one record once either source links the two. The shallower record remains, so a cited work keeps its home.
        """
        while True:
            other = next((self.alias[norm(i)] for i in work.ids if self.alias.get(norm(i), work) is not work), None)
            if other is None:
                break
            keep, gone = (work, other) if 0 < work.depth < other.depth else (other, work)
            keep.merge(gone)
            for i in gone.ids:
                self.alias[norm(i)] = keep
            work = keep
        for i in work.ids:
            self.alias[norm(i)] = work
        return work

    def _works(self) -> list[Work]:
        return list({id(w): w for w in self.alias.values()}.values())

    def _lookup(self, q: Query, label: dict[str, Any]) -> list[str] | None:
        """Identifiers for a strong match, or None, recording a possible match or no match."""
        self.lookups += 1
        try:
            found = self.c.resolver.candidates(q)
        except ResolveRefused as exc:
            self.unidentified.append({**label, "why": str(exc)})
            return None
        strong = [c for c in found if c.strength == "strong"]
        if strong:
            return ranked([strong[0].id, *strong[0].also])
        if found:
            self.possible.append(
                {**label, "candidate": found[0].id, "confidence": found[0].confidence, "title": found[0].title}
            )
        else:
            self.unidentified.append(label)
        return None

    def depth_one(self, citekey: str, entry: BibEntry) -> Work | None:
        """A cited work: by the identifier its entry declares, or by a strong lookup match."""
        ids = declared(entry)
        if ids:
            w = Work(ids=ranked([str(i) for i in ids]), depth=1, reached_by="declared", citekeys=[citekey])
            wid = primary(entry)
            w.home = "refs/" + wid.path if wid else home_of(w.ids[0])
            return w
        found = self._lookup(query_for(entry), {"citekey": citekey, "text": entry.fields.get("title", "")})
        if not found:
            return None
        w = Work(ids=found, depth=1, reached_by="lookup", citekeys=[citekey])
        w.home = home_of(w.ids[0])
        return w

    def reference(self, ref: Reference) -> Work | None:
        """The work a reference names, identified by its identifier, zbMATH's document number, or a lookup of its text."""
        if ref.id:
            return Work(ids=[ref.id], msc=list(ref.msc), reached_by="index", sources={"text": (ref.text or "")[:200]})
        if ref.zbmath:
            try:
                zb = self.c.zbmath.by_document(ref.zbmath)
            except ServiceError:
                zb = None
            if zb and zb.ids:
                w = Work(ids=ranked(zb.ids), reached_by="index", sources={"zbmath": zb.document})
                w.fill(zb.title, zb.authors, zb.year, zb.msc or ref.msc)
                return w
        if ref.text:
            q = self._queries.get(ref.text) or _text_query(ref.text)
            found = self._lookup(q, {"text": ref.text[:200]})
            if found:
                return Work(ids=found, msc=list(ref.msc), reached_by="lookup", sources={"text": ref.text[:200]})
        return None

    # --- metadata -----------------------------------------------------------------------------------

    def enrich(self, work: Work, expand: bool) -> None:
        """Fill a work from zbMATH and OpenAlex, and, when it is to be expanded, collect its references from both and from its source if on disk."""
        zb = None
        for ident in list(work.ids):
            if norm(ident).partition(":")[0] in ("doi", "arxiv", "zbl"):
                try:
                    zb = self.c.zbmath.by_id(ident)
                except ServiceError:
                    zb = None
                if zb:
                    break
        if zb:
            work.add_ids(zb.ids)
            work.fill(zb.title, zb.authors, zb.year, zb.msc)
            work.sources["zbmath"] = zb.document
        oa = None
        for ident in list(work.ids):
            if norm(ident).partition(":")[0] in ("doi", "arxiv"):
                try:
                    oa = self.c.openalex.by_id(ident)
                except ServiceError:
                    oa = None
                if oa:
                    break
        if oa:
            work.add_ids(oa.ids)
            work.fill(oa.title, oa.authors, oa.year)
            work.open_pdf = work.open_pdf or oa.open_pdf
            work.sources["openalex"] = oa.openalex
        if not expand:
            return
        if zb and zb.references:
            work.add_references(zb.references)
        if oa and oa.references:
            try:
                listed = self.c.openalex.batch(oa.references)
            except ServiceError:
                listed = []
            for r in listed:
                if not r.ids and r.title and r.authors:
                    # OpenAlex knows the work but not an identifier: look it up by title, first author and year, not as bare text
                    self._queries[r.title] = Query(_plain(r.title), (_surname(r.authors[0]),), str(r.year or ""))
            work.add_references([Reference(id=r.ids[0] if r.ids else None, text=r.title or None) for r in listed])
        src = self.root / work.home / "src"
        if src.is_dir():
            items = from_source(src)
            refs = []
            for item in items:
                rid = f"arxiv:{item.arxiv}" if item.arxiv else f"doi:{item.doi}" if item.doi else None
                if not rid:
                    self._queries[item.text] = bib_query(item)
                refs.append(Reference(id=rid, text=item.text))
            work.add_references(refs)

    def _classify(self, works: list[Work]) -> None:
        """Give each work an MSC code or an arXiv category where either is to be had, for the subject filter."""
        for w in works:
            if w.msc:
                continue
            for ident in list(w.ids):
                if norm(ident).partition(":")[0] not in ("doi", "arxiv", "zbl"):
                    continue
                try:
                    zb = self.c.zbmath.by_id(ident)
                except ServiceError:
                    zb = None
                if zb:
                    w.add_ids(zb.ids)
                    w.fill(zb.title, zb.authors, zb.year, zb.msc)
                    w.sources["zbmath"] = zb.document
                    break
        for w in works:
            if w.msc or w.arxiv:
                continue
            # zbMATH has no record under this identifier, often a book cited by one edition's DOI: OpenAlex gives the title and authors, and perhaps an arXiv number, and zbMATH is asked by title
            oa = None
            if w.doi:
                try:
                    oa = self.c.openalex.by_id(f"doi:{w.doi}")
                except ServiceError:
                    oa = None
            if oa:
                w.add_ids(oa.ids)
                w.fill(oa.title, oa.authors, oa.year)
                w.open_pdf = w.open_pdf or oa.open_pdf
                w.sources["openalex"] = oa.openalex
            if w.title and w.authors:
                try:
                    zb = self.c.zbmath.by_title(w.title, w.authors, w.year)
                except ServiceError:
                    zb = None
                if zb:
                    w.add_ids(zb.ids)
                    w.fill(zb.title, zb.authors, zb.year, zb.msc)
                    w.sources["zbmath"] = zb.document
        pending = [w.arxiv for w in works if not w.msc and w.arxiv and not w.arxiv_category]
        if pending:
            try:
                cats = self.c.arxiv.categories([a for a in pending if a])
            except ServiceError:
                cats = {}
            for w in works:
                if not w.msc and w.arxiv:
                    w.arxiv_category = w.arxiv_category or cats.get(norm("arxiv:" + w.arxiv).partition(":")[2], "")

    # --- the walk -----------------------------------------------------------------------------------

    def _cited(self, bib: dict[str, BibEntry], cited: list[str], expand: bool) -> list[Work]:
        """The cited works, identified and filled, with their references read when they are to be expanded."""
        self.log(f"identifying {len(cited)} cited works")
        for ck in cited:
            entry = bib.get(ck)
            w = self.depth_one(ck, entry) if entry is not None else None
            if w is not None:
                self._remember(w)
        for w in self._works():
            self.enrich(w, expand=expand)
            self._remember(w)
        return self._works()

    def _next(self, frontier: list[Work], depth: int) -> list[Work]:
        """The works the frontier cites that are not yet known, identified and classified, at `depth`."""
        self.log(f"depth {depth}: reading the references of {len(frontier)} works")
        fresh: list[Work] = []
        seen: dict[str, Work] = {}
        for i, w in enumerate(sorted(frontier, key=lambda x: (-len(x.reached_from), x.key)), 1):
            self.log(f"  {i}/{len(frontier)} {w.ids[0]}: {len(w.references)} references")
            own = {norm(x) for x in w.ids}
            for ref in w.references:
                cand = self.reference(ref)
                if cand is None or any(norm(x) in own for x in cand.ids):
                    continue
                target = self._known(cand.ids) or next((seen[norm(x)] for x in cand.ids if norm(x) in seen), None)
                if target is not None:
                    if w.key not in target.reached_from:
                        target.reached_from.append(w.key)
                    continue
                gone = next((self._excluded_by[norm(x)] for x in cand.ids if norm(x) in self._excluded_by), None)
                if gone is not None:
                    gone["cited_by"] += 1
                    continue
                cand.depth = depth
                cand.reached_from = [w.key]
                fresh.append(cand)
                for x in cand.ids:
                    seen[norm(x)] = cand
        self.log(f"depth {depth}: classifying {len(fresh)} works by subject")
        self._classify(fresh)
        return fresh

    def survey(self, bib: dict[str, BibEntry], cited: list[str]) -> Survey:
        """Count what the cited works cite, by MSC family and arXiv category; nothing is kept and no record is written."""
        first = self._cited(bib, cited, expand=True)
        fresh = self._next(first, 2)
        # classifying can show two references name one work, or a cited one
        found: dict[int, Work] = {}
        for c in fresh:
            if self._known(c.ids) is None:
                w = self._remember(c)
                found[id(w)] = w
        references = [w for w in found.values() if w.depth == 2]
        return Survey(
            cited={k: dict(v.most_common()) for k, v in M.tally([(w.msc, w.arxiv_category) for w in first]).items()},
            references={
                k: dict(v.most_common()) for k, v in M.tally([(w.msc, w.arxiv_category) for w in references]).items()
            },
            counts={
                "cited": len(first),
                "references": len(references),
                "possible": len(self.possible),
                "unidentified": len(self.unidentified),
                "references_unknown": sum(1 for w in first if not w.references_known),
                "lookups": self.lookups,
            },
        )

    def run(self, settings: Settings, bib: dict[str, BibEntry], cited: list[str], bib_texts: list[str]) -> Plan:
        if settings.depth < 1:
            raise PlanRefused("[crawl] depth must be at least 1: depth 1 is the bibliography itself")
        subjects = M.families(settings.subjects)
        if settings.depth > 1 and not subjects:
            raise PlanRefused('set subjects under [crawl] to MSC families such as ["14N"] to plan past depth 1')
        frontier = self._cited(bib, cited, expand=settings.depth > 1)
        for d in range(2, settings.depth + 1):
            fresh = self._next(frontier, d)
            kept: list[Work] = []
            for c in fresh:
                if self._known(c.ids) is None:  # classifying can show a reference names a work already kept
                    verdict = M.passes(c.msc, c.arxiv_category, subjects, settings.categories)
                    if not verdict:
                        why = (
                            "outside the subjects"
                            if c.msc
                            else "arXiv category not in categories"
                            if c.arxiv_category
                            else "no MSC code and no arXiv category"
                        )
                        out = {
                            "id": c.ids[0],
                            "title": c.title or c.sources.get("text", ""),
                            "depth": d,
                            "why": why,
                            "cited_by": len(c.reached_from),
                            "msc": c.msc[:3],
                            "category": c.arxiv_category,
                        }
                        self.excluded.append(out)
                        for x in c.ids:
                            self._excluded_by[norm(x)] = out
                        continue
                    c.home = home_of(c.ids[0])
                kept.append(self._remember(c))
            frontier = [w for w in {id(w): w for w in kept}.values() if w.depth == d]
            self.log(f"depth {d}: {len(frontier)} works kept, {len(fresh) - len(kept)} excluded")
            for c in frontier:
                self.enrich(c, expand=d < settings.depth)
                self._remember(c)
            frontier = [w for w in self._works() if w.depth == d]
        return self._finish(settings, subjects, bib_texts)

    def _finish(self, settings: Settings, subjects: list[str], bib_texts: list[str]) -> Plan:
        works = self._works()
        for w in works:
            # a citing work may have been merged since, under a key of higher rank
            keys = [self.alias[norm(k)].key if norm(k) in self.alias else k for k in w.reached_from]
            w.reached_from = [k for k in dict.fromkeys(keys) if k != w.key]
        ordered = sorted(works, key=lambda w: (w.depth, -len(w.reached_from), w.key))
        for w in ordered:
            previous = load_work(self.root / w.home / "work.json")
            if previous and previous.download:
                w.download = previous.download  # a re-plan keeps what was already fetched
            elif (self.root / w.home / "src").is_dir() or (self.root / w.home / "paper.pdf").is_file():
                # put there by `loom digest fetch` or `loom refs add`, which count as downloads the same way
                kind = "source" if (self.root / w.home / "src").is_dir() else "pdf"
                w.download = {"kind": kind, "fetched": "before the crawl"}
            save_work(self.root, w)
        downloadable = [w for w in ordered if w.downloadable]
        selected = downloadable[: max(0, settings.cap)]
        on_disk = [w for w in selected if w.download.get("fetched")]
        to_fetch = [w for w in selected if not w.download.get("fetched")]
        counts = {
            "works": len(ordered),
            "downloadable": len(downloadable),
            "from_arxiv": sum(1 for w in downloadable if w.downloadable == "source"),
            "open_copies": sum(1 for w in downloadable if w.downloadable == "pdf"),
            "metadata_only": len(ordered) - len(downloadable),
            "excluded": len(self.excluded),
            "references_unknown": sum(1 for w in ordered if w.depth < settings.depth and not w.references_known),
            "lookups": self.lookups,
            "strong_by_lookup": sum(1 for w in ordered if w.reached_by == "lookup"),
            "possible": len(self.possible),
            "unidentified": len(self.unidentified),
            "selected": len(selected),
            "already_fetched": len(on_disk),
            "over_cap": max(0, len(downloadable) - max(0, settings.cap)),
        }
        sources = sum(1 for w in to_fetch if w.downloadable == "source")
        pdfs = len(to_fetch) - sources
        estimate = {
            "bytes": float(
                sources * _average(ordered, "source", AVG_SOURCE) + pdfs * _average(ordered, "pdf", AVG_PDF)
            ),
            "seconds": sources * SOURCE_SECONDS + pdfs * PDF_SECONDS,
        }
        return Plan(
            record=PLAN,
            made=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            fingerprint=fingerprint(settings, bib_texts),
            settings=settings.as_dict(),
            subjects=subjects,
            categories=sorted(set(settings.categories)),
            order=[w.key for w in ordered],
            homes={w.key: w.home for w in ordered},
            selected=[w.key for w in selected],
            counts=counts,
            estimate=estimate,
            excluded=sorted(self.excluded, key=lambda e: (e["depth"], -e["cited_by"], e["id"])),
            possible=self.possible,
            unidentified=self.unidentified,
        )


def _counted(counts: dict[str, int], limit: int = 12) -> str:
    return " · ".join(f"{k} {n}" for k, n in list(counts.items())[:limit]) or "none"


def summary(plan: Plan) -> list[str]:
    """The plan as a person reads it before deciding to fetch."""
    c, e, s = plan.counts, plan.estimate, plan.settings
    lines = [
        f"depth {s['depth']} · subjects {' '.join(plan.subjects) or 'none'} · categories {' '.join(plan.categories) or 'none'} · cap {s['cap']}",
        f"  {c['works']} works: {c['downloadable']} downloadable (arXiv {c['from_arxiv']}, open copies {c['open_copies']}), {c['metadata_only']} metadata only, {c['excluded']} excluded",
    ]
    outside = Counter(
        M.family(x["msc"][0]) for x in plan.excluded if x["why"] == "outside the subjects" and x.get("msc")
    )
    if outside:
        lines.append(f"  excluded, outside the subjects: {_counted(dict(outside.most_common()), 8)}")
    uncategorised = Counter(x["category"] for x in plan.excluded if x["why"] == "arXiv category not in categories")
    if uncategorised:
        lines.append(
            f"  excluded, no MSC code and a category not listed: {_counted(dict(uncategorised.most_common()), 8)}"
        )
    neither = sum(1 for x in plan.excluded if x["why"] == "no MSC code and no arXiv category")
    if neither:
        lines.append(f"  excluded, no MSC code and no arXiv category: {neither}")
    if c["references_unknown"]:
        lines.append(
            f"  references not yet known for {c['references_unknown']} works (no index lists them; they are read from a source once it is fetched)"
        )
    size = f"{e['bytes'] / 1e9:.1f} GB" if e["bytes"] >= 1e9 else f"{e['bytes'] / 1e6:.0f} MB"
    minutes = e["seconds"] / 60
    lines.append(
        f"  to fetch: {c['selected'] - c['already_fetched']} ({c['already_fetched']} already on disk) · ~{size} · ~{minutes:.0f} min · {c['lookups']} lookups made"
    )
    if c["over_cap"]:
        lines.append(
            f"  over the cap: {c['over_cap']} downloadable works would be left out; raise cap under [crawl] to include them"
        )
    lines.append(
        f"  identified by lookup: {c['strong_by_lookup']} strong (followed), {c['possible']} possible (listed, not followed), {c['unidentified']} unidentified"
    )
    lines.append("  the excluded, possible and unidentified works are listed in refs/crawl/plan.json")
    return lines


def survey_summary(survey: Survey) -> list[str]:
    """A survey as a person reads it before choosing subjects and categories."""
    c, cited, refs = survey.counts, survey.cited, survey.references
    lines = [
        f"the {c['cited']} cited works, by primary MSC family: {_counted(cited['primary'])}",
        f"the {c['references']} works they cite, by primary MSC family: {_counted(refs['primary'])}",
        f"  by any of their codes: {_counted(refs['any'])}",
        f"  with no MSC code, by arXiv category: {_counted(refs['categories'])}",
        f"  with neither: {refs['neither'].get('works', 0)}",
        f"  not counted: {c['possible']} possible matches, {c['unidentified']} references not identified",
    ]
    if c["references_unknown"]:
        lines.append(
            f"  references not yet known for {c['references_unknown']} cited works (no index lists them; they are read from a source once it is fetched)"
        )
    return lines
