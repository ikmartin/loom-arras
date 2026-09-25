"""`loom doctor`: the one command to run when something is off -- the machine's tools, the author name and the arras bundle, and the quilt's own setup when run inside one."""

from __future__ import annotations

import click

from loom.cli._common import emit_json
from loom.cli._quilt import quilt_option
from loom.doctor import run_doctor


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Machine-readable report on stdout.")
@click.option("--strict", is_flag=True, help="Count a warning as a failure: exit 2 when any item warns.")
@click.option("--agents", is_flag=True, help="Also look for claude and codex, as when the quilt configures an agent.")
@quilt_option
@click.pass_context
def doctor(ctx: click.Context, as_json: bool, strict: bool, agents: bool, quilt_path: str | None) -> None:
    """Check the TeX toolchain and what loom needs of it, poppler, git, the author name and the arras bundle; inside a quilt, also its engine, its agent configuration, its generated files, its .gitignore and its config.

    Each item is ok, warn (works, but you will hit it) or fail (a command you need will refuse), with the command that fixes it. Exits 0 when nothing fails and 2 when anything does; under --strict a warning counts as a failure. Writes nothing; a tool is run only to ask its version or test what loom needs of it, and one that has not answered in 10 s is reported as hung.
    """
    report = run_doctor(quilt_path, agents=agents, strict=strict)
    if as_json:
        emit_json(report.to_dict())
    else:
        click.echo(report.render())
    ctx.exit(report.exit_code)
