"""`loom agent check` (plan 0.14 phase 5): test the command `loom serve` would start an agent with, without starting it."""

from __future__ import annotations

import shutil

import click

from loom.cli._quilt import open_quilt, quilt_option


@click.group(name="agent")
def agent() -> None:
    """The agent loom serve may start for a turn: ai/ai-config.toml, and whether config.toml lets it."""


@agent.command(name="check")
@quilt_option
def check_command(quilt_path: str | None) -> None:
    """Say whether loom serve will start an agent here, with what command, and what would stop it. Runs nothing.

    Exits 1 when the config is incomplete, its command is not on PATH, or git tracks ai/ai-config.toml -- a command a quilt carries came from whoever committed it, and loom refuses to run it.
    """
    from loom.agent import CONFIG, PROMPT, argv, launching, load, tracked

    root = open_quilt(quilt_path).root
    faults: list[str] = []
    on = launching(root)
    click.echo(f"launching: {'on' if on else 'off'} (launch under [ai] in config.toml)")
    cfg, problems = load(root)
    faults += problems
    if tracked(root):
        faults.append(f"git tracks {CONFIG}: loom will not run a command the quilt carries; git rm --cached it")
    if cfg is not None:
        click.echo(f"config: {cfg.source}")
        click.echo(f"name: {cfg.name}")
        sample = "s-0000-00-00-0000"
        fill = {"session": sample, "agent_session": "<the session's conversation id>", "quilt": str(root)}
        fill["prompt"] = "<the prompt>"
        for label, template in (("start", cfg.start), ("resume", cfg.resume)):
            if not template:
                click.echo(f"{label}: (none: start runs every turn)" if label == "resume" else f"{label}: (none)")
                continue
            cmd = argv(template, **fill)
            click.echo(f"{label}: {' '.join(cmd)}")
            where = shutil.which(cmd[0])
            if where is None:
                faults.append(f"{cmd[0]} is not on PATH")
        click.echo("prompt: " + argv([PROMPT], **fill, name=cfg.name)[0])
    from loom.agent import unignored

    if CONFIG in unignored(root):
        click.echo(
            f"note: .gitignore does not ignore {CONFIG}, so it could be committed by accident; loom upgrade adds it"
        )
    for f in faults:
        click.echo(f"fault: {f}")
    if faults:
        raise SystemExit(1)
    click.echo("ok" + ("" if on else ": the command is sound, and loom serve will not start it until launch = true"))
