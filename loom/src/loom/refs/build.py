"""`loom library update`: everything a machine can make about the works a quilt cites (plan 0.12 §4.4, plan 0.18.5).

Resolve, fetch, extract and map, each a no-op where its work is done, so re-running after the bibliography grows does the new entry alone. The report says what the run did, and what stands in each work's way under the command that clears it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from loom.refs.fetch import Fetched, fetch_work, identifier_for, work_dir
from loom.refs.identity import declared
from loom.refs.pages import read_map, storage_root
from loom.refs.resolve import Resolver, ResolveRefused, load, query_for, save
from loom.scan.bib import BibEntry
from loom.scan.scan import ScanResult

if TYPE_CHECKING:
    from loom.cli.report import Group, Report
    from loom.digest.extract import ExtractReport
    from loom.refs.resolve import Candidate
    from loom.refs.scan import ScanReport

#: Called as each step reaches a work: (stage, citekey, n, total), n counting from 1.
OnProgress = Callable[[str, str, int, int], None]
#: The steps of `loom library update`, in the order they run: `gather` reads the bibliography, the rest act per work.
STEPS = ("gather", "resolve", "fetch", "extract", "map")
#: The steps `build_refs` takes, one work at a time.
WORK_STEPS = STEPS[1:]
#: The command that grants this run the network, and the line that grants it for good.
ONLINE = "loom library update --online, or set online = true under [library] in config.toml"


@dataclass
class WorkState:
    """What the quilt holds for one cited work, after whatever this run did to it."""

    citekey: str
    cited_by: int = 0
    #: The work's primary citekey when this entry is another document of it (`refs.scan.versions_of`); '' for a primary.
    version_of: str = ""
    pages: int = 0
    sections: int = 0
    declared: bool = False  # the entry states an arXiv id, the one kind of identifier a source is fetched on
    identified: bool = False  # the entry states some global identifier: a DOI, an eprint, an MR or zbl number
    candidate: str = ""
    source: bool = False
    pdf: bool = False
    digest: bool = False
    fetched: Fetched | None = None
    extract_error: str = ""
    #: Results the author verified that a fresh extraction dropped and this run put back (`--redo` rewrites the digest file).
    restored: list[str] = field(default_factory=list)
    #: Of those, the ones the fresh extraction now states differently, for the author to look at again.
    contradicted: list[str] = field(default_factory=list)
    #: The author's standing claim that this work has no document to hold, or '' -- `digests/unreadable.json`.
    unreadable: str = ""
    #: The candidates this run's lookup found, best first; None when it asked nothing.
    lookup: list[Candidate] | None = None
    #: What extraction said about the digest this run wrote; None when it wrote none.
    extraction: ExtractReport | None = None
    #: The new digest's diagnostics as `tally` counts them; '' when this run wrote no digest.
    lint: str = ""
    #: Whether this run wrote the page text and section map; `map_error` says why it could not, `map_warning` what to look at.
    remapped: bool = False
    map_error: str = ""
    map_warning: str = ""

    @property
    def needs_a_person(self) -> str:
        """Why a person has to look at this work, or '' when nobody does."""
        if self.fetched is not None and self.fetched.discarded:
            return "wrong title on arrival"
        if not (self.source or self.pdf):
            return "no artifact and no identifier anyone will serve"
        return ""

    results: int = 0

    @property
    def thin(self) -> bool:
        """A digest with far fewer results than its paper has pages.

        Extraction counted as done in the first study run for two papers that yielded one result and none, out of 27 and 13: a declaration idiom the extractor missed. A mechanical digest is not correct by construction, and one this sparse is reported rather than counted.
        """
        return self.digest and self.pages >= 8 and self.results * 4 < self.pages

    @property
    def blocked(self) -> tuple[str, str]:
        """What stands between this work and a digest, and the command that clears it with `CITEKEY` standing for the work; ('', '') when nothing does.

        Blocked is about entering the digest, so a work with source and no PDF is not blocked -- it extracts, and what it then lacks is a page to read, which the lint reports. A work declared unreadable is never blocked either: the author has said there is nothing to wait for, and it is listed in its own section. Only the first cause is shown, because the second is not yet knowable.
        """
        if self.unreadable or self.digest:
            return ("", "")
        if self.extract_error:
            return (f"extraction failed: {self.extract_error}", "")
        if self.source:
            return ("", "")
        if self.fetched is not None and self.fetched.discarded:
            return (f"discarded on arrival: {self.fetched.discarded}", "")
        if self.declared or self.candidate:
            return ("source not fetched yet", "loom library update --online gets it from arXiv")
        if self.identified or self.pdf:
            # a DOI names the published article and a dropped PDF is a page image: neither is LaTeX, and only arXiv serves that
            return (
                "no arXiv id to fetch a source on",
                "loom library update --online looks for the preprint; or loom library add FILE --for CITEKEY with its LaTeX source",
            )
        return (
            "no identifier and no document",
            "loom library update CITEKEY --online looks it up; or add a doi or eprint to the entry; "
            "or loom library add FILE --for CITEKEY",
        )

    @property
    def needs_an_agent(self) -> bool:
        """Page text and no usable digest: the tail §4.3 leaves to the reading path, and any digest too thin to trust."""
        return self.pages > 0 and (self.thin or (not self.source and not self.digest))


@dataclass
class BuildReport:
    """What one `loom library update` did, and what is left."""

    works: list[WorkState] = field(default_factory=list)
    #: The steps this run took, in order.
    steps: tuple[str, ...] = WORK_STEPS
    #: The gathering that opened the run, or None when it did not gather.
    scan: ScanReport | None = None
    looked_up: int = 0
    recorded: int = 0
    lookup_errors: list[str] = field(default_factory=list)
    resolve_off: bool = False
    fetch_off: bool = False
    #: Citekeys whose digest this run wrote; the works already digested are not listed again.
    entered: list[str] = field(default_factory=list)

    @property
    def declared(self) -> int:
        return sum(1 for w in self.works if w.declared)

    @property
    def with_candidate(self) -> int:
        return sum(1 for w in self.works if not w.declared and w.candidate)

    @property
    def fetchable(self) -> int:
        """Works a fetch would actually go and get: an identifier of their own, and no source on disk yet."""
        return sum(1 for w in self.works if not w.source and (w.declared or w.candidate))

    @property
    def unresolved(self) -> int:
        return sum(1 for w in self.works if not w.declared and not w.candidate)

    @property
    def lookable(self) -> int:
        """Works a lookup would actually ask about: no arXiv id, no candidate, and no source on disk."""
        return sum(1 for w in self.works if not (w.declared or w.candidate or w.source))

    @property
    def sources(self) -> int:
        return sum(1 for w in self.works if w.source)

    @property
    def pdfs(self) -> int:
        return sum(1 for w in self.works if w.pdf)

    @property
    def digests(self) -> int:
        return sum(1 for w in self.works if w.digest)

    @property
    def mapped(self) -> int:
        return sum(1 for w in self.works if w.pages)

    @property
    def pages(self) -> int:
        return sum(w.pages for w in self.works)

    @property
    def discarded(self) -> list[WorkState]:
        return [w for w in self.works if w.fetched is not None and w.fetched.discarded]

    @property
    def blocked(self) -> list[WorkState]:
        """Works that did not enter the digest and are waiting on something nameable."""
        return [w for w in self.works if w.blocked[0]]

    @property
    def unreadable(self) -> list[WorkState]:
        """Works the author has declared there is no document for; listed and never retried."""
        return [w for w in self.works if w.unreadable]

    @property
    def for_a_person(self) -> list[WorkState]:
        return [w for w in self.works if w.needs_a_person]

    @property
    def for_an_agent(self) -> list[WorkState]:
        return [w for w in self.works if w.needs_an_agent]

    def report(self) -> Report:
        """The run as a report: a verdict, a count per step taken, then what this run did, what failed and why, and what stands in each work's way under the command that clears it.

        A blocked work is listed under its reason, the command that clears it given once for the group with `CITEKEY` standing for the work; a reason that is the work's own (an extraction error) stays beside its citekey. What waits for a person or an agent is counted and left to `loom library`.
        """
        from loom.cli.report import Group, Item, Report, counted, table

        n = len(self.works)
        ran = self.steps
        sections = sum(1 for x in self.works if x.sections)
        rows = []
        if "resolve" in ran:
            rows.append(
                (
                    "resolved",
                    str(n),
                    f"entries: {self.declared} state an arXiv id, {self.with_candidate} have a strong candidate, "
                    f"{self.unresolved} have neither" + (" (offline)" if self.resolve_off else ""),
                )
            )
        if "fetch" in ran:
            rows.append(
                (
                    "fetched",
                    str(self.sources),
                    f"{'source' if self.sources == 1 else 'sources'} and {counted(self.pdfs, 'PDF')}; "
                    f"{len(self.discarded)} rejected on the title check" + (" (offline)" if self.fetch_off else ""),
                )
            )
        if "extract" in ran:
            rows.append(
                (
                    "extracted",
                    str(self.digests),
                    "digests" + (f", {self.recorded} results recorded" if self.recorded else ""),
                )
            )
        if "map" in ran:
            rows.append(
                ("mapped", str(self.mapped), f"works from PDF text, {self.pages} pages, sections found for {sections}")
            )
        width = max((len(r[1]) for r in rows), default=0)
        lines = table((label, count.rjust(width), text) for label, count, text in rows)
        groups = list(self.scan.report().groups) if self.scan is not None else []
        if self.scan is not None:
            lines.insert(0, f"gathered: {self.scan.report().verdict}")
        # a step that was offline with nothing to do says nothing; one with work waiting says how to go online
        off: list[Item] = []
        if self.resolve_off and self.lookable:
            off.append(Item(f"{counted(self.lookable, 'entry', 'entries')} could be looked up"))
        if self.fetch_off and self.fetchable:
            off.append(Item(f"{counted(self.fetchable, 'work')} could be fetched"))
        groups.append(Group("needs the network", off, limit=None, next=ONLINE if off else None))
        groups += self._this_run()
        thin = sorted((x for x in self.works if x.thin), key=lambda x: x.citekey.lower())
        groups.append(
            Group("too thin to trust", [Item(f"{x.results} results, {x.pages} pages", key=x.citekey) for x in thin])
        )
        restored = sorted((x for x in self.works if x.restored), key=lambda x: x.citekey.lower())
        groups.append(
            Group(
                "verified results kept through the new extraction",
                [Item(", ".join(x.restored), key=x.citekey) for x in restored],
            )
        )
        contradicted = sorted(rid for x in restored for rid in x.contradicted)
        groups.append(
            Group(
                "stated differently by the new extraction, so check again",
                [Item("", key=rid, fixes=[f"loom library why {rid}"]) for rid in contradicted],
                problem=True,
            )
        )
        by_reason: dict[tuple[str, str], list[Item]] = {}
        # blocked is about entering the digest, which a run of the map step alone does not attempt
        for x in self.blocked if {"resolve", "fetch", "extract"} & set(ran) else []:
            missing, how = x.blocked
            own = next((p for p in OWN_REASON if missing.startswith(p + ": ")), None)
            if own is not None:
                # the reason is the work's own, so it stays beside its citekey
                by_reason.setdefault(OWN_REASON[own], []).append(Item(missing.removeprefix(own + ": "), key=x.citekey))
            else:
                by_reason.setdefault((missing, how), []).append(Item("", key=x.citekey))
        for (missing, how), items in sorted(by_reason.items(), key=lambda g: (-len(g[1]), g[0][0])):
            items.sort(key=lambda i: (i.key or "").lower())
            cut = len(items) > LISTED
            groups.append(
                Group(
                    f"blocked: {missing}",
                    items,
                    limit=LISTED,
                    problem=True,
                    next=(f"{how}; {EVERY}" if how else EVERY) if cut else (how or None),
                )
            )
        groups.append(
            Group(
                "declared unreadable, not retried",
                [Item(x.unreadable, key=x.citekey) for x in sorted(self.unreadable, key=lambda x: x.citekey.lower())],
            )
        )
        person, agent = self.for_a_person, self.for_an_agent
        waiting = []
        if person or agent:
            waiting.append(
                Group(
                    "left for you and for an agent",
                    [
                        Item(
                            f"{counted(len(person), 'work')} need{'s' if len(person) == 1 else ''} you, {len(agent)} an agent"
                        )
                    ],
                    counted=False,
                    next="loom library lists them",
                )
            )
        blocked = len(self.blocked) if {"resolve", "fetch", "extract"} & set(ran) else 0
        failed = self.failures
        verdict = (
            f"{self.digests} of {counted(n, 'work')} digested"
            + (f"; this run {self.did}" if self.did else ", nothing new this run")
            + (f"; {failed} failed" if failed else "")
            + (f"; {blocked} blocked" if blocked else "")
            + f"; {len(person)} need{'s' if len(person) == 1 else ''} you, {len(agent)} an agent"
        )
        notes = (
            ["a candidate becomes the work's identity when you add its field to your own bibliography entry"]
            if any(w.lookup for w in self.works)
            else []
        )
        return Report(
            verdict,
            ok=not (blocked or failed or person or agent or thin or contradicted),
            lines=lines,
            groups=[g for g in groups if g.items] + waiting,
            notes=notes,
            data={
                "steps": list(ran),
                "looked_up": self.looked_up,
                "recorded": self.recorded,
                "entered": list(self.entered),
                "lookup_errors": list(self.lookup_errors),
                "scan": self.scan.report().to_json() if self.scan is not None else None,
                "works": [_row(w) for w in self.works],
            },
        )

    @property
    def did(self) -> str:
        """What this run made, `looked up 2, fetched 1 and extracted 1`; '' when it made nothing."""
        from loom.cli.report import counted

        made = [
            (f"looked up {sum(1 for w in self.works if w.lookup is not None)}", "resolve"),
            (
                f"fetched {sum(1 for w in self.works if w.fetched is not None and (w.fetched.source or w.fetched.pdf))}",
                "fetch",
            ),
            (f"extracted {len(self.entered)}", "extract"),
            (f"mapped {sum(1 for w in self.works if w.remapped)}", "map"),
        ]
        done = [text for text, step in made if step in self.steps and not text.endswith(" 0")]
        if self.scan is not None and self.scan.added:
            done.insert(0, f"gathered {counted(len(self.scan.added), 'entry', 'entries')}")
        return ", ".join(done[:-1]) + (" and " if len(done) > 1 else "") + done[-1] if done else ""

    @property
    def failures(self) -> int:
        """What this run tried and could not do and no blocked group lists: a lookup, a fetch refused, a map.

        A discarded fetch and a failed extraction are each a work's blocked reason, counted there once.
        """
        refused = sum(1 for w in self.works if w.fetched is not None and w.fetched.refused)
        return len(self.lookup_errors) + refused + sum(1 for w in self.works if w.map_error)

    def _this_run(self) -> list[Group]:
        """The groups saying what this run did to each work: looked up, fetched, extracted, mapped, and each failure with its reason."""
        from loom.cli.report import Group, Item, counted

        def by_key(items: list[Item]) -> list[Item]:
            return sorted(items, key=lambda i: (i.key or "").lower())

        looked = [w for w in self.works if w.lookup is not None]
        found: list[Item] = []
        for w in looked:
            for c in (w.lookup or [])[:1]:
                names = ", ".join(a.split(",")[0] for a in c.authors[:3]) + (" et al." if len(c.authors) > 3 else "")
                also = f" (also {', '.join(c.also)})" if c.also else ""
                found.append(
                    Item(
                        f"{w.citekey}: {c.strength} {c.confidence:.2f}  {c.source}  {c.title} — {names} {c.year}".rstrip(),
                        key=f"{c.id}{also}",
                    )
                )
        unmatched = [Item("", key=w.citekey) for w in looked if not w.lookup]
        fetched = [w for w in self.works if w.fetched is not None and not (w.fetched.refused or w.fetched.discarded)]
        got = []
        for w in fetched:
            assert w.fetched is not None
            what = " and ".join(x for x in ["source" if w.fetched.source else "", "PDF" if w.fetched.pdf else ""] if x)
            got.append(Item(f"{what or 'nothing new'}, on {w.fetched.via} {w.fetched.ident}", key=w.citekey))
        refused = [
            Item(w.fetched.refused, key=w.citekey) for w in self.works if w.fetched is not None and w.fetched.refused
        ]
        extracted: list[Item] = []
        noted: list[Item] = []
        for w in self.works:
            r = w.extraction
            if r is None:
                continue
            by = ", ".join(f"{k} {t}" for t, k in sorted(r.by_taxon.items(), key=lambda x: (-x[1], x[0])))
            numbering = (
                f"numbering from the paper's .aux, except {counted(r.emulated, 'unlabelled result')} counted by emulation"
                if r.numbering == "aux" and r.emulated
                else "numbering from the paper's .aux"
                if r.numbering == "aux"
                else "numbering emulated" + (f" (compile failed: {r.compile_error})" if r.compile_error else "")
            )
            total = sum(r.by_taxon.values())
            extracted.append(
                Item(
                    f"{counted(total, 'result')}"
                    + (f" ({by})" if by else "")
                    + f", {counted(r.sections, 'section')}; {numbering}; its lint: {w.lint or 'clean'}",
                    key=w.citekey,
                )
            )
            noted += [
                Item(f"environment {env} is not declared in this quilt; add {hint}", key=w.citekey)
                for env, hint in r.unknown_envs.items()
            ]
            noted += [Item(f"skipped {s}", key=w.citekey) for s in r.skipped]
        mapped = [
            Item(f"{counted(w.pages, 'page')}, {counted(w.sections, 'section')}", key=w.citekey)
            for w in self.works
            if w.remapped
        ]
        unmapped = [Item(w.map_error, key=w.citekey) for w in self.works if w.map_error]
        look = [Item(w.map_warning, key=w.citekey) for w in self.works if w.map_warning]
        return [
            Group("lookups that failed", [Item(e) for e in self.lookup_errors], problem=True, limit=None),
            Group("looked up: the best candidate for each", by_key(found)),
            Group(
                "looked up: no match",
                by_key(unmatched),
                next="loom library add FILE --for CITEKEY files a document you hold" if unmatched else None,
            ),
            Group("not fetched", by_key(refused), problem=True, limit=None),
            Group("fetched", by_key(got)),
            Group("extracted", by_key(extracted)),
            Group("noted while extracting", by_key(noted), limit=None),
            Group("not mapped", by_key(unmapped), problem=True, limit=None),
            Group("mapped, to look at", by_key(look), limit=None),
            Group("mapped", by_key(mapped)),
        ]

    def lines(self) -> list[str]:
        """The report's text, line by line."""
        return self.report().render().split("\n")


#: Blocked reasons that differ per work, printed beside each citekey under one heading and fix.
OWN_REASON = {
    "extraction failed": ("extraction failed", ""),
    "discarded on arrival": (
        "fetched and discarded: its title did not match the entry",
        "look at it; loom library add FILE --for CITEKEY files the right document",
    ),
}
#: How many works a group of the report lists before it counts the rest.
LISTED = 12
#: The command that lists every work, named where a group is cut.
EVERY = "loom library update --dry-run --json lists every work"


def _row(w: WorkState) -> dict[str, object]:
    """One work's line of the report's JSON."""
    from dataclasses import asdict

    r = w.extraction
    return {
        "citekey": w.citekey,
        "cited_by": w.cited_by,
        "declared": w.declared,
        "candidate": w.candidate,
        "source": w.source,
        "pdf": w.pdf,
        "digest": w.digest,
        "pages": w.pages,
        "sections": w.sections,
        "candidates": None if w.lookup is None else [asdict(c) | {"strength": c.strength} for c in w.lookup],
        "fetched": None
        if w.fetched is None
        else {"source": w.fetched.source, "pdf": w.fetched.pdf, "via": w.fetched.via, "identifier": w.fetched.ident},
        "discarded": w.fetched.discarded if w.fetched else "",
        "refused": w.fetched.refused if w.fetched else "",
        "extraction": None
        if r is None
        else {
            "results": sum(r.by_taxon.values()),
            "by_taxon": dict(r.by_taxon),
            "sections": r.sections,
            "uses": r.uses,
            "numbering": r.numbering,
            "emulated": r.emulated,
            "requires": list(r.requires),
            "skipped": list(r.skipped),
            "lint": w.lint,
        },
        "extract_error": w.extract_error,
        "mapped": w.remapped,
        "map_error": w.map_error,
        "blocked": w.blocked[0],
        "unreadable": w.unreadable,
        "needs_a_person": w.needs_a_person,
        "needs_an_agent": w.needs_an_agent,
        "restored": list(w.restored),
    }


def cited_counts(result: ScanResult) -> dict[str, int]:
    """How many of the author's own keys cite each work; the order §10 extracts in."""
    keys: dict[str, set[str]] = {}
    for c in result.edges.cites:
        if c.file in result.assembly.digest_files:
            continue  # the cited papers' own citations are not demand from this quilt
        # keys, not \cite commands: the viewer counts citing keys, and one column saying 7 beside another saying 4 for
        # the same work is two numbers under one word
        keys.setdefault(c.citekey, set()).add(c.src)
    return {ck: len(srcs) for ck, srcs in keys.items()}


def _has_source(root: Path, entry: BibEntry) -> bool:
    src = work_dir(root, entry) / "src"
    return src.is_dir() and any(src.rglob("*.tex"))


def main_tex(root: Path, entry: BibEntry) -> Path | None:
    """The source file to extract from: the one declaring `\\documentclass`, preferring a shallow path and a conventional name."""
    src = work_dir(root, entry) / "src"
    if not src.is_dir():
        return None
    found: list[Path] = []
    for path in sorted(src.rglob("*.tex")):
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:100_000]
        except OSError:
            continue
        if "\\documentclass" in head or "\\documentstyle" in head:
            found.append(path)
    if not found:
        return None
    pref = ("main.tex", "ms.tex", "paper.tex", "article.tex")
    found.sort(key=lambda p: (p.name.lower() not in pref, len(p.relative_to(src).parts), p.name.lower()))
    return found[0]


def survey(result: ScanResult) -> list[WorkState]:
    """What the quilt holds for every cited work, before anything is fetched; reads disk only."""
    from loom.refs.scan import primary_of
    from loom.refs.unreadable import declarations

    root = result.quilt.root
    counts = cited_counts(result)
    declared_unreadable = declarations(root, "unreadable")
    tops = primary_of(result.bib)
    out: list[WorkState] = []
    for ck in sorted(set(result.bib) | set(counts)):
        entry = result.bib.get(ck)
        if entry is None:
            continue
        ident, via = identifier_for(root, entry)
        home = work_dir(root, entry)
        m = read_map(home)
        from loom.refs.proposals import load_results

        out.append(
            WorkState(
                citekey=ck,
                cited_by=counts.get(ck, 0),
                version_of=tops.get(ck, ""),
                pages=m.pages if m else 0,
                sections=len(m.sections) if m else 0,
                results=sum(1 for r in load_results(root, ck).values() if r.cls == "mechanical"),
                declared=via == "declared",
                identified=bool(declared(entry)),
                candidate=ident or "" if via == "candidate" else "",
                source=_has_source(root, entry),
                pdf=(home / "paper.pdf").is_file(),
                digest=(root / "digests" / f"{ck}.tex").is_file(),
                unreadable=(d.why if (d := declared_unreadable.get(ck)) else ""),
            )
        )
    # cited works first, most-cited first: 15 of relloc's 22 are cited, and the other 7 are not worth a page yet
    out.sort(key=lambda w: (-w.cited_by, w.citekey))
    return out


def _each(progress: OnProgress | None, stage: str, works: list[WorkState]) -> Iterator[WorkState]:
    """Each of `works`, telling `progress` before it is worked on."""
    for i, w in enumerate(works, 1):
        if progress is not None:
            progress(stage, w.citekey, i, len(works))
        yield w


def _resolve_step(
    result: ScanResult, works: list[WorkState], report: BuildReport, refresh: bool, progress: OnProgress | None = None
) -> None:
    """Ask the two services for identifiers, for cited entries that declare none and have no answer on disk."""
    cfg = result.quilt.config
    if not cfg.online:
        report.resolve_off = True
        return
    root = result.quilt.root
    resolver = Resolver(cache=storage_root(root) / "cache" / "resolve", contact=cfg.contact, refresh=refresh)
    for w in _each(progress, "resolve", works):
        entry = result.bib[w.citekey]
        # A PDF on disk is not a reason to stop looking. A source is strictly better -- verbatim statements, real
        # numbers, internal edges -- and skipping here made the order of two commands decide which artifact a work
        # ended up with: ingest the PDFs first and loom never asked for the source (§3, derive eagerly and in full).
        if w.declared or w.source:
            continue
        if load(root, entry) and not refresh:
            continue  # an answer is on disk; asking again is what --redo is for
        try:
            found = resolver.candidates(query_for(entry))
        except ResolveRefused as exc:
            report.lookup_errors.append(f"{w.citekey}: {exc}")
            continue
        save(root, entry, found)
        w.lookup = found
        ident, via = identifier_for(root, entry)
        if via == "candidate" and ident:
            w.candidate = ident
    report.looked_up = resolver.requests


def _fetch_step(
    result: ScanResult,
    works: list[WorkState],
    report: BuildReport,
    candidates: bool,
    progress: OnProgress | None = None,
) -> None:
    """Fetch source and PDF for every work that has an identifier and no artifact; checks titles on arrival."""
    if not result.quilt.config.online:
        report.fetch_off = True
        return
    for w in _each(progress, "fetch", works):
        if w.source:
            continue  # a PDF alone is not enough: see `_resolve_step`
        from loom.refs.fetch import pdf_url

        if not (w.declared or w.candidate or (not w.pdf and pdf_url(result.bib[w.citekey]))):
            continue
        got = fetch_work(result.quilt, w.citekey, result.bib[w.citekey], pdf=True, allow_candidate=candidates)
        w.fetched = got
        # or-ed, not assigned: a PDF already on disk is not re-downloaded, so this fetch reporting none says nothing
        # about whether the work has one
        w.source, w.pdf = w.source or got.source, w.pdf or got.pdf


def _extract_step(
    result: ScanResult,
    works: list[WorkState],
    force: bool,
    progress: OnProgress | None = None,
    *,
    compile: bool = True,
    named: frozenset[str] = frozenset(),
) -> list[str]:
    """Extract a digest for every work whose source landed and whose digest is absent, or every one with a source under `force`.

    A version (`WorkState.version_of`) is extracted only when the author's text cites it or the run `named` it, so a second document of a work brings no second digest.
    """
    from loom.digest.extract import extract_digest

    root = result.quilt.root
    written: list[str] = []
    for w in _each(progress, "extract", [w for w in works if _extractable(w, named)]):
        if w.digest and not force:
            continue
        if not w.source:
            continue
        main = main_tex(root, result.bib[w.citekey])
        if main is None:
            w.extract_error = "no file in the source declares \\documentclass"
            continue
        try:
            text, w.extraction = extract_digest(result, w.citekey, main, engine=None, compile=compile)
        except Exception as exc:  # noqa: BLE001 -- one paper that will not build must not stop the other twenty
            w.extract_error = f"{type(exc).__name__}: {exc}"
            continue
        target = root / "digests" / f"{w.citekey}.tex"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        w.restored, w.contradicted = _restore_verified(result, w.citekey, text)
        w.digest = True
        written.append(w.citekey)
    return written


def _extractable(w: WorkState, named: frozenset[str]) -> bool:
    """Whether extraction may read `w`: a primary always, a version only when cited or named."""
    return not w.version_of or bool(w.cited_by) or w.citekey in named


def _restore_verified(result: ScanResult, citekey: str, text: str) -> tuple[list[str], list[str]]:
    """Put back every result the author verified that a fresh extraction of `citekey` left out, and keep the author's edits.

    The digest file is rewritten whole by an extraction, and a node `library verify` added to it, or an edit the author made to an extracted one, is the author's: losing it while `results.json` still says `verified` was the CLI study's defect 3. A mechanical result a person verified is put back as extracted, with their edit. A result the new extraction states differently from the author's record is put back as the author left it and listed, so the author can look again.
    """
    import re

    from loom.refs.proposals import VERIFIED, append_to_digest, load_results, rewrite_in_digest, state_of

    restored: list[str] = []
    contradicted: list[str] = []
    for r in load_results(result.quilt.root, citekey).values():
        # an extracted result is the extractor's own reading, which a fresh extraction is entitled to replace
        if state_of(r) != VERIFIED:
            continue
        edited = any(act.get("act") == "edited" for act in r.origin)
        present = re.search(r"\\label\{" + re.escape(r.id) + r"\}", text) is not None
        if present:
            if edited and rewrite_in_digest(result.quilt.root, citekey, r):
                restored.append(r.id)
                contradicted.append(r.id)
            continue
        append_to_digest(result.quilt.root, citekey, result.assembly.prefix_of(citekey), r)
        restored.append(r.id)
    return restored, contradicted


def _map_step(result: ScanResult, works: list[WorkState], force: bool, progress: OnProgress | None = None) -> None:
    """Write page text and the section map for every work with a PDF whose recorded map is not current."""
    from loom.refs.pages import MapRefused, is_current, write_map

    root = result.quilt.root
    for w in _each(progress, "map", works):
        home = work_dir(root, result.bib[w.citekey])
        pdf = home / "paper.pdf"
        if not pdf.is_file() or (is_current(home, pdf) and not force):
            continue
        try:
            m = write_map(home, pdf)
        except MapRefused as exc:
            w.map_error = str(exc)  # reported; the run carries on with the other twenty
            continue
        w.pages, w.sections, w.remapped = m.pages, len(m.sections), True
        if m.pages and m.chars / m.pages < 200:
            w.map_warning = "almost no text: probably a scan, which cannot be searched or quoted"
        elif m.suspect:
            w.map_warning = "too few sections for its length; the section map is a guess (a book?)"


def _record_step(result: ScanResult, works: list[WorkState], written: list[str]) -> int:
    """Write `results.json` for every digest that has none, and tally each new digest's lint; returns how many results were recorded.

    Derived, not incidental: a mechanical digest's results are a function of its `.tex`, so this runs for any digest lacking records rather than only for the ones this run extracted. That is what lets a quilt whose digests predate the reference layer gain them by running `loom library update` once.
    """
    from loom.refs.proposals import record_extracted, results_path

    root = result.quilt.root
    want = [w.citekey for w in works if w.digest and not results_path(root, w.citekey).is_file()]
    if not want and not written:
        return 0
    from loom.cli.diagnostics import tally
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    rescan = scan(load_quilt(root))
    for w in works:
        if w.citekey in written:
            rel = f"digests/{w.citekey}.tex"
            hits = [d for d in rescan.lint if any(loc.file == rel for loc in d.locations) or w.citekey in d.message]
            w.lint = tally(hits, None).replace(" in your documents", "") if hits else ""
    return sum(record_extracted(rescan, ck) for ck in dict.fromkeys([*written, *want]))


def build_refs(
    result: ScanResult,
    *,
    only: tuple[str, ...] = (),
    refresh: bool = False,
    candidates: bool = True,
    force: bool = False,
    compile: bool = True,
    steps: tuple[str, ...] = WORK_STEPS,
    progress: OnProgress | None = None,
) -> BuildReport:
    """Make everything about this quilt's cited works that a machine can make.

    Parameters
    ----------
    result : ScanResult
        The scanned quilt.
    only : tuple of str, default ()
        Citekeys to limit the run to; empty means every entry in the bibliography.
    refresh : bool, default False
        Ask the services again where an answer is already recorded (`--redo`).
    candidates : bool, default True
        Fetch on a resolver candidate where the entry declares no identifier (§4.3).
    force : bool, default False
        Re-extract a digest and re-map a PDF that are already current (`--redo`); verified results are kept.
    compile : bool, default True
        Compile each paper for its numbering; False emulates it (`--no-compile`).
    steps : tuple of str, default WORK_STEPS
        Which steps to run; the CLI's `--only` narrows this to one.
    progress : callable, optional
        Called as (stage, citekey, n, total) when each step reaches a work, n counting from 1.

    Returns
    -------
    BuildReport
        Counts per step and the two handoff lists.

    See Also
    --------
    survey : the same picture with nothing fetched.
    planned : what each step would act on, for a dry run.
    """
    works = survey(result)
    if only:
        works = [w for w in works if w.citekey in set(only)]
    report = BuildReport(works=works, steps=tuple(s for s in WORK_STEPS if s in steps))
    if "resolve" in steps:
        _resolve_step(result, works, report, refresh, progress)
    if "fetch" in steps:
        _fetch_step(result, works, report, candidates, progress)
    if "extract" in steps:
        report.entered = _extract_step(result, works, force, progress, compile=compile, named=frozenset(only))
        report.recorded = _record_step(result, works, report.entered)
    # Counted after extraction, not by the survey that opened the run: `survey` reads results.json before this run has
    # written it, and a count taken then called every one of sixteen fresh digests "too thin to trust".
    from loom.refs.proposals import load_results

    for w in works:
        w.results = sum(1 for r in load_results(result.quilt.root, w.citekey).values() if r.cls == "mechanical")
    if "map" in steps:
        _map_step(result, works, force, progress)
    return report


def planned(
    result: ScanResult,
    works: list[WorkState],
    *,
    steps: tuple[str, ...] = WORK_STEPS,
    redo: bool = False,
    candidates: bool = True,
    named: frozenset[str] = frozenset(),
) -> dict[str, list[str]]:
    """The citekeys each step of a run would act on, read from disk alone: a dry run's answer, which asks no service and writes nothing.

    Mirrors each step's own test of whether its work is done; what a fetch would bring is unknowable offline, so extraction counts the sources already on disk.
    """
    from loom.refs.fetch import pdf_url
    from loom.refs.pages import is_current

    root = result.quilt.root
    out: dict[str, list[str]] = {}
    if "resolve" in steps:
        out["resolve"] = [
            w.citekey for w in works if not (w.declared or w.source) and (redo or not load(root, result.bib[w.citekey]))
        ]
    if "fetch" in steps:
        out["fetch"] = [
            w.citekey
            for w in works
            if not w.source
            and (w.declared or (w.candidate and candidates) or (not w.pdf and pdf_url(result.bib[w.citekey])))
        ]
    if "extract" in steps:
        out["extract"] = [w.citekey for w in works if w.source and (redo or not w.digest) and _extractable(w, named)]
    if "map" in steps:
        out["map"] = []
        for w in works:
            home = work_dir(root, result.bib[w.citekey])
            if (home / "paper.pdf").is_file() and (redo or not is_current(home, home / "paper.pdf")):
                out["map"].append(w.citekey)
    return out


def plan_report(
    works: list[WorkState], plan: dict[str, list[str]], *, online: bool, scan: ScanReport | None = None
) -> Report:
    """A dry run as a report: what gathering would add, and the works each step would act on, the network's steps marked when this run is offline."""
    from loom.cli.report import Group, Item, Report, counted

    verbs = {"resolve": "look up", "fetch": "fetch", "extract": "extract", "map": "map"}
    parts = [f"{verbs[s]} {len(plan[s])}" for s in WORK_STEPS if s in plan]
    said = ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1] if parts else ""
    doing = [
        "gather the bibliography" if scan is not None else "",
        f"{said} of {counted(len(works), 'work')}" if said else "",
    ]
    verdict = "would " + ", then ".join(x for x in doing if x)
    groups = list(scan.report().groups) if scan is not None else []
    lines = [f"gathered: {scan.report().verdict}"] if scan is not None else []
    for step in WORK_STEPS:
        keys = sorted(plan.get(step, []), key=str.lower)
        network = step in ("resolve", "fetch") and not online
        groups.append(
            Group(
                f"would {verbs[step]}" + (", with the network" if network else ""),
                [Item("", key=ck) for ck in keys],
                limit=LISTED,
                next=ONLINE if network and keys else (EVERY if len(keys) > LISTED else None),
            )
        )
    return Report(
        verdict,
        dry_run=True,
        lines=lines,
        groups=[g for g in groups if g.items],
        data={
            "steps": [s for s in STEPS if s in plan or (s == "gather" and scan is not None)],
            "online": online,
            "would": {s: plan[s] for s in WORK_STEPS if s in plan},
            "scan": scan.report().to_json() if scan is not None else None,
            "works": [_row(w) for w in works],
        },
    )
