"""`loom build [--keys KEY...]` (book 12.5)."""

from __future__ import annotations

import click

from loom.cli._common import EXIT_CONTENT, note
from loom.cli._quilt import open_quilt, quilt_option
from loom.render.build import build


@click.command(name="build")
@click.option(
    "--keys",
    "keys",
    multiple=True,
    help="Limit rendering to these keys and their masters; the manifest is always complete.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Render every fragment again, ignoring the cache and retrying remembered SVG failures.",
)
@quilt_option
@click.pass_context
def build_command(ctx: click.Context, keys: tuple[str, ...], force: bool, quilt_path: str | None) -> None:
    """Scan, derive, render, and publish build/. Exit 1 if any error-severity diagnostic exists (the build is still published).

    Rendering is cached per fragment by its inputs, which include loom's own version and, in a checkout, loom's code; --force renders everything regardless, and tries again every block whose SVG failed before.
    """
    quilt = open_quilt(quilt_path)
    report = build(quilt, list(keys) or None, force=force)
    errors = sum(1 for d in report.diagnostics if d.severity == "error")
    click.echo(
        f"rendered {len(report.rendered)} fragment(s), {len(report.skipped)} unchanged; {len(report.manifest['nodes'])} nodes, {len(report.manifest['keys'])} keys; {errors} error(s)"
    )
    for d in report.diagnostics:
        if d.severity == "error":
            note(f"error   {d.code:<36} {d.message}")
    if report.has_errors:
        ctx.exit(EXIT_CONTENT)
