"""`loom upgrade` (book 12.2): refresh loom.sty and the generated AI-layer files to the installed loom's versions; edited mode files are kept and a `.new` written beside them."""

from __future__ import annotations

from importlib import resources

import click

from loom.cli._quilt import open_quilt, quilt_option


@click.command()
@quilt_option
def upgrade(quilt_path: str | None) -> None:
    """Refresh loom.sty, ai/orientation.md, ai/README.md, the vendor files, and unedited mode files; report edited ones."""
    from loom.ai.layout import upgrade_layer

    quilt = open_quilt(quilt_path)
    root = quilt.root
    sty = resources.files("loom").joinpath("assets", "loom.sty").read_text(encoding="utf-8")
    p = root / "loom.sty"
    if not p.is_file() or p.read_text(encoding="utf-8") != sty:
        p.write_text(sty, encoding="utf-8")
        click.echo("wrote loom.sty")
    else:
        click.echo("loom.sty is current")
    if (root / "ai").is_dir():
        rep = upgrade_layer(root)
        for rel in rep.written:
            click.echo(f"wrote {rel}")
        for rel in rep.kept:
            click.echo(f"kept {rel} (edited); the new shipped version is beside it as {rel}.new")
        if not rep.written and not rep.kept:
            click.echo("ai/ is current")
    else:
        click.echo("no ai/ (loom ai init creates it)")
    click.echo("config.toml and the ledger need no migration")
