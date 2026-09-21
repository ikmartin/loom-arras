"""`loom ai ...` (book 12.8). M3 ships `discard`; init, orient, start and check arrive at M6."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError, find_session
from loom.cli._quilt import open_quilt, quilt_option


@click.group()
def ai() -> None:
    """The optional AI layer: runs, orientation, promotion, and discarding review records."""


@ai.command()
@click.argument("run", required=False, default=None)
@click.option(
    "--before", default=None, metavar="DATE", help="Discard every record created before this date (YYYY-MM-DD)."
)
@click.option("--author", default=None, help="Discard every record whose author matches.")
@click.option("--target", default=None, help="Discard every record with an annotation on this key.")
@click.option("--undo", is_flag=True, help="Reverse: mark matching records not discarded.")
@quilt_option
def discard(
    run: str | None, before: str | None, author: str | None, target: str | None, undo: bool, quilt_path: str | None
) -> None:
    """Flag a session's or an author's annotations ignored (or unflag with --undo). Nothing is deleted.

    Discarding appends an event like any other change, so a sitting's findings can be dismissed and brought back without anything being rewritten or lost.
    """
    from loom.cli._common import agent_marker
    from loom.clock import stamp
    from loom.records.log import append
    from loom.records.store import Records

    quilt = open_quilt(quilt_path)
    root = quilt.root
    records = Records(root, quilt.history_dir).records
    sources: list[str] = []
    if run:
        found = find_session(root, run)
        # a migrated session's annotations still carry the grouping they were written with
        sources.append(found.source or found.id)
    elif before or author or target:
        for rec in records:
            created = min((a.created for a in rec.annotations), default="")
            if before and not (created and created[:10] < before):
                continue
            if author and not any(a.author_id == author for a in rec.annotations):
                continue
            if target and not any(a.target_key == target for a in rec.annotations):
                continue
            sources.append(rec.rel)
    else:
        raise EnvError("give SESSION, or --before, --author, or --target")
    if not sources:
        click.echo("no matching records")
        return
    from loom.cli._common import whoever
    from loom.sessions import ID, by_source, close, resume

    who = whoever(root)
    known = by_source(root)
    for rel in sources:
        event: dict[str, object] = {
            "event": "discarded",
            "source": rel,
            "when": stamp(),
            "author": who,
            "kind": "agent" if agent_marker() else "human",
            "session": rel if ID.match(rel) else known.get(rel),
        }
        if undo:
            event["undo"] = True
        append(root, event)
        # Discarding a sitting's findings ends the sitting: that is what discarding a run meant, and a session whose
        # every finding is dismissed has no business in the list of what is open.
        sid = rel if ID.match(rel) else known.get(rel)
        if sid:
            (resume if undo else close)(root, sid, who)
        click.echo(f"{'restored' if undo else 'discarded'} {rel}")


@ai.command(name="init")
@click.option("--permissions", is_flag=True, help="Also write the agents' permission settings (.claude/settings.json).")
@click.option("--skills", is_flag=True, help="Also write skill stubs and slash commands for Claude Code.")
@quilt_option
def ai_init(permissions: bool, skills: bool, quilt_path: str | None) -> None:
    """Write ai/ (orientation, modes, runs/) and the vendor files CLAUDE.md and AGENTS.md; refuses if ai/ exists."""
    from loom.ai.layout import init_layer

    quilt = open_quilt(quilt_path)
    try:
        rep = init_layer(quilt.root, permissions=permissions, skills=skills)
    except FileExistsError:
        raise EnvError("ai/ exists; run loom upgrade to refresh it") from None
    for rel in rep.written:
        click.echo(f"wrote {rel}")
    click.echo(
        'next: start your agent here; it reads CLAUDE.md and runs loom ai orient. loom ai start "a name" opens a run.'
    )


@ai.command(name="orient")
@click.option(
    "--session",
    "session",
    default=None,
    envvar="LOOM_SESSION",
    metavar="SESSION",
    help="Attach to this session: also print its journal and command log. An id, a title, or a unique id suffix.",
)
@quilt_option
def ai_orient(session: str | None, quilt_path: str | None) -> None:
    """Print the orientation document followed by the quilt's live state, and with --session that session's own journal.

    This is also how an agent joins a session it did not open: `loom ai orient --session <id>` prints the orientation, the quilt's live state, and that session's journal and command log, which is the scrollback a later sitting resumes from.
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
    click.echo(live_text(result, Records(root, result.quilt.history_dir), where), nl=False)
    log_run(found.id if found else None, "loom ai orient", root)


@ai.command(name="start")
@click.argument("name", required=False, default=None)
@quilt_option
def ai_start(name: str | None, quilt_path: str | None) -> None:
    """Open a session named NAME and make it active, printing its id.

    The same session a person opens with `loom session new`: an agent and the author working the same job land in one place, which they could not when a run was the agent's alone. Loom does not launch your agent -- `loom ai init` writes the line in CLAUDE.md and AGENTS.md that tells one to run `loom ai orient`.
    """
    from loom.cli._common import whoever
    from loom.sessions import create, set_active

    quilt = open_quilt(quilt_path)
    if not (quilt.root / "ai").is_dir():
        raise EnvError("no ai/ in this quilt; run loom ai init first")
    s = create(quilt.root, (name or "").strip() or "untitled", whoever(quilt.root))
    set_active(quilt.root, s.id)
    click.echo(s.id)


@ai.command(name="runs")
@click.option("--all", "show_all", is_flag=True, help="Include closed sessions, marked.")
@quilt_option
def ai_runs(show_all: bool, quilt_path: str | None) -> None:
    """List this quilt's sessions, newest last, as `YYYY-MM-DD: title`. The same list `loom session list` prints."""
    from loom.ai.orient import open_sessions

    quilt = open_quilt(quilt_path)
    rows = open_sessions(quilt.root, include_closed=show_all)
    if not rows:
        click.echo("no sessions yet" if show_all else "no open sessions")
        return
    for _sid, title, created, closed in rows:
        click.echo(f"  {created[:10]}: {title}" + (" (closed)" if closed else ""))


@ai.command(name="name")
@click.argument("new_name")
@click.option(
    "--session", "session", default=None, envvar="LOOM_SESSION", metavar="SESSION", help="The session to rename."
)
@quilt_option
def ai_name(new_name: str, session: str | None, quilt_path: str | None) -> None:
    """Retitle a session. The id it was opened under does not change, because that is its address."""
    from loom.cli._common import whoever
    from loom.sessions import rename

    quilt = open_quilt(quilt_path)
    found = find_session(quilt.root, session)
    rename(quilt.root, found.id, new_name, whoever(quilt.root))
    click.echo(f"{found.id}: {new_name}")


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


@ai.command(name="findings")
@click.option(
    "--session", "session", default=None, envvar="LOOM_SESSION", metavar="SESSION", help="The session to report on."
)
@click.option("--severity", "f_severity", default=None, help="Only findings of this severity.")
@click.option("--kind", "f_kind", default=None, help="Only findings of this kind.")
@click.option("--status", "f_status", default=None, help="Only findings in this state: open, resolved or discarded.")
@click.option("--all", "f_all", is_flag=True, help="Include withdrawn findings, with the reason they were withdrawn.")
@click.option("--json", "as_json", is_flag=True, help="Print the findings as JSON.")
@quilt_option
def ai_findings(
    session: str | None,
    f_severity: str | None,
    f_kind: str | None,
    f_status: str | None,
    f_all: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """What this run has annotated: id, target, kind, status, and the quoted text; `--json` carries the whole finding.

    An agent re-reading its own findings is the common case — a re-check resolves what is met and edits what still stands, and needs the ids to do it. The JSON form carries `message`, `payload` and `placement` too, so a re-check can tell what it already said and what it already suggested without reading the log itself.
    """
    import json

    from loom.cli._quilt import open_scan
    from loom.records.store import Records

    result = open_scan(quilt_path)
    root = result.quilt.root
    found = find_session(root, session)
    rel = found.source or found.id
    rows = [
        {
            "id": a.annotation.id,
            "target": a.annotation.target_key,
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
    if as_json:
        click.echo(json.dumps({"session": found.id, "findings": rows, "proposals": proposals}, indent=2))
        return
    if proposals:
        # what the author did with this run's proposals: a reattaching agent otherwise ran `refs why` on each id it
        # happened to know from the run's thread, which is how it learned the author's decisions three times over
        click.echo(f"{rel}: {len(proposals)} proposal(s)")
        for pr in proposals:
            extra = (
                f" -- {pr['reason']}"
                if pr.get("reason")
                else (" (edited by the author first)" if pr.get("edited") else "")
            )
            if pr.get("renamed_from"):
                extra += f" (renamed by the author from {pr['renamed_from']})"
            click.echo(f"  {pr['id']}  {pr['state']}{extra}")
            # the edit itself: a reattached agent that could not see it diffed its own scratch script against the digest
            for line in pr.get("edit") or []:
                click.echo(f"      {line}")
        click.echo("")
    if not rows:
        click.echo(f"{rel}: no findings yet")
        return
    for r in rows:
        sev = f" {r['severity']}" if r["severity"] else ""
        mark = "" if r["status"] == "open" else f" ({r['status']})"
        quote = f"  \u201c{r['quote']}\u201d" if r["quote"] else ""
        click.echo(f"{r['id']}  {r['target']}  {r['kind']}{sev}{mark}{quote}")
        if r["discarded"]:
            click.echo(f"      withdrawn: {r['discard_reason'] or 'no reason given'}")


@ai.command(name="check")
@click.argument("session", metavar="SESSION")
@quilt_option
@click.pass_context
def ai_check(ctx: click.Context, session: str, quilt_path: str | None) -> None:
    """Report files outside SESSION, the annotation log, and build/ modified since it opened (loom:agent-wrote-outside-run)."""
    from loom.ai.check import outside_writes

    quilt = open_quilt(quilt_path)
    found = find_session(quilt.root, session)  # an id, a title or a unique suffix, as everywhere else (DR-167)
    try:
        hits = outside_writes(quilt.root, found)
    except ValueError as exc:
        raise ContentError(str(exc)) from exc
    for rel in hits:
        click.echo(f"error   loom:agent-wrote-outside-run          {rel} changed after the session opened")
    if hits:
        ctx.exit(1)
    click.echo("ok: nothing outside the session changed")
