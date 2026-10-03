"""`loom build [--keys KEY...]` (book 12.5)."""

from __future__ import annotations

import click

from loom.cli._common import EXIT_CONTENT
from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.diagnostics import groups as diagnostic_groups
from loom.cli.diagnostics import tally
from loom.cli.report import Progress, Report, counted
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
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def build_command(keys: tuple[str, ...], force: bool, as_json: bool, quilt_path: str | None) -> None:
    """Scan, derive, render, and publish build/. Exit 1 if any error-severity diagnostic exists (the build is still published).

    Rendering is cached per fragment by its inputs, which include loom's own version and, in a checkout, loom's code; --force renders everything regardless, and tries again every block whose SVG failed before. Only errors are listed; `loom lint` lists every diagnostic.
    """
    quilt = open_quilt(quilt_path)
    with Progress("scanning") as progress:
        report = build(quilt, list(keys) or None, force=force, progress=progress.told)
    errors = [d for d in report.diagnostics if d.severity == "error"]
    done = f"published build/: {counted(len(report.rendered), 'fragment')} rendered, {len(report.skipped)} unchanged"
    Report(
        done + (f"; {tally(errors, report.result)}" if errors else ""),
        ok=not report.has_errors,
        exit=EXIT_CONTENT if report.has_errors else 0,
        groups=diagnostic_groups(errors, report.result, cited_next="loom lint --json"),
        data={
            "rendered": len(report.rendered),
            "skipped": len(report.skipped),
            "nodes": len(report.manifest["nodes"]),
            "keys": len(report.manifest["keys"]),
            "diagnostics": [d.to_dict() for d in report.diagnostics],
        },
    ).emit(as_json)
