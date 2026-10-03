"""`loom upgrade` (book 12.2): refresh loom.sty and the generated AI-layer files to the installed loom's versions; edited mode files are kept and a `.new` written beside them."""

from __future__ import annotations

from importlib import resources

import click

from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.report import Group, Item, Report, counted


@click.command()
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def upgrade(as_json: bool, quilt_path: str | None) -> None:
    """Refresh loom.sty, ai/orientation.md, ai/README.md, the vendor files, and unedited mode files; report edited ones."""
    from loom.ai.layout import upgrade_layer
    from loom.gitignore import ensure

    quilt = open_quilt(quilt_path)
    root = quilt.root
    written: list[str] = []
    kept: list[str] = []
    added = ensure(root)
    if added:
        written.append(".gitignore")
    sty = resources.files("loom").joinpath("assets", "loom.sty").read_text(encoding="utf-8")
    p = root / "loom.sty"
    if not p.is_file() or p.read_text(encoding="utf-8") != sty:
        p.write_text(sty, encoding="utf-8")
        written.append("loom.sty")
    has_ai = (root / "ai").is_dir()
    if has_ai:
        rep = upgrade_layer(root)
        written += [str(rel) for rel in rep.written]
        kept += [str(rel) for rel in rep.kept]
    beside = [rel for rel in kept if (root / f"{rel}.new").is_file()]
    groups = [
        Group(
            "wrote",
            [Item(f"added {', '.join(added)}" if rel == ".gitignore" else "", key=rel) for rel in written],
            limit=None,
        ),
        Group(
            "kept, as you edited them",
            [
                Item(f"the new version is beside it as {rel.rsplit('/', 1)[-1]}.new" if rel in beside else "", key=rel)
                for rel in kept
            ],
            limit=None,
            problem=True,
        ),
    ]
    if written or kept:
        parts = ([f"wrote {counted(len(written), 'file')}"] if written else []) + (
            [f"kept {counted(len(kept), 'edited file')}"] if kept else []
        )
        verdict = (
            "upgraded: "
            + "; ".join(parts)
            + (f", {len(beside)} with a new version beside it to merge" if beside else "")
        )
    else:
        verdict = "already current: loom.sty" + (" and ai/" if has_ai else "")
    Report(
        verdict,
        ok=not beside,
        groups=[g for g in groups if g.items],
        lines=[] if has_ai else ["no ai/ to upgrade; loom ai init creates it"],
        data={"written": written, "kept": kept, "beside": beside, "gitignore": added, "ai": has_ai},
    ).emit(as_json)
