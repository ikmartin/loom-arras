"""`loom accept`, `loom annotate`, `loom status` (book 7.3, 7.4.3, 7.7, 12.6)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError, NotFoundError
from loom.cli._quilt import describe, open_scan, quilt_option, require_text, resolve_key
from loom.cli.build_cmds import engine_for, log_run
from loom.cli.graph import keyed, natural, when
from loom.cli.report import Group, Item, Progress, Report, counted
from loom.clock import stamp, today
from loom.records.annotations import (
    GRADED,
    KINDS,
    PLACEMENTS,
    SEVERITIES,
    find_annotation,
    full_kind,
    next_id,
)
from loom.records.ledger import AcceptRow, append_rows
from loom.records.log import append
from loom.records.selectors import find_quote, make_selector
from loom.records.snapshots import snapshots_dir, write_snapshot
from loom.records.store import Records
from loom.render.manifest import key_hash, own_text
from loom.scan.hashing import normalize, sha256
from loom.scan.quilt import NoAuthorError, resolve_author
from loom.scan.scan import ScanResult
from loom.tex.runner import compile_tex


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
    pdf = root / "build" / Path(master).stem / f"{Path(master).stem}.pdf"
    newest = max((result.files[f].abspath.stat().st_mtime for f in result.files), default=0.0)
    if pdf.exists() and pdf.stat().st_mtime >= newest:
        return True, ""
    res = compile_tex(root, master, root / "build" / Path(master).stem, engine_for(result, master))
    return res.ok, res.first_error


def _acceptance_master(result: ScanResult, key: str) -> str:
    """Choose a deterministic document context for an acceptance not explicitly scoped to one master: never an agent's document, which nothing is accepted in."""
    reached = [m for m in result.nodes[key].reached_by if result.document_role(m) == "drafting"]
    if result.default_master and result.default_master in reached:
        return result.default_master
    if reached:
        return str(reached[0])
    own = [m for m in result.masters if result.document_role(m) == "drafting"]
    return result.default_master or (own[0] if own else "")


def _owned(result: ScanResult, key: str) -> bool:
    """A key the person's own documents reach, and not an agent document's derived key: what `--all-live` and `--master` may accept."""
    n = result.nodes[key]
    return not n.derived_of and any(result.document_role(m) == "drafting" for m in n.reached_by)


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
            raise ContentError(f"{master} is not a live drafting document; {key} cannot be accepted against it")
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
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
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
    """Record acceptance rows and snapshots for KEYS; the only writer of the ledger."""
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
        if accept_master and result.document_role(accept_master) != "drafting":
            raise EnvError(
                f"{accept_master} is not a live drafting document"
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
        if incomplete:
            raise ContentError(f"live incomplete keys prevent {scope}: {', '.join(incomplete)}")
        unclassified = [
            k for k in targets if result.nodes[k].kind == "environment" and result.nodes[k].basis == "unclassified"
        ]
        if unclassified:
            raise ContentError(f"live unclassified keys prevent {scope}: {', '.join(unclassified)}")
        open_claims = [
            k for k in targets if result.nodes[k].kind == "environment" and result.nodes[k].basis == "open-claim"
        ]
        if open_claims:
            raise ContentError(f"open claims cannot be accepted as established: {', '.join(open_claims)}")
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
    # each document a row is recorded against must compile, unless --force: the rows hash the source either way, so the compile is a check on the claim, not part of what is recorded
    documents = [] if force else list(dict.fromkeys(contexts[key] for key in targets if contexts.get(key)))
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
        f"{verdict} as {name}" + ("; nothing written" if dry_run else ""),
        dry_run=dry_run,
        groups=[Group(verb, items, next="loom status" if len(items) > 12 else None)],
        data=_accepted(rows, written, present),
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


def _writer(
    root: Path, session: str | None, author: str | None, *, sniff: bool = True, dry_run: bool = False
) -> tuple[str, str, str]:
    """(session id, author kind, author name) for whoever is writing (plan 0.13 §5).

    The two were one field: an agent's annotation recorded its run directory as its author, so the log could say *who* only by naming a place. Now the session says where the work belongs and the author says who did it -- a person by their name, an agent by what it is called, never by the author's git identity that its shell happens to share (DR-185).

    Writing with nothing active opens a session, for a person and an agent alike: refusing would make the first annotation of a sitting a two-command ritual.

    The caller says who is writing; the shell is asked only when nobody does, and only where asking it makes sense. `sniff=False` is the API's: a write arriving over HTTP is somebody at a browser, and the shell `loom serve` happens to have been started in says nothing about them. With `loom serve` running in an agent's terminal every note the author wrote in their own browser was recorded `author: "agent"`. Without a name to use it refuses, as a comment from an unnamed author always has, rather than guessing from the environment (plan 0.13 §8).
    """
    from loom.cli._common import agent_name, find_session, is_agent
    from loom.sessions import ensure_active

    # **An explicit identity wins, in both directions** (plan 0.13 §8). A declared name decides the kind by what it
    # calls itself, so an agent naming itself is an agent in a person's shell and a person naming themselves is a
    # person in an agent's; the marker is the safety net for a writer who declared nothing at all.
    declared = (author or "").strip()
    robot = agent_name() if sniff else None
    name = declared or robot or _author(author, root)
    kind = is_agent(declared) if declared else bool(robot)
    if session:
        s = find_session(root, session)
    elif dry_run:
        from loom.sessions import active, sessions

        here = sessions(root).get(active(root) or "")
        return (here.id if here else "a new session"), "agent" if kind else "human", name
    else:
        s = ensure_active(root, name)
    return s.id, "agent" if kind else "human", name


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


def _one_comment(
    result: ScanResult,
    writer: tuple[str, str, str],
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
    page: int | None = None,
    rects: list[list[float]] | None = None,
    in_doc: str | None = None,
    *,
    dry_run: bool = False,
) -> str:
    """Append one review event to the log and describe it; the only writer of review records.

    `page` with `quote` or `rects` makes this a note on a page of a cited work (plan 0.13 item 2): the target is then a citekey or a work identifier, and the event records the identifier, the artifact's hash, and a page anchor beside the usual text triple. Everything else about the event is as it is for a key.
    """
    root = result.quilt.root
    records = Records(root, result.quilt.history_dir).records
    date = today()
    session, akind, aid = writer
    base = {"when": stamp(), "author": aid, "kind": akind, "session": session}
    # An agent's links are its contract with the viewer: one that names nothing the viewer shows is refused here, with the command that prints a good one. A person's are their own business.
    if message and akind == "agent":
        from loom.links import refuse_bad_links

        refuse_bad_links(result, root, message)

    # a reply or a resolution is its text and nothing else; the rest would be dropped without a word
    if reply or resolve:
        lost = [
            f"--{n}"
            for n, v in (("quote", quote), ("severity", severity), ("payload", payload), ("placement", placement))
            if v
        ]
        if lost:
            raise EnvError(
                f"a {'reply' if reply else 'resolution'} carries its text only, so {', '.join(lost)} would be lost; "
                f"write a suggestion of its own for text to paste in, or --edit {reply or resolve} to change the note itself"
            )

    if resolve:
        found = find_annotation(records, resolve)
        if found is None:
            raise NotFoundError("annotation", f"no annotation {resolve}")
        _, parent = found
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
        ann_id = next_id(records, date)
        _append(
            root,
            {
                **base,
                "event": "replied",
                "id": ann_id,
                "target": parent.target_key,
                # the text the reply was written against, which may have moved on since the note it answers
                "against": _version(result, parent.target_key, dry_run=dry_run) or parent.target_hash,
                "anchor": parent.selector.to_dict() if parent.selector else None,
                "in": parent.in_doc,
                "annotation_kind": kind or "question",
                "body": message or "",
                "reply_to": reply,
            },
            dry_run,
        )
        return f"{ann_id}  {parent.target_key}  reply to {reply}  ({aid})"

    if not target:
        raise EnvError("TARGET is required")
    work = _work_target(result, target)
    if work is not None or page is not None or rects:
        return _note_on_page(
            result, base, records, date, target, work, message, quote, kind, severity, page, rects, dry_run=dry_run
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
            raise ContentError(f"quote not found in {key}")
        if len(spans) > 1:
            raise ContentError(f"quote is ambiguous ({len(spans)} occurrences); give a longer quote")
        selector = make_selector(text, quote)
    if kind is None:
        kind = "note"
    full = full_kind(kind)
    if full is None:
        raise EnvError(f"kind must be one of {', '.join(KINDS)} (any unambiguous prefix will do)")
    kind = full
    if severity is not None and severity not in SEVERITIES:
        raise EnvError(f"severity must be one of {', '.join(SEVERITIES)}")
    if severity is not None and kind not in GRADED:
        raise EnvError(f"--severity grades a fault, and --kind {kind} claims none; it belongs on {' or '.join(GRADED)}")
    if placement is not None and placement not in PLACEMENTS:
        raise EnvError(f"placement must be one of {', '.join(PLACEMENTS)}")
    if placement and not payload:
        raise EnvError("--placement says where a payload goes; give --payload too")
    ann_id = next_id(records, date)
    _append(
        root,
        {
            **base,
            "event": "created",
            "id": ann_id,
            "target": key,
            "against": _version(result, key, dry_run=dry_run) or key_hash(result, node_key),
            "anchor": selector.to_dict() if selector else None,
            "in": in_doc,
            "annotation_kind": kind,
            "body": message or "",
            "severity": severity,
            "payload": payload,
            "placement": placement,
        },
        dry_run,
    )
    sev = f" {severity}" if severity else ""
    return f"{ann_id}  {key}  {kind}{sev}  ({aid}{' run' if akind == 'run' else ''})"


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
            f"--page is for a page of a cited work, and {target} names none: give a citekey from the bibliography "
            "or an identifier one of its entries states (doi:…, arXiv:…)"
        )
    return EnvError(f"--page is for a page of a cited work, and {target} is a key in this quilt")


def _note_on_page(
    result: ScanResult,
    base: dict[str, Any],
    records: list[Any],
    date: str,
    target: str,
    work: tuple[str, Any] | None,
    message: str | None,
    quote: str | None,
    kind: str | None,
    severity: str | None,
    page: int | None,
    rects: list[list[float]] | None,
    *,
    dry_run: bool = False,
) -> str:
    """A note on a page of a cited work: the same event as any annotation, with the work as its target and a page anchor."""
    from loom.refs.anchoring import anchor_on_page
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map
    from loom.render.serve import open_url

    if work is None:
        raise _not_a_work(result, target)
    citekey, wid = work
    if page is None:
        raise EnvError(f"{citekey} is a cited work: say which page with --page N, and what on it with --quote or --box")
    if quote and rects:
        raise EnvError("give --quote for text on the page or --box for a rectangle on it, not both")
    if not quote and not rects:
        raise EnvError("a note on a page needs --quote (text on it) or --box (x0,y0,x1,y1 in points, origin top left)")
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
    if kind is None:
        kind = "note"
    full = full_kind(kind)
    if full is None:
        raise EnvError(f"kind must be one of {', '.join(KINDS)} (any unambiguous prefix will do)")
    kind = full
    if severity is not None and severity not in SEVERITIES:
        raise EnvError(f"severity must be one of {', '.join(SEVERITIES)}")
    if severity is not None and kind not in GRADED:
        raise EnvError(f"--severity grades a fault, and --kind {kind} claims none; it belongs on {' or '.join(GRADED)}")
    ann_id = next_id(records, date)
    # Quads are recorded only for a box, where they are the anchor; for text they are derived at build time from
    # the offsets, as a result's are, so a record never carries two descriptions that could drift apart.
    recorded = placed.anchor.to_dict()
    if placed.anchor.basis == "text":
        recorded.pop("quads", None)
    _append(
        result.quilt.root,
        {
            **base,
            "event": "created",
            "id": ann_id,
            "target": str(wid),
            "against": "sha256:" + placed.anchor.sha256,
            "anchor": {**recorded, **placed.selector.to_dict()},
            "annotation_kind": kind,
            "body": message or "",
            "severity": severity,
        },
        dry_run,
    )
    sev = f" {severity}" if severity else ""
    said = f"{ann_id}  {citekey} p.{page} ({placed.said})  {kind}{sev}  ({base['author']})"
    where = open_url(result.quilt.root, f"library/{citekey}?page={page}&annot={ann_id}")
    return said + (f"\nopen: {where}" if where else "")


def discard_annotation(
    root: Path,
    ann_id: str,
    writer: tuple[str, str, str],
    reason: str | None,
    undo: bool = False,
    *,
    dry_run: bool = False,
) -> str:
    """Withdraw one finding: it was raised in error and should not stand; with `undo`, put it back.

    Distinct from resolving, which says the author addressed it, and from `loom ai discard`, which sets a whole run aside. Nothing is deleted, so the finding and its reason stay in the log, and an undo is another event rather than the removal of one.
    """
    records = Records(root).records
    if find_annotation(records, ann_id) is None:
        raise NotFoundError("annotation", f"no annotation {ann_id}")
    session, akind, aid = writer
    event: dict[str, Any] = {
        "event": "discarded",
        "id": ann_id,
        "when": stamp(),
        "author": aid,
        "kind": akind,
        "session": session,
        "body": reason or "",
    }
    if undo:
        event["undo"] = True
    _append(root, event, dry_run)
    return f"{'reopened' if undo else 'withdrew'} {ann_id}"


def check_edit(body: str | None, severity: str | None, payload: str | None) -> None:
    """An edit must change something, and an edit to an empty body says nothing -- `--discard` is how a finding is withdrawn."""
    if body is not None and not body.strip():
        raise EnvError("an edit to an empty body says nothing; give the new text, or withdraw it with --discard")
    if body is None and severity is None and payload is None:
        raise EnvError("--edit with nothing to change; give a new body, --severity or --payload")


def edit_annotation(
    result: ScanResult, ann_id: str, writer: tuple[str, str, str], dry_run: bool = False, /, **fields: str | None
) -> str:
    """Supersede an annotation's body or payload; the history stays in the log and one current body is shown.

    This is what a re-check does to a finding that still stands, so the finding is restated against the text as it is now: the edit records that version, and replay adopts it. A reply is dialogue; an edit is restatement.
    """
    root = result.quilt.root
    found = find_annotation(Records(root).records, ann_id)
    if found is None:
        raise NotFoundError("annotation", f"no annotation {ann_id}")
    session, akind, aid = writer
    event: dict[str, Any] = {
        "event": "edited",
        "id": ann_id,
        "when": stamp(),
        "author": aid,
        "session": session,
        "kind": akind,
    }
    version = _version(result, found[1].target_key, dry_run=dry_run)
    if version:
        event["against"] = version
    _append(root, {**event, **{k: v for k, v in fields.items() if v is not None}}, dry_run)
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
    "page",
    "box",
    "in",
)
BATCH_VERBS = ("reply", "resolve", "edit", "discard")


def _batch_line(result: ScanResult, writer: tuple[str, str, str], item: dict[str, Any], dry_run: bool = False) -> str:
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
    if item.get("discard"):
        return discard_annotation(root, str(item["discard"]), writer, item.get("message"), dry_run=dry_run)
    if item.get("edit"):
        check_edit(item.get("message"), item.get("severity"), item.get("payload"))
        return edit_annotation(
            result,
            str(item["edit"]),
            writer,
            dry_run,
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
        page=int(item["page"]) if item.get("page") is not None else None,
        rects=_rects(str(item["box"])) if item.get("box") else None,
        in_doc=str(item["in"]) if item.get("in") else None,
        dry_run=dry_run,
    )


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
    help="A note on page N of a cited work (TARGET a citekey or a work identifier); with --quote or --box.",
)
@click.option(
    "--box",
    "box",
    default=None,
    metavar="X0,Y0,X1,Y1",
    help="Anchor to a rectangle on the page, in points with the origin at the top left; ';' separates several.",
)
# Not a `click.Choice`: the choice would reject a prefix before `full_kind` could resolve one, which is the whole
# point of accepting them — `confirmation` is long, and `--kind conf` should cost nothing (DR-204).
@click.option(
    "--kind",
    default=None,
    metavar="|".join(KINDS),
    help="What the annotation is; any unambiguous prefix. Default note.",
)
@click.option(
    "--session",
    "session",
    default=None,
    envvar="LOOM_SESSION",
    help="Write into this session: an id, a title, or a unique id suffix. Default the active one.",
)
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
    "--in",
    "in_doc",
    default=None,
    metavar="DOC",
    help="A claim about the node as read in this document: marked there, listed on the node's own page, absent elsewhere.",
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
@click.option("--dry-run", is_flag=True, help="Say what would be written, and write nothing, not even a session.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def annotate(
    target: str | None,
    message: str | None,
    quote: str | None,
    page: int | None,
    box: str | None,
    kind: str | None,
    session: str | None,
    author: str | None,
    reply: str | None,
    resolve: str | None,
    edit: str | None,
    discard_id: str | None,
    severity: str | None,
    payload: str | None,
    placement: str | None,
    in_doc: str | None,
    undo: bool,
    batch: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Write an annotation on TARGET: a key, an equation's qualified key, a master path -- or, with --page, a cited work.

    A note on a page of a cited work names the work by citekey or identifier and the place by --page with --quote (text on the page) or --box (a rectangle on it). It lands in the same log and the same session as every other annotation, and `loom status --reading` lists it.
    """
    result = open_scan(quilt_path)
    root = result.quilt.root
    # Each of these names its annotation by id and takes no TARGET (7.4), so the one positional given is the body.
    if (reply or resolve or edit or discard_id) and message is None:
        message, target = target, None
    if undo and not (discard_id or resolve):
        raise EnvError("--undo applies to --resolve or --discard")
    if not batch:
        _check_named(result, target, reply or resolve or edit or discard_id, in_doc, page is not None or bool(box))
    writer = _writer(root, session, author, dry_run=dry_run)
    written: list[str] = []

    def done(said: str, **verb: Any) -> None:
        """Log what was done, afterwards and with the annotation it touched, so a session's record says which (plan 0.14); the report says it once the command is through."""
        written.append(said)
        if not dry_run:
            log_run(writer[0], _logged(said, **verb), root)

    if batch:
        for lineno, line in enumerate(sys.stdin, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EnvError(f"batch line {lineno}: {exc}") from exc
            try:
                done(_batch_line(result, writer, item, dry_run), **{k: item.get(k) for k in _VERB_KEYS})
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
    if discard_id:
        done(
            discard_annotation(root, discard_id, writer, message, undo, dry_run=dry_run), discard=discard_id, undo=undo
        )
    elif edit:
        check_edit(message, severity, payload)
        done(
            edit_annotation(result, edit, writer, dry_run, body=message, severity=severity, payload=payload),
            edit=edit,
        )
    else:
        done(
            _one_comment(
                result,
                writer,
                target,
                message,
                quote,
                kind,
                reply,
                resolve,
                severity,
                payload,
                placement,
                undo,
                page=page,
                rects=_rects(box) if box else None,
                in_doc=in_doc,
                dry_run=dry_run,
            ),
            target=target,
            quote=quote,
            kind=kind,
            reply=reply,
            resolve=resolve,
            undo=undo,
            page=page,
            **{"in": in_doc},
        )
    first, *rest = written[0].split("\n")
    Report(_would(first) if dry_run else first, lines=rest, dry_run=dry_run, data=_annotated(written)).emit(as_json)


def _check_named(result: ScanResult, target: str | None, ann_id: str | None, in_doc: str | None, on_page: bool) -> None:
    """Refuse an annotation, a target or a document that names nothing, before any session is opened or logged to (K3)."""
    if ann_id:
        if find_annotation(Records(result.quilt.root).records, ann_id) is None:
            raise NotFoundError("annotation", f"no annotation {ann_id}")
        return
    if not target:
        raise EnvError("TARGET is required")
    if _work_target(result, target) is None:
        if on_page:
            raise _not_a_work(result, target)
        resolve_key(result, target)
    if in_doc is not None and in_doc.strip("/") not in result.masters:
        raise NotFoundError("document", f"{in_doc} is not a document of this quilt; loom status names them")


#: How a dry run says each change it did not make.
_WOULD = {"withdrew": "would withdraw", "resolved": "would resolve", "reopened": "would reopen", "edited": "would edit"}


def _would(said: str) -> str:
    """What `annotate --dry-run` says: the change it would have made, in the conditional."""
    verb, _, rest = said.partition(" ")
    return f"{_WOULD[verb]} {rest}" if verb in _WOULD else f"would write {said}"


def _annotated(written: list[str]) -> dict[str, Any]:
    """`loom annotate --json`'s data: each change as it was said, with the annotation it made or touched."""
    return {"written": [{"id": m.group(0) if (m := _ANN.search(w)) else None, "said": w} for w in written]}


_ANN = re.compile(r"a-\d{4}-\d{2}-\d{2}-\d+")
_VERB_KEYS = ("target", "quote", "kind", "reply", "resolve", "edit", "discard", "page", "in")


def _logged(said: str, **verb: Any) -> str:
    """The `run.log` line for one annotation: the verb as it was used, and the annotation it made or changed after `→`.

    The id is read from what the command printed, which names it first for a new note or reply and last for a resolve, an edit or a discard -- the first id in the text either way.
    """
    parts = ["loom annotate"]
    for flag in ("reply", "resolve", "edit", "discard"):
        if verb.get(flag):
            parts.append(f"--{flag} {verb[flag]}")
            break
    else:
        if verb.get("target"):
            parts.append(str(verb["target"]))
        if verb.get("page"):
            parts.append(f"--page {verb['page']}")
        if verb.get("quote"):
            parts.append("--quote")
        if verb.get("kind"):
            parts.append(f"--kind {verb['kind']}")
        if verb.get("in"):
            parts.append(f"--in {verb['in']}")
    if verb.get("undo"):
        parts.append("--undo")
    found = _ANN.search(said)
    return " ".join(parts) + (f" → {found.group(0)}" if found else "")


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
        if res.record.discarded:
            continue
        a = res.annotation
        if a.anchor is not None:
            if a.status != "discarded":
                reading.append(
                    {
                        "work": res.work,
                        "target": a.target_key,
                        "page": a.anchor.page,
                        "basis": a.anchor.basis,
                        "id": a.id,
                        "kind": a.kind,
                        "severity": a.severity,
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
            {"id": a.id, "kind": a.kind, "severity": a.severity, "status": a.status, "detached": res.detached}
        )
    for key, ks in states.items():
        n = result.nodes[key]
        if n.kind == "section" and not live.get(key):
            continue  # a section is a row only when it carries a finding; otherwise it is structure, not work
        if n.derived_of:
            continue  # an agent document's node is that document's, not the person's work: its counterpart is the row
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
    # An id two live files both define has no text and no state of its own until one definition goes (5.3.5); it is a row, so it cannot vanish from the list.
    for key, n in result.nodes.items():
        if n.kind != "conflict":
            continue
        keys[key] = {
            "key": key,
            "node": key,
            "kind": "statement",
            "taxon": n.taxon or "",
            "title": n.title or "",
            "state": "conflicted",
            "conflict": list(n.conflict),
            "fixes": [f"loom fork {key} --in {path}" for path in n.conflict],
            "incomplete": [],
            "reached_by": list(n.reached_by),
            "reviews": {"latest_current": None, "latest_any": None, "open": {}, "detached": 0, "annotations": []},
            "previous_key_match": None,
            "closure": [key],
        }
    runs = [
        {
            "path": r.rel,
            "discarded": r.discarded,
            "annotations": len(r.annotations),
            "kind": "session",
        }
        for r in records.records
    ]
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
    return {
        "summary": summarise(result, keys),
        "keys": keys,
        "runs": runs,
        "undigested": undigested,
        "retired": retired,
        "reading": sorted(reading, key=lambda r: (r["work"], r["page"], r["id"])),
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
@click.option("--runs", "f_runs", is_flag=True, help="Every session on record, with its annotations.")
@click.option("--master", "f_master", default=None, metavar="DOC", help="Keys this document reaches.")
@click.option("--tag", "f_tag", default=None, help="Keys carrying this tag.")
@click.option(
    "--severity",
    "f_severity",
    type=click.Choice(SEVERITIES),
    default=None,
    help="Keys carrying an annotation of this severity.",
)
@click.option(
    "--kind", "f_kind", default=None, metavar="|".join(KINDS), help="Keys carrying an annotation of this kind."
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
    help="List the notes on pages of cited works, by work; they are in no row and count toward nothing otherwise.",
)
@click.option("--explain", default=None, metavar="KEY", help="Why KEY is in its state, with the diff of what moved.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
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
    f_runs: bool,
    f_master: str | None,
    f_tag: str | None,
    f_severity: str | None,
    f_kind: str | None,
    f_status: str | None,
    f_detached: bool,
    f_digests: bool,
    f_reading: bool,
    explain: str | None,
    as_json: bool,
    run_dir: str | None,
    quilt_path: str | None,
) -> None:
    """List every key with its computed state, cause if stale, and review facts. Never exits nonzero.

    Notes on pages of cited works are not keys and appear in no row; `--reading` lists them by work, and `--json` always carries them under `reading`.
    """
    result = open_scan(quilt_path)
    f_kind, f_master, f_tag = _check_filters(result, f_kind, f_master, f_tag)
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
        severity=f_severity,
        kind=f_kind,
        status=f_status,
        detached=f_detached,
    )
    payload["summary"] = summarise(result, payload["keys"])
    payload["unmatched"] = unmatched_cites(result)
    filtered = any((f_stale, f_draft, f_incomplete, f_loose, f_master, f_tag, f_severity, f_kind, f_status, f_detached))
    if f_reading:
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
    elif f_runs:
        rows: list[tuple[tuple[str, ...], str]] = [
            (
                (r["kind"], counted(r["annotations"], "annotation"), "discarded" if r["discarded"] else ""),
                r["path"],
            )
            for r in sorted(payload["runs"], key=lambda r: natural(r["path"]))
        ]
        out = Report(
            f"{counted(len(rows), 'session')} on record" if rows else "no sessions on record",
            groups=[Group("", keyed(rows), limit=None)],
        )
    elif f_unmatched:
        rows = [((u["cite"],), f"{u['file']}:{u['line']}") for u in payload["unmatched"]]
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


def _check_filters(
    result: ScanResult, kind: str | None, master: str | None, tag: str | None
) -> tuple[str | None, str | None, str | None]:
    """`status`'s --kind, --master and --tag as the quilt names them, each refused by name when it names nothing (K3)."""
    from loom.cli.nodes import document_named

    if kind is not None:
        full = full_kind(kind)
        if full is None:
            raise EnvError(f"--kind {kind}: an annotation's kind is one of {', '.join(KINDS)}")
        kind = full
    if master is not None:
        master = document_named(result, master.strip("/"))
    if tag is not None:
        tags = {t for n in result.nodes.values() for t in n.directives.get("tags", "").replace(" ", "").split(",") if t}
        if tag not in tags:
            listed = ", ".join(sorted(tags)[:12]) + (", …" if len(tags) > 12 else "")
            raise NotFoundError(
                "tag", f"--tag {tag}: no node carries it" + (f"; tags in use: {listed}" if tags else "")
            )
    return kind, master, tag


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
    """What a row says beside its state: its open findings, or who last reviewed it clean, and what has come loose."""
    facts = []
    opened = {k: v for k, v in e["reviews"]["open"].items() if v}
    if opened:
        facts.append(", ".join(f"{v} open {k}{'s' if v != 1 else ''}" for k, v in opened.items()))
    elif e["reviews"]["latest_current"]:
        last = e["reviews"]["latest_current"]
        facts.append(f"reviewed clean ({last['author']['id']}, {last['date'][:10]})")
    if e["reviews"]["detached"]:
        facts.append(f"{e['reviews']['detached']} detached")
    if e.get("previous_key_match"):
        facts.append(f"acceptance recorded under {e['previous_key_match']}; re-accept to confirm")
    return facts


def _work_of(result: ScanResult, key: str) -> str:
    """The citekey of the work an external key was read from, or its file when no digest names one."""
    n = result.nodes[key]
    return result.assembly.digest_files.get(n.file) or n.file


def _status_report(
    result: ScanResult, payload: dict[str, Any], filtered: bool, include_digests: bool, hidden: set[str]
) -> Report:
    """`loom status`'s rows as a report: the author's keys grouped by state, what needs action first, then the cited works' keys summarised by work."""
    rows = payload["keys"]
    own = {k: e for k, e in rows.items() if not result.nodes[k].external}
    cited = {k: e for k, e in rows.items() if result.nodes[k].external}
    by_group: dict[str, list[tuple[tuple[str, ...], str]]] = {g: [] for g, _ in STATE_GROUPS}
    fixes: dict[str, list[str]] = {}
    for key in sorted(own, key=natural):
        e = own[key]
        stale = bool(e.get("acceptance") and not e["acceptance"]["fresh"])
        group = "stale" if stale else e["state"]
        title = e["title"] if len(e["title"]) <= 32 else e["title"][:31] + "…"
        said = _facts(e)
        if e["state"] == "conflicted":
            said.insert(0, f"defined by {' and '.join(e['conflict'])}")
            fixes[key] = list(e["fixes"])
        if stale:
            said.insert(
                0,
                "; ".join(
                    c["kind"]
                    + (" " + c["id"] if c.get("id") else "")
                    + (f" ({c['when'][:10]})" if c.get("when") else "")
                    for c in e["acceptance"]["causes"]
                ),
            )
        if e["incomplete"]:
            said.append(f"incomplete: {'; '.join(e['incomplete'])}")
        by_group.setdefault(group, []).append(((e["taxon"] or e["kind"], title, "; ".join(said)), key))
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
        for work in sorted(set(shown) | set(unshown), key=natural):
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
    if own:
        verdict = f"{counted(len(own), 'key')} of yours{' match' if filtered else ''}: " + ", ".join(parts)
    else:
        verdict = "no keys of yours match" if filtered else "no keys of yours yet"
    if s["loose"]:
        verdict += f"; {s['loose']} loose"
    return Report(verdict, ok=not (s["stale"] or s["conflicted"]), groups=groups)


def _reading_report(payload: dict[str, Any]) -> Report:
    """`loom status --reading`: the notes on pages of cited works, a group per work."""
    by_work: dict[str, list[dict[str, Any]]] = {}
    for r in payload["reading"]:
        by_work.setdefault(r["work"] or r["target"], []).append(r)
    groups = []
    for work in sorted(by_work, key=natural):
        rows = []
        for r in by_work[work]:
            where = f"p.{r['page']}" + (" (box)" if r["basis"] == "box" else "")
            state = r["status"] + (", detached" if r["detached"] else "") + ("" if r["recorded"] else ", unrecorded")
            first = r["body"].strip().splitlines()[0] if r["body"].strip() else ""
            rows.append(((where, r["kind"], state, first[:40] + ("…" if len(first) > 40 else "")), r["id"]))
        groups.append(Group(work, keyed(rows), limit=None))
    n = len(payload["reading"])
    return Report(
        f"{counted(n, 'note')} on the pages of {counted(len(by_work), 'cited work')}"
        if n
        else "no notes on any cited work's pages",
        groups=groups,
    )


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
        lines.append("no causes: the acceptance is fresh" if ks.row else "never accepted")
    e = payload["keys"].get(key) or {"reviews": {"open": dict(ks.open), "detached": ks.detached}}
    opened = {k: v for k, v in e["reviews"]["open"].items() if v}
    if opened:
        lines.append(", ".join(f"{v} open {k}{'s' if v != 1 else ''}" for k, v in opened.items()))
    if e["reviews"]["detached"]:
        lines.append(f"{counted(e['reviews']['detached'], 'detached annotation')}: the quoted text is gone")
    if ks.causes:
        lines += ["", f"causes ({len(ks.causes)})"]
    for c in ks.causes:
        lines.append(f"  {c.kind}{' ' + c.id if c.id else ''}{' (' + when(c.when) + ')' if c.when else ''}")
        diff = records.diff_for(result, c, key)
        if diff:
            lines += ["    " + line for line in diff.splitlines()]
    taxon = n.taxon or n.kind
    return Report(
        f"{key} ({taxon}): {state_label(result, key, ks.label) or 'a section'}",
        ok=not ks.causes,
        lines=lines,
    )
