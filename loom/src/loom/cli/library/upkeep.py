"""`loom library review | check | import | drop` (book 8; plan 0.18.5): what waits for the person, what has gone wrong, and the library's upkeep.

`review` and `check` read and are an agent's as much as the author's; `import` and `drop` are the author's.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, ContentError, EnvError, NotFoundError, refuse_under_agent
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.library import _works
from loom.cli.library.decide import _short
from loom.cli.report import Group, Item, Report, counted

_JSON = "Print the report as one JSON object (book 12.9)."
_DRY = "Say what would be written; write nothing."


@click.command(name="review")
@click.argument("work", required=False, metavar="[WORK]")
@click.option("--json", "as_json", is_flag=True, help=_JSON)
@quilt_option
@_works.logged("review")
def review(work: str | None, as_json: bool, quilt_path: str | None) -> None:
    """List what waits for you to review: proposed results and open citation suggestions, one line each with its id.

    With WORK, only that work's proposals. Each line ends with the id that `loom library verify` and `loom library discard` take.
    """
    from loom.records.store import Records
    from loom.refs.check import recorded_works
    from loom.refs.proposals import PROPOSED, load_results, state_of

    result = open_scan(quilt_path)
    root = result.quilt.root
    scope = [_works.one_work(result, work)] if work else recorded_works(root)
    proposals: list[Item] = []
    for ck in scope:
        for rid, r in sorted(load_results(root, ck).items()):
            if state_of(r) != PROPOSED:
                continue
            where = f"p.{r.anchor.page}" if r.anchor.kind == "pdf" and r.anchor.page else "its source"
            proposals.append(
                Item(
                    f"{ck}  {r.taxon} {r.number or r.local}  {where}",
                    key=rid,
                    data={"work": ck, "taxon": r.taxon, "number": r.number, "page": r.anchor.page or None},
                )
            )
    citations: list[Item] = []
    if not work:
        for rec in Records(root).records:
            if rec.discarded:
                continue
            for a in rec.annotations:
                if a.kind != "citation" or a.status != "open" or a.in_reply_to is not None:
                    continue
                page = a.anchor.page if a.anchor is not None and a.anchor.page else None
                said = _short(a.payload) if a.payload else "names no work, so it can only be discarded"
                citations.append(
                    Item(
                        f"on {a.target_key}: {said}" + (f"  p.{page}" if page else ""),
                        key=a.id,
                        data={"on": a.target_key, "work": a.payload, "page": page, "session": rec.rel},
                    )
                )
        citations.sort(key=lambda i: i.key or "")
    total = len(proposals) + len(citations)
    parts = [counted(len(proposals), "proposed result")] if proposals else []
    parts += [counted(len(citations), "citation suggestion")] if citations else []
    nxt = "loom library verify ID, or loom library discard ID --why '…'"
    Report(
        f"waiting for review: {' and '.join(parts)}"
        if total
        else f"nothing waits for review{f' in {scope[0]}' if work else ''}",
        groups=_works.present(
            Group("proposed results", proposals, next=nxt),
            Group("citation suggestions", citations, next=nxt),
        ),
        data={
            "proposed": [{"id": i.key, **i.data} for i in proposals],
            "citations": [{"id": i.key, **i.data} for i in citations],
        },
    ).emit(as_json)


#: `check`'s headings and fixes, by problem, in the order they print.
PROBLEMS: dict[str, tuple[str, str]] = {
    "transcription-changed": (
        "verified results whose page no longer reads that way",
        "read the page again, then loom library verify ID for what still holds",
    ),
    "page-gone": ("verified results whose page is gone", "loom library update WORK --only map --redo"),
    "version_mismatch": (
        "verified results read from a different document",
        "read the page again, then loom library verify ID for what still holds",
    ),
    "file-gone": ("verified results whose source file is gone", "loom library update WORK --only fetch --online"),
    "no-page-text": ("verified results with no page text to re-read", "loom library update WORK --only map"),
    "wrong-document": (
        "documents that are another work's",
        "loom library add FILE --for WORK, with the right document",
    ),
    "unconfirmed-document": (
        "documents that may not be their work",
        "loom library read WORK 1 shows the page; if it is not the work, loom library add FILE --for WORK",
    ),
    "empty-digest": ("digests with no results recorded", "loom library update WORK records them"),
    "guessed-map": (
        "section maps that are a guess",
        "read it by page, loom library read WORK PAGES; the map is not its structure",
    ),
    "duplicate-document": (
        "entries that name one document",
        "keep one of them in your bibliography; loom never edits it",
    ),
    "uncited-lint": (
        "works nothing cites that lint finds wrong",
        "nothing, or loom library ignore WORK --why WHY if you will not cite it; no exit code counts them",
    ),
}
#: Problems listed for the record that leave `check` ok: a work nothing cites is the author's to keep or drop.
NOT_FAULTS = {"uncited-lint"}


@click.command(name="check")
@click.argument("works", nargs=-1, metavar="[WORK...]")
@click.option("--json", "as_json", is_flag=True, help=_JSON)
@quilt_option
@_works.logged("check")
def check(works: tuple[str, ...], as_json: bool, quilt_path: str | None) -> None:
    """Check the library for what has gone wrong, each problem with its fix.

    Re-reads every verified result's anchor against the page or source it names; never re-judges a verified rendering, which a person judged once, and never re-checks extraction. Then: a stored PDF whose first page carries another work's title, a digest with no results, a section map with far too few sections for its length, and entries or versions holding one document, once per work. Exit 1 when anything is wrong. Works nothing cites whose digests lint finds wrong are listed too, and do not fail it.
    """
    from loom.cli.lint_cmd import all_diagnostics
    from loom.refs.check import (
        duplicate_documents,
        empty_digests,
        guessed_maps,
        moved_anchors,
        recorded_works,
        uncited_lint,
        wrong_documents,
    )

    result = open_scan(quilt_path)
    root = result.quilt.root
    scope = sorted(_works.works(result, works)) if works else sorted(set(result.bib) | set(recorded_works(root)))
    checked, problems = moved_anchors(root, result.bib, scope)
    problems += wrong_documents(root, result.bib, scope)
    problems += empty_digests(root, scope)
    problems += guessed_maps(root, result.bib, scope)
    problems += duplicate_documents(root, result.bib, scope if works else None)
    problems += uncited_lint(result, all_diagnostics(result), scope)
    by_kind: dict[str, list[Item]] = {}
    for p in problems:
        by_kind.setdefault(p.kind, []).append(Item(p.why, key=p.key, data={"work": p.work, "problem": p.kind}))
    faults = [p for p in problems if p.kind not in NOT_FAULTS]
    uncited = len(problems) - len(faults)
    affected = len({p.work for p in faults})
    reread = counted(checked, "verified anchor")
    Report(
        (
            f"{counted(len(faults), 'problem')} in {counted(affected, 'work')}; {reread} re-read"
            if faults
            else f"nothing wrong in {counted(len(scope), 'work')}; {reread} re-read"
        )
        + (f"; {counted(uncited, 'work')} nothing cites with lint diagnostics" if uncited else ""),
        ok=not faults,
        exit=EXIT_CONTENT if faults else 0,
        groups=[
            Group(
                heading,
                sorted(by_kind[kind], key=lambda i: i.key or ""),
                problem=kind not in NOT_FAULTS,
                limit=None,
                next=fix,
            )
            for kind, (heading, fix) in PROBLEMS.items()
            if kind in by_kind
        ],
        data={
            "checked": checked,
            "works": len(scope),
            "problems": [{"problem": p.kind, "key": p.key, "work": p.work, "why": p.why} for p in problems],
        },
    ).emit(as_json)


@click.command(name="import")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--name", "citekey", default=None, metavar="CITEKEY", help="File it under this citekey, rewriting its ids."
)
@click.option("--dry-run", is_flag=True, help=_DRY)
@click.option("--json", "as_json", is_flag=True, help=_JSON)
@quilt_option
def import_digest(path: Path, citekey: str | None, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Copy a digest from another quilt into digests/, rewriting its citekey and id prefix when --name renames it.

    It never overwrites a digest already there.
    """
    from loom.digest.importer import plan_digest_import, write_digest_import

    refuse_under_agent(
        "loom library import", "A digest is the author's file once it is in digests/; say which one to bring in."
    )
    result = open_scan(quilt_path)
    root = result.quilt.root
    try:
        plan = plan_digest_import(result, path, citekey)
    except ValueError as exc:
        raise ContentError(str(exc)) from exc
    dest = root / plan.target
    if dest.exists():
        raise EnvError(f"{dest.relative_to(root).as_posix()} exists; loom library import never overwrites")
    if not dry_run:
        write_digest_import(root, plan)
    rel = dest.relative_to(root).as_posix()
    warnings = []
    if plan.missing_packages:
        warnings.append(
            Item(f"requires {', '.join(plan.missing_packages)}, not loaded by the preamble", key="loom:missing-package")
        )
    if plan.undeclared_envs:
        warnings.append(
            Item(
                f"environments not declared in this quilt: {', '.join(plan.undeclared_envs)}",
                key="loom:unknown-environment",
            )
        )
    if plan.citekey not in result.bib:
        warnings.append(Item(f"{plan.citekey} is not in the bibliography", key="loom:digest-without-bib"))
    renamed = plan.citekey != plan.old_citekey
    Report(
        f"{'would write' if dry_run else 'wrote'} {rel}"
        + (f", renamed {plan.old_citekey} to {plan.citekey} in {counted(plan.renamed, 'place')}" if renamed else "")
        + (f"; {counted(len(warnings), 'warning')}" if warnings else ""),
        ok=not warnings,
        dry_run=dry_run,
        groups=[Group("warnings", warnings, limit=None, next="loom lint")] if warnings else [],
        data={
            "digest": rel,
            "citekey": plan.citekey,
            "renamed_from": plan.old_citekey if renamed else None,
            "rewrites": plan.renamed,
            "missing_packages": list(plan.missing_packages),
            "undeclared_envs": list(plan.undeclared_envs),
            "in_bibliography": plan.citekey in result.bib,
        },
    ).emit(as_json)


@click.command(name="drop")
@click.option("--work", "work", default=None, metavar="WORK", help="Everything recorded for this work.")
@click.option("--session", "session", default=None, metavar="SESSION", help="Everything proposed in this session.")
@click.option("--proposed", is_flag=True, help="Every result still proposed, in every work.")
@click.option("--yes", is_flag=True, help="Do not ask.")
@click.option("--dry-run", is_flag=True, help="Say what would be dropped; drop nothing.")
@click.option("--json", "as_json", is_flag=True, help=_JSON)
@quilt_option
def drop(
    work: str | None,
    session: str | None,
    proposed: bool,
    yes: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Remove recorded results: one work's, one session's proposals, or every one still proposed.

    Dropping costs re-reading, never correctness. A verified node already written into digests/<citekey>.tex is the author's file and is never touched; only the records and the proposals go.
    """
    from loom.refs.check import recorded_works
    from loom.refs.proposals import (
        PROPOSED,
        append_event,
        load_results,
        results_path,
        save_results,
        state_of,
        write_proposed_tex,
    )

    refuse_under_agent(
        "loom library drop",
        "Removing recorded results is the author's; an agent corrects its own proposal with "
        "loom library propose --supersedes.",
    )
    if sum(map(bool, [work, session, proposed])) != 1:
        raise EnvError("give exactly one of --work, --session or --proposed")
    result = open_scan(quilt_path)
    root = result.quilt.root
    # a work no longer in the bibliography is still named by the results recorded for it
    ck = (work if results_path(root, work).is_file() else _works.one_work(result, work)) if work else None
    by, known = _session_names(root, session) if session else (set(), False)
    doomed: list[tuple[str, str]] = []
    for w in [ck] if ck else recorded_works(root):
        for rid, r in load_results(root, w).items():
            if ck or (proposed and state_of(r) == PROPOSED) or (by and any(o.get("by") in by for o in r.origin)):
                doomed.append((w, rid))
    if session and not doomed and not known:
        raise NotFoundError("session", f"{session} names no session and nothing was proposed under it")
    if not doomed:
        Report("nothing to drop", dry_run=dry_run, data={"dropped": []}).emit(as_json)
        return
    if not yes and not dry_run:
        if not sys.stdin.isatty():
            raise EnvError("dropping needs confirmation; pass --yes")
        for w, rid in doomed[:10]:
            click.echo(f"  {w}  {rid}", err=True)
        if len(doomed) > 10:
            click.echo(f"  … and {len(doomed) - 10} more", err=True)
        click.confirm(f"drop {len(doomed)} record(s)?", abort=True, err=True)
    if not dry_run:
        for w in dict.fromkeys(c for c, _ in doomed):
            results = load_results(root, w)
            for _, rid in [d for d in doomed if d[0] == w]:
                results.pop(rid, None)
                append_event(root, w, {"event": "dropped", "id": rid})
            if results:
                save_results(root, w, results)
            else:
                results_path(root, w).unlink(missing_ok=True)
            write_proposed_tex(root, w, result.assembly.prefix_of(w), results)
    per: dict[str, list[str]] = {}
    for w, rid in doomed:
        per.setdefault(w, []).append(rid)
    Report(
        f"{'would drop' if dry_run else 'dropped'} {counted(len(doomed), 'record')}; "
        "verified nodes already in digests/ are not touched",
        dry_run=dry_run,
        groups=[Group(w, [Item("", key=rid) for rid in sorted(rids)]) for w, rids in sorted(per.items())],
        data={"dropped": [{"work": w, "id": rid} for w, rid in doomed]},
    ).emit(as_json)


def _session_names(root: Path, given: str) -> tuple[set[str], bool]:
    """What a proposal's origin may call the session `given` names (as typed, and its id), and whether any session answers to it, deleted ones included."""
    from loom.sessions import SessionNotFound, resolve

    for deleted in (False, True):
        try:
            return {given, resolve(root, given, deleted=deleted).id}, True
        except SessionNotFound:
            continue
    return {given}, False


#: The commands this module adds to `loom library`.
COMMANDS: list[click.Command] = [review, check, import_digest, drop]
