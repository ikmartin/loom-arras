"""`loom compile`, `loom source`, `loom check` (book 12.5). `loom build` and `loom serve` live in render/; `loom linearize` (17.13) replaced `loom assemble`."""

from __future__ import annotations

from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, ContentError, EnvError, find_run, note
from loom.cli._quilt import open_scan, quilt_option, require_text, resolve_key
from loom.clock import stamp
from loom.reshape.linearize import flatten
from loom.scan.scan import ScanResult
from loom.tex.bundle import (
    Bundle,
    build_bundle,
    bundle_filename,
    draft_bundle,
    region_text,
    substituted_region,
    substituted_region_text,
)
from loom.tex.runner import CompileResult, compile_tex, normalise_engine


def engine_for(result: ScanResult, master: str, override: str | None = None) -> str:
    closure = result.closures.get(master)
    return normalise_engine(override or (closure.engine if closure else None) or result.quilt.config.engine)


def log_run(run_dir: str | None, command: str, root: Path | None = None) -> None:
    """Append `command` to the run's run.log; a relative run directory is the quilt's (`root`) when `root` is given."""
    if not run_dir:
        return
    # The same resolver every other `--run` uses. It never creates: an unmatched value used to be mkdir'd at the quilt
    # root, and the directory that left behind then shadowed the real run for every later command, so a whole session's
    # annotations were filed under a run that did not exist.
    p = find_run(root, run_dir) if root is not None else Path(run_dir)
    p.mkdir(parents=True, exist_ok=True)
    with (p / "run.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp()}  {command}\n")


def write_bundle(result: ScanResult, b: Bundle) -> Path:
    """Write a key's closure document under build/bundles/, for `loom compile KEY` and `loom check` to run latexmk on.

    A bundle is an internal artifact now: `loom source KEY --closure` is how a reader or an agent gets the text, so
    nothing copies one into a run directory and nothing gitignores it.
    """
    root = result.quilt.root
    out = root / "build" / "bundles" / bundle_filename(b.key)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(b.text, encoding="utf-8")
    return out


@click.command()
@click.argument("target", required=False, default=None)
@click.option("--engine", default=None, help="Override the engine (pdflatex, lualatex, xelatex).")
@click.option(
    "--with",
    "with_file",
    default=None,
    metavar="FILE",
    help="Substitute a unified diff, a .tex file, or an annotation's proposed text for KEY's text; the quilt is not touched.",
)
@click.option("--draft", "draft_file", default=None, metavar="FILE", help="Compile a node file not yet in the quilt.")
@click.option("--run", "run_dir", default=None, metavar="DIR", envvar="LOOM_RUN", help="Log this call to DIR/run.log.")
@quilt_option
@click.pass_context
def compile(  # noqa: A001
    ctx: click.Context,
    target: str | None,
    engine: str | None,
    with_file: str | None,
    draft_file: str | None,
    run_dir: str | None,
    quilt_path: str | None,
) -> None:
    """Run latexmk from the root into build/<stem>/ for a master (default: the default master), or for a key.

    Compiling a key builds the document of its closure and runs latexmk on that, so `--with` previews a proposed diff and `--draft` a node that has no id yet: neither writes into the quilt, and a failure names the digests whose packages are missing before it names the error.
    """
    result = open_scan(quilt_path)
    root = result.quilt.root
    parts = ["loom compile"] + ([target] if target else [])
    if with_file:
        parts += ["--with", with_file]
    if draft_file:
        parts += ["--draft", draft_file]
    log_run(run_dir, " ".join(parts), root)
    if draft_file:
        if not result.masters:
            raise ContentError("the quilt has no master; compiling a draft needs a preamble")
        b = draft_bundle(result, Path(draft_file).expanduser())
        if b.missing:
            raise ContentError(f"the draft references unknown labels: {', '.join(b.missing)}")
        out = write_bundle(result, b)
        res = compile_tex(
            root,
            str(out.relative_to(root)),
            root / "build" / "bundles" / out.stem,
            engine_for(result, result.default_master or result.masters[0], engine),
        )
        if report_compile(res, out.stem, root):
            return
        ctx.exit(EXIT_CONTENT)
    if target is None or target in result.masters or (root / target).is_file() and target.endswith(".tex"):
        if with_file:
            raise EnvError("--with substitutes one key's text; give a KEY rather than a master")
        master = target or result.default_master
        if master is None:
            raise EnvError("the quilt has no master")
        res = compile_tex(root, master, root / "build" / Path(master).stem, engine_for(result, master, engine))
        label = master
    else:
        key = resolve_key(result, target)
        require_text(result, key)
        if not result.masters:
            raise ContentError("the quilt has no master; compiling a key needs a preamble")
        override = None
        if with_file:
            override = substitution_for(result, key, with_file)
        b = build_bundle(result, key, override_text=override)
        out = write_bundle(result, b)
        stem = out.stem
        res = compile_tex(
            root,
            str(out.relative_to(root)),
            root / "build" / "bundles" / stem,
            engine_for(result, result.default_master or result.masters[0], engine),
        )
        label = f"bundle {key}"
    if res.usable == "failed" and label.startswith("bundle "):
        for line in missing_package_notes(result, b.closure + [key]):
            click.echo(line, err=True)
    if not report_compile(res, label, root):
        ctx.exit(EXIT_CONTENT)


def substitution_for(result: ScanResult, key: str, with_file: str) -> str:
    """Resolve `--with`: a file on disk, else an annotation id whose payload is the proposal it names.

    A file is tried first, because a path is what the option has always taken and a filename could otherwise be shadowed by an id. An annotation is accepted because the payload **is** the proposal — it is what `loom comment --payload` was for — and asking an agent to copy its own suggestion into a file before compiling it is a step with nothing in it.
    """
    from loom.records.annotations import find_annotation
    from loom.records.store import Records

    root = result.quilt.root
    p = Path(with_file).expanduser()
    try:
        if p.is_file():
            return substituted_region(result, key, p)
        found = find_annotation(Records(root, result.quilt.history_dir).records, with_file)
        if found is None:
            raise EnvError(f"--with {with_file}: no such file, and no annotation has that id")
        _, ann = found
        if not ann.payload:
            raise ContentError(f"--with {with_file}: that annotation proposes no text")
        if ann.target_key != key:
            raise ContentError(f"--with {with_file}: that annotation is on {ann.target_key}, not {key}")
        return substituted_region_text(result, key, ann.payload)
    except OSError as exc:
        raise EnvError(f"--with {with_file}: {exc.strerror or exc}") from exc
    except ValueError as exc:
        raise ContentError(f"--with {with_file}: {exc}") from exc


def report_compile(res: CompileResult, label: str, root: Path) -> bool:
    """Print the outcome of one compile; True when it produced a PDF, whether or not the log carried warnings.

    A nonzero exit with a readable PDF and no `!` line is reported as warnings, not as a failure: latexmk exits nonzero on an undefined reference, and an agent told FAILED cannot tell its own proposal from a document that was already like that.
    """
    state = res.usable
    if state == "ok":
        click.echo(f"compiled {label} -> {res.outdir.relative_to(root)}/ ({res.engine})")
        return True
    if state == "warnings":
        click.echo(f"compiled {label} with warnings -> {res.outdir.relative_to(root)}/ ({res.engine})")
        for w in res.warnings:
            click.echo(f"  {w}", err=True)
        return True
    click.echo(f"FAILED {label}: {res.first_error}", err=True)
    return False


def missing_package_notes(result: ScanResult, keys: list[str]) -> list[str]:
    """`loom:missing-package` lines for the digests among `keys`, named before a failed bundle compile (book 8.11)."""
    files = {result.nodes[k].file for k in keys if k in result.nodes and result.nodes[k].digest}
    out: list[str] = []
    for d in result.lint:
        if d.code == "loom:missing-package" and any(loc.file in files for loc in d.locations):
            out.append(f"{d.code}: {d.message}")
    return out


@click.command()
@click.option("--no-compile", is_flag=True, help="Lint only.")
@click.option(
    "--bundles",
    type=click.Choice(["all", "stale", "none"]),
    default="stale",
    help="Which bundles to compile (stale needs the ledger, milestone M3).",
)
@quilt_option
@click.pass_context
def check(ctx: click.Context, no_compile: bool, bundles: str, quilt_path: str | None) -> None:
    """lint, then compile every master, then bundles. Exit 1 on any failure. The CI command."""
    from loom.cli.lint_cmd import all_diagnostics

    result = open_scan(quilt_path)
    root = result.quilt.root
    failed = False
    diags = all_diagnostics(result)
    errors = [d for d in diags if d.severity == "error"]
    for d in diags:
        note(f"{d.severity:<7} {d.code:<36} {d.message}")
    if errors:
        failed = True
    if not no_compile:
        for master in result.masters:
            res = compile_tex(root, master, root / "build" / Path(master).stem, engine_for(result, master))
            bad = res.usable == "failed"
            click.echo(("FAILED  " if bad else "ok      ") + master + (f": {res.first_error}" if bad else ""))
            failed = failed or bad
        keys: list[str] = []
        if bundles == "all":
            keys = [k for k, n in result.nodes.items() if n.kind == "environment" and n.digest is None]
        elif bundles == "stale":
            keys = []  # the ledger arrives at M3; until then nothing is stale
        for key in keys:
            b = build_bundle(result, key)
            out = write_bundle(result, b)
            res = compile_tex(
                root,
                str(out.relative_to(root)),
                root / "build" / "bundles" / out.stem,
                engine_for(result, result.default_master or result.masters[0]),
            )
            bad = res.usable == "failed"
            click.echo(
                ("error   loom:bundle-failed  " if bad else "ok      ")
                + f"bundle {key}"
                + (f": {res.first_error}" if bad else "")
            )
            failed = failed or bad
    click.echo("check: " + ("FAILED" if failed else "ok"))
    if failed:
        ctx.exit(EXIT_CONTENT)


def document_rel(result: ScanResult, target: str) -> str | None:
    """The quilt-relative path when TARGET names a scanned document rather than a key, else None."""
    if not target.endswith(".tex"):
        return None
    p = Path(target)
    rel = str(p.resolve().relative_to(result.quilt.root)) if p.is_absolute() else target
    return rel if rel in result.files else None


@click.command()
@click.argument("target", metavar="TARGET")
@click.option("--closure", is_flag=True, help="Everything TARGET depends on, in dependency order, then TARGET itself.")
@click.option("--run", "run_dir", default=None, metavar="DIR", envvar="LOOM_RUN", help="Log this call to DIR/run.log.")
@quilt_option
def source(target: str, closure: bool, run_dir: str | None, quilt_path: str | None) -> None:
    """Print TARGET's LaTeX source: a key's own text, or a document flattened with every inclusion expanded in place.

    This is how a reader or an agent gets the text of a result or of a whole paper. It writes nothing: there is no file to clean up, none to keep out of version control, and none to go stale against the author's next edit.

    With --closure, a key is preceded by exactly the statements it depends on, in dependency order. A document is already whole, so --closure does not apply to one.
    """
    result = open_scan(quilt_path)
    doc = document_rel(result, target)
    if doc is not None:
        if closure:
            raise EnvError(f"--closure is for a key; {doc} is a document and already carries what it includes")
        log_run(run_dir, f"loom source {doc}", result.quilt.root)
        click.echo(flatten(result.quilt.root, doc).text.rstrip("\n"))
        return
    key = resolve_key(result, target)
    region = result.assembly.regions.get(key)
    if region is not None:
        # an equation's label names a point inside a node, not a node: print the node that holds it, and say so,
        # rather than index a region as if it were one -- which crashed with a KeyError on a digest's display equation
        note(
            f"{region.label} labels {'an equation' if region.where != 'prose' else 'a line'} inside {region.container}; printing that"
        )
        key = region.container
    require_text(result, key)
    log_run(run_dir, f"loom source {key}" + (" --closure" if closure else ""), result.quilt.root)
    if not closure:
        click.echo(region_text(result, key).rstrip("\n"))
        return
    if not result.masters:
        raise ContentError("the quilt has no master; a closure document needs a preamble")
    b = build_bundle(result, key)
    click.echo(b.text.rstrip("\n"))
    if b.missing:
        note(f"closure entries without a statement: {', '.join(b.missing)}")
