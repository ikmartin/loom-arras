"""`loom upgrade`: refresh the generated AI-layer files and the `.gitignore` lines loom relies on to the installed loom's versions; edited mode files are kept and a `.new` written beside them."""

from __future__ import annotations

import click

from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.report import Group, Item, Report, counted
from loom.paths import AI


@click.command()
@click.option("--dry-run", is_flag=True, help="Say which files would be refreshed, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def upgrade(dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Refresh ai/orientation.md, ai/README.md, the permission and MCP client files, unedited mode files and the .gitignore lines loom relies on; report edited ones."""
    from loom.ai.clients import write_clients
    from loom.ai.layout import SHELL, upgrade_layer, variant
    from loom.gitignore import ensure, missing

    quilt = open_quilt(quilt_path)
    root = quilt.root
    written: list[str] = []
    kept: list[str] = []
    beside: list[str] = []
    added = missing(root) if dry_run else ensure(root)
    if added:
        written.append(".gitignore")
    has_ai = (root / AI).is_dir()
    if has_ai:
        shell = variant(root) == SHELL
        rep = upgrade_layer(root, write=not dry_run, shell=shell)
        written += [str(rel) for rel in rep.written]
        # the client files follow the variant: what starts the server over MCP, nothing in a shell
        written += write_clients(root, write=not dry_run, shell=shell).written
        kept += [str(rel) for rel in rep.kept]
        beside = [rel for rel in kept if f"{rel}.new" in rep.new_beside]
    groups = [
        Group(
            "would write" if dry_run else "wrote",
            [
                Item(
                    f"{'would add' if dry_run else 'added'} {', '.join(added)}" if rel == ".gitignore" else "", key=rel
                )
                for rel in written
            ],
            limit=None,
        ),
        Group(
            "kept, as you edited them",
            [
                Item(
                    f"the new version {'would go' if dry_run else 'is'} beside it as {rel.rsplit('/', 1)[-1]}.new"
                    if rel in beside
                    else "",
                    key=rel,
                    fixes=[
                        f"merge {rel}.new into {rel}, then delete {rel}.new: it is not written again until loom ships another"
                    ]
                    if rel in beside
                    else [],
                )
                for rel in kept
            ],
            limit=None,
            problem=True,
        ),
    ]
    if written or kept:
        parts = ([f"{'would write' if dry_run else 'wrote'} {counted(len(written), 'file')}"] if written else []) + (
            [f"{'would keep' if dry_run else 'kept'} {counted(len(kept), 'edited file')}"] if kept else []
        )
        # one file kept with its new version beside it is one file, said once (T5)
        merge = (
            ""
            if not beside
            else (
                ", its new version beside it to merge"
                if len(kept) == 1
                else ", each with its new version beside it to merge"
            )
            if len(beside) == len(kept)
            else f", {len(beside)} with a new version beside it to merge"
        )
        verdict = ("" if dry_run else "upgraded: ") + "; ".join(parts) + merge
    else:
        verdict = "already current" + (": ai/ and .gitignore" if has_ai else ": .gitignore")
    Report(
        verdict,
        dry_run=dry_run,
        ok=not beside,
        groups=[g for g in groups if g.items],
        lines=[] if has_ai else ["no ai/ to upgrade; loom ai init creates it"],
        data={
            "written": written,
            "kept": kept,
            "beside": beside,
            "gitignore": added,
            "ai": has_ai,
        },
    ).emit(as_json)
