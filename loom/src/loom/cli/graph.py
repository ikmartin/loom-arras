"""`loom deps` and `loom unravel` (book 12.4)."""

from __future__ import annotations

from typing import Any

import click

from loom.cli._common import emit_json
from loom.cli._quilt import describe, open_scan, quilt_option, resolve_key
from loom.cli.build_cmds import log_run
from loom.scan.scan import ScanResult


def _edge_entries(result: ScanResult, key: str, kind: str) -> list[dict[str, str]]:
    """One entry per dependency target; `via` lists every mechanism that established it, comma-joined."""
    assert result.graph is not None
    order: list[str] = []
    vias: dict[str, list[str]] = {}
    kinds: dict[str, str] = {}
    for e in result.graph.out.get(key, []):
        if e.kind != kind and e.via != "nested":
            continue
        target = result.graph.statement_key(e.to)
        if target not in vias:
            order.append(target)
            vias[target] = []
            kinds[target] = e.kind
        if e.via not in vias[target]:
            vias[target].append(e.via)
    return [{"key": t, "via": ",".join(vias[t]), "kind": kinds[t]} for t in order]


def deps_payload(result: ScanResult, key: str) -> dict[str, Any]:
    assert result.graph is not None
    n = result.assembly.nodes[key]
    statement = (
        _edge_entries(result, key, "statement")
        if n.kind != "proof"
        else _edge_entries(result, n.of or key, "statement")
    )
    proof: list[dict[str, str]] = []
    if n.kind == "proof":
        proof = _edge_entries(result, key, "proof")
    else:
        for pk in n.proofs:
            proof.extend(_edge_entries(result, pk, "proof"))
    closure = result.graph.closure(key)
    return {"key": key, "statement": statement, "proof": proof, "closure": [{"key": k} for k in closure]}


@click.command()
@click.argument("key")
@click.option("--closure", "show_closure", is_flag=True, help="The transitive statement closure in dependency order.")
@click.option("--json", "as_json", is_flag=True)
@click.option("--run", "run_dir", default=None, envvar="LOOM_RUN", metavar="DIR", help="Log this call to DIR/run.log.")
@quilt_option
def deps(key: str, show_closure: bool, as_json: bool, run_dir: str | None, quilt_path: str | None) -> None:
    """What KEY depends on: direct statement-edges and proof-edges, grouped."""
    log_run(run_dir, f"loom deps {key}")
    result = open_scan(quilt_path)
    key = resolve_key(result, key)
    payload = deps_payload(result, key)
    if as_json:
        emit_json(payload)
        return
    click.echo(describe(result, key))
    if show_closure:
        click.echo("closure (dependencies first):")
        for entry in payload["closure"]:
            click.echo(f"  {describe(result, entry['key'])}")
        return
    for label, entries in (("statement", payload["statement"]), ("proof", payload["proof"])):
        click.echo(f"{label}-edges:")
        for entry in entries:
            click.echo(f"  {describe(result, entry['key'])}  via {entry['via']}")
        if not entries:
            click.echo("  (none)")


def unravel_payload(result: ScanResult, key: str) -> dict[str, Any]:
    assert result.graph is not None
    n = result.assembly.nodes[key]
    dependents = []
    for dk in result.graph.downstream(key):
        via = next(
            (
                e.via
                for e in result.graph.out.get(dk, [])
                if result.graph.statement_key(e.to) == key or e.to in n.proofs or e.to == key
            ),
            "transitive",
        )
        dependents.append(
            {
                "key": dk,
                "via": via,
                "kind": result.assembly.nodes[dk].kind if dk in result.assembly.nodes else "unknown",
            }
        )
    targets = {key, *n.proofs}
    references = [
        {"file": e.file, "line": e.line, "key": e.src, "label": e.label}
        for e in result.edges.edges
        if e.to in targets or result.graph.statement_key(e.to) == key
    ]
    inclusions = [
        {"file": inc.parent, "line": result.files[inc.parent].line_of(inc.site_start), "master": m}
        for m, exp in result.expansions.items()
        for inc in exp.inclusions
        if inc.child == n.file
    ]
    return {
        "id": key,
        "dependents": dependents,
        "references": references,
        "inclusions": inclusions,
        "ledger": [],
        "annotations": [],
    }


@click.command()
@click.argument("id_", metavar="ID")
@click.option("--json", "as_json", is_flag=True)
@click.option("--run", "run_dir", default=None, envvar="LOOM_RUN", metavar="DIR", help="Log this call to DIR/run.log.")
@quilt_option
def unravel(id_: str, as_json: bool, run_dir: str | None, quilt_path: str | None) -> None:
    """Everything downstream of ID: dependents, reference and inclusion sites, ledger rows, annotations. Reports; changes nothing."""
    log_run(run_dir, f"loom unravel {id_}")
    result = open_scan(quilt_path)
    key = resolve_key(result, id_)
    payload = unravel_payload(result, key)
    if as_json:
        emit_json(payload)
        return
    click.echo(f"{describe(result, key)}: nothing is changed by this report")
    for section in ("dependents", "references", "inclusions", "ledger", "annotations"):
        items = payload[section]
        click.echo(f"{section}:")
        for item in items:
            if section == "dependents":
                click.echo(f"  {describe(result, item['key'])}  via {item['via']}")
            elif section == "references":
                click.echo(f"  {item['file']}:{item['line']}  in {item['key']}")
            elif section == "inclusions":
                click.echo(f"  {item['file']}:{item['line']}  ({item['master']})")
            else:
                click.echo(f"  {item}")
        if not items:
            click.echo("  (none)")
