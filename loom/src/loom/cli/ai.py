"""`loom ai ...`: the agent layer, its orientation, its documents, and an agent's annotations."""

from __future__ import annotations

import shlex
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from loom.ai.clients import BY_KEY, CLIENTS
from loom.cli._common import EXIT_CONTENT, EnvError, NotFoundError, find_session
from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.help import CommandGroup
from loom.cli.report import Group, Item, Report, counted, table
from loom.cli.review import STATUSES
from loom.paths import AI, COPIES, DIGESTS

if TYPE_CHECKING:
    from loom.ai.clients import Client, ClientReport
    from loom.ai.layout import LayerReport

#: What a verdict adds when the client files start a server this loom cannot run yet (`sdk_groups`).
NO_SERVER = "the loom server cannot start until loom is reinstalled"


@click.group(cls=CommandGroup)
def ai() -> None:
    """Set up the agent layer and read what an agent works from: its orientation, its documents and its annotations."""


@ai.command(name="delete")
@click.option("--by", "by", default=None, metavar="NAME", help="Annotations NAME wrote.")
@click.option("--target", default=None, metavar="KEY", help="Annotations on KEY.")
@click.option(
    "--before",
    default=None,
    metavar="DATE",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Annotations written before this date (YYYY-MM-DD).",
)
@click.option(
    "--version",
    "version",
    default=None,
    metavar="HASH",
    help="Annotations written on this version of their text: the hash `loom ai annotations --json` gives as `against`.",
)
@click.option("--yes", is_flag=True, help="Delete without asking, where nobody is at a terminal to answer.")
@click.option(
    "--as", "as_name", default=None, metavar="NAME", help="Who is deleting them; default your configured name."
)
@click.option("--dry-run", is_flag=True, help="Say what would be deleted and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def delete_command(
    by: str | None,
    target: str | None,
    before: datetime | None,
    version: str | None,
    yes: bool,
    as_name: str | None,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Delete the annotations matching every one of --by, --target, --before and --version, with their replies; this cannot be undone.

    Deleting removes them from the log rather than marking them, so nothing of them stays to be read; an agent whose annotation is deleted hears so once, from `loom since`. One annotation is deleted with `loom annotate --delete ID`.
    """
    from loom.cli._common import refuse_under_agent, whoever
    from loom.records.log import delete
    from loom.records.store import Records
    from loom.since import note_deletion

    refuse_under_agent(
        "loom ai delete",
        "Deleting annotations in bulk is the author's; delete one of your own with loom annotate --delete ID.",
        as_name,
    )
    if not (by or target or before or version):
        raise EnvError("give --by, --target, --before or --version: which annotations to delete")
    quilt = open_quilt(quilt_path)
    root = quilt.root
    records = Records(root, quilt.history_dir).records
    if target and not any(a.target_key == target for rec in records for a in rec.annotations):
        from loom.scan.scan import scan

        if target not in scan(quilt).nodes:
            raise NotFoundError("key", f"{target} is no key of this quilt and no annotation's target")
    hits = [
        a
        for rec in records
        for a in rec.annotations
        if a.in_reply_to is None
        and (not by or a.author_id == by)
        and (not target or a.target_key == target)
        # compared as ISO dates, which order as their strings do once both are YYYY-MM-DD
        and (not before or (a.created and a.created[:10] < before.date().isoformat()))
        and (not version or a.target_hash == version)
    ]
    data = {"deleted": [a.id for a in hits]}
    if not hits:
        Report("no annotation matches; nothing deleted", data=data).emit(as_json)
        return
    listed = [
        Group(
            "would be deleted" if dry_run else "deleted",
            [Item(f"{a.type or 'untyped'} on {a.target_key} by {a.author_id}", key=a.id) for a in hits],
        )
    ]
    if dry_run:
        Report(
            f"would delete {counted(len(hits), 'annotation')}, with their replies",
            dry_run=True,
            groups=listed,
            data=data,
        ).emit(as_json)
        return
    if not yes:
        if not sys.stdin.isatty():
            raise EnvError(
                f"this deletes {counted(len(hits), 'annotation')} for good; --dry-run lists them, and --yes deletes them"
            )
        if not click.confirm(f"delete {counted(len(hits), 'annotation')}, with their replies, for good?", err=True):
            Report("nothing deleted", data={**data, "deleted": []}).emit(as_json)
            return
    who = whoever(root, as_name)
    removed = delete(root, [a.id for a in hits])
    note_deletion(root, removed, who)
    Report(f"deleted {counted(len(hits), 'annotation')}, with their replies", groups=listed, data=data).emit(as_json)


def install_layer(root: Path, *, write: bool = True, shell: bool | None = None) -> tuple[LayerReport, ClientReport]:
    """Write the agent layer into a quilt, or refresh it where `.loom/ai/` exists, with the MCP client files of its variant.

    Parameters
    ----------
    root : Path
        The quilt root.
    write : bool, default True
        False writes nothing and reports what would be written.
    shell : bool, optional
        True for an agent with no MCP, which runs `loom` in a shell; False for one that attaches over MCP, with the shell beside the tools; default the way the quilt already uses, else MCP.

    Returns
    -------
    LayerReport
        `written` (quilt-relative paths), and where `.loom/ai/` existed, `kept` and `new_beside` for edited mode files, as `loom upgrade` reports them.
    ClientReport
        The client files written, current, left alone or, in the shell variant, removed.

    See Also
    --------
    loom.ai.layout.upgrade_layer : the refresh alone, which `loom upgrade` runs.
    """
    from loom.ai.clients import write_clients
    from loom.ai.layout import (
        SHELL,
        VERSION_FILE,
        LayerReport,
        ensure_root_line,
        init_layer,
        quilt_config,
        tracked_docs,
        upgrade_layer,
        variant,
        vendor_files,
    )

    if shell is None:
        shell = variant(root) == SHELL
    if not (root / AI).exists():
        if write:
            rep = init_layer(root, shell=shell)
        else:
            rep = LayerReport(written=[*tracked_docs(), f"{AI}/README.md", f"{AI}/{VERSION_FILE}"])
            rep.written += [*vendor_files(quilt_config(root), shell=shell), *ensure_root_line(root, False, shell=shell)]
    else:
        rep = upgrade_layer(root, write=write, shell=shell)
    clients = write_clients(root, write, shell=shell)
    if write:
        # the client files name this machine's paths, so the root .gitignore keeps them out of the repository
        from loom.gitignore import ensure

        ensure(root)
    return rep, clients


def sdk_groups(shell: bool) -> list[Group]:
    """The warning for client files that start a server this loom cannot run yet.

    Parameters
    ----------
    shell : bool
        True for the shell variant, whose agents need no server.

    Returns
    -------
    list of Group
        One group of problems carrying the reinstall command; empty in the shell variant or with the SDK present.
    """
    from loom.mcp.sdk import has_sdk, reinstall_hint

    if shell or has_sdk():
        return []
    return [
        Group(
            "this loom has no MCP SDK",
            [Item("agents here get no loom tools without it", fixes=[reinstall_hint()])],
            limit=None,
            problem=True,
            counted=False,
        )
    ]


@ai.command(name="init")
@click.option(
    "--mcp/--shell",
    "mcp",
    default=None,
    help="How agents here reach loom: the loom MCP server's tools with loom in a shell beside them, or loom in a shell alone, for an agent with no MCP. Default the way the quilt already uses, else MCP.",
)
@click.option(
    "--client",
    type=click.Choice([c.key for c in CLIENTS]),
    default=None,
    help="Print the loom server's entry for this agent app, to add to its settings by hand, and write nothing.",
)
@click.option("--dry-run", is_flag=True, help="Say what would be written and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def ai_init(mcp: bool | None, client: str | None, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Write the agent layer: .loom/ai/ (orientation, rules, modes), CLAUDE.md, AGENTS.md and GEMINI.md, the permission files, and what starts the loom MCP server for each agent's app.

    The permission files say what agents may run, for Claude Code (.claude/settings.json) and Codex (.codex/rules/loom.rules). Over MCP, the default, the server's files are .mcp.json (Claude Code, VS Code), .codex/config.toml, .gemini/settings.json and .cursor/mcp.json, gitignored because they name this machine's paths; one that holds settings of your own is left alone, and --client prints the entry to add to it, or to an app configured outside the quilt. Where .loom/ai/ exists this refreshes what `loom upgrade` would, keeping an edited mode file and writing the new version beside it.
    """
    quilt = open_quilt(quilt_path)
    if client is not None:
        _print_entry(BY_KEY[client], quilt.root, as_json)
        return
    from loom.ai.layout import SHELL, variant

    existed = (quilt.root / AI).is_dir()
    shell = variant(quilt.root) == SHELL if mcp is None else not mcp
    rep, clients = install_layer(quilt.root, write=not dry_run, shell=shell)
    written = sorted(dict.fromkeys(str(rel) for rel in rep.written))
    by_dir: dict[str, list[str]] = {}
    for rel in written:
        parts = rel.split("/")
        by_dir.setdefault("/".join(parts[: min(2, len(parts) - 1)]) + "/" if len(parts) > 1 else "./", []).append(rel)
    groups = []
    if written:
        groups.append(
            Group(
                "would write, by directory" if dry_run else "written, by directory",
                [
                    Item(counted(len(names), "file"), key=d, data={"files": names})
                    for d, names in sorted(by_dir.items())
                ],
                limit=None,
                next=None if dry_run else 'loom session new --name "a name"',
            )
        )
    if rep.kept:
        groups.append(
            Group(
                "edited, so kept, with the new version beside",
                [Item("", key=rel) for rel in sorted(rep.new_beside)],
                limit=None,
            )
        )
    sdk = sdk_groups(shell)
    groups += _client_groups(clients, dry_run) + sdk
    data = {
        "written": written,
        "kept": sorted(rep.kept),
        "new_beside": sorted(rep.new_beside),
        "refreshed": existed,
        "variant": SHELL if shell else "mcp",
        "clients": clients.to_json(),
    }
    n = len(written) + len(clients.written)
    if dry_run:
        verdict = f"would write {counted(n, 'file')} of the agent layer" if n or clients.removed else "nothing to write"
    elif not existed:
        start = (
            "it reads CLAUDE.md and runs loom ai orient"
            if shell
            else "approve the loom server it asks to start, and it calls loom_ai_orient"
        )
        first = "reinstall loom as below, then " if sdk else ""
        verdict = f"wrote the agent layer, {counted(n, 'file')}; {first}start your agent here: {start}"
    elif n or rep.kept or clients.removed:
        verdict = f"refreshed the agent layer: {counted(n, 'file')} written" + (
            f", {counted(len(rep.kept), 'edited file')} kept" if rep.kept else ""
        )
    else:
        verdict = "the agent layer is current; nothing written"
    if sdk and (existed or dry_run):
        verdict += f"; {NO_SERVER}"
    Report(verdict, ok=not clients.tracked and not sdk, dry_run=dry_run, groups=groups, data=data).emit(as_json)


def _client_groups(clients: ClientReport, dry_run: bool) -> list[Group]:
    """`ai init`'s groups for the MCP client files: written, removed, and the two kinds left alone, each with what to do."""
    from loom.ai.clients import PROJECT

    app = {c.file: c for c in PROJECT}
    groups = []
    if clients.written:
        groups.append(
            Group(
                f"{'would start' if dry_run else 'starts'} the loom MCP server, gitignored",
                [Item(app[rel].label, key=rel) for rel in clients.written],
                limit=None,
            )
        )
    if clients.removed:
        groups.append(
            Group(
                f"{'would remove' if dry_run else 'removed'}: agents here run loom in a shell",
                [Item(app[rel].label, key=rel) for rel in clients.removed],
                limit=None,
            )
        )
    if clients.foreign:
        groups.append(
            Group(
                "holds settings of yours, so left alone: add the loom server by hand",
                [
                    Item(app[rel].label, key=rel, fixes=[f"loom ai init --client {app[rel].key} prints the entry"])
                    for rel in clients.foreign
                ],
                limit=None,
                problem=True,
            )
        )
    if clients.tracked:
        groups.append(
            Group(
                "tracked by git, so not written: it names this machine's paths",
                [Item(app[rel].label, key=rel, fixes=[f"git rm --cached {rel}"]) for rel in clients.tracked],
                limit=None,
                problem=True,
            )
        )
    return groups


def _print_entry(client: Client, root: Path, as_json: bool) -> None:
    """`ai init --client`: the entry that starts loom's server for `client`, printed as it is pasted, never wrapped."""
    from loom.ai.clients import render

    entry = render(client, root)
    where = client.file or client.where
    said = f"the loom server for {client.label}, serving {client.agent}: add it to {where}"
    if client.file is None:
        said += "; loom writes nothing outside the quilt"
    sdk = sdk_groups(False)
    if as_json:
        Report(said, ok=not sdk, groups=sdk, data={"client": client.key, "file": where, "entry": entry}).emit(True)
        return
    Report(said, ok=not sdk, groups=sdk).emit(False)
    click.echo("")
    click.echo(entry, nl=False)


@ai.command(name="orient")
@click.option(
    "--session",
    "session",
    default=None,
    envvar="LOOM_SESSION",
    metavar="SESSION",
    help="Attach to this session: also print the end of its chat and its command log. An id, a title, or a unique id suffix.",
)
@quilt_option
def ai_orient(session: str | None, quilt_path: str | None) -> None:
    """Print the orientation documents followed by the quilt's live state, and with --session the end of that session's chat.

    This is also how an agent joins a session it did not open: `loom ai orient --session <id>` prints the orientation, the quilt's live state, and the last messages of that session's chat with its command log, which is what a later sitting resumes from.
    """
    from loom.ai.orient import live_text, mode_index, static_text
    from loom.cli._quilt import open_scan
    from loom.cli.build_cmds import log_run
    from loom.records.store import Records

    result = open_scan(quilt_path)
    root = result.quilt.root
    from loom.sessions import files_dir

    found = find_session(root, session) if session else None
    where = files_dir(root, found) if found else None
    click.echo(static_text(root), nl=False)
    click.echo(mode_index(root), nl=False)
    click.echo(live_text(result, Records(root, result.quilt.history_dir), where, found.id if found else None), nl=False)
    log_run(found.id if found else None, "loom ai orient", root)


@ai.command(name="mode")
@click.argument("name")
@click.option(
    "--session", "session", default=None, envvar="LOOM_SESSION", metavar="SESSION", help="Log this call to the session."
)
@quilt_option
def ai_mode(name: str, session: str | None, quilt_path: str | None) -> None:
    """Print mode NAME in full: when it fits, what it is for, and what its report shows.

    The quilt's own copy in .loom/ai/modes/ is printed, so an edit the author made there holds; with no .loom/ai/, the shipped one. `loom ai orient` lists every mode with its one line.
    """
    from loom.ai.layout import MODES
    from loom.ai.orient import mode_text
    from loom.cli.build_cmds import log_run

    quilt = open_quilt(quilt_path)
    if name not in MODES:
        raise NotFoundError("mode", f"no mode {name!r}; the modes are {', '.join(MODES)}")
    found = find_session(quilt.root, session) if session else None
    click.echo(mode_text(quilt.root, name), nl=False)
    log_run(found.id if found else None, f"loom ai mode {name}", quilt.root)


@ai.command(name="drafts")
@click.option("--closed", is_flag=True, help="List retained closed agent documents instead of active ones.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def ai_drafts(as_json: bool, closed: bool, quilt_path: str | None) -> None:
    """List each agent document: the working document it was drafted from and what has moved there since.

    Before a large instruction, an agent checks its document here: a stale one is refreshed first, or the agent says what it is working against.
    """
    from loom.cli._quilt import open_scan
    from loom.draft_lifecycle import closed_drafts
    from loom.drafts import copy_states
    from loom.history.ledger import load_history
    from loom.section_drafts import context_changed, metadata

    result = open_scan(quilt_path)
    if closed:
        rows = [
            {"copy": copy, "closed": True, "when": row["when"], "snapshot": row["snapshot"]}
            for copy, row in sorted(closed_drafts(load_history(result.quilt.history_dir)).items())
        ]
        Report(
            counted(len(rows), "closed agent document"),
            groups=[
                Group(
                    "closed agent documents",
                    [
                        Item(f"{row['copy']}  closed {row['when']}", fixes=[f"loom ai reopen {row['copy']}"])
                        for row in rows
                    ],
                    limit=None,
                )
            ]
            if rows
            else [],
            data={"copies": rows},
        ).emit(as_json)
        return
    history = load_history(result.quilt.history_dir)
    states = sorted(copy_states(result, history), key=lambda st: st.copy)
    data = {
        "copies": [
            {
                **st.to_dict(),
                **metadata(result, st.copy),
                "context_changed": context_changed(result, metadata(result, st.copy).get("context") or {}),
            }
            for st in states
        ]
    }
    if not states:
        Report(f"no agent documents: loom draft DOC --ai NAME copies one into {COPIES}/", data=data).emit(as_json)
        return
    items: list[Item] = []
    for st in states:
        if not st.stale:
            items.append(Item(f"{st.copy}  drafted from {st.source}  fresh"))
            continue
        moved = [f"{', '.join(st.changed)} changed"] if st.changed else []
        moved += [f"{', '.join(st.gone)} gone from {st.source}"] if st.gone else []
        moved += ["the prose between nodes"] if st.prose else []
        moved += ["the preamble"] if st.preamble else []
        items.append(
            Item(
                f"{st.copy}  drafted from {st.source}  stale: {'; '.join(moved)}",
                fixes=[f"loom ai refresh {shlex.quote(st.copy)}"],
            )
        )
    stale = sum(1 for st in states if st.stale)
    Report(
        counted(len(states), "agent document")
        + (f", {stale} stale: refresh it before a large instruction" if stale else ", every one fresh"),
        ok=not stale,
        groups=[Group("agent documents", items, limit=None)],
        data=data,
    ).emit(as_json)


def proposals_by(root: Path, name: str) -> list[dict[str, Any]]:
    """Every digest proposal `name` made, with the author's decision on it: state, the edit as diff lines, and the reason for a discard."""
    from loom.refs.proposals import DISCARDED, VERIFIED, edit_diff, load_results, read_events, state_of

    out: list[dict[str, Any]] = []
    for path in sorted((root / DIGESTS).glob("*.results.json")):
        ck = path.name[: -len(".results.json")]
        reasons = {e.get("id"): e.get("reason", "") for e in read_events(root, ck) if e.get("event") == "discarded"}
        for rid, r in sorted(load_results(root, ck).items()):
            if not any(o.get("act") == "proposed" and o.get("by") == name for o in r.origin):
                continue
            out.append(
                {
                    "id": rid,
                    "work": ck,
                    "state": "transcription verified" if state_of(r) == VERIFIED else state_of(r),
                    "edited": any(o.get("act") == "edited" for o in r.origin),
                    "edit": edit_diff(r),
                    "renamed_from": next((str(o.get("was")) for o in r.origin if o.get("act") == "renamed"), ""),
                    "reason": reasons.get(rid, "") if state_of(r) == DISCARDED else "",
                }
            )
    return out


@ai.command(name="annotations")
@click.option(
    "--by", "f_by", default=None, metavar="NAME", help="Only annotations NAME wrote; with it, NAME's proposals too."
)
@click.option("--target", "f_target", default=None, metavar="KEY", help="Only annotations on KEY.")
@click.option("--type", "f_type", default=None, metavar="TYPE", help="Only annotations of this type, by id or name.")
@click.option("--status", "f_status", type=click.Choice(STATUSES), default=None, help="Only annotations in this state.")
@click.option("--json", "as_json", is_flag=True, help="Print the annotations as JSON.")
@quilt_option
def ai_annotations(
    f_by: str | None,
    f_target: str | None,
    f_type: str | None,
    f_status: str | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """List annotations: id, target, type, status, author and the quoted text, every one unless --by, --target, --type or --status narrows it; `--json` carries each one whole.

    An agent re-reading its own annotations is the common case — a re-check resolves what is met and edits what still stands, and needs the ids to do it — so `--by` its own name lists them, with what the author decided on each result it proposed. The JSON form carries `message` too, so a re-check can tell what it already said without reading the log itself; `loom changes --by` lists the edits it suggested.
    """
    from loom.cli._quilt import open_scan
    from loom.mailbox import on_page, page_lines
    from loom.records.store import Records

    result = open_scan(quilt_path)
    root = result.quilt.root
    type_id = None
    if f_type is not None:
        from loom.records.types import load_types, type_named

        try:
            named = type_named(load_types(root), f_type)
        except ValueError as exc:
            raise EnvError(f"--type {f_type}: {exc}") from exc
        type_id = named.id if named else None
    resolved = Records(root, result.quilt.history_dir).resolved(result)
    if f_target is not None and f_target not in result.nodes:
        if not any(f_target in (a.annotation.target_key, a.work) for a in resolved):
            raise NotFoundError("key", f"{f_target} is no key of this quilt and no annotation's target")
    rows = [
        {
            "id": a.annotation.id,
            "target": a.annotation.target_key,
            # an annotation on a cited work: the citekey the agent knows it by, and the page (plan 0.13 item 2)
            "work": a.work or None,
            "page": a.annotation.anchor.page if a.annotation.anchor else None,
            "type": a.annotation.type,
            "status": a.annotation.status,
            "reply_to": a.annotation.in_reply_to,
            "detached": a.detached,
            "recorded": a.recorded,
            "quote": a.annotation.selector.exact if a.annotation.selector else None,
            "message": a.annotation.body,
            # who wrote it, so an agent tells the author's from its own: it answers the author's, and may edit its own
            "author": {"kind": a.annotation.author_kind, "id": a.annotation.author_id},
            # on a PDF page: where it stands now, the tool, whether a changed file moved it, its source and a crop of the page
            **(on_page(result, a) if a.annotation.page is not None or a.annotation.anchor is not None else {}),
        }
        for a in resolved
        if (f_by is None or a.annotation.author_id == f_by)
        and (f_target is None or f_target in (a.annotation.target_key, a.work))
    ]
    rows = [r for r in rows if (not type_id or r["type"] == type_id) and (not f_status or r["status"] == f_status)]
    proposals = proposals_by(root, f_by) if f_by else []
    # what the author did with an agent's proposals: a reattaching agent otherwise ran `library why` on each id it happened to know, which is how it learned the author's decisions three times over
    lines: list[str] = []
    if proposals:
        lines += ["", f"proposals ({len(proposals)})"]
        for pr in proposals:
            extra = (
                f" -- {pr['reason']}"
                if pr.get("reason")
                else (" (edited by the author first)" if pr.get("edited") else "")
            )
            if pr.get("renamed_from"):
                extra += f" (renamed by the author from {pr['renamed_from']})"
            lines.append(f"  {pr['id']}  {pr['state']}{extra}")
            # the edit itself: a reattached agent that could not see it diffed its own scratch script against the digest
            lines += [f"      {line}" for line in pr.get("edit") or []]
    cells = []
    under: list[list[str]] = []
    for r in rows:
        mark = "" if r["status"] == "open" else f" ({r['status']})"
        quote = f"\u201c{r['quote']}\u201d" if r["quote"] else ""
        where = f"{r['work'] or r['target']} p.{r['page']}" if r["page"] else r["target"]
        rest = quote
        who = r["author"]["id"] if isinstance(r["author"], dict) else ""
        cells.append((str(r["id"]), str(where), f"{r['type'] or 'untyped'}{mark}", f"by {who}", rest))
        under.append(page_lines(r, "    "))
    # aligned, so the columns read down (T2); a crop and a source line under the annotation they belong to
    items = [Item(text) for line, more in zip(table(cells), under, strict=True) for text in (line, *more)]
    narrowed = any(x is not None for x in (f_by, f_target, f_type, f_status))
    verdict = (
        counted(len(rows), "annotation") if rows else ("no annotations match" if narrowed else "no annotations yet")
    ) + (f" by {f_by}" if f_by else "")
    if proposals:
        verdict += f", {counted(len(proposals), 'proposal')}"
    Report(
        verdict,
        groups=[Group("annotations", items, count=len(rows), limit=None)] if items else [],
        lines=lines,
        data={"annotations": rows, "proposals": proposals},
    ).emit(as_json)


@ai.command(name="refresh")
@click.argument("document")
@click.option("--dry-run", is_flag=True, help="Say what would be refreshed and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def refresh_draft(document: str, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Update an agent document from the working document it was drafted from, keeping its outstanding proposals."""
    from loom.adopt import refresh
    from loom.cli._quilt import open_scan
    from loom.sync import SyncError

    try:
        answer = refresh(open_scan(quilt_path), document, write=not dry_run)
    except (SyncError, ValueError, OSError) as exc:
        raise EnvError(str(exc)) from exc
    copy, conflicts, updated, wrote = answer["copy"], answer["conflicts"], answer["updated"], answer["written"]
    name = Path(copy).name
    would = "would be " if dry_run else ""
    done = [Group(f"{would}updated", [Item("", key=k) for k in sorted(updated)])] if updated else []
    if conflicts:
        # a conflict left waiting is not success, in either form
        Report(
            f"{copy}: {counted(len(conflicts), 'conflict')} left to reconcile in your editor"
            + (
                f"; the rest {would or ''}refreshed, {counted(len(updated), 'node')} {would}updated"
                if wrote
                else f"; nothing {'would be ' if dry_run else ''}written"
            ),
            ok=False,
            exit=EXIT_CONTENT,
            dry_run=dry_run,
            groups=[
                Group(
                    "changed on both sides, in the working document and in the agent document",
                    [Item(c) for c in sorted(conflicts)],
                    problem=True,
                    limit=None,
                    next=f"loom ai refresh {shlex.quote(name)}",
                ),
                *done,
            ],
            data=answer,
        ).emit(as_json)
        return
    if not wrote:
        verdict = f"{copy} is already up to date; nothing written"
    elif dry_run:
        verdict = f"would refresh {copy}: {counted(len(updated), 'node')} updated"
    else:
        verdict = f"refreshed {copy}: {counted(len(updated), 'node')} updated"
    Report(verdict, dry_run=dry_run, groups=done, data=answer).emit(as_json)


@ai.command(name="close")
@click.argument("document")
@click.option("--yes", is_flag=True, help="Close even when unapplied changes remain; text and annotations are kept.")
@click.option("--dry-run", is_flag=True, help="Say what would change and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def close_draft(document: str, yes: bool, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Close an agent document, retaining its text and annotations and releasing its scope."""
    from loom.cli._common import agent_marker, whoever
    from loom.cli._quilt import open_scan
    from loom.draft_lifecycle import close_draft as close
    from loom.sync import SyncError

    if agent_marker():
        raise EnvError("Closing drafts is an author action")
    result = open_scan(quilt_path)
    try:
        answer = close(result, document, whoever(result.quilt.root), confirmed=yes or dry_run, write=not dry_run)
        if answer.get("confirmation_required") and not as_json and not dry_run:
            if click.confirm(answer["message"]):
                answer = close(open_scan(quilt_path), document, whoever(result.quilt.root), confirmed=True)
        Report(answer["message"], ok=not answer.get("confirmation_required", False), dry_run=dry_run, data=answer).emit(
            as_json
        )
    except (SyncError, ValueError, OSError) as exc:
        raise EnvError(str(exc)) from exc


@ai.command(name="reopen")
@click.argument("document")
@click.option("--dry-run", is_flag=True, help="Say what would change and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def reopen_draft(document: str, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Reopen a retained agent document when its scope and identities are available."""
    from loom.cli._common import agent_marker, whoever
    from loom.cli._quilt import open_scan
    from loom.draft_lifecycle import reopen_draft as reopen
    from loom.sync import SyncError

    if agent_marker():
        raise EnvError("Reopening drafts is an author action")
    result = open_scan(quilt_path)
    try:
        answer = reopen(result, document, whoever(result.quilt.root), write=not dry_run)
        Report(answer["message"], ok=not answer.get("confirmation_required", False), dry_run=dry_run, data=answer).emit(
            as_json
        )
    except (SyncError, ValueError, OSError) as exc:
        raise EnvError(str(exc)) from exc
