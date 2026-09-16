"""`loom lint` (book 12.5): every diagnostic, grouped by severity; exit 1 if any error."""

from __future__ import annotations

import click

from loom.cli._common import EXIT_CONTENT, emit_json
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.build_cmds import log_run
from loom.records.store import Records
from loom.scan.model import Diagnostic
from loom.scan.scan import ScanResult


def format_diagnostic(d: Diagnostic) -> str:
    locs = ", ".join(f"{loc.file}:{loc.line}" for loc in d.locations)
    keys = " ".join(d.keys)
    parts = [f"{d.severity:<7} {d.code:<36} {d.message}"]
    if locs:
        parts.append(f"[{locs}]")
    if keys:
        parts.append(f"keys: {keys}")
    return "  ".join(parts)


def all_diagnostics(result: ScanResult) -> list[Diagnostic]:
    """Scanner diagnostics plus those derived from the ledger and review records, in the scanner's order."""
    records = Records(result.quilt.root)
    extra = records.diagnostics(result, records.key_states(result))
    diags = list(result.lint) + extra
    diags.sort(
        key=lambda d: (
            {"error": 0, "warning": 1, "info": 2}[d.severity],
            d.code,
            d.locations[0].file if d.locations else "",
            d.locations[0].line if d.locations else 0,
        )
    )
    return diags


def summary_line(diags: list[Diagnostic]) -> str:
    counts = {s: sum(1 for d in diags if d.severity == s) for s in ("error", "warning", "info")}
    return f"{counts['error']} errors, {counts['warning']} warnings, {counts['info']} infos"


@click.command(name="lint")
@click.option("--json", "as_json", is_flag=True)
@click.option("--run", "run_dir", default=None, envvar="LOOM_RUN", metavar="DIR", help="Log this call to DIR/run.log.")
@quilt_option
@click.pass_context
def lint_command(ctx: click.Context, as_json: bool, run_dir: str | None, quilt_path: str | None) -> None:
    """Scan and print every diagnostic. Fast; no LaTeX runs."""
    log_run(run_dir, "loom lint")
    result = open_scan(quilt_path)
    diags = all_diagnostics(result)
    if as_json:
        emit_json([d.to_dict() for d in diags])
    else:
        for d in diags:
            click.echo(format_diagnostic(d))
        click.echo(summary_line(diags))
    if any(d.severity == "error" for d in diags):
        ctx.exit(EXIT_CONTENT)
