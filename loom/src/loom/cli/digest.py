"""`loom digest extract | import` (book 8.5, 8.10). Fetching moved to `loom refs fetch`, which fetches on a candidate as well as a declared identifier and checks the title on arrival (plan 0.12 §4.3)."""

from __future__ import annotations

from pathlib import Path

import click

from loom.cli._common import ContentError, EnvError, note
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.diagnostics import groups as diagnostic_groups
from loom.cli.diagnostics import has_errors, tally
from loom.cli.report import Group, Item, Progress, Report, counted
from loom.digest.extract import extract_digest
from loom.digest.importer import plan_digest_import, write_digest_import
from loom.scan.quilt import load_quilt
from loom.scan.scan import ScanResult, scan


@click.group(name="digest")
def digest() -> None:
    """Make digests of cited papers: extract one from a paper's source, or port one in.

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
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def extract(
    citekey: str,
    src: Path | None,
    to: str | None,
    engine: str | None,
    no_compile: bool,
    as_json: bool,
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
    with Progress(f"extracting {citekey}") as progress:
        progress.item(src.name)
        text, report = extract_digest(result, citekey, src, engine=engine, compile=not no_compile)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        progress.next_stage("recording its results")
        rescan = scan(load_quilt(root))
        # mechanical extraction and an agent's reading end in the same place, or half the digest is invisible to every surface that reads results (contract §1.4)
        from loom.refs.proposals import record_extracted

        recorded = record_extracted(rescan, citekey)
    rel = target.relative_to(root).as_posix() if target.is_relative_to(root) else target.as_posix()
    hits = [d for d in rescan.lint if any(loc.file == rel for loc in d.locations) or citekey in d.message]
    total = sum(report.by_taxon.values())
    lines = ["", *report.summary().splitlines()]
    if recorded:
        lines.append(f"Recorded {counted(recorded, 'result')} in digests/{citekey}.results.json")
    # the digest is the subject here, so its diagnostics are listed in full rather than summarised as a cited work's
    bad = has_errors(hits, None)
    Report(
        f"wrote {rel}: {counted(total, 'result')} from {citekey}; its lint: {tally(hits, None).replace(' in your documents', '')}",
        ok=not bad,
        lines=lines,
        groups=diagnostic_groups(hits, None),
        data={
            "citekey": citekey,
            "digest": rel,
            "results": total,
            "recorded": recorded,
            "numbering": report.numbering,
            "skipped": list(report.skipped),
            "requires": list(report.requires),
            "diagnostics": [d.to_dict() for d in hits],
        },
    ).emit(as_json)


@digest.command(name="import")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--as", "as_citekey", default=None, metavar="CITEKEY", help="Rename the digest's citekey on the way in.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def import_digest(path: Path, as_citekey: str | None, as_json: bool, quilt_path: str | None) -> None:
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
    rel = dest.relative_to(result.quilt.root).as_posix()
    warnings = []
    if plan.missing_packages:
        warnings.append(
            Item(f"requires {', '.join(plan.missing_packages)}, not loaded by the preamble", key="loom:missing-package")
        )
    if plan.undeclared_envs:
        warnings.append(
            Item(
                f"environments not declared in this quilt: {', '.join(plan.undeclared_envs)}",
                key="loom:unknown-environment",
            )
        )
    if plan.citekey not in result.bib:
        warnings.append(Item(f"{plan.citekey} is not in the bibliography", key="loom:digest-without-bib"))
    renamed = plan.citekey != plan.old_citekey
    Report(
        f"wrote {rel}"
        + (f", renamed {plan.old_citekey} to {plan.citekey} in {counted(plan.renamed, 'place')}" if renamed else "")
        + (f"; {counted(len(warnings), 'warning')}" if warnings else ""),
        ok=not warnings,
        groups=[Group("warnings", warnings, limit=None, next="loom lint")] if warnings else [],
        data={
            "digest": rel,
            "citekey": plan.citekey,
            "renamed_from": plan.old_citekey if renamed else None,
            "rewrites": plan.renamed,
            "missing_packages": list(plan.missing_packages),
            "undeclared_envs": list(plan.undeclared_envs),
            "in_bibliography": plan.citekey in result.bib,
        },
    ).emit(as_json)
