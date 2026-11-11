"""`loom build [--keys KEY...] [--force] [--no-compile]`."""

from __future__ import annotations

import click

from loom.cli._common import EXIT_CONTENT
from loom.cli._quilt import open_quilt, quilt_option, resolve_key
from loom.cli.diagnostics import groups as diagnostic_groups
from loom.cli.diagnostics import has_errors, tally
from loom.cli.report import Progress, Report, counted
from loom.paths import BUILD
from loom.render.build import build
from loom.scan.scan import scan


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
    help="Render every block again, ignoring the cache and making again every text TeX refused.",
)
@click.option(
    "--no-compile",
    is_flag=True,
    help="Run no TeX: text no compile makes comes from the cache, else shows as its source.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def build_command(keys: tuple[str, ...], force: bool, no_compile: bool, as_json: bool, quilt_path: str | None) -> None:
    """Scan, derive, render, and publish .loom/build/. Exit 1 if any error-severity diagnostic exists outside the works nothing cites (the build is still published).

    A document is read from the HTML its compile made, and shows as its source until one has. Text no compile makes, a node no document reaches, a digest, a landmark, a comparison, is made by TeX as snippets. Rendering is cached per block by its inputs, which include loom's own version and, in a checkout, loom's code; --force renders everything regardless, and makes again every text TeX refused before. Only errors are listed; `loom lint` lists every diagnostic.
    """
    quilt = open_quilt(quilt_path)
    with Progress("scanning") as progress:
        # the keys are resolved against a scan before anything is built, and the build reuses that scan
        result = scan(quilt) if keys else None
        wanted = [resolve_key(result, k) for k in keys] if result is not None else None
        report = build(quilt, wanted, force=force, reuse=result, progress=progress.told, tex=not no_compile)
    errors = [d for d in report.diagnostics if d.severity == "error"]
    bad = has_errors(errors, report.result)
    done = f"published {BUILD}/: {counted(len(report.rendered), 'block')} rendered, {len(report.skipped)} unchanged"
    Report(
        done + (f"; {tally(errors, report.result)}" if bad else ""),
        ok=not bad,
        exit=EXIT_CONTENT if bad else 0,
        groups=diagnostic_groups(errors, report.result, cited_next="loom lint --json"),
        data={
            "rendered": len(report.rendered),
            "skipped": len(report.skipped),
            "nodes": len(report.manifest["nodes"]),
            "keys": len(report.manifest["keys"]),
            "diagnostics": [d.to_dict() for d in report.diagnostics],
        },
    ).emit(as_json)
