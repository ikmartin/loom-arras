"""`loom library add`: the author files the documents they hold, each under the work it shows it is (book 8.14, 8.16)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from loom.cli._common import EnvError, refuse_under_agent, whoever
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.library._works import one_work, present
from loom.cli.report import Group, Item, Report, counted


def _documents(paths: tuple[Path, ...]) -> list[tuple[Path, str]]:
    """(path, kind) for every document the arguments hold: each PDF, a `.tex` file, or a folder holding no PDF as one LaTeX source.

    Checked before anything is read or written; an argument holding neither is refused by name (K3).
    """
    out: list[tuple[Path, str]] = []
    for path in paths:
        if path.is_dir():
            pdfs = sorted(p for p in path.rglob("*.pdf") if p.is_file())
            if pdfs:
                out += [(p, "pdf") for p in pdfs]
            elif any(path.rglob("*.tex")):
                out.append((path, "source"))
            else:
                raise EnvError(f"{path} holds no PDF and no LaTeX source")
        elif path.suffix.lower() == ".pdf":
            out.append((path, "pdf"))
        elif path.suffix.lower() == ".tex":
            out.append((path, "source"))
        else:
            raise EnvError(f"{path.name} is neither a PDF nor LaTeX source; loom files those two things")
    return out


def _came_from(root: Path, path: Path) -> str:
    """Where a document came from, as the ledger and its entry record it: quilt-relative inside the quilt, else its name."""
    resolved = path.resolve()
    return resolved.relative_to(root.resolve()).as_posix() if resolved.is_relative_to(root.resolve()) else path.name


@click.command(name="add")
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path), metavar="FILE...")
@click.option(
    "--for",
    "for_work",
    default=None,
    metavar="WORK",
    help="The work every FILE is; without it each is matched to the bibliography by what it shows.",
)
@click.option(
    "--force",
    is_flag=True,
    help="With --for, file a document that does not show it is that work; the override is recorded.",
)
@click.option(
    "--as", "as_name", default=None, metavar="NAME", help="Who is filing, when the user config and git do not say."
)
@click.option("--dry-run", is_flag=True, help="Say what would be filed, skipped and refused, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def add_command(
    files: tuple[Path, ...],
    for_work: str | None,
    force: bool,
    as_name: str | None,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """File PDFs and LaTeX sources in loom's store, each under the work it shows it is.

    A FILE is a PDF, a `.tex` file, or a folder: each PDF in a folder is a document, and a folder holding no PDF is one LaTeX source. A document is filed on a strong match only: an identifier on its first pages equals the entry's, or its whole title is the entry's and the entry's first author leads its byline. Anything weaker is skipped with its reason, and a document naming two entries equally is refused. With `--for`, every FILE is that work's: a PDF that does not show it, or any document that shows it is another work's, is refused unless `--force`, and a source is refused when its own title is another's. A work that holds a document gets the new one beside it under a sibling entry, never over it (book 8.16), and a PDF's page text is written at once.
    """
    from loom.refs.ingest import identify_document, identify_source
    from loom.refs.pages import sha256_of
    from loom.refs.scan import Filing, append_entries, file_document, plan_filing, tree_sha

    if force and not for_work:
        raise EnvError("--force applies only with --for: name the work the document is")
    refuse_under_agent(
        "loom library add",
        "Filing a document under a work is the author's: a wrong PDF under the right entry is read by every anchor into it.",
        as_name,
    )
    docs = _documents(files)
    result = open_scan(quilt_path)
    root, bib = result.quilt.root, result.bib
    target = one_work(result, for_work) if for_work else None
    rows: list[dict[str, Any]] = []
    plans: list[Filing] = []
    refused: list[tuple[Path, str]] = []
    skipped: list[tuple[Path, str]] = []
    for path, kind in docs:
        identity = identify_source(path, bib) if kind == "source" else identify_document(path, bib)
        strong = [{"citekey": m.citekey, "strength": m.strength, "how": m.how} for m in identity.strong]
        row: dict[str, Any] = {"file": str(path), "kind": kind, "strong": strong, "citekey": "", "reason": ""}
        rows.append(row)
        forced = ""
        if target is not None:
            why = identity.refusal_for(target, bib[target])
            if why and not force:
                refused.append((path, why))
                row.update(outcome="refused", citekey=target, reason=why)
                continue
            forced, ck = why, target
        else:
            best = identity.best()
            if len(best) > 1:
                why = f"it names {' and '.join(m.citekey for m in best)} equally"
                refused.append((path, why))
                row.update(outcome="refused", reason=why)
                continue
            if not best:
                skipped.append((path, identity.weak))
                row.update(outcome="skipped", reason=identity.weak)
                continue
            ck = best[0].citekey
        sha = sha256_of(path) if kind == "pdf" else tree_sha(path)
        plans.append(Filing(path, ck, kind, sha, _came_from(root, path), forced=forced))
        row.update(citekey=ck, forced=forced)
    if target is not None and refused:
        shown = "; ".join(f"{p.name}: {why}" for p, why in refused)
        raise EnvError(
            f"nothing filed under {target}, {shown}. "
            f"If it is {target}'s, pass --force with --for {target}, and the override is recorded"
        )
    taken, seen = set(bib), dict[str, str]()
    entries = []
    for f in plans:
        sibling = plan_filing(result.quilt, bib, f, taken, seen)
        if sibling is not None:
            entries.append(sibling)
    filed = [f for f in plans if not f.already]
    if not dry_run:
        by = whoever(root, as_name)
        for f in filed:
            file_document(result.quilt, f, by=by)
        append_entries(result.quilt, entries)
    for f in plans:
        row = next(r for r in rows if r["file"] == str(f.path))
        row.update(
            outcome="skipped" if f.already else "filed",
            reason=f.already,
            sibling=f.sibling,
            home=f.home.relative_to(root).as_posix() if f.home is not None and not f.already else "",
            page_text=f.kind == "pdf" and not f.already and not f.unmapped and not dry_run,
            error=f.unmapped,
        )
    skipped += [(f.path, f.already) for f in plans if f.already]
    _report(filed, skipped, refused, rows, dry_run).emit(as_json)


def _report(
    filed: list[Any],
    skipped: list[tuple[Path, str]],
    refused: list[tuple[Path, str]],
    rows: list[dict[str, Any]],
    dry_run: bool,
) -> Report:
    """Every document as filed, skipped or refused, each with its reason (audit §4)."""
    items: list[Item] = []
    for f in filed:
        what = "PDF" if f.kind == "pdf" else "LaTeX source"
        text = f"{f.path.name} as {f.citekey}'s {what}" + (
            f", beside its first document as {f.sibling}" if f.sibling else ""
        )
        if f.kind == "pdf" and not dry_run:
            text += f", without page text ({f.unmapped})" if f.unmapped else ", with its page text"
        if f.forced:
            text += f"; forced, though {f.forced}"
        work = f.sibling or f.citekey
        fixes = [f"loom library update {work} --only extract makes its digest"] if f.kind == "source" else []
        items.append(Item(text, fixes=fixes))
    total = len(filed) + len(skipped) + len(refused)
    verdict = (
        f"{counted(total, 'document')}: {len(filed)} {'would be filed' if dry_run else 'filed'}, "
        f"{len(skipped)} skipped, {len(refused)} refused"
    )
    return Report(
        verdict,
        ok=not (skipped or refused),
        dry_run=dry_run,
        groups=present(
            Group(
                "refused: it names two entries equally",
                [Item(f"{p.name}: {why}") for p, why in refused],
                problem=True,
                limit=None,
                next="loom library add FILE --for WORK files it under the one it is",
            ),
            Group(
                "skipped",
                [Item(f"{p.name}: {why}") for p, why in skipped],
                limit=None,
                next="loom library add FILE --for WORK files a document you know is that work",
            ),
            Group("would be filed" if dry_run else "filed", items, limit=None),
        ),
        notes=["the store is not in version control: a collaborator fetches or adds their own copy"]
        if filed and not dry_run
        else [],
        data={"filed": len(filed), "skipped": len(skipped), "refused": len(refused), "documents": rows},
    )


#: The commands this module adds to `loom library`.
COMMANDS: list[click.Command] = [add_command]
