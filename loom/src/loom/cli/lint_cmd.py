"""`loom lint` (book 12.5): every diagnostic, one group per code with the author's before the cited works'; exit 1 if any error. `--nodes` groups by node id (book 17.16)."""

from __future__ import annotations

import click

from loom.cli._common import EXIT_CONTENT
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.build_cmds import log_run
from loom.cli.diagnostics import groups as diagnostic_groups
from loom.cli.diagnostics import has_errors, tally
from loom.cli.diagnostics import item as diag_item
from loom.cli.report import Group, Report, counted
from loom.history.checks import verify
from loom.history.ledger import load_history
from loom.records.store import Records
from loom.scan.labels import is_id_shaped
from loom.scan.model import Diagnostic
from loom.scan.scan import ScanResult

NODE_CODES = {
    "duplicate-id",
    "unreachable",
    "dangling-link",
    "loom:id-reused",
    "loom:node-recovered",
    "loom:unlabelled-node",
    "loom:reference-to-loose",
    "loom:missing-proof",
}


def format_diagnostic(d: Diagnostic) -> str:
    locs = ", ".join(f"{loc.file}:{loc.line}" for loc in d.locations)
    keys = " ".join(d.keys)
    parts = [f"{d.severity:<7} {d.code:<36} {d.message}"]
    if locs:
        parts.append(f"[{locs}]")
    if keys:
        parts.append(f"keys: {keys}")
    return "  ".join(parts)


def _sorted(diags: list[Diagnostic]) -> list[Diagnostic]:
    diags.sort(
        key=lambda d: (
            {"error": 0, "warning": 1, "info": 2}[d.severity],
            d.code,
            d.locations[0].file if d.locations else "",
            d.locations[0].line if d.locations else 0,
        )
    )
    return diags


def all_diagnostics(result: ScanResult) -> list[Diagnostic]:
    """Scanner diagnostics plus those derived from the ledger, the review records, and the full walk of the history, in the scanner's order."""
    records = Records(result.quilt.root, result.quilt.history_dir)
    extra = records.diagnostics(result, records.key_states(result))
    seen = {(d.code, d.message) for d in result.lint}
    walk = [d for d in verify(result, load_history(result.quilt.history_dir)) if (d.code, d.message) not in seen]
    return _sorted(list(result.lint) + extra + walk)


def summary_line(diags: list[Diagnostic]) -> str:
    counts = {s: sum(1 for d in diags if d.severity == s) for s in ("error", "warning", "info")}
    return f"{counts['error']} errors, {counts['warning']} warnings, {counts['info']} infos"


def by_node(result: ScanResult, diags: list[Diagnostic]) -> tuple[dict[str, list[Diagnostic]], list[Diagnostic]]:
    """Diagnostics about a node's identity, per id, plus the superseded-file block: the hygiene report of `loom lint --nodes`."""
    slugs = result.assembly.citeslugs
    per: dict[str, list[Diagnostic]] = {}
    for d in diags:
        if d.code not in NODE_CODES:
            continue
        for k in d.keys:
            stmt = k.split("/", 1)[0]
            if is_id_shaped(stmt, slugs):
                per.setdefault(stmt, []).append(d)
    superseded = [d for d in diags if d.code == "loom:superseded-file"]
    return dict(sorted(per.items())), superseded


@click.command(name="lint")
@click.option("--json", "as_json", is_flag=True)
@click.option(
    "--nodes",
    "nodes",
    is_flag=True,
    help="One block per node id: what is wrong with its identity, and the superseded files.",
)
@click.option(
    "--session", "run_dir", default=None, metavar="SESSION", envvar="LOOM_SESSION", help="Log this call to the session."
)
@quilt_option
def lint_command(as_json: bool, nodes: bool, run_dir: str | None, quilt_path: str | None) -> None:
    """Scan and print every diagnostic. Fast; no LaTeX runs."""
    result = open_scan(quilt_path)
    log_run(run_dir, "loom lint", result.quilt.root)
    diags = all_diagnostics(result)
    if nodes:
        per, superseded = by_node(result, diags)
        bad = any(d.severity == "error" for ds in per.values() for d in ds)
        groups = [Group(k, [diag_item(d) for d in ds], problem=True, limit=None) for k, ds in per.items()]
        if superseded:
            groups.append(Group("superseded files", [diag_item(d) for d in superseded], limit=None))
        verdict = (
            f"{counted(len(per), 'node')} with a fault in its identity"
            + (f"; {counted(len(superseded), 'superseded file')}" if superseded else "")
            if per or superseded
            else "every node is defined once; no file is superseded"
        )
        Report(
            verdict,
            ok=not bad,
            exit=EXIT_CONTENT if bad else 0,
            groups=groups,
            data={
                "nodes": {k: [d.to_dict() for d in ds] for k, ds in per.items()},
                "superseded": [d.to_dict() for d in superseded],
            },
        ).emit(as_json)
        return
    bad = has_errors(diags, result)
    Report(
        tally(diags, result),
        ok=not bad,
        exit=EXIT_CONTENT if bad else 0,
        groups=diagnostic_groups(diags, result),
        data={"diagnostics": [d.to_dict() for d in diags]},
    ).emit(as_json)
