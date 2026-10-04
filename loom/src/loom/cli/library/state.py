"""The bare `loom library` report, and `loom library WORK` (plan 0.18.5): verdict first, what waits for whom, each with the command that clears it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loom.cli.library._works import one_work, present
from loom.cli.report import LIMIT, Group, Item, Report, counted, table
from loom.refs.build import WorkState
from loom.scan.scan import ScanResult

#: Why a cited work needs the person, each with the command that clears it (`WORK` and `FILE` stand for the work and a document).
CAUSES: dict[str, tuple[str, str]] = {
    "unidentified": (
        "need you: no document and no identifier",
        "loom library add FILE --for WORK files one, or loom library ignore WORK --why '…' sets it aside",
    ),
    "wrong-title": (
        "need you: the title did not match on fetch",
        "loom library add FILE --for WORK files the right document",
    ),
    "offline": (
        "need you: no document yet, and fetching one needs the network",
        "loom library update --online looks it up and fetches it",
    ),
}
#: The "offline" cause where the quilt already allows the network: nothing is the person's to do but run the update.
FETCHABLE = ("no document yet: the next update fetches it", "loom library update looks it up and fetches it")


def cause_entry(result: ScanResult, cause: str) -> tuple[str, str]:
    """The heading and command for `cause`, as this quilt's network consent makes them: a quilt already online is never told to pass --online."""
    if cause == "offline" and result.quilt.config.online:
        return FETCHABLE
    return CAUSES[cause]


#: What a cited work whose document loom has not yet read is waiting for; nobody's judgement, only a run.
UNREAD = ("not read yet: a document with no page text, or a source with no digest", "loom library update reads them")
#: Where an agent is told to go for a work with pages and no digest.
INGEST = "an agent digests them in ingest mode (ai/modes/ingest.md)"


@dataclass
class Row:
    """One work as the library reports it: what the store holds, what waits on it, and why it needs the person.

    A work with versions is one row, its primary's: `versions` names the other documents, whose citations and results are counted in, and whose own store state is not.
    """

    work: WorkState
    waiting: int = 0
    cause: str = ""
    other_version: Any = None
    extracted: int = 0
    verified: int = 0
    versions: list[str] = field(default_factory=list)
    #: The author's keys citing the work, through any of its versions.
    cited: int = 0
    #: Whether the work or one of its versions has a digest.
    digested: bool = False

    @property
    def unread(self) -> bool:
        """A document loom has not yet read: a PDF with no page text, or a source with no digest."""
        w = self.work
        return not w.unreadable and ((w.pdf and not w.pages) or (w.source and not w.digest))

    @property
    def done(self) -> bool:
        w = self.work
        return self.digested and not (self.cause or self.waiting or self.unread or w.needs_an_agent)

    def to_json(self) -> dict[str, Any]:
        w, v = self.work, self.other_version
        return {
            "citekey": w.citekey,
            "cited_by": self.cited,
            "versions": self.versions,
            "source": w.source,
            "pdf": w.pdf,
            "pages": w.pages,
            "sections": w.sections,
            "digest": w.digest,
            "digest_version": {"extracted_from": v.extracted_from, "cited_as": v.cited_as} if v is not None else None,
            "waiting": self.waiting,
            "extracted": self.extracted,
            "verified": self.verified,
            "needs": self.cause,
            "needs_an_agent": w.needs_an_agent,
            "ignored": w.unreadable,
        }


def cause_of(w: WorkState) -> str:
    """The key in `CAUSES` for why work `w` needs the person, or '' when it does not.

    A work with a document is never sent to the network, and one with no document is never told to map (study D1–D5).
    """
    if w.unreadable:
        return ""
    if w.fetched is not None and w.fetched.discarded:
        return "wrong-title"
    if w.source or w.pdf:
        return ""
    if w.declared or w.candidate or w.identified:
        return "offline"
    return "unidentified"


def rows(result: ScanResult, works: list[WorkState] | None = None, *, fold: bool = True) -> list[Row]:
    """Every work `survey` sees, or `works` when a run already has them (their `fetched` says what a fetch discarded).

    With `fold`, a version whose primary is among them is counted into the primary's row and has none of its own (`Row.versions`).
    """
    from loom.refs.build import survey
    from loom.refs.proposals import EXTRACTED, PROPOSED, VERIFIED, load_results, state_of
    from loom.scan.digests import other_version_of

    root = result.quilt.root
    out = []
    for w in survey(result) if works is None else works:
        states = [state_of(r) for r in load_results(root, w.citekey).values()]
        other = other_version_of(result.assembly, w.citekey) if w.digest else None
        out.append(
            Row(
                w,
                waiting=states.count(PROPOSED),
                cause=cause_of(w),
                other_version=other,
                extracted=states.count(EXTRACTED),
                verified=states.count(VERIFIED),
                cited=w.cited_by,
                digested=w.digest,
            )
        )
    by_key = {r.work.citekey: r for r in out}
    if not fold:
        return out
    for r in out:
        top = by_key.get(r.work.version_of)
        if top is None:
            continue
        top.versions.append(r.work.citekey)
        top.waiting += r.waiting
        top.extracted += r.extracted
        top.verified += r.verified
        top.cited += r.cited
        top.digested = top.digested or r.digested
    return [r for r in out if r.work.version_of not in by_key]


def open_suggestions(result: ScanResult) -> list[Any]:
    """The citation suggestions still open, which `loom library review` lists beside the proposals."""
    from loom.records.store import Records

    return [
        a
        for rec in Records(result.quilt.root).records
        if not rec.discarded
        for a in rec.annotations
        if a.kind == "citation" and a.status == "open"
    ]


def report(result: ScanResult, works: list[WorkState] | None = None) -> Report:
    """The library's report: verdict, then what needs the person by cause, what waits for review, what needs an agent, and what is done.

    Parameters
    ----------
    result : ScanResult
        The scanned quilt.
    works : list of WorkState, optional
        The works as a run left them; default what is on disk (`survey`), which knows nothing of a fetch's discards.

    Returns
    -------
    Report
        Groups only over the works the author's documents cite; the rest are one count. `data` carries every work's row, the accepted citations and the relations.
    """
    from loom.refs.links import read_links
    from loom.refs.notes import read_notes

    root = result.quilt.root
    every = rows(result, works)
    cited = [r for r in every if r.cited]
    by_key = sorted(cited, key=lambda r: r.work.citekey.lower())
    groups: list[Group] = []
    for cause in CAUSES:
        heading, how = cause_entry(result, cause)
        items = [Item(_cause_text(result, r), key=r.work.citekey) for r in by_key if r.cause == cause]
        groups.append(Group(heading, items, problem=True, next=how))
    groups.append(
        Group(UNREAD[0], [Item(_unread_text(r), key=r.work.citekey) for r in by_key if r.unread], next=UNREAD[1])
    )
    suggestions = open_suggestions(result)
    waiting = sum(r.waiting for r in every) + len(suggestions)
    review = [Item(counted(r.waiting, "proposal"), key=r.work.citekey) for r in sorted(every, key=_key) if r.waiting]
    if suggestions:
        review.append(Item(counted(len(suggestions), "citation suggestion")))
    # the items count per work, so the heading carries the total itself
    groups.append(
        Group(
            f"waiting for review ({waiting})", review, counted=False, next="loom library review lists each with its id"
        )
    )
    agent = [r for r in by_key if r.work.needs_an_agent and not r.cause]
    groups.append(
        Group(
            "need an agent: pages and no digest", [Item(_agent_text(r), key=r.work.citekey) for r in agent], next=INGEST
        )
    )
    ignored = [r for r in by_key if r.work.unreadable]
    groups.append(Group("set aside by you", [Item(r.work.unreadable, key=r.work.citekey) for r in ignored]))
    notes = read_notes(root)
    groups.append(
        Group(
            "accepted citations: works an agent suggested and you accepted",
            [_note_item(n) for n in sorted(notes, key=lambda n: str(n.get("work", "")).lower())],
            next="loom library --json lists every one" if len(notes) > LIMIT else None,
        )
    )
    shown = present(*groups)
    done = sum(1 for r in cited if r.done)
    # counts with nothing listed under them: the count is in the heading, so no `… and N more` line follows it
    if done:
        shown.append(Group(f"done: {counted(done, 'work')} digested, nothing waiting", counted=False))
    if len(every) > len(cited):
        uncited = len(every) - len(cited)
        shown.append(Group(f"cited nowhere, so not followed: {counted(uncited, 'entry', 'entries')}", counted=False))
    # a work an update will fetch on the quilt's own consent waits on a run, not on the person
    need_you = sum(1 for r in cited if r.cause and cause_entry(result, r.cause) is not FETCHABLE)
    digested = sum(1 for r in cited if r.digested)
    verdict = (
        f"{counted(len(cited), 'work')} cited, {digested} digested; "
        f"{need_you} need{'s' if need_you == 1 else ''} you, {waiting} wait{'s' if waiting == 1 else ''} for review"
    )
    return Report(
        verdict,
        ok=not (need_you or waiting or agent or any(r.unread for r in cited)),
        groups=shown,
        data={
            "cited": len(cited),
            "digested": digested,
            "need_you": need_you,
            "waiting": waiting,
            "need_an_agent": len(agent),
            "done": done,
            "works": [r.to_json() for r in every],
            "reference_notes": notes,
            "links": [x.to_json() for x in read_links(root)],
        },
    )


def work_report(result: ScanResult, citekey: str) -> Report:
    """One work's report: its row of the store, what it needs and from whom, where the author cites it, and the citations accepted for it."""
    from loom.refs.notes import read_notes
    from loom.refs.resolve import _fold

    row = next((r for r in rows(result) if r.work.citekey == citekey), None) or next(
        r for r in rows(result, fold=False) if r.work.citekey == citekey
    )
    w = row.work
    table_rows = [
        ("cited", "src", "pdf", "pages", "secs", "digest", "extracted", "verified", "waiting"),
        (
            str(row.cited),
            "yes" if w.source else "-",
            "yes" if w.pdf else "-",
            str(w.pages or "-"),
            str(w.sections or "-"),
            ("preprint" if row.other_version is not None else "yes") if w.digest else "-",
            str(row.extracted or "-"),
            str(row.verified or "-"),
            str(row.waiting or "-"),
        ),
    ]
    groups: list[Group] = []
    if row.cause:
        heading, how = cause_entry(result, row.cause)
        # one work, so the command names it
        how = how.replace(" WORK", f" {citekey}").replace("update --online", f"update {citekey} --online")
        groups.append(Group(heading, [Item(_cause_text(result, row), key=citekey)], problem=True, next=how))
    if row.unread:
        groups.append(Group(UNREAD[0], [Item(_unread_text(row), key=citekey)], next=UNREAD[1]))
    if row.other_version is not None:
        groups.append(
            Group(
                "digest read off another version than the one cited: its numbers and pages are unverified",
                [Item(row.other_version.why, key=citekey)],
                problem=True,
                next=f"loom library read {citekey} PAGES checks one against the page",
            )
        )
    if row.waiting:
        groups.append(
            Group(
                "waiting for review",
                [Item(counted(row.waiting, "proposal"), key=citekey)],
                next=f"loom library review {citekey}",
            )
        )
    if w.needs_an_agent and not row.cause:
        groups.append(Group("needs an agent", [Item(_agent_text(row), key=citekey)], next=INGEST))
    if w.unreadable:
        groups.append(Group("set aside by you", [Item(w.unreadable, key=citekey)]))
    # where, not only how often: agents dumped the whole draft to a file and grepped it to find this
    sites = sorted(
        {
            (c.src, c.postnote or "")
            for c in result.edges.cites
            if c.citekey == citekey and c.file not in result.assembly.digest_files
        }
    )
    groups.append(Group("cited by", [Item(f"[{pn}]" if pn else "", key=src) for src, pn in sites], limit=None))
    title = _fold(str(result.bib[citekey].fields.get("title") or ""))
    accepted = [
        n
        for n in read_notes(result.quilt.root)
        if citekey in str(n.get("work", "")) or (title and title in _fold(str(n.get("work", ""))))
    ]
    groups.append(
        Group(
            "accepted citations naming it",
            [_note_item(n) for n in accepted],
            limit=None,
        )
    )
    state = (
        "digested" + (" from another version" if row.other_version is not None else "")
        if w.digest
        else "digested through a version"
        if row.digested
        else ("set aside" if w.unreadable else "not digested")
    )
    needs = (
        "needs you" if row.cause else ("waits for review" if row.waiting else ("done" if row.done else "in progress"))
    )
    verdict = f"{citekey}: cited by {counted(row.cited, 'key')}, {state}; {needs}"
    said = (
        [f"versions {', '.join(row.versions)}: other documents of this work, counted in this row"]
        if row.versions
        else [f"a version of {w.version_of}: loom library {w.version_of} reports the work"]
        if w.version_of
        else []
    )
    return Report(
        verdict,
        ok=row.done,
        lines=[*said, "", *table(table_rows)],
        groups=present(*groups),
        data={"work": row.to_json(), "reference_notes": accepted},
    )


def show(quilt_path: str | None, work: str | None, as_json: bool) -> None:
    """Print the library's report, or with `work` that work's; the group and its hidden `_work` command call this."""
    from loom.cli._quilt import open_scan

    result = open_scan(quilt_path)
    if work is None:
        report(result).emit(as_json)
        return
    work_report(result, one_work(result, work)).emit(as_json)


def _note_item(n: dict[str, Any]) -> Item:
    """An accepted citation: when, the work as the suggestion named it, and the keys it was suggested for."""
    return Item(
        f"{str(n.get('accepted', {}).get('when', ''))[:10]}  {n.get('work', '')}",
        key=", ".join(n.get("for", [])) or None,
    )


def _key(r: Row) -> str:
    return r.work.citekey.lower()


def _cause_text(result: ScanResult, r: Row) -> str:
    """What an item of a need-you group says beside its citekey: the discard's reason, the identifier to fetch on, or the title."""
    w = r.work
    if r.cause == "wrong-title" and w.fetched is not None:
        return w.fetched.discarded
    if r.cause == "offline":
        return (
            f"{w.candidate} (a candidate)"
            if w.candidate
            else ("arXiv id declared" if w.declared else "identifier declared")
        )
    return str(result.bib[w.citekey].fields.get("title") or "")[:60]


def _unread_text(r: Row) -> str:
    w = r.work
    return "PDF with no page text" if w.pdf and not w.pages else "source with no digest"


def _agent_text(r: Row) -> str:
    w = r.work
    if w.thin:
        return f"a digest too thin to trust: {counted(w.results, 'result')} over {counted(w.pages, 'page')}"
    return counted(w.pages, "page")
