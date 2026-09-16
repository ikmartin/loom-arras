"""`loom doctor`: report the toolchain, the author name, and the arras bundle; exit 2 if a required tool is missing."""

from __future__ import annotations

import click

from loom.cli._common import EXIT_USAGE, emit_json
from loom.doctor import run_doctor


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Machine-readable report on stdout.")
@click.pass_context
def doctor(ctx: click.Context, as_json: bool) -> None:
    """Report Python, the TeX toolchain, git, the arras bundle, the resolved author name, and the interface version."""
    report = run_doctor()
    if as_json:
        emit_json(report.to_dict())
    else:
        click.echo(report.render())
    if not report.ok:
        ctx.exit(EXIT_USAGE)
