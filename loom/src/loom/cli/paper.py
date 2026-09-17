"""`loom id`, `loom import`, `loom atomize`, `loom inline` (book 12.3) and the identity test they share."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, EXIT_USAGE, ContentError, EnvError, emit_json, note
from loom.cli._quilt import open_quilt, open_scan, quilt_option
from loom.cli.build_cmds import engine_for
from loom.reshape.anchoring import anchoring_violations
from loom.reshape.atomize import inline as inline_text
from loom.reshape.atomize import plan_atomize, plan_payload, verify_plan, write_atomize, write_moves
from loom.reshape.ids import apply_insertions, plan_insertions, unified_diff
from loom.reshape.importer import apply_import, plan_import, report_counts, set_main
from loom.scan.alloc import visible_locals
from loom.scan.labels import next_local
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult, scan
from loom.scan.source import IGNORE_RE
from loom.tex.identity import IdentityResult, identity_test


@click.command(name="id")
@click.argument("file", required=False, default=None)
@click.option(
    "--to", "to", default=None, metavar="DEST", help="Write the patched copy here instead of printing a diff."
)
@click.option("--sections/--no-sections", default=True, help="Also label sections through subsubsection (default on).")
@click.option("--all-levels", is_flag=True, help="Also label paragraphs and subparagraphs.")
@click.option("--prefix", default=None)
@click.option("--next", "next_only", is_flag=True, help="Print the next free id and nothing else; inserts nothing.")
@click.option("--json", "as_json", is_flag=True, help="With --next: print it as JSON.")
@quilt_option
@click.pass_context
def id_command(
    ctx: click.Context,
    file: str | None,
    to: str | None,
    sections: bool,
    all_levels: bool,
    prefix: str | None,
    next_only: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Print a patch (or write a copy with --to) inserting \\label{<id>} on every untagged theorem-like environment and section in FILE, or with --next the next free id. Never modifies FILE."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    pre_next = prefix or result.quilt.config.prefix
    if next_only:
        allocated = f"{pre_next}-{next_local(visible_locals(result, pre_next))}"
        emit_json({"id": allocated, "prefix": pre_next}) if as_json else click.echo(allocated)
        return
    if file is None:
        click.echo("ERROR: name a file to label, or pass --next for the next free id", err=True)
        ctx.exit(EXIT_USAGE)
    rel = _rel(root, file)
    if rel not in result.files:
        raise EnvError(f"{file} is not a scanned file of this quilt")
    v = anchoring_violations(result.files[rel].text, set(result.taxa))
    if v:
        for x in v:
            note(f"{rel}:{x.line}  \\{x.kind}{{{x.env}}} is not alone on its line")
        note("loom:line-anchoring: fix these lines first (or import with --fix-anchoring)")
        ctx.exit(EXIT_CONTENT)
    pre = prefix or result.quilt.config.prefix
    ins = plan_insertions(result, [rel], pre, next_local(visible_locals(result, pre)), sections, all_levels)
    before = result.files[rel].text
    after = apply_insertions(before, ins)
    if to:
        out = Path(to).expanduser()
        if out.exists():
            raise EnvError(f"{to} exists; id never overwrites")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(after, encoding="utf-8")
        click.echo(f"{out}  ({len(ins)} labels)")
        return
    click.echo(unified_diff(before, after, rel), nl=False)
    if not ins:
        note("nothing to label")


def _rel(root: Path, file: str) -> str:
    p = Path(file).expanduser()
    p = p if p.is_absolute() else (Path.cwd() / p)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return file


def run_import(
    quilt: Quilt, paper: Path, yes: bool, fix_anchors: bool, prefix: str | None = None
) -> IdentityResult | None:
    """The import flow of 6.2; returns the identity result (None when skipped)."""
    if not paper.is_file():
        raise EnvError(f"{paper} is not a file")
    plan = plan_import(quilt, paper, fix_anchors, prefix)
    note(f"Resolving closure of {paper.name} ... {len(plan.files)} files")
    # the arrows are what would be copied, not what was: everything below is a plan until "Wrote N files" at the end
    note("Plan, nothing written yet:")
    for dest, src in plan.files.items():
        if Path(src).name != Path(dest).name or not dest.startswith(quilt.config.drafts):
            note(f"  {Path(src).relative_to(plan.paper_dir).as_posix()} -> {dest}")
        else:
            note(f"  {Path(src).name} -> {dest}")
    for name in plan.outside:
        note(f"  {name} -> not copied; it lies outside the paper directory (loom:import-outside-tree)")
    if plan.violations:
        note(f"Nothing was written. {paper.name} has {len(plan.violations)} line-anchoring violation(s):")
        for v in plan.violations[:20]:
            note(f"  line {v.line}: \\{v.kind}{{{v.env}}} is not alone on its line")
        raise ContentError(
            "loom needs a theorem-like \\begin and \\end alone on their lines to find a node's exact span. "
            "Fix them in the paper, or pass --fix-anchoring to rewrite loom's copy and leave your original alone."
        )
    if plan.spans:
        raise ContentError("an environment spans files: " + "; ".join(plan.spans))
    scratch = Path(tempfile.mkdtemp(prefix="loom-identity-"))
    from loom.tex.runner import compile_tex

    before = compile_tex(plan.paper_dir, plan.master_rel, scratch / "before", quilt.config.engine, halt_on_error=False)
    if not before.ok:
        raise ContentError(
            f"the original does not compile in its own directory ({before.first_error}); fix it before importing"
        )
    note(f"Compiling original in {plan.paper_dir} ... ok")
    if plan.diff:
        note(
            f"Proposed edits ({plan.diff.count(chr(10) + '+') - plan.diff.count(chr(10) + '+++')} lines in {sum(1 for _ in set(i.file for i in plan.insertions))} file(s)):"
        )
        click.echo(plan.diff, nl=False)
    else:
        note("Proposed edits: none (every node already carries an id)")
    if not yes:
        if not sys.stdin.isatty():
            raise EnvError("import needs confirmation; pass --yes")
        click.confirm("Apply?", abort=True)
    written = apply_import(quilt, plan)
    changed = set_main(quilt, plan.master_quilt_rel)
    note(f"Wrote {len(written)} files." + (f" main = {plan.master_quilt_rel}" if changed else ""))
    result = scan(open_quilt(str(quilt.root)))
    note(report_counts(result))
    engine = engine_for(result, plan.master_quilt_rel)
    ident = identity_test(plan.paper_dir, plan.master_rel, quilt.root, plan.master_quilt_rel, scratch, engine)
    note(ident.summary())
    return ident


@click.command(name="import")
@click.argument("file")
@click.option("--yes", "-y", is_flag=True)
@click.option(
    "--fix-anchoring",
    "fix_anchors",
    is_flag=True,
    help="Rewrite the copy so every theorem-like \\begin and \\end is alone on its line.",
)
@click.option("--prefix", default=None)
@quilt_option
@click.pass_context
def import_command(
    ctx: click.Context, file: str, yes: bool, fix_anchors: bool, prefix: str | None, quilt_path: str | None
) -> None:
    """Copy a paper and everything it reaches into the quilt, inserting ids into the copies and changing nothing else."""
    quilt = open_quilt(quilt_path)
    ident = run_import(quilt, Path(file).expanduser(), yes, fix_anchors, prefix)
    if ident is not None and not ident.passed and not ident.skipped:
        ctx.exit(EXIT_CONTENT)


@click.command()
@click.argument("src", required=False, default=None)
@click.argument("dest", required=False, default=None)
@click.option("--to", "to", default=None, metavar="DEST")
@click.option(
    "--key",
    "keys",
    multiple=True,
    metavar="KEY",
    help="Move only these nodes, wherever they live; SRC is not needed. Writes the node files and prints the patch for the source, which loom never edits.",
)
@click.option("--json", "as_json", is_flag=True, help="With --key: print the plan and write nothing.")
@click.option("--proofs", type=click.Choice(["attached", "separate"]), default="attached")
@click.option("--sections", is_flag=True, help="Also move labelled sections and subsections to nodes/.")
@click.option(
    "--all", "all_files", is_flag=True, help="Act on SRC and every file it reaches, writing spines under --to-dir."
)
@click.option("--to-dir", default=None, metavar="DIR")
@click.option(
    "--ignore-src",
    is_flag=True,
    help="Add `% !LOOM ignore` to SRC's first line, so the quilt keeps one definition of each node.",
)
@quilt_option
@click.pass_context
def atomize(
    ctx: click.Context,
    src: str | None,
    dest: str | None,
    to: str | None,
    keys: tuple[str, ...],
    as_json: bool,
    proofs: str,
    sections: bool,
    all_files: bool,
    to_dir: str | None,
    ignore_src: bool,
    quilt_path: str | None,
) -> None:
    """Move each node of SRC into nodes/<id>.tex and write DEST, a copy of SRC with inclusion lines in their place. SRC's text is not modified (with --ignore-src, a directive line is added above it)."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    if keys:
        _atomize_keys(ctx, result, list(keys), src, as_json, proofs)
        return
    if as_json:
        raise EnvError("--json needs --key")
    if src is None:
        click.echo("ERROR: name the file to atomize, or the nodes with --key", err=True)
        ctx.exit(EXIT_USAGE)
    src_rel = _rel(root, src)
    if src_rel not in result.files:
        raise EnvError(f"{src} is not a scanned file of this quilt")
    if all_files:
        if not to_dir:
            raise EnvError("--all needs --to-dir DIR")
        exp = result.expansions.get(src_rel)
        files = [src_rel] + ([f for f in exp.reached if f != src_rel] if exp else [])
        targets = [(f, f"{to_dir.rstrip('/')}/{f}") for f in files]
    else:
        target = dest or to
        if not target:
            click.echo("ERROR: specify a destination file after the source, or with --to", err=True)
            ctx.exit(2)
        targets = [(src_rel, _rel(root, target))]
    plans = []
    for s_rel, d_rel in targets:
        if (root / d_rel).exists():
            raise EnvError(f"{d_rel} exists; atomize never overwrites")
        plan = plan_atomize(result, s_rel, d_rel, proofs, sections)
        if plan.refusals:
            for r in plan.refusals:
                note(f"{s_rel}: {r}")
            ctx.exit(EXIT_CONTENT)
        plans.append(plan)
    total = 0
    for plan in plans:
        try:
            written = write_atomize(result, plan)
        except FileExistsError as exc:
            raise ContentError(f"loom:atomize-target-exists: {exc} exists") from exc
        total += len(written) - 1
        deferred = sum(1 for m in plan.moves if ".proof" in m.target)
        click.echo(f"Moved {len(plan.moves) - deferred} nodes and {deferred} deferred proofs to nodes/")
        old_lines = result.files[plan.src].text.count("\n")
        click.echo(f"Wrote {plan.dest} (spine, {plan.spine.count(chr(10))} lines, was {old_lines})")
        if plan.unlabelled:
            note(f"Not moved (no id): {', '.join(plan.unlabelled)}; run loom id first")
    plan = plans[0]
    ident = _identity_for(result, root, plan.src, plan.dest)
    if ident is not None:
        note(ident.summary())
    if ignore_src:
        for pl in plans:
            p_src = root / pl.src
            text = p_src.read_text(encoding="utf-8")
            if not IGNORE_RE.search(text[:400]):
                p_src.write_text("% !LOOM ignore\n" + text, encoding="utf-8")
            note(f"Wrote `% !LOOM ignore` above {pl.src}: the quilt now has one definition of each node.")
    else:
        note(
            f"Note: {plan.src} still defines its ids inline, so the quilt has two copies of every node it moved. Pass --ignore-src, delete it, or move it out of the quilt."
        )
    if ident is not None and not ident.passed and not ident.skipped:
        ctx.exit(EXIT_CONTENT)


@click.command(name="inline")
@click.argument("src")
@click.argument("dest", required=False, default=None)
@click.option("--to", "to", default=None, metavar="DEST")
@click.option("--all", "recursive", is_flag=True, help="Inline recursively.")
@quilt_option
@click.pass_context
def inline_command(
    ctx: click.Context, src: str, dest: str | None, to: str | None, recursive: bool, quilt_path: str | None
) -> None:
    """Write DEST, a copy of SRC with every \\input of a node file replaced by its contents. The reverse of atomize."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    src_rel = _rel(root, src)
    target = dest or to
    if not target:
        click.echo("ERROR: specify a destination file after the source, or with --to", err=True)
        ctx.exit(2)
    d_rel = _rel(root, target)
    if (root / d_rel).exists():
        raise EnvError(f"{d_rel} exists; inline never overwrites")
    text = inline_text(result, src_rel, recursive)
    (root / d_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / d_rel).write_text(text, encoding="utf-8")
    click.echo(f"Wrote {d_rel} ({text.count(chr(10))} lines)")
    ident = _identity_for(result, root, src_rel, d_rel)
    if ident is not None:
        note(ident.summary())
        if not ident.passed and not ident.skipped:
            ctx.exit(EXIT_CONTENT)


def _atomize_keys(
    ctx: click.Context, result: ScanResult, keys: list[str], src: str | None, as_json: bool, proofs: str
) -> None:
    """`atomize --key`: write the node files and print the patch for the source, or with --json print the plan and write nothing.

    The source is never edited: the editor applies the patch (loom-lsp offers it as one workspace edit), which is what keeps undo and an unsaved buffer the author's business.
    """
    root = result.quilt.root
    src_rel = _rel(root, src) if src else None
    if src_rel is None:
        unknown = [k for k in keys if k not in result.assembly.nodes]
        if unknown:
            for k in unknown:
                note(f"{k} is not a key of this quilt")
            ctx.exit(EXIT_CONTENT)
        homes = {result.assembly.nodes[k].file for k in keys}
        if len(homes) > 1:
            raise EnvError("those keys live in different files; atomize one file's nodes at a time")
        src_rel = homes.pop()
    if src_rel not in result.files:
        raise EnvError(f"{src or keys[0]} is not in a scanned file of this quilt")
    plan = plan_atomize(result, src_rel, src_rel, proofs, False, keys=keys)
    if not plan.refusals and not plan.moves:
        plan.refusals.append(f"nothing to move for {', '.join(keys)}")
    if plan.refusals:
        if as_json:
            emit_json(plan_payload(result, plan))
            ctx.exit(EXIT_CONTENT)
        for r in plan.refusals:
            note(f"{src_rel}: {r}")
        ctx.exit(EXIT_CONTENT)
    problem = verify_plan(result, plan)
    if problem is not None:
        raise ContentError(f"loom:atomize-plan-unsound: {problem}")
    if as_json:
        emit_json(plan_payload(result, plan))
        return
    for m in plan.moves:
        if (root / m.target).exists():
            raise ContentError(f"loom:atomize-target-exists: {m.target} exists")
    written = write_moves(result, plan)
    for path in written:
        click.echo(f"Wrote {path}")
    click.echo(unified_diff(result.files[src_rel].text, plan.spine, src_rel), nl=False)
    note(
        f"{src_rel} is yours to change: apply the patch above, or let your editor do it. Until then lint reports duplicate ids."
    )


def _identity_for(result: ScanResult, root: Path, src_rel: str, dest_rel: str) -> IdentityResult | None:
    """Identity test for a rewrite of SRC into DEST: a master SRC is compiled directly; otherwise the first master reaching SRC is compiled in a scratch copy of the quilt where DEST's text stands at SRC's path. None when no master reaches SRC."""
    scratch = Path(tempfile.mkdtemp(prefix="loom-identity-"))
    if src_rel in result.masters:
        return identity_test(root, src_rel, root, dest_rel, scratch, engine_for(result, src_rel))
    node = result.nodes.get(src_rel)
    masters = node.reached_by if node else []
    if not masters:
        note(f"Identity test: skipped (no master reaches {src_rel})")
        return None
    master = masters[0]
    after = scratch / "quilt"
    shutil.copytree(root, after, ignore=shutil.ignore_patterns("build", ".git", ".loom"))
    (after / src_rel).write_text((root / dest_rel).read_text(encoding="utf-8"), encoding="utf-8")
    return identity_test(root, master, after, master, scratch, engine_for(result, master))
