"""`loom digest extract | import` (book 8.5, 8.10). Fetching moved to `loom refs fetch`, which fetches on a candidate as well as a declared identifier and checks the title on arrival (plan 0.12 §4.3)."""

from __future__ import annotations

from pathlib import Path

import click

from loom.cli._common import ContentError, EnvError, note
from loom.cli._quilt import open_scan, quilt_option
from loom.digest.extract import extract_digest
from loom.digest.importer import plan_digest_import, write_digest_import
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan


@click.group(name="digest")
def digest() -> None:
    """Digests of cited papers: extract one from a paper's source, or port one in.

    To search what the digests hold, see `loom refs find` (statements) and `loom refs grep` (page text); to read a page, `loom refs page`; for the whole mechanical pass over every cited work, `loom refs build`.
    """


@digest.command(name="extract")
@click.argument("citekey")
@click.argument("src", type=click.Path(exists=True, dir_okay=False, path_type=Path))
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
    src: Path,
    to: str | None,
    engine: str | None,
    no_compile: bool,
    quilt_path: str | None,
) -> None:
    """Produce digests/CITEKEY.tex mechanically from the reference paper whose main file is SRC (proofs dropped, ids prefixed)."""
    result = open_scan(quilt_path)
    root = result.quilt.root
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
