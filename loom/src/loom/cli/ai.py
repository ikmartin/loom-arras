"""`loom ai ...` (book 12.8). M3 ships `discard`; init, orient, start, promote, and check arrive at M6."""

from __future__ import annotations

from pathlib import Path

import click

from loom.cli._common import ContentError, EnvError
from loom.cli._quilt import open_quilt, quilt_option
from loom.records.annotations import load_record, record_paths


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
    """Flag a run's or a comment session's records ignored (or unflag with --undo). Nothing is deleted."""
    quilt = open_quilt(quilt_path)
    root = quilt.root
    paths: list[Path] = []
    if run:
        p = Path(run).expanduser()
        if not p.is_absolute():
            p = root / p
        if p.is_dir():
            p = p / "annotations.json"
        if not p.is_file():
            raise EnvError(f"no record at {run}")
        paths.append(p)
    elif before or author or target:
        for p in record_paths(root):
            rec = load_record(root, p)
            if isinstance(rec, str):
                continue
            created = min((a.created for a in rec.annotations), default="")
            if before and not (created and created[:10] < before):
                continue
            if author and not any(a.author_id == author for a in rec.annotations):
                continue
            if target and not any(a.target_key == target for a in rec.annotations):
                continue
            paths.append(p)
    else:
        raise EnvError("give RUN, or --before, --author, or --target")
    if not paths:
        click.echo("no matching records")
        return
    for p in paths:
        rec = load_record(root, p)
        if isinstance(rec, str):
            raise ContentError(rec)
        rec.discarded = not undo
        rec.write()
        toml = p.parent / "run.toml"
        if toml.is_file():
            text = toml.read_text(encoding="utf-8")
            if "discarded" in text:
                import re

                text = re.sub(r"discarded\s*=\s*(true|false)", f"discarded = {'false' if undo else 'true'}", text)
            else:
                text = text.rstrip("\n") + f"\ndiscarded = {'false' if undo else 'true'}\n"
            toml.write_text(text, encoding="utf-8")
        click.echo(f"{'restored' if undo else 'discarded'} {p.relative_to(root).as_posix()}")


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
    click.echo("next: loom ai start [SLUG]; then, in the agent, loom ai orient --run $LOOM_RUN")


@ai.command(name="orient")
@click.option(
    "--run",
    "run_dir",
    default=None,
    envvar="LOOM_RUN",
    metavar="RUN",
    help="Also print this run's thread.md and run.log.",
)
@quilt_option
def ai_orient(run_dir: str | None, quilt_path: str | None) -> None:
    """Print the orientation document followed by the quilt's live state (and a run's journal with --run)."""
    from loom.ai.orient import live_text, static_text
    from loom.cli._quilt import open_scan
    from loom.cli.build_cmds import log_run
    from loom.records.store import Records

    result = open_scan(quilt_path)
    root = result.quilt.root
    run: Path | None = None
    if run_dir:
        run = Path(run_dir)
        if not run.is_absolute():
            run = root / run
        if not run.is_dir():
            raise EnvError(f"no run at {run_dir}")
    click.echo(static_text(root), nl=False)
    click.echo(live_text(result, Records(root), run), nl=False)
    log_run(run_dir, "loom ai orient", root)


@ai.command(name="start")
@click.argument("slug", required=False, default=None)
@click.option("--no-launch", is_flag=True, help="Create the run without launching [ai] agent.")
@quilt_option
@click.pass_context
def ai_start(ctx: click.Context, slug: str | None, no_launch: bool, quilt_path: str | None) -> None:
    """Create a run directory under ai/runs/, print its path, and launch [ai] agent from config.toml if set."""
    from loom.ai.runs import launch_agent, start_run

    quilt = open_quilt(quilt_path)
    if not (quilt.root / "ai").is_dir():
        raise EnvError("no ai/ in this quilt; run loom ai init first")
    agent = quilt.config.ai_agent
    d = start_run(quilt.root, slug, agent if agent and not no_launch else None)
    rel = d.relative_to(quilt.root).as_posix()
    click.echo(rel)
    if agent and not no_launch:
        click.echo(f"(launching: {agent})")
        try:
            code = launch_agent(quilt.root, agent, d)
        except FileNotFoundError as exc:
            raise EnvError(f"[ai] agent = {agent!r} is not on PATH ({exc}); the run {rel} was created") from None
        if code != 0:
            ctx.exit(code)


@ai.command(name="promote")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--replace", is_flag=True, help="Overwrite an existing digest after showing the diff.")
@quilt_option
@click.pass_context
def ai_promote(ctx: click.Context, path: Path, replace: bool, quilt_path: str | None) -> None:
    """Copy a digest out of a run into digests/; lint runs on the result. A drafted node is previewed in arras and pasted by hand."""
    import difflib

    from loom.ai.promote import plan_promotion, write_promotion
    from loom.cli._quilt import open_scan
    from loom.cli.lint_cmd import all_diagnostics
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    result = open_scan(quilt_path)
    root = result.quilt.root
    try:
        plan = plan_promotion(result, path.resolve())
    except ValueError as exc:
        raise ContentError(str(exc)) from exc
    dest = root / plan.target
    if dest.exists() and plan.kind == "digest":
        if not replace:
            raise ContentError(f"{plan.target} exists; pass --replace to overwrite it")
        diff = difflib.unified_diff(
            dest.read_text(encoding="utf-8").splitlines(keepends=True),
            plan.text.splitlines(keepends=True),
            fromfile=plan.target,
            tofile=plan.target,
        )
        click.echo("".join(diff), nl=False)
    try:
        write_promotion(root, plan, replace)
    except FileExistsError:
        raise ContentError(f"{plan.target} exists") from None
    click.echo(f"promoted {path.name} -> {plan.target}")
    run_dir = path.resolve().parent
    if (run_dir / "run.toml").is_file():
        from loom.cli.build_cmds import log_run

        log_run(str(run_dir), f"loom ai promote {path.name} -> {plan.target}")  # so ai check knows the author moved it
    rescan = scan(load_quilt(root))
    problems = [d for d in all_diagnostics(rescan) if any(loc.file == plan.target for loc in d.locations)]
    for d in problems:
        click.echo(f"  {d.severity:<8}{d.code:<34}{d.message}")
    if any(d.severity == "error" for d in problems):
        ctx.exit(1)


@ai.command(name="check")
@click.argument("run")
@quilt_option
@click.pass_context
def ai_check(ctx: click.Context, run: str, quilt_path: str | None) -> None:
    """Report files outside RUN, comments/, and build/ modified since the run started (loom:agent-wrote-outside-run)."""
    from loom.ai.check import outside_writes

    quilt = open_quilt(quilt_path)
    run_dir = Path(run)
    if not run_dir.is_absolute():
        run_dir = quilt.root / run_dir
    if not run_dir.is_dir():
        raise EnvError(f"no run at {run}")
    try:
        hits = outside_writes(quilt.root, run_dir)
    except ValueError as exc:
        raise ContentError(str(exc)) from exc
    for rel in hits:
        click.echo(f"error   loom:agent-wrote-outside-run          {rel} changed after the run started")
    if hits:
        ctx.exit(1)
    click.echo("ok: nothing outside the run changed")
