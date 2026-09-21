"""`loom accept`, `loom comment`, `loom status` (book 7.3, 7.4.3, 7.7, 12.6)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError, emit_json, find_run
from loom.cli._quilt import describe, open_quilt, open_scan, quilt_option, require_text, resolve_key
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


@click.command(name="review")
@quilt_option
def review_command(quilt_path: str | None) -> None:
    """Observe current review causes and publish the review panel without accepting any key."""
    from loom.render.build import build

    report = build(open_quilt(quilt_path))
    stale = sum(1 for key in report.manifest["keys"].values() if key.get("acceptance", {}).get("fresh") is False)
    click.echo(f"review updated: {stale} stale key{'s' if stale != 1 else ''}; build/manifest.json published")


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


def write_acceptance(result: ScanResult, keys: list[str], author: str) -> tuple[list[AcceptRow], int, int]:
    """Record acceptance rows and the snapshots they name; returns (rows, snapshots written, snapshots already present).

    The one writer of the ledger, shared by `loom accept` and `loom refs verify`. They make different claims -- the author's own mathematics against a faithful copy of someone else's -- but the record is the same shape, and a second implementation would drift in exactly the way that makes `stale` stop meaning anything.
    """
    root = result.quilt.root
    rows: list[AcceptRow] = []
    written = present = 0
    master = result.default_master or (result.masters[0] if result.masters else "")
    closure_obj = result.closures.get(master)
    pre_text = closure_obj.raw_text() if closure_obj else ""
    hist = result.quilt.history_dir
    pre_hash, w = write_snapshot(root, pre_text, hist)
    written += w
    present += not w
    for key in keys:
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
                key=key,
                author=author,
                date=stamp(),
                text=text_hash,
                preamble=pre_hash,
                master=master,
                closure=closure,
                basis=result.nodes[key].basis if result.nodes[key].kind == "environment" else "",
                direct={dep: closure[dep] for dep in Records.direct_keys(result, key) if dep in closure},
            )
        )
    append_rows(root, rows)
    return rows, written, present


@click.command()
@click.argument("keys", nargs=-1)
@click.option("--proofs", is_flag=True, help="Also accept every proof attached to each statement given.")
@click.option(
    "--stale",
    "accept_stale",
    is_flag=True,
    help="Accept every key that is currently accepted-stale, after confirmation.",
)
@click.option(
    "--all-live", is_flag=True, help="Accept every live author-owned statement and proof, after confirmation."
)
@click.option("--author", default=None)
@click.option("--force", is_flag=True, help="Accept even when the master does not compile.")
@click.option("--yes", "-y", is_flag=True)
@quilt_option
def accept(
    keys: tuple[str, ...],
    proofs: bool,
    accept_stale: bool,
    all_live: bool,
    author: str | None,
    force: bool,
    yes: bool,
    quilt_path: str | None,
) -> None:
    """Record acceptance rows and snapshots for KEYS; the only writer of the ledger."""
    from loom.cli._common import refuse_under_agent

    refuse_under_agent("loom accept", "Accepting is you saying the mathematics holds; run it in your own terminal.")
    if all_live and (keys or proofs or accept_stale):
        raise EnvError("--all-live cannot be combined with keys, --proofs, or --stale")
    result = open_scan(quilt_path)
    root = result.quilt.root
    name = _author(author, root)
    records = Records(root, result.quilt.history_dir)
    targets: list[str] = []
    if all_live:
        conflicts = sorted(k for k, n in result.nodes.items() if n.kind == "conflict" and n.reached_by)
        if conflicts:
            raise ContentError(f"live conflicted keys prevent --all-live: {', '.join(conflicts)}")
        targets = sorted(
            k for k, n in result.nodes.items() if n.kind in ("environment", "proof") and n.reached_by and not n.external
        )
        if not targets:
            click.echo("no live author-owned statements or proofs to accept")
            return
        incomplete = [k for k in targets if result.nodes[k].incomplete]
        if incomplete:
            raise ContentError(f"live incomplete keys prevent --all-live: {', '.join(incomplete)}")
        unclassified = [
            k for k in targets if result.nodes[k].kind == "environment" and result.nodes[k].basis == "unclassified"
        ]
        if unclassified:
            raise ContentError(f"live unclassified keys prevent --all-live: {', '.join(unclassified)}")
        open_claims = [
            k for k in targets if result.nodes[k].kind == "environment" and result.nodes[k].basis == "open-claim"
        ]
        if open_claims:
            raise ContentError(f"open claims cannot be accepted as established: {', '.join(open_claims)}")
        statements = sum(result.nodes[k].kind == "environment" for k in targets)
        click.echo(f"--all-live selects {statements} statements and {len(targets) - statements} proofs")
        if not yes:
            if not sys.stdin.isatty():
                raise EnvError("--all-live needs confirmation; pass --yes")
            click.confirm(
                f"accept these {len(targets)} keys as mathematically correct in their current dependency contexts?",
                abort=True,
            )
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
        # Two claims, two commands. `loom accept` says "I have proved this, or I am satisfied it holds" and is about
        # the author's own mathematics; a digest node's is "this copy is faithful to the paper it came from", which
        # settles nothing mathematical and is not the author's to settle. DR-172 relabelled the output where the
        # command needed splitting, and this finishes it (plan 0.12 §5.6).
        if n.external:
            if n.digest:
                raise EnvError(
                    f"{key} is a digest node: someone else's theorem, which is not yours to accept.\n"
                    f"To record that the copy is faithful: loom refs verify {key}"
                )
            raise EnvError(
                f"{key} quotes someone else's result, which is not yours to accept. "
                "To verify its transcription, represent it as a digest result and use loom refs verify there."
            )
        targets.append(key)
        if proofs:
            targets.extend(n.proofs)
    if not targets:
        raise EnvError("give at least one KEY, --stale, or --all-live")
    for key in targets:
        if result.nodes[key].incomplete:
            raise ContentError(f"{key} contains \\incomplete; remove the mark before accepting")
        if result.nodes[key].kind == "environment" and result.nodes[key].basis == "open-claim":
            raise ContentError(f"{key} is an open claim and cannot be accepted as established")
    if not force:
        ok, err = _master_compiles(result)
        if not ok:
            raise ContentError(f"the default master does not compile ({err}); fix it or pass --force")
    rows, written, present = write_acceptance(result, targets, name)
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
    undo: bool = False,
) -> str:
    """Append one review event to the log and describe it; the only writer of review records."""
    root = result.quilt.root
    records = Records(root, result.quilt.history_dir).records
    date = today()
    run, akind, aid = writer
    base = {"when": stamp(), "author": aid, "kind": "agent" if akind == "run" else "human", "run": run}

    if resolve:
        found = find_annotation(records, resolve)
        if found is None:
            raise ContentError(f"no annotation {resolve}")
        _, parent = found
        event: dict[str, Any] = {**base, "event": "resolved", "id": resolve, "body": message or ""}
        if undo:
            event["undo"] = True
        append(root, event)
        return f"{'reopened' if undo else 'resolved'} {resolve}"

    if reply:
        if not (message or "").strip():
            raise EnvError("a reply with no message says nothing; give the text as the argument after the id")
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
    if severity is not None and kind == "ok":
        raise EnvError("--severity grades a fault and --kind ok names none; drop one of them")
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


def discard_annotation(
    root: Path, ann_id: str, writer: tuple[str | None, str, str], reason: str | None, undo: bool = False
) -> str:
    """Withdraw one finding: it was raised in error and should not stand; with `undo`, put it back.

    Distinct from resolving, which says the author addressed it, and from `loom ai discard`, which sets a whole run aside. Nothing is deleted, so the finding and its reason stay in the log, and an undo is another event rather than the removal of one.
    """
    records = Records(root).records
    if find_annotation(records, ann_id) is None:
        raise ContentError(f"no annotation {ann_id}")
    run, akind, aid = writer
    event: dict[str, Any] = {
        "event": "discarded",
        "id": ann_id,
        "when": stamp(),
        "author": aid,
        "kind": "agent" if akind == "run" else "human",
        "run": run,
        "body": reason or "",
    }
    if undo:
        event["undo"] = True
    append(root, event)
    return f"{'reopened' if undo else 'discarded'} {ann_id}"


def check_edit(body: str | None, severity: str | None, payload: str | None) -> None:
    """An edit must change something, and an edit to an empty body says nothing -- `--discard` is how a finding is withdrawn."""
    if body is not None and not body.strip():
        raise EnvError("an edit to an empty body says nothing; give the new text, or withdraw it with --discard")
    if body is None and severity is None and payload is None:
        raise EnvError("--edit with nothing to change; give a new body, --severity or --payload")


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


BATCH_KEYS = (
    "target",
    "message",
    "quote",
    "kind",
    "reply",
    "resolve",
    "edit",
    "discard",
    "severity",
    "payload",
    "placement",
)
BATCH_VERBS = ("reply", "resolve", "edit", "discard")


def _batch_line(result: ScanResult, writer: tuple[str | None, str, str], item: dict[str, Any]) -> str:
    """One line of `--batch`: a new annotation, or one change to an existing one, named by exactly one verb.

    An unknown key is refused rather than ignored. A batch is written by a program that cannot see the result, so a misspelled `messsage` that silently files an empty annotation is a fault the writer never learns about — and every verb `loom comment` has on the command line is available here, so there is no reason to fall back to one call per change.
    """
    unknown = sorted(set(item) - set(BATCH_KEYS))
    if unknown:
        raise EnvError(f"unknown key(s) {', '.join(unknown)}; accepted: {', '.join(BATCH_KEYS)}")
    verbs = [v for v in BATCH_VERBS if item.get(v)]
    if len(verbs) > 1:
        raise EnvError(f"one verb per line; this one gives {' and '.join(verbs)}")
    root = result.quilt.root
    if item.get("discard"):
        return discard_annotation(root, str(item["discard"]), writer, item.get("message"))
    if item.get("edit"):
        check_edit(item.get("message"), item.get("severity"), item.get("payload"))
        return edit_annotation(
            root,
            str(item["edit"]),
            writer,
            body=item.get("message"),
            severity=item.get("severity"),
            payload=item.get("payload"),
        )
    return _one_comment(
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
    "--discard",
    "discard_id",
    default=None,
    metavar="ID",
    help="Withdraw a finding you should not have raised; resolving would claim the author addressed it.",
)
@click.option(
    "--severity", type=click.Choice(list(SEVERITIES)), default=None, help="How bad the fault is, not how keen you are."
)
@click.option("--payload", default=None, help="Suggested text the author may preview and copy.")
@click.option(
    "--placement", type=click.Choice(list(PLACEMENTS)), default=None, help="Where the payload goes, as a hint."
)
@click.option(
    "--undo",
    is_flag=True,
    help="With --resolve or --discard, put the finding back: an undo is another event, never a removal.",
)
@click.option(
    "--batch",
    is_flag=True,
    help="Read JSON lines from stdin, one annotation or one change per line; an unknown key is an error.",
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
    discard_id: str | None,
    severity: str | None,
    payload: str | None,
    placement: str | None,
    undo: bool,
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
                click.echo(_batch_line(result, writer, item))
            except (ContentError, EnvError) as exc:
                raise ContentError(f"batch line {lineno}: {exc.message}") from exc
        return
    # Each of these names its annotation by id and takes no TARGET (7.4), so the one positional given is the body.
    # `--edit` and `--discard` did this; `--reply` and `--resolve` read it as a target and filed an empty body.
    if (reply or resolve or edit or discard_id) and message is None:
        message, target = target, None
    if undo and not (discard_id or resolve):
        raise EnvError("--undo applies to --resolve or --discard")
    if discard_id:
        click.echo(discard_annotation(root, discard_id, writer, message, undo))
        return
    if edit:
        check_edit(message, severity, payload)
        click.echo(edit_annotation(root, edit, writer, body=message, severity=severity, payload=payload))
        return
    click.echo(
        _one_comment(result, writer, target, message, quote, kind, reply, resolve, severity, payload, placement, undo)
    )


def status_payload(result: ScanResult, records: Records) -> dict[str, Any]:
    states = records.key_states(result)
    derived = records.derived(result, states)
    keys: dict[str, Any] = {}
    assert result.graph is not None
    live: dict[str, list[dict[str, Any]]] = {}
    for res in records.resolved(result):
        if res.record.discarded:
            continue
        a = res.annotation
        live.setdefault(a.target_key, []).append(
            {"id": a.id, "kind": a.kind, "severity": a.severity, "status": a.status, "detached": res.detached}
        )
    for key, ks in states.items():
        n = result.nodes[key]
        if n.kind == "section" and not live.get(key):
            continue  # a section is a row only when it carries a finding; otherwise it is structure, not work
        entry: dict[str, Any] = {
            "key": key,
            "node": n.of if n.kind == "proof" and n.of else key,
            "kind": n.kind if n.kind == "section" else ("proof" if n.kind == "proof" else "statement"),
            "taxon": n.taxon or "",
            "title": n.title or "",
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
                "annotations": live.get(key, []),
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
    undigested = sorted(
        {
            c.citekey
            for c in result.edges.cites
            if c.postnote and c.citekey not in digested and c.file not in result.assembly.digest_files
        }
    )
    retired = sorted(k for k in records.latest if k not in result.nodes and k not in result.assembly.labels)
    return {
        "summary": summarise(result, keys),
        "keys": keys,
        "runs": runs,
        "undigested": undigested,
        "retired": retired,
    }


STATUSES = ("open", "resolved")


def summarise(result: ScanResult, rows: dict[str, Any]) -> dict[str, int]:
    """The counting line, over the author's own keys among the rows it is printed under.

    A filtered list is summarised by what it holds, not by the quilt, and external keys are never in the arithmetic: a digest's results are permanently draft, permanently loose, and settled as a dependency, so counting them answers this line's questions about somebody else's paper (DR-172).
    """
    rows = {k: e for k, e in rows.items() if not result.nodes[k].external}
    acc = [e for e in rows.values() if e.get("acceptance")]
    return {
        "keys": len(rows),
        "accepted": sum(1 for e in acc if e["acceptance"]["fresh"]),
        "stale": sum(1 for e in acc if not e["acceptance"]["fresh"]),
        "draft": sum(1 for e in rows.values() if e["state"] == "draft"),
        "incomplete": sum(1 for e in rows.values() if e["state"] == "incomplete"),
        "loose": sum(1 for k in rows if not result.nodes[k].reached_by),
        "proved": sum(1 for e in rows.values() if e.get("derived", {}).get("proved")),
        "settled": sum(1 for e in rows.values() if e.get("derived", {}).get("settled")),
    }


def state_label(result: ScanResult, key: str, state: str) -> str:
    """What a state is called for this key: accepting an external node claims its transcription is faithful, not that the author settled the theorem (DR-172)."""
    n = result.nodes.get(key)
    if n is None or not n.external or not state.startswith("accepted"):
        return state
    return state.replace("accepted", "transcription verified", 1)  # keeps a trailing ", stale"


def reached_external(result: ScanResult, rows: dict[str, Any]) -> set[str]:
    """Which external keys the corpus actually leans on: one is reached when something the author wrote depends on it, transitively.

    Mirrors arras's `reached.ts`, which the review panel has used since 0.9. Digesting one paper wholesale brings in a hundred external nodes of which two or three carry weight, and reachedness is the difference; depth is the wrong test, since a cited result you lean on needs checking whoever cited it and one you never use needs nothing.
    """
    external = {k for k, n in result.nodes.items() if n.external}
    out: set[str] = set()
    for key, e in rows.items():
        if key in external:
            continue  # only what the corpus itself wrote reaches
        for dep in e.get("closure", []):
            if dep not in external:
                continue
            out.add(dep)
            for inner in rows.get(dep, {}).get("closure", []):
                if inner in external:
                    out.add(inner)
    return out


def filter_keys(
    result: ScanResult,
    rows: dict[str, Any],
    *,
    stale: bool = False,
    draft: bool = False,
    incomplete: bool = False,
    loose: bool = False,
    master: str | None = None,
    tag: str | None = None,
    severity: str | None = None,
    kind: str | None = None,
    status: str | None = None,
    detached: bool = False,
    hide: set[str] | None = None,
) -> dict[str, Any]:
    """Every row filter `loom status` offers, in one place, so the text form and `--json` answer the same question.

    The annotation filters keep a key when any live annotation on it matches; `detached` is the same test on `reviews.detached`.
    """
    out: dict[str, Any] = {}
    for key, e in rows.items():
        if hide and key in hide:
            continue
        n = result.nodes[key]
        anns = e["reviews"]["annotations"]
        if stale and not (e.get("acceptance") and not e["acceptance"]["fresh"]):
            continue
        if draft and e["state"] != "draft":
            continue
        if incomplete and e["state"] != "incomplete":
            continue
        if loose and n.reached_by:
            continue
        if master and master not in n.reached_by:
            continue
        if tag and tag not in (n.directives.get("tags", "").replace(" ", "").split(",")):
            continue
        if severity and not any(a["severity"] == severity for a in anns):
            continue
        if kind and not any(a["kind"] == kind for a in anns):
            continue
        if status and not any(a["status"] == status for a in anns):
            continue
        if detached and not e["reviews"]["detached"]:
            continue
        out[key] = e
    return out


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
@click.option(
    "--severity",
    "f_severity",
    type=click.Choice(SEVERITIES),
    default=None,
    help="Keys carrying an annotation of this severity.",
)
@click.option("--kind", "f_kind", default=None, help="Keys carrying an annotation of this kind.")
@click.option(
    "--status",
    "f_status",
    type=click.Choice(list(STATUSES)),
    default=None,
    help="Keys carrying an annotation in this state.",
)
@click.option("--detached", "f_detached", is_flag=True, help="Keys whose annotations no longer find their quoted text.")
@click.option(
    "--include-digests",
    "f_digests",
    is_flag=True,
    help="Also list the digest keys nothing in this quilt depends on; they are left out by default.",
)
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
    f_severity: str | None,
    f_kind: str | None,
    f_status: str | None,
    f_detached: bool,
    f_digests: bool,
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
    # A digest holds every result of a cited paper; the handful the author's own arguments reach are work, and the
    # rest are the literature. Reachedness is the line arras's review panel has drawn since 0.9 (DR-172).
    reached = reached_external(result, payload["keys"])
    external = {k for k in payload["keys"] if result.nodes[k].external}
    hidden = set() if f_digests else external - reached
    payload["digests"] = {
        "shown": len(external - hidden),
        "reached": len(external & reached),
        "not_counted": len(hidden),
    }
    payload["keys"] = filter_keys(
        result,
        payload["keys"],
        hide=hidden,
        stale=f_stale,
        draft=f_draft,
        incomplete=f_incomplete,
        loose=f_loose,
        master=f_master,
        tag=f_tag,
        severity=f_severity,
        kind=f_kind,
        status=f_status,
        detached=f_detached,
    )
    payload["summary"] = summarise(result, payload["keys"])
    if as_json:
        emit_json(payload)
        return
    if explain:
        key = resolve_key(result, explain)
        states = records.key_states(result)
        ks = states.get(key)
        if ks is None:
            raise EnvError(f"{key} is not a statement, proof or section key")
        section = result.nodes[key].kind == "section"
        click.echo(f"{describe(result, key)}  {state_label(result, key, ks.label)}".rstrip())
        click.echo(f"  in {result.nodes[key].file}")
        if section:
            click.echo("  a section: it carries findings and takes no acceptance")
        elif not ks.causes:
            click.echo("  no causes: the acceptance is fresh" if ks.row else "  never accepted")
        e = payload["keys"].get(key) or {"reviews": {"open": dict(ks.open), "detached": ks.detached}}
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
    for key, e in payload["keys"].items():
        state = state_label(result, key, e["state"]) + (
            ", stale" if e.get("acceptance") and not e["acceptance"]["fresh"] else ""
        )
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
        click.echo(f"{describe(result, key):<40} {e['title'][:38]:<40} {state:<18} {cause:<40} {'; '.join(facts)}{inc}")
    s = payload["summary"]
    d = payload["digests"]
    line = f"{s['stale']} stale of {s['accepted'] + s['stale']} accepted; {s['draft']} draft; {s['incomplete']} incomplete; {s['loose']} loose; {s['proved']} proved, {s['settled']} settled"
    if f_digests and d["shown"]:
        line += f" · {d['shown']} digest keys shown"
    elif d["reached"]:
        line += f" · {d['reached']} digest keys you depend on"
    if d["not_counted"]:
        line += f" · {d['not_counted']} digest keys not counted"
    click.echo(line)
