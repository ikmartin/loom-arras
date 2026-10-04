"""`loom ai ...` (book 11 and 12.8): the agent layer, its orientation, its documents, and a session's annotations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from loom.cli._common import EXIT_CONTENT, EnvError, NotFoundError, find_session
from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.help import CommandGroup
from loom.cli.report import Group, Item, Report, counted
from loom.cli.review import STATUSES
from loom.records.annotations import KINDS, SEVERITIES

if TYPE_CHECKING:
    from loom.ai.layout import LayerReport


@click.group(cls=CommandGroup)
def ai() -> None:
    """Set up the agent layer and read what an agent works from: its orientation, its documents and its annotations."""


@ai.command()
@click.argument("run", metavar="SESSION", required=False, default=None)
@click.option(
    "--before",
    default=None,
    metavar="DATE",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Withdraw every record created before this date (YYYY-MM-DD).",
)
@click.option("--by", "by", default=None, metavar="NAME", help="Withdraw every record with an annotation by NAME.")
@click.option("--target", default=None, metavar="KEY", help="Withdraw every record with an annotation on KEY.")
@click.option("--undo", is_flag=True, help="Restore the matching records instead.")
@click.option("--dry-run", is_flag=True, help="Say what would be withdrawn and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def discard(
    run: str | None,
    before: datetime | None,
    by: str | None,
    target: str | None,
    undo: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Withdraw a session's annotations, or those matching --before, --by or --target; --undo restores them.

    Withdrawing appends an event like any other change, so a sitting's annotations can be withdrawn and restored without anything being rewritten or lost. A withdrawn session is closed, and a restored one opened again.
    """
    from loom.cli._common import agent_marker, refuse_under_agent
    from loom.clock import stamp
    from loom.records.log import append
    from loom.records.store import Records

    refuse_under_agent(
        "loom ai discard",
        "Withdrawing a session's annotations is the author's; ask the author, or withdraw one of your own with loom annotate --discard.",
    )
    quilt = open_quilt(quilt_path)
    root = quilt.root
    records = Records(root, quilt.history_dir).records
    sources: list[str] = []
    if run:
        found = find_session(root, run)
        sources.append(found.id)
    elif before or by or target:
        if target and not any(a.target_key == target for rec in records for a in rec.annotations):
            from loom.scan.scan import scan

            if target not in scan(quilt).nodes:
                raise NotFoundError("key", f"{target} is no key of this quilt and no annotation's target")
        for rec in records:
            created = min((a.created for a in rec.annotations), default="")
            # compared as ISO dates, which order as their strings do once both are YYYY-MM-DD
            if before and not (created and created[:10] < before.date().isoformat()):
                continue
            if by and not any(a.author_id == by for a in rec.annotations):
                continue
            if target and not any(a.target_key == target for a in rec.annotations):
                continue
            sources.append(rec.rel)
    else:
        raise EnvError("give SESSION, or --before, --by, or --target")
    verb = "restored" if undo else "withdrew"
    data = {"sessions": sorted(sources), "undo": undo}
    if not sources:
        Report(f"no matching records; nothing {'restored' if undo else 'withdrawn'}", data=data).emit(as_json)
        return
    heading = ("would be " if dry_run else "") + ("restored" if undo else "withdrawn")
    listed = [Group(heading, [Item("", key=rel) for rel in sorted(sources)], limit=None)]
    if dry_run:
        Report(
            f"would {'restore' if undo else 'withdraw'} the annotations of {counted(len(sources), 'session')}",
            dry_run=True,
            groups=listed,
            data=data,
        ).emit(as_json)
        return
    from loom.cli._common import whoever
    from loom.sessions import ID, close, resume

    who = whoever(root)
    for rel in sources:
        event: dict[str, object] = {
            "event": "discarded",
            "source": rel,
            "when": stamp(),
            "author": who,
            "kind": "agent" if agent_marker() else "human",
            "session": rel,
        }
        if undo:
            event["undo"] = True
        append(root, event)
        # withdrawing a sitting's annotations ends the sitting; a session whose every annotation is withdrawn has no business in the list of what is open
        if ID.match(rel):
            (resume if undo else close)(root, rel, who)
    Report(
        f"{verb} the annotations of {counted(len(sources), 'session')}"
        + ("; each is open again" if undo else "; each is closed, and nothing is deleted"),
        groups=listed,
        data=data,
    ).emit(as_json)


#: The agents `ai init --agent` can name in `ai/ai-config.toml`; with none, every key is written commented out.
AGENTS = ("claude", "codex")


def install_layer(root: Path, *, skills: bool = False, agent: str | None = None, write: bool = True) -> LayerReport:
    """Write the agent layer into a quilt, or refresh it where `ai/` exists, and `ai/ai-config.toml` when it is absent.

    Parameters
    ----------
    root : Path
        The quilt root.
    skills : bool, default False
        Also write the Claude Code skills and slash commands; where `ai/` exists they are refreshed when present either way.
    agent : str, optional
        `claude` or `codex`, whose command a new `ai/ai-config.toml` names; default every key commented out. An existing one is the person's and is never touched.
    write : bool, default True
        False writes nothing and reports what would be written.

    Returns
    -------
    LayerReport
        `written` (quilt-relative paths), and where `ai/` existed, `kept` and `new_beside` for edited mode files, as `loom upgrade` reports them.

    See Also
    --------
    loom.ai.layout.upgrade_layer : the refresh alone, which `loom upgrade` runs.
    """
    from loom.agent import CONFIG, config_text
    from loom.ai.layout import (
        VERSION_FILE,
        LayerReport,
        ensure_root_line,
        init_layer,
        quilt_config,
        tracked_docs,
        upgrade_layer,
        vendor_files,
    )

    if not (root / "ai").exists():
        if write:
            rep = init_layer(root, skills=skills)
        else:
            rep = LayerReport(written=[*tracked_docs(), "ai/README.md", f"ai/{VERSION_FILE}"])
            rep.written += [*vendor_files(quilt_config(root), True, skills, True), *ensure_root_line(root, False)]
    else:
        rep = upgrade_layer(root, write=write)
        if skills:
            for rel, text in vendor_files(quilt_config(root), False, True, False).items():
                p = root / rel
                if rel in rep.written or (p.is_file() and p.read_text(encoding="utf-8") == text):
                    continue
                if write:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(text, encoding="utf-8")
                rep.written.append(rel)
    if not (root / CONFIG).exists():
        if write:
            (root / CONFIG).parent.mkdir(parents=True, exist_ok=True)
            (root / CONFIG).write_text(config_text(agent), encoding="utf-8")
        rep.written.append(CONFIG)
    return rep


@ai.command(name="init")
@click.option("--skills", is_flag=True, help="Also write skill stubs and slash commands for Claude Code.")
@click.option(
    "--agent",
    type=click.Choice(AGENTS),
    default=None,
    help="The agent a new ai/ai-config.toml names; default every key commented out. An existing one is kept.",
)
@click.option("--dry-run", is_flag=True, help="Say what would be written and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def ai_init(skills: bool, agent: str | None, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Write the agent layer: ai/ (orientation, rules, modes), ai/ai-config.toml, CLAUDE.md and AGENTS.md, and the permission files.

    The permission files say what agents may run, for Claude Code (.claude/settings.json) and Codex (.codex/rules/loom.rules). Where ai/ exists this refreshes what `loom upgrade` would, keeping an edited mode file and writing the new version beside it; an existing ai/ai-config.toml is the person's and is kept.
    """
    quilt = open_quilt(quilt_path)
    existed = (quilt.root / "ai").is_dir()
    rep = install_layer(quilt.root, skills=skills, agent=agent, write=not dry_run)
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
    data = {"written": written, "kept": sorted(rep.kept), "new_beside": sorted(rep.new_beside), "refreshed": existed}
    if dry_run:
        verdict = f"would write {counted(len(written), 'file')} of the agent layer" if written else "nothing to write"
    elif not existed:
        verdict = f"wrote the agent layer, {counted(len(written), 'file')}; start your agent here: it reads CLAUDE.md and runs loom ai orient"
    elif written or rep.kept:
        verdict = f"refreshed the agent layer: {counted(len(written), 'file')} written" + (
            f", {counted(len(rep.kept), 'edited file')} kept" if rep.kept else ""
        )
    else:
        verdict = "the agent layer is current; nothing written"
    Report(verdict, dry_run=dry_run, groups=groups, data=data).emit(as_json)


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
    from loom.ai.orient import live_text, static_text
    from loom.cli._quilt import open_scan
    from loom.cli.build_cmds import log_run
    from loom.records.store import Records

    result = open_scan(quilt_path)
    root = result.quilt.root
    from loom.sessions import files_dir

    found = find_session(root, session) if session else None
    where = files_dir(root, found) if found else None
    click.echo(static_text(root), nl=False)
    click.echo(live_text(result, Records(root, result.quilt.history_dir), where, found.id if found else None), nl=False)
    log_run(found.id if found else None, "loom ai orient", root)


@ai.command(name="drafts")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def ai_drafts(as_json: bool, quilt_path: str | None) -> None:
    """List each agent document drafted from a working document, and what has moved in that document since.

    Before a large instruction, an agent checks its document here: a stale one is refreshed first, or the agent says what it is working against.
    """
    from loom.cli._quilt import open_scan
    from loom.drafts import copy_states
    from loom.history.ledger import load_history

    result = open_scan(quilt_path)
    states = sorted(copy_states(result, load_history(result.quilt.history_dir)), key=lambda st: st.copy)
    data = {"copies": [st.to_dict() for st in states]}
    if not states:
        Report(
            f"no agent documents drafted from a working document: loom draft DOC --ai NAME writes one into {result.quilt.config.drafting_ai}/",
            data=data,
        ).emit(as_json)
        return
    items = []
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
                fixes=[f"loom ai refresh {st.copy}"],
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


def run_proposals(root: Path, run: str) -> list[dict[str, Any]]:
    """Every digest proposal a run made, with the author's decision on it: state, the edit as diff lines, and the reason for a discard."""
    from loom.refs.proposals import edit_diff, load_results, read_events

    out: list[dict[str, Any]] = []
    for path in sorted((root / "digests").glob("*.results.json")):
        ck = path.name[: -len(".results.json")]
        reasons = {e.get("id"): e.get("reason", "") for e in read_events(root, ck) if e.get("event") == "discarded"}
        for rid, r in sorted(load_results(root, ck).items()):
            if not any(o.get("act") == "proposed" and Path(str(o.get("by", ""))).name == run for o in r.origin):
                continue
            out.append(
                {
                    "id": rid,
                    "work": ck,
                    "state": "transcription verified" if r.state == "verified" else r.state,
                    "edited": any(o.get("act") == "edited" for o in r.origin),
                    "edit": edit_diff(r),
                    "renamed_from": next((str(o.get("was")) for o in r.origin if o.get("act") == "renamed"), ""),
                    "reason": reasons.get(rid, "") if r.state == "discarded" else "",
                }
            )
    return out


@ai.command(name="annotations")
@click.option(
    "--session", "session", default=None, envvar="LOOM_SESSION", metavar="SESSION", help="The session to report on."
)
@click.option(
    "--severity", "f_severity", type=click.Choice(SEVERITIES), default=None, help="Only annotations of this severity."
)
@click.option("--kind", "f_kind", type=click.Choice(KINDS), default=None, help="Only annotations of this kind.")
@click.option("--status", "f_status", type=click.Choice(STATUSES), default=None, help="Only annotations in this state.")
@click.option(
    "--all", "f_all", is_flag=True, help="Include withdrawn annotations, with the reason they were withdrawn."
)
@click.option("--json", "as_json", is_flag=True, help="Print the annotations as JSON.")
@quilt_option
def ai_annotations(
    session: str | None,
    f_severity: str | None,
    f_kind: str | None,
    f_status: str | None,
    f_all: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """List a session's annotations: id, target, kind, status and the quoted text; `--json` carries each one whole.

    An agent re-reading its own annotations is the common case — a re-check resolves what is met and edits what still stands, and needs the ids to do it. The JSON form carries `message`, `payload` and `placement` too, so a re-check can tell what it already said and what it already suggested without reading the log itself.
    """
    from loom.cli._quilt import open_scan
    from loom.records.store import Records

    result = open_scan(quilt_path)
    root = result.quilt.root
    found = find_session(root, session)
    rel = found.id
    rows = [
        {
            "id": a.annotation.id,
            "target": a.annotation.target_key,
            # a note on a page of a cited work: the citekey the agent knows it by, and the page (plan 0.13 item 2)
            "work": a.work or None,
            "page": a.annotation.anchor.page if a.annotation.anchor else None,
            "kind": a.annotation.kind,
            "severity": a.annotation.severity,
            "status": a.annotation.status,
            "reply_to": a.annotation.in_reply_to,
            "detached": a.detached,
            "recorded": a.recorded,
            "quote": a.annotation.selector.exact if a.annotation.selector else None,
            "message": a.annotation.body,
            "payload": a.annotation.payload,
            "placement": a.annotation.placement,
            "discarded": a.annotation.status == "discarded" or a.record.discarded,
            "discard_reason": a.annotation.discard_reason,
        }
        for a in Records(root, result.quilt.history_dir).resolved(result)
        if a.record.rel == rel or a.record.rel.startswith(f"{rel}/")
    ]
    rows = [
        r
        for r in rows
        if (f_all or not r["discarded"])
        and (not f_severity or r["severity"] == f_severity)
        and (not f_kind or r["kind"] == f_kind)
        and (not f_status or r["status"] == f_status)
    ]
    proposals = run_proposals(root, rel.rsplit("/", 1)[-1])
    # what the author did with this run's proposals: a reattaching agent otherwise ran `library why` on each id it happened to know from the run's thread, which is how it learned the author's decisions three times over
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
    items = []
    for r in rows:
        sev = f" {r['severity']}" if r["severity"] else ""
        shown = "withdrawn" if r["status"] == "discarded" else r["status"]
        mark = "" if shown == "open" or r["discarded"] else f" ({shown})"
        quote = f"  \u201c{r['quote']}\u201d" if r["quote"] else ""
        where = f"{r['work']} p.{r['page']}" if r["page"] else r["target"]
        withdrawn = f"; withdrawn: {r['discard_reason'] or 'no reason given'}" if r["discarded"] else ""
        items.append(Item(f"{r['id']}  {where}  {r['kind']}{sev}{mark}{quote}{withdrawn}"))
    verdict = f"{rel}: " + (counted(len(rows), "annotation") if rows else "no annotations yet")
    if proposals:
        verdict += f", {counted(len(proposals), 'proposal')}"
    Report(
        verdict,
        groups=[Group("annotations", items, limit=None)] if items else [],
        lines=lines,
        data={"session": found.id, "annotations": rows, "proposals": proposals},
    ).emit(as_json)


@ai.command(name="refresh")
@click.argument("document")
@click.option("--dry-run", is_flag=True, help="Say what would be refreshed and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
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
                    next=f"loom ai refresh {name}",
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
