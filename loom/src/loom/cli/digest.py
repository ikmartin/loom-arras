"""`loom digest extract | import` (book 8.5, 8.10). Fetching moved to `loom refs fetch`, which fetches on a candidate as well as a declared identifier and checks the title on arrival (plan 0.12 §4.3)."""

from __future__ import annotations

from pathlib import Path

import click

from loom.cli._common import ContentError, EnvError, note
from loom.cli._quilt import open_scan, quilt_option
from loom.digest.extract import extract_digest
from loom.digest.importer import plan_digest_import, write_digest_import
from loom.scan.quilt import load_quilt
from loom.scan.scan import ScanResult, scan


@click.group(name="digest")
def digest() -> None:
    """Digests of cited papers: extract one from a paper's source, or port one in.

    To search what the digests hold, see `loom refs find` (statements) and `loom refs grep` (page text); to read a page, `loom refs page`; for the whole mechanical pass over every cited work, `loom refs build`.
    """


def _must_be_stored(root: Path, src: Path, citekey: str) -> Path:
    """Refuse a source outside loom's store: renderable content must have a document behind it (plan 0.13 §4).

    A digest extracted from a file on the author's desktop cites page numbers nobody else can open, and nothing later in the pipeline can repair that -- so the obligation starts where the digest is born, and the two commands that put a document in the store are named here rather than left to be found.
    """
    from loom.refs.pages import storage_root

    store = storage_root(root)
    if src.resolve().is_relative_to(store.resolve()):
        return src
    raise EnvError(
        f"{src} is not in loom's store, so a digest made from it would cite a document nobody else holds.\n"
        f"File it first: loom refs add <FILE> {citekey}, or loom refs fetch {citekey} where an identifier will serve it.\n"
        f"The store is {store.relative_to(root)}/."
    )


def _stored_source(result: ScanResult, citekey: str) -> Path:
    """The stored source to extract from, or a refusal naming the two ways to put one there."""
    from loom.refs.build import main_tex

    entry = result.bib.get(citekey)
    main = main_tex(result.quilt.root, entry) if entry is not None else None
    if main is None:
        raise EnvError(
            f"loom holds no source for {citekey}, so there is nothing to extract from.\n"
            f"loom refs fetch {citekey} where an identifier will serve it, or loom refs add {citekey} <FILE-OR-DIR> "
            f"for source you already hold."
        )
    return main


@digest.command(name="extract")
@click.argument("citekey")
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=False)
@click.option("--to", "to", default=None, metavar="PATH", help="Write here instead of digests/<citekey>.tex.")
@click.option(
    "--engine", default=None, help="Engine for compiling the reference (default: its magic comment or pdflatex)."
)
@click.option(
    "--no-compile", "no_compile", is_flag=True, help="Skip compiling the reference; number results by emulation."
)
@quilt_option
@click.pass_context
def extract(
    ctx: click.Context,
    citekey: str,
    src: Path | None,
    to: str | None,
    engine: str | None,
    no_compile: bool,
    quilt_path: str | None,
) -> None:
    """Produce digests/CITEKEY.tex mechanically from the reference paper's source (proofs dropped, ids prefixed).

    With no SRC, the source loom holds for CITEKEY: the file in the store declaring `\\documentclass`, which is what `loom refs fetch` or `loom refs add` put there. A path may be given instead, and must be inside the store -- a digest made from a file nobody else holds cites pages nobody else can open.
    """
    result = open_scan(quilt_path)
    root = result.quilt.root
    src = _stored_source(result, citekey) if src is None else _must_be_stored(root, src, citekey)
    target = root / (to or f"digests/{citekey}.tex")
    if target.exists():
        raise EnvError(f"{target.relative_to(root)} exists; use --to to write elsewhere")
    if citekey not in result.bib:
        note(f"warning: {citekey} is not in the bibliography (loom:digest-without-bib)")
    click.echo(f"Reading {src} ...")
    text, report = extract_digest(result, citekey, src, engine=engine, compile=not no_compile)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    click.echo(f"Wrote {target.relative_to(root) if target.is_relative_to(root) else target}")
    click.echo(report.summary())
    rescan = scan(load_quilt(root))
    # mechanical extraction and an agent's reading end in the same place, or half the digest is invisible to
    # every surface that reads results (contract §1.4)
    from loom.refs.proposals import record_extracted

    recorded = record_extracted(rescan, citekey)
    if recorded:
        click.echo(f"recorded {recorded} result(s) in digests/{citekey}.results.json")
    rel = target.relative_to(root).as_posix() if target.is_relative_to(root) else target.as_posix()
    hits = [d for d in rescan.lint if any(loc.file == rel for loc in d.locations) or citekey in d.message]
    if hits:
        click.echo("Lint on the digest:")
        for d in hits:
            click.echo(f"  {d.severity:<8}{d.code:<34}{d.message}")
    else:
        click.echo("Lint on the digest: clean")


@digest.command(name="import")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--as", "as_citekey", default=None, metavar="CITEKEY", help="Rename the digest's citekey on the way in.")
@quilt_option
@click.pass_context
def import_digest(ctx: click.Context, path: Path, as_citekey: str | None, quilt_path: str | None) -> None:
    """Copy a digest from another quilt into digests/, rewriting its id prefix when --as renames the citekey."""
    result = open_scan(quilt_path)
    try:
        plan = plan_digest_import(result, path, as_citekey)
    except ValueError as exc:
        raise ContentError(str(exc)) from exc
    try:
        dest = write_digest_import(result.quilt.root, plan)
    except FileExistsError as exc:
        raise EnvError(
            f"{Path(str(exc)).relative_to(result.quilt.root)} exists; digest import never overwrites"
        ) from exc
    click.echo(
        f"Wrote {dest.relative_to(result.quilt.root)}"
        + (
            f" (renamed {plan.old_citekey} to {plan.citekey}, {plan.renamed} rewrites)"
            if plan.citekey != plan.old_citekey
            else ""
        )
    )
    if plan.missing_packages:
        note(f"requires: {', '.join(plan.missing_packages)} not loaded by the preamble (loom:missing-package)")
    if plan.undeclared_envs:
        note(f"environments not declared in this quilt: {', '.join(plan.undeclared_envs)} (loom:unknown-environment)")
    if plan.citekey not in result.bib:
        note(f"{plan.citekey} is not in the bibliography (loom:digest-without-bib)")
