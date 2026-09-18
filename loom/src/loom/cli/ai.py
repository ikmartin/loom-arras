"""`loom ai ...` (book 12.8). M3 ships `discard`; init, orient, start and check arrive at M6."""

from __future__ import annotations

from pathlib import Path

import click

from loom.cli._common import ContentError, EnvError, find_run
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
    """Flag a run's or an author's annotations ignored (or unflag with --undo). Nothing is deleted.

    Discarding appends an event like any other change, so a run's findings can be dismissed and brought back without anything being rewritten or lost.
    """
    from loom.clock import stamp
    from loom.records.log import append
    from loom.records.store import Records

    quilt = open_quilt(quilt_path)
    root = quilt.root
    records = Records(root, quilt.history_dir).records
    sources: list[str] = []
    if run:
        d = find_run(root, run)
        sources.append(d.relative_to(root).as_posix())
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
        raise EnvError("give RUN, or --before, --author, or --target")
    if not sources:
        click.echo("no matching records")
        return
    for rel in sources:
        is_run = rel.startswith("ai/runs/")
        event: dict[str, object] = {
            "event": "discarded",
            "source": rel,
            "when": stamp(),
            "author": rel.rsplit("/", 1)[-1],
            "kind": "agent" if is_run else "human",
            "run": rel if is_run else None,
        }
        if undo:
            event["undo"] = True
        append(root, event)
        toml = root / rel / "run.toml"
        if toml.is_file():
            import re

            text = toml.read_text(encoding="utf-8")
            if "discarded" in text:
                text = re.sub(r"discarded\s*=\s*(true|false)", f"discarded = {'false' if undo else 'true'}", text)
            else:
                text = text.rstrip("\n") + f"\ndiscarded = {'false' if undo else 'true'}\n"
            toml.write_text(text, encoding="utf-8")
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
    "--run",
    "run_dir",
    default=None,
    envvar="LOOM_RUN",
    metavar="RUN",
    help="Attach to this run: also print its thread.md and run.log. A name, a prefix of one, or a path.",
)
@quilt_option
def ai_orient(run_dir: str | None, quilt_path: str | None) -> None:
    """Print the orientation document followed by the quilt's live state, and with --run a run's own journal.

    This is also how an agent attaches to a run it did not start: `loom ai orient --run <name>` prints the orientation, the quilt's live state, and that run's thread.md and run.log, which is the scrollback a later session resumes from.
    """
    from loom.ai.orient import live_text, static_text
    from loom.cli._quilt import open_scan
    from loom.cli.build_cmds import log_run
    from loom.records.store import Records

    result = open_scan(quilt_path)
    root = result.quilt.root
    run: Path | None = find_run(root, run_dir) if run_dir else None
    click.echo(static_text(root), nl=False)
    click.echo(live_text(result, Records(root, result.quilt.history_dir), run), nl=False)
    log_run(run.relative_to(root).as_posix() if run else None, "loom ai orient", root)


@ai.command(name="start")
@click.argument("name", required=False, default=None)
@quilt_option
def ai_start(name: str | None, quilt_path: str | None) -> None:
    """Create a run directory under ai/runs/ named NAME, and print its path.

    Loom does not launch your agent. `loom ai init` writes the line in CLAUDE.md and AGENTS.md that tells one to run `loom ai orient`, so starting a session is `claude`, and this is the command it runs when you ask it to begin a run.
    """
    from loom.ai.runs import start_run

    quilt = open_quilt(quilt_path)
    if not (quilt.root / "ai").is_dir():
        raise EnvError("no ai/ in this quilt; run loom ai init first")
    d = start_run(quilt.root, name)
    click.echo(d.relative_to(quilt.root).as_posix())


@ai.command(name="runs")
@click.option("--all", "show_all", is_flag=True, help="Include discarded runs, marked.")
@quilt_option
def ai_runs(show_all: bool, quilt_path: str | None) -> None:
    """List this quilt's runs, newest last, as `YYYY-MM-DD: name`."""
    from loom.ai.orient import open_runs

    quilt = open_quilt(quilt_path)
    rows = open_runs(quilt.root, include_discarded=show_all)
    if not rows:
        click.echo("no runs yet" if show_all else "no open runs")
        return
    for _rel, name, created, discarded in rows:
        click.echo(f"  {created[:10]}: {name}" + (" (discarded)" if discarded else ""))


@ai.command(name="name")
@click.argument("new_name")
@click.option("--run", "run_dir", default=None, envvar="LOOM_RUN", metavar="RUN", help="The run to rename.")
@quilt_option
def ai_name(new_name: str, run_dir: str | None, quilt_path: str | None) -> None:
    """Rename a run. The directory keeps the name it was created under, which is its address."""
    from loom.ai.runs import rename_run

    quilt = open_quilt(quilt_path)
    d = find_run(quilt.root, run_dir)
    rename_run(d, new_name)
    click.echo(f"{d.relative_to(quilt.root).as_posix()}: {new_name}")


@ai.command(name="findings")
@click.option("--run", "run_dir", default=None, envvar="LOOM_RUN", metavar="RUN", help="The run to report on.")
@click.option("--severity", "f_severity", default=None, help="Only findings of this severity.")
@click.option("--kind", "f_kind", default=None, help="Only findings of this kind.")
@click.option("--status", "f_status", default=None, help="Only findings in this state: open, resolved or discarded.")
@click.option("--all", "f_all", is_flag=True, help="Include withdrawn findings, with the reason they were withdrawn.")
@click.option("--json", "as_json", is_flag=True, help="Print the findings as JSON.")
@quilt_option
def ai_findings(
    run_dir: str | None,
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
    d = find_run(root, run_dir)
    rel = d.relative_to(root).as_posix()
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
        if a.record.rel.startswith(f"{rel}/") or a.annotation.author_id == d.name
    ]
    rows = [
        r
        for r in rows
        if (f_all or not r["discarded"])
        and (not f_severity or r["severity"] == f_severity)
        and (not f_kind or r["kind"] == f_kind)
        and (not f_status or r["status"] == f_status)
    ]
    if as_json:
        click.echo(json.dumps({"run": rel, "findings": rows}, indent=2))
        return
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
@click.argument("run")
@quilt_option
@click.pass_context
def ai_check(ctx: click.Context, run: str, quilt_path: str | None) -> None:
    """Report files outside RUN, the annotation log, and build/ modified since the run started (loom:agent-wrote-outside-run)."""
    from loom.ai.check import outside_writes

    quilt = open_quilt(quilt_path)
    run_dir = find_run(quilt.root, run)  # a name, a prefix or a path, resolved as everywhere else (DR-167)
    try:
        hits = outside_writes(quilt.root, run_dir)
    except ValueError as exc:
        raise ContentError(str(exc)) from exc
    for rel in hits:
        click.echo(f"error   loom:agent-wrote-outside-run          {rel} changed after the run started")
    if hits:
        ctx.exit(1)
    click.echo("ok: nothing outside the run changed")
