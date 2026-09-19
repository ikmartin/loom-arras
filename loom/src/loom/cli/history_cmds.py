"""`loom draft`, `loom canonize`, `loom stamp`, `loom fork`, `loom revert`, `loom live`, `loom linearize`, `loom history` (book chapter 17).

Usage refusals are EnvError (exit 2), content refusals ContentError (exit 1); every command that writes ends with one `Recorded:` note naming the ledger line or step. Patches are printed for the editor to apply; loom rewrites no author file.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError, emit_json, note
from loom.cli._quilt import open_scan, quilt_option, require_text, resolve_key
from loom.cli.build_cmds import engine_for
from loom.history.checks import verify
from loom.history.ledger import Entry, History, Version, actor_for, append_entry, load_history
from loom.history.steps import file_hash, infer_parent, plan_freeze, slug, text_hash, write_step
from loom.history.versions import matching_version, materialize, parse_address, read_version
from loom.reshape.atomize import _single_node_file
from loom.reshape.canon import draft_entry, plan_draft
from loom.reshape.fork import _relabel, _rewrite_refs, plan_fork
from loom.reshape.ids import unified_diff
from loom.reshape.importer import report_counts, set_main, set_main_forced
from loom.reshape.linearize import flatten, to_canon
from loom.scan.alloc import visible_locals
from loom.scan.labels import next_local, split_id
from loom.scan.quilt import load_quilt
from loom.scan.scan import ScanResult, scan
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
@click.argument("canon")
@click.option("--to", "to", default=None, metavar="FILE", help="The draft to write (default: <drafting>/<stem>.tex).")
@click.option("--no-ids", "no_ids", is_flag=True, help="Copy without inserting ids.")
@click.option(
    "--fix-anchoring",
    "fix_anchors",
    is_flag=True,
    help="Rewrite the copy so every theorem-like \\begin and \\end is alone on its line.",
)
@click.option("--prefix", default=None, help="Id prefix for the ids inserted.")
@click.option("--no-check", "no_check", is_flag=True, help="Skip the identity test.")
@click.option("--yes", "-y", is_flag=True)
@quilt_option
def draft(
    canon: str,
    to: str | None,
    no_ids: bool,
    fix_anchors: bool,
    prefix: str | None,
    no_check: bool,
    yes: bool,
    quilt_path: str | None,
) -> None:
    """Copy a canon document into the drafting directory as a working draft, with \\usepackage{loom} and an id on every node; the canon file is not touched."""
    result = open_scan(quilt_path)
    quilt = result.quilt
    root = quilt.root
    canon_rel = _rel(root, canon)
    if not (root / canon_rel).is_file():
        raise EnvError(f"{canon} is not a file of this quilt")
    if Path(canon_rel).parent.as_posix() != quilt.config.canon:
        raise EnvError(f"{canon_rel} is not a canon document; the canon directory is {quilt.config.canon}/")
    dest_rel = _rel(root, to) if to else f"{quilt.config.drafting}/{Path(canon_rel).name}"
    if Path(dest_rel).parent.as_posix() != quilt.config.drafting:
        raise EnvError(f"a draft goes directly under {quilt.config.drafting}/, not at {dest_rel}")
    if (root / dest_rel).exists():
        raise EnvError(f"{dest_rel} exists; draft never overwrites")
    history = _history(result)
    plan = plan_draft(result, history, canon_rel, dest_rel, ids=not no_ids, fix_anchors=fix_anchors, prefix=prefix)
    if plan.moved and plan.step is not None:
        note(
            f"loom:canon-edited: {canon_rel} is not the text step {plan.step.step:04d} recorded; drafting from the file as it is"
        )
    if plan.violations:
        note(f"Nothing was written. {canon_rel} has {len(plan.violations)} line-anchoring violation(s):")
        for v in plan.violations[:20]:
            note(f"  line {v.line}: \\{v.kind}{{{v.env}}} is not alone on its line")
        raise ContentError(
            "loom needs a theorem-like \\begin and \\end alone on their lines to find a node's exact span. "
            "Pass --fix-anchoring to rewrite the draft and leave the canon document alone."
        )
    if plan.spans:
        raise ContentError("an environment spans files: " + "; ".join(plan.spans))
    note("Plan, nothing written yet:")
    note(f"  {canon_rel} -> {dest_rel} ({len(plan.insertions)} ids)")
    if plan.diff:
        click.echo(plan.diff, nl=False)
    _confirm(yes, "draft")
    dest = root / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(plan.text, encoding="utf-8")
    note(f"Wrote {dest_rel}")
    if not no_check:
        with tempfile.TemporaryDirectory(prefix="loom-identity-") as tmp:
            ident = identity_test(root, canon_rel, root, dest_rel, Path(tmp), quilt.config.engine)
        note(ident.summary())
        if not ident.passed and not ident.skipped:
            dest.unlink(missing_ok=True)
            raise ContentError(
                f"the draft does not typeset as {canon_rel}; {dest_rel} was removed and nothing was recorded. Pass --no-check to keep it anyway."
            )
    changed = set_main(quilt, dest_rel)
    if changed:
        note(f"main = {dest_rel}")
    after = scan(load_quilt(root))
    note(report_counts(after))
    entry = append_entry(quilt.history_dir, "draft", draft_entry(quilt, plan), actor_for(root))
    note(f"Recorded: draft (ledger line {entry.line})")


# ---- canonize -----------------------------------------------------------------


def _canonize_params(f: Callable[..., Any]) -> Callable[..., Any]:
    decos: list[Any] = [
        click.argument("document"),
        click.option("--to", "to", default=None, metavar="FILE", help="The canon file (default: <canon>/<stem>.tex)."),
        click.option("--message", "-m", "message", required=True, help="What this landmark is."),
        click.option("--no-check", "no_check", is_flag=True, help="Skip the identity test."),
        click.option("--parent", "parent", type=int, default=None, help="The step this one continues."),
        click.option("--json", "as_json", is_flag=True),
        quilt_option,
    ]
    for deco in reversed(decos):
        f = deco(f)
    return f


def _run_canonize(
    document: str,
    to: str | None,
    message: str,
    no_check: bool,
    parent: int | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    result = open_scan(quilt_path)
    quilt = result.quilt
    root = quilt.root
    doc_rel = _rel(root, document)
    if doc_rel not in result.files:
        raise EnvError(f"{document} is not a scanned file of this quilt")
    src = result.files[doc_rel]
    if "\\documentclass" not in src.text:
        raise EnvError(f"{doc_rel} is not a document (no \\documentclass)")
    live = doc_rel in result.masters
    to_rel = _rel(root, to) if to else f"{quilt.config.canon}/{Path(doc_rel).name}"
    if Path(to_rel).parent.as_posix() != quilt.config.canon:
        raise EnvError(f"a canon document goes directly under {quilt.config.canon}/, not at {to_rel}")
    if (root / to_rel).exists():
        raise EnvError(f"{to_rel} exists; canonize never overwrites a landmark")
    conflicted = sorted(k for k, n in result.nodes.items() if n.kind == "conflict" and doc_rel in n.reached_by)
    if conflicted:
        raise ContentError(
            f"{doc_rel} reaches {', '.join(conflicted)}, defined by two files each; a landmark needs one text per key. loom lint --nodes shows them."
        )
    spans = [
        d
        for d in result.lint
        if d.code == "loom:environment-spans-files" and any(loc.file == doc_rel for loc in d.locations)
    ]
    if spans:
        raise ContentError(f"an environment spans files in {doc_rel}; loom lint --nodes shows it")
    if not live:
        why = "superseded" if src.superseded else ("ignored" if src.ignored else "outside the drafting directory")
        note(f"warning: {doc_rel} is {why}; canonizing it anyway, recorded as not live")
    flat = flatten(root, doc_rel)
    text = to_canon(flat.text)
    dest = root / to_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    if not no_check:
        with tempfile.TemporaryDirectory(prefix="loom-identity-") as tmp:
            ident = identity_test(root, doc_rel, root, to_rel, Path(tmp), engine_for(result, doc_rel))
        note(ident.summary())
        if not ident.passed and not ident.skipped:
            dest.unlink(missing_ok=True)
            raise ContentError(
                f"the flat copy does not typeset as {doc_rel}; {to_rel} was removed and nothing was recorded. Pass --no-check to write it anyway."
            )
    history = _history(result)
    plan = plan_freeze(result, history, document=doc_rel)
    declared = parent
    if declared is None:
        for e in reversed(history.entries):
            if e.action == "draft" and (e.get("to") or {}).get("path") == doc_rel:
                step = (e.get("from") or {}).get("step")
                if isinstance(step, int):
                    declared = step
                break
    ancestry = infer_parent(history, plan.current, declared)
    entry = write_step(
        history,
        "canonize",
        Path(to_rel).stem,
        plan,
        actor_for(root),
        extra={
            "message": message,
            "document": doc_rel,
            "live": live,
            "from": {"path": doc_rel, "hash": file_hash(root / doc_rel)},
            "to": {"path": to_rel, "hash": text_hash(text)},
            "inlined": list(flat.inlined),
            "reaches": plan.reaches,
            "parent": ancestry,
        },
        document_text=text,
        document_name=Path(to_rel).name,
    )
    reached_frozen = sum(1 for k in plan.froze if k in plan.reaches)
    elsewhere = len(plan.froze) - reached_frozen
    how = ancestry.get("how", "unknown")
    parent_text = f"parent {ancestry['step']:04d} ({how})" if "step" in ancestry else "parent unknown"
    if as_json:
        emit_json({**entry.to_dict(), "line": entry.line})
    else:
        click.echo(f"Wrote {to_rel} (flat, {text.count(chr(10))} lines)")
        click.echo(
            f"step {entry.step:04d} froze {len(plan.froze)} keys ({reached_frozen} reached by {doc_rel}, {elsewhere} elsewhere), "
            f"{plan.unchanged} unchanged, {parent_text}"
        )
        if plan.skipped:
            note(f"skipped (conflicted): {', '.join(plan.skipped)}")
    note(f"Recorded: canonize as step {entry.step:04d} ({entry.dir})")
    from loom.refs.scan import scan_bibliography

    for line in scan_bibliography(result.quilt).lines():
        note(line)


@click.command()
@_canonize_params
def canonize(
    document: str,
    to: str | None,
    message: str,
    no_check: bool,
    parent: int | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Write DOCUMENT as one flat, self-contained canon file and record a step: every key's text at this moment, quilt-wide, with what the document reaches named."""
    _run_canonize(document, to, message, no_check, parent, as_json, quilt_path)


@click.command(hidden=True)
@_canonize_params
def canonicalize(
    document: str,
    to: str | None,
    message: str,
    no_check: bool,
    parent: int | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """The same as canonize."""
    note("canonicalize → canonize")
    _run_canonize(document, to, message, no_check, parent, as_json, quilt_path)


@click.command(hidden=True)
@_canonize_params
def canonise(
    document: str,
    to: str | None,
    message: str,
    no_check: bool,
    parent: int | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """The same as canonize."""
    note("canonise → canonize")
    _run_canonize(document, to, message, no_check, parent, as_json, quilt_path)


# ---- stamp --------------------------------------------------------------------


@click.command()
@click.option("--message", "-m", "message", required=True, help="What this stamp marks.")
@click.option("--in", "in_doc", default=None, metavar="FILE", help="Only the keys this document reaches.")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def stamp(message: str, in_doc: str | None, as_json: bool, quilt_path: str | None) -> None:
    """Record every key whose text moved since the last step, quilt-wide (or within one document with --in), without writing a canon file."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    narrow = _rel(root, in_doc) if in_doc else None
    if narrow is not None and narrow not in result.masters:
        raise EnvError(f"{in_doc} is not a live document of this quilt")
    history = _history(result)
    plan = plan_freeze(result, history, narrow_to=narrow)
    if not plan.froze and not plan.removed and not plan.restored:
        last = history.next_step() - 1
        raise ContentError(
            f"nothing to stamp: no key has moved since step {last:04d}"
            if last
            else "nothing to stamp: no key has an id"
        )
    entry = write_step(
        history, "stamp", f"stamp-{slug(message)}", plan, actor_for(root), extra={"message": message, "in": narrow}
    )
    if as_json:
        emit_json({**entry.to_dict(), "line": entry.line})
    else:
        click.echo(
            f"step {entry.step:04d} froze {len(plan.froze)} keys"
            + (f", {len(plan.removed)} removed" if plan.removed else "")
            + (f", {len(plan.restored)} restored" if plan.restored else "")
            + (f" (in {narrow})" if narrow else "")
        )
        if plan.skipped:
            note(f"skipped (conflicted): {', '.join(plan.skipped)}")
    note(f"Recorded: stamp as step {entry.step:04d} ({entry.dir})")


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
@click.argument("key", required=False, default=None)
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def history(key: str | None, as_json: bool, quilt_path: str | None) -> None:
    """The steps and stamps of this quilt, one per line; with KEY, that key's versions and whether the head equals one. `loom history verify` walks every step directory against the ledger.

    KEY is an id, a proof key, or the word `verify`.
    """
    if key == "verify":
        _verify(as_json, quilt_path)
        return
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
        click.echo("no history yet: loom canonize or loom stamp records the first step")
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


def _detail(e: Entry) -> str:
    frm, to = e.get("from"), e.get("to")
    if e.action == "draft":
        return f"{(frm or {}).get('path')} -> {(to or {}).get('path')}"
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
