"""`loom id`, `loom import`, `loom atomize`, `loom deloom` (book 6, 12.3) and the identity test they share."""

from __future__ import annotations

import shlex
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click

from loom.cli._common import EXIT_CONTENT, ContentError, EnvError, NotFoundError, destination, note
from loom.cli._quilt import open_quilt, open_scan, quilt_option
from loom.cli.build_cmds import engine_for, log_run
from loom.cli.report import Group, Item, Progress, Report, counted
from loom.history.ledger import actor_for, append_entry, load_history
from loom.history.steps import FreezePlan, text_hash, write_step
from loom.reshape.anchoring import anchoring_violations
from loom.reshape.anchoring import fix_anchoring as repair_anchoring
from loom.reshape.atomize import plan_atomize, plan_payload, verify_plan, write_atomize, write_moves
from loom.reshape.canon import apply_import, plan_import
from loom.reshape.ids import apply_insertions, plan_insertions, unified_diff
from loom.reshape.importer import set_main, set_main_forced
from loom.scan.alloc import visible_locals
from loom.scan.labels import PREFIX, next_local
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult, scan
from loom.tex.identity import IdentityResult, identity_test


def identity_said(ident: IdentityResult | None, after: str, before: str) -> str:
    """The identity test's outcome in a clause: `X typesets as Y`, or why it was not compared, or that it differs."""
    if ident is None:
        return f"{after} was not compared with {before}: no document includes it"
    if ident.skipped:
        return f"{after} was not compared with {before}: {ident.skipped}"
    if ident.passed:
        return f"{after} typesets to the same text as {before}"
    return f"{after} does not typeset as {before}"


def identity_group(ident: IdentityResult | None) -> list[Group]:
    """Where a failed identity test found the two typeset texts apart: the first differing line and every label whose number moved."""
    if ident is None or ident.passed or ident.skipped:
        return []
    items = []
    if ident.first_difference:
        a, b = ident.first_difference
        items += [Item(f"before: {a[:80]}"), Item(f"after:  {b[:80]}")]
    items += [Item(f"{x} -> {y}", key=lab) for lab, (x, y) in sorted(ident.changed_numbers.items())]
    return [Group("where the typeset text differs", items, problem=True)]


def bibliography_groups(quilt: Quilt) -> tuple[list[Group], dict[str, Any]]:
    """The bibliography scan a landmark triggers, as groups for the report of the command that made the landmark, and its JSON."""
    from loom.refs.scan import scan_bibliography

    bib = scan_bibliography(quilt).report()
    head = Group("bibliography", [Item(bib.verdict), *(Item(line) for line in bib.lines)], limit=None, counted=False)
    rest = [
        Group(f"bibliography, {g.heading}", g.items, count=g.count, limit=g.limit, next=g.next, problem=g.problem)
        for g in bib.groups
    ]
    return [head, *rest], bib.to_json()


def check_prefix(ctx: click.Context, param: click.Parameter, value: str | None) -> str | None:
    """A `--prefix` that the id grammar accepts: letters and digits, no hyphen; refused before the command runs."""
    if value is not None and not PREFIX.match(value):
        raise EnvError(f"--prefix {value!r} is not an id prefix: letters and digits, without hyphens")
    return value


def quilt_relative(quilt: Quilt, path: Path) -> str:
    """`path` as the quilt root names it, or as given when it lies outside the quilt; for what a `--to` wrote."""
    root = Path(quilt.root).resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)


@click.command(name="id")
@click.argument("file", required=False, default=None)
@click.option(
    "--to",
    "to",
    default=None,
    metavar="FILE",
    help="Write the patched copy here instead of printing a diff; never among the quilt's sources.",
)
@click.option("--sections/--no-sections", default=True, help="Also label sections through subsubsection (default on).")
@click.option("--all-levels", is_flag=True, help="Also label paragraphs and subparagraphs.")
@click.option("--prefix", default=None, callback=check_prefix, help="The id prefix (default: the quilt's).")
@click.option("--fix-anchoring", is_flag=True, help="Include line-anchoring repairs in the patch or written copy.")
@click.option("--next", "next_only", is_flag=True, help="Print the next free id and nothing else; inserts nothing.")
@click.option("--json", "as_json", is_flag=True, help="With --next: print it as JSON.")
@click.option(
    "--session", "run_dir", default=None, metavar="SESSION", envvar="LOOM_SESSION", help="Log this call to the session."
)
@quilt_option
def id_command(
    file: str | None,
    to: str | None,
    sections: bool,
    all_levels: bool,
    prefix: str | None,
    fix_anchoring: bool,
    next_only: bool,
    as_json: bool,
    run_dir: str | None,
    quilt_path: str | None,
) -> None:
    """Print a patch inserting \\label{<id>} on every untagged theorem-like environment and section in FILE, or write the patched copy with --to; with --next, print the next free id.

    FILE is never modified.
    """
    result = open_scan(quilt_path)
    root = result.quilt.root
    pre = prefix or result.quilt.config.prefix
    if next_only:
        if fix_anchoring:
            raise EnvError("--fix-anchoring requires a FILE; it cannot be used with --next")
        log_run(run_dir, "loom id --next", root)
        allocated = f"{pre}-{next_local(visible_locals(result, pre))}"
        Report(allocated, data={"id": allocated, "prefix": pre}).emit(as_json)
        return
    if as_json:
        raise EnvError("--json applies to --next; a file's labels are printed as a diff")
    if file is None:
        raise EnvError("name a file to label, or pass --next for the next free id")
    rel = _rel(root, file)
    if rel not in result.files:
        raise NotFoundError("file", f"{file} is not a scanned file of this quilt")
    out = destination(result.quilt, to) if to else None
    log_run(run_dir, f"loom id {file}", root)
    before = result.files[rel].text
    theorem_names = set(result.taxa)
    v = anchoring_violations(before, theorem_names)
    if v and not fix_anchoring:
        lines = [f"  {rel}:{x.line}  \\{x.kind}{{{x.env}}} is not alone on its line" for x in v]
        raise ContentError(
            f"loom:line-anchoring: {counted(len(v), 'line')} of {rel} must be fixed first, or pass --fix-anchoring:\n"
            + "\n".join(lines)
        )
    anchored = repair_anchoring(before, theorem_names) if v else before
    planning = scan(result.quilt, overlay={rel: anchored}) if v else result
    ins = plan_insertions(planning, [rel], pre, next_local(visible_locals(planning, pre)), sections, all_levels)
    after = apply_insertions(anchored, ins)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(after, encoding="utf-8")
        shown = quilt_relative(result.quilt, out)
        Report(f"wrote {shown}: {rel} with {counted(len(ins), 'label')} inserted; {rel} is unchanged").emit()
        return
    if after == before:
        Report(f"nothing to label in {rel}: every node and section in it has an id").emit()
        return
    click.echo(unified_diff(before, after, rel), nl=False)


def _rel(root: Path, file: str) -> str:
    p = Path(file).expanduser()
    p = p if p.is_absolute() else (Path.cwd() / p)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return file


@dataclass
class Imported:
    """What an import did, for the report of `import` or `init --from`: a clause for the verdict, the groups and the data."""

    said: str
    ident: IdentityResult | None
    groups: list[Group] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


def _document_counts(result: ScanResult, doc: str) -> list[Item]:
    """What the drafted document holds, counted in it alone: its results by kind, its sections, its proofs, its broken references."""
    mine = [n for n in result.nodes.values() if n.file == doc or doc in n.reached_by]
    taxa = Counter(n.taxon for n in mine if n.kind == "environment")
    sections = sum(1 for n in mine if n.kind == "section")
    proofs = Counter(n.attach_via for n in mine if n.kind == "proof")
    dangling = sum(1 for d in result.lint if d.code == "dangling-link" and any(loc.file == doc for loc in d.locations))
    items = [
        Item(
            "results: "
            + (", ".join(f"{n} {t}" for t, n in sorted(taxa.items(), key=lambda x: (-x[1], x[0]))) or "none")
            + (f"; {counted(sections, 'section')}" if sections else "")
        ),
        Item(
            "proofs: "
            + (
                f"{sum(proofs.values())}, {proofs.get('adjacent', 0)} beside their statement, "
                f"{proofs.get('ref', 0)} by reference, {proofs.get('enclosure', 0)} by enclosure, "
                f"{proofs.get('none', 0)} unattached"
                if proofs
                else "none"
            )
        ),
    ]
    if dangling:
        items.append(Item(f"{counted(dangling, 'reference')} to a label the paper never defines", fixes=["loom lint"]))
    return items


def run_import(
    quilt: Quilt,
    paper: Path,
    yes: bool,
    check: bool = True,
    fix_anchors: bool = False,
    dry_run: bool = False,
    to: str | None = None,
) -> Imported:
    """The import of 6.1: the assets at the root, the paper as received kept as a landmark named for the working document, and that document drafted from it at once at `to` (default the paper's name in the drafting directory), with the identity test between them.

    Every refusal raises before anything is written; the plan is shown on stderr only when a terminal is asked to confirm it, and is in the refusal when one is not. `dry_run` stops at the plan, which needs no confirmation and writes nothing; the identity test needs the written document, so it does not run.
    """
    from loom.history.steps import slug
    from loom.reshape.canon import plan_draft
    from loom.scan.quilt import load_quilt

    if not paper.is_file():
        raise EnvError(f"{paper} is not a file")
    root = quilt.root
    dest_rel = None
    if to is not None:
        dest_rel = quilt_relative(quilt, destination(quilt, to, drafting=True))
        if Path(dest_rel).parent.as_posix() != quilt.config.drafting:
            raise EnvError(f"{to}: an imported document goes directly in {quilt.config.drafting}/")
    plan = plan_import(quilt, paper, dest_rel)
    if plan.exists:
        stem, n = Path(plan.dest_rel).stem, 2
        while (root / quilt.config.drafting / f"{stem}-{n}.tex").exists():
            n += 1
        raise EnvError(
            f"{plan.dest_rel} exists; import never overwrites a document. Import it under another name: "
            f"loom import {shlex.quote(str(paper))} --to {quilt.config.drafting}/{stem}-{n}.tex"
        )
    arrows = [(Path(src).relative_to(plan.paper_dir).as_posix(), dest) for dest, src in sorted(plan.assets.items())]
    from loom.tex.runner import compile_tex, stage_sources

    ident: IdentityResult | None = None
    with tempfile.TemporaryDirectory(prefix="loom-identity-") as tmp:
        scratch = Path(tmp)
        # a copy without the author's build products: latexmk would otherwise read and rewrite them
        staged = stage_sources(plan.paper_dir, scratch / "original", plan.outside)
        before = compile_tex(staged, plan.master_rel, scratch / "before", quilt.config.engine, halt_on_error=False)
        if not before.ok:
            raise ContentError(
                f"the original does not compile from a clean copy of {plan.paper_dir} ({before.first_error}); fix it before importing"
            )
        draft = plan_draft(scan(quilt), plan.text, plan.dest_rel, fix_anchors=fix_anchors, assets=plan.assets)
        if draft.violations:
            lines = [f"  line {v.line}: \\{v.kind}{{{v.env}}} is not alone on its line" for v in draft.violations[:20]]
            more = len(draft.violations) - len(lines)
            raise ContentError(
                f"nothing was written: {plan.master_rel} has {counted(len(draft.violations), 'line-anchoring violation')}:\n"
                + "\n".join(lines)
                + (f"\n  … and {more} more" if more > 0 else "")
                + "\nloom needs a theorem-like \\begin and \\end alone on their lines to find a result's exact span. "
                "Pass --fix-anchoring to rewrite the draft; the paper as received is kept as it is."
            )
        if draft.spans:
            raise ContentError("an environment spans files: " + "; ".join(draft.spans))
        proposed = [
            f"  {plan.master_rel} -> {plan.dest_rel} (linearized, {len(plan.inlined)} files inlined; kept as received in step 0001)",
            f"  {plan.dest_rel}: \\usepackage{{loom}} and {len(draft.insertions)} ids",
            *(f"  {src} -> {dest}" for src, dest in arrows),
            *(f"  {name} -> not copied; it lies outside the paper directory" for name in plan.outside),
        ]
        if dry_run:
            return Imported(
                f"would import {plan.master_rel} as {plan.dest_rel} with {len(draft.insertions)} ids, "
                f"the paper as received kept as the landmark of step {load_history(quilt.history_dir).next_step():04d}; "
                "the identity test runs when it is written",
                None,
                [Group("would write", [Item(line.strip()) for line in proposed], limit=None)],
                {
                    "document": plan.dest_rel,
                    "from": plan.master_rel,
                    "ids": len(draft.insertions),
                    "written": sorted([plan.dest_rel, *plan.assets]),
                    "inlined": list(plan.inlined),
                    "outside": list(plan.outside),
                },
            )
        if not yes:
            if not sys.stdin.isatty():
                raise EnvError("import needs confirmation; pass --yes. It would write:\n" + "\n".join(proposed))
            note("Nothing written yet; the import would write:\n" + "\n".join(proposed))
            click.confirm("Apply?", abort=True)
        written = apply_import(quilt, plan)
        drafted = root / plan.dest_rel
        drafted.parent.mkdir(parents=True, exist_ok=True)
        drafted.write_text(draft.text, encoding="utf-8")
        written.append(plan.dest_rel)
        if check:
            ident = identity_test(staged, plan.master_rel, root, plan.dest_rel, scratch, quilt.config.engine)
            if not ident.passed and not ident.skipped:
                drafted.unlink(missing_ok=True)
                diffs = "\n".join(
                    f"  {i.text}" + (f"  {i.key}" if i.key else "") for i in identity_group(ident)[0].items
                )
                raise ContentError(
                    f"the drafted document does not typeset as the original; {plan.dest_rel} was removed and nothing was recorded. Pass --no-check to keep it anyway.\n"
                    + diffs
                )
    history = load_history(quilt.history_dir)
    original = (plan.paper_dir / plan.master_rel).read_text(encoding="utf-8", errors="replace")
    name = slug(Path(plan.dest_rel).stem)
    entry = write_step(
        history,
        "import",
        name,
        FreezePlan(),
        actor_for(root),
        extra={
            "from": {"name": plan.master_rel, "hash": text_hash(original)},
            "landmark": f"{name}.tex",
            "to": {"path": f"{name}.tex", "hash": text_hash(plan.text)},
            "inlined": list(plan.inlined),
            "drafted": {"path": plan.dest_rel, "hash": text_hash(draft.text), "ids": len(draft.insertions)},
        },
        document_text=plan.text,
        document_name=f"{name}.tex",
    )
    main_set = set_main(load_quilt(root), plan.dest_rel)
    after = scan(load_quilt(root))
    wrote = [Item(f"{plan.master_rel} -> {plan.dest_rel}, {len(draft.insertions)} ids inserted")]
    wrote += [Item(f"{src} -> {dest}") for src, dest in arrows if dest in written]
    if main_set:
        wrote.append(Item(f"config.toml: main = {plan.dest_rel}"))
    groups = [Group("written", wrote, limit=None)]
    if plan.outside:
        groups.append(
            Group(
                "not copied, outside the paper directory (loom:import-outside-tree)",
                [Item(n) for n in sorted(plan.outside)],
                limit=None,
            )
        )
    groups += identity_group(ident)
    groups.append(Group(f"in {plan.dest_rel}", _document_counts(after, plan.dest_rel), limit=None, counted=False))
    bib_groups, bib = bibliography_groups(quilt)
    groups += bib_groups
    checked = identity_said(ident, plan.dest_rel, "the original") if check else "the identity test was skipped"
    said = (
        f"imported {plan.master_rel} as {plan.dest_rel} with {len(draft.insertions)} ids; {checked}; "
        f"the paper as received is landmark {name}, step {entry.step:04d}"
    )
    data = {
        "document": plan.dest_rel,
        "from": plan.master_rel,
        "landmark": name,
        "step": entry.step,
        "ids": len(draft.insertions),
        "written": sorted(written),
        "inlined": list(plan.inlined),
        "outside": list(plan.outside),
        "main": plan.dest_rel if main_set else None,
        "identity": None if ident is None else ("skipped" if ident.skipped else "pass" if ident.passed else "fail"),
        "bibliography": bib,
    }
    return Imported(said, ident, groups, data)


@click.command(name="import")
@click.argument("file")
@click.option("--yes", "-y", is_flag=True, help="Import without asking for confirmation.")
@click.option("--no-check", "no_check", is_flag=True, help="Skip the identity test.")
@click.option(
    "--fix-anchoring",
    "fix_anchors",
    is_flag=True,
    help="Rewrite the drafted document so every theorem-like \\begin and \\end is alone on its line.",
)
@click.option(
    "--to",
    "to",
    default=None,
    metavar="FILE",
    help="The working document to draft, directly in the drafting directory (default: the paper's file name there).",
)
@click.option("--dry-run", is_flag=True, help="Say what the import would write, and write nothing; no identity test.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def import_command(
    file: str,
    yes: bool,
    no_check: bool,
    fix_anchors: bool,
    to: str | None,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Bring a paper into the quilt: its styles, bibliography and figures at the root, the paper as received kept as a landmark, and the working document drafted from it at once in the drafting directory."""
    quilt = open_quilt(quilt_path)
    path = Path(file).expanduser()
    if not path.is_file():
        raise NotFoundError("file", f"{file} is not a file")
    done = run_import(quilt, path, yes, check=not no_check, fix_anchors=fix_anchors, dry_run=dry_run, to=to)
    groups = list(done.groups)
    if not dry_run:
        document = done.data["document"]
        groups.append(
            Group(
                "",
                [Item(f"{document} is the working document to edit; the landmark keeps the paper as received")],
                next="loom lint; loom build",
            )
        )
    Report(done.said, dry_run=dry_run, groups=groups, data=done.data).emit(as_json)


@click.command()
@click.argument("src", required=False, default=None)
@click.option(
    "--to",
    "to",
    default=None,
    metavar="FILE",
    help="The spine to write: SRC with inclusion lines in place of its nodes.",
)
@click.option(
    "--key",
    "keys",
    multiple=True,
    metavar="KEY",
    help="Move only these nodes, wherever they live; SRC is not needed. Writes the node files and prints the patch for the source, which loom never edits.",
)
@click.option(
    "--proofs",
    type=click.Choice(["attached", "separate"]),
    default="attached",
    help="Keep each proof in its statement's node file, or give it a file of its own.",
)
@click.option("--sections", is_flag=True, help="Also move labelled sections and subsections to nodes/.")
@click.option(
    "--all", "all_files", is_flag=True, help="Act on SRC and every file it reaches, writing spines under --to-dir."
)
@click.option("--to-dir", default=None, metavar="DIR", help="With --all: the directory the spines are written under.")
@click.option(
    "--retire",
    is_flag=True,
    help="Move SRC into retired/ once its spine is written, instead of leaving it superseded in place.",
)
@click.option(
    "--dry-run", is_flag=True, help="Say what would be written and moved, and write nothing; no identity test."
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def atomize(
    src: str | None,
    to: str | None,
    keys: tuple[str, ...],
    proofs: str,
    sections: bool,
    all_files: bool,
    to_dir: str | None,
    retire: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Move each node of SRC into nodes/<id>.tex and write the spine --to FILE, a copy of SRC with inclusion lines in their place.

    SRC is not modified; the history records that the spine superseded it, so it defines nothing until `loom live`.
    """
    with Progress("scanning") as progress:
        result = open_scan(quilt_path)
        if keys:
            report, diff = _atomize_keys(result, list(keys), src, proofs, dry_run, as_json)
        else:
            report, diff = _atomize(progress, result, src, to, proofs, sections, all_files, to_dir, retire, dry_run), ""
    if as_json:
        report.emit(True)
        return
    report.emit()
    if diff:
        click.echo("")
        click.echo(diff, nl=False)


def _atomize(
    progress: Progress,
    result: ScanResult,
    src: str | None,
    to: str | None,
    proofs: str,
    sections: bool,
    all_files: bool,
    to_dir: str | None,
    retire: bool,
    dry_run: bool,
) -> Report:
    """`loom atomize SRC`'s work, its report returned for the caller to print once the progress line is gone."""
    root = result.quilt.root
    if src is None:
        raise EnvError("name the file to atomize, or the nodes with --key")
    src_rel = _rel(root, src)
    if src_rel not in result.files:
        raise NotFoundError("file", f"{src} is not a scanned file of this quilt")
    if result.files[src_rel].superseded:
        raise ContentError(f"{src_rel} is superseded and defines nothing; loom live {src_rel} first")
    if all_files:
        if not to_dir:
            raise EnvError("--all needs --to-dir DIR")
        exp = result.expansions.get(src_rel)
        files = [src_rel] + ([f for f in exp.reached if f != src_rel] if exp else [])
        targets = [(f, f"{to_dir.rstrip('/')}/{f}") for f in files]
    else:
        if not to:
            raise EnvError("name the spine to write with --to FILE")
        targets = [(src_rel, to)]
    targets = [(s_rel, quilt_relative(result.quilt, destination(result.quilt, d, source=True))) for s_rel, d in targets]
    if retire:
        for s_rel, _ in targets:
            if (root / "retired" / s_rel).exists():
                raise EnvError(f"retired/{s_rel} exists; atomize never overwrites")
    plans = []
    progress.next_stage("planning", len(targets))
    for s_rel, d_rel in targets:
        progress.item(s_rel)
        plan = plan_atomize(result, s_rel, d_rel, proofs, sections)
        if plan.refusals:
            raise ContentError("\n".join(f"{s_rel}: {r}" for r in plan.refusals))
        plans.append(plan)
    wrote: list[Item] = []
    unlabelled: list[Group] = []
    progress.next_stage("writing" if not dry_run else "checking", len(plans))
    for plan in plans:
        progress.item(plan.dest)
        if dry_run:
            taken = [m.target for m in plan.moves if (root / m.target).exists()]
            if taken:
                raise ContentError(f"loom:atomize-target-exists: {taken[0]} exists")
        else:
            try:
                write_atomize(result, plan)
            except FileExistsError as exc:
                raise ContentError(f"loom:atomize-target-exists: {exc} exists") from exc
        deferred = sum(1 for m in plan.moves if ".proof" in m.target)
        moved_sections = sum(
            1 for m in plan.moves if result.nodes.get(m.key) is not None and result.nodes[m.key].kind == "section"
        )
        old_lines = result.files[plan.src].text.count("\n")
        parts = [counted(len(plan.moves) - deferred - moved_sections, "result"), counted(deferred, "proof")]
        if moved_sections:
            parts.append(counted(moved_sections, "section"))
        wrote.append(
            Item(
                f"{plan.dest}: {plan.spine.count(chr(10))} lines, was {old_lines}; {', '.join(parts)} set apart in nodes/"
            )
        )
        if plan.unlabelled:
            unlabelled.append(
                Group(
                    f"not moved from {plan.src}, for want of an id",
                    [Item("", key=u) for u in sorted(plan.unlabelled)],
                    problem=True,
                    next=f"loom id {plan.src}",
                )
            )
    plan = plans[0]
    retired = [f"retired/{pl.src}" for pl in plans] if retire else []
    superseded = [] if retire else [pl.src for pl in plans]
    record = {
        "from": [pl.src for pl in plans],
        "to": [pl.dest for pl in plans],
        "keys": sorted({m.key for pl in plans for m in pl.moves}),
        "superseded": superseded,
        "retired": retired,
    }
    moved = sum(len(pl.moves) for pl in plans)
    ident: IdentityResult | None = None
    if not dry_run:
        progress.next_stage(f"identity test: compiling {plan.src} and {plan.dest}")
        ident = _identity_for(result, root, plan.src, plan.dest)
        for pl in plans if retire else []:
            target_path = root / "retired" / pl.src
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(root / pl.src), str(target_path))
        append_entry(result.quilt.history_dir, "atomize", record, actor_for(root))
    for pl in plans:
        if result.quilt.config.main in (pl.src, f"retired/{pl.src}") and (
            result.quilt.config.main != pl.dest if dry_run else set_main_forced(result.quilt, pl.dest)
        ):
            wrote.append(Item(f"config.toml: main = {pl.dest}"))
    would = "would be " if dry_run else ""
    groups = [Group("would write" if dry_run else "written", wrote, limit=None)]
    if superseded:
        groups.append(
            Group(
                f"{would}superseded: each defines nothing until loom live FILE says otherwise",
                [Item(s) for s in sorted(superseded)],
            )
        )
    if retired:
        groups.append(Group(f"{would}moved to retired/", [Item(r) for r in sorted(retired)]))
    groups += unlabelled
    groups += identity_group(ident)
    failed = ident is not None and not ident.passed and not ident.skipped
    others = f" and {counted(len(plans) - 1, 'other file')}" if len(plans) > 1 else ""
    if dry_run:
        verdict = f"would atomize {plan.src} into {plan.dest}{others}, {counted(moved, 'file')} in nodes/; the identity test runs when it is written"
    else:
        verdict = f"atomized {plan.src} into {plan.dest}{others}, {counted(moved, 'file')} in nodes/; {identity_said(ident, plan.dest, plan.src)}"
    return Report(
        verdict,
        ok=not failed and not unlabelled,
        exit=EXIT_CONTENT if failed else 0,
        dry_run=dry_run,
        groups=groups,
        data={
            **record,
            "identity": None if ident is None else ("skipped" if ident.skipped else "pass" if ident.passed else "fail"),
        },
    )


def _atomize_keys(
    result: ScanResult, keys: list[str], src: str | None, proofs: str, dry_run: bool, as_json: bool
) -> tuple[Report, str]:
    """`atomize --key`: write the node files; the report and the patch for the source are returned to print. With --dry-run, the plan and the patch alone.

    The source is never edited: the editor applies the patch (loom-lsp offers it as one workspace edit), which is what keeps undo and an unsaved buffer the author's business. The JSON carries the plan (`plan_payload`) either way.
    """
    root = result.quilt.root
    src_rel = _rel(root, src) if src else None
    if src_rel is None:
        unknown = [k for k in keys if k not in result.assembly.nodes]
        if unknown:
            raise NotFoundError("node", "\n".join(f"{k} is not a key of this quilt" for k in unknown))
        homes = {result.assembly.nodes[k].file for k in keys}
        if len(homes) > 1:
            raise EnvError("those keys live in different files; atomize one file's nodes at a time")
        src_rel = homes.pop()
    if src_rel not in result.files:
        raise NotFoundError("file", f"{src or keys[0]} is not in a scanned file of this quilt")
    plan = plan_atomize(result, src_rel, src_rel, proofs, False, keys=keys)
    if not plan.refusals and not plan.moves:
        plan.refusals.append(f"nothing to move for {', '.join(keys)}")
    if plan.refusals:
        refusal = "\n".join(f"{src_rel}: {r}" for r in plan.refusals)
        if as_json:
            Report(
                f"nothing can move: {refusal}",
                ok=False,
                exit=EXIT_CONTENT,
                dry_run=dry_run,
                data=plan_payload(result, plan),
            ).emit(True)
        raise ContentError(refusal)
    problem = verify_plan(result, plan)
    if problem is not None:
        raise ContentError(f"loom:atomize-plan-unsound: {problem}")
    for m in plan.moves:
        if (root / m.target).exists():
            raise ContentError(f"loom:atomize-target-exists: {m.target} exists")
    diff = unified_diff(result.files[src_rel].text, plan.spine, src_rel)
    if dry_run:
        files = sorted(m.target for m in plan.moves)
        report = Report(
            f"would write {counted(len(files), 'node file')}, with this patch for {src_rel}",
            dry_run=True,
            groups=[Group("would write", [Item(p) for p in files], limit=None)],
            data={**plan_payload(result, plan), "diff": diff},
        )
    else:
        written = write_moves(result, plan)
        report = Report(
            f"wrote {counted(len(written), 'node file')}; apply this patch to {src_rel}, which loom never edits, "
            "and until then the moved results are defined twice, with no text",
            ok=False,
            groups=[Group("written", [Item(p) for p in sorted(written)], limit=None)],
            data={**plan_payload(result, plan), "diff": diff, "written": sorted(written)},
        )
    return report, diff


def _identity_for(result: ScanResult, root: Path, src_rel: str, dest_rel: str) -> IdentityResult | None:
    """Identity test for a rewrite of SRC into DEST: a master SRC is compiled directly; otherwise the first master reaching SRC is compiled in a scratch copy of the quilt where DEST's text stands at SRC's path. None when no master reaches SRC."""
    if src_rel in result.masters:
        with tempfile.TemporaryDirectory(prefix="loom-identity-") as tmp:
            return identity_test(root, src_rel, root, dest_rel, Path(tmp), engine_for(result, src_rel))
    node = result.nodes.get(src_rel)
    masters = node.reached_by if node else []
    if not masters:
        return None
    master = masters[0]
    with tempfile.TemporaryDirectory(prefix="loom-identity-") as tmp:
        scratch = Path(tmp)
        after = scratch / "quilt"
        shutil.copytree(root, after, ignore=shutil.ignore_patterns("build", ".git", ".loom"))
        (after / src_rel).write_text((root / dest_rel).read_text(encoding="utf-8"), encoding="utf-8")
        return identity_test(root, master, after, master, scratch, engine_for(result, master))


@click.command(name="deloom")
@click.argument("source")
@click.option(
    "--to",
    "to",
    required=True,
    metavar="FILE",
    help="The file to write: one flat document, never among the quilt's sources (build/ or outside the quilt).",
)
@click.option(
    "--keep-referenced-ids",
    "keep_ids",
    is_flag=True,
    help="Keep the id label of a referenced result that has no label of yours, and the references to it.",
)
@click.option(
    "--keep-incomplete",
    "keep_incomplete",
    is_flag=True,
    help="Keep every \\incomplete{…}, defined to print nothing as loom.sty defines it.",
)
@click.option("--dry-run", is_flag=True, help="Say what would be removed and written, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def deloom_command(
    source: str,
    to: str,
    keep_ids: bool,
    keep_incomplete: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Write FILE, the document SOURCE flattened, with loom taken out and every other line as written.

    Removed: `\\usepackage{loom}`, `% !LOOM` lines, `\\uses{…}`, and every label that is a loom id; a reference to an id moves to your own label beside it. A referenced result whose only label is its id, and any `\\incomplete{…}`, block the deloom until you give the result a label or resolve the incomplete, or pass the flag that keeps them.
    """
    from loom.reshape.deloom import deloom
    from loom.reshape.linearize import flatten

    result = open_scan(quilt_path)
    root = result.quilt.root
    rel = _rel(root, source)
    if rel not in result.masters:
        named = [m for m in result.masters if Path(m).name == source or Path(m).stem == source]
        if len(named) != 1:
            raise NotFoundError("document", f"{source} is not a document of this quilt; `loom status` lists them")
        rel = named[0]
    target = destination(result.quilt, to)
    shown = quilt_relative(result.quilt, target)
    ids = {n.id for n in result.nodes.values() if n.id} | {k for k, n in result.nodes.items() if n.kind == "conflict"}
    done = deloom(flatten(root, rel).text, ids, keep_ids=keep_ids, keep_incomplete=keep_incomplete)
    if done.blocked:
        lines = [f"{rel} cannot be deloomed as it stands:"]
        if done.blocked_ids:
            lines.append(f"  {len(done.blocked_ids)} referenced result(s) whose only label is their id:")
            for name, count in sorted(done.blocked_ids.items()):
                node = result.nodes.get(name)
                what = f" ({node.taxon}{f', “{node.title}”' if node.title else ''})" if node else ""
                lines.append(f"    {name}{what}: {count} reference(s)")
            lines.append(
                "  give each a label of your own beside its id, or pass --keep-referenced-ids to keep those ids"
            )
        if done.blocked_incomplete:
            where = ", ".join(str(n) for n in done.blocked_incomplete)
            lines.append(
                f"  {len(done.blocked_incomplete)} \\incomplete{{…}}, line(s) {where}: resolve them, or pass --keep-incomplete to keep them"
            )
        raise ContentError("\n".join(lines))
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(done.text, encoding="utf-8")
    groups = []
    if done.kept_ids:
        groups.append(
            Group(
                "ids kept, each the only label of a referenced result; give it a label of your own to replace it",
                [Item(f"line {line}", key=name) for name, line in sorted(done.kept_ids.items(), key=lambda kv: kv[1])],
            )
        )
    if done.kept_incomplete:
        groups.append(
            Group("\\incomplete{…} kept, printing nothing", [Item(f"line {n}") for n in done.kept_incomplete])
        )
    Report(
        f"{'would write' if dry_run else 'wrote'} {shown}: {counted(len(done.removed), 'id label')}, {done.uses} \\uses and "
        f"{counted(done.directives, '% !LOOM line')} removed; {counted(done.moved, 'reference')} moved to your labels",
        dry_run=dry_run,
        groups=groups,
        data={
            "source": rel,
            "to": shown,
            "removed": done.removed,
            "moved": done.moved,
            "uses": done.uses,
            "directives": done.directives,
            "kept_ids": done.kept_ids,
            "kept_incomplete": done.kept_incomplete,
        },
    ).emit(as_json)
