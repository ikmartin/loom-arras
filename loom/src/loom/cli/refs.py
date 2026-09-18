"""`loom refs path | add | resolve` (book 8.9, 8.9.1): where a cited work's fetched artifacts are, how to put one there by hand, and which identifier an entry that states none most likely has."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, ContentError, EnvError, note
from loom.cli._quilt import open_scan, quilt_option
from loom.refs.identity import declared, primary
from loom.refs.resolve import Resolver, ResolveRefused, query_for, save
from loom.scan.scan import ScanResult


def _home(result: ScanResult, citekey: str) -> Path:
    """The work's directory under `refs/`, or a refusal naming what is missing."""
    entry = result.bib.get(citekey)
    if entry is None:
        raise EnvError(f"{citekey} is not in the bibliography, so it has no identity to file under")
    wid = primary(entry)
    assert wid is not None  # identify() always yields at least a synthetic id for a real entry
    return result.quilt.root / "refs" / wid.path


@click.group(name="refs")
def refs() -> None:
    """Fetched works: where their artifacts are, how to add one by hand, and identifiers for works that state none."""


@refs.command(name="path")
@click.argument("citekey")
@click.option("--pdf", "want", flag_value="pdf", help="The PDF rather than the directory.")
@click.option("--src", "want", flag_value="src", help="The unpacked source rather than the directory.")
@quilt_option
@click.pass_context
def path_command(ctx: click.Context, citekey: str, want: str | None, quilt_path: str | None) -> None:
    """Print where CITEKEY's fetched artifacts live. Nothing under refs/ is meant to be navigated by hand."""
    result = open_scan(quilt_path)
    home = _home(result, citekey)
    target = home if want is None else (home / "paper.pdf" if want == "pdf" else home / "src")
    click.echo(target)
    if not target.exists():
        # printed anyway: the path is where it *would* go, which is what `refs add` and `digest fetch` need
        note(f"nothing there yet; loom digest fetch {citekey}" + (" --pdf" if want == "pdf" else ""))
        ctx.exit(EXIT_CONTENT)


@refs.command(name="add")
@click.argument("citekey")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--force", is_flag=True, help="Replace an artifact that is already there.")
@quilt_option
@click.pass_context
def add_command(ctx: click.Context, citekey: str, file: Path, force: bool, quilt_path: str | None) -> None:
    """File FILE as CITEKEY's PDF under refs/.

    A published PDF usually sits behind a subscription that loom cannot and should not automate past, so the author supplies the bytes and names the citekey they know; loom resolves the identifier and does the filing.
    """
    result = open_scan(quilt_path)
    if file.suffix.lower() != ".pdf":
        raise EnvError(f"{file.name} is not a PDF; only a work's PDF can be added by hand (its source is fetched)")
    home = _home(result, citekey)
    dest = home / "paper.pdf"
    if dest.exists() and not force:
        raise EnvError(f"{dest.relative_to(result.quilt.root)} exists; pass --force to replace it")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(file, dest)
    click.echo(f"Wrote {dest.relative_to(result.quilt.root)}")
    note("refs/ is not in version control: a collaborator cloning the quilt fetches or adds their own copy")


@refs.command(name="resolve")
@click.argument("citekeys", nargs=-1)
@click.option("--refresh", is_flag=True, help="Ask again even where an answer is recorded.")
@click.option("--json", "as_json", is_flag=True, help="Print the candidates as JSON.")
@quilt_option
@click.pass_context
def resolve_command(
    ctx: click.Context, citekeys: tuple[str, ...], refresh: bool, as_json: bool, quilt_path: str | None
) -> None:
    """Look up identifiers for cited works whose bibliography entry states none. Requires [refs] resolve = true.

    Asks zbMATH Open, then Crossref, and prints candidates with how well each matched. Nothing is changed: a candidate becomes the work's identity when you add the field to your own bibliography entry. Answers are kept under refs/, so `loom lint` can name them and a second run asks nothing. With no CITEKEYS, every cited entry that states no identifier.
    """
    result = open_scan(quilt_path)
    cfg = result.quilt.config
    if not cfg.resolve:
        raise EnvError(
            "looking up is off: set resolve = true under [refs] in config.toml to allow it (it sends bibliography titles and authors to zbMATH Open and Crossref)"
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
    resolver = Resolver(cache=root / "refs" / "cache" / "resolve", contact=cfg.contact, refresh=refresh)
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
@click.option("--from", "run_dir", default=None, metavar="RUN", help="The run whose suggestion this is.")
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
