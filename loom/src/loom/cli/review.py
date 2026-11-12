"""`loom accept`, `loom annotate`, `loom status`."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError, NotFoundError, from_stdin
from loom.cli._quilt import describe, open_scan, quilt_option, require_text, resolve_key
from loom.cli.build_cmds import engine_for, log_run
from loom.cli.graph import keyed, natural, when
from loom.cli.report import Group, Item, Progress, Report, counted
from loom.clock import stamp, today
from loom.paths import document_build
from loom.records.annotations import (
    find_annotation,
    next_id,
)
from loom.records.ids import ANNOTATION
from loom.records.ledger import AcceptRow, append_rows
from loom.records.log import append, append_new
from loom.records.marks import MARKS
from loom.records.selectors import find_quote, make_selector
from loom.records.snapshots import snapshots_dir, write_snapshot
from loom.records.store import Records
from loom.records.types import COLORS, STYLES, WEIGHTS, drawn_look, load_types, look_problem, type_named
from loom.render.fragments import plain_title
from loom.render.manifest import key_hash, own_text
from loom.scan.hashing import normalize, sha256
from loom.scan.quilt import NoAuthorError, resolve_author
from loom.scan.scan import ScanResult
from loom.tex.runner import compile_document


def _author(explicit: str | None, root: Path) -> str:
    try:
        return resolve_author(explicit, root)[0]
    except NoAuthorError as exc:
        raise EnvError(str(exc)) from exc


def _master_compiles(result: ScanResult, master: str | None = None) -> tuple[bool, str]:
    master = master or result.default_master
    if master is None:
        return True, ""
    root = result.quilt.root
    pdf = root / document_build(master) / f"{Path(master).stem}.pdf"
    newest = max((result.files[f].abspath.stat().st_mtime for f in result.files), default=0.0)
    if pdf.exists() and pdf.stat().st_mtime >= newest:
        return True, ""
    res = compile_document(
        root, result.base_of(master), master, root / document_build(master), engine_for(result, master)
    )
    return res.ok, res.first_error


def _acceptance_master(result: ScanResult, key: str) -> str:
    """Choose a deterministic document context for an acceptance not explicitly scoped to one master: never an agent's document, which nothing is accepted in."""
    reached = [m for m in result.nodes[key].reached_by if result.document_role(m) == "person"]
    if result.default_master and result.default_master in reached:
        return result.default_master
    if reached:
        return str(reached[0])
    own = [m for m in result.masters if result.document_role(m) == "person"]
    return result.default_master or (own[0] if own else "")


def _owned(result: ScanResult, key: str) -> bool:
    """A key the person's own documents reach, and not an agent document's derived key: what `--all-live` and `--master` may accept."""
    n = result.nodes[key]
    return not n.derived_of and any(result.document_role(m) == "person" for m in n.reached_by)


def _snapshot(root: Path, text: str, hist: Path, dry_run: bool) -> tuple[str, bool]:
    """`write_snapshot`, or with `dry_run` only its hash and whether it would be written."""
    if not dry_run:
        return write_snapshot(root, text, hist)
    digest = sha256(normalize(text))
    return digest, not (snapshots_dir(root, hist) / f"{digest.split(':', 1)[1]}.tex").exists()


def write_acceptance(
    result: ScanResult,
    keys: list[str],
    author: str,
    masters: dict[str, str] | None = None,
    *,
    dry_run: bool = False,
) -> tuple[list[AcceptRow], int, int]:
    """Record acceptance rows and the snapshots they name; returns (rows, snapshots written, snapshots already present).

    The one writer of the ledger, shared by `loom accept` and `loom library verify`. They make different claims -- the author's own mathematics against a faithful copy of someone else's -- but the record is the same shape, and a second implementation would drift in exactly the way that makes `stale` stop meaning anything. With `dry_run` the rows are computed and nothing is written.
    """
    root = result.quilt.root
    rows: list[AcceptRow] = []
    written = present = 0
    hist = result.quilt.history_dir
    preambles: dict[str, str] = {}
    fallback = result.default_master or (result.masters[0] if result.masters else "")
    chosen = {key: (masters or {}).get(key, fallback) for key in keys}
    for key, master in chosen.items():
        if master and master not in result.closures:
            # a row's preamble is its document's; a path that is not a live document has none, and an empty one would read as a change for ever
            raise ContentError(f"{master} is not a live document of yours; {key} cannot be accepted against it")
    for key in keys:
        unavailable = [d for d in result.dependencies.closure(key) if result.dependencies.texts.get(d) is None]
        if unavailable:
            raise ContentError("Cannot identify the full equation: " + ", ".join(unavailable))
    for key in keys:
        master = chosen[key]
        if master not in preambles:
            closure_obj = result.closures.get(master)
            pre_text = closure_obj.raw_text() if closure_obj else ""
            preambles[master], w = _snapshot(root, pre_text, hist, dry_run)
            written += w
            present += not w
        text_hash, w = _snapshot(root, own_text(result, result.nodes[key]), hist, dry_run)
        written += w
        present += not w
        closure: dict[str, str] = {}
        for dep, h in Records.closure_hashes(result, key).items():
            closure[dep] = h
            _, w2 = _snapshot(root, result.dependencies.texts[dep], hist, dry_run)
            written += w2
            present += not w2
        assert text_hash == key_hash(result, key)
        rows.append(
            AcceptRow(
                key=key,
                author=author,
                date=stamp(),
                text=text_hash,
                preamble=preambles[master],
                master=master,
                closure=closure,
                basis=result.nodes[key].basis if result.nodes[key].kind == "environment" else "",
                dependency_version=1,
                direct={dep: closure[dep] for dep in Records.direct_keys(result, key) if dep in closure},
            )
        )
    if not dry_run:
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
@click.option("--master", "accept_master", default=None, help="Accept every statement and proof reached by MASTER.")
@click.option("--as", "author", default=None, metavar="NAME", help="Who accepts; default your configured name.")
@click.option(
    "--force", is_flag=True, help="Accept even when the document the acceptance is recorded against does not compile."
)
@click.option("--yes", "-y", is_flag=True, help="Accept --stale, --all-live or --master without asking.")
@click.option("--dry-run", is_flag=True, help="Say what would be accepted, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def accept(
    keys: tuple[str, ...],
    proofs: bool,
    accept_stale: bool,
    all_live: bool,
    accept_master: str | None,
    author: str | None,
    force: bool,
    yes: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Record that you accept KEYS as mathematically correct, each against the document it is read in."""
    from loom.cli._common import refuse_under_agent

    refuse_under_agent(
        "loom accept", "Accepting is you saying the mathematics holds; run it in your own terminal.", author
    )
    if all_live and (keys or proofs or accept_stale or accept_master):
        raise EnvError("--all-live cannot be combined with keys, --proofs, --stale, or --master")
    if accept_master and (keys or proofs or accept_stale):
        raise EnvError("--master cannot be combined with keys, --proofs, or --stale")
    result = open_scan(quilt_path)
    root = result.quilt.root
    name = _author(author, root)
    records = Records(root, result.quilt.history_dir, reviewer=name)
    targets: list[str] = []
    contexts: dict[str, str] = {}
    if all_live or accept_master:
        if accept_master and result.document_role(accept_master) != "person":
            raise EnvError(
                f"{accept_master} is not a live document of yours"
                + (": nothing in an agent's document is accepted" if result.document_role(accept_master) else "")
            )
        conflicts = sorted(
            k
            for k, n in result.nodes.items()
            if n.kind == "conflict" and (accept_master in n.reached_by if accept_master else _owned(result, k))
        )
        scope = f"--master {accept_master}" if accept_master else "--all-live"
        if conflicts:
            raise ContentError(f"live conflicted keys prevent {scope}: {', '.join(conflicts)}")
        targets = sorted(
            k
            for k, n in result.nodes.items()
            if n.kind in ("environment", "proof")
            and (accept_master in n.reached_by if accept_master else _owned(result, k))
            and not n.derived_of
            and not n.external
        )
        if not targets:
            Report(
                "nothing to accept: no statement or proof of yours is in scope",
                dry_run=dry_run,
                data=_accepted([], 0, 0),
            ).emit(as_json)
            return
        incomplete = [k for k in targets if result.nodes[k].incomplete]
        unclassified = [
            k for k in targets if result.nodes[k].kind == "environment" and result.nodes[k].basis == "unclassified"
        ]
        open_claims = [
            k for k in targets if result.nodes[k].kind == "environment" and result.nodes[k].basis == "open-claim"
        ]
        blocked = [
            f"{said}: {', '.join(ks)}"
            for said, ks in (
                (f"live incomplete keys prevent {scope}", incomplete),
                (f"live unclassified keys prevent {scope}", unclassified),
                ("open claims cannot be accepted as established", open_claims),
            )
            if ks
        ]
        if blocked:
            # the rest can still be accepted, by key (T3)
            rest = [k for k in targets if k not in {*incomplete, *unclassified, *open_claims}]
            raise ContentError(
                "; ".join(blocked) + (f". Accept the rest by key: loom accept {' '.join(rest)}" if rest else "")
            )
        statements = sum(result.nodes[k].kind == "environment" for k in targets)
        label = f"--master {accept_master}" if accept_master else "--all-live"
        if not yes and not dry_run:
            if not sys.stdin.isatty():
                raise EnvError(f"{label} needs confirmation; pass --yes")
            click.echo(f"{label} selects {statements} statements and {len(targets) - statements} proofs", err=True)
            click.confirm(
                f"accept these {len(targets)} keys as mathematically correct in their current dependency contexts?",
                abort=True,
            )
        contexts = {key: accept_master or _acceptance_master(result, key) for key in targets}
    if accept_stale:
        states = records.key_states(result)
        stale = sorted(k for k, s in states.items() if s.state == "accepted" and not s.fresh)
        if not stale:
            Report("nothing is stale; nothing accepted", dry_run=dry_run, data=_accepted([], 0, 0)).emit(as_json)
            return
        if not yes and not dry_run:
            if not sys.stdin.isatty():
                raise EnvError("--stale needs confirmation; pass --yes")
            for k in stale:
                causes = ", ".join(c.kind + (" " + c.id if c.id else "") for c in states[k].causes)
                click.echo(f"  {describe(result, k)}  {causes}", err=True)
            click.confirm(f"accept these {len(stale)} stale keys?", abort=True)
        targets = stale
        # each row's own document, where the history's moves have taken it; a document that is gone is never written against again
        contexts = {
            key: (Records.row_document(result, records.latest[key]) if key in records.latest else None)
            or _acceptance_master(result, key)
            for key in targets
        }
    for k in keys:
        key = resolve_key(result, k)
        require_text(result, key)
        n = result.nodes[key]
        if n.kind not in ("environment", "proof"):
            raise EnvError(f"{key} is not a statement or proof key")
        if n.derived_of:
            raise EnvError(
                f"{key} is an agent document's node, which is never accepted; acceptance belongs to the node it becomes, {n.derived_of}"
            )
        # Two claims, two commands. `loom accept` says "I have proved this, or I am satisfied it holds" and is about
        # the author's own mathematics; a digest node's is "this copy is faithful to the paper it came from", which
        # settles nothing mathematical and is not the author's to settle. DR-172 relabelled the output where the
        # command needed splitting, and this finishes it (plan 0.12 §5.6).
        if n.external:
            if n.digest:
                raise EnvError(
                    f"{key} is a digest node: someone else's theorem, which is not yours to accept.\n"
                    f"To record that the copy is faithful: loom library verify {key}"
                )
            raise EnvError(
                f"{key} quotes someone else's result, which is not yours to accept. "
                "To verify its transcription, represent it as a digest result and use loom library verify there."
            )
        targets.append(key)
        contexts[key] = _acceptance_master(result, key)
        if proofs:
            targets.extend(n.proofs)
            contexts.update({proof: contexts[key] for proof in n.proofs})
    if not targets:
        raise EnvError("give at least one KEY, --stale, --all-live, or --master")
    for key in targets:
        if result.nodes[key].incomplete:
            raise ContentError(f"{key} contains \\incomplete; remove the mark before accepting")
        if result.nodes[key].kind == "environment" and result.nodes[key].basis == "open-claim":
            raise ContentError(f"{key} is an open claim and cannot be accepted as established")
    # a key whose own latest row is fresh and of its text now, against the same document, is accepted already: a second row would say nothing new (T7)
    states = records.key_states(result)
    already = [
        k
        for k in targets
        if (st := states.get(k)) is not None
        and st.state == "accepted"
        and st.fresh
        and st.row is not None
        and st.row.author == name
        and st.row.master == contexts.get(k)
        and st.row.text == key_hash(result, k)
    ]
    targets = [k for k in targets if k not in already]
    if not targets:
        Report(
            f"already accepted as {name}: {', '.join(already)}; nothing written",
            dry_run=dry_run,
            data={**_accepted([], 0, 0), "already": already},
        ).emit(as_json)
        return
    # each document a row is recorded against must compile, unless --force: the rows hash the source either way, so the compile is a check on the claim, not part of what is recorded
    documents = list(dict.fromkeys(contexts[key] for key in targets if contexts.get(key)))
    uncompiled, documents = (documents, []) if force else ([], documents)
    with Progress("compiling", len(documents)) as p:
        for master in documents:
            p.item(master)
            ok, err = _master_compiles(result, master)
            if not ok:
                raise ContentError(f"{master} does not compile ({err}); fix it or pass --force")
    rows, written, present = write_acceptance(result, targets, name, contexts, dry_run=dry_run)
    said = [r.key for r in rows]
    verb = "would accept" if dry_run else "accepted"
    if len(said) <= 3 and not (all_live or accept_master or accept_stale):
        verdict = f"{verb} " + (", ".join(said[:-1]) + " and " + said[-1] if len(said) > 1 else said[0])
    else:
        statements = sum(result.nodes[r.key].kind == "environment" for r in rows)
        verdict = f"{verb} {counted(statements, 'statement')} and {counted(len(rows) - statements, 'proof')}"
    items = keyed(
        [
            ((result.nodes[r.key].taxon or result.nodes[r.key].kind, f"against {r.master}" if r.master else ""), r.key)
            for r in sorted(rows, key=lambda r: natural(r.key))
        ]
    )
    Report(
        f"{verdict} as {name}"
        + (f", without compiling {', '.join(uncompiled)}, as --force asks" if uncompiled else "")
        + (f"; {counted(len(already), 'key')} already accepted" if already else "")
        + ("; nothing written" if dry_run else ""),
        dry_run=dry_run,
        groups=[Group(verb, items, next="loom status" if len(items) > 12 else None)],
        data={**_accepted(rows, written, present), "already": already},
    ).emit(as_json)


def _accepted(rows: list[AcceptRow], written: int, present: int) -> dict[str, Any]:
    """`loom accept --json`'s data: each row recorded, and the snapshots it wrote."""
    return {
        "accepted": [{"key": r.key, "author": r.author, "date": r.date, "master": r.master} for r in rows],
        "snapshots": {"written": written, "present": present},
    }


def _target_text(result: ScanResult, target: str) -> tuple[str, str]:
    """(canonical key, own text) for a key, a region key, or a master path."""
    key = resolve_key(result, target)
    region = result.assembly.regions.get(key)
    node_key = region.container if region else key
    require_text(result, node_key)
    n = result.nodes[node_key]
    text, _ = Records.own_pieces(result, n)
    return key, text


def _annotator(root: Path, author: str | None, *, sniff: bool = True) -> tuple[str, str]:
    """(author kind, author name) for whoever writes an annotation: a person by their name, an agent by what it is called, never by the author's git identity that its shell happens to share (DR-185).

    A declared name decides the kind by what it calls itself; an agent's shell must declare a name that says so (`signed`), and anybody with no name to use is refused. `sniff=False` is the API's: a write over HTTP is somebody at a browser, and the shell `loom serve` was started in says nothing about them.
    """
    from loom.cli._common import is_agent, signed

    declared = signed(author) if sniff else (author or "").strip()
    name = declared or _author(author, root)
    return ("agent" if is_agent(declared) else "human"), name


def _version(result: ScanResult, key: str, *, dry_run: bool = False) -> str | None:
    """The hash of `key`'s current text, frozen so a note written against it can always be shown; None for what is not a key (a work's page).

    Freezing at write time closes the gap the build's own freezing leaves: a version written against and changed again before the next build was lost. Snapshots are stored by hash, so a version many notes share is kept once.
    """
    node_key = result.assembly.regions[key].container if key in result.assembly.regions else key
    node = result.nodes.get(node_key)
    if node is None:
        return None
    digest, _ = _snapshot(result.quilt.root, own_text(result, node), result.quilt.history_dir, dry_run)
    return digest


def _append(root: Path, event: dict[str, Any], dry_run: bool) -> None:
    """`records.log.append`, unless this is a dry run."""
    if not dry_run:
        append(root, event)


def _append_new(root: Path, event: dict[str, Any], records: list[Any], date: str, dry_run: bool) -> str:
    """`records.log.append_new`, and the id it drew; a dry run says an id of the kind it would draw and writes nothing."""
    return next_id(records, date) if dry_run else append_new(root, event, date)


def _one_comment(
    result: ScanResult,
    writer: tuple[str, str],
    target: str | None,
    message: str | None,
    quote: str | None,
    type_given: str | None,
    reply: str | None,
    resolve: str | None,
    undo: bool = False,
    page: int | None = None,
    rects: list[list[float]] | None = None,
    in_doc: str | None = None,
    *,
    look: dict[str, Any] | None = None,
    strokes: list[list[float]] | None = None,
    mark: str | None = None,
    dry_run: bool = False,
) -> str:
    """Append one review event to the log and describe it; the only writer of review records.

    The target is a key; a cited work, whole or with `page` one of its pages; or a project PDF with its `page`. Text or a box on a cited work's page is anchored through the work's store (plan 0.13 item 2); anything drawn with a `mark`, or along `strokes`, and anything on a project PDF, records its page, place and the PDF's hash (`records/marks.py`). Everything else about the event is as it is for a key.
    """
    root = result.quilt.root
    records = Records(root, result.quilt.history_dir).records
    date = today()
    akind, aid = writer
    base = {"when": stamp(), "author": aid, "kind": akind}
    # An agent's links are its contract with the viewer: one that names nothing the viewer shows is refused here, with the command that prints a good one. A person's are their own business.
    if message and akind == "agent":
        from loom.links import refuse_bad_links

        refuse_bad_links(result, root, message)

    if reply or resolve:
        refuse_lost(
            "reply" if reply else "resolve",
            reply or resolve,
            {"quote": quote, "type": type_given, **(look or {})},
        )

    if resolve:
        found = find_annotation(records, resolve)
        if found is None:
            raise NotFoundError("annotation", f"no annotation {resolve}")
        _, parent = found
        if not undo and not _opens(root, parent.type):
            raise EnvError(
                f"{resolve} only informs, so there is nothing to resolve: only an annotation whose type stays open until resolved is resolved"
            )
        event: dict[str, Any] = {**base, "event": "resolved", "id": resolve, "body": message or ""}
        if undo:
            event["undo"] = True
        _append(root, event, dry_run)
        return f"{'reopened' if undo else 'resolved'} {resolve}"

    if reply:
        if not (message or "").strip():
            raise EnvError("a reply with no message says nothing; give the text as the argument after the id")
        found = find_annotation(records, reply)
        if found is None:
            raise NotFoundError("annotation", f"no annotation {reply}")
        _, parent = found
        ann_id = _append_new(
            root,
            {
                **base,
                "event": "replied",
                "target": parent.target_key,
                # the text the reply was written against, which may have moved on since the note it answers
                "against": _version(result, parent.target_key, dry_run=dry_run) or parent.target_hash,
                "anchor": parent.selector.to_dict() if parent.selector else None,
                "in": parent.in_doc,
                "body": message or "",
                "reply_to": reply,
            },
            records,
            date,
            dry_run,
        )
        return f"{ann_id}  {parent.target_key}  reply to {reply}  ({aid})"

    if not target:
        raise EnvError("TARGET is required")
    type_id, own, drawn = _type_and_look(root, type_given, look or {})
    if not (message or "").strip() and _opens(root, type_id):
        raise EnvError(NO_MESSAGE)
    styled = {"type": type_id, "look": own, "drawn": drawn}
    from loom.records.marks import project_pdf

    pdf_path = project_pdf(result, target)
    work = None if pdf_path else _work_target(result, target)
    if pdf_path is not None or (work is not None and (mark or strokes)):
        return _on_pdf_page(
            result, base, records, date, target, message, quote, styled, page, rects, strokes, mark, dry_run=dry_run
        )
    if mark or strokes:
        raise EnvError("--mark and --stroke draw on a page of a PDF: a project PDF's path, or a cited work's citekey")
    if work is not None and page is None and not quote and not rects:
        return _on_work(result, base, records, date, work, message, styled, dry_run=dry_run)
    if work is not None or page is not None or rects:
        return _note_on_page(
            result, base, records, date, target, work, message, quote, styled, page, rects, dry_run=dry_run
        )
    key, text = _target_text(result, target)
    node_key = result.assembly.regions[key].container if key in result.assembly.regions else key
    if in_doc is not None:
        # a claim about the node as read in one document (plan 0.15, decision 9): the document must hold the node
        in_doc = in_doc.strip("/")
        if in_doc not in result.masters:
            raise NotFoundError("document", f"{in_doc} is not a document of this quilt; loom status names them")
        if in_doc not in result.nodes[node_key].reached_by:
            raise EnvError(f"{in_doc} does not hold {key}, so nothing about {key} is read there")
    selector = None
    if quote:
        spans = find_quote(text, quote)
        if not spans:
            raise NotFoundError("quote", f"quote not found in {key}; `loom source {key}` prints its text")
        if len(spans) > 1:
            raise EnvError(f"quote is ambiguous ({len(spans)} occurrences); give a longer quote")
        selector = make_selector(text, quote)
    ann_id = _append_new(
        root,
        {
            **base,
            "event": "created",
            "target": key,
            "against": _version(result, key, dry_run=dry_run) or key_hash(result, node_key),
            "anchor": selector.to_dict() if selector else None,
            "in": in_doc,
            **styled,
            "body": message or "",
        },
        records,
        date,
        dry_run,
    )
    return f"{ann_id}  {key}  {type_id or 'untyped'}  ({aid})"


NO_MESSAGE = 'an annotation of a type that stays open until resolved asks something, so it needs words; give them after the target: loom annotate TARGET "…"'


def _opens(root: Path, type_id: str | None) -> bool:
    """Whether an annotation of type `type_id` stays open until resolved; an untyped one, or one whose type is gone, only informs."""
    t = load_types(root).get(type_id)
    return bool(t and t.open)


def _type_and_look(
    root: Path, given: str | None, look: dict[str, Any]
) -> tuple[str | None, dict[str, Any], dict[str, Any]]:
    """(type id, the look set on the annotation, the whole look it is drawn with) for a new one, refused when the type is not the quilt's or the look cannot be drawn."""
    types = load_types(root)
    try:
        t = type_named(types, given)
    except ValueError as exc:
        raise EnvError(str(exc)) from exc
    why = look_problem(look)
    if why:
        raise EnvError(f"--{why}")
    return (t.id if t else None), look, drawn_look(t, look, types.plain)


def _work_target(result: ScanResult, target: str) -> tuple[str, Any] | None:
    """(citekey, WorkId) when `target` names a cited work -- by citekey, or by an identifier any entry states -- else None.

    A key wins over a work: the assembly is asked first, so a citekey that happens to equal a label is still the label. The identifier form is what an agent reading `cited:` links has, and what the record stores.
    """
    from loom.refs.identity import identify, parse, primary

    try:
        resolve_key(result, target)
        return None
    except EnvError:
        pass
    if target in result.bib:
        wid = primary(result.bib[target])
        return (target, wid) if wid is not None else None
    wid = parse(target)
    if wid is None:
        return None
    for ck, entry in result.bib.items():
        if any((w.scheme, w.value) == (wid.scheme, wid.value) for w in identify(entry)):
            return ck, primary(entry) or wid
    return None


def _not_a_work(result: ScanResult, target: str) -> EnvError:
    """The refusal of `--page` on a target that is not a cited work: a key, or nothing at all."""
    try:
        resolve_key(result, target)
    except EnvError:
        return EnvError(
            f"--page is for a page of a PDF, and {target} names none: give a citekey from the bibliography, "
            "an identifier one of its entries states (doi:…, arXiv:…), or a project PDF's path"
        )
    return EnvError(f"--page is for a page of a PDF, and {target} is a key in this quilt")


def _note_on_page(
    result: ScanResult,
    base: dict[str, Any],
    records: list[Any],
    date: str,
    target: str,
    work: tuple[str, Any] | None,
    message: str | None,
    quote: str | None,
    styled: dict[str, Any],
    page: int | None,
    rects: list[list[float]] | None,
    *,
    dry_run: bool = False,
) -> str:
    """An annotation on a page of a cited work, anchored by its words or a box: the same event as any annotation, with the work as its target and a page anchor."""
    from loom.refs.anchoring import anchor_on_page
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map
    from loom.render.serve import open_url

    if work is None:
        raise _not_a_work(result, target)
    citekey, wid = work
    if page is None:
        raise EnvError(f"{citekey} is a cited work: say which page with --page N, and what on it with --quote or --box")
    if not quote and not rects:
        raise EnvError(
            "an annotation on a page needs --quote (text on it) or --box (x0,y0,x1,y1 in points, origin top left)"
        )
    home = work_dir(result.quilt.root, result.bib[citekey])
    if read_map(home) is None or not (home / "paper.pdf").is_file():
        raise ContentError(
            f"{citekey} has no readable copy on this machine; loom library update {citekey} --online fetches one, "
            f"or loom library add FILE --for {citekey} files yours"
        )
    placed = anchor_on_page(home, page, quote, rects)
    if not placed.found:
        raise ContentError(
            f"that text is not on {citekey} p.{page}: quote from `loom library read {citekey} {page}`, or draw a --box"
        )
    # Quads are recorded only for a box, where they are the anchor; for text they are derived at build time from
    # the offsets, as a result's are, so a record never carries two descriptions that could drift apart.
    recorded = placed.anchor.to_dict()
    if placed.anchor.basis == "text":
        recorded.pop("quads", None)
    ann_id = _append_new(
        result.quilt.root,
        {
            **base,
            "event": "created",
            "target": str(wid),
            "against": "sha256:" + placed.anchor.sha256,
            "anchor": {**recorded, **placed.selector.to_dict()},
            **({"gap": placed.gap} if placed.gap is not None else {}),
            **styled,
            "body": message or "",
        },
        records,
        date,
        dry_run,
    )
    said = f"{ann_id}  {citekey} p.{page} ({placed.said})  {styled['type'] or 'untyped'}  ({base['author']})"
    where = open_url(result.quilt.root, f"library/{citekey}?page={page}&annot={ann_id}")
    return said + (f"\nopen: {where}" if where else "")


def _on_work(
    result: ScanResult,
    base: dict[str, Any],
    records: list[Any],
    date: str,
    work: tuple[str, Any],
    message: str | None,
    styled: dict[str, Any],
    *,
    dry_run: bool = False,
) -> str:
    """An annotation on a cited work as a whole: the work's identifier as its target, and no anchor."""
    citekey, wid = work
    ann_id = _append_new(
        result.quilt.root,
        {**base, "event": "created", "target": str(wid), "anchor": None, **styled, "body": message or ""},
        records,
        date,
        dry_run,
    )
    return f"{ann_id}  {citekey}  {styled['type'] or 'untyped'}  ({base['author']})"


def _on_pdf_page(
    result: ScanResult,
    base: dict[str, Any],
    records: list[Any],
    date: str,
    target: str,
    message: str | None,
    quote: str | None,
    styled: dict[str, Any],
    page: int | None,
    rects: list[list[float]] | None,
    strokes: list[list[float]] | None,
    mark: str | None,
    *,
    dry_run: bool = False,
) -> str:
    """An annotation on a page of a project PDF, or one drawn with a tool on a cited work's page: its page, place, strokes, tool and the PDF's hash, with the words it quotes."""
    from loom.records.marks import (
        MarkRefused,
        artifact_of,
        clean_rects,
        clean_strokes,
        pdf_target,
        placed,
        recorded_context,
    )

    on, pdf = pdf_target(result, target)
    if pdf is None:
        raise ContentError(
            f"{target} has no readable copy on this machine; loom library update {target} --online fetches one, "
            f"or loom library add FILE --for {target} files yours"
        )
    try:
        rects = clean_rects(rects)
        strokes = clean_strokes(strokes)
        here = placed(pdf, page, mark, (quote or "").strip() or None, rects, strokes, (message or "").strip())
    except MarkRefused as exc:
        raise (ContentError if exc.code == "not-on-page" else EnvError)(exc.message) from exc
    # the words around it and, for a drawing, its gap from them, by which a changed file places it again
    assert page is not None
    around = recorded_context(result, pdf, page, here, drawn=bool(mark or strokes))
    anchor = around.pop("anchor", None)
    if quote and quote.strip() and not (anchor or {}).get("exact"):
        anchor = {"prefix": "", "suffix": "", **(anchor or {}), "exact": quote.strip()}
    event: dict[str, Any] = {
        **base,
        "event": "created",
        "target": on,
        "page": page,
        "rects": here,
        "artifact": artifact_of(pdf),
        "anchor": anchor,
        **around,
        **styled,
        "body": message or "",
    }
    for k, v in (("strokes", strokes), ("mark", mark)):
        if v:
            event[k] = v
    ann_id = _append_new(result.quilt.root, event, records, date, dry_run)
    what = mark or ("ink" if strokes else "words" if quote else "box")
    return f"{ann_id}  {target} p.{page} ({what})  {styled['type'] or 'untyped'}  ({base['author']})"


def delete_annotation(
    root: Path, ann_id: str, writer: tuple[str, str], *, dry_run: bool = False
) -> tuple[str, list[dict[str, Any]]]:
    """Delete one annotation, with its replies: removed from the log, not marked.

    An agent deletes only what it wrote; a person deletes any. A person deleting an agent's annotation leaves that agent a line its next `loom since` reports once (`since.note_deletion`). Returns what to say, and the events removed, which `records.log.restore` puts back.
    """
    from loom.records.log import delete
    from loom.since import note_deletion

    found = find_annotation(Records(root).records, ann_id)
    if found is None:
        raise NotFoundError("annotation", f"no annotation {ann_id}")
    ann = found[1]
    akind, aid = writer
    if akind == "agent" and not (ann.author_kind == "agent" and ann.author_id == aid):
        raise EnvError(f"{ann_id} is {ann.author_id}'s, and an agent deletes only its own annotations")
    if dry_run:
        return f"deleted {ann_id}", []
    removed = delete(root, [ann_id])
    if akind != "agent":
        note_deletion(root, removed, aid)
    replies = sum(1 for e in removed if e.get("event") == "replied")
    said = f"deleted {ann_id}" + (f" and {replies} repl{'y' if replies == 1 else 'ies'} to it" if replies else "")
    return said, removed


#: What each verb carries beside its message; anything else given with it is refused by `refuse_lost`.
VERB_CARRIES: dict[str, tuple[str, ...]] = {
    "reply": (),
    "resolve": (),
    "edit": ("type", "color", "style", "weight", "opacity", "box", "stroke"),
    "delete": (),
}
_VERB_NOUN = {"reply": "a reply", "resolve": "a resolution", "edit": "an edit", "delete": "a deletion"}


def refuse_lost(verb: str, ann_id: str | None, given: dict[str, Any]) -> None:
    """Refuse an option `verb` would drop without a word: a verb carries its message and its `VERB_CARRIES` only.

    Called by `_one_comment` for a reply or resolution, and by `annotate` and `_batch_line` for an edit or a discard. An anchor, a kind and a document are set when an annotation is written, so losing one of those points at a new annotation rather than at `--edit`.
    """
    carried = VERB_CARRIES[verb]
    lost = [f"--{n}" for n, v in given.items() if v and n not in carried]
    if not lost:
        return
    fixed = {"--quote", "--page", "--box", "--in"}
    carries = ", ".join(f"--{n}" for n in carried)
    what = f"{_VERB_NOUN[verb]} carries " + (f"a new body, {carries} only" if carried else "its text only")
    if fixed & set(lost):
        fix = (
            "an annotation's anchor and document are set when it is written; write a new annotation for different ones"
        )
    elif verb == "delete":
        fix = "give the id alone"
    else:
        fix = f"`loom suggest KEY --with …` proposes text to put in, and --edit {ann_id} changes the annotation itself"
    raise EnvError(f"{what}, so {', '.join(lost)} would be lost; {fix}")


def check_edit(
    body: str | None,
    type_given: str | None,
    look: dict[str, Any],
    geometry: bool = False,
) -> None:
    """An edit must change something, and an edit to an empty body says nothing -- `--delete` is how one is taken back."""
    if body is not None and not body.strip():
        raise EnvError("an edit to an empty body says nothing; give the new text, or delete it with --delete")
    if body is None and type_given is None and not look and not geometry:
        raise EnvError("--edit with nothing to change; give a new body, --type, a look, --box or --stroke")


def edit_annotation(
    result: ScanResult,
    ann_id: str,
    writer: tuple[str, str],
    dry_run: bool = False,
    /,
    type_given: str | None = None,
    look: dict[str, Any] | None = None,
    rects: Any = None,
    strokes: Any = None,
    clear_look: bool = False,
    **fields: str | None,
) -> str:
    """Supersede an annotation's body, its type, its look or, on a PDF page, where a drawn one stands; the history stays in the log and one current body is shown.

    This is what a re-check does to a finding that still stands, so the finding is restated against the text as it is now: the edit records that version, and replay adopts it. A reply is dialogue; an edit is restatement. `type_given` of '' takes the type off; `clear_look` drops the look set on the annotation itself, so it is drawn in its type's again, before any of `look` is set over it.
    """
    root = result.quilt.root
    found = find_annotation(Records(root).records, ann_id)
    if found is None:
        raise NotFoundError("annotation", f"no annotation {ann_id}")
    ann = found[1]
    restyled: dict[str, Any] = {}
    if type_given is not None or look or clear_look:
        types = load_types(root)
        try:
            t = type_named(types, type_given) if type_given is not None else types.get(ann.type)
        except ValueError as exc:
            raise EnvError(str(exc)) from exc
        why = look_problem(look or {})
        if why:
            raise EnvError(f"--{why}")
        own = {**({} if clear_look else ann.own_look), **(look or {})}
        restyled = {"look": own, "drawn": drawn_look(t, own, types.plain)}
        if type_given is not None:
            restyled["type"] = t.id if t else None
    if rects or strokes:
        from loom.records.marks import MarkRefused, regeometry

        try:
            restyled.update(regeometry(result, ann, rects, strokes))
        except MarkRefused as exc:
            raise EnvError(exc.message) from exc
    if fields.get("body") is not None and ann.mark in ("pin", "text") and not str(fields["body"]).strip():
        raise EnvError(f"a {ann.mark} says something; delete it instead")
    akind, aid = writer
    event: dict[str, Any] = {"event": "edited", "id": ann_id, "when": stamp(), "author": aid, "kind": akind}
    version = _version(result, found[1].target_key, dry_run=dry_run)
    if version:
        event["against"] = version
    _append(root, {**event, **restyled, **{k: v for k, v in fields.items() if v is not None}}, dry_run)
    return f"edited {ann_id}"


BATCH_KEYS = (
    "target",
    "message",
    "quote",
    "type",
    "color",
    "style",
    "weight",
    "opacity",
    "reply",
    "resolve",
    "edit",
    "delete",
    "page",
    "box",
    "stroke",
    "mark",
    "in",
)
BATCH_VERBS = ("reply", "resolve", "edit", "delete")
#: The fields an edit or a deletion is checked for, by their batch key and their flag's name.
_LOSABLE = (
    "quote", "type", "color", "style", "weight", "opacity", "page", "box", "stroke", "mark", "in",
)  # fmt: skip
#: The look's fields, by their batch key and their flag's name.
LOOK_KEYS = ("color", "style", "weight", "opacity")


def _batch_line(result: ScanResult, writer: tuple[str, str], item: dict[str, Any], dry_run: bool = False) -> str:
    """One line of `--batch`: a new annotation, or one change to an existing one, named by exactly one verb.

    An unknown key is refused rather than ignored. A batch is written by a program that cannot see the result, so a misspelled `messsage` that silently files an empty annotation is a fault the writer never learns about — and every verb `loom annotate` has on the command line is available here, so there is no reason to fall back to one call per change.
    """
    unknown = sorted(set(item) - set(BATCH_KEYS))
    if unknown:
        raise EnvError(f"unknown key(s) {', '.join(unknown)}; accepted: {', '.join(BATCH_KEYS)}")
    verbs = [v for v in BATCH_VERBS if item.get(v)]
    if len(verbs) > 1:
        raise EnvError(f"one verb per line; this one gives {' and '.join(verbs)}")
    root = result.quilt.root
    for verb in ("delete", "edit"):
        if item.get(verb):
            refuse_lost(verb, str(item[verb]), {k: item.get(k) for k in _LOSABLE})
    if item.get("delete"):
        return delete_annotation(root, str(item["delete"]), writer, dry_run=dry_run)[0]
    look = {k: item[k] for k in LOOK_KEYS if item.get(k) is not None}
    rects = _rects(str(item["box"])) if item.get("box") else None
    strokes = _strokes(str(item["stroke"])) if item.get("stroke") else None
    if item.get("edit"):
        check_edit(item.get("message"), item.get("type"), look, bool(rects or strokes))
        return edit_annotation(
            result,
            str(item["edit"]),
            writer,
            dry_run,
            item.get("type"),
            look,
            rects,
            strokes,
            body=item.get("message"),
        )
    return _one_comment(
        result,
        writer,
        item.get("target"),
        item.get("message"),
        item.get("quote"),
        item.get("type"),
        item.get("reply"),
        item.get("resolve"),
        page=int(item["page"]) if item.get("page") is not None else None,
        rects=rects,
        in_doc=str(item["in"]) if item.get("in") else None,
        look=look,
        strokes=strokes,
        mark=str(item["mark"]) if item.get("mark") else None,
        dry_run=dry_run,
    )


def _strokes(given: str | tuple[str, ...]) -> list[list[float]]:
    """`x,y,x,y…` per stroke, as `--stroke` repeats or a batch line separates them with ';', in points from the page's top left."""
    parts = [given] if isinstance(given, str) else list(given)
    out: list[list[float]] = []
    for part in (q for p in parts for q in p.split(";")):
        try:
            out.append([float(n) for n in part.split(",") if n.strip()])
        except ValueError as exc:
            raise EnvError(f"--stroke wants x,y,x,y… in points, got {part!r}") from exc
    return out


def _rects(box: str) -> list[list[float]]:
    """`x0,y0,x1,y1[;x0,y0,x1,y1…]` as rectangles, in points with the origin at the top left."""
    out: list[list[float]] = []
    for part in box.split(";"):
        nums = [p.strip() for p in part.split(",") if p.strip()]
        if len(nums) != 4:
            raise EnvError(f"--box wants x0,y0,x1,y1 (points, origin top left), got {part!r}")
        try:
            out.append([float(n) for n in nums])
        except ValueError as exc:
            raise EnvError(f"--box wants numbers, got {part!r}") from exc
    return out


@click.command()
@click.argument("target", required=False, default=None)
@click.argument("message", required=False, default=None)
@click.option(
    "--quote",
    default=None,
    help="Anchor to this exact text: once in a key's own text, or on the page of a cited work given by --page.",
)
@click.option(
    "--page",
    "page",
    type=int,
    default=None,
    metavar="N",
    help="Page N of a PDF: a cited work (TARGET a citekey or a work identifier) or a project PDF by its path; with --quote, --box or --stroke.",
)
@click.option(
    "--box",
    "box",
    default=None,
    metavar="X0,Y0,X1,Y1",
    help="Anchor to a rectangle on the page, in points with the origin at the top left; ';' separates several. With --edit, where a drawn one stands now.",
)
@click.option(
    "--stroke",
    "strokes",
    multiple=True,
    metavar="X,Y,X,Y,…",
    help="A line of ink or an arrow on the page, in points from its top left; repeat for more lines. With --edit, its lines now.",
)
@click.option(
    "--mark",
    type=click.Choice(MARKS),
    default=None,
    help="Draw it on the PDF page with this tool: a pin or words on the page in the --box, a box or an oval round it, ink or an arrow along each --stroke.",
)
@click.option(
    "--type",
    "type_given",
    default=None,
    metavar="TYPE",
    help="The annotation's type, by id or name, from the quilt's annotation types; default none. With --edit, '' takes it off.",
)
@click.option("--color", type=click.Choice(list(COLORS)), default=None, help="Its colour, over its type's.")
@click.option(
    "--style", type=click.Choice(list(STYLES)), default=None, help="How it is drawn on words, over its type's."
)
@click.option(
    "--weight",
    type=click.IntRange(*WEIGHTS),
    default=None,
    help="An underline's or a strike's thickness, in whole pixels.",
)
@click.option("--opacity", type=click.IntRange(0, 100), default=None, help="Its opacity, in percent.")
@click.option(
    "--as",
    "author",
    default=None,
    metavar="NAME",
    help="Who is writing; an agent names itself, with Agent or AI in the name.",
)
@click.option("--reply", default=None, metavar="ID", help="Answer annotation ID; the message is the reply.")
@click.option("--resolve", default=None, metavar="ID", help="Mark annotation ID resolved, with the message as why.")
@click.option(
    "--edit",
    default=None,
    metavar="ID",
    help="Restate an annotation: a new body, --type, a look, or where a drawn one stands; never its anchor.",
)
@click.option(
    "--delete",
    "delete_id",
    default=None,
    metavar="ID",
    help="Delete an annotation, with its replies; an agent deletes only its own. It is removed from the log, not marked.",
)
@click.option(
    "--in",
    "in_doc",
    default=None,
    metavar="DOC",
    help="A claim about the node as read in this document: marked there, listed on the node's own page, absent elsewhere.",
)
@click.option(
    "--undo",
    is_flag=True,
    help="With --resolve, open the annotation again: an undo is another event, never a removal.",
)
@click.option(
    "--batch",
    is_flag=True,
    help="Read JSON lines from stdin, one annotation or one change per line; an unknown key is an error.",
)
@click.option("--dry-run", is_flag=True, help="Say what would be written, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def annotate(
    target: str | None,
    message: str | None,
    quote: str | None,
    page: int | None,
    box: str | None,
    strokes: tuple[str, ...],
    mark: str | None,
    type_given: str | None,
    color: str | None,
    style: str | None,
    weight: int | None,
    opacity: int | None,
    author: str | None,
    reply: str | None,
    resolve: str | None,
    edit: str | None,
    delete_id: str | None,
    in_doc: str | None,
    undo: bool,
    batch: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Write an annotation on TARGET: a key, an equation's qualified key, a master path, a cited work, or a project PDF; a MESSAGE of `-` is read from stdin.

    An annotation carries its author, its time and the version of the text it was written on, and belongs to no session. One on a cited work with no --page is on the whole work. One on a page of a PDF -- a cited work by citekey or identifier, or a project PDF by its path -- names the page with --page and the place with --quote (words on it), --box (a rectangle) or --stroke (ink), drawn with a --mark tool where it is not on words; `loom status --reading` lists those on cited works.
    """
    result = open_scan(quilt_path)
    root = result.quilt.root
    # Each of these names its annotation by id and takes no TARGET, so the one positional given is the body.
    if (reply or resolve or edit or delete_id) and message is None:
        message, target = target, None
    if batch and "-" in (message, target):
        raise EnvError("--batch reads its lines from stdin, so no text can be - beside it")
    (message,) = from_stdin({"MESSAGE": message})
    if undo and not resolve:
        raise EnvError("--undo applies to --resolve")
    verbs = [f"--{n}" for n, v in (("reply", reply), ("resolve", resolve), ("edit", edit), ("delete", delete_id)) if v]
    if len(verbs) > 1:
        raise EnvError(f"one verb per call; this one gives {' and '.join(verbs)}")
    look: dict[str, Any] = {
        k: v for k, v in (("color", color), ("style", style), ("weight", weight), ("opacity", opacity)) if v is not None
    }
    if edit or delete_id:
        given = {"quote": quote, "type": type_given, **look}
        refuse_lost(
            "edit" if edit else "delete",
            edit or delete_id,
            {**given, "page": page, "box": box, "stroke": strokes, "mark": mark, "in": in_doc},
        )
    if quote and box and not edit:
        raise EnvError("give --quote for words on the page or --box for a rectangle on it, not both")
    if delete_id and (message or "").strip():
        raise EnvError("a deletion says nothing, since nothing said with it is kept: give the id alone")
    if not batch:
        _check_named(
            result, target, reply or resolve or edit or delete_id, in_doc, page is not None or bool(box or strokes)
        )
        if (
            not (reply or resolve or edit or delete_id)
            and not (message or "").strip()
            and _given_opens(root, type_given)
        ):
            raise EnvError(NO_MESSAGE)
    lines = _batch_lines(result, author) if batch else []
    writer = _annotator(root, author)
    written: list[str] = []
    done = written.append

    if batch:
        for lineno, item in lines:
            try:
                done(_batch_line(result, writer, item, dry_run))
            except EnvError as exc:
                raise EnvError(f"batch line {lineno}: {exc.message}") from exc
            except ContentError as exc:
                raise ContentError(f"batch line {lineno}: {exc.message}") from exc
        Report(
            f"{'would write' if dry_run else 'wrote'} {counted(len(written), 'change')} from the batch"
            if written
            else "the batch was empty; nothing written",
            dry_run=dry_run,
            groups=[Group("", [Item(w.split(chr(10))[0]) for w in written], limit=None)],
            data=_annotated(written),
        ).emit(as_json)
        return
    if delete_id:
        done(delete_annotation(root, delete_id, writer, dry_run=dry_run)[0])
    elif edit:
        check_edit(message, type_given, look, bool(box or strokes))
        done(
            edit_annotation(
                result,
                edit,
                writer,
                dry_run,
                type_given,
                look,
                _rects(box) if box else None,
                _strokes(strokes) if strokes else None,
                body=message,
            )
        )
    else:
        done(
            _one_comment(
                result,
                writer,
                target,
                message,
                quote,
                type_given,
                reply,
                resolve,
                undo,
                page=page,
                rects=_rects(box) if box else None,
                in_doc=in_doc,
                look=look,
                strokes=_strokes(strokes) if strokes else None,
                mark=mark,
                dry_run=dry_run,
            )
        )
    first, *rest = written[0].split("\n")
    Report(_would(first) if dry_run else first, lines=rest, dry_run=dry_run, data=_annotated(written)).emit(as_json)


def _batch_lines(result: ScanResult, author: str | None) -> list[tuple[int, dict[str, Any]]]:
    """Every `--batch` line from stdin, each checked as a dry run before any is written, so a refused line leaves nothing half done.

    A line cannot name an annotation an earlier line of the same batch makes, since that id exists only once it is written.
    """
    items: list[tuple[int, dict[str, Any]]] = []
    for lineno, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        try:
            items.append((lineno, json.loads(line)))
        except json.JSONDecodeError as exc:
            raise EnvError(f"batch line {lineno}: {exc}; nothing was written") from exc
    if not items:
        return items
    trial = _annotator(result.quilt.root, author)
    for lineno, item in items:
        try:
            _batch_line(result, trial, item, dry_run=True)
        except EnvError as exc:
            raise EnvError(f"batch line {lineno}: {exc.message}; nothing was written") from exc
        except ContentError as exc:
            raise ContentError(f"batch line {lineno}: {exc.message}; nothing was written") from exc
    return items


def _given_opens(root: Path, given: str | None) -> bool:
    """Whether the type a command names stays open until resolved; a type the quilt lacks is refused later, where it is written."""
    t = load_types(root).find(given) if given else None
    return bool(t and t.open)


def _check_named(result: ScanResult, target: str | None, ann_id: str | None, in_doc: str | None, on_page: bool) -> None:
    """Refuse an annotation, a target or a document that names nothing, before anything is written (K3)."""
    if ann_id:
        if find_annotation(Records(result.quilt.root).records, ann_id) is None:
            raise NotFoundError("annotation", f"no annotation {ann_id}")
        return
    if not target:
        raise EnvError("TARGET is required")
    from loom.records.marks import project_pdf

    if project_pdf(result, target) is None and _work_target(result, target) is None:
        if on_page:
            raise _not_a_work(result, target)
        resolve_key(result, target)
    if in_doc is not None and in_doc.strip("/") not in result.masters:
        raise NotFoundError("document", f"{in_doc} is not a document of this quilt; loom status names them")


#: How a dry run says each change it did not make.
_WOULD = {
    "resolved": "would resolve",
    "reopened": "would reopen",
    "edited": "would edit",
    "deleted": "would delete",
}


def _would(said: str) -> str:
    """What `annotate --dry-run` says: the change it would have made, in the conditional."""
    verb, _, rest = said.partition(" ")
    return f"{_WOULD[verb]} {rest}" if verb in _WOULD else f"would write {said}"


def _annotated(written: list[str]) -> dict[str, Any]:
    """`loom annotate --json`'s data: each change as it was said, with the annotation it made or touched."""
    return {"written": [{"id": m.group(0) if (m := _ANN.search(w)) else None, "said": w} for w in written]}


_ANN = re.compile(ANNOTATION)


def status_payload(result: ScanResult, records: Records) -> dict[str, Any]:
    states = records.key_states(result)
    derived = records.derived(result, states)
    keys: dict[str, Any] = {}
    assert result.graph is not None
    live: dict[str, list[dict[str, Any]]] = {}
    # Notes on a page of a cited work have no key, so they have no row and count toward nothing (plan 0.13 item 4):
    # they are additions to the text and open is their resting state. They are listed on their own, by work.
    reading: list[dict[str, Any]] = []
    for res in records.resolved(result):
        a = res.annotation
        if a.anchor is not None or res.work:
            reading.append(
                {
                    "work": res.work,
                    "target": a.target_key,
                    # a whole work has no page, and one drawn on a page records its own
                    "page": a.anchor.page if a.anchor else a.page,
                    "basis": a.anchor.basis if a.anchor else (a.mark or ("box" if a.rects else None)),
                    "id": a.id,
                    "type": a.type,
                    "status": a.status,
                    "reply_to": a.in_reply_to,
                    "detached": res.detached,
                    "recorded": res.recorded,
                    "quote": a.selector.exact if a.selector else "",
                    "body": a.body,
                }
            )
            continue
        live.setdefault(a.target_key, []).append(
            {"id": a.id, "type": a.type, "status": a.status, "detached": res.detached}
        )
    # each live agent document's own rows, apart from the author's: what waits in it is the agent's work and the author's to look at, never the author's to-do list
    agent_rows: dict[str, dict[str, Any]] = {m: {} for m in result.masters if result.document_role(m) == "agent"}
    for key, ks in states.items():
        n = result.nodes[key]
        if n.kind == "section" and not live.get(key):
            continue  # a section is a row only when it carries a finding; otherwise it is structure, not work
        # an agent document is flat, so its own nodes, labelled or positional, are defined in its file
        agent_doc = n.file if n.file in agent_rows else None
        if agent_doc and not (n.incomplete or any(ks.open.values())):
            continue  # an agent document's node with nothing waiting is a row nowhere
        if n.conflict_of:
            continue  # one definition of a conflicted id: the id's own row below says so, rather than a positional key
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
        if agent_doc:
            entry["counterpart"] = n.derived_of
            agent_rows[agent_doc][key] = entry
            continue
        keys[key] = entry
    # An id two live files both define has no text and no state of its own until one definition goes; it is a row, so it cannot vanish from the list.
    from loom.history.ledger import load_history
    from loom.reshape.fork import conflict_fixes

    history = (
        load_history(result.quilt.history_dir) if any(n.kind == "conflict" for n in result.nodes.values()) else None
    )
    for key, n in result.nodes.items():
        if n.kind != "conflict" or history is None:
            continue
        keys[key] = {
            "key": key,
            "node": key,
            "kind": "statement",
            "taxon": n.taxon or "",
            "title": n.title or "",
            "state": "conflicted",
            "conflict": list(n.conflict),
            "fixes": conflict_fixes(result, history, key, list(n.conflict)),
            "incomplete": [],
            "reached_by": list(n.reached_by),
            "reviews": {"open": {}, "detached": 0, "annotations": []},
            "previous_key_match": None,
            "closure": [key],
        }
    from loom.refs.scan import other_versions

    digested = set(result.assembly.digest_files.values())
    # a key whose version is digested is answered through it, as lint counts it
    digested |= {k for k, vs in other_versions(result.bib).items() if digested & set(vs)}
    undigested = sorted(
        {
            c.citekey
            for c in result.edges.cites
            if c.postnote and c.citekey not in digested and c.file not in result.assembly.digest_files
        }
    )
    retired = sorted(k for k in records.latest if k not in result.nodes and k not in result.assembly.labels)
    from loom.history.ledger import load_history

    history = load_history(result.quilt.history_dir)
    copies = history.copies(result.masters)
    return {
        "summary": summarise(result, keys),
        "keys": keys,
        "agent_documents": {
            m: {
                "source": copies.get(m, ""),
                "keys": rows,
                "summary": agent_summary(rows),
            }
            for m, rows in sorted(agent_rows.items())
        },
        "undigested": undigested,
        "retired": retired,
        # a sort that keeps the log's order on one page, since an id says nothing of when
        "reading": sorted(reading, key=lambda r: (r["work"], r["page"] or 0)),
    }


STATUSES = ("open", "resolved")


def agent_summary(rows: dict[str, Any]) -> dict[str, int]:
    """What waits in one agent document: its rows, those marked incomplete, and their open annotations."""
    return {
        "keys": len(rows),
        "incomplete": sum(1 for e in rows.values() if e["incomplete"]),
        "open": sum(sum(e["reviews"]["open"].values()) for e in rows.values()),
    }


def agent_line(payload: dict[str, Any]) -> str:
    """Each agent document and what waits in it, in one line: `ai orient`'s, and the end of status's verdict."""
    said = []
    for doc, a in payload["agent_documents"].items():
        s = a["summary"]
        parts = [f"{s['incomplete']} incomplete"] if s["incomplete"] else []
        parts += [f"{s['open']} open"] if s["open"] else []
        said.append(f"{doc} {', '.join(parts) if parts else 'nothing waiting'}")
    return "; ".join(said)


def summarise(result: ScanResult, rows: dict[str, Any]) -> dict[str, int]:
    """The counting line, over the author's own keys among the rows it is printed under.

    A filtered list is summarised by what it holds, not by the quilt, and external keys are never in the arithmetic: a digest's results are permanently draft, permanently loose, and settled as a dependency, so counting them answers this line's questions about somebody else's paper (DR-172).
    """
    rows = {k: e for k, e in rows.items() if not result.nodes[k].external}
    acc = [e for e in rows.values() if e.get("acceptance")]
    return {
        "keys": len(rows),
        "conflicted": sum(1 for e in rows.values() if e["state"] == "conflicted"),
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
    type_id: str | None = None,
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
        if type_id and not any(a["type"] == type_id for a in anns):
            continue
        if status and not any(a["status"] == status for a in anns):
            continue
        if detached and not e["reviews"]["detached"]:
            continue
        out[key] = e
    return out


@click.command()
@click.option("--stale", "f_stale", is_flag=True, help="Accepted keys whose text, closure or preamble moved since.")
@click.option("--draft", "f_draft", is_flag=True, help="Keys never accepted.")
@click.option("--incomplete", "f_incomplete", is_flag=True, help="Keys marked \\incomplete.")
@click.option("--loose", "f_loose", is_flag=True, help="Keys no live document reaches.")
@click.option(
    "--unmatched-cites",
    "f_unmatched",
    is_flag=True,
    help="Located citations of a digested work that match no digest node.",
)
@click.option("--undigested", "f_undigested", is_flag=True, help="Works cited with a locator and not digested.")
@click.option("--retired", "f_retired", is_flag=True, help="Keys accepted once and defined by no document now.")
@click.option("--master", "f_master", default=None, metavar="DOC", help="Keys this document reaches.")
@click.option(
    "--in-order",
    "f_in_order",
    is_flag=True,
    help="With --master: the document's keys in the order it prints them, sections and an agent document's own among them, each with its state.",
)
@click.option("--tag", "f_tag", default=None, help="Keys carrying this tag.")
@click.option(
    "--type", "f_type", default=None, metavar="TYPE", help="Keys carrying an annotation of this type, by id or name."
)
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
@click.option(
    "--reading",
    "f_reading",
    is_flag=True,
    help="List the annotations on cited works, by work; they are in no row and count toward nothing otherwise.",
)
@click.option("--explain", default=None, metavar="KEY", help="Why KEY is in its state, with the diff of what moved.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@click.option("--session", "run_dir", default=None, envvar="LOOM_SESSION", help="Log this call to the session.")
@quilt_option
def status(
    f_stale: bool,
    f_draft: bool,
    f_incomplete: bool,
    f_loose: bool,
    f_unmatched: bool,
    f_undigested: bool,
    f_retired: bool,
    f_master: str | None,
    f_in_order: bool,
    f_tag: str | None,
    f_type: str | None,
    f_status: str | None,
    f_detached: bool,
    f_digests: bool,
    f_reading: bool,
    explain: str | None,
    as_json: bool,
    run_dir: str | None,
    quilt_path: str | None,
) -> None:
    """List every key with its computed state, cause if stale, and review facts; it exits 0 whatever it finds, and 2 only on an argument it refuses.

    Annotations on cited works are not on keys and appear in no row; `--reading` lists them by work, and `--json` always carries them under `reading`. While `loom serve` runs, a document it last compiled with errors or into no PDF is listed too, and `--json` carries how each of its compiles stands under `compiles`.
    """
    if f_in_order and f_master is None:
        raise EnvError("--in-order lists one document's keys; name it with --master DOC")
    result = open_scan(quilt_path)
    f_type, f_master, f_tag = _check_filters(result, f_type, f_master, f_tag)
    if explain:
        explain = resolve_key(result, explain)
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
        type_id=f_type,
        status=f_status,
        detached=f_detached,
    )
    for a in payload["agent_documents"].values():
        a["keys"] = filter_keys(
            result,
            a["keys"],
            incomplete=f_incomplete,
            master=f_master,
            tag=f_tag,
            type_id=f_type,
            status=f_status,
            detached=f_detached,
        )
        a["summary"] = agent_summary(a["keys"])
    payload["summary"] = summarise(result, payload["keys"])
    payload["unmatched"] = unmatched_cites(result)
    from loom.render.compiles import served

    compiles = served(result.quilt.root)
    if compiles is not None:
        payload["compiles"] = compiles
    filtered = any((f_stale, f_draft, f_incomplete, f_loose, f_master, f_tag, f_type, f_status, f_detached))
    if f_in_order:
        assert f_master is not None
        out, payload["in_order"] = _in_order_report(result, records, f_master)
    elif f_reading:
        out = _reading_report(payload)
    elif explain:
        out = _explain_report(result, records, payload, explain)
    elif f_undigested:
        out = Report(
            f"{counted(len(payload['undigested']), 'work')} cited with a locator and not digested"
            if payload["undigested"]
            else "every work cited with a locator is digested",
            groups=[Group("", [Item("", key=ck) for ck in payload["undigested"]], limit=None)],
        )
    elif f_retired:
        out = Report(
            f"{counted(len(payload['retired']), 'retired key')}: accepted once, and defined by no document now"
            if payload["retired"]
            else "no retired keys",
            groups=[
                Group(
                    "",
                    keyed(
                        [
                            (("ledger rows remain; last accepted", when(records.latest[k].date)[:10]), k)
                            for k in sorted(payload["retired"], key=natural)
                        ]
                    ),
                    limit=None,
                )
            ],
        )
    elif f_unmatched:
        rows: list[tuple[tuple[str, ...], str]] = [
            ((u["cite"],), f"{u['file']}:{u['line']}") for u in payload["unmatched"]
        ]
        out = Report(
            f"{counted(len(rows), 'citation')} with a locator no digest node matches"
            if rows
            else "every located citation of a digested work matches a node",
            groups=[Group("", keyed(rows), limit=None)],
        )
    else:
        out = _status_report(result, payload, filtered, f_digests, hidden)
    out.data = payload
    out.emit(as_json)


def _in_order_report(result: ScanResult, records: Records, master: str) -> tuple[Report, list[dict[str, Any]]]:
    """`status --master DOC --in-order`: DOC's keys in the order it prints them, each with its state and its open annotations.

    Read from the scan rather than from status's rows, which leave out a section without findings and an agent document's own nodes, both of which a reader of the document's structure wants.
    """
    exp = result.expansions.get(master)
    states = records.key_states(result)
    placed = []
    for key, n in result.nodes.items():
        if n.kind not in ("environment", "section", "proof") or n.conflict_of or n.external:
            continue
        at = exp.exp_offset(n.file, n.start) if exp is not None else None
        if at is not None:
            placed.append((at, key, n))
    rows: list[tuple[tuple[str, ...], str]] = []
    data: list[dict[str, Any]] = []
    for _, key, n in sorted(placed, key=lambda r: r[0]):
        ks = states.get(key)
        opened = {k: v for k, v in (ks.open if ks else {}).items() if v}
        title = n.title or ""
        rows.append(
            (
                (
                    n.taxon or n.kind,
                    title if len(title) <= 32 else title[:31] + "…",
                    ks.label if ks else "",
                    ", ".join(f"{v} open {k}{'s' if v != 1 else ''}" for k, v in opened.items()),
                ),
                key,
            )
        )
        data.append(
            {
                "key": key,
                "kind": n.kind,
                "taxon": n.taxon or "",
                "title": title,
                "state": ks.label if ks else "",
                "open": opened,
            }
        )
    report = Report(
        f"{counted(len(rows), 'key')} in {master}, in the order it prints them" if rows else f"{master} holds no keys",
        groups=[Group("", keyed(rows), limit=None)] if rows else [],
    )
    return report, data


def _check_filters(
    result: ScanResult, type_given: str | None, master: str | None, tag: str | None
) -> tuple[str | None, str | None, str | None]:
    """`status`'s --type, --master and --tag as the quilt names them, each refused by name when it names nothing (K3)."""
    from loom.cli.nodes import document_named

    type_id = None
    if type_given is not None:
        try:
            found = type_named(load_types(result.quilt.root), type_given)
        except ValueError as exc:
            raise EnvError(f"--type {type_given}: {exc}") from exc
        type_id = found.id if found else None
    if master is not None:
        master = document_named(result, master.strip("/"))
    if tag is not None:
        tags = {t for n in result.nodes.values() for t in n.directives.get("tags", "").replace(" ", "").split(",") if t}
        if tag not in tags:
            listed = ", ".join(sorted(tags)[:12]) + (", …" if len(tags) > 12 else "")
            raise NotFoundError(
                "tag", f"--tag {tag}: no node carries it" + (f"; tags in use: {listed}" if tags else "")
            )
    return type_id, master, tag


def unmatched_cites(result: ScanResult) -> list[dict[str, Any]]:
    """Each `\\cite[locator]{KEY}` of a digested work whose locator matches no node of its digest, for `--unmatched-cites`."""
    digested = set(result.assembly.digest_files.values())
    out = []
    for cite in result.edges.cites:
        if (
            cite.postnote
            and cite.citekey in digested
            and not any(
                e.via == "postnote" and e.src == cite.src and e.label == f"{cite.citekey}|{cite.postnote}"
                for e in result.edges.edges
            )
        ):
            out.append(
                {
                    "file": cite.file,
                    "line": cite.line,
                    "citekey": cite.citekey,
                    "postnote": cite.postnote,
                    "cite": f"\\cite[{cite.postnote}]{{{cite.citekey}}}",
                }
            )
    return out


#: The order status groups the author's rows in: what needs action first.
STATE_GROUPS = (
    ("conflicted", "conflicted"),
    ("stale", "stale"),
    ("incomplete", "incomplete"),
    ("proposed", "proposed"),
    ("draft", "draft"),
    ("accepted", "accepted"),
    ("", "sections with findings"),
)


def _facts(e: dict[str, Any]) -> list[str]:
    """What a row says beside its state: its open annotations by type, and what has come loose."""
    facts = []
    opened = {k: v for k, v in e["reviews"]["open"].items() if v}
    if opened:
        facts.append(", ".join(f"{v} open {k}{'s' if v != 1 else ''}" for k, v in opened.items()))
    if e["reviews"]["detached"]:
        facts.append(f"{e['reviews']['detached']} detached")
    if e.get("previous_key_match"):
        facts.append(f"acceptance recorded under {e['previous_key_match']}; re-accept to confirm")
    return facts


#: A stale acceptance's causes in the viewer's words (`arras/src/lib/review/evidence.ts`), so the two say one thing (K7).
CAUSE_WORDS = {
    "own-text-changed": "edited",
    "transcription-changed": "its transcription changed",
    "dependency-changed": "{id} changed",
    "dependency-removed": "{id} is no longer available",
    "dependency-added": "new dependency {id}",
    "dependency-scope-unavailable": "the full equation for {id} cannot be identified",
    "dependency-baseline-unavailable": "the earlier version of {id} is unavailable",
    "preamble-changed": "document definitions or formatting changed",
    "basis-changed": "the mathematical classification changed",
    "document-gone": "{id}, which it was accepted in, is unavailable",
}


def _cause_words(kind: str, id: str | None, at: str = "") -> str:
    """One cause of a stale acceptance in words, `at` (when it moved) after it, as `status` and `status --explain` both say it."""
    said = str(id or "a dependency")
    if said.startswith("equation:"):
        said = "equation " + said.removeprefix("equation:")
    return CAUSE_WORDS.get(kind, kind.replace("-", " ")).format(id=said) + (f" {at}" if at else "")


def _row_title(title: str, numbers: dict[str, Any]) -> str:
    """A row's title as the reader reads it: each `\\ref` by the number the last build printed for it, the rest of its LaTeX made plain, cut at a word."""
    title = re.sub(
        r"\\(?:eq|c|C|auto)?ref\s*\{([^}]*)\}",
        lambda m: numbers[m.group(1)].number if m.group(1) in numbers else m.group(1),
        title,
    )
    return plain_title(title, 32)


def _row_kind(e: dict[str, Any], numbers: dict[str, Any], key: str) -> str:
    """A row's kind, with the number the last build printed for it where there is one: `lemma 3.2`."""
    kind = e["taxon"] or e["kind"]
    return f"{kind} {numbers[key].number}" if key in numbers and numbers[key].number else kind


def _numbers(result: ScanResult) -> dict[str, Any]:
    """The numbers the default document's last build printed, by label; empty before a build."""
    from loom.tex.aux import read_numbers

    master = result.default_master
    return read_numbers(result.quilt.root, master) if master else {}


def _work_of(result: ScanResult, key: str) -> str:
    """The citekey of the work an external key was read from, or its file when no digest names one."""
    n = result.nodes[key]
    return result.assembly.digest_files.get(n.file) or n.file


def _compile_problems(compiles: dict[str, Any]) -> list[Group]:
    """The documents `loom serve` last compiled with errors or into no PDF, each with the line TeX stopped at and the command that shows the whole log."""
    from loom.paths import document_name

    items = []
    for doc, c in sorted(compiles.items()):
        last = c.get("last")
        if not last or last.get("result") == "ok":
            continue
        said = "no PDF, the last good one kept" if last["result"] == "failed" else "PDF made with errors"
        where = f" at {last['at']}" if last.get("at") else ""
        items.append(
            Item(
                f"{said}: {last.get('error') or 'no error line'}{where}",
                key=doc,
                fixes=[f"loom compile {document_name(doc)}"],
            )
        )
    return [Group("did not compile cleanly", items, limit=None, problem=True)] if items else []


def _status_report(
    result: ScanResult, payload: dict[str, Any], filtered: bool, include_digests: bool, hidden: set[str]
) -> Report:
    """`loom status`'s rows as a report: the author's keys grouped by state, what needs action first, then the cited works' keys summarised by work."""
    rows = payload["keys"]
    own = {k: e for k, e in rows.items() if not result.nodes[k].external}
    cited = {k: e for k, e in rows.items() if result.nodes[k].external}
    by_group: dict[str, list[tuple[tuple[str, ...], str]]] = {g: [] for g, _ in STATE_GROUPS}
    fixes: dict[str, list[str]] = {}
    numbers = _numbers(result)
    for key in sorted(own, key=natural):
        e = own[key]
        stale = bool(e.get("acceptance") and not e["acceptance"]["fresh"])
        group = "stale" if stale else e["state"]
        title = _row_title(e["title"], numbers)
        said = _facts(e)
        if e["state"] == "conflicted":
            said.insert(0, f"defined by {' and '.join(e['conflict'])}")
            fixes[key] = list(e["fixes"])
        if stale:
            said.insert(
                0,
                "; ".join(
                    _cause_words(c["kind"], c.get("id"), str(c.get("when") or "")[:10])
                    for c in e["acceptance"]["causes"]
                ),
            )
        if e["incomplete"]:
            said.append(f"incomplete: {'; '.join(e['incomplete'])}")
        by_group.setdefault(group, []).append(((_row_kind(e, numbers, key), title, "; ".join(said)), key))
    aligned = dict(
        zip(
            [k for g, _ in STATE_GROUPS for _, k in by_group[g]],
            keyed([r for g, _ in STATE_GROUPS for r in by_group[g]]),
            strict=True,
        )
    )
    groups = []
    for g, heading in STATE_GROUPS:
        if not by_group[g]:
            continue
        items = [aligned[k] for _, k in by_group[g]]
        for item in items:
            item.fixes = fixes.get(str(item.key), [])
        groups.append(
            Group(
                heading,
                items,
                limit=None,
                problem=g in ("conflicted", "stale"),
                next="loom accept --stale" if g == "stale" else None,
            )
        )
    s = payload["summary"]
    d = payload["digests"]
    if cited or (d["not_counted"] and not filtered):
        shown: dict[str, list[str]] = {}
        unshown: dict[str, int] = {}
        for k in cited:
            e = cited[k]
            mark = ", stale" if e.get("acceptance") and not e["acceptance"]["fresh"] else ""
            shown.setdefault(_work_of(result, k), []).append(state_label(result, k, e["state"]) + mark)
        for k in () if filtered else hidden:
            unshown[_work_of(result, k)] = unshown.get(_work_of(result, k), 0) + 1
        items = []
        # a work with nothing you depend on is the same sentence every time: one line names them all (T2)
        idle = sorted((w for w in unshown if w not in shown), key=natural)
        for work in sorted(shown, key=natural):
            states: dict[str, int] = {}
            for st in shown.get(work, []):
                states[st] = states.get(st, 0) + 1
            what = "shown" if include_digests else "you depend on"
            said = (
                [
                    f"{counted(len(shown[work]), 'result')} {what} ("
                    + ", ".join(f"{n} {st}" for st, n in sorted(states.items()))
                    + ")"
                ]
                if work in shown
                else []
            )
            if unshown.get(work):
                said.append(f"{unshown[work]} not counted")
            items.append(Item(", ".join(said), key=work))
        if idle:
            items.append(
                Item(
                    f"{counted(len(idle), 'work')} with {counted(sum(unshown[w] for w in idle), 'result')}, none you depend on, not counted",
                    key=", ".join(idle),
                )
            )
        groups.append(
            Group("in cited works", items, limit=None, next="loom status --include-digests" if unshown else None)
        )
    parts = []
    for g, heading in STATE_GROUPS:
        n = len(by_group[g])
        if n and g:
            parts.append(f"{n} {heading}")
        elif n:
            parts.append(counted(n, "section") + " with findings")
    waiting = {doc: a for doc, a in payload["agent_documents"].items() if a["keys"]}
    for doc, a in waiting.items():
        rows_ = []
        for key in sorted(a["keys"], key=natural):
            e = a["keys"][key]
            said = _facts(e)
            if e["incomplete"]:
                said.append(f"incomplete: {'; '.join(e['incomplete'])}")
            rows_.append(((e["taxon"] or e["kind"], _row_title(e["title"], {}), "; ".join(said)), key))
        groups.append(Group(f"in {doc}", keyed(rows_), limit=None, next=f"loom status --master {doc} --in-order"))
    groups.extend(_compile_problems(payload.get("compiles") or {}))
    if own:
        verdict = f"{counted(len(own), 'key')} of yours{' match' if filtered else ''}: " + ", ".join(parts)
    else:
        verdict = "no keys of yours match" if filtered else "no keys of yours yet"
    if s["loose"]:
        verdict += f"; {s['loose']} loose"
    if waiting:
        verdict += f"; {counted(len(waiting), 'agent document')}: " + agent_line({"agent_documents": waiting})
    return Report(verdict, ok=not (s["stale"] or s["conflicted"]), groups=groups)


def _reading_report(payload: dict[str, Any]) -> Report:
    """`loom status --reading`: the annotations on cited works, a group per work."""
    by_work: dict[str, list[dict[str, Any]]] = {}
    for r in payload["reading"]:
        by_work.setdefault(r["work"] or r["target"], []).append(r)
    groups = []
    for work in sorted(by_work, key=natural):
        rows = []
        for r in by_work[work]:
            where = (f"p.{r['page']}" if r["page"] else "the whole work") + (
                f" ({r['basis']})" if r["basis"] not in (None, "text") else ""
            )
            state = r["status"] + (", detached" if r["detached"] else "") + ("" if r["recorded"] else ", unrecorded")
            first = r["body"].strip().splitlines()[0] if r["body"].strip() else ""
            rows.append(
                ((where, r["type"] or "untyped", state, first[:40] + ("…" if len(first) > 40 else "")), r["id"])
            )
        groups.append(Group(work, keyed(rows), limit=None))
    n = len(payload["reading"])
    return Report(
        f"{counted(n, 'annotation')} on {counted(len(by_work), 'cited work')}"
        if n
        else "no annotations on any cited work",
        groups=groups,
    )


def _not_accepted(records: Records, key: str) -> str:
    """What `--explain` says of a key the local reviewer has not accepted: whose acceptances the ledger does hold, latest first per reviewer."""
    latest: dict[str, str] = {}
    for row in records.rows:
        if row.key == key and row.author and row.author != records.reviewer:
            latest[row.author] = max(latest.get(row.author, ""), str(row.date)[:10])
    if not latest:
        return "never accepted"
    others = ", ".join(f"{who} on {when}" for who, when in sorted(latest.items()))
    you = f"you ({records.reviewer})" if records.reviewer else "you"
    return f"not accepted by {you}; accepted by {others}"


def _explain_report(result: ScanResult, records: Records, payload: dict[str, Any], explain: str) -> Report:
    """`loom status --explain KEY`: the key's state, where it is, its open findings, and each cause of staleness with its diff."""
    key = resolve_key(result, explain)
    states = records.key_states(result)
    ks = states.get(key)
    if ks is None:
        raise EnvError(f"{key} is not a statement, proof or section key")
    section = result.nodes[key].kind == "section"
    n = result.nodes[key]
    lines = [f"in {n.file}"]
    if section:
        lines.append("a section: it carries findings and takes no acceptance")
    elif not ks.causes:
        lines.append("no causes: the acceptance is fresh" if ks.row else _not_accepted(records, key))
    e = payload["keys"].get(key) or {"reviews": {"open": dict(ks.open), "detached": ks.detached}}
    opened = {k: v for k, v in e["reviews"]["open"].items() if v}
    if opened:
        lines.append(", ".join(f"{v} open {k}{'s' if v != 1 else ''}" for k, v in opened.items()))
    if e["reviews"]["detached"]:
        lines.append(f"{counted(e['reviews']['detached'], 'detached annotation')}: the quoted text is gone")
    if ks.causes:
        lines += ["", f"causes ({len(ks.causes)})"]
    for c in ks.causes:
        lines.append("  " + _cause_words(c.kind, c.id, f"({when(c.when)})" if c.when else ""))
        diff = records.diff_for(result, c, key)
        if diff:
            lines += ["    " + line for line in diff.splitlines()]
    taxon = n.taxon or n.kind
    return Report(
        f"{key} ({taxon}): {state_label(result, key, ks.label) or 'a section'}",
        ok=not ks.causes,
        lines=lines,
    )
