"""`loom compile`, `loom assemble`, `loom bundle`, `loom check` (book 12.5). `loom build` and `loom serve` live in render/ once the converter exists."""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, ContentError, EnvError, note
from loom.cli._quilt import open_scan, quilt_option, resolve_key
from loom.clock import stamp
from loom.scan.scan import ScanResult
from loom.tex.assemble import assemble as assemble_text
from loom.tex.bundle import Bundle, build_bundle, bundle_filename, draft_bundle, substituted_region
from loom.tex.runner import compile_tex, normalise_engine


def engine_for(result: ScanResult, master: str, override: str | None = None) -> str:
    closure = result.closures.get(master)
    return normalise_engine(override or (closure.engine if closure else None) or result.quilt.config.engine)


def log_run(run_dir: str | None, command: str) -> None:
    if not run_dir:
        return
    p = Path(run_dir)
    p.mkdir(parents=True, exist_ok=True)
    with (p / "run.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp()}  {command}\n")


def write_bundle(result: ScanResult, b: Bundle, to: str | None, run_dir: str | None) -> Path:
    root = result.quilt.root
    out = Path(to).expanduser() if to else root / "build" / "bundles" / bundle_filename(b.key)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(b.text, encoding="utf-8")
    if run_dir:
        rp = Path(run_dir)
        rp.mkdir(parents=True, exist_ok=True)
        shutil.copy(out, rp / f"bundle-{bundle_filename(b.key)[:-4]}.tex")
    return out


@click.command()
@click.argument("key", required=False, default=None)
@click.option("--to", "to", default=None, metavar="FILE", help="Write here instead of build/bundles/.")
@click.option(
    "--run",
    "run_dir",
    default=None,
    metavar="DIR",
    envvar="LOOM_RUN",
    help="Also copy into the run directory and log the call.",
)
@click.option(
    "--with",
    "with_file",
    default=None,
    metavar="FILE",
    help="Substitute a unified diff or a .tex file for the key's text.",
)
@click.option(
    "--draft", "draft_file", default=None, metavar="FILE", help="Bundle a node file that is not yet in the quilt."
)
@quilt_option
def bundle(
    key: str | None,
    to: str | None,
    run_dir: str | None,
    with_file: str | None,
    draft_file: str | None,
    quilt_path: str | None,
) -> None:
    """Write build/bundles/<key>.tex: the statements KEY depends on, in dependency order, then KEY itself."""
    result = open_scan(quilt_path)
    if not result.masters:
        raise ContentError("the quilt has no master; a bundle needs a preamble")
    log_run(run_dir, "loom bundle " + " ".join(x for x in [key, "--with", with_file, "--draft", draft_file] if x))
    if draft_file:
        b = draft_bundle(result, Path(draft_file).expanduser())
        if b.missing:
            raise ContentError(f"the draft references unknown labels: {', '.join(b.missing)}")
    else:
        if key is None:
            raise EnvError("give a KEY, or --draft FILE")
        key = resolve_key(result, key)
        if result.nodes[key].kind not in ("environment", "proof", "section"):
            raise EnvError(f"{key} is not a statement or proof key")
        override = None
        if with_file:
            try:
                override = substituted_region(result, key, Path(with_file).expanduser())
            except ValueError as exc:
                raise ContentError(f"--with {with_file}: {exc}") from exc
        b = build_bundle(result, key, override_text=override)
    out = write_bundle(result, b, to, run_dir)
    click.echo(str(out.relative_to(result.quilt.root)) if out.is_relative_to(result.quilt.root) else str(out))
    if b.missing and not draft_file:
        note(f"closure entries without a statement: {', '.join(b.missing)}")


@click.command()
@click.argument("target", required=False, default=None)
@click.option("--engine", default=None, help="Override the engine (pdflatex, lualatex, xelatex).")
@quilt_option
@click.pass_context
def compile(ctx: click.Context, target: str | None, engine: str | None, quilt_path: str | None) -> None:  # noqa: A001
    """Run latexmk from the root into build/<stem>/ for a master (default: the default master), or for a bundle by key."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    if target is None or target in result.masters or (root / target).is_file() and target.endswith(".tex"):
        master = target or result.default_master
        if master is None:
            raise EnvError("the quilt has no master")
        res = compile_tex(root, master, root / "build" / Path(master).stem, engine_for(result, master, engine))
        label = master
    else:
        key = resolve_key(result, target)
        b = build_bundle(result, key)
        out = write_bundle(result, b, None, None)
        stem = out.stem
        res = compile_tex(
            root,
            str(out.relative_to(root)),
            root / "build" / "bundles" / stem,
            engine_for(result, result.default_master or result.masters[0], engine),
        )
        label = f"bundle {key}"
    if res.ok:
        click.echo(f"compiled {label} -> {res.outdir.relative_to(root)}/ ({res.engine})")
    else:
        if label.startswith("bundle "):
            for line in missing_package_notes(result, b.closure + [key]):
                click.echo(line, err=True)
        click.echo(f"FAILED {label}: {res.first_error}", err=True)
        ctx.exit(EXIT_CONTENT)


def missing_package_notes(result: ScanResult, keys: list[str]) -> list[str]:
    """`loom:missing-package` lines for the digests among `keys`, named before a failed bundle compile (book 8.11)."""
    files = {result.nodes[k].file for k in keys if k in result.nodes and result.nodes[k].digest}
    out: list[str] = []
    for d in result.lint:
        if d.code == "loom:missing-package" and any(loc.file in files for loc in d.locations):
            out.append(f"{d.code}: {d.message}")
    return out


@click.command()
@click.argument("master")
@click.argument("dest")
@quilt_option
def assemble(master: str, dest: str, quilt_path: str | None) -> None:
    """Write DEST: MASTER flattened with every \\input, \\nest (levels shifted), and \\include expanded, for arXiv or latexdiff."""
    result = open_scan(quilt_path)
    if master not in result.masters:
        raise EnvError(f"{master} is not a master of this quilt ({', '.join(result.masters) or 'none'})")
    out = Path(dest).expanduser()
    if out.exists():
        raise EnvError(f"{dest} exists; assemble never overwrites")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(assemble_text(result.quilt.root, master), encoding="utf-8")
    click.echo(str(out))


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
            click.echo(("ok      " if res.ok else "FAILED  ") + master + ("" if res.ok else f": {res.first_error}"))
            failed = failed or not res.ok
        keys: list[str] = []
        if bundles == "all":
            keys = [k for k, n in result.nodes.items() if n.kind == "environment" and n.digest is None]
        elif bundles == "stale":
            keys = []  # the ledger arrives at M3; until then nothing is stale
        for key in keys:
            b = build_bundle(result, key)
            out = write_bundle(result, b, None, None)
            res = compile_tex(
                root,
                str(out.relative_to(root)),
                root / "build" / "bundles" / out.stem,
                engine_for(result, result.default_master or result.masters[0]),
            )
            click.echo(
                ("ok      " if res.ok else "FAILED  ") + f"bundle {key}" + ("" if res.ok else f": {res.first_error}")
            )
            failed = failed or not res.ok
    click.echo("check: " + ("FAILED" if failed else "ok"))
    if failed:
        ctx.exit(EXIT_CONTENT)
