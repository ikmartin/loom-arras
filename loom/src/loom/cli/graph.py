"""`loom deps` and `loom downstream` (book 12.4)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

import click

from loom.cli._quilt import open_scan, quilt_option, resolve_key
from loom.cli.build_cmds import log_run
from loom.cli.report import WIDTH, Group, Item, Report, counted, table
from loom.scan.scan import ScanResult


def natural(text: str) -> tuple[Any, ...]:
    """A sort key that orders the numbers inside `text` by value, so `rem-2.4` comes before `rem-2.10`."""
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.split(r"(\d+)", text) if p)


def when(stamp: str) -> str:
    """An ISO timestamp as a reader takes it in: `2026-09-16 14:03`, the date always."""
    return stamp[:16].replace("T", " ") if len(stamp) > 10 else stamp


def taxon(result: ScanResult, key: str) -> str:
    """What `key` is (`Lemma`, `Proof`), or '' for a path or a key the assembly does not hold."""
    n = result.assembly.nodes.get(key)
    if n is None or n.kind in ("master", "file"):
        return ""
    return n.taxon or n.kind


def keyed(rows: Sequence[tuple[tuple[str, ...], str]]) -> list[Item]:
    """Items whose text columns are aligned across `rows` and whose key goes last, each row `(columns, key)`.

    The keys line up in one column as far as the lines that fit within the width reach; a longer line keeps its key at its end and wraps.
    """
    lines = [ln.rstrip() for ln in table([(*cols, "") for cols, _ in rows])] if rows else []
    fits = [len(ln) for ln, (_, key) in zip(lines, rows, strict=True) if 2 + len(ln) + 2 + len(key) <= WIDTH]
    width = max(fits, default=0)
    return [
        Item(ln.ljust(width) if 2 + width + 2 + len(key) <= WIDTH else ln, key=key)
        for ln, (_, key) in zip(lines, rows, strict=True)
    ]


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
    return {
        "key": key,
        "statement": statement,
        "proof": proof,
        "closure": [{"key": k} for k in closure],
        "relations": _relation_entries(result, key),
    }


def _proof_closure(result: ScanResult, key: str, closure: list[dict[str, str]]) -> list[str]:
    """What the closures of a statement's proofs add to its own, in dependency order: with it, what `loom source KEY --closure` prints (`tex.bundle.build_bundle`).

    `deps --closure` stays the statement closure, which is what the statement's meaning rests on; a proof's citations are what checking it needs, so they are listed apart rather than folded in. Empty for a proof key, whose closure already holds them.
    """
    assert result.graph is not None
    n = result.assembly.nodes[key]
    if n.kind == "proof":
        return []
    have = {e["key"] for e in closure} | {key}
    out: list[str] = []
    for pk in n.proofs:
        for k in result.graph.closure(pk):
            if k not in have and k not in out:
                out.append(k)
    return out


def _relation_entries(result: ScanResult, key: str) -> list[dict[str, str]]:
    """Both directions of every declared relation of `key`, in target order. These are not dependencies and are reported apart from them."""
    node = result.assembly.nodes[key]
    mine = {key, node.of} if node.kind == "proof" else {key, *node.proofs}
    out: dict[str, str] = {}
    for r in result.relations:
        if r.from_key in mine and r.to_key not in mine:
            out.setdefault(r.to_key, r.kind)
        elif r.to_key in mine and r.from_key not in mine:
            out.setdefault(r.from_key, r.kind)
    return [{"key": k, "kind": out[k]} for k in sorted(out)]


@click.command()
@click.argument("key")
@click.option("--closure", "show_closure", is_flag=True, help="The transitive statement closure in dependency order.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@click.option(
    "--session", "run_dir", default=None, metavar="SESSION", envvar="LOOM_SESSION", help="Log this call to the session."
)
@quilt_option
def deps(key: str, show_closure: bool, as_json: bool, run_dir: str | None, quilt_path: str | None) -> None:
    """Show what KEY depends on: direct statement-edges and proof-edges, grouped."""
    result = open_scan(quilt_path)
    asked = key
    key = resolve_key(result, key)
    log_run(run_dir, f"loom deps {asked}", result.quilt.root)
    payload = deps_payload(result, key)
    if show_closure:
        rest = [e["key"] for e in payload["closure"] if e["key"] != key]
        added = _proof_closure(result, key, payload["closure"])
        payload["proof_closure"] = [{"key": k} for k in added]
        verdict = (
            f"{key} depends on {counted(len(rest), 'statement')}, transitively"
            if rest
            else f"{key}'s statement depends on no other statement"
            if added
            else f"{key} depends on nothing"
        )
        if added:
            verdict += f"; its proof adds {len(added)}, which loom source {key} --closure prints with it"
        groups = [
            Group("closure, dependencies first", keyed([((taxon(result, k),), k) for k in rest]), limit=None),
            Group(
                "added by its proof, not part of the statement's closure",
                keyed([((taxon(result, k),), k) for k in added]),
                limit=None,
            ),
        ]
        Report(verdict, groups=[g for g in groups if g.items], data=payload).emit(as_json)
        return
    groups = []
    for heading, entries in (("through its statement", payload["statement"]), ("through its proof", payload["proof"])):
        rows = [
            ((taxon(result, e["key"]), f"via {e['via']}"), e["key"])
            for e in sorted(entries, key=lambda e: natural(e["key"]))
        ]
        groups.append(Group(heading, keyed(rows), limit=None))
    if payload["relations"]:
        rows = [((taxon(result, e["key"]), e["kind"]), e["key"]) for e in payload["relations"]]
        groups.append(Group("see also, not a dependency", keyed(rows), limit=None))
    s, p = len(payload["statement"]), len(payload["proof"])
    verdict = (
        f"{key} depends directly on {counted(s + p, 'result')}: {s} through its statement, {p} through its proof"
        if s + p
        else f"{key} depends on nothing"
    )
    Report(verdict, groups=[g for g in groups if g.items], data=payload).emit(as_json)


def _downstream_records(result: ScanResult, key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The acceptance rows and the live annotations on `key` and its proofs, for `downstream`'s last two blocks.

    Withdrawn annotations are left out: `downstream` reports what a change to this key would disturb, and a withdrawn finding disturbs nothing.
    """
    from loom.records.store import Records

    records = Records(result.quilt.root, result.quilt.history_dir)
    targets = {key, *result.assembly.nodes[key].proofs}
    ledger = [
        {"key": r.key, "author": r.author, "date": r.date, "master": r.master} for r in records.rows if r.key in targets
    ]
    annotations = [
        {
            "id": a.id,
            "target": a.target_key,
            "kind": a.kind,
            "severity": a.severity,
            "status": a.status,
            "author": a.author_id,
            "created": a.created,
            "quote": a.selector.exact if a.selector else None,
            "message": a.body,
            "detached": res.detached,
            "recorded": res.recorded,
        }
        for res in records.resolved(result)
        for a in [res.annotation]
        if a.target_key in targets and not res.record.discarded
    ]
    return ledger, annotations


def downstream_payload(result: ScanResult, key: str) -> dict[str, Any]:
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
    ledger, annotations = _downstream_records(result, key)
    return {
        "id": key,
        "dependents": dependents,
        "references": references,
        "inclusions": inclusions,
        "ledger": ledger,
        "annotations": annotations,
    }


@click.command(name="downstream")
@click.argument("id_", metavar="ID")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@click.option(
    "--session", "run_dir", default=None, metavar="SESSION", envvar="LOOM_SESSION", help="Log this call to the session."
)
@quilt_option
def downstream(id_: str, as_json: bool, run_dir: str | None, quilt_path: str | None) -> None:
    """Show everything downstream of ID: dependents, reference and inclusion sites, ledger rows, annotations. Reports; changes nothing."""
    result = open_scan(quilt_path)
    key = resolve_key(result, id_)
    log_run(run_dir, f"loom downstream {id_}", result.quilt.root)
    payload = downstream_payload(result, key)
    dependents = sorted(payload["dependents"], key=lambda e: natural(e["key"]))
    references = sorted(payload["references"], key=lambda e: (natural(e["file"]), e["line"]))
    inclusions = sorted(payload["inclusions"], key=lambda e: (natural(e["file"]), e["line"]))
    ledger = sorted(payload["ledger"], key=lambda e: (natural(e["key"]), e["date"]))
    annotations = sorted(payload["annotations"], key=lambda e: natural(e["id"]))
    groups = [
        Group("dependents", keyed([((taxon(result, e["key"]), f"via {e['via']}"), e["key"]) for e in dependents])),
        Group("references", keyed([((f"{e['file']}:{e['line']}", "in"), e["key"]) for e in references])),
        Group("inclusions", keyed([((f"{e['file']}:{e['line']}", "in"), e["master"]) for e in inclusions])),
        Group(
            "acceptances",
            keyed([((when(e["date"]), e["author"], f"against {e['master']}"), e["key"]) for e in ledger]),
        ),
        Group("annotations", [_annotation_item(e) for e in annotations]),
    ]
    parts = [counted(len(g.items), g.heading.rstrip("s"), g.heading) for g in groups if g.items]
    verdict = f"changing {key} would reach " + (", ".join(parts) if parts else "nothing else") + "; nothing was changed"
    Report(verdict, groups=[g for g in groups if g.items], data=payload).emit(as_json)


def _annotation_item(e: dict[str, Any]) -> Item:
    """One annotation on the key or its proofs: its kind, grade and state, then the first line of what it says, its id last."""
    sev = f" {e['severity']}" if e["severity"] else ""
    mark = "" if e["status"] == "open" else f", {e['status']}"
    loose = ", detached" if e["detached"] else ""
    head = f"{e['kind']}{sev}{mark}{loose} on {e['target']}"
    first = (e["message"] or "").strip().splitlines()
    room = WIDTH - 6 - len(head) - len(e["id"])
    said = (
        f": {first[0] if len(first[0]) <= room else first[0][: max(room - 1, 0)] + '…'}" if first and room > 8 else ""
    )
    return Item(head + said, key=e["id"])
