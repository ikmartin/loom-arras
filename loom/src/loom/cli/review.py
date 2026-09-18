"""`loom accept`, `loom comment`, `loom status` (book 7.3, 7.4.3, 7.7, 12.6)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError, emit_json, find_run
from loom.cli._quilt import describe, open_scan, quilt_option, require_text, resolve_key
from loom.cli.build_cmds import engine_for, log_run
from loom.clock import stamp, today
from loom.records.annotations import (
    KINDS,
    PLACEMENTS,
    SEVERITIES,
    find_annotation,
    next_id,
)
from loom.records.ledger import AcceptRow, append_rows
from loom.records.log import append
from loom.records.selectors import find_quote, make_selector
from loom.records.snapshots import write_snapshot
from loom.records.store import Records
from loom.render.manifest import key_hash, own_text
from loom.scan.quilt import NoAuthorError, resolve_author
from loom.scan.scan import ScanResult
from loom.tex.runner import compile_tex


def _author(explicit: str | None, root: Path) -> str:
    try:
        return resolve_author(explicit, root)[0]
    except NoAuthorError as exc:
        raise EnvError(str(exc)) from exc


def _master_compiles(result: ScanResult) -> tuple[bool, str]:
    master = result.default_master
    if master is None:
        return True, ""
    root = result.quilt.root
    pdf = root / "build" / Path(master).stem / f"{Path(master).stem}.pdf"
    newest = max((result.files[f].abspath.stat().st_mtime for f in result.files), default=0.0)
    if pdf.exists() and pdf.stat().st_mtime >= newest:
        return True, ""
    res = compile_tex(root, master, root / "build" / Path(master).stem, engine_for(result, master))
    return res.ok, res.first_error


@click.command()
@click.argument("keys", nargs=-1)
@click.option("--proofs", is_flag=True, help="Also accept every proof attached to each statement given.")
@click.option(
    "--stale",
    "accept_stale",
    is_flag=True,
    help="Accept every key that is currently accepted-stale, after confirmation.",
)
@click.option("--author", default=None)
@click.option("--force", is_flag=True, help="Accept even when the master does not compile.")
@click.option("--yes", "-y", is_flag=True)
@quilt_option
def accept(
    keys: tuple[str, ...],
    proofs: bool,
    accept_stale: bool,
    author: str | None,
    force: bool,
    yes: bool,
    quilt_path: str | None,
) -> None:
    """Record acceptance rows and snapshots for KEYS; the only writer of the ledger."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    name = _author(author, root)
    records = Records(root)
    targets: list[str] = []
    if accept_stale:
        states = records.key_states(result)
        stale = sorted(k for k, s in states.items() if s.state == "accepted" and not s.fresh)
        if not stale:
            click.echo("nothing is stale")
            return
        for k in stale:
            click.echo(
                f"  {describe(result, k)}  {', '.join(c.kind + (' ' + c.id if c.id else '') for c in states[k].causes)}"
            )
        if not yes:
            if not sys.stdin.isatty():
                raise EnvError("--stale needs confirmation; pass --yes")
            click.confirm(f"accept these {len(stale)} stale keys?", abort=True)
        targets = stale
    for k in keys:
        key = resolve_key(result, k)
        require_text(result, key)
        n = result.nodes[key]
        if n.kind not in ("environment", "proof"):
            raise EnvError(f"{key} is not a statement or proof key")
        targets.append(key)
        if proofs:
            targets.extend(n.proofs)
    if not targets:
        raise EnvError("give at least one KEY, or --stale")
    for key in targets:
        if result.nodes[key].incomplete:
            raise ContentError(f"{key} contains \\incomplete; remove the mark before accepting")
    if not force:
        ok, err = _master_compiles(result)
        if not ok:
            raise ContentError(f"the default master does not compile ({err}); fix it or pass --force")
    rows: list[AcceptRow] = []
    written = present = 0
    master = result.default_master or (result.masters[0] if result.masters else "")
    closure_obj = result.closures.get(master)
    pre_text = closure_obj.raw_text() if closure_obj else ""
    hist = result.quilt.history_dir
    pre_hash, w = write_snapshot(root, pre_text, hist)
    written += w
    present += not w
    for key in targets:
        text_hash, w = write_snapshot(root, own_text(result, result.nodes[key]), hist)
        written += w
        present += not w
        closure: dict[str, str] = {}
        for dep, h in Records.closure_hashes(result, key).items():
            closure[dep] = h
            _, w2 = write_snapshot(root, own_text(result, result.nodes[dep]), hist)
            written += w2
            present += not w2
        assert text_hash == key_hash(result, key)
        rows.append(
            AcceptRow(
                key=key, author=name, date=stamp(), text=text_hash, preamble=pre_hash, master=master, closure=closure
            )
        )
    append_rows(root, rows)
    for row in rows:
        click.echo(f"accepted {describe(result, row.key):<40} by {row.author}  {row.date[:10]}")
    click.echo(f"snapshots: {written} written, {present} already present")


def _target_text(result: ScanResult, target: str) -> tuple[str, str]:
    """(canonical key, own text) for a key, a region key, or a master path."""
    key = resolve_key(result, target)
    region = result.assembly.regions.get(key)
    node_key = region.container if region else key
    require_text(result, node_key)
    n = result.nodes[node_key]
    text, _ = Records.own_pieces(result, n)
    return key, text


def _writer(root: Path, run_dir: str | None, author: str | None) -> tuple[str | None, str, str]:
    """(run, author kind, author id) for whoever is writing: a run writes as itself, a person as their name."""
    if run_dir:
        rp = find_run(root, run_dir)
        rel = rp.relative_to(root).as_posix() if rp.is_relative_to(root) else rp.name
        return rel, "run", rp.name
    name = _author(author, root)
    return None, "person", name


def _one_comment(
    result: ScanResult,
    writer: tuple[str | None, str, str],
    target: str | None,
    message: str | None,
    quote: str | None,
    kind: str | None,
    reply: str | None,
    resolve: str | None,
    severity: str | None = None,
    payload: str | None = None,
    placement: str | None = None,
) -> str:
    """Append one review event to the log and describe it; the only writer of review records."""
    root = result.quilt.root
    records = Records(root).records
    date = today()
    run, akind, aid = writer
    base = {"when": stamp(), "author": aid, "kind": "agent" if akind == "run" else "human", "run": run}

    if resolve:
        found = find_annotation(records, resolve)
        if found is None:
            raise ContentError(f"no annotation {resolve}")
        _, parent = found
        append(root, {**base, "event": "resolved", "id": resolve, "body": message or ""})
        return f"resolved {resolve}"

    if reply:
        found = find_annotation(records, reply)
        if found is None:
            raise ContentError(f"no annotation {reply}")
        _, parent = found
        ann_id = next_id(records, date)
        append(
            root,
            {
                **base,
                "event": "replied",
                "id": ann_id,
                "target": parent.target_key,
                "against": parent.target_hash,
                "anchor": parent.selector.to_dict() if parent.selector else None,
                "annotation_kind": kind or "question",
                "body": message or "",
                "reply_to": reply,
            },
        )
        return f"{ann_id}  {parent.target_key}  reply to {reply}  ({aid})"

    if not target:
        raise EnvError("TARGET is required")
    key, text = _target_text(result, target)
    node_key = result.assembly.regions[key].container if key in result.assembly.regions else key
    selector = None
    if quote:
        spans = find_quote(text, quote)
        if not spans:
            raise ContentError(f"quote not found in {key}")
        if len(spans) > 1:
            raise ContentError(f"quote is ambiguous ({len(spans)} occurrences); give a longer quote")
        selector = make_selector(text, quote)
    if kind is None:
        kind = "ok" if not message else "objection"
    if kind not in KINDS:
        raise EnvError(f"kind must be one of {', '.join(KINDS)}")
    if severity is not None and severity not in SEVERITIES:
        raise EnvError(f"severity must be one of {', '.join(SEVERITIES)}")
    if placement is not None and placement not in PLACEMENTS:
        raise EnvError(f"placement must be one of {', '.join(PLACEMENTS)}")
    if placement and not payload:
        raise EnvError("--placement says where a payload goes; give --payload too")
    ann_id = next_id(records, date)
    append(
        root,
        {
            **base,
            "event": "created",
            "id": ann_id,
            "target": key,
            "against": key_hash(result, node_key),
            "anchor": selector.to_dict() if selector else None,
            "annotation_kind": kind,
            "body": message or "",
            "severity": severity,
            "payload": payload,
            "placement": placement,
        },
    )
    sev = f" {severity}" if severity else ""
    return f"{ann_id}  {key}  {kind}{sev}  ({aid}{' run' if akind == 'run' else ''})"


def edit_annotation(root: Path, ann_id: str, writer: tuple[str | None, str, str], **fields: str | None) -> str:
    """Supersede an annotation's body or payload; the history stays in the log and one current body is shown.

    This is what a re-check does to a finding that still stands. A reply is dialogue; an edit is restatement.
    """
    records = Records(root).records
    if find_annotation(records, ann_id) is None:
        raise ContentError(f"no annotation {ann_id}")
    run, akind, aid = writer
    event = {"event": "edited", "id": ann_id, "when": stamp(), "author": aid, "run": run}
    event["kind"] = "agent" if akind == "run" else "human"
    append(root, {**event, **{k: v for k, v in fields.items() if v is not None}})
    return f"edited {ann_id}"


@click.command()
@click.argument("target", required=False, default=None)
@click.argument("message", required=False, default=None)
@click.option(
    "--quote", default=None, help="Anchor to this exact text, which must occur once in the target's own text."
)
@click.option("--kind", type=click.Choice(list(KINDS)), default=None)
@click.option(
    "--run",
    "run_dir",
    default=None,
    envvar="LOOM_RUN",
    help="Write as this run: a name, a prefix of one, or a path. The run is the author.",
)
@click.option("--author", default=None)
@click.option("--reply", default=None, metavar="ID")
@click.option("--resolve", default=None, metavar="ID")
@click.option(
    "--edit", default=None, metavar="ID", help="Supersede an annotation's body; the history stays in the log."
)
@click.option(
    "--severity", type=click.Choice(list(SEVERITIES)), default=None, help="How bad the fault is, not how keen you are."
)
@click.option("--payload", default=None, help="Suggested text the author may preview and copy.")
@click.option(
    "--placement", type=click.Choice(list(PLACEMENTS)), default=None, help="Where the payload goes, as a hint."
)
@click.option(
    "--batch",
    is_flag=True,
    help="Read JSON lines from stdin: {target, message, quote, kind, reply, resolve, severity, payload, placement}.",
)
@quilt_option
def comment(
    target: str | None,
    message: str | None,
    quote: str | None,
    kind: str | None,
    run_dir: str | None,
    author: str | None,
    reply: str | None,
    resolve: str | None,
    edit: str | None,
    severity: str | None,
    payload: str | None,
    placement: str | None,
    batch: bool,
    quilt_path: str | None,
) -> None:
    """Write an annotation on TARGET (a key, an equation's qualified key, or a master path); the only writer of review records."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    if run_dir and author:
        raise EnvError("give --run or --author, not both")
    writer = _writer(root, run_dir, author)
    log_run(
        run_dir,
        "loom comment "
        + " ".join(x for x in [target, "--quote" if quote else "", "--kind " + kind if kind else ""] if x),
        root,
    )
    if batch:
        for lineno, line in enumerate(sys.stdin, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ContentError(f"batch line {lineno}: {exc}") from exc
            try:
                click.echo(
                    _one_comment(
                        result,
                        writer,
                        item.get("target"),
                        item.get("message"),
                        item.get("quote"),
                        item.get("kind"),
                        item.get("reply"),
                        item.get("resolve"),
                        item.get("severity"),
                        item.get("payload"),
                        item.get("placement"),
                    )
                )
            except (ContentError, EnvError) as exc:
                raise ContentError(f"batch line {lineno}: {exc.message}") from exc
        return
    if edit:
        # `loom comment --edit ID "the new body"` takes no target, so the one positional given is the body
        body = message if message is not None else target
        click.echo(edit_annotation(root, edit, writer, body=body, severity=severity, payload=payload))
        return
    click.echo(_one_comment(result, writer, target, message, quote, kind, reply, resolve, severity, payload, placement))


def status_payload(result: ScanResult, records: Records) -> dict[str, Any]:
    states = records.key_states(result)
    derived = records.derived(result, states)
    keys: dict[str, Any] = {}
    assert result.graph is not None
    for key, ks in states.items():
        n = result.nodes[key]
        entry: dict[str, Any] = {
            "key": key,
            "node": n.of if n.kind == "proof" and n.of else key,
            "kind": "proof" if n.kind == "proof" else "statement",
            "state": ks.state,
            "incomplete": list(n.incomplete),
            "reached_by": list(n.reached_by),
            "reviews": {
                "latest_current": {
                    "author": {"kind": ks.latest_current.author_kind, "id": ks.latest_current.author_id},
                    "date": ks.latest_current.created,
                }
                if ks.latest_current
                else None,
                "latest_any": {
                    "author": {"kind": ks.latest_any.author_kind, "id": ks.latest_any.author_id},
                    "date": ks.latest_any.created,
                }
                if ks.latest_any
                else None,
                "open": dict(ks.open),
                "detached": ks.detached,
            },
            "previous_key_match": ks.previous_key_match,
            "closure": result.graph.closure(key),
        }
        if ks.row is not None:
            entry["acceptance"] = {
                "author": ks.row.author,
                "date": ks.row.date,
                "fresh": ks.fresh,
                "causes": [c.to_dict() for c in ks.causes],
            }
        if key in derived:
            entry["derived"] = derived[key]
        keys[key] = entry
    summary = {
        "keys": len(keys),
        "accepted": sum(1 for s in states.values() if s.state == "accepted" and s.fresh),
        "stale": sum(1 for s in states.values() if s.state == "accepted" and not s.fresh),
        "draft": sum(1 for s in states.values() if s.state == "draft"),
        "incomplete": sum(1 for s in states.values() if s.state == "incomplete"),
        "loose": sum(1 for k in states if not result.nodes[k].reached_by),
        "proved": sum(1 for d in derived.values() if d["proved"]),
        "settled": sum(1 for d in derived.values() if d["settled"]),
    }
    runs = [
        {
            "path": r.rel,
            "discarded": r.discarded,
            "annotations": len(r.annotations),
            "kind": "run" if r.is_run else "comments",
        }
        for r in records.records
    ]
    digested = set(result.assembly.digest_files.values())
    undigested = sorted({c.citekey for c in result.edges.cites if c.postnote and c.citekey not in digested})
    retired = sorted(k for k in records.latest if k not in result.nodes and k not in result.assembly.labels)
    return {"summary": summary, "keys": keys, "runs": runs, "undigested": undigested, "retired": retired}


@click.command()
@click.option("--stale", "f_stale", is_flag=True)
@click.option("--draft", "f_draft", is_flag=True)
@click.option("--incomplete", "f_incomplete", is_flag=True)
@click.option("--loose", "f_loose", is_flag=True)
@click.option("--unmatched-cites", "f_unmatched", is_flag=True)
@click.option("--undigested", "f_undigested", is_flag=True)
@click.option("--retired", "f_retired", is_flag=True)
@click.option("--runs", "f_runs", is_flag=True)
@click.option("--master", "f_master", default=None)
@click.option("--tag", "f_tag", default=None)
@click.option("--explain", default=None, metavar="KEY")
@click.option("--json", "as_json", is_flag=True)
@click.option("--run", "run_dir", default=None, envvar="LOOM_RUN")
@quilt_option
def status(
    f_stale: bool,
    f_draft: bool,
    f_incomplete: bool,
    f_loose: bool,
    f_unmatched: bool,
    f_undigested: bool,
    f_retired: bool,
    f_runs: bool,
    f_master: str | None,
    f_tag: str | None,
    explain: str | None,
    as_json: bool,
    run_dir: str | None,
    quilt_path: str | None,
) -> None:
    """Every key with its computed state, cause if stale, and review facts. Never exits nonzero."""
    result = open_scan(quilt_path)
    records = Records(result.quilt.root)
    log_run(run_dir, "loom status", result.quilt.root)
    payload = status_payload(result, records)
    if as_json:
        emit_json(payload)
        return
    if explain:
        key = resolve_key(result, explain)
        states = records.key_states(result)
        ks = states.get(key)
        if ks is None:
            raise EnvError(f"{key} is not a statement or proof key")
        click.echo(f"{describe(result, key)}  {ks.label}")
        click.echo(f"  in {result.nodes[key].file}")
        if not ks.causes:
            click.echo("  no causes: the acceptance is fresh" if ks.row else "  never accepted")
        e = payload["keys"][key]
        opened = {k: v for k, v in e["reviews"]["open"].items() if v}
        if opened:
            click.echo("  " + ", ".join(f"{v} open {k}{'s' if v != 1 else ''}" for k, v in opened.items()))
        if e["reviews"]["detached"]:
            click.echo(f"  {e['reviews']['detached']} detached annotation(s): the quoted text is gone")
        for c in ks.causes:
            click.echo(f"  {c.kind}{' ' + c.id if c.id else ''}{' (' + c.when + ')' if c.when else ''}")
            diff = records.diff_for(result, c, key)
            if diff:
                click.echo("".join("    " + line for line in diff.splitlines(keepends=True)), nl=False)
        return
    if f_undigested:
        for ck in payload["undigested"]:
            click.echo(ck)
        return
    if f_retired:
        for k in payload["retired"]:
            click.echo(f"{k}  (ledger rows remain; last accepted {records.latest[k].date[:10]})")
        return
    if f_runs:
        for r in payload["runs"]:
            click.echo(
                f"{r['path']}  {r['kind']}  {r['annotations']} annotation(s){'  discarded' if r['discarded'] else ''}"
            )
        return
    if f_unmatched:
        digested = set(result.assembly.digest_files.values())
        for cite in result.edges.cites:
            if (
                cite.postnote
                and cite.citekey in digested
                and not any(
                    e.via == "postnote" and e.src == cite.src and e.label == f"{cite.citekey}|{cite.postnote}"
                    for e in result.edges.edges
                )
            ):
                click.echo(
                    f"{cite.file}:{cite.line}  \\cite[{cite.postnote}]{{{cite.citekey}}}  no digest node matches"
                )
        return
    rows = payload["keys"]
    for key, e in rows.items():
        n = result.nodes[key]
        if f_stale and not (e.get("acceptance") and not e["acceptance"]["fresh"]):
            continue
        if f_draft and e["state"] != "draft":
            continue
        if f_incomplete and e["state"] != "incomplete":
            continue
        if f_loose and n.reached_by:
            continue
        if f_master and f_master not in n.reached_by:
            continue
        if f_tag and f_tag not in (n.directives.get("tags", "").replace(" ", "").split(",")):
            continue
        state = e["state"] + (", stale" if e.get("acceptance") and not e["acceptance"]["fresh"] else "")
        cause = ""
        if e.get("acceptance") and e["acceptance"]["causes"]:
            cause = "; ".join(
                c["kind"] + (" " + c["id"] if c.get("id") else "") + (f" ({c['when']})" if c.get("when") else "")
                for c in e["acceptance"]["causes"]
            )
        facts = []
        opened = {k: v for k, v in e["reviews"]["open"].items() if v}
        if opened:
            facts.append(", ".join(f"{v} open {k}{'s' if v != 1 else ''}" for k, v in opened.items()))
        elif e["reviews"]["latest_current"]:
            facts.append(
                f"reviewed clean ({e['reviews']['latest_current']['author']['id']}, {e['reviews']['latest_current']['date'][:10]})"
            )
        if e["reviews"]["detached"]:
            facts.append(f"{e['reviews']['detached']} detached")
        if e.get("previous_key_match"):
            facts.append(f"acceptance recorded under {e['previous_key_match']}; re-accept to confirm")
        inc = f"  incomplete: {'; '.join(e['incomplete'])}" if e["incomplete"] else ""
        click.echo(f"{describe(result, key):<40} {state:<18} {cause:<40} {'; '.join(facts)}{inc}")
    s = payload["summary"]
    click.echo(
        f"{s['stale']} stale of {s['accepted'] + s['stale']} accepted; {s['draft']} draft; {s['incomplete']} incomplete; {s['loose']} loose; {s['proved']} proved, {s['settled']} settled"
    )
