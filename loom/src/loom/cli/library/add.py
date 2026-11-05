"""`loom library add`: the author keeps the documents they hold, a PDF whatever is known about it: under the work it shows it is, or as a work of its own."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from loom.cli._common import EnvError, refuse_under_agent, whoever
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.library._works import one_work, present
from loom.cli.report import Group, Item, Progress, Report, counted


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
    help="The work every FILE is, which is taken at your word for a PDF; without it each is matched to the bibliography by what it shows.",
)
@click.option(
    "--force",
    is_flag=True,
    help="With --for, file a LaTeX source that shows it is another work; the override is recorded.",
)
@click.option(
    "--online", is_flag=True, help="Allow this run to look up the identifier a PDF states, over `[library] online`."
)
@click.option(
    "--as", "as_name", default=None, metavar="NAME", help="Who is filing, when the user config and git do not say."
)
@click.option("--dry-run", is_flag=True, help="Say what would be filed, skipped and refused, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def add_command(
    files: tuple[Path, ...],
    for_work: str | None,
    force: bool,
    online: bool,
    as_name: str | None,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Keep PDFs and LaTeX sources in loom's store, a PDF whatever is known about it.

    A FILE is a PDF, a `.tex` file, or a folder: each PDF in a folder is a document, and a folder holding no PDF is one LaTeX source. Every PDF is copied into the store. It is filed under an entry on a strong match: an identifier on its first pages equals the entry's, or its whole title is the entry's and the entry's first author leads its byline or its file name. Any other PDF becomes a work of its own, its entry made from what it shows: its file name, its document information, its first page. A lookup of the identifier it states, where the network is allowed, only adds to that entry. With `--for`, every FILE is that work's: a PDF is taken at your word, and what it shows to the contrary is reported and recorded. A LaTeX source is filed only on a strong match, skipped with its reason otherwise, and with `--for` refused when it shows it is another work's unless `--force`. A work that holds a document gets the new one beside it under a sibling entry, never over it, unless it is a copy of one of the work's documents: it states that version's identifier, or its title, byline and page count are that document's. A copy is recorded in the ledger and not filed. A PDF's page text is written at once.
    """
    from loom.refs.add import identify, named_for, plan_new_work, withdraw_setting_aside
    from loom.refs.added import added_entry
    from loom.refs.ingest import identify_document, identify_source
    from loom.refs.lookup import key_for
    from loom.refs.pages import sha256_of
    from loom.refs.scan import (
        Filing,
        append_entries,
        bib_file,
        file_document,
        one_work_of,
        plan_filing,
        record_copy_of,
        tree_sha,
    )
    from loom.scan.bib import BibEntry

    if force and not for_work:
        raise EnvError("--force applies only with --for: name the work the document is")
    refuse_under_agent(
        "loom library add",
        "Filing a document under a work is the author's: a wrong PDF under the right entry is read by every anchor into it.",
        as_name,
    )
    docs = _documents(files)
    result = open_scan(quilt_path)
    root = result.quilt.root
    # holds the works this run makes as well, so a second PDF of one is filed beside the first
    bib = dict(result.bib)
    allowed = online or result.quilt.config.online
    target = one_work(result, for_work) if for_work else None
    rows: list[dict[str, Any]] = []
    plans: list[Filing] = []
    refused: list[tuple[Path, str]] = []
    skipped: list[tuple[Path, str]] = []
    #: The command that files each skipped document, for the case its reason shows.
    fixes: dict[Path, str] = {}
    #: A refused document's own work, when it is a version of the work named by --for.
    versions: dict[Path, str] = {}
    where: str | None = None  # the .bib a missing entry goes in, read once and only when needed
    planned: set[Path] = set()
    #: The works this run makes, by their document's hash.
    made: dict[str, str] = {}
    with Progress("reading documents", len(docs)) as progress:
        for path, kind in docs:
            progress.item(path.name)
            row: dict[str, Any] = {"file": str(path), "kind": kind, "strong": [], "citekey": "", "reason": ""}
            rows.append(row)
            if kind == "pdf" and not _is_pdf(path):
                refused.append((path, "it is not a PDF"))
                row.update(outcome="refused", reason="it is not a PDF")
                continue
            if kind == "pdf" and target is None:
                sha = sha256_of(path)
                seen = identify(root, bib, path, online=allowed, offer=sha not in made)
                row.update(strong=seen.matches, reason=seen.weak)
                ck = seen.best or made.get(sha, "")
                if ck:
                    plans.append(Filing(path, ck, kind, sha, _came_from(root, path)))
                    row.update(citekey=ck, forced="")
                    continue
                key = key_for(seen.offer, set(bib))
                f = plan_new_work(root, path, key, seen.offer, _came_from(root, path), planned)
                f.apart, f.nearest = seen.weak, seen.nearest
                assert f.new is not None
                bib[key] = BibEntry(key, "misc", dict(f.new))
                made[sha] = key
                plans.append(f)
                row.update(citekey=key, forced="", new=True)
                continue
            identity = identify_source(path, bib) if kind == "source" else identify_document(path, bib)
            row["strong"] = [{"citekey": m.citekey, "strength": m.strength, "how": m.how} for m in identity.strong]
            forced = ""
            if target is not None and kind == "pdf":
                ck, forced = named_for(identity, bib, target)
            elif target is not None:
                why = identity.refusal_for(target, bib[target])
                if why and not force:
                    refused.append((path, why))
                    row.update(outcome="refused", citekey=target, reason=why)
                    other = next((m.citekey for m in identity.strong if m.citekey != target), "")
                    if other and one_work_of([other, target], bib):
                        versions[path] = other
                    continue
                forced, ck = why, target
            else:
                best = identity.best()
                if len(best) > 1 and (top := one_work_of([m.citekey for m in best], bib)):
                    best = [m for m in best if m.citekey == top] or best[:1]
                if len(best) > 1:
                    why = f"it names {' and '.join(m.citekey for m in best)} equally"
                    refused.append((path, why))
                    row.update(outcome="refused", reason=why)
                    continue
                if not best:
                    skipped.append((path, identity.weak))
                    where = bib_file(result) if where is None else where
                    fixes[path] = _fix_for(identity, where)
                    row.update(outcome="skipped", reason=identity.weak)
                    continue
                ck = best[0].citekey
            sha = sha256_of(path) if kind == "pdf" else tree_sha(path)
            plans.append(Filing(path, ck, kind, sha, _came_from(root, path), forced=forced, named=target is not None))
            row.update(citekey=ck, forced=forced)
    if target is not None and refused:
        shown = "; ".join(f"{p.name}: {why}" for p, why in refused)
        version = next(iter(set(versions.values())), "") if len(set(versions.values())) == 1 else ""
        raise EnvError(
            f"nothing filed under {target}, {shown}. "
            + (
                f"{version} is a version of the same work: loom library add FILE --for {version} files it there"
                if version and len(versions) == len(refused)
                else f"If it is {target}'s, pass --force with --for {target}, and the override is recorded"
            )
        )
    taken, once = set(bib), dict[str, str]()
    entries = []
    for f in plans:
        if f.new is not None:
            once[f.sha] = f.path.name
            continue
        sibling = plan_filing(result.quilt, bib, f, taken, once, planned)
        if sibling is not None:
            entries.append(sibling)
    filed = [f for f in plans if not f.already]
    if not dry_run:
        by = whoever(root, as_name)
        for f in plans:
            if f.kind == "pdf":
                withdraw_setting_aside(root, f.sha, by)
        for f in filed:
            file_document(result.quilt, f, by=by)
            if f.new is not None:
                entries.append(added_entry(f.citekey, f.new, by, source="`loom library add`, added by hand"))
        for f in plans:
            if f.copy_of:
                record_copy_of(result.quilt, bib, f)
        append_entries(result.quilt, entries)
    for f in plans:
        row = next(r for r in rows if r["file"] == str(f.path))
        row.update(
            outcome="skipped" if f.already else "filed",
            reason=f.already or f.apart,
            sibling=f.sibling,
            home=f.home.relative_to(root).as_posix() if f.home is not None and not f.already else "",
            page_text=f.kind == "pdf" and not f.already and not f.unmapped and not dry_run,
            error=f.unmapped,
        )
    held = [f for f in plans if f.already]
    _report(filed, skipped, refused, rows, dry_run, fixes, held).emit(as_json)


def _is_pdf(path: Path) -> bool:
    """Whether a file opens as a PDF does, which is all that is asked of one before it is kept."""
    try:
        with path.open("rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False


def _fix_for(identity: Any, bib: str) -> str:
    """The command that files a skipped LaTeX source, for the reason it was skipped: the entry to write for a source nothing matches."""
    where = bib or "your bibliography"
    return f"add its entry to {where}, then loom library add FILE files it"


def _report(
    filed: list[Any],
    skipped: list[tuple[Path, str]],
    refused: list[tuple[Path, str]],
    rows: list[dict[str, Any]],
    dry_run: bool,
    how: dict[Path, str],
    held: list[Any] | None = None,
) -> Report:
    """Every document as filed, already held, skipped or refused, each with its reason (audit §4), and under a skipped one the command `how` gives for it.

    A PDF kept as a work of its own says the title it was given and the entry nearest it. A document the store holds already is said once under one heading, beside the work it is filed under; only a copy of another work's document says more.
    """
    held = held or []
    items: list[Item] = []
    for f in filed:
        what = "PDF" if f.kind == "pdf" else "LaTeX source"
        titled = f'as the new work {f.citekey}, titled "{f.new["title"]}"' if f.new else f"as {f.citekey}'s {what}"
        text = f"{f.path.name} {titled}" + (
            f", beside its first document as {f.sibling}"
            if f.sibling
            else ", in place of the document you set aside"
            if f.replaces
            else ""
        )
        if f.kind == "pdf" and not dry_run:
            text += f", without page text ({f.unmapped})" if f.unmapped else ", with its page text"
        if f.forced:
            text += f"; on your word, though {f.forced}"
        work = f.sibling or f.citekey
        fixes = [f"loom library update {work} --only extract makes its digest"] if f.kind == "source" else []
        if f.new and f.nearest:
            fixes.append(f"loom library add FILE --for {f.nearest} files it there instead, if that is what it is")
        items.append(Item(text, fixes=fixes))
    total = len(filed) + len(held) + len(skipped) + len(refused)
    verdict = (
        f"{counted(total, 'document')}: {len(filed)} {'would be filed' if dry_run else 'filed'}, "
        + (f"{len(held)} already in loom's store, " if held else "")
        + f"{len(skipped)} skipped, {len(refused)} refused"
    )
    return Report(
        verdict,
        ok=not (skipped or refused),
        dry_run=dry_run,
        groups=present(
            Group(
                "refused",
                [Item(f"{p.name}: {why}") for p, why in refused],
                problem=True,
                limit=None,
                next="loom library add FILE --for WORK files a source under the one it is"
                if any(p.suffix.lower() != ".pdf" for p, _ in refused)
                else None,
            ),
            Group(
                "skipped",
                [Item(f"{p.name}: {why}", fixes=[how[p]] if p in how else []) for p, why in skipped],
                limit=None,
            ),
            Group("would be filed" if dry_run else "filed", items, limit=None),
            Group(
                "already in loom's store, under the work each is",
                [
                    Item(
                        f.path.name
                        + (
                            ""
                            if f.already.startswith(("already in loom's store", "already filed"))
                            else f": {f.already}"
                        ),
                        key=f.citekey,
                    )
                    for f in held
                ],
                limit=None,
            ),
        ),
        notes=["the store is not in version control: a collaborator fetches or adds their own copy"]
        if filed and not dry_run
        else [],
        data={"filed": len(filed), "skipped": len(skipped), "refused": len(refused), "documents": rows},
    )


#: The commands this module adds to `loom library`.
COMMANDS: list[click.Command] = [add_command]
