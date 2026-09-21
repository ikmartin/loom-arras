"""`loom refs` (book 8.9, 8.9.1; plan 0.12 §4.3, §4.4): a quilt's reference layer.

`path` and `add` say where a cited work's artifacts live and put one there by hand; `resolve` asks which identifier an entry that states none most likely has; `fetch` brings sources and PDFs in on a declared identifier or a strong candidate; `match` lists what a person has to look at; and `build` runs the whole mechanical pipeline, which is the one command that starts a digest.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any, TypeVar, cast

import click

from loom.cli._common import EXIT_CONTENT, ContentError, EnvError, note
from loom.cli._quilt import open_quilt, open_scan, quilt_option
from loom.clock import stamp
from loom.refs.identity import declared, primary
from loom.refs.pages import storage_root
from loom.refs.resolve import Resolver, ResolveRefused, query_for, save
from loom.scan.scan import ScanResult


def _home(result: ScanResult, citekey: str) -> Path:
    """The work's directory in loom's store, or a refusal naming what is missing."""
    entry = result.bib.get(citekey)
    if entry is None:
        raise EnvError(f"{citekey} is not in the bibliography, so it has no identity to file under")
    wid = primary(entry)
    assert wid is not None  # identify() always yields at least a synthetic id for a real entry
    return storage_root(result.quilt.root) / wid.path


F = TypeVar("F", bound=Callable[..., Any])


def logged(name: str) -> Callable[[F], F]:
    """Give a read-only `refs` command `--session`, logging the call to that session as `loom source --session` does."""
    import functools

    def wrap(f: F) -> F:
        @click.option(
            "--session",
            "run_dir",
            default=None,
            envvar="LOOM_SESSION",
            metavar="SESSION",
            help="Log this call to the session.",
        )
        @functools.wraps(f)
        def inner(*args: Any, run_dir: str | None = None, **kwargs: Any) -> Any:
            if run_dir:
                from loom.cli._quilt import open_quilt
                from loom.cli.build_cmds import log_run

                shown = [str(v) for k, v in kwargs.items() if v not in (None, False, (), "") and k != "quilt_path"]
                log_run(run_dir, " ".join(["loom refs", name, *shown]), open_quilt(kwargs.get("quilt_path")).root)
            return f(*args, **kwargs)

        return cast(F, inner)

    return wrap


@click.group(name="refs")
def refs() -> None:
    """Fetched works: where their artifacts are, how to add one by hand, and identifiers for works that state none."""


@refs.command(name="path")
@click.argument("citekey")
@click.option("--pdf", "want", flag_value="pdf", help="The PDF rather than the directory.")
@click.option("--src", "want", flag_value="src", help="The unpacked source rather than the directory.")
@quilt_option
@click.pass_context
@logged("path")
def path_command(ctx: click.Context, citekey: str, want: str | None, quilt_path: str | None) -> None:
    """Print where CITEKEY's artifacts live, under digests/storage. Nothing there is meant to be navigated by hand; the author's own pile goes in refs/ (book 8.16)."""
    result = open_scan(quilt_path)
    home = _home(result, citekey)
    target = home if want is None else (home / "paper.pdf" if want == "pdf" else home / "src")
    click.echo(target)
    if not target.exists():
        # printed anyway: the path is where it *would* go, which is what `refs add` and `refs fetch` need
        note(f"nothing there yet; loom refs fetch {citekey}")
        ctx.exit(EXIT_CONTENT)


@refs.command(name="add")
@click.argument("citekey")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--force", is_flag=True, help="Replace an artifact that is already there.")
@quilt_option
@click.pass_context
def add_command(ctx: click.Context, citekey: str, file: Path, force: bool, quilt_path: str | None) -> None:
    """File FILE as CITEKEY's PDF, or its LaTeX source, in loom's store.

    A published PDF usually sits behind a subscription that loom cannot and should not automate past, so the author supplies the bytes and names the citekey they know; loom resolves the identifier and does the filing. A `.tex` file, or a directory of them, is filed as the work's source, which is what `loom digest extract` reads: fetching is the usual way source arrives, and this is the way for a paper that is not on a preprint server.
    """
    result = open_scan(quilt_path)
    home = _home(result, citekey)
    root = result.quilt.root
    if file.is_dir() or file.suffix.lower() == ".tex":
        dest = home / "src"
        if dest.is_dir() and any(dest.rglob("*.tex")) and not force:
            raise EnvError(f"{dest.relative_to(root)} already holds source; pass --force to replace it")
        if force and dest.is_dir():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        if file.is_dir():
            shutil.copytree(file, dest, dirs_exist_ok=True)
        else:
            shutil.copy(file, dest / file.name)
        click.echo(f"Wrote {dest.relative_to(root)}/")
        note(f"loom digest extract {citekey} now reads it; the store is not in version control")
        return
    if file.suffix.lower() != ".pdf":
        raise EnvError(f"{file.name} is neither a PDF nor LaTeX source; loom files those two things")
    dest = home / "paper.pdf"
    if dest.exists() and not force:
        raise EnvError(f"{dest.relative_to(root)} exists; pass --force to replace it")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(file, dest)
    click.echo(f"Wrote {dest.relative_to(root)}")
    note("the PDF is not in version control: a collaborator cloning the quilt fetches or adds their own copy")


@refs.command(name="resolve")
@click.argument("citekeys", nargs=-1)
@click.option("--refresh", is_flag=True, help="Ask again even where an answer is recorded.")
@click.option("--json", "as_json", is_flag=True, help="Print the candidates as JSON.")
@click.option(
    "--resolve",
    "allow_resolve",
    is_flag=True,
    help="Allow looking up for this run, without setting [refs] resolve in config.toml.",
)
@quilt_option
@click.pass_context
def resolve_command(
    ctx: click.Context,
    citekeys: tuple[str, ...],
    refresh: bool,
    as_json: bool,
    allow_resolve: bool,
    quilt_path: str | None,
) -> None:
    """Look up identifiers for cited works whose bibliography entry states none. Requires [refs] resolve = true, or --resolve for one run.

    Asks zbMATH Open, then Crossref, and prints candidates with how well each matched. Nothing is changed: a candidate becomes the work's identity when you add the field to your own bibliography entry. Answers are kept in the store, so `loom lint` can name them and a second run asks nothing. With no CITEKEYS, every cited entry that states no identifier.
    """
    result = open_scan(quilt_path)
    cfg = result.quilt.config
    cfg.resolve = cfg.resolve or allow_resolve  # this run's consent, written nowhere (DR-193)
    if not cfg.resolve:
        raise EnvError(
            "looking up is off: set resolve = true under [refs] in config.toml to allow it, or pass --resolve for this run (it sends bibliography titles and authors to zbMATH Open and Crossref)"
        )
    root = result.quilt.root
    if citekeys:
        missing = [ck for ck in citekeys if ck not in result.bib]
        if missing:
            raise EnvError(f"not in the bibliography: {', '.join(missing)}")
        wanted = list(citekeys)
    else:
        cited = {c.citekey for c in result.edges.cites}
        wanted = sorted(ck for ck in cited if ck in result.bib and not declared(result.bib[ck]))
    resolver = Resolver(cache=storage_root(root) / "cache" / "resolve", contact=cfg.contact, refresh=refresh)
    report: dict[str, object] = {}
    failures = 0
    for ck in wanted:
        entry = result.bib[ck]
        if declared(entry) and not citekeys:
            continue
        try:
            found = resolver.candidates(query_for(entry))
        except ResolveRefused as exc:
            failures += 1
            report[ck] = {"error": str(exc)}
            if not as_json:
                click.echo(f"{ck}: {exc}")
            continue
        path = save(root, entry, found)
        report[ck] = {
            "candidates": [asdict(c) | {"strength": c.strength} for c in found],
            "record": str(path.relative_to(root)),
        }
        if as_json:
            continue
        if not found:
            click.echo(f"{ck}: no match")
            continue
        for i, c in enumerate(found[:3]):
            lead = f"{ck}:" if i == 0 else " " * (len(ck) + 1)
            names = ", ".join(a.split(",")[0] for a in c.authors[:3]) + (" et al." if len(c.authors) > 3 else "")
            also = f" (also {', '.join(c.also)})" if c.also else ""
            click.echo(
                f"{lead} {c.id}{also}  {c.strength} {c.confidence:.2f}  {c.source}  {c.title} — {names} {c.year}".rstrip()
            )
    if as_json:
        click.echo(json.dumps({"lookups": resolver.requests, "works": report}, indent=2))
    else:
        if not wanted:
            click.echo("every cited work states an identifier")
        note(
            "nothing was changed: add the field to your own bibliography entry to make a candidate the work's identity"
        )
    if failures:
        ctx.exit(EXIT_CONTENT)


@refs.command(name="note")
@click.option("--from", "run_dir", default=None, metavar="SESSION", help="The session whose suggestion this is.")
@click.option(
    "--accept", "accept_id", default=None, metavar="ID", help="Record this citation suggestion and resolve it."
)
@click.option("--reject", "reject_id", default=None, metavar="ID", help="Resolve the suggestion without recording it.")
@click.option("--reason", default=None, help="Why, optionally; it rides on the resolve event.")
@click.option("--author", default=None, help="Who accepted, when the user config and git do not say.")
@click.option("--list", "as_list", is_flag=True, help="Print what has been accepted.")
@quilt_option
def note_command(
    run_dir: str | None,
    accept_id: str | None,
    reject_id: str | None,
    reason: str | None,
    author: str | None,
    as_list: bool,
    quilt_path: str | None,
) -> None:
    """Accept or reject an agent's citation suggestion.

    Accepting appends to `reference-notes.jsonl` and resolves the annotation; rejecting resolves it and records nothing, the reason riding on the resolve event. Neither touches `refs.bib`: a candidate becomes a work's identity when your own bibliography entry says so, and nothing else (DR-122). This is the breadcrumb for the day you add it.
    """
    from loom.clock import stamp
    from loom.records.annotations import find_annotation
    from loom.records.log import append
    from loom.records.store import Records
    from loom.refs.notes import append_note, read_notes
    from loom.scan.quilt import resolve_author

    result = open_scan(quilt_path)
    root = result.quilt.root
    if as_list:
        notes = read_notes(root)
        if not notes:
            click.echo("no reference notes yet")
            return
        for n in notes:
            keys = ", ".join(n.get("for", [])) or "-"
            click.echo(f"{n.get('accepted', {}).get('when', '')[:10]}  {n.get('work', '')}  ({keys})")
        return
    if bool(accept_id) == bool(reject_id):
        raise EnvError("give --accept ID or --reject ID")
    ann_id = accept_id or reject_id
    assert ann_id is not None
    found = find_annotation(Records(root).records, ann_id)
    if found is None:
        raise ContentError(f"no annotation {ann_id}")
    _rec, ann = found
    if ann.kind != "citation":
        raise ContentError(f"{ann_id} is a {ann.kind}, not a citation suggestion")
    who = resolve_author(author, root)[0]
    if accept_id:
        # The payload names the work and the body argues for it: a note whose `work` held the argument could never
        # become a bibliography entry, which is the one thing the breadcrumb exists for.
        if not ann.payload:
            raise ContentError(f"{ann_id} proposes no work; a citation suggestion names one in --payload")
        append_note(
            root,
            {
                "work": ann.payload,
                "for": [ann.target_key],
                "claim": ann.body,
                "identifier": {"verified": False},
                "accepted": {"when": stamp(), "who": who},
                "from": {"run": _rec.rel if _rec.is_run else None, "annotation": ann_id},
            },
        )
    append(
        root,
        {
            "event": "resolved",
            "id": ann_id,
            "when": stamp(),
            "author": who,
            "kind": "human",
            "run": None,
            "body": reason or ("accepted" if accept_id else "rejected"),
        },
    )
    click.echo(f"{'accepted' if accept_id else 'rejected'} {ann_id}" + (f": {reason}" if reason else ""))


@refs.command(name="scan")
@click.option("--dry-run", is_flag=True, help="Report what would be added and write nothing.")
@quilt_option
def scan_command(dry_run: bool, quilt_path: str | None) -> None:
    """Add every bibliography entry the canon documents carry to digests/bibliography.bib.

    Reads each canon document's inline `thebibliography` and the `.bib` files it names. The file is only ever appended to: an entry already there is never rewritten or removed, so a hand correction survives. A `\\bibitem` becomes an entry with its text in `loom-text`, its identifiers, and a heuristic author, title and year. `import`, `canonize` and `refs build` run this themselves.

    It also files what the author dropped in `refs/`, and **adopts** any document the store holds that no entry names -- an entry deleted by hand leaves a PDF and its page text that nothing can reach, and an entry is what names it. Adoption happens once per document; a later scan leaves it alone.
    """
    from loom.refs.scan import scan_bibliography

    for line in scan_bibliography(open_quilt(quilt_path), write=not dry_run).lines():
        click.echo(line + (" (dry run)" if dry_run and line.startswith("digests/") else ""))


@refs.command(name="build")
@click.argument("citekeys", nargs=-1)
@click.option("--refresh", is_flag=True, help="Ask the lookup services again where an answer is recorded.")
@click.option("--no-candidates", is_flag=True, help="Fetch only on identifiers an entry declares itself.")
@click.option("--force", is_flag=True, help="Re-extract digests that are already present.")
@click.option(
    "--fetch",
    "allow_fetch",
    is_flag=True,
    help="Allow fetching for this run, without setting [refs] fetch in config.toml.",
)
@click.option(
    "--resolve",
    "allow_resolve",
    is_flag=True,
    help="Allow looking identifiers up for this run, without setting [refs] resolve in config.toml.",
)
@click.option(
    "--only",
    "only_steps",
    default=None,
    metavar="STEP[,STEP]",
    help="Run only these steps: resolve, fetch, extract, map.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as JSON.")
@quilt_option
def build_command(
    citekeys: tuple[str, ...],
    refresh: bool,
    no_candidates: bool,
    force: bool,
    allow_fetch: bool,
    allow_resolve: bool,
    only_steps: str | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Make everything about this quilt's cited works that a machine can make: resolve, fetch, extract, report.

    The one command that starts a digest. It runs `loom refs scan` first, and each step is a no-op where its work is done, so running it again after a new entry reaches the bibliography resolves, fetches and extracts that entry alone. Nothing here touches the network unless `[refs] resolve` and `[refs] fetch` say it may; without them it still extracts from whatever sources are already on disk. The last two lines say what is left for a person and what is left for an agent.
    """
    from loom.refs.build import build_refs
    from loom.refs.scan import scan_bibliography

    report = scan_bibliography(open_quilt(quilt_path))
    if not as_json:
        for line in report.lines():
            note(line)
    result = open_scan(quilt_path)
    # the flags are this run's consent, and are not written anywhere: the config is the standing answer (DR-193)
    result.quilt.config.fetch = result.quilt.config.fetch or allow_fetch
    result.quilt.config.resolve = result.quilt.config.resolve or allow_resolve
    steps = tuple(s.strip() for s in only_steps.split(",")) if only_steps else ("resolve", "fetch", "extract", "map")
    unknown = [s for s in steps if s not in ("resolve", "fetch", "extract", "map")]
    if unknown:
        raise EnvError(f"unknown step: {', '.join(unknown)} (resolve, fetch, extract, map)")
    missing = [ck for ck in citekeys if ck not in result.bib]
    if missing:
        raise EnvError(f"not in the bibliography: {', '.join(missing)}")
    built = build_refs(result, only=citekeys, refresh=refresh, candidates=not no_candidates, force=force, steps=steps)
    if as_json:
        click.echo(
            json.dumps(
                {
                    "looked_up": built.looked_up,
                    "works": [
                        {
                            "citekey": w.citekey,
                            "cited_by": w.cited_by,
                            "declared": w.declared,
                            "candidate": w.candidate,
                            "source": w.source,
                            "pdf": w.pdf,
                            "digest": w.digest,
                            "pages": w.pages,
                            "sections": w.sections,
                            "discarded": w.fetched.discarded if w.fetched else "",
                            "refused": w.fetched.refused if w.fetched else "",
                            "extract_error": w.extract_error,
                        }
                        for w in built.works
                    ],
                },
                indent=2,
            )
        )
        return
    for line in built.lines():
        click.echo(line)
    for err in built.lookup_errors[:5]:
        note(err)


@refs.command(name="fetch")
@click.argument("citekeys", nargs=-1)
@click.option("--no-pdf", is_flag=True, help="Take the source only; the PDF is fetched by default.")
@click.option("--no-candidates", is_flag=True, help="Fetch only on identifiers an entry declares itself.")
@click.option(
    "--fetch",
    "allow_fetch",
    is_flag=True,
    help="Allow fetching for this run, without setting [refs] fetch in config.toml.",
)
@quilt_option
@click.pass_context
def fetch_command(
    ctx: click.Context,
    citekeys: tuple[str, ...],
    no_pdf: bool,
    no_candidates: bool,
    allow_fetch: bool,
    quilt_path: str | None,
) -> None:
    """Fetch sources and PDFs for cited works into loom's store, checking on arrival that each is the work its entry names.

    Fetches on an identifier the entry declares, or on a strong candidate a lookup proposed (plan 0.12 §4.3): a candidate is enough to fetch with and never enough to be an identity, because fetching is reversible and checkable and identifying is neither. A source whose own title does not match the entry is discarded rather than filed. With no CITEKEYS, every cited work that has no artifact yet.
    """
    from loom.refs.build import survey
    from loom.refs.fetch import fetch_work

    result = open_scan(quilt_path)
    result.quilt.config.fetch = result.quilt.config.fetch or allow_fetch  # this run's consent, written nowhere (DR-193)
    missing = [ck for ck in citekeys if ck not in result.bib]
    if missing:
        raise EnvError(f"not in the bibliography: {', '.join(missing)}")
    wanted = (
        [w for w in survey(result) if w.citekey in set(citekeys)]
        if citekeys
        else [w for w in survey(result) if not (w.source or w.pdf) and (w.declared or w.candidate)]
    )
    if not wanted:
        click.echo("nothing to fetch: every cited work has an artifact, or names no identifier anyone will serve")
        return
    if no_pdf:
        # the source alone extracts, and its digest is checkable against LaTeX; what it lacks is a page (plan 0.13 §4)
        note("warning: --no-pdf leaves these works with no page to read, and their page locators unverified")
    bad = 0
    for w in wanted:
        got = fetch_work(
            result.quilt, w.citekey, result.bib[w.citekey], pdf=not no_pdf, allow_candidate=not no_candidates
        )
        if got.discarded:
            bad += 1
            click.echo(f"{w.citekey}: discarded — {got.discarded}")
        elif got.refused:
            bad += 1
            click.echo(f"{w.citekey}: {got.refused}")
        else:
            what = ", ".join(x for x in ["source" if got.source else "", "pdf" if got.pdf else ""] if x)
            click.echo(f"{w.citekey}: {what} ({got.via} {got.ident})")
    if bad:
        ctx.exit(EXIT_CONTENT)


@refs.command(name="match")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
def match_command(as_json: bool, quilt_path: str | None) -> None:
    """The cited works a person has to look at: no artifact and no identifier, or a source discarded on arrival.

    Reads disk only; it never fetches and never asks a service. This is the list `loom refs build` counts on its `needs you` line.
    """
    from loom.refs.build import survey

    works = survey(result := open_scan(quilt_path))
    rows = [w for w in works if w.needs_a_person]
    if as_json:
        click.echo(
            json.dumps(
                [{"citekey": w.citekey, "cited_by": w.cited_by, "why": w.needs_a_person} for w in rows], indent=2
            )
        )
        return
    if not rows:
        click.echo("nothing needs you: every cited work has an artifact or an identifier")
        return
    for w in rows:
        title = (result.bib[w.citekey].fields.get("title") or "")[:48]
        click.echo(f"{w.citekey:<44}{w.cited_by:>3} cited  {w.needs_a_person}")
        if title:
            click.echo(f"{'':<44}    {title}")
    note("add a PDF by hand: loom refs add CITEKEY FILE")


@refs.command(name="map")
@click.argument("citekeys", nargs=-1)
@click.option("--force", is_flag=True, help="Re-map even where the recorded map matches the PDF on disk.")
@quilt_option
@click.pass_context
def map_command(ctx: click.Context, citekeys: tuple[str, ...], force: bool, quilt_path: str | None) -> None:
    """Write page text and the section map for cited works that have a PDF.

    Deterministic, eager and cheap: no model, nothing to review, and re-running costs nothing where the artifact has not changed. The page text is committed, which is what lets a coauthor who holds no PDF re-check an anchor; the token geometry an anchor's quad needs is written per page by `loom refs locate`, on demand, because it is thirty times the size.
    """
    from loom.refs.build import survey
    from loom.refs.fetch import work_dir
    from loom.refs.pages import MapRefused, is_current, write_map

    result = open_scan(quilt_path)
    root = result.quilt.root
    missing = [ck for ck in citekeys if ck not in result.bib]
    if missing:
        raise EnvError(f"not in the bibliography: {', '.join(missing)}")
    works = [w for w in survey(result) if not citekeys or w.citekey in set(citekeys)]
    done = skipped = failed = 0
    pages = sections = 0
    for w in works:
        home = work_dir(root, result.bib[w.citekey])
        pdf = home / "paper.pdf"
        if not pdf.is_file():
            continue
        if is_current(home, pdf) and not force:
            skipped += 1
            continue
        try:
            m = write_map(home, pdf)
        except MapRefused as exc:
            failed += 1
            click.echo(f"{w.citekey}: {exc}")
            continue
        done += 1
        pages += m.pages
        sections += len(m.sections)
        thin = m.pages and m.chars / m.pages < 200
        click.echo(
            f"{w.citekey}: {m.pages} pages, {len(m.sections)} sections"
            + ("  — almost no text: this PDF is probably a scan and cannot be searched or quoted" if thin else "")
            + ("  — too few sections for its length; the section map is a guess (a book?)" if m.suspect else "")
        )
    click.echo(f"{done} mapped ({pages} pages, {sections} sections), {skipped} already current, {failed} failed")
    if failed:
        ctx.exit(EXIT_CONTENT)


def resolve_works(result: ScanResult, needles: tuple[str, ...]) -> set[str]:
    """Citekeys for each argument: an exact citekey, else every entry whose author or title contains it.

    Agents reached outside loom for this twice in the first study run, grepping `refs.bib` for an author's name -- and once it mattered, because there are two Edidin-Graham 1998 papers. An argument that matches nothing is refused by name rather than answered with an empty table, which read as "nothing is known about that work".
    """
    from loom.refs.resolve import _fold

    out: set[str] = set()
    for needle in needles:
        if needle in result.bib:
            out.add(needle)
            continue
        want = _fold(needle)
        hits = {
            ck
            for ck, e in result.bib.items()
            if want
            and (
                want in _fold(ck)
                or want in _fold(e.fields.get("author", ""))
                or want in _fold(e.fields.get("title", ""))
            )
        }
        if not hits:
            raise EnvError(f"{needle!r} is not a citekey, and no entry's author or title contains it")
        out |= hits
    return out


@refs.command(name="coverage")
@click.argument("citekeys", nargs=-1)
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
@logged("coverage")
def coverage_command(citekeys: tuple[str, ...], as_json: bool, quilt_path: str | None) -> None:
    """What the quilt knows about each cited work: source, PDF, page text, digest, and proposals waiting on the author.

    A search over a partly digested corpus is a search over silence, so this is the line every other answer should be read against. Each argument is a citekey or a fragment of an author's name or a title -- `romagny`, `intrinsic normal cone` -- and a fragment that matches several works lists them all, because two papers by the same authors in the same year is exactly when guessing goes wrong.
    """
    from loom.refs.build import survey
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map

    result = open_scan(quilt_path)
    root = result.quilt.root
    wanted = resolve_works(result, citekeys)
    works = [w for w in survey(result) if not citekeys or w.citekey in wanted]
    for w in works:
        m = read_map(work_dir(root, result.bib[w.citekey]))
        w.pages, w.sections = (m.pages, len(m.sections)) if m else (0, 0)
    if as_json:
        click.echo(
            json.dumps(
                [
                    {
                        "citekey": w.citekey,
                        "cited_by": w.cited_by,
                        "source": w.source,
                        "pdf": w.pdf,
                        "pages": w.pages,
                        "sections": w.sections,
                        "digest": w.digest,
                    }
                    for w in works
                ],
                indent=2,
            )
        )
        return
    from loom.refs.proposals import load_results

    pending = {
        w.citekey: sum(1 for r in load_results(root, w.citekey).values() if r.state == "proposed") for w in works
    }
    click.echo(f"{'work':<44}{'cited':>6}{'src':>5}{'pdf':>5}{'pages':>7}{'secs':>6}{'digest':>8}{'waiting':>9}")
    for w in works:
        click.echo(
            f"{w.citekey[:43]:<44}{w.cited_by:>6}{'yes' if w.source else '-':>5}"
            f"{'yes' if w.pdf else '-':>5}{w.pages or '-':>7}{w.sections or '-':>6}{'yes' if w.digest else '-':>8}"
            f"{pending[w.citekey] or '-':>9}"
        )
    digested = sum(1 for w in works if w.digest)
    mapped = sum(1 for w in works if w.pages)
    click.echo(f"\n{digested} of {len(works)} works digested; {mapped} have page text")
    if len(works) == 1 and works[0].cited_by:
        # where, not only how often: agents dumped the whole draft to a file and grepped it to find this
        ck = works[0].citekey
        sites = sorted(
            {
                (c.src, c.postnote or "")
                for c in result.edges.cites
                if c.citekey == ck and c.file not in result.assembly.digest_files
            }
        )
        click.echo("cited by: " + "; ".join(f"{src}" + (f" [{pn}]" if pn else "") for src, pn in sites))
    if sum(pending.values()):
        click.echo(
            f"{sum(pending.values())} proposal(s) waiting on the author: loom refs verify ID, or the digest view"
        )


def _page_range(spec: str) -> tuple[int, int]:
    """`12` or `10-14` as (first, last); a refusal for anything else."""
    m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", spec)
    if not m:
        raise EnvError(f"{spec!r} is not a page or a page range (12, or 10-14)")
    lo = int(m.group(1))
    hi = int(m.group(2) or lo)
    if hi < lo:
        raise EnvError(f"{spec!r} ends before it begins")
    return lo, hi


@refs.command(name="page")
@click.argument("citekey")
@click.argument("pages")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
@click.pass_context
@logged("page")
def page_command(ctx: click.Context, citekey: str, pages: str, as_json: bool, quilt_path: str | None) -> None:
    """Print CITEKEY's page text for PAGES (`12` or `10-14`), with the section each page falls in.

    The sanctioned read. A quotation an agent proposes must come from here, because this is the text the anchor is checked against; anything quoted from elsewhere may be right and cannot be verified.
    """
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map, read_page

    result = open_scan(quilt_path)
    if citekey not in result.bib:
        raise EnvError(f"{citekey} is not in the bibliography")
    home = work_dir(result.quilt.root, result.bib[citekey])
    m = read_map(home)
    if m is None:
        raise ContentError(f"{citekey} has no page text yet; run loom refs map {citekey}")
    lo, hi = _page_range(pages)
    if lo > m.pages:
        raise ContentError(f"{citekey} has {m.pages} pages; {lo} is past the end")
    out = []
    for n in range(lo, min(hi, m.pages) + 1):
        text = read_page(home, n)
        if text is None:
            continue
        sec = m.section_of(n)
        out.append({"page": n, "section": f"{sec.n} {sec.title}".strip() if sec else "", "text": text.rstrip("\n")})
    if as_json:
        click.echo(json.dumps({"citekey": citekey, "sha256": m.sha256, "pages": out}, indent=2))
        return
    for entry_ in out:
        head = f"--- {citekey} p.{entry_['page']}"
        if entry_["section"]:
            head += f"  [{entry_['section']}]"
        click.echo(head + " " + "-" * max(0, 60 - len(head)))
        click.echo(entry_["text"])
    if not out:
        ctx.exit(EXIT_CONTENT)


@refs.command(name="grep")
@click.argument("text")
@click.option("--work", "works_only", multiple=True, help="Limit to these citekeys.")
@click.option("--limit", default=20, show_default=True, help="Stop after this many hits.")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
@logged("grep")
def grep_command(text: str, works_only: tuple[str, ...], limit: int, as_json: bool, quilt_path: str | None) -> None:
    """Search the raw page text of every mapped work for TEXT, a literal phrase (not a pattern).

    The cold-start path: before anything is digested this is the only thing that can answer, and it answers with pages to read rather than with statements. **Page text is mathematics that has been through a text layer**, so a hit is a pointer and never a quotable statement — read the page with `loom refs page`, and quote from that.
    """
    from loom.refs.build import survey
    from loom.refs.fetch import work_dir
    from loom.refs.search import grep_work

    if re.search(r"\\\||\.\*|\|\||\[\^|\\[bdswBDSW]", text):
        # an agent searched "A\|B.*C", found nothing and read that as an absence
        raise EnvError(
            f"{text!r} looks like a pattern; loom refs grep matches a literal phrase. Run it once per phrase."
        )
    result = open_scan(quilt_path)
    root = result.quilt.root
    works = [w for w in survey(result) if not works_only or w.citekey in set(works_only)]
    # every work with page text is searched before anything is truncated. Stopping at the limit would make the
    # answer depend on citation order: the first two papers would fill it and the other twelve would look empty.
    hits = []
    searched = 0
    for w in works:
        if not w.pages:
            continue
        searched += 1
        hits.extend(grep_work(work_dir(root, result.bib[w.citekey]), w.citekey, text))
    # Truncated per work, not first-come. A plain cap filled up with whichever papers came first in citation order,
    # and an agent looking for one paper's hits found them crowded out and had to rerun with --work.
    per_work: dict[str, int] = {}
    for h in hits:
        per_work[h.citekey] = per_work.get(h.citekey, 0) + 1
    each = max(1, limit // max(1, len(per_work)))
    seen: dict[str, int] = {}
    shown: list[Any] = []
    for h in hits:
        if seen.get(h.citekey, 0) < each and len(shown) < limit:
            shown.append(h)
            seen[h.citekey] = seen.get(h.citekey, 0) + 1
    if as_json:
        click.echo(
            json.dumps(
                {
                    "searched": searched,
                    "of": len(works),
                    "truncated": len(hits) > limit,
                    "hits": [
                        {"work": h.citekey, "page": h.page, "section": h.section, "context": h.context} for h in shown
                    ],
                },
                indent=2,
            )
        )
        return
    for h in shown:
        where = f"{h.citekey} p.{h.page}" + (f" [{h.section}]" if h.section else "")
        click.echo(f"{where:<52} {h.context}")
    click.echo(
        f"\n{len(hits)} hit(s) in {len({h.citekey for h in hits})} of {searched} works with page text"
        + (f" — showing {len(shown)}" if len(hits) > limit else "")
    )
    if len(hits) > len(shown):
        click.echo("per work: " + ", ".join(f"{ck} {n}" for ck, n in sorted(per_work.items(), key=lambda x: -x[1])))
    if not hits and searched < len(works):
        click.echo(f"{len(works) - searched} of {len(works)} works have no page text yet (loom refs map)")
    if shown:
        note("page text is mathematics after a text layer: read the page before quoting anything from it")


@refs.command(name="locate")
@click.argument("citekey")
@click.argument("text")
@click.option("--page", "page_no", type=int, required=True, help="The page the text is on.")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
@click.pass_context
@logged("locate")
def locate_command(
    ctx: click.Context, citekey: str, text: str, page_no: int, as_json: bool, quilt_path: str | None
) -> None:
    """Print the region of CITEKEY's page PAGE that TEXT occupies, so an anchor need not compute geometry.

    Token geometry is thirty times the size of plain page text, so it is produced for the one page asked about and kept there; nothing writes it in bulk. Where `loom serve` is running, an `open:` line follows with a link into the viewer at that page: a quad is four numbers, and what anyone wants next is to see the page it is on.
    """
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map, token_boxes
    from loom.refs.search import locate_span

    result = open_scan(quilt_path)
    if citekey not in result.bib:
        raise EnvError(f"{citekey} is not in the bibliography")
    home = work_dir(result.quilt.root, result.bib[citekey])
    m = read_map(home)
    pdf = home / "paper.pdf"
    if m is None or not pdf.is_file():
        raise ContentError(f"{citekey} has no mapped PDF; run loom refs map {citekey}")
    xml = token_boxes(pdf, page_no, home)
    span = locate_span(xml, text, page_no)
    if span is None:
        click.echo(f"not found on {citekey} p.{page_no}")
        ctx.exit(EXIT_CONTENT)
        return
    if as_json:
        click.echo(
            json.dumps(
                {"kind": "pdf", "sha256": m.sha256, "page": span.page, "quads": [list(q) for q in span.lines]},
                indent=2,
            )
        )
    else:
        x0, y0, x1, y1 = span.quad
        lines = f"{len(span.lines)} line{'s' if len(span.lines) != 1 else ''}"
        click.echo(f"{citekey} p.{span.page}  {x0:.1f} {y0:.1f} {x1:.1f} {y1:.1f}  ({span.words} words, {lines})")
        # A quad is four numbers; what anyone wants next is to see the page it is on. The line is printed only when a
        # server is actually listening, because a dead link is worse than none.
        from loom.render.serve import open_url

        where = open_url(result.quilt.root, f"library/{citekey}?page={span.page}")
        if where:
            click.echo(f"open: {where}")


def _work_home(result: ScanResult, citekey: str) -> Path:
    from loom.refs.fetch import work_dir

    if citekey not in result.bib:
        raise EnvError(f"{citekey} is not in the bibliography")
    return work_dir(result.quilt.root, result.bib[citekey])


def _find_result(result: ScanResult, target: str) -> tuple[str, str, dict[str, Any]]:
    """(citekey, id, that work's results), raising loom's own refusal rather than a LookupError."""
    from loom.refs.proposals import find_result

    try:
        return find_result(result, target)
    except LookupError as exc:
        raise ContentError(str(exc)) from exc


@refs.command(name="propose")
@click.argument("citekey")
@click.option(
    "--local", required=True, help="The paper's own name for the result: thm-4.1, cor-2.3.1, eq-1, thm-star-2."
)
@click.option("--page", "page_spec", default=None, help="The page the statement is on, or 353-354 if it runs over.")
@click.option(
    "--source-file",
    default=None,
    metavar="FILE",
    help="Quote the work's LaTeX source instead of a page: a file under the directory `loom refs path` prints.",
)
@click.option("--source-text", required=True, help="The paper's own words, verbatim; checked against the page or file.")
@click.option(
    "--statement", required=True, help="The same result as LaTeX, in the paper's words only; the author verifies it."
)
@click.option("--taxon", default=None, help="theorem, lemma, definition, equation, …; read off --local when omitted.")
@click.option("--number", default="", help="The paper's numbers when it states several results together: '3.2, 3.3'.")
@click.option("--level", type=click.Choice(["1", "3"]), default="3", show_default=True, help="1 is a main result.")
@click.option("--supersedes", default=None, metavar="ID", help="Re-propose something discarded, recording the chain.")
@click.option("--session", "run_dir", default=None, envvar="LOOM_SESSION", help="The session proposing this.")
@click.option("--json", "as_json", is_flag=True, help="Print the stored record as JSON.")
@quilt_option
@click.pass_context
def propose_command(
    ctx: click.Context,
    citekey: str,
    local: str,
    page_spec: str | None,
    source_file: str | None,
    source_text: str,
    statement: str,
    taxon: str | None,
    number: str,
    level: str,
    supersedes: str | None,
    run_dir: str | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Propose one result of CITEKEY, its quotation checked against the page or source file it claims to come from.

    The only write an agent makes to the reference layer. SOURCE-TEXT must appear on PAGE — whitespace, hyphenation across lines and ligatures are normalised, nothing else is — and on failure nothing is stored and the page's text is printed so the quotation can be corrected in the same turn. For a work with a LaTeX source, quote the source with --source-file instead: the mathematics is there, and in a PDF's text layer it is often control bytes. A proposal lands in `digests/CITEKEY.proposed.tex`, which no bundle inputs, and waits there for the author to verify or discard it.
    """
    from loom.cli._common import agent_marker
    from loom.refs.pages import read_map, read_pages
    from loom.refs.proposals import (
        PROPOSED,
        Anchor,
        Result,
        append_event,
        check_local,
        discarded_locals,
        load_results,
        quilt_env,
        save_results,
        write_proposed_tex,
    )
    from loom.refs.search import find_in_page, words_not_on_page

    if (page_spec is None) == (source_file is None):
        raise EnvError("give --page for a page of the PDF, or --source-file for the work's LaTeX source: one of them")
    try:
        taxon, local_number = check_local(local, taxon)
    except ValueError as exc:
        raise ContentError(str(exc)) from exc
    result = open_scan(quilt_path)
    root = result.quilt.root
    home = _work_home(result, citekey)

    # a discard the agent cannot see is a discard it will make again (§5.5)
    gone = discarded_locals(root, citekey)
    if local in gone and not supersedes:
        raise ContentError(
            f"{citekey} {local} was discarded: {gone[local]}\n"
            f"If this proposal answers that, pass --supersedes to record the chain."
        )

    if source_file is not None:
        anchor, where = _source_anchor(ctx, root, home, citekey, source_file, source_text)
        page_no = 0
    else:
        assert page_spec is not None
        m = read_map(home)
        if m is None:
            raise ContentError(f"{citekey} has no page text; run loom refs map {citekey} first")
        page_no, last = _page_range(page_spec)
        if last - page_no > 3:
            raise EnvError(f"{page_spec} spans {last - page_no + 1} pages; a statement is anchored to at most four")
        page_text = read_pages(home, page_no, last)
        if page_text is None:
            raise ContentError(f"{citekey} has {m.pages} pages; {page_spec} runs past the end")
        where = f"p.{page_no}" if last == page_no else f"pp.{page_no}-{last}"
        if not find_in_page(page_text, source_text):
            click.echo(f"refused: that text is not on {citekey} {where}. The page reads:\n", err=True)
            click.echo(page_text.rstrip("\n"))
            click.echo("\nNothing was stored. Quote from this text and propose again.", err=True)
            ctx.exit(EXIT_CONTENT)
        anchor = Anchor(kind="pdf", sha256=m.sha256, page=page_no, last=last if last > page_no else 0)

    wrapper = re.search(
        r"\\(begin|end)\s*\{(theorem|lemma|proposition|corollary|definition|remark|example|construction|conjecture|claim|notation)\*?\}|\\label\s*\{",
        statement,
    )
    if wrapper:
        # Thirteen of thirteen first attempts by two agents wrapped the statement in its own environment -- one had
        # read a note about exactly this mistake -- and loom wrapped it again: a nested environment, the label doubled.
        # A note does not stop it, because a result written as LaTeX looks like an environment. Refusing does.
        raise ContentError(
            f"--statement contains {wrapper.group(0)!r}. The statement is the body only: loom writes the "
            f"\\begin{{{taxon}}}, the locator and the \\label itself. Pass the text between them."
        )
    results = load_results(root, citekey)
    if level != "1" and not any(r.level == 1 and r.state != "discarded" for r in results.values()):
        raise ContentError(
            f"{citekey} has no level-1 result yet. Read the abstract and introduction and propose the main results "
            f"first (--level 1); everything deeper is cheaper once they are there."
        )

    prefix = result.assembly.prefix_of(citekey)
    if run_dir:
        # "ai/runs/2026-...-fixed-stacks" and "2026-...-fixed-stacks" are one run; provenance showed both spellings
        run_dir = Path(run_dir).name
    rid = f"{prefix}-{local}" if not local.startswith(prefix) else local
    if rid in results:
        prior = results[rid]
        mine = (
            bool(run_dir)
            and prior.state == "proposed"
            and any(
                o.get("act") == "proposed" and Path(str(o.get("by", ""))).name == Path(run_dir or "").name
                for o in prior.origin
            )
        )
        if supersedes and supersedes == rid and mine:
            # A run correcting its own proposal before anyone has looked at it. Without this an agent that made a
            # mistake could only re-propose under a new id -- `thm-2.1-clean` -- and eleven results became twenty-two
            # for the author to review. It touches nothing the author has decided: the record is still `proposed`.
            results.pop(rid)
            append_event(
                root, citekey, {"event": "withdrawn", "id": rid, "local": local, "run": Path(run_dir or "").name}
            )
        elif supersedes and supersedes == rid and prior.state == "discarded":
            # The chain lives in the log, which `discarded_locals` replays and `loom refs why` prints. Keeping the
            # discarded record here as well would force the new one to take a mangled id -- and an id is how a
            # locator finds a result (contract §6.2), so it may not carry the history of how it was arrived at.
            results.pop(rid)
        else:
            raise ContentError(f"{rid} is already recorded ({prior.state}); loom refs why {rid}")
    number = number or local_number
    from loom.refs.proposals import numbers_of

    nums = numbers_of(number)
    if len(nums) > 1:
        # the id is the first number's; the others ride as aliases, so a citation to either finds it
        local = f"{local.split('-')[0]}-{nums[0]}"
        rid = f"{prefix}-{local}"
        if rid in results:
            raise ContentError(f"{rid} is already recorded ({results[rid].state}); loom refs why {rid}")
    r = Result(
        id=rid,
        local=local,
        taxon=taxon,
        number=number,
        statement=statement,
        source_text=source_text,
        anchor=anchor,
        env=quilt_env(result, taxon),
        level=int(level),
        cls="anchored",
        state=PROPOSED,
        origin=[{"act": "proposed", "by": run_dir or "", "when": stamp()}],
        supersedes=supersedes or "",
    )
    results[rid] = r
    save_results(root, citekey, results)
    write_proposed_tex(root, citekey, prefix, results)
    append_event(
        root,
        citekey,
        {
            "event": "proposed",
            "id": rid,
            "local": local,
            "page": page_no,
            "run": run_dir or "",
            "supersedes": supersedes or "",
        },
    )
    if as_json:
        click.echo(json.dumps(r.to_json(), indent=2))
        return
    click.echo(f"proposed {rid} (source text checked against {where})")
    added = words_not_on_page(statement, source_text)
    if added:
        # a gloss is the commonest correction an author makes, and a line in the orientation did not stop it
        click.echo(
            f"not in the quoted {'page' if page_no else 'source'} text: {', '.join(added)}. A statement is the "
            f"paper's words only; if these are yours, correct it now with --supersedes {rid}, and put the gloss in "
            "your notes file.",
            err=True,
        )
    if agent_marker():
        # the author's verb is not the agent's next step, and "verified" is the author's word (plan 0.12 §5.6)
        click.echo(f"in digests/{citekey}.proposed.tex, waiting for the author, who verifies or discards it")
    else:
        click.echo(f"in digests/{citekey}.proposed.tex — nothing inputs that file until you verify it")
        note(f"loom refs verify {rid}   |   loom refs discard {rid} --reason '…'")


def _source_anchor(
    ctx: click.Context, root: Path, home: Path, citekey: str, source_file: str, source_text: str
) -> tuple[Any, str]:
    """A LaTeX anchor for a quotation of the work's source (contract §9.3), or the refusal that says what is there."""
    import hashlib

    from loom.anchors import Anchor
    from loom.refs.proposals import locate_quote

    src = home / "src"
    given = Path(source_file)
    f = (given if given.is_absolute() else (src / given if (src / given).is_file() else home / given)).resolve()
    if not f.is_file() or not f.is_relative_to(home.resolve()):
        tex = sorted(p.relative_to(src).as_posix() for p in src.rglob("*.tex")) if src.is_dir() else []
        raise ContentError(
            f"{source_file} is not a file of {citekey}'s source; "
            + (f"it has {', '.join(tex[:12])}" if tex else f"{citekey} has no source (loom refs fetch {citekey})")
        )
    data = f.read_bytes()
    # surrogateescape round-trips any byte, so the offsets below are the file's own even in a Latin-1 source
    text = data.decode("utf-8", "surrogateescape")
    rel = f.relative_to(root.resolve()).as_posix()
    span = locate_quote(text, source_text)
    if span is None:
        head = " ".join(source_text.split()[:3])
        near = [row for row in text.splitlines() if head and head in " ".join(row.split())][:5]
        click.echo(f"refused: that text is not in {rel}. Quote the file exactly; only whitespace may differ.", err=True)
        if near:
            click.echo("Lines that begin the same way:\n" + "\n".join(near))
        click.echo("Nothing was stored.", err=True)
        ctx.exit(EXIT_CONTENT)
        raise AssertionError  # ctx.exit raises; this keeps the type checker's flow honest
    a, b = (len(text[:i].encode("utf-8", "surrogateescape")) for i in span)
    anchor = Anchor(kind="tex", sha256=hashlib.sha256(data).hexdigest(), path=rel, bytes=[a, b])
    return anchor, rel


@refs.command(name="verify")
@click.argument("target")
@click.option("--statement", default=None, help="Your own rendering, replacing the proposed one before verifying.")
@click.option("--local", default=None, help="The paper's own name for it, correcting the proposal's: cor-3.2.1.")
@click.option("--taxon", default=None, help="The environment, when --local does not imply it.")
@click.option("--author", default=None, help="Who verified, when the user config and git do not say.")
@click.option("--yes", "-y", is_flag=True, help="Skip the question; you have read both texts.")
@quilt_option
def verify_command(
    target: str,
    statement: str | None,
    local: str | None,
    taxon: str | None,
    author: str | None,
    yes: bool,
    quilt_path: str | None,
) -> None:
    """Record that a transcription is faithful: promote a proposal into the digest, or re-verify one already there.

    Two claims must not share a word. `loom accept` says *I have proved this, or I am satisfied it holds* and is about your own mathematics; this says *this copy is faithful to the paper it came from*, and settles nothing mathematical. With --statement you fix the rendering first: you are editing `statement`, never `source_text`, so the anchor is untouched and the result stays re-checkable — and both parties are recorded, because a record that credits an agent with a sentence you wrote cannot be audited.
    """
    from loom.cli._common import refuse_under_agent
    from loom.refs.proposals import page_context, verify_result
    from loom.scan.quilt import resolve_author

    refuse_under_agent(
        "loom refs verify",
        "Verify in the digest view, where the page and the rendering are side by side, or in your own terminal. "
        "An agent proposes; it does not vouch for its own reading.",
        author,
    )
    result = open_scan(quilt_path)
    who = resolve_author(author, result.quilt.root)[0]
    citekey, rid, results = _find_result(result, target)
    r = results[rid]
    # §5.3: nothing may offer verify without showing both texts, and a terminal is a surface like any other
    context, found = page_context(result.quilt.root, r)
    if r.anchor.kind == "pdf":
        click.echo(f"{rid}   p.{r.anchor.page} of {citekey}")
        where = "(around the quoted span)" if found else "(quoted span not located; whole page)"
        click.echo(f"\n--- the page {where} ---")
    else:
        # a result quoted from, or extracted out of, the paper's own LaTeX has no page
        click.echo(f"{rid}   from {r.anchor.path or citekey + ' (its source)'}")
        click.echo("\n--- the source ---")
    click.echo(context)
    click.echo("\n--- rendered as ---")
    click.echo((statement or r.statement).strip())
    if not yes:
        if not sys.stdin.isatty():
            raise EnvError("verifying needs you to have read both texts; pass --yes once you have")
        click.confirm("\nis the rendering faithful to the page?", abort=True)
    try:
        for line in verify_result(result, target, statement, who, local=local, taxon=taxon):
            click.echo(line)
    except LookupError as exc:
        raise ContentError(str(exc)) from exc


@refs.command(name="discard")
@click.argument("target")
@click.option("--reason", required=True, help="Why it should not stand; the agent that proposed it is shown this.")
@click.option("--author", default=None, help="Who discarded, when the user config and git do not say.")
@quilt_option
def discard_command(target: str, reason: str, author: str | None, quilt_path: str | None) -> None:
    """Discard a proposed result, with a reason.

    The reason is not a courtesy. `loom refs propose` refuses a discarded work-and-local-id and returns it, so the agent that proposed the thing learns why in the turn it fails rather than proposing it again next session. Nothing is deleted: the log keeps it and `loom refs why` reports it.
    """
    from loom.cli._common import refuse_under_agent
    from loom.refs.proposals import discard_result
    from loom.scan.quilt import resolve_author

    refuse_under_agent("loom refs discard", "Discard in the digest view or in your own terminal.", author)
    result = open_scan(quilt_path)
    who = resolve_author(author, result.quilt.root)[0]
    try:
        click.echo(discard_result(result, target, reason, who))
    except LookupError as exc:
        raise ContentError(str(exc)) from exc


@refs.command(name="why")
@click.argument("target")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
@logged("why")
def why_command(target: str, as_json: bool, quilt_path: str | None) -> None:
    """Where a result came from, what state it is in, and who changed it.

    Provenance names every party, not just the first: a record that credits an agent with a sentence you wrote cannot be audited.
    """
    from loom.refs.proposals import edit_diff, read_events

    result = open_scan(quilt_path)
    citekey, rid, results = _find_result(result, target)
    r = results[rid]
    chain = [e for e in read_events(result.quilt.root, citekey) if e.get("id") == rid or e.get("supersedes") == rid]
    if as_json:
        click.echo(json.dumps({"work": citekey, **r.to_json(), "events": chain}, indent=2))
        return
    click.echo(f"{rid}")
    click.echo(f"  state      {'transcription verified' if r.state == 'verified' else r.state}")
    click.echo(f"  work       {citekey}")
    click.echo(
        f"  anchor     p.{r.anchor.page} of sha256:{r.anchor.sha256[:12]}  ({r.anchor.kind}, level {r.level}, {r.cls})"
    )
    for o in r.origin:
        click.echo(f"  {o.get('act', ''):<10} {o.get('by') or '—'}  {str(o.get('when', ''))[:19]}")
    diff = edit_diff(r)
    if diff:
        # what the author changed, which is what a later proposer should learn from
        click.echo("\n  the author's edit (- proposed, + verified):")
        for line in diff:
            click.echo(f"    {line}")
    if r.supersedes:
        click.echo(f"  supersedes {r.supersedes}")
    for e in chain:
        if e.get("event") == "discarded":
            click.echo(f"  discarded  {e.get('reason', '')}")


@refs.command(name="drop")
@click.option("--work", "work_ck", default=None, help="Everything recorded for this work.")
@click.option("--session", "run_id", default=None, envvar="LOOM_SESSION", help="Everything proposed in this session.")
@click.option("--unverified", is_flag=True, help="Every result not yet verified, in every work.")
@click.option("--yes", "-y", is_flag=True, help="Do not ask.")
@quilt_option
def drop_command(work_ck: str | None, run_id: str | None, unverified: bool, yes: bool, quilt_path: str | None) -> None:
    """Remove recorded results. The store is safe to delete: dropping it costs re-reading, never correctness.

    A verified node already written into `digests/<citekey>.tex` is the author's file and is never touched here; only the records and the proposals are removed.
    """
    from loom.refs.proposals import append_event, load_results, results_path, save_results, write_proposed_tex

    if sum(map(bool, [work_ck, run_id, unverified])) != 1:
        raise EnvError("give exactly one of --work, --session or --unverified")
    result = open_scan(quilt_path)
    root = result.quilt.root
    works = (
        [work_ck]
        if work_ck
        else [p.name[: -len(".results.json")] for p in sorted((root / "digests").glob("*.results.json"))]
    )
    doomed: list[tuple[str, str]] = []
    for ck in works:
        for rid, r in load_results(root, ck).items():
            if (
                work_ck
                or (unverified and r.state != "verified")
                or (run_id and any(o.get("by") == run_id for o in r.origin))
            ):
                doomed.append((ck, rid))
    if not doomed:
        click.echo("nothing to drop")
        return
    for ck, rid in doomed[:10]:
        click.echo(f"  {ck}  {rid}")
    if len(doomed) > 10:
        click.echo(f"  … and {len(doomed) - 10} more")
    if not yes:
        if not sys.stdin.isatty():
            raise EnvError("dropping needs confirmation; pass --yes")
        click.confirm(f"drop {len(doomed)} record(s)?", abort=True)
    for ck in {c for c, _ in doomed}:
        results = load_results(root, ck)
        for _, rid in [d for d in doomed if d[0] == ck]:
            results.pop(rid, None)
            append_event(root, ck, {"event": "dropped", "id": rid})
        if results:
            save_results(root, ck, results)
        else:
            results_path(root, ck).unlink(missing_ok=True)
        write_proposed_tex(root, ck, result.assembly.prefix_of(ck), results)
    click.echo(f"dropped {len(doomed)} record(s); verified nodes already in digests/ were not touched")


@refs.command(name="link")
@click.option("--from", "frm", required=True, metavar="ID", help="The result the claim is about.")
@click.option("--to", "to", required=True, metavar="ID", help="The result it relates to.")
@click.option("--kind", required=True, help="same-notion, generalises, specialises, depends-on, contradicts.")
@click.option("--why", required=True, help="One or two sentences. This is what you read six months later.")
@click.option(
    "--session", "run_dir", default=None, envvar="LOOM_SESSION", help="The session asserting it; an agent must say which."
)
@click.option("--author", default=None, help="Who asserted it, when the user config and git do not say.")
@quilt_option
def link_command(
    frm: str, to: str, kind: str, why: str, run_dir: str | None, author: str | None, quilt_path: str | None
) -> None:
    """Assert a typed relation between two results, with a reason.

    **Nobody verifies this and it says so.** A relation has no page span to check it against, so a verification step would be theatre; a link is an assertion, attributed to whoever made it. Links are never citable, never enter a closure, and are never written into a digest — they are navigation, not mathematics.
    """
    from loom.refs.links import add_link
    from loom.refs.proposals import find_result
    from loom.scan.quilt import resolve_author

    result = open_scan(quilt_path)
    root = result.quilt.root
    for end in (frm, to):
        if end not in result.nodes:
            try:
                find_result(result, end)
            except LookupError as exc:
                raise ContentError(f"{end} is not a result in any digest: {exc}") from exc
    from loom.cli._common import agent_marker

    if run_dir:
        # who asserted it, as `loom comment` records it: an assertion is somebody's, and a reader weighs it by whose
        who = Path(run_dir).name
    elif agent_marker():
        # an agent with no --session would otherwise be recorded as the author, by way of git: eleven links in the second
        # study run were, and a reader could not tell the author's assertions from an agent's
        raise EnvError(
            "an agent is running this shell: pass --session SESSION, or --author, so the link says who asserted it"
        )
    else:
        who = resolve_author(author, root)[0]
    try:
        made = add_link(root, frm, to, kind, why, who)
    except ValueError as exc:
        raise EnvError(str(exc)) from exc
    click.echo(f"{made.id}: {frm} {kind} {to}")
    note("asserted, not checked: a link is somebody's reading, and every surface that shows it says so")


@refs.command(name="links")
@click.argument("target", required=False)
@click.option("--depth", default=1, show_default=True, help="Follow links this many hops out from TARGET.")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
@logged("links")
def links_command(target: str | None, depth: int, as_json: bool, quilt_path: str | None) -> None:
    """Links touching TARGET, out to --depth hops, or every link when TARGET is omitted.

    An agent walking a chain of results called this once per node; --depth walks it in one.
    """
    from loom.refs.links import KINDS, read_links, touching

    result = open_scan(quilt_path)
    root = result.quilt.root
    if target:
        frontier, seen_ids, found = {target}, set(), []
        for _ in range(max(1, depth)):
            nxt: set[str] = set()
            for key in frontier:
                for x in touching(root, key):
                    if x.id not in seen_ids:
                        seen_ids.add(x.id)
                        found.append(x)
                        nxt |= {x.frm, x.to}
            frontier = nxt - frontier
    else:
        found = read_links(root)
    if as_json:
        click.echo(json.dumps([x.to_json() for x in found], indent=2))
        return
    if not found:
        click.echo("no links yet" if not target else f"nothing links {target}")
        return
    for x in found:
        click.echo(f"{x.id}  {x.frm}")
        click.echo(f"{'':<10}{KINDS.get(x.kind, x.kind)} {x.to}")
        click.echo(f"{'':<10}{x.why}  — {x.by or 'unattributed'}")


@refs.command(name="unlink")
@click.argument("link_id")
@quilt_option
def unlink_command(link_id: str, quilt_path: str | None) -> None:
    """Remove a link."""
    from loom.refs.links import remove_link

    result = open_scan(quilt_path)
    try:
        gone = remove_link(result.quilt.root, link_id)
    except LookupError as exc:
        raise ContentError(str(exc)) from exc
    click.echo(f"removed {gone.id}: {gone.frm} {gone.kind} {gone.to}")


@refs.command(name="recheck")
@click.argument("citekeys", nargs=-1)
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
@click.pass_context
def recheck_command(ctx: click.Context, citekeys: tuple[str, ...], as_json: bool, quilt_path: str | None) -> None:
    """Re-read every verified result's anchor and report what moved. It does not re-check extraction: a mis-numbered or missing result in a mechanical digest is invisible to it.

    This is what makes `transcription verified` a claim a command can falsify. It re-reads the page the anchor names and compares it to the stored `source_text`; it never re-verifies anything by itself, because re-verifying is a person saying the copy is still faithful, which is `loom refs verify`. **A verified node's LaTeX is never re-checked** — that rendering was judged by a person once, and re-judging it mechanically would claim a check that does not exist.
    """
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map, read_pages
    from loom.refs.proposals import VERIFIED, load_results, locate_quote
    from loom.refs.search import find_in_page

    result = open_scan(quilt_path)
    root = result.quilt.root
    works = citekeys or tuple(
        p.name[: -len(".results.json")] for p in sorted((root / "digests").glob("*.results.json"))
    )
    rows: list[dict[str, Any]] = []
    checked = 0
    for ck in works:
        if ck not in result.bib:
            continue
        home = work_dir(root, result.bib[ck])
        m = read_map(home)
        for rid, r in load_results(root, ck).items():
            if r.state != VERIFIED or r.cls == "mechanical":
                continue  # a mechanical result is its own source; there is nothing to re-read
            if r.anchor.kind == "tex" and r.anchor.path:
                checked += 1
                # the source is fetched, not committed: a fresh clone re-reads it after loom refs fetch
                try:
                    text = (root / r.anchor.path).read_bytes().decode("utf-8", "surrogateescape")
                except OSError:
                    rows.append({"id": rid, "work": ck, "moved": "file-gone", "why": f"{r.anchor.path} is not here"})
                    continue
                if locate_quote(text, r.source_text) is None:
                    rows.append(
                        {
                            "id": rid,
                            "work": ck,
                            "moved": "transcription-changed",
                            "why": f"{r.anchor.path} no longer reads that way",
                        }
                    )
                continue
            if r.anchor.kind != "pdf" or not r.anchor.page:
                continue
            checked += 1
            if m is None:
                rows.append({"id": rid, "work": ck, "moved": "no-page-text", "why": "run loom refs map"})
                continue
            if m.sha256 and r.anchor.sha256 and m.sha256 != r.anchor.sha256:
                rows.append(
                    {
                        "id": rid,
                        "work": ck,
                        "moved": "version_mismatch",
                        "why": "the artifact is not the one this was read from",
                    }
                )
                continue
            # the whole span: a verified statement over a page break is re-read over both pages, not its first
            page = read_pages(home, r.anchor.page, max(r.anchor.page, r.anchor.last))
            if page is None:
                rows.append(
                    {"id": rid, "work": ck, "moved": "page-gone", "why": f"p.{r.anchor.page} is no longer there"}
                )
            elif not find_in_page(page, r.source_text):
                rows.append(
                    {
                        "id": rid,
                        "work": ck,
                        "moved": "transcription-changed",
                        "why": f"p.{r.anchor.page} no longer reads that way",
                    }
                )
    if as_json:
        click.echo(json.dumps({"checked": checked, "moved": rows}, indent=2))
        return
    for row in rows:
        click.echo(f"{row['id'][:58]:<60}{row['moved']:<24}{row['why']}")
    click.echo(f"{checked} verified anchor(s) re-read; {len(rows)} moved")
    if rows:
        note("read the page again and loom refs verify what still holds")
        ctx.exit(EXIT_CONTENT)


@refs.command(name="find")
@click.argument("text")
@click.option("--work", "works_only", multiple=True, help="Limit to these citekeys.")
@click.option("--limit", default=15, show_default=True, help="Stop showing after this many.")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
@logged("find")
def find_command(text: str, works_only: tuple[str, ...], limit: int, as_json: bool, quilt_path: str | None) -> None:
    """Search the statements this corpus has digested.

    **Every answer carries how much of the corpus it could have searched**, because a search over a partly digested corpus is a search over silence and a result set that does not say so reads like a finding. When nothing matches, the fallback is named.
    """
    from loom.refs.proposals import load_results
    from loom.refs.search import normalize

    result = open_scan(quilt_path)
    root = result.quilt.root
    wanted = normalize(text).lower()
    works = [p.name[: -len(".results.json")] for p in sorted((root / "digests").glob("*.results.json"))]
    if works_only:
        works = [w for w in works if w in set(works_only)]
    hits: list[dict[str, Any]] = []
    searched = 0
    for ck in works:
        results = load_results(root, ck)
        if results:
            searched += 1
        for rid, r in results.items():
            if r.state == "discarded":
                continue
            hay = normalize(f"{r.statement} {r.source_text}").lower()
            if wanted and wanted in hay:
                hits.append(
                    {"id": rid, "work": ck, "state": r.state, "level": r.level, "page": r.anchor.page, "class": r.cls}
                )
    total = len({p.name for p in (root / "digests").glob("*.results.json")})
    every = len(result.bib)
    if as_json:
        click.echo(
            json.dumps({"results": len(hits), "searched": searched, "of": every, "hits": hits[:limit]}, indent=2)
        )
        return
    # grouped by work, a few from each, as grep is: 149 unranked hits for "localization" in the second study run
    by_work: dict[str, int] = {}
    for h in hits:
        by_work[h["work"]] = by_work.get(h["work"], 0) + 1
    each = max(1, limit // max(1, len(by_work)))
    taken: dict[str, int] = {}
    shown_hits: list[dict[str, Any]] = []
    for h in hits:
        if taken.get(h["work"], 0) < each and len(shown_hits) < limit:
            shown_hits.append(h)
            taken[h["work"]] = taken.get(h["work"], 0) + 1
    for h in shown_hits:
        flag = " (proposed)" if h["state"] == "proposed" else ""
        where = f"p.{h['page']}" if h["page"] else h["class"]
        click.echo(f"{h['id'][:58]:<60}{where:<10}level {h['level']}{flag}")
    click.echo(
        f"\nresults: {len(hits)} in {len(by_work)} works"
        + (f" — showing {len(shown_hits)}" if len(hits) > len(shown_hits) else "")
    )
    if len(hits) > len(shown_hits):
        click.echo("per work: " + ", ".join(f"{w} {n}" for w, n in sorted(by_work.items(), key=lambda x: -x[1])))
    click.echo(f"coverage: {total} of {every} works digested")
    if not hits:
        click.echo(f"try: loom refs grep {text!r}")


@refs.command(name="ingest")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Say what would be filed and file nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
def ingest_command(directory: Path, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Match every PDF under DIRECTORY to a bibliography entry and file the ones that are unambiguous.

    Three signals: an identifier in the text of the first pages, the paper's own title, and the filename. **Two agreeing signals attach**, and an identifier read off the page attaches on its own. Everything else is listed by `loom refs match` with its evidence, because a wrong PDF filed against the right entry is worse than an unfiled one — the corpus this was built against has 25 files for 22 entries, eleven of which match nothing at all.
    """
    import shutil

    from loom.refs.fetch import work_dir
    from loom.refs.ingest import look_at

    result = open_scan(quilt_path)
    root = result.quilt.root
    pdfs = sorted(p for p in directory.rglob("*.pdf") if p.is_file())
    if not pdfs:
        raise EnvError(f"no PDFs under {directory}")
    rows: list[dict[str, Any]] = []
    filed = 0
    for pdf in pdfs:
        cand = look_at(pdf, result.bib)
        ck, score, sigs = cand.best()
        row: dict[str, Any] = {
            "file": pdf.name,
            "pages": cand.pages,
            "citekey": ck,
            "score": round(score, 3),
            "signals": [{"kind": s.kind, "strength": s.strength, "detail": s.detail} for s in sigs],
            "filed": False,
        }
        if ck and cand.attachable:
            dest = work_dir(root, result.bib[ck]) / "paper.pdf"
            if dest.exists():
                row["skipped"] = "already has a PDF"
            elif not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(pdf, dest)
                row["filed"] = True
                filed += 1
            else:
                row["filed"] = True
        rows.append(row)
    if as_json:
        click.echo(json.dumps({"pdfs": len(pdfs), "filed": filed, "works": rows}, indent=2))
        return
    for row in rows:
        mark = "+" if row["filed"] else ("·" if row.get("skipped") else "?")
        kinds = ",".join(s["kind"] for s in row["signals"]) or "nothing"
        click.echo(f"{mark} {row['file'][:46]:<48}{(row['citekey'] or '—')[:34]:<36}{kinds}")
    unmatched = [r for r in rows if not r["filed"] and not r.get("skipped")]
    click.echo(f"\n{len(pdfs)} PDFs; {filed} filed{' (dry run)' if dry_run else ''}; {len(unmatched)} for you")
    if unmatched:
        note("a wrong PDF against the right entry is worse than an unfiled one: loom refs add CITEKEY FILE")


@refs.command(name="overview")
@click.argument("citekey")
@quilt_option
@click.pass_context
@logged("overview")
def overview_command(ctx: click.Context, citekey: str, quilt_path: str | None) -> None:
    """Print a digest's Overview: the paper's own framing, which is prose and so is no result.

    Agents read it from the digest's `.tex` by hand in every study iteration -- it is where a paper says which results it considers main and what it assumes throughout, and no other command reaches it.
    """
    from loom.refs.proposals import digest_path

    result = open_scan(quilt_path)
    ck = next(iter(resolve_works(result, (citekey,))), citekey)
    path = digest_path(result.quilt.root, ck)
    if not path.is_file():
        raise ContentError(f"{ck} has no digest; loom refs coverage says what it has")
    text = path.read_text(encoding="utf-8")
    m = re.search(
        r"\\section\*\{Overview\}(.*?)(?=\\section|\\begin\{(?:theorem|lemma|proposition|definition|corollary)|\Z)",
        text,
        re.S,
    )
    if not m or not m.group(1).strip():
        click.echo(f"{ck}'s digest has no Overview")
        ctx.exit(EXIT_CONTENT)
        return
    click.echo(m.group(1).strip())


@refs.command(name="unreadable")
@click.argument("citekey")
@click.option("--why", default=None, help="Why no document can be held for this work; required unless --undo.")
@click.option("--undo", is_flag=True, help="Withdraw the declaration; --why then says why it was wrong.")
@click.option("--author", default=None, help="Who declared it, when the user config and git do not say.")
@quilt_option
def unreadable_command(citekey: str, why: str | None, undo: bool, author: str | None, quilt_path: str | None) -> None:
    """Declare that CITEKEY has no document loom can hold, and stop it being asked for.

    Nothing in a bibliography entry says that the Stacks Project is a living work with no fixed version, so loom would chase a PDF that does not exist on every build. This records the claim -- in loom's own file, never in your `.bib` -- and the invariant's lint goes quiet for the work while `loom refs build` lists it in a section of its own. It is a claim about the world, so it is yours to make and an agent is refused.
    """
    from loom.cli._common import refuse_under_agent
    from loom.refs.unreadable import declarations, declare
    from loom.scan.quilt import resolve_author

    refuse_under_agent(
        "loom refs unreadable",
        "Whether a work can be obtained at all is the author's claim about the world, not something to infer from a "
        "failed fetch. Report what you could not find, and let the author declare it.",
        author,
    )
    if not why:
        raise EnvError("--why is required: the reason is what a reader of this file has to go on")
    result = open_scan(quilt_path)
    root = result.quilt.root
    if citekey not in result.bib:
        raise ContentError(f"{citekey} is not in the bibliography; this declaration is keyed by citekey")
    standing = declarations(root, "unreadable").get(citekey)
    if undo and standing is None:
        raise ContentError(f"{citekey} is not declared unreadable")
    if not undo and standing is not None:
        raise ContentError(f"{citekey} is already declared unreadable ({standing.why}); --undo withdraws it")
    who = resolve_author(author, root)[0]
    declare(root, "unreadable", citekey, why, who, undo=undo)
    click.echo(f"{citekey} is no longer declared unreadable" if undo else f"{citekey} declared unreadable: {why}")


@refs.command(name="forget")
@click.argument("target")
@click.option("--why", default=None, help="Why the store should stop offering it; required unless --undo.")
@click.option("--undo", is_flag=True, help="Withdraw the tombstone, so the document is offered again.")
@click.option("--author", default=None, help="Who forgot it, when the user config and git do not say.")
@quilt_option
def forget_command(target: str, why: str | None, undo: bool, author: str | None, quilt_path: str | None) -> None:
    """Stop the store offering a bibliography entry for TARGET, a citekey or a content hash.

    The store is a seed of last resort: a document nobody's entry names is offered one on the next scan, from the copy ledger's record of how it arrived. That is right until you have deliberately deleted the entry, at which point the offer is loom undoing your decision every time. This is the tombstone that stops it, and like every deletion in loom it removes nothing -- the document stays in the store and the ledger keeps its arrival.
    """
    from loom.cli._common import refuse_under_agent
    from loom.refs.scan import load_ledger
    from loom.refs.unreadable import declarations, declare
    from loom.scan.quilt import resolve_author

    refuse_under_agent(
        "loom refs forget",
        "A tombstone says the author decided against this document. Say what you found and let them decide.",
        author,
    )
    if not why:
        raise EnvError("--why is required: a tombstone with no reason cannot be judged later")
    result = open_scan(quilt_path)
    root = result.quilt.root
    key = _forget_key(root, target, result.bib)
    standing = declarations(root, "forget").get(key)
    if undo and standing is None:
        raise ContentError(f"{key} is not forgotten")
    if not undo and standing is not None:
        raise ContentError(f"{key} is already forgotten ({standing.why}); --undo withdraws it")
    who = resolve_author(author, root)[0]
    declare(root, "forget", key, why, who, undo=undo)
    if not undo and key.startswith("sha256:") and key.removeprefix("sha256:") not in load_ledger(root):
        note("warning: no document with that hash is in the copy ledger, so nothing offers it today")
    click.echo(f"{key} is remembered again" if undo else f"{key} forgotten: {why}")


def _forget_key(root: Path, target: str, bib: dict[str, Any]) -> str:
    """The key a tombstone is filed under: a citekey as given, or a full hash found from any prefix of one."""
    from loom.refs.scan import load_ledger

    if target in bib:
        return target
    want = target.removeprefix("sha256:").lower()
    if re.fullmatch(r"[0-9a-f]{6,64}", want):
        hits = [sha for sha in load_ledger(root) if sha.startswith(want)]
        if len(hits) > 1:
            raise ContentError(f"{target} names {len(hits)} documents in the copy ledger; give more of the hash")
        if hits:
            return f"sha256:{hits[0]}"
        if len(want) == 64:
            return f"sha256:{want}"
    raise ContentError(f"{target} is neither a citekey in the bibliography nor a hash in the copy ledger")
