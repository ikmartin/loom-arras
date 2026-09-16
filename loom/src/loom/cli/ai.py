"""`loom ai ...` (book 12.8). M3 ships `discard`; init, orient, start, promote, and check arrive at M6."""

from __future__ import annotations

from pathlib import Path

import click

from loom.cli._common import ContentError, EnvError
from loom.cli._quilt import open_quilt, quilt_option
from loom.records.annotations import load_record, record_paths


@click.group()
def ai() -> None:
    """The optional AI layer: runs, orientation, promotion, and discarding review records."""


@ai.command()
@click.argument("run", required=False, default=None)
@click.option(
    "--before", default=None, metavar="DATE", help="Discard every record created before this date (YYYY-MM-DD)."
)
@click.option("--author", default=None, help="Discard every record whose author matches.")
@click.option("--target", default=None, help="Discard every record with an annotation on this key.")
@click.option("--undo", is_flag=True, help="Reverse: mark matching records not discarded.")
@quilt_option
def discard(
    run: str | None, before: str | None, author: str | None, target: str | None, undo: bool, quilt_path: str | None
) -> None:
    """Flag a run's or a comment session's records ignored (or unflag with --undo). Nothing is deleted."""
    quilt = open_quilt(quilt_path)
    root = quilt.root
    paths: list[Path] = []
    if run:
        p = Path(run).expanduser()
        if not p.is_absolute():
            p = root / p
        if p.is_dir():
            p = p / "annotations.json"
        if not p.is_file():
            raise EnvError(f"no record at {run}")
        paths.append(p)
    elif before or author or target:
        for p in record_paths(root):
            rec = load_record(root, p)
            if isinstance(rec, str):
                continue
            created = min((a.created for a in rec.annotations), default="")
            if before and not (created and created[:10] < before):
                continue
            if author and not any(a.author_id == author for a in rec.annotations):
                continue
            if target and not any(a.target_key == target for a in rec.annotations):
                continue
            paths.append(p)
    else:
        raise EnvError("give RUN, or --before, --author, or --target")
    if not paths:
        click.echo("no matching records")
        return
    for p in paths:
        rec = load_record(root, p)
        if isinstance(rec, str):
            raise ContentError(rec)
        rec.discarded = not undo
        rec.write()
        toml = p.parent / "run.toml"
        if toml.is_file():
            text = toml.read_text(encoding="utf-8")
            if "discarded" in text:
                import re

                text = re.sub(r"discarded\s*=\s*(true|false)", f"discarded = {'false' if undo else 'true'}", text)
            else:
                text = text.rstrip("\n") + f"\ndiscarded = {'false' if undo else 'true'}\n"
            toml.write_text(text, encoding="utf-8")
        click.echo(f"{'restored' if undo else 'discarded'} {p.relative_to(root).as_posix()}")
