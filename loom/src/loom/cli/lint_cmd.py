"""`loom lint` (book 12.5): every diagnostic, grouped by severity; exit 1 if any error."""

from __future__ import annotations

import click

from loom.cli._common import EXIT_CONTENT, emit_json
from loom.cli._quilt import open_scan, quilt_option
from loom.scan.model import Diagnostic


def format_diagnostic(d: Diagnostic) -> str:
    locs = ", ".join(f"{loc.file}:{loc.line}" for loc in d.locations)
    keys = " ".join(d.keys)
    parts = [f"{d.severity:<7} {d.code:<36} {d.message}"]
    if locs:
        parts.append(f"[{locs}]")
    if keys:
        parts.append(f"keys: {keys}")
    return "  ".join(parts)


def summary_line(diags: list[Diagnostic]) -> str:
    counts = {s: sum(1 for d in diags if d.severity == s) for s in ("error", "warning", "info")}
    return f"{counts['error']} errors, {counts['warning']} warnings, {counts['info']} infos"


@click.command(name="lint")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
@click.pass_context
def lint_command(ctx: click.Context, as_json: bool, quilt_path: str | None) -> None:
    """Scan and print every diagnostic. Fast; no LaTeX runs."""
    result = open_scan(quilt_path)
    diags = result.lint
    if as_json:
        emit_json([d.to_dict() for d in diags])
    else:
        for d in diags:
            click.echo(format_diagnostic(d))
        click.echo(summary_line(diags))
    if any(d.severity == "error" for d in diags):
        ctx.exit(EXIT_CONTENT)
