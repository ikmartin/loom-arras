"""`loom library read`, `search` and `why` (plan 0.18.5): an agent's reading of the library, none of which writes."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import click

from loom.cli._common import EXIT_CONTENT, ContentError, EnvError, note
from loom.cli._quilt import open_bib, open_scan, quilt_option
from loom.cli.library._works import find_result, is_suggestion, logged, one_work, present, works
from loom.cli.report import Group, Item, Report, counted, table
from loom.scan.bib import BibEntry

#: What `--where` prints: the work's directory in the store, its PDF, or its unpacked source.
WHERE = ("dir", "pdf", "src")
#: Syntax a literal search would match nothing with: an agent searched "A\|B.*C", found nothing and read that as an absence.
#: A `\label{…}` in a statement, which a snippet leaves out: it is the id, said again.
LABEL = re.compile(r"\\label\{[^}]*\}\s*")
#: What a result's LaTeX says about where it sits rather than what it states: its citation title, its labels, references and `\uses`, and the environment markers. A search matches and quotes the statement, so a citekey inside a `\cite` never matches every result of its work.
APPARATUS = re.compile(
    r"\\cite(?:\[[^\]]*\])?\{[^}]*\}|\\(?:uses|label|ref|eqref|cref)\{[^}]*\}|\\(?:begin|end)\{[^}]*\}"
)


def _prose(tex: str) -> str:
    """`tex` without its apparatus (`APPARATUS`) and the brackets it leaves behind."""
    return re.sub(r"\[\{\s*\}\]|\{\s*\}", " ", APPARATUS.sub(" ", tex))


PATTERN = re.compile(r"\\\||\.\*|\|\||\[\^|\\[bdswBDSW]")


def page_range(spec: str) -> tuple[int, int]:
    """`12` or `10-14` as (first, last); a refusal for anything else."""
    m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", spec)
    if not m:
        raise EnvError(f"{spec!r} is not a page or a page range (12, or 10-14)")
    lo = int(m.group(1))
    hi = int(m.group(2) or lo)
    if hi < lo:
        raise EnvError(f"{spec!r} ends before it begins")
    return lo, hi


def no_pages(home: Path, citekey: str) -> str:
    """What a work with no page text should do next: map the PDF it has, or get one; a work with no PDF is never told to map."""
    if (home / "paper.pdf").is_file():
        return f"loom library update {citekey} --only map writes it from the PDF"
    return f"it has no PDF: loom library add FILE --for {citekey} files one"


def _entry(quilt_path: str | None, needle: str) -> tuple[Path, dict[str, BibEntry], str, Any]:
    """(root, bibliography, citekey, scan or None) for one WORK; an exact citekey is read without a scan, which costs a second on a large quilt."""
    quilt, bib = open_bib(quilt_path)
    if needle in bib:
        return quilt.root, bib, needle, None
    result = open_scan(quilt_path)
    return result.quilt.root, result.bib, one_work(result, needle), result


@click.command(name="read")
@click.argument("work")
@click.argument("pages", required=False)
@click.option(
    "--where",
    type=click.Choice(WHERE),
    default=None,
    help="Print where the work's directory, PDF or source is kept, instead of reading it.",
)
@click.option(
    "--json", "as_json", is_flag=True, help="Print the pages, the overview or the location as one JSON object."
)
@quilt_option
@click.pass_context
@logged("read")
def read_command(
    ctx: click.Context, work: str, pages: str | None, where: str | None, as_json: bool, quilt_path: str | None
) -> None:
    """Print a cited work's page text for PAGES (`12` or `10-14`), each page with its section, or without PAGES its digest's Overview.

    The page text is the sanctioned read: a quotation an agent proposes must come from it, because it is the text the anchor is checked against. The Overview is the paper's own framing, which is prose and so no result. `--where` prints where loom keeps the work instead; nothing there is meant to be navigated by hand, and the author's own pile goes in refs/ (book 8.16).
    """
    if where is not None and pages is not None:
        raise EnvError("--where prints where the work is kept; give PAGES or --where, not both")
    if pages is not None:
        lo, hi = page_range(pages)  # refused before the quilt is opened
    root, bib, ck, result = _entry(quilt_path, work)
    from loom.cli.library._works import home_in

    home = home_in(root, bib, ck)
    if where is not None:
        target = {"dir": home, "pdf": home / "paper.pdf", "src": home / "src"}[where]
        there = target.exists()
        if as_json:
            Report(
                str(target) if there else f"nothing there yet: {target}",
                ok=there,
                exit=0 if there else EXIT_CONTENT,
                data={"citekey": ck, "where": where, "path": str(target), "exists": there},
            ).emit(True)
            return
        click.echo(target)
        if not there:
            # printed anyway: the path is where it *would* go
            note(
                f"nothing there yet; loom library update {ck} --online fetches it, or loom library add FILE --for {ck}"
            )
            ctx.exit(EXIT_CONTENT)
        return
    if pages is None:
        _overview(result if result is not None else open_scan(quilt_path), ck, as_json)
        return
    from loom.refs.pages import read_map, read_page

    m = read_map(home)
    if m is None:
        raise ContentError(f"{ck} has no page text yet; {no_pages(home, ck)}")
    if lo > m.pages:
        raise ContentError(f"{ck} has {m.pages} pages; {lo} is past the end")
    out = []
    for n in range(lo, min(hi, m.pages) + 1):
        text = read_page(home, n)
        if text is None:
            continue
        sec = m.section_of(n)
        out.append({"page": n, "section": f"{sec.n} {sec.title}".strip() if sec else "", "text": text.rstrip("\n")})
    if not out:
        raise ContentError(f"{ck} has no page text for {pages}; {no_pages(home, ck)}")
    if as_json:
        first, last = out[0]["page"], out[-1]["page"]
        Report(
            f"{ck} p.{first}" + (f"-{last}" if last != first else ""),
            data={"citekey": ck, "sha256": m.sha256, "pages": out},
        ).emit(True)
        return
    for page in out:
        head = f"--- {ck} p.{page['page']}"
        if page["section"]:
            head += f"  [{page['section']}]"
        click.echo(head + " " + "-" * max(0, 60 - len(head)))
        click.echo(page["text"])


def _overview(result: Any, ck: str, as_json: bool) -> None:
    """Print `ck`'s digest's Overview, warning on stderr when the digest was read off another version than the one cited."""
    from loom.refs.proposals import digest_path
    from loom.scan.digests import other_version_of

    path = digest_path(result.quilt.root, ck)
    if not path.is_file():
        raise ContentError(f"{ck} has no digest; loom library {ck} says what it has")
    m = re.search(
        r"\\section\*\{Overview\}(.*?)(?=\\section|\\begin\{(?:theorem|lemma|proposition|definition|corollary)|\Z)",
        path.read_text(encoding="utf-8"),
        re.S,
    )
    v = other_version_of(result.assembly, ck)
    if v is not None:
        note(
            f"{ck}: the digest {v.why}; its numbers and pages are unverified, so check one with loom library read {ck} PAGES"
        )
    if not m or not m.group(1).strip():
        raise ContentError(f"{ck}'s digest has no Overview")
    text = m.group(1).strip()
    if as_json:
        Report(f"{ck}'s overview", data={"citekey": ck, "overview": text}).emit(True)
        return
    click.echo(text)


@click.command(name="search")
@click.argument("text")
@click.option(
    "--pages",
    "in_pages",
    is_flag=True,
    help="Search the page text of every mapped work, not the results digested from them.",
)
@click.option("--work", "only", multiple=True, metavar="WORK", help="Search only this work; repeatable.")
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=20,
    show_default=True,
    help="Show at most this many hits; everything is still searched.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
@logged("search")
def search_command(
    text: str, in_pages: bool, only: tuple[str, ...], limit: int, as_json: bool, quilt_path: str | None
) -> None:
    """Search the library's results for every word of TEXT, ignoring case, best match first; with --pages, its page text.

    A word in a result's locator, its local name or its work's title counts three, one in its statement one; a main result (level 1) and each citation of it in your documents count more. **Every answer says how much of the library it could search**, because a search over a partly digested corpus is a search over silence. Page text is mathematics after a text layer, so a page hit is a pointer and never a quotation: read the page with `loom library read`, and quote from that.
    """
    from loom.refs.search import terms_of

    if PATTERN.search(text):
        raise EnvError(
            f"{text!r} looks like a pattern; loom library search matches words literally. Run it once per phrase."
        )
    terms = terms_of(text)
    if not terms:
        raise EnvError("give at least one word to search for")
    result = open_scan(quilt_path)
    wanted = works(result, only) if only else None
    (_pages if in_pages else _results)(result, text, terms, wanted, limit).emit(as_json)


def _locator(r: Any) -> str:
    """How the paper names a result: the postnote of its locator (`Proposition 3.2`), else its taxon and number."""
    m = re.search(r"\\cite\[([^\]]*)\]", r.locator or "")
    if m:
        return re.sub(r",\s*p+\.\s*~?\s*[\d-]+$", "", m.group(1)).replace("~", " ").strip()
    return f"{r.taxon.capitalize()} {r.number}".strip() if r.number else r.local


def _citations(result: Any) -> dict[str, int]:
    """How many times the author's documents cite or reference each result id."""
    out: dict[str, int] = {}
    for e in result.edges.edges:
        if e.file not in result.assembly.digest_files:
            out[e.to] = out.get(e.to, 0) + 1
    return out


def _results(result: Any, text: str, terms: list[str], wanted: set[str] | None, limit: int) -> Report:
    """The ranked result search (WQ-41): ties by citekey, then id. Each hit says its state, and a work read off another version than the one cited says so once."""
    from loom.refs.proposals import DISCARDED, load_results, said_state, state_of
    from loom.refs.search import score_result, snippet
    from loom.scan.digests import other_version_of

    root = result.quilt.root
    digested = [p.name[: -len(".results.json")] for p in sorted((root / "digests").glob("*.results.json"))]
    keys = [ck for ck in digested if wanted is None or ck in wanted]
    cites = _citations(result)
    hits: list[dict[str, Any]] = []
    searched = 0
    for ck in keys:
        results = load_results(root, ck)
        if results:
            searched += 1
        entry = result.bib.get(ck)
        title = str(entry.fields.get("title") or "") if entry else ""
        for rid, r in results.items():
            if state_of(r) == DISCARDED:
                continue
            where = _locator(r)
            score = score_result(
                terms,
                f"{where} {r.local} {title}",
                _prose(f"{r.statement} {r.source_text}"),
                level=r.level,
                citations=cites.get(rid, 0),
            )
            if score is None:
                continue
            source, statement = _prose(r.source_text), _prose(r.statement)
            body = source if any(t in source.casefold() for t in terms) else statement
            hits.append(
                {
                    "id": rid,
                    "work": ck,
                    "locator": where,
                    "snippet": snippet(LABEL.sub("", body or statement), terms, 44),
                    "score": score,
                    "state": state_of(r),
                    "said": said_state(r),
                    "level": r.level,
                    "page": r.anchor.page,
                    "class": r.cls,
                    "citations": cites.get(rid, 0),
                    "same": re.sub(r"[^0-9a-z]+", "", statement.casefold()),
                }
            )
    hits = _once_per_work(hits, result.bib)
    hits.sort(key=lambda h: (-h["score"], h["work"], h["id"]))
    shown = hits[:limit]
    in_works = len({h["of"] for h in hits})
    # a state and a work's versions are said once, in a heading and a group of their own, not on every hit
    by_state: dict[str, list[Item]] = {}
    for h in shown:
        by_state.setdefault(h["said"], []).append(Item(f"{h['work']}  {h['locator']}  {h['snippet']}", key=h["id"]))
    also: dict[str, dict[str, int]] = {}
    for h in shown:
        for v in h["versions"]:
            also.setdefault(h["work"], {})[v] = also.get(h["work"], {}).get(v, 0) + 1
    q = shlex.quote(text)
    cut = len(hits) > len(shown)
    # a digest's version is its extraction's, so it is said for a work whose extracted results were hit
    mechanical = dict.fromkeys(h["work"] for h in shown if h["class"] == "mechanical")
    versions = {ck: other_version_of(result.assembly, ck) for ck in mechanical}
    return Report(
        f"{counted(len(hits), 'result')} in {counted(in_works, 'work')}"
        + (f", showing {len(shown)}" if cut else "")
        + f"; {len(digested)} of {len(result.bib)} works digested",
        lines=[] if hits else [f"next: loom library search {q} --pages searches the page text"],
        groups=present(
            *[
                Group(
                    f"{said}, best match first",
                    items,
                    count=sum(1 for h in hits if h["said"] == said),
                    limit=None,
                    next=(
                        f"loom library search {q} --limit {len(hits)} shows every one"
                        if cut
                        else "loom library why ID says where one came from"
                    )
                    if i == len(by_state) - 1
                    else None,
                )
                for i, (said, items) in enumerate(by_state.items())
            ],
            Group(
                "also stated in another version",
                [
                    Item(
                        ", ".join(f"{counted(n, 'result')} in {v}" for v, n in sorted(vs.items())),
                        key=work,
                    )
                    for work, vs in sorted(also.items())
                ],
                limit=None,
            ),
        ),
        notes=[f"{ck}: {v.read_from}" for ck, v in versions.items() if v is not None],
        data={"results": len(hits), "searched": searched, "of": len(result.bib), "truncated": cut, "hits": shown},
    )


def _once_per_work(hits: list[dict[str, Any]], bib: Any) -> list[dict[str, Any]]:
    """Each result once per work: hits on one statement in several versions of a work become the primary's hit, else the best one, naming the versions that also hold it.

    `of` is the work's primary citekey; the statement is compared as `same`, its words without apparatus, which is dropped from the hit.
    """
    from loom.refs.scan import primary_of

    tops = primary_of(bib)
    kept: dict[tuple[str, str], dict[str, Any]] = {}
    for h in sorted(hits, key=lambda h: (h["work"] in tops, -h["score"], h["work"], h["id"])):
        h["of"] = tops.get(h["work"], h["work"])
        same = h.pop("same")
        first = kept.get((h["of"], same)) if same else None
        if first is not None:
            first["versions"].append(h["work"])
            continue
        h["versions"] = []
        kept[(h["of"], same or h["id"])] = h
    for h in kept.values():
        h["versions"].sort()
    return list(kept.values())


def _pages(result: Any, text: str, terms: list[str], wanted: set[str] | None, limit: int) -> Report:
    """The page search: pages ranked by how often the terms occur on them, every work's best page shown before any work's second.

    A work's versions are one work: a page a version holds as the work does is one hit, the work's, and the version is named once below.
    """
    from loom.refs.build import survey
    from loom.refs.fetch import work_dir
    from loom.refs.scan import primary_of
    from loom.refs.search import search_pages

    root = result.quilt.root
    tops = primary_of(result.bib)
    pool = [w for w in survey(result) if wanted is None or w.citekey in wanted]
    found = []
    searched = 0
    for w in pool:
        if not w.pages:
            continue
        searched += 1
        found.extend(search_pages(work_dir(root, result.bib[w.citekey]), w.citekey, terms))
    found.sort(key=lambda h: (h.citekey in tops, -h.score, h.citekey, h.page))
    hits = []
    seen: dict[tuple[str, int, str], Any] = {}
    also: dict[str, dict[str, int]] = {}
    for h in found:
        same = (tops.get(h.citekey, h.citekey), h.page, h.context)
        first = seen.get(same)
        if first is None:
            seen[same] = h
            hits.append(h)
        else:
            per = also.setdefault(first.citekey, {})
            per[h.citekey] = per.get(h.citekey, 0) + 1
    hits.sort(key=lambda h: (-h.score, h.citekey, h.page))
    works_with_pages = len({tops.get(w.citekey, w.citekey) for w in pool if w.pages})
    # Every work is searched before anything is cut, and the cut takes each work's best page before any work's second: a plain top-N filled up with whichever paper had the most pages, and the others looked empty.
    per_work: dict[str, list[Any]] = {}
    for h in hits:
        per_work.setdefault(tops.get(h.citekey, h.citekey), []).append(h)
    shown: list[Any] = []
    depth = 0
    while len(shown) < limit and any(len(v) > depth for v in per_work.values()):
        for ck in sorted(per_work, key=lambda k: (-per_work[k][0].score, k)):
            if depth < len(per_work[ck]) and len(shown) < limit:
                shown.append(per_work[ck][depth])
        depth += 1
    shown.sort(key=lambda h: (-h.score, h.citekey, h.page))
    q = shlex.quote(text)
    items = [
        Item(f"p.{h.page}" + (f" [{h.section}]" if h.section else "") + f"  {h.context}", key=h.citekey) for h in shown
    ]
    taken = {ck: sum(1 for h in shown if tops.get(h.citekey, h.citekey) == ck) for ck in per_work}
    by_work = [
        Item(
            counted(len(v), "page"),
            key=ck,
            fixes=[f"loom library search {q} --pages --work {ck} --limit {len(v)}"] if taken[ck] < len(v) else [],
        )
        for ck, v in sorted(per_work.items(), key=lambda kv: kv[0].lower())
    ]
    cut = len(hits) > len(shown)
    verdict = (
        f"{counted(len(hits), 'hit')} in {len(per_work)} of {counted(works_with_pages, 'work')} with page text"
        + (f", showing {len(shown)}" if cut else "")
    )
    if searched < len(pool):
        verdict += f"; {len(pool) - searched} of {len(pool)} have none to search (loom library)"
    return Report(
        verdict,
        groups=present(
            Group(
                "pages, most hits first",
                items,
                count=len(hits),
                limit=None,
                next=f"loom library read {shown[0].citekey} {shown[0].page} reads one" if shown else None,
            ),
            Group("pages per work", by_work if cut else []),
            Group(
                "also on a version's page",
                [
                    Item(", ".join(f"{counted(n, 'page')} in {v}" for v, n in sorted(vs.items())), key=ck)
                    for ck, vs in sorted(also.items())
                ],
                limit=None,
            ),
        ),
        notes=["page text is mathematics after a text layer: read the page before quoting anything from it"]
        if shown
        else [],
        data={
            "searched": searched,
            "of": len(pool),
            "truncated": cut,
            "hits": [
                {"work": h.citekey, "page": h.page, "section": h.section, "context": h.context, "score": h.score}
                for h in shown
            ],
        },
    )


@click.command(name="why")
@click.argument("target", metavar="ID")
@click.option(
    "--depth", type=click.IntRange(min=1), default=1, show_default=True, help="Follow its relations this many hops out."
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
@logged("why")
def why_command(target: str, depth: int, as_json: bool, quilt_path: str | None) -> None:
    """Show where a result came from, what state it is in and who changed it, then its relations to other results.

    Provenance names every party, not just the first: a record that credits an agent with a sentence you wrote cannot be audited. A relation is somebody's reading, asserted and never checked. ID may also be a citation suggestion's annotation id.
    """
    result = open_scan(quilt_path)
    if is_suggestion(target):
        _why_suggestion(result, target).emit(as_json)
        return
    from loom.refs.proposals import edit_diff, read_events, said_state, state_of
    from loom.scan.digests import other_version_of

    citekey, rid, results = find_result(result, target)
    r = results[rid]
    chain = [e for e in read_events(result.quilt.root, citekey) if e.get("id") == rid or e.get("supersedes") == rid]
    state = said_state(r)
    # the numbers of an extracted result are its digest's, read off whatever version was extracted
    version = other_version_of(result.assembly, citekey) if r.cls == "mechanical" else None
    if r.anchor.kind == "pdf":
        last = f"-{r.anchor.last}" if r.anchor.last > r.anchor.page else ""
        anchor = f"p.{r.anchor.page}{last} of {citekey}'s PDF"
    else:
        anchor = f"{r.anchor.path or citekey + ' (its source)'}"
    rows = [
        ("state", state),
        *([("version", version.read_from)] if version is not None else []),
        ("anchor", f"{anchor} ({r.anchor.kind}, level {r.level}, {r.cls})"),
        *((str(o.get("act", "")), f"{o.get('by') or '—'}  {str(o.get('when', ''))[:19]}") for o in r.origin),
    ]
    if r.supersedes:
        rows.append(("supersedes", r.supersedes))
    rows += [("discarded", str(e.get("reason", ""))) for e in chain if e.get("event") == "discarded"]
    found = _relations(result.quilt.root, rid, depth)
    from loom.refs.links import KINDS

    related = [
        Item(f"{x.frm} {KINDS.get(x.kind, x.kind)} {x.to}: {x.why} — {x.by or 'unattributed'}", key=x.id)
        for x in sorted(found, key=lambda x: x.id)
    ]
    hops = f"{depth} hop{'s' if depth != 1 else ''}"
    Report(
        f"{rid}, {state}, from {citekey}; "
        + (f"{counted(len(found), 'relation')} within {hops}" if found else "no relations"),
        lines=["", *(f"  {line}" for line in table(rows))],
        groups=present(
            # what the author changed, which is what a later proposer should learn from
            Group("the author's edit (- proposed, + verified)", [Item(line) for line in edit_diff(r)], limit=None),
            Group(f"relations within {hops}: asserted, not checked", related, limit=None),
        ),
        data={
            "work": citekey,
            **r.to_json(),
            "state": state_of(r),
            "version": version.to_json() if version is not None else None,
            "events": chain,
            "links": [x.to_json() for x in found],
        },
    ).emit(as_json)


def _relations(root: Path, rid: str, depth: int) -> list[Any]:
    """Every relation within `depth` hops of `rid`, either direction, each once and in the order found."""
    from loom.refs.links import touching

    frontier, seen, found = {rid}, set(), []
    for _ in range(depth):
        nxt: set[str] = set()
        for key in frontier:
            for x in touching(root, key):
                if x.id not in seen:
                    seen.add(x.id)
                    found.append(x)
                    nxt |= {x.frm, x.to}
        frontier = nxt - frontier
    return found


def _why_suggestion(result: Any, ann_id: str) -> Report:
    """A citation suggestion's provenance: who suggested which work for which key, and whether it is still open."""
    from loom.cli._common import NotFoundError
    from loom.records.annotations import find_annotation
    from loom.records.store import Records

    found = find_annotation(Records(result.quilt.root).records, ann_id)
    if found is None:
        raise NotFoundError("annotation", f"no annotation {ann_id}")
    rec, ann = found
    if ann.kind != "citation":
        raise ContentError(f"{ann_id} is a {ann.kind}, not a citation suggestion or a result")
    rows = [
        ("state", ann.status),
        ("suggested", f"{ann.author_id or '—'} ({ann.author_kind})  {ann.created[:19]}"),
        ("session", rec.rel),
        ("for", ann.target_key),
        ("work", ann.payload or "—"),
    ]
    return Report(
        f"{ann_id}, a citation suggestion, {ann.status}",
        lines=[
            "",
            *(f"  {line}" for line in table(rows)),
            "",
            f"  {ann.body}",
            *(["", "next: loom library review lists what is still open"] if ann.status == "open" else []),
        ],
        data={"annotation": ann.to_dict(), "session": rec.rel},
    )


#: The commands this module adds to `loom library`.
COMMANDS: list[click.Command] = [read_command, search_command, why_command]
