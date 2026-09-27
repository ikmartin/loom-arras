"""`loom draft`, `loom stamp`, `loom fork`, `loom revert`, `loom live`, `loom mv`, `loom linearize`, `loom history` (book chapter 17).

Usage refusals are EnvError (exit 2), content refusals ContentError (exit 1); every command that writes ends with one `Recorded:` note naming the ledger line or step. Patches are printed for the editor to apply; loom rewrites no author file.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError, emit_json, note
from loom.cli._quilt import open_scan, quilt_option, require_text, resolve_key
from loom.cli.build_cmds import engine_for
from loom.history.checks import verify
from loom.history.ledger import Entry, History, Version, actor_for, append_entry, load_history
from loom.history.steps import file_hash, plan_freeze, slug, text_hash, write_step
from loom.history.versions import matching_version, materialize, parse_address, read_version
from loom.reshape.atomize import _single_node_file
from loom.reshape.canon import plan_draft
from loom.reshape.fork import _relabel, _rewrite_refs, plan_fork
from loom.reshape.ids import unified_diff
from loom.reshape.importer import set_main_forced
from loom.reshape.linearize import flatten, to_canon
from loom.scan.alloc import visible_locals
from loom.scan.labels import next_local, split_id
from loom.scan.quilt import load_quilt
from loom.scan.scan import ScanResult, scan, skipped_dirs
from loom.tex.assemble import shift_sectioning
from loom.tex.identity import identity_test


def _rel(root: Path, file: str) -> str:
    p = Path(file).expanduser()
    p = p if p.is_absolute() else (Path.cwd() / p)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return file


def _history(result: ScanResult) -> History:
    return load_history(result.quilt.history_dir)


def _confirm(yes: bool, what: str) -> None:
    if yes:
        return
    if not sys.stdin.isatty():
        raise EnvError(f"{what} needs confirmation; pass --yes")
    click.confirm("Apply?", abort=True)


# ---- draft ------------------------------------------------------------------


@click.command()
@click.argument("document")
@click.option(
    "--ai",
    "ai_name",
    required=True,
    metavar="NAME",
    help="The copy to write in the agent's drafting directory.",
)
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def draft(document: str, ai_name: str, as_json: bool, quilt_path: str | None) -> None:
    """Copy a live drafting document into the agent's drafting directory as NAME, flat, with every label it defines derived; a copy step records what each of its nodes began from (book 17.7).

    Starting a document from an old version of one is `loom history restore`.
    """
    _draft_ai(open_scan(quilt_path), document, ai_name, as_json)


def _draft_ai(result: ScanResult, source: str, name: str, as_json: bool) -> None:
    """`loom draft SOURCE --ai NAME`: one agent copy per document, never over an existing file or a taken name."""
    from loom.reshape.copy import plan_copy

    quilt = result.quilt
    root = quilt.root
    source_rel = _rel(root, source)
    role = result.document_role(source_rel)
    if role != "drafting":
        raise EnvError(
            f"{source_rel} is an agent's document; only a document in {quilt.config.drafting}/ is copied"
            if role
            else f"{source_rel} is not a live document in {quilt.config.drafting}/"
        )
    dest_rel = name if "/" in name else f"{quilt.config.drafting_ai}/{name}"
    if not dest_rel.endswith(".tex"):
        dest_rel += ".tex"
    if Path(dest_rel).parent.as_posix() != quilt.config.drafting_ai:
        raise EnvError(f"an agent's document goes directly under {quilt.config.drafting_ai}/, not at {dest_rel}")
    if (root / dest_rel).exists():
        raise EnvError(f"{dest_rel} exists; draft never overwrites")
    taken = [m for m in result.masters if Path(m).stem == Path(dest_rel).stem]
    if taken:
        raise EnvError(
            f"{taken[0]} is already named {Path(dest_rel).stem}; arras and the build tell documents apart by name"
        )
    history = _history(result)
    existing = [c for c, s in history.copies(result.masters).items() if s == source_rel]
    if existing:
        raise EnvError(f"{source_rel} already has an agent copy, {existing[0]}; an agent works in that one")
    conflicted = sorted(k for k, n in result.nodes.items() if n.kind == "conflict" and source_rel in n.reached_by)
    if conflicted:
        raise ContentError(
            f"{source_rel} reaches {', '.join(conflicted)}, defined by two files each; a copy needs one text per key"
        )
    plan = plan_copy(result, history, source_rel, dest_rel)
    dest = root / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(plan.text, encoding="utf-8")
    entry = write_step(
        history,
        "copy",
        f"copy-{Path(dest_rel).stem}",
        plan.freeze,
        actor_for(root),
        extra={"from": source_rel, "to": dest_rel, "bases": plan.bases},
        document_text=plan.source_text,
        document_name=Path(source_rel).name,
    )
    if as_json:
        emit_json({**entry.to_dict(), "line": entry.line})
        return
    click.echo(f"Wrote {dest_rel}: {source_rel} flat, {len(plan.labels)} labels derived, {len(plan.bases)} nodes based")
    click.echo(f"step {entry.step:04d} froze {len(plan.freeze.froze)} keys the copy's bases need")
    note(f"Recorded: copy as step {entry.step:04d} ({entry.dir})")


# ---- stamp --------------------------------------------------------------------


@click.command()
@click.argument("document", required=False, default=None)
@click.option(
    "--message",
    "-m",
    "message",
    required=True,
    help="What this stamp marks; given a DOCUMENT, it names the landmark (`widgets-v3`).",
)
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def stamp(document: str | None, message: str, as_json: bool, quilt_path: str | None) -> None:
    """Record every key whose text moved since the last step, quilt-wide; given DOCUMENT, only the keys it reaches, and its flat text kept as a landmark.

    A landmark is how a document stood at a moment worth returning to: `loom history show NAME` prints it and `loom history restore NAME --to FILE` starts a document from it (book 17.9).
    """
    result = open_scan(quilt_path)
    root = result.quilt.root
    history = _history(result)
    doc = _rel(root, document) if document else None
    if doc is not None and result.document_role(doc) != "drafting":
        raise EnvError(f"{document} is not a live document in {result.quilt.config.drafting}/")
    name = slug(message)
    if doc is not None and history.landmark(name) is not None:
        raise EnvError(f"a landmark is already named {name}; name this one differently")
    conflicted = (
        sorted(k for k, n in result.nodes.items() if n.kind == "conflict" and doc in n.reached_by) if doc else []
    )
    if conflicted:
        raise ContentError(
            f"{doc} reaches {', '.join(conflicted)}, defined by two files each; a landmark needs one text per key. loom lint --nodes shows them."
        )
    plan = plan_freeze(result, history, document=doc, narrow_to=doc)
    if doc is None and not plan.froze and not plan.removed and not plan.restored:
        last = history.next_step() - 1
        raise ContentError(
            f"nothing to stamp: no key has moved since step {last:04d}"
            if last
            else "nothing to stamp: no key has an id"
        )
    extra: dict[str, Any] = {"message": message, "in": doc}
    text = None
    if doc is not None:
        text = flatten(root, doc).text
        extra.update(landmark=f"{name}.tex", to={"path": f"{name}.tex", "hash": text_hash(text)}, reaches=plan.reaches)
    entry = write_step(
        history,
        "stamp",
        name if doc is not None else f"stamp-{name}",
        plan,
        actor_for(root),
        extra=extra,
        document_text=text,
        document_name=f"{name}.tex" if text is not None else None,
    )
    if as_json:
        emit_json({**entry.to_dict(), "line": entry.line})
    else:
        click.echo(
            f"step {entry.step:04d} froze {len(plan.froze)} keys"
            + (f", {len(plan.removed)} removed" if plan.removed else "")
            + (f", {len(plan.restored)} restored" if plan.restored else "")
            + (f"; landmark {name}, {doc} as it stands" if doc else "")
        )
        if plan.skipped:
            note(f"skipped (conflicted): {', '.join(plan.skipped)}")
    note(f"Recorded: stamp as step {entry.step:04d} ({entry.dir})")
    if doc is not None:
        # a landmark is what the quilt's bibliography is gathered from, so a new one may carry entries it lacks (book 8.15)
        from loom.refs.scan import scan_bibliography

        for line in scan_bibliography(result.quilt).lines():
            note(line)


# ---- fork ---------------------------------------------------------------------


@click.command()
@click.argument("node_id")
@click.option("--in", "in_doc", required=True, metavar="FILE", help="The document that gets its own copy.")
@click.option(
    "--from", "at", default=None, metavar="@N", help="Copy the text the key had at step N instead of the head."
)
@click.option("--as", "as_id", default=None, metavar="ID", help="The new id (default: the next free one).")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def fork(node_id: str, in_doc: str, at: str | None, as_id: str | None, as_json: bool, quilt_path: str | None) -> None:
    """Give FILE its own copy of a node under a new id: a node file when FILE includes the node, else the copy inline; printed as a patch for FILE, with its references rewritten. Nothing outside FILE changes."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    doc_rel = _rel(root, in_doc)
    key = node_id
    if key not in result.nodes:
        key = resolve_key(result, node_id)
    n = result.nodes[key]
    if n.kind not in ("environment", "conflict") or not n.id:
        raise EnvError(f"{node_id} is not a statement with an id")
    ref = at.lstrip("@") if at else None
    history = _history(result)
    plan = plan_fork(result, history, n.id, doc_rel, ref, as_id)
    if plan.refusal:
        raise ContentError(plan.refusal)
    if as_json:
        emit_json(
            {
                "id": plan.node_id,
                "new": plan.new_id,
                "in": plan.doc,
                "mode": plan.mode,
                "node_file": plan.node_file,
                "node_text": plan.node_text,
                "patched": plan.patched,
                "diff": plan.diff,
                "elsewhere": plan.elsewhere,
            }
        )
    if plan.node_file:
        target = root / plan.node_file
        if target.exists():
            raise ContentError(f"{plan.node_file} exists")
        if not as_json:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(plan.node_text, encoding="utf-8")
            click.echo(f"Wrote {plan.node_file}")
    if not as_json:
        click.echo(plan.diff, nl=False)
        note(f"{plan.doc} is yours to change: apply the patch above, or let your editor do it.")
        for f, count in sorted(plan.elsewhere.items()):
            note(f"{f} still refers to {plan.node_id} ({count} reference(s)); that may be what you want")
    if as_json:
        return
    entry = append_entry(
        result.quilt.history_dir,
        "fork",
        {
            "new": plan.new_id,
            "from": {"id": plan.node_id, "step": plan.step, "hash": plan.hash},
            "in": plan.doc,
            "to": plan.node_file or plan.doc,
            "patched": plan.doc,
        },
        actor_for(root),
    )
    note(f"Recorded: fork {plan.node_id} -> {plan.new_id} (ledger line {entry.line})")


# ---- revert -------------------------------------------------------------------


@click.command()
@click.argument("address")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def revert(address: str, as_json: bool, quilt_path: str | None) -> None:
    """Print the patch that puts KEY@N's recorded text back in place of the head's; the file is the author's to change. Reverting materializes a version, it never points at one."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    parsed = parse_address(address)
    if parsed is None:
        raise EnvError(f"{address} is not an address; write KEY@N or KEY@name")
    key, ref = parsed
    key = resolve_key(result, key)
    require_text(result, key)
    n = result.nodes[key]
    if n.kind not in ("environment", "proof"):
        raise EnvError(f"{key} is not a statement or proof key")
    history = _history(result)
    try:
        v, text = read_version(history, key, ref)
        body = materialize(text, result)
    except LookupError as exc:
        raise ContentError(str(exc)) from exc
    src = result.files[n.file].text
    patched = src[: n.start] + body.rstrip("\n") + src[n.end :]
    diff = unified_diff(src, patched, n.file)
    if as_json:
        emit_json({"key": key, "step": v.step, "hash": v.hash, "file": n.file, "diff": diff, "patched": patched})
    else:
        click.echo(diff, nl=False)
        if not diff:
            note(f"{key} already has the text of @{v.step}")
    entry = append_entry(
        result.quilt.history_dir, "revert", {"key": key, "step": v.step, "hash": v.hash, "in": n.file}, actor_for(root)
    )
    note(f"After applying, {key} has the text of @{v.step} ({v.name}). Recorded: revert (ledger line {entry.line})")


# ---- live ---------------------------------------------------------------------


@click.command()
@click.argument("file")
@quilt_option
def live(file: str, quilt_path: str | None) -> None:
    """Make a superseded document live again: it defines its nodes once more."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    rel = _rel(root, file)
    history = _history(result)
    if rel not in history.superseded_paths():
        raise EnvError(f"{rel} is not superseded")
    entry = append_entry(result.quilt.history_dir, "live", {"path": rel}, actor_for(root))
    click.echo(f"{rel} is live")
    note(f"Recorded: live (ledger line {entry.line})")


# ---- mv -----------------------------------------------------------------------


def _document_path(result: ScanResult, rel: str, given: str) -> None:
    """Refuse `rel` unless it can name a drafting document: a `.tex` directly in the drafting directory, inside the quilt.

    `given` is the argument as typed, for a path `_rel` could not make quilt-relative. The directories the scan never enters are named, since a retired path or one in the history is the likeliest slip.
    """
    drafting = result.quilt.config.drafting
    if Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise EnvError(f"{given} is outside the quilt; loom mv moves drafting documents within {drafting}/")
    for d in skipped_dirs(result.quilt):
        if rel == d or rel.startswith(f"{d}/"):
            raise EnvError(
                f"{rel} is inside {d}/, not the drafting directory {drafting}/; loom mv moves only drafting documents"
            )
    if not rel.endswith(".tex"):
        raise EnvError(f"{rel} is not a .tex file; a drafting document is a .tex directly in {drafting}/")
    if Path(rel).parent.as_posix() != drafting:
        raise EnvError(
            f"{rel} is not directly in the drafting directory {drafting}/; loom mv moves only drafting documents"
        )


def _named_documents(result: ScanResult) -> set[str]:
    """Every drafting-document path a record or the history names: `[quilt] main`, acceptance rows' `master`, annotations' `in` and whole-document targets, the sync record's main and documents, and any path a ledger line carries.

    `loom mv`'s record-only form refuses a path outside this set, since nothing would follow it. Ledger lines are read by value shape (a string, a list of strings, or `{path}`) so a new action needs no case here.
    """
    from loom.records.store import Records, is_document_path
    from loom.sync import SyncError, SyncState

    root = result.quilt.root
    records = Records(root, result.quilt.history_dir)
    named: set[str] = {result.quilt.config.main, *(row.master for row in records.rows if row.master)}
    for rec in records.records:
        for a in rec.annotations:
            named.update(p for p in (a.in_doc, a.target_key) if p)
    try:
        state = SyncState.read(root)
        named.update([state.master, *state.documents])
    except SyncError:
        pass
    for e in _history(result).entries:
        for v in e.data.values():
            for item in v if isinstance(v, list) else [v]:
                if isinstance(item, dict):
                    item = item.get("path")
                if isinstance(item, str):
                    named.add(item)
    return {p for p in named if is_document_path(result, p)}


@click.command("mv")
@click.argument("old")
@click.argument("new")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def mv(old: str, new: str, as_json: bool, quilt_path: str | None) -> None:
    """Move the drafting document OLD to NEW and record the move, so every record naming OLD follows it. When OLD is already gone and NEW is a live document, record a rename made elsewhere; nothing is moved.

    Both are .tex files directly in the drafting directory. Moving the default document moves [quilt] main with it.
    """
    result = open_scan(quilt_path)
    root = result.quilt.root
    old_rel, new_rel = _rel(root, old), _rel(root, new)
    _document_path(result, old_rel, old)
    _document_path(result, new_rel, new)
    if old_rel == new_rel:
        raise EnvError(f"{old_rel} and {new_rel} are the same path")
    old_here, new_here = (root / old_rel).exists(), (root / new_rel).exists()
    if old_here and new_here:
        raise EnvError(
            f"{old_rel} and {new_rel} both exist; loom mv never overwrites, and records a rename only once {old_rel} is gone"
        )
    if not old_here and not new_here:
        raise EnvError(f"neither {old_rel} nor {new_rel} exists: there is nothing to move and no rename to record")
    if old_here:
        if old_rel not in result.masters:
            src = result.files.get(old_rel)
            if src is not None and src.superseded:
                raise EnvError(
                    f"{old_rel} is superseded ({src.superseded}); `loom live {old_rel}` first, or move what superseded it"
                )
            raise EnvError(
                f"{old_rel} is not a live drafting document (it has no \\documentclass, or is ignored); loom mv moves only documents"
            )
        shutil.move(str(root / old_rel), str(root / new_rel))
        moved = True
    else:
        if new_rel not in result.masters:
            raise EnvError(
                f"{new_rel} is not a live drafting document; a rename is recorded only to a document loom scans"
            )
        if old_rel not in _named_documents(result):
            raise EnvError(
                f"{old_rel} is not a document any record or the history names; there is nothing to follow to {new_rel}"
            )
        if result.current_document(old_rel) == new_rel:
            raise EnvError(f"the history already takes {old_rel} to {new_rel}; nothing to record")
        moved = False
    entry = append_entry(
        result.quilt.history_dir, "move", {"from": old_rel, "to": new_rel, "moved": moved}, actor_for(root)
    )
    main = result.quilt.config.main
    main_moved = (main == old_rel or result.current_document(main) == old_rel) and set_main_forced(
        result.quilt, new_rel
    )
    if as_json:
        emit_json({**entry.to_dict(), "line": entry.line})
    elif moved:
        click.echo(f"Moved {old_rel} to {new_rel}")
    else:
        click.echo(f"{old_rel} was renamed to {new_rel} outside loom; records naming it follow")
    if main_moved:
        note(f"main = {new_rel}")
    note(f"Recorded: move (ledger line {entry.line})")


# ---- linearize ----------------------------------------------------------------


@click.command()
@click.argument("spine")
@click.option("--to", "to", required=True, metavar="FILE", help="The flat document to write.")
@click.option(
    "--fork", "do_fork", is_flag=True, help="Give this document its own copy of every node another document shares."
)
@click.option("--keep-shared", "keep_shared", is_flag=True, help="Leave shared node files as inclusions, marked.")
@click.option("--no-check", "no_check", is_flag=True, help="Skip the identity test.")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def linearize(
    spine: str, to: str, do_fork: bool, keep_shared: bool, no_check: bool, as_json: bool, quilt_path: str | None
) -> None:
    """Write FILE: SPINE with every \\input, \\include and \\nest (levels shifted) expanded in place. The spine and every file it inlined are then superseded."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    spine_rel = _rel(root, spine)
    if spine_rel not in result.files:
        raise EnvError(f"{spine} is not a scanned file of this quilt")
    to_rel = _rel(root, to)
    if (root / to_rel).exists():
        raise EnvError(f"{to_rel} exists; linearize never overwrites")
    if do_fork and keep_shared:
        raise EnvError("--fork and --keep-shared exclude each other")
    exp = result.expansions.get(spine_rel)
    reached = [f for f in (exp.reached if exp else {}) if f != spine_rel]
    shared: dict[str, list[str]] = {}
    for f in reached:
        others = [m for m in result.nodes[f].reached_by if m != spine_rel] if f in result.nodes else []
        if others:
            shared[f] = others
    ids_in = {
        f: [k for k, n in result.nodes.items() if n.file == f and n.kind == "environment" and n.id] for f in shared
    }
    if shared and not (do_fork or keep_shared):
        lines = [
            f"  {f} ({', '.join(ids_in[f]) or 'no ids'}) is also included by {', '.join(ms)}"
            for f, ms in sorted(shared.items())
        ]
        raise ContentError(
            "the spine shares nodes with another document; inlining them would define each twice:\n"
            + "\n".join(lines)
            + "\nEither --fork (this document gets its own copies) or --keep-shared (they stay inclusions, marked)."
        )
    forks: list[dict[str, Any]] = []
    if do_fork:
        for f in sorted(shared):
            if not _single_node_file(result, f):
                raise ContentError(
                    f"{f} holds more than one node; move them out first with loom atomize --key, then linearize"
                )
    marker = None
    if keep_shared:

        def marker(child: str) -> str:
            ids = ids_in.get(child, [])
            example = f"loom fork {ids[0]} --in {to_rel}" if ids else f"loom atomize --key ... {child}"
            return f"% !LOOM shared: {child} is also included by {', '.join(shared[child])} -- `{example}` to split"

    flat = flatten(root, spine_rel, skip=set(shared) if shared else None, marker=marker)
    text = flat.text
    if do_fork:
        import re

        taken: set[str] = set()
        for f in sorted(shared):
            ids = ids_in[f]
            node = result.nodes[ids[0]] if ids else None
            if node is None:
                continue
            prefix = (split_id(node.id or "") or (result.quilt.config.prefix, ""))[0]
            seen = visible_locals(result, prefix) | taken
            new_id = f"{prefix}-{next_local(seen)}"
            taken.add(new_id.split("-", 1)[1])
            names = {node.id or "", *node.aliases, *node.label_offsets}
            body = _rewrite_refs(_relabel(result.files[f].text, node, node.id or "", new_id), names, new_id)
            stem = f[: -len(".tex")]
            pat = re.compile(r"^([ \t]*)\\(input|nest)\{(" + re.escape(stem) + "|" + re.escape(f) + r")\}[ \t]*$", re.M)

            def repl(m: re.Match[str], body: str = body) -> str:
                b = shift_sectioning(body, 1) if m.group(2) == "nest" else body
                return b.rstrip("\n")

            text = pat.sub(repl, text)
            text = _rewrite_refs(text, names, new_id)
            forks.append({"new": new_id, "from": {"id": node.id, "hash": file_hash(root / f)}, "file": f})
    dest = root / to_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    if not no_check and spine_rel in result.masters:
        with tempfile.TemporaryDirectory(prefix="loom-identity-") as tmp:
            ident = identity_test(root, spine_rel, root, to_rel, Path(tmp), engine_for(result, spine_rel))
        note(ident.summary())
        if not ident.passed and not ident.skipped:
            dest.unlink(missing_ok=True)
            raise ContentError(
                f"the flat copy does not typeset as {spine_rel}; {to_rel} was removed and nothing was recorded. Pass --no-check to write it anyway."
            )
    superseded = [spine_rel, *[f for f in flat.inlined if f in result.files]]
    entry = append_entry(
        result.quilt.history_dir,
        "linearize",
        {"from": spine_rel, "to": to_rel, "superseded": superseded, "forks": forks, "kept": list(flat.kept)},
        actor_for(root),
    )
    if as_json:
        emit_json({**entry.to_dict(), "line": entry.line})
    else:
        click.echo(f"Wrote {to_rel} ({text.count(chr(10))} lines, {len(flat.inlined)} files inlined)")
        for fk in forks:
            click.echo(f"  {fk['from']['id']} -> {fk['new']}  ({fk['file']})")
        for f in flat.kept:
            click.echo(f"  kept {f} as an inclusion (shared)")
    note(f"{', '.join(superseded)} are now superseded and inert; loom live FILE reverses that")
    if result.quilt.config.main in superseded and set_main_forced(result.quilt, to_rel):
        note(f"main = {to_rel}")
    note(f"Recorded: linearize (ledger line {entry.line})")


# ---- history ------------------------------------------------------------------


def _version_lines(result: ScanResult, history: History, key: str) -> tuple[list[Version], Version | None, str]:
    versions = history.versions_of(key)
    n = result.nodes.get(key)
    head_hash = ""
    if n is not None and n.kind in ("environment", "proof"):
        from loom.render.manifest import key_hash

        head_hash = key_hash(result, key)
    return versions, matching_version(history, key, head_hash) if head_hash else None, head_hash


@click.command()
@click.argument("words", nargs=-1)
@click.option(
    "--to",
    "to",
    default=None,
    metavar="FILE",
    help="With restore: the new document, directly in the drafting directory.",
)
@click.option(
    "--plain", is_flag=True, help="With show: the paper without loom, its package line swapped for the macro block."
)
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def history(words: tuple[str, ...], to: str | None, plain: bool, as_json: bool, quilt_path: str | None) -> None:
    """The steps and stamps of this quilt, one per line; with KEY, that key's versions and whether the head equals one.

    `loom history show LANDMARK [--plain]` prints a landmark's text; `loom history restore LANDMARK --to FILE` starts a document from it; `loom history verify` walks every step directory against the ledger. A landmark is named by its name, its step, or `DOC@STEP` (book 17.9).
    """
    verb = words[0] if words else None
    if verb == "verify":
        _verify(as_json, quilt_path)
        return
    if verb in ("show", "restore"):
        if len(words) != 2:
            raise EnvError(f"loom history {verb} needs one LANDMARK: its name, its step, or DOC@STEP")
        (_show if verb == "show" else _restore)(words[1], to, plain, as_json, quilt_path)
        return
    if len(words) > 1:
        raise EnvError("loom history takes one KEY, or show, restore or verify")
    key = verb
    result = open_scan(quilt_path)
    hist = _history(result)
    if key is not None:
        k = resolve_key(result, key)
        versions, match, head_hash = _version_lines(result, hist, k)
        if as_json:
            emit_json(
                {
                    "key": k,
                    "versions": [{"step": v.step, "hash": v.hash, "name": v.name, "of": v.of} for v in versions],
                    "head": head_hash or None,
                    "head_is": match.step if match else None,
                }
            )
            return
        if not versions:
            click.echo(f"{k} has no recorded version")
        for v in versions:
            click.echo(f"{k}@{v.step}  {v.hash[:19]}  {v.name}" + (f"  of {v.of}" if v.of else ""))
        if head_hash:
            click.echo(f"head: {'the text of @' + str(match.step) if match else 'differs from every version'}")
        return
    if as_json:
        emit_json([{**e.to_dict(), "line": e.line} for e in hist.entries])
        return
    if not hist.entries:
        click.echo("no history yet: loom stamp records the first step")
        return
    for e in hist.entries:
        when = e.when[:10]
        if e.step is not None:
            what = f"{e.step:04d}  {e.action:<9} {when}  {e.name}"
            if e.message:
                what += f'  "{e.message}"'
            what += f"  froze {len(e.get('froze') or {})}"
            if e.get("removed"):
                what += f", removed {len(e.get('removed'))}"
            click.echo(what)
        else:
            click.echo(f"      {e.action:<9} {when}  {_detail(e)}")


def _landmark(quilt_path: str | None, ref: str) -> tuple[ScanResult, History, Entry, str]:
    """The scan, the history, the landmark `ref` names and its text; EnvError naming the landmarks there are."""
    result = open_scan(quilt_path)
    hist = _history(result)
    e = hist.landmark(ref)
    if e is None:
        names = ", ".join(f"{Path(str(x.get('landmark'))).stem} (@{x.step})" for x in hist.landmarks()) or "none yet"
        raise EnvError(f"no landmark answers to {ref}; the landmarks are {names}")
    path = hist.landmark_path(e)
    if not path.is_file():
        raise ContentError(f"the text of landmark {ref} is missing: {path.relative_to(result.quilt.root)}")
    return result, hist, e, path.read_text(encoding="utf-8")


def _show(ref: str, to: str | None, plain: bool, as_json: bool, quilt_path: str | None) -> None:
    """`loom history show LANDMARK [--plain]`: the text as the step kept it, or without loom."""
    if to is not None:
        raise EnvError("--to belongs to loom history restore")
    _, _, e, text = _landmark(quilt_path, ref)
    text = to_canon(text) if plain else text
    if as_json:
        emit_json({"landmark": Path(str(e.get("landmark"))).stem, "step": e.step, "in": e.get("in"), "text": text})
        return
    click.echo(text, nl=False)


def _restore(ref: str, to: str | None, plain: bool, as_json: bool, quilt_path: str | None) -> None:
    """`loom history restore LANDMARK --to FILE`: a new drafting document from a landmark, with the package line and an id on every node that has none; the author's alone."""
    from loom.cli._common import refuse_under_agent

    refuse_under_agent("loom history restore", "Ask the author to start the document.")
    if plain:
        raise EnvError("--plain belongs to loom history show")
    if to is None:
        raise EnvError("loom history restore needs --to FILE, the new document")
    result, hist, e, text = _landmark(quilt_path, ref)
    quilt = result.quilt
    root = quilt.root
    dest_rel = _rel(root, to)
    if Path(dest_rel).parent.as_posix() != quilt.config.drafting:
        raise EnvError(f"a restored document goes directly under {quilt.config.drafting}/, not at {dest_rel}")
    if (root / dest_rel).exists():
        raise EnvError(f"{dest_rel} exists; restore never overwrites")
    plan = plan_draft(result, text, dest_rel)
    if plan.violations or plan.spans:
        raise ContentError(
            f"landmark {ref} cannot be drafted as it is: "
            + "; ".join(plan.spans or [f"line {v.line}" for v in plan.violations])
        )
    dest = root / dest_rel
    dest.write_text(plan.text, encoding="utf-8")
    name = Path(str(e.get("landmark"))).stem
    entry = append_entry(
        quilt.history_dir,
        "restore",
        {
            "from": {"landmark": name, "step": e.step},
            "to": {"path": dest_rel, "hash": text_hash(plan.text)},
            "ids": len(plan.insertions),
        },
        actor_for(root),
    )
    if as_json:
        emit_json({**entry.to_dict(), "line": entry.line})
        return
    click.echo(f"Wrote {dest_rel} from landmark {name} (@{e.step}), {len(plan.insertions)} ids inserted")
    if any(n.kind == "conflict" and dest_rel in n.conflict for n in scan(load_quilt(root)).nodes.values()):
        note(
            f"{dest_rel} defines ids another live document also defines; loom lint lists them, and loom fork or retiring one resolves each"
        )
    note(f"Recorded: restore (ledger line {entry.line})")


def _detail(e: Entry) -> str:
    frm, to = e.get("from"), e.get("to")
    if e.action == "atomize":
        return f"{', '.join(frm or [])} -> {', '.join(to or [])}"
    if e.action == "linearize":
        return f"{frm} -> {to}"
    if e.action == "fork":
        return f"{(frm or {}).get('id')} -> {e.get('new')} in {e.get('in')}"
    if e.action == "revert":
        return f"{e.get('key')}@{e.get('step')} in {e.get('in')}"
    if e.action == "live":
        return str(e.get("path"))
    if e.action == "restore":
        return f"{(frm or {}).get('landmark')} (@{(frm or {}).get('step')}) -> {(to or {}).get('path')}"
    if e.action == "copy":
        return f"{frm} -> {to} ({len(e.get('bases') or {})} nodes based)"
    if e.action == "move":
        how = (
            "" if e.get("moved") else (" (renamed in a pull)" if e.get("via") == "sync" else " (renamed outside loom)")
        )
        return f"{frm} -> {to}{how}"
    return ""


def _verify(as_json: bool, quilt_path: str | None) -> None:
    """`loom history verify`: walk every step directory against the ledger -- missing or edited version files, preambles, copies, and ancestry that no longer resolves."""
    result = open_scan(quilt_path)
    hist = _history(result)
    diags = verify(result, hist)
    if as_json:
        emit_json([d.to_dict() for d in diags])
    else:
        from loom.cli.lint_cmd import format_diagnostic

        for d in diags:
            click.echo(format_diagnostic(d))
        steps = hist.steps()
        files = sum(len(e.get("froze") or {}) for e in steps)
        if not diags:
            click.echo(f"history verified: {len(steps)} steps, {files} version files")
    if any(d.severity == "error" for d in diags):
        raise SystemExit(1)
