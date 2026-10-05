"""`loom draft`, `loom stamp`, `loom fork`, `loom revert`, `loom live`, `loom mv`, `loom linearize`, `loom history` (book chapter 17).

Usage refusals are EnvError (exit 2), content refusals ContentError (exit 1); every command reports through `loom.cli.report`, a write naming what it wrote and the step it made. Patches are printed for the editor to apply; loom rewrites no author file.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import click

from loom.cli._common import EXIT_CONTENT, ContentError, EnvError, NotFoundError, destination, note, writer
from loom.cli._quilt import open_scan, quilt_option, require_text, resolve_key
from loom.cli.build_cmds import engine_for
from loom.cli.diagnostics import groups as diagnostic_groups
from loom.cli.diagnostics import has_errors, tally
from loom.cli.diagnostics import item as diagnostic_item
from loom.cli.help import CommandGroup
from loom.cli.paper import bibliography_groups, identity_group, identity_said
from loom.cli.report import Group, Item, Progress, Report, counted, table
from loom.history.checks import verify
from loom.history.ledger import Entry, History, Version, actor_for, append_entry, load_history
from loom.history.steps import (
    file_hash,
    plan_document_stamp,
    plan_freeze,
    slug,
    stamp_document,
    text_hash,
    write_step,
)
from loom.history.versions import matching_version, materialize, parse_address, read_version, version_at
from loom.reshape.atomize import _single_node_file
from loom.reshape.canon import plan_draft
from loom.reshape.fork import _relabel, _rewrite_refs, plan_fork
from loom.reshape.ids import unified_diff
from loom.reshape.importer import set_main_forced
from loom.reshape.linearize import flatten, to_canon
from loom.scan.alloc import visible_locals
from loom.scan.labels import LABEL_DEF, next_local, rename_labels, split_id
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
    help="The agent document to write, directly in the agent's drafting directory.",
)
@click.option(
    "--as",
    "declared",
    default=None,
    metavar="NAME",
    help="Who drafts it; an agent names itself, including Agent or AI.",
)
@click.option("--dry-run", is_flag=True, help="Say what would be written, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def draft(
    document: str, ai_name: str, declared: str | None, dry_run: bool, as_json: bool, quilt_path: str | None
) -> None:
    """Draft an agent document NAME from a live working document: flat, in the agent's drafting directory, with every label it defines derived.

    A copy step records what each of its nodes began from (book 17.7), and who drafted it: `--as`, else the configured author; an agent that has not named itself is refused. Starting a document from an old version of one is `loom history restore`.
    """
    _draft_ai(open_scan(quilt_path), document, ai_name, declared, dry_run, as_json)


def _draft_ai(result: ScanResult, source: str, name: str, declared: str | None, dry_run: bool, as_json: bool) -> None:
    """`loom draft SOURCE --ai NAME`: one agent document per working document, never over an existing file or a taken name."""
    from loom.reshape.copy import plan_copy

    quilt = result.quilt
    root = quilt.root
    actor = writer(root, declared)[0] or None
    source_rel = _rel(root, source)
    role = result.document_role(source_rel)
    if role != "drafting":
        if role:
            raise EnvError(
                f"{source_rel} is an agent document; an agent document is drafted from one in {quilt.config.drafting}/"
            )
        raise NotFoundError("document", f"{source_rel} is not a live document in {quilt.config.drafting}/")
    dest_rel = name if "/" in name else f"{quilt.config.drafting_ai}/{name}"
    if not dest_rel.endswith(".tex"):
        dest_rel += ".tex"
    if Path(dest_rel).parent.as_posix() != quilt.config.drafting_ai:
        raise EnvError(f"an agent document goes directly under {quilt.config.drafting_ai}/, not at {dest_rel}")
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
        raise EnvError(f"{source_rel} already has an agent document, {existing[0]}; an agent works in that one")
    conflicted = sorted(k for k, n in result.nodes.items() if n.kind == "conflict" and source_rel in n.reached_by)
    if conflicted:
        raise ContentError(
            f"{source_rel} reaches {', '.join(conflicted)}, defined by two files each; an agent document needs one text per key"
        )
    plan = plan_copy(result, history, source_rel, dest_rel)

    def detail(step: int) -> list[str]:
        kept = counted(len(plan.freeze.froze), "result")
        return [
            f"{counted(len(plan.labels), 'label')} derived, {counted(len(plan.bases), 'result')} based on {source_rel}"
            + (f"; step {step:04d} keeps the text of {kept} they start from" if plan.freeze.froze else "")
        ]

    if dry_run:
        step = history.next_step()
        Report(
            f"would write {dest_rel}, an agent document drafted from {source_rel}, and record it as step {step:04d}",
            dry_run=True,
            lines=detail(step),
            data={"action": "copy", "step": step, "from": source_rel, "to": dest_rel, "bases": plan.bases},
        ).emit(as_json)
        return
    dest = root / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(plan.text, encoding="utf-8")
    entry = write_step(
        history,
        "copy",
        f"copy-{Path(dest_rel).stem}",
        plan.freeze,
        actor,
        extra={"from": source_rel, "to": dest_rel, "bases": plan.bases},
        document_text=plan.source_text,
        document_name=Path(source_rel).name,
    )
    Report(
        f"wrote {dest_rel}, an agent document drafted from {source_rel}; step {entry.step:04d} records it",
        lines=detail(entry.step or 0),
        data={**entry.to_dict(), "line": entry.line},
    ).emit(as_json)


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
@click.option("--dry-run", is_flag=True, help="Say what the step would record, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def stamp(document: str | None, message: str, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Record every key whose text moved since the last step, quilt-wide; given DOCUMENT, only the keys it reaches, and its flat text kept as a landmark.

    A landmark is how a document stood at a moment worth returning to: `loom history show NAME` prints it and `loom history restore NAME --to FILE` starts a document from it (book 17.9).
    """
    result = open_scan(quilt_path)
    root = result.quilt.root
    history = _history(result)
    doc = _rel(root, document) if document else None
    if doc is not None and result.document_role(doc) != "drafting":
        raise NotFoundError("document", f"{document} is not a live document in {result.quilt.config.drafting}/")
    name = slug(message)
    if doc is not None:
        if history.landmark(name) is not None:
            raise EnvError(f"a landmark is already named {name}; name this one differently")
        try:
            if dry_run:
                plan, _ = plan_document_stamp(result, history, doc)
            else:
                entry, plan = stamp_document(result, history, doc, name, message, actor_for(root))
        except ValueError as exc:
            raise ContentError(str(exc)) from exc
    else:
        plan = plan_freeze(result, history)
        if not plan.froze and not plan.removed and not plan.restored:
            last = history.next_step() - 1
            Report(
                f"nothing to stamp: no result has changed since step {last:04d}"
                if last
                else "nothing to stamp: no result has an id",
                dry_run=dry_run,
                data={"step": None},
            ).emit(as_json)
            return
    if dry_run:
        step = history.next_step()
        data: dict[str, Any] = {
            "action": "stamp",
            "step": step,
            "message": message,
            "in": doc,
            "froze": sorted(plan.froze),
            "removed": list(plan.removed),
            "restored": list(plan.restored),
        }
    else:
        if doc is None:
            entry = write_step(
                history, "stamp", f"stamp-{name}", plan, actor_for(root), extra={"message": message, "in": None}
            )
        step, data = entry.step or 0, {**entry.to_dict(), "line": entry.line}
    changed = ", ".join(
        part
        for part in (
            f"a new version of {counted(len(plan.froze), 'result')}" if plan.froze else "",
            f"{counted(len(plan.removed), 'result')} removed" if plan.removed else "",
            f"{counted(len(plan.restored), 'result')} restored" if plan.restored else "",
        )
        if part
    )
    groups = []
    if plan.skipped:
        groups.append(
            Group(
                "not recorded, each defined by two files and so with no text",
                [Item("", key=k) for k in sorted(plan.skipped)],
                problem=True,
                next="loom lint",
            )
        )
    if doc is not None and not dry_run:
        # a landmark is what the quilt's bibliography is gathered from, so a new one may carry entries it lacks (book 8.15)
        bib_groups, data["bibliography"] = bibliography_groups(result.quilt)
        groups += bib_groups
    Report(
        f"step {step:04d} {'would record' if dry_run else 'records'} "
        + (changed or "no changed result")
        + (f"; landmark {name} {'would keep' if dry_run else 'keeps'} {doc} as it stands" if doc else ""),
        ok=not plan.skipped,
        dry_run=dry_run,
        groups=groups,
        data=data,
    ).emit(as_json)


# ---- fork ---------------------------------------------------------------------


class StepType(click.ParamType[int]):
    """A step of the history, `@N` or `N`, as its number; anything else is refused by name before the command runs."""

    name = "@N"

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> int:
        if isinstance(value, int):
            return value
        digits = str(value).strip().removeprefix("@")
        if digits.isdigit() and int(digits) > 0:
            return int(digits)
        # an EnvError, not click's usage error, so the refusal reads as every other one does
        raise EnvError(f"--from {value} is not a step; write @N, the step's number, e.g. @3")


@click.command()
@click.argument("node_id")
@click.option("--in", "in_doc", required=True, metavar="FILE", help="The document that gets its own copy.")
@click.option(
    "--from",
    "at",
    type=StepType(),
    default=None,
    metavar="@N",
    help="Copy the text the key had at step N instead of the head.",
)
@click.option("--name", "new_id", default=None, metavar="ID", help="The new id (default: the next free one).")
@click.option("--dry-run", is_flag=True, help="Print the plan and the patch, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def fork(
    node_id: str,
    in_doc: str,
    at: int | None,
    new_id: str | None,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Give FILE its own copy of a node under a new id: a node file when FILE includes the node, else the copy inline.

    The copy is printed as a patch for FILE, with its references rewritten; nothing outside FILE changes.
    """
    result = open_scan(quilt_path)
    root = result.quilt.root
    doc_rel = _rel(root, in_doc)
    key = node_id
    if key not in result.nodes:
        key = resolve_key(result, node_id)
    n = result.nodes[key]
    if n.kind not in ("environment", "conflict") or not n.id:
        raise EnvError(f"{node_id} is not a statement with an id")
    if doc_rel not in result.files:
        raise NotFoundError("document", f"{in_doc} is not a scanned file of this quilt")
    if new_id is not None and split_id(new_id) is None:
        raise EnvError(f"{new_id} is not an id; an id is PREFIX-XXXX, e.g. {result.quilt.config.prefix}-0100")
    history = _history(result)
    if at is not None and history.resolve_step(str(at)) is None:
        raise NotFoundError("step", f"no step {at} in the history; loom history lists them")
    plan = plan_fork(result, history, n.id, doc_rel, str(at) if at is not None else None, new_id)
    if plan.refusal:
        raise ContentError(plan.refusal)
    target = root / plan.node_file if plan.node_file else None
    if target is not None and target.exists():
        raise ContentError(f"{plan.node_file} exists")
    elsewhere = Group(
        f"still referring to {plan.node_id}, which may be what you want",
        [Item(counted(count, "reference"), key=f) for f, count in sorted(plan.elsewhere.items())],
    )
    data = {
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
    where = f", in {plan.node_file}" if plan.node_file else ""
    if dry_run:
        verdict = f"would fork {plan.node_id} as {plan.new_id} for {plan.doc}{where}, with this patch for {plan.doc}"
    else:
        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(plan.node_text, encoding="utf-8")
        append_entry(
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
        verdict = f"forked {plan.node_id} as {plan.new_id} for {plan.doc}{where}; apply this patch to {plan.doc}, which loom never edits"
    report = Report(verdict, ok=dry_run, dry_run=dry_run, groups=[elsewhere] if plan.elsewhere else [], data=data)
    if as_json:
        report.emit(True)
        return
    report.emit()
    click.echo("")
    click.echo(plan.diff, nl=False)


# ---- revert -------------------------------------------------------------------


@click.command()
@click.argument("address")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def revert(address: str, as_json: bool, quilt_path: str | None) -> None:
    """Print the patch that puts KEY@N's recorded text back in place of the head's; the file is the author's to change. Reverting materializes a version, it never points at one."""
    result = open_scan(quilt_path)
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
        if version_at(history, key, ref) is None:
            raise NotFoundError("version", str(exc)) from exc
        raise ContentError(str(exc)) from exc
    src = result.files[n.file].text
    patched = src[: n.start] + body.rstrip("\n") + src[n.end :]
    diff = unified_diff(src, patched, n.file)
    # Nothing is recorded: applying the patch is the author's act (17.11), and whether the head is again @N is read from its text, never from a note that a patch was once printed.
    if as_json or not diff:
        Report(
            f"the patch gives {key} the text of @{v.step} ({v.name}) again, once applied to {n.file}"
            if diff
            else f"{key} already has the text of @{v.step}; nothing to apply",
            data={"key": key, "step": v.step, "hash": v.hash, "file": n.file, "diff": diff, "patched": patched},
        ).emit(as_json)
        return
    click.echo(diff, nl=False)
    note(f"Apply the patch to {n.file} and {key} has the text of @{v.step} ({v.name}) again.")


# ---- live ---------------------------------------------------------------------


def _scan_after(result: ScanResult, action: str, data: dict[str, Any]) -> ScanResult:
    """The scan the quilt would give with one more ledger line, read from a copy of the quilt; how a dry run tells what a record would change.

    Paths and keys in the result are quilt-relative, so they read as the quilt's own; the copy is gone once this returns, so nothing may be read from disk through it.
    """
    root = result.quilt.root
    with tempfile.TemporaryDirectory(prefix="loom-dry-run-") as tmp:
        copy = Path(tmp) / "quilt"
        shutil.copytree(root, copy, ignore=shutil.ignore_patterns("build", ".git"), symlinks=True)
        quilt = load_quilt(copy)
        append_entry(quilt.history_dir, action, data, None)
        return scan(quilt)


@click.command()
@click.argument("file")
@click.option("--dry-run", is_flag=True, help="Say what making it live would define twice, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def live(file: str, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Make a superseded document live again, so that it defines its nodes once more."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    rel = _rel(root, file)
    history = _history(result)
    if rel not in history.superseded_paths():
        if rel not in result.files:
            raise NotFoundError("document", f"{file} is not a file of this quilt")
        raise EnvError(f"{rel} is not superseded")
    before = {k for k, n in result.nodes.items() if n.kind == "conflict"}
    if dry_run:
        now = _scan_after(result, "live", {"path": rel})
        data: dict[str, Any] = {"action": "live", "path": rel}
    else:
        entry = append_entry(result.quilt.history_dir, "live", {"path": rel}, actor_for(root))
        now = scan(load_quilt(root))
        data = {**entry.to_dict(), "line": entry.line}
    # A live document defines its nodes again, so any id another live file also defines has no text from now on: said here, since it is this command that made it so.
    made = sorted(k for k, n in now.nodes.items() if n.kind == "conflict" and k not in before and rel in n.conflict)
    items = [
        Item(
            "also in " + " and ".join(f for f in now.nodes[key].conflict if f != rel),
            key=key,
            fixes=[f"loom fork {key} --in {rel}"],
        )
        for key in made
    ]
    became = "would be" if dry_run else "is"
    Report(
        f"{rel} {became} live, and {counted(len(made), 'id')} it defines {'would be' if dry_run else 'is now' if len(made) == 1 else 'are now'} defined twice, with no text until one definition goes"
        if made
        else f"{rel} {became} live",
        ok=not made,
        dry_run=dry_run,
        groups=[Group("defined twice", items, problem=True)] if made else [],
        data={**data, "conflicted": made},
    ).emit(as_json)


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
@click.option("--dry-run", is_flag=True, help="Say what would be moved and recorded, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def mv(old: str, new: str, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
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
        raise NotFoundError(
            "document",
            f"neither {old_rel} nor {new_rel} exists: there is nothing to move and no rename to record",
        )
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
    main = result.quilt.config.main
    follows = main == old_rel or result.current_document(main) == old_rel
    record = {"from": old_rel, "to": new_rel, "moved": moved}
    if dry_run:
        main_moved = follows and main != new_rel
        data: dict[str, Any] = {"action": "move", **record}
    else:
        if moved:
            shutil.move(str(root / old_rel), str(root / new_rel))
        entry = append_entry(result.quilt.history_dir, "move", record, actor_for(root))
        main_moved = follows and set_main_forced(result.quilt, new_rel)
        data = {**entry.to_dict(), "line": entry.line}
    if dry_run:
        said = (
            f"would move {old_rel} to {new_rel}"
            if moved
            else f"would record that {old_rel} was renamed to {new_rel} outside loom"
        )
    else:
        said = f"moved {old_rel} to {new_rel}" if moved else f"{old_rel} was renamed to {new_rel} outside loom"
    Report(
        said + ("; every record naming it would follow" if dry_run else "; every record naming it follows"),
        dry_run=dry_run,
        lines=[f"config.toml: main = {new_rel}"] if main_moved else [],
        data=data,
    ).emit(as_json)


# ---- linearize ----------------------------------------------------------------


@click.command()
@click.argument("spine")
@click.option("--to", "to", required=True, metavar="FILE", help="The flat document to write.")
@click.option(
    "--fork", "do_fork", is_flag=True, help="Give this document its own copy of every node another document shares."
)
@click.option("--keep-shared", "keep_shared", is_flag=True, help="Leave shared node files as inclusions, marked.")
@click.option("--no-check", "no_check", is_flag=True, help="Skip the identity test.")
@click.option(
    "--dry-run", is_flag=True, help="Say what would be written and superseded, and write nothing; no identity test."
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def linearize(
    spine: str,
    to: str,
    do_fork: bool,
    keep_shared: bool,
    no_check: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Write FILE, SPINE with every \\input, \\include and \\nest (levels shifted) expanded in place; the spine and every file it inlined are then superseded."""
    with Progress("scanning") as progress:
        report = _linearize(progress, spine, to, do_fork, keep_shared, no_check, dry_run, quilt_path)
    report.emit(as_json)


def _linearize(
    progress: Progress,
    spine: str,
    to: str,
    do_fork: bool,
    keep_shared: bool,
    no_check: bool,
    dry_run: bool,
    quilt_path: str | None,
) -> Report:
    """`loom linearize`'s work, its report returned for the caller to print once the progress line is gone."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    spine_rel = _rel(root, spine)
    if spine_rel not in result.files:
        raise NotFoundError("file", f"{spine} is not a scanned file of this quilt")
    progress.next_stage("flattening")
    to_rel = destination(result.quilt, to, drafting=True).relative_to(root.resolve()).as_posix()
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
        renames: list[tuple[set[str], str, dict[str, str]]] = []
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
            inner = _inner_labels(body, names | {new_id}, new_id)
            stem = f[: -len(".tex")]
            pat = re.compile(r"^([ \t]*)\\(input|nest)\{(" + re.escape(stem) + "|" + re.escape(f) + r")\}[ \t]*$", re.M)

            def repl(m: re.Match[str], body: str = body) -> str:
                b = shift_sectioning(body, 1) if m.group(2) == "nest" else body
                return b.rstrip("\n")

            text = pat.sub(repl, text)
            renames.append((names, new_id, inner))
            forks.append({"new": new_id, "from": {"id": node.id, "hash": file_hash(root / f)}, "file": f})
        # once every copy is in, so a forked node's reference to another forked node follows it too
        for names, new_id, inner in renames:
            text = rename_labels(_rewrite_refs(text, names, new_id), inner)
    forked = {fk["file"] for fk in forks}
    kept = [f for f in flat.kept if f not in forked]
    superseded = [spine_rel, *[f for f in flat.inlined if f in result.files]]
    record = {"from": spine_rel, "to": to_rel, "superseded": superseded, "forks": forks, "kept": kept}
    groups = []
    if forks:
        groups.append(
            Group(
                "forked, so this document has its own copy",
                [Item(f"{fk['from']['id']} -> {fk['new']}", key=fk["file"]) for fk in forks],
            )
        )
    if kept:
        groups.append(Group("kept as inclusions, shared with another document", [Item(f) for f in sorted(kept)]))
    groups.append(
        Group(
            ("would be " if dry_run else "") + "superseded: each defines nothing until loom live FILE says otherwise",
            [Item(f) for f in superseded],
        )
    )
    shape = f"{spine_rel} flat: {text.count(chr(10))} lines, {counted(len(flat.inlined), 'file')} inlined"
    main = result.quilt.config.main
    if dry_run:
        return Report(
            f"would write {to_rel}, {shape}; the identity test runs when it is written",
            dry_run=True,
            lines=[f"config.toml: main = {to_rel}"] if main in superseded and main != to_rel else [],
            groups=groups,
            data={"action": "linearize", **record},
        )
    dest = root / to_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    checked = (
        "not compared with it, as --no-check asked"
        if no_check
        else f"not compared with it: {spine_rel} is not a document"
    )
    if not no_check and spine_rel in result.masters:
        progress.next_stage(f"identity test: compiling {spine_rel} and {to_rel}")
        with tempfile.TemporaryDirectory(prefix="loom-identity-") as tmp:
            ident = identity_test(root, spine_rel, root, to_rel, Path(tmp), engine_for(result, spine_rel))
        if not ident.passed and not ident.skipped:
            dest.unlink(missing_ok=True)
            diffs = "\n".join(f"  {i.text}" + (f"  {i.key}" if i.key else "") for i in identity_group(ident)[0].items)
            raise ContentError(
                f"the flat copy does not typeset as {spine_rel}; {to_rel} was removed and nothing was recorded. Pass --no-check to write it anyway.\n"
                + diffs
            )
        checked = identity_said(ident, "it", spine_rel)
    entry = append_entry(result.quilt.history_dir, "linearize", record, actor_for(root))
    main_moved = main in superseded and set_main_forced(result.quilt, to_rel)
    progress.next_stage(f"scanning with {to_rel}")
    had = {(d.code, d.message) for d in result.lint if d.severity == "error"}
    brought = [d for d in scan(load_quilt(root)).lint if d.severity == "error" and (d.code, d.message) not in had]
    if brought:
        groups.insert(
            0,
            Group(
                f"errors {spine_rel} did not have",
                [diagnostic_item(d) for d in brought],
                problem=True,
                next="loom lint",
            ),
        )
    return Report(
        f"wrote {to_rel}, {shape}; {checked}"
        + (f"; it has {counted(len(brought), 'error')} {spine_rel} did not have" if brought else ""),
        ok=not brought,
        exit=EXIT_CONTENT if brought else 0,
        lines=[f"config.toml: main = {to_rel}"] if main_moved else [],
        groups=groups,
        data={**entry.to_dict(), "line": entry.line, "errors": [d.to_dict() for d in brought]},
    )


def _inner_labels(body: str, own: set[str], new_id: str) -> dict[str, str]:
    """Every other label a forked node's text defines, each given the new id after it (`eq:fix` -> `eq:fix-dm-0012`).

    Labels are claimed quilt-wide, so a fork that kept them would define each twice while the original stays live; `own` is the node's id and aliases, which `_relabel` has already handled.
    """
    return {m.group(2): f"{m.group(2)}-{new_id}" for m in LABEL_DEF.finditer(body) if m.group(2) not in own}


# ---- history ------------------------------------------------------------------


def _version_lines(result: ScanResult, history: History, key: str) -> tuple[list[Version], Version | None, str]:
    versions = history.versions_of(key)
    n = result.nodes.get(key)
    head_hash = ""
    if n is not None and n.kind in ("environment", "proof"):
        from loom.render.manifest import key_hash

        head_hash = key_hash(result, key)
    return versions, matching_version(history, key, head_hash) if head_hash else None, head_hash


class _HistoryGroup(CommandGroup):
    """`loom history`: a word that names no subcommand is a KEY, whose versions the hidden `_versions` command lists.

    Asked for help, a word that is no key either is refused with the nearest command, so a typo never gets help of its own.
    """

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            if any(a in ("--help", "-h") for a in args[1:]) and not _is_key(ctx, args[0]):
                import difflib

                close = difflib.get_close_matches(args[0], list(self.commands), n=1)
                raise EnvError(
                    f"no such command or key: {args[0]}"
                    + (f"; did you mean {close[0]}?" if close else "; loom history --help lists the commands")
                )
            return args[0], _versions, args[1:]
        return super().resolve_command(ctx, args)


def _is_key(ctx: click.Context, word: str) -> bool:
    """Whether `word` names a key of the quilt `history` runs in; False outside a quilt."""
    try:
        resolve_key(open_scan(ctx.params.get("quilt_path")), word)
    except click.ClickException:
        return False
    return True


def _inherited(quilt_path: str | None, as_json: bool) -> tuple[str | None, bool]:
    """`--quilt` and `--json` given before the subcommand (`loom history --json show v1`) count as given after it."""
    parent = click.get_current_context().parent
    given = parent.params if parent is not None else {}
    return quilt_path or given.get("quilt_path"), as_json or bool(given.get("as_json"))


@click.group(cls=_HistoryGroup, invoke_without_command=True, subcommand_metavar="[KEY | COMMAND [ARGS]...]")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
@click.pass_context
def history(ctx: click.Context, as_json: bool, quilt_path: str | None) -> None:
    """List the steps and stamps of this quilt, one per line; `loom history KEY` lists that key's versions and whether the head equals one.

    A landmark, which `show` prints and `restore` starts a document from, is named by its name, its step, or `DOC@STEP` (book 17.9).
    """
    if ctx.invoked_subcommand is not None:
        return
    result = open_scan(quilt_path)
    hist = _history(result)
    steps = [e for e in hist.entries if e.step is not None]
    rows = []
    for e in hist.entries:
        when = e.when[:10]
        if e.step is not None:
            what = e.name + (f' "{e.message}"' if e.message else "")
            what += f"; {counted(len(e.get('froze') or {}), 'version')}"
            if e.get("removed"):
                what += f", {len(e.get('removed'))} removed"
            rows.append((f"{e.step:04d}", e.action, when, what))
        else:
            rows.append(("", e.action, when, _detail(e)))
    Report(
        f"{counted(len(steps), 'step')} and {counted(len(hist.entries) - len(steps), 'other record')} in the history"
        if hist.entries
        else "no history yet: loom stamp records the first step",
        lines=table(rows),
        data={"entries": [{**e.to_dict(), "line": e.line} for e in hist.entries]},
    ).emit(as_json)


@click.command(name="KEY", hidden=True)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def _versions(as_json: bool, quilt_path: str | None) -> None:
    """List the versions recorded for KEY, and whether its text now is one of them."""
    quilt_path, as_json = _inherited(quilt_path, as_json)
    key = click.get_current_context().info_name or ""
    result = open_scan(quilt_path)
    hist = _history(result)
    k = resolve_key(result, key)
    versions, match, head_hash = _version_lines(result, hist, k)
    head = ""
    groups = []
    if head_hash:
        head = f"; its text now is that of @{match.step}" if match else "; its text now differs from every version"
        if versions and not match:
            last = versions[-1].step
            groups.append(
                Group(
                    "to make its text a version again",
                    [
                        Item("record the text now as a new version", fixes=['loom stamp -m "…"']),
                        Item(f"or put the text of @{last} back", fixes=[f"loom revert {k}@{last}"]),
                    ],
                    counted=False,
                )
            )
    Report(
        f"{k} has {counted(len(versions), 'recorded version')}{head}" if versions else f"{k} has no recorded version",
        groups=groups,
        lines=table((f"{k}@{v.step}", v.name, f"of {v.of}" if v.of else "") for v in versions),
        data={
            "key": k,
            "versions": [{"step": v.step, "hash": v.hash, "name": v.name, "of": v.of} for v in versions],
            "head": head_hash or None,
            "head_is": match.step if match else None,
        },
    ).emit(as_json)


def _landmark(quilt_path: str | None, ref: str) -> tuple[ScanResult, History, Entry, str]:
    """The scan, the history, the landmark `ref` names and its text; NotFoundError naming the landmarks there are."""
    result = open_scan(quilt_path)
    hist = _history(result)
    e = hist.landmark(ref)
    if e is None:
        names = ", ".join(f"{Path(str(x.get('landmark'))).stem} (@{x.step})" for x in hist.landmarks()) or "none yet"
        raise NotFoundError("landmark", f"no landmark answers to {ref}; the landmarks are {names}")
    path = hist.landmark_path(e)
    if not path.is_file():
        raise ContentError(f"the text of landmark {ref} is missing: {path.relative_to(result.quilt.root)}")
    return result, hist, e, path.read_text(encoding="utf-8")


@history.command(name="show")
@click.argument("name")
@click.option("--plain", is_flag=True, help="The paper without loom, its package line swapped for the macro block.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def history_show(name: str, plain: bool, as_json: bool, quilt_path: str | None) -> None:
    """Print a landmark's text.

    The text of the landmark NAME as its step kept it, raw; with --plain, the paper without loom.
    """
    quilt_path, as_json = _inherited(quilt_path, as_json)
    _, _, e, text = _landmark(quilt_path, name)
    text = to_canon(text) if plain else text
    if as_json:
        stem = Path(str(e.get("landmark"))).stem
        Report(
            f"landmark {stem}, step {e.step:04d}" + (", without loom" if plain else ""),
            data={"landmark": stem, "step": e.step, "in": e.get("in"), "text": text},
        ).emit(True)
        return
    click.echo(text, nl=False)


@history.command(name="restore")
@click.argument("name")
@click.option("--to", "to", default=None, metavar="FILE", help="The new document, directly in the drafting directory.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def history_restore(name: str, to: str | None, as_json: bool, quilt_path: str | None) -> None:
    """Start a document from a landmark.

    A new drafting document from the landmark NAME, with the package line and an id on every node that has none; the author's alone.
    """
    from loom.cli._common import refuse_under_agent

    quilt_path, as_json = _inherited(quilt_path, as_json)
    refuse_under_agent("loom history restore", "Ask the author to start the document.")
    if to is None:
        raise EnvError("loom history restore needs --to FILE, the new document")
    result, hist, e, text = _landmark(quilt_path, name)
    quilt = result.quilt
    root = quilt.root
    dest = destination(quilt, to, drafting=True)
    dest_rel = dest.relative_to(Path(root).resolve()).as_posix()
    if Path(dest_rel).parent.as_posix() != quilt.config.drafting:
        raise EnvError(f"a restored document goes directly under {quilt.config.drafting}/, not at {dest_rel}")
    plan = plan_draft(result, text, dest_rel)
    if plan.violations or plan.spans:
        raise ContentError(
            f"landmark {name} cannot be drafted as it is: "
            + "; ".join(plan.spans or [f"line {v.line}" for v in plan.violations])
        )
    dest.write_text(plan.text, encoding="utf-8")
    stem = Path(str(e.get("landmark"))).stem
    entry = append_entry(
        quilt.history_dir,
        "restore",
        {
            "from": {"landmark": stem, "step": e.step},
            "to": {"path": dest_rel, "hash": text_hash(plan.text)},
            "ids": len(plan.insertions),
        },
        actor_for(root),
    )
    twice = sorted(
        k for k, n in scan(load_quilt(root)).nodes.items() if n.kind == "conflict" and dest_rel in n.conflict
    )
    Report(
        f"wrote {dest_rel} from landmark {stem} (@{e.step}), {counted(len(plan.insertions), 'id')} inserted"
        + (f"; {counted(len(twice), 'id')} it defines another live document also defines" if twice else ""),
        ok=not twice,
        groups=[
            Group(
                "defined twice, with no text until loom fork or retiring one document resolves each",
                [Item("", key=k, fixes=[f"loom fork {k} --in {dest_rel}"]) for k in twice],
                problem=True,
            )
        ]
        if twice
        else [],
        data={**entry.to_dict(), "line": entry.line},
    ).emit(as_json)


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
    if e.action == "adopt":
        return f"{e.get('copy')} incorporated ({len(e.get('taken') or [])} selected nodes); mathematics not accepted"
    if e.action == "refresh":
        return f"{e.get('copy')} updated from its working document"
    if e.action == "copy":
        return f"{frm} -> {to} ({len(e.get('bases') or {})} nodes based)"
    if e.action == "move":
        how = (
            "" if e.get("moved") else (" (renamed in a pull)" if e.get("via") == "sync" else " (renamed outside loom)")
        )
        return f"{frm} -> {to}{how}"
    return ""


@history.command(name="verify")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def history_verify(as_json: bool, quilt_path: str | None) -> None:
    """Check the history against its ledger.

    Every step directory is walked against the ledger: missing or edited version files, preambles, copies, and ancestry that no longer resolves.
    """
    quilt_path, as_json = _inherited(quilt_path, as_json)
    result = open_scan(quilt_path)
    hist = _history(result)
    diags = verify(result, hist)
    steps = hist.steps()
    files = sum(len(e.get("froze") or {}) for e in steps)
    bad = has_errors(diags, result)
    Report(
        f"history: {tally(diags, result)}, in {counted(len(steps), 'step')}"
        if diags
        else f"history verified: {counted(len(steps), 'step')}, {counted(files, 'recorded version')}",
        ok=not bad,
        exit=EXIT_CONTENT if bad else 0,
        groups=diagnostic_groups(diags, result, cited_next="loom history verify --json"),
        data={"diagnostics": [d.to_dict() for d in diags]},
    ).emit(as_json)
