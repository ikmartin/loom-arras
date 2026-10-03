"""`loom agent check` (plan 0.14 phase 5): test the command `loom serve` would start an agent with, without starting it."""

from __future__ import annotations

from typing import Any

import click

from loom.cli._common import EXIT_USAGE
from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.report import Group, Item, Report, counted


@click.group(name="agent")
def agent() -> None:
    """The agent loom serve may start for a turn: ai/ai-config.toml, and whether config.toml lets it."""


@agent.command(name="check")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def check_command(as_json: bool, quilt_path: str | None) -> None:
    """Say whether loom serve will start an agent here, with what command, and what would stop it. Runs nothing.

    Exits 2 when launching is on or an agent is configured, and something would stop it: the config is incomplete, its command is not on PATH, or git tracks ai/ai-config.toml -- a command a quilt carries came from whoever committed it, and loom refuses to run it. With no agent configured and launching off there is nothing to stop, and it exits 0.
    """
    from loom.agent import CONFIG, PROMPT, SAMPLE, argv, diagnose

    root = open_quilt(quilt_path).root
    d = diagnose(root)
    lines = ["", f"launching: {'on' if d.launch else 'off'} (launch under [ai] in config.toml)"]
    data: dict[str, Any] = {
        "launch": d.launch,
        "configured": d.configured,
        "config": None,
        "name": None,
        "commands": {label: cmd for label, cmd in d.commands},
        "prompt": None,
        "faults": list(d.faults),
        "unignored": d.unignored,
    }
    if d.config is not None:
        prompt = argv([PROMPT], **SAMPLE, quilt=str(root), name=d.config.name)[0]
        data.update(config=d.config.source, name=d.config.name, prompt=prompt)
        lines += [f"config: {d.config.source}", f"name: {d.config.name}"]
        commands = dict(d.commands)
        for label in ("start", "resume"):
            if label in commands:
                lines.append(f"{label}: {' '.join(commands[label])}")
            else:
                lines.append(f"{label}: (none: start runs every turn)" if label == "resume" else f"{label}: (none)")
        lines.append(f"prompt: {prompt}")
    groups = []
    if d.unignored:
        groups.append(
            Group(
                "warnings",
                [
                    Item(
                        f".gitignore does not ignore {CONFIG}, so it could be committed by accident",
                        fixes=["loom upgrade"],
                    )
                ],
                problem=True,
            )
        )
    if not d.faults:
        verdict = (
            f"ok: loom serve will start {d.config.name if d.config else 'the agent'} for a turn when a message waits"
            if d.launch
            else "ok: the command is sound, and loom serve will not start it until launch = true"
        )
        Report(verdict, groups=groups, lines=lines, data=data).emit(as_json)
        return
    if not d.configured and not d.launch:
        Report(
            "no agent is configured, and launching is off: loom serve starts none",
            groups=groups,
            lines=[*lines, f"config: none; fill in {CONFIG} to configure one"],
            data=data,
        ).emit(as_json)
        return
    faults = Group("faults", [Item(f) for f in d.faults], problem=True, limit=None)
    verdict = (
        f"loom serve will not start the agent: {counted(len(d.faults), 'fault')}"
        if d.launch
        else f"the agent's configuration has {counted(len(d.faults), 'fault')}; launching is off, so loom serve starts nothing"
    )
    Report(verdict, ok=False, exit=EXIT_USAGE, groups=[faults, *groups], lines=lines, data=data).emit(as_json)
