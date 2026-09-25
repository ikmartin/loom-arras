"""`loom agent check` (plan 0.14 phase 5): test the command `loom serve` would start an agent with, without starting it."""

from __future__ import annotations

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
    from loom.agent import CONFIG, PROMPT, SAMPLE, argv, diagnose

    root = open_quilt(quilt_path).root
    d = diagnose(root)
    click.echo(f"launching: {'on' if d.launch else 'off'} (launch under [ai] in config.toml)")
    if d.config is not None:
        click.echo(f"config: {d.config.source}")
        click.echo(f"name: {d.config.name}")
        commands = dict(d.commands)
        for label in ("start", "resume"):
            if label in commands:
                click.echo(f"{label}: {' '.join(commands[label])}")
            else:
                click.echo(f"{label}: (none: start runs every turn)" if label == "resume" else f"{label}: (none)")
        click.echo("prompt: " + argv([PROMPT], **SAMPLE, quilt=str(root), name=d.config.name)[0])
    if d.unignored:
        click.echo(
            f"note: .gitignore does not ignore {CONFIG}, so it could be committed by accident; loom upgrade adds it"
        )
    for f in d.faults:
        click.echo(f"fault: {f}")
    if d.faults:
        raise SystemExit(1)
    click.echo(
        "ok" + ("" if d.launch else ": the command is sound, and loom serve will not start it until launch = true")
    )
