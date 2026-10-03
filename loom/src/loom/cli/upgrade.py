"""`loom upgrade` (book 12.2): refresh loom.sty and the generated AI-layer files to the installed loom's versions; edited mode files are kept and a `.new` written beside them."""

from __future__ import annotations

from importlib import resources

import click

from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.report import Group, Item, Report, counted


@click.command()
@click.option("--dry-run", is_flag=True, help="Say which files would be refreshed, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def upgrade(dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Refresh loom.sty, ai/orientation.md, ai/README.md, the vendor files, and unedited mode files; report edited ones."""
    from loom.ai.layout import upgrade_layer
    from loom.gitignore import ensure, missing

    quilt = open_quilt(quilt_path)
    root = quilt.root
    written: list[str] = []
    kept: list[str] = []
    beside: list[str] = []
    added = missing(root) if dry_run else ensure(root)
    if added:
        written.append(".gitignore")
    sty = resources.files("loom").joinpath("assets", "loom.sty").read_text(encoding="utf-8")
    p = root / "loom.sty"
    if not p.is_file() or p.read_text(encoding="utf-8") != sty:
        if not dry_run:
            p.write_text(sty, encoding="utf-8")
        written.append("loom.sty")
    has_ai = (root / "ai").is_dir()
    if has_ai:
        rep = upgrade_layer(root, write=not dry_run)
        written += [str(rel) for rel in rep.written]
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
        verdict = (
            ("" if dry_run else "upgraded: ")
            + "; ".join(parts)
            + (f", {len(beside)} with a new version beside it to merge" if beside else "")
        )
    else:
        verdict = "already current: loom.sty" + (" and ai/" if has_ai else "")
    Report(
        verdict,
        dry_run=dry_run,
        ok=not beside,
        groups=[g for g in groups if g.items],
        lines=[] if has_ai else ["no ai/ to upgrade; loom ai init creates it"],
        data={"written": written, "kept": kept, "beside": beside, "gitignore": added, "ai": has_ai},
    ).emit(as_json)
