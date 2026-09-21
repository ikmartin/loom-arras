"""`loom refs build`: the one command that starts the digest (plan 0.12 §4.4).

Everything §3 calls *derived* is what this makes, and it makes all of it. The steps exist as their own verbs too -- for forcing work after a rule changes, and for running one step over what is already on disk -- but an author never runs them in order, because a four-command ritual is what §3's own rule forbids: anything a machine can derive, a machine derives eagerly, in full, and again whenever its inputs change.

Each step is a no-op where its work is done, so re-running after `refs.bib` changes resolves, fetches and extracts the new entry alone. The report's last two lines are the handoff: what needs a person, and what needs an agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from loom.refs.fetch import Fetched, fetch_work, identifier_for, work_dir
from loom.refs.pages import read_map, storage_root
from loom.refs.resolve import Resolver, ResolveRefused, load, query_for, save
from loom.scan.bib import BibEntry
from loom.scan.scan import ScanResult


@dataclass
class WorkState:
    """What the quilt holds for one cited work, after whatever this run did to it."""

    citekey: str
    cited_by: int = 0
    pages: int = 0
    sections: int = 0
    declared: bool = False
    candidate: str = ""
    source: bool = False
    pdf: bool = False
    digest: bool = False
    fetched: Fetched | None = None
    extract_error: str = ""
    #: The author's standing claim that this work has no document to hold, or '' -- `digests/unreadable.json`.
    unreadable: str = ""

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
        """What stands between this work and a digest, and the command that clears it; ('', '') when nothing does.

        Blocked is about entering the digest, so a work with source and no PDF is not blocked -- it extracts, and what it then lacks is a page to read, which the lint reports. A work declared unreadable is never blocked either: the author has said there is nothing to wait for, and it is listed in its own section. Only the first cause is shown, because the second is not yet knowable.
        """
        if self.unreadable or self.digest:
            return ("", "")
        if not (self.declared or self.candidate or self.pdf or self.source):
            return ("no identifier", f"loom refs resolve {self.citekey}, or add doi/eprint to the entry")
        if self.extract_error:
            return (f"extraction failed: {self.extract_error}", "")
        if not self.source:
            return (
                "no source to extract from",
                f"loom refs fetch {self.citekey}, or loom refs add {self.citekey} <FILE>",
            )
        return ("", "")

    @property
    def needs_an_agent(self) -> bool:
        """Page text and no usable digest: the tail §4.3 leaves to the reading path, and any digest too thin to trust."""
        return self.pages > 0 and (self.thin or (not self.source and not self.digest))


@dataclass
class BuildReport:
    """What one `loom refs build` did, and what is left."""

    works: list[WorkState] = field(default_factory=list)
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

    def lines(self) -> list[str]:
        """The report as printed: four counts, then the two handoff lines (§4.4)."""
        n = len(self.works)
        out = [
            f"resolved   {n} entries: {self.declared} declared, {self.with_candidate} strong candidates, {self.unresolved} unresolved"
            + ("  (lookup off)" if self.resolve_off else ""),
            f"fetched    {self.sources} sources, {self.pdfs} PDFs; {len(self.discarded)} rejected on the title check"
            + ("  (fetching off)" if self.fetch_off else ""),
            f"extracted  {self.digests} digests" + (f", {self.recorded} results recorded" if self.recorded else ""),
            f"mapped     {self.mapped} works from PDF text; {self.pages} pages; sections found for {sum(1 for w in self.works if w.sections)}",
        ]
        # a step that was off and had nothing to do says nothing; one that was off with work waiting says how to turn it on
        if self.resolve_off and self.unresolved:
            out.append(
                f"           {self.unresolved} entries could be looked up: set resolve = true under [refs] in config.toml, or pass --resolve, and run again"
            )
        if self.fetch_off and self.fetchable:
            out.append(
                f"           {self.fetchable} works could be fetched: set fetch = true under [refs] in config.toml, or pass --fetch, and run again"
            )
        thin = [w for w in self.works if w.thin]
        if thin:
            out.append(
                f"           {len(thin)} too thin to trust: "
                + ", ".join(f"{w.citekey} ({w.results} results, {w.pages} pages)" for w in thin[:3])
            )
        errors = [w for w in self.works if w.extract_error and not w.blocked[0]]
        if errors:
            out.append(f"           {len(errors)} failed to extract: {', '.join(w.citekey for w in errors[:3])}")
        # Three sections, because a count says a build happened and a list says what to do next (plan 0.13 §4). A work
        # the author has declared unreadable is in neither of the first two: it is not waiting for anything.
        if self.entered:
            out.append("")
            out.append(f"entered the digest  {len(self.entered)}: " + ", ".join(sorted(self.entered)[:8]))
        blocked = self.blocked
        if blocked:
            out.append("")
            out.append(f"blocked             {len(blocked)}")
            for w in blocked[:8]:
                missing, how = w.blocked
                out.append(f"  {w.citekey:<22}{missing:<34}{how}")
        unreadable = self.unreadable
        if unreadable:
            out.append("")
            out.append(f"declared unreadable {len(unreadable)}, not retried")
            for w in unreadable:
                out.append(f"  {w.citekey:<22}{w.unreadable}")
        out.append("")
        person, agent = self.for_a_person, self.for_an_agent
        out.append(f"needs you      {len(person):<3}loom refs match")
        out.append(f"needs an agent {len(agent):<3}works with pages and no digest")
        return out


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
    from loom.refs.unreadable import declarations

    root = result.quilt.root
    counts = cited_counts(result)
    declared_unreadable = declarations(root, "unreadable")
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
                pages=m.pages if m else 0,
                sections=len(m.sections) if m else 0,
                results=sum(1 for r in load_results(root, ck).values() if r.cls == "mechanical"),
                declared=via == "declared",
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


def _resolve_step(result: ScanResult, works: list[WorkState], report: BuildReport, refresh: bool) -> None:
    """Ask the two services for identifiers, for cited entries that declare none and have no answer on disk."""
    cfg = result.quilt.config
    if not cfg.resolve:
        report.resolve_off = True
        return
    root = result.quilt.root
    resolver = Resolver(cache=storage_root(root) / "cache" / "resolve", contact=cfg.contact, refresh=refresh)
    for w in works:
        entry = result.bib[w.citekey]
        # A PDF on disk is not a reason to stop looking. A source is strictly better -- verbatim statements, real
        # numbers, internal edges -- and skipping here made the order of two commands decide which artifact a work
        # ended up with: ingest the PDFs first and loom never asked for the source (§3, derive eagerly and in full).
        if w.declared or w.source:
            continue
        if load(root, entry) and not refresh:
            continue  # an answer is on disk; asking again is what --refresh is for
        try:
            found = resolver.candidates(query_for(entry))
        except ResolveRefused as exc:
            report.lookup_errors.append(f"{w.citekey}: {exc}")
            continue
        save(root, entry, found)
        ident, via = identifier_for(root, entry)
        if via == "candidate" and ident:
            w.candidate = ident
    report.looked_up = resolver.requests


def _fetch_step(result: ScanResult, works: list[WorkState], report: BuildReport, candidates: bool) -> None:
    """Fetch source and PDF for every work that has an identifier and no artifact; checks titles on arrival."""
    if not result.quilt.config.fetch:
        report.fetch_off = True
        return
    for w in works:
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


def _extract_step(result: ScanResult, works: list[WorkState], force: bool) -> list[str]:
    """Run `loom digest extract` on every work whose source landed and whose digest is absent."""
    from loom.digest.extract import extract_digest

    root = result.quilt.root
    written: list[str] = []
    for w in works:
        if w.digest and not force:
            continue
        if not w.source:
            continue
        main = main_tex(root, result.bib[w.citekey])
        if main is None:
            w.extract_error = "no file in the source declares \\documentclass"
            continue
        try:
            text, _report = extract_digest(result, w.citekey, main, engine=None, compile=True)
        except Exception as exc:  # noqa: BLE001 -- one paper that will not build must not stop the other twenty
            w.extract_error = f"{type(exc).__name__}: {exc}"
            continue
        target = root / "digests" / f"{w.citekey}.tex"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        w.digest = True
        written.append(w.citekey)
    return written


def _map_step(result: ScanResult, works: list[WorkState], force: bool) -> None:
    """Write page text and the section map for every work with a PDF whose recorded map is not current."""
    from loom.refs.pages import MapRefused, is_current, write_map

    root = result.quilt.root
    for w in works:
        home = work_dir(root, result.bib[w.citekey])
        pdf = home / "paper.pdf"
        if not pdf.is_file() or (is_current(home, pdf) and not force):
            continue
        try:
            m = write_map(home, pdf)
        except MapRefused:
            continue  # `loom refs map` reports why; the composite carries on with the other twenty
        w.pages, w.sections = m.pages, len(m.sections)


def _record_step(result: ScanResult, works: list[WorkState], written: list[str]) -> int:
    """Write `results.json` for every digest that has none; returns how many results were recorded.

    Derived, not incidental: a mechanical digest's results are a function of its `.tex`, so this runs for any digest lacking records rather than only for the ones this run extracted. That is what lets a quilt whose digests predate the reference layer gain them by running `loom refs build` once.
    """
    from loom.refs.proposals import record_extracted, results_path

    root = result.quilt.root
    want = [w.citekey for w in works if w.digest and not results_path(root, w.citekey).is_file()]
    if not want and not written:
        return 0
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    rescan = scan(load_quilt(root))
    return sum(record_extracted(rescan, ck) for ck in dict.fromkeys([*written, *want]))


def build_refs(
    result: ScanResult,
    *,
    only: tuple[str, ...] = (),
    refresh: bool = False,
    candidates: bool = True,
    force: bool = False,
    steps: tuple[str, ...] = ("resolve", "fetch", "extract", "map"),
) -> BuildReport:
    """Make everything about this quilt's cited works that a machine can make.

    Parameters
    ----------
    result : ScanResult
        The scanned quilt.
    only : tuple of str, default ()
        Citekeys to limit the run to; empty means every entry in the bibliography.
    refresh : bool, default False
        Ask the services again where an answer is already recorded.
    candidates : bool, default True
        Fetch on a resolver candidate where the entry declares no identifier (§4.3).
    force : bool, default False
        Re-extract a digest that is already present.
    steps : tuple of str, default ('resolve', 'fetch', 'extract', 'map')
        Which steps to run; the CLI's `--only` narrows this.

    Returns
    -------
    BuildReport
        Counts per step and the two handoff lists.

    See Also
    --------
    survey : the same picture with nothing fetched, which is what `loom refs match` reads.
    """
    works = survey(result)
    if only:
        works = [w for w in works if w.citekey in set(only)]
    report = BuildReport(works=works)
    if "resolve" in steps:
        _resolve_step(result, works, report, refresh)
    if "fetch" in steps:
        _fetch_step(result, works, report, candidates)
    if "extract" in steps:
        report.entered = _extract_step(result, works, force)
        report.recorded = _record_step(result, works, report.entered)
    # Counted after extraction, not by the survey that opened the run: `survey` reads results.json before this run has
    # written it, and a count taken then called every one of sixteen fresh digests "too thin to trust".
    from loom.refs.proposals import load_results

    for w in works:
        w.results = sum(1 for r in load_results(result.quilt.root, w.citekey).values() if r.cls == "mechanical")
    if "map" in steps:
        _map_step(result, works, force)
    return report
