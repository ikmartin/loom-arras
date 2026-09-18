"""`loom upgrade` (book 12.2): refresh loom.sty and the generated AI-layer files to the installed loom's versions; edited mode files are kept and a `.new` written beside them."""

from __future__ import annotations

from importlib import resources

import click

from loom.cli._quilt import open_quilt, quilt_option
from loom.history.migrate import migrate_history
from loom.refs.migrate import migrate


@click.command()
@quilt_option
def upgrade(quilt_path: str | None) -> None:
    """Refresh loom.sty, ai/orientation.md, ai/README.md, the vendor files, and unedited mode files; report edited ones. Also brings the records to the current layout: snapshots into the history's texts/, `drafts` renamed `drafting` in config.toml."""
    from loom.ai.layout import upgrade_layer
    from loom.records.lastseen import ensure_gitignore_line

    quilt = open_quilt(quilt_path)
    root = quilt.root
    if ensure_gitignore_line(root):
        click.echo("wrote .gitignore (loom's last-seen cache)")
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
    refs_rep = migrate(root)
    for line in refs_rep.moved:
        click.echo(f"moved {line}")
    for key in refs_rep.retired:
        click.echo(f"removed {key} from config.toml (withdrawn; it did nothing)")
    if refs_rep.unknown:
        click.echo(
            f"provenance split for {', '.join(refs_rep.unknown)}: the recorded identifier names the published work, so "
            "what the statements were extracted from is unknown; loom:unverified-locators names it until you say"
        )
    if not refs_rep.done:
        click.echo("references are current")
    hist_rep = migrate_history(root, quilt.history_dir)
    if hist_rep.moved:
        click.echo(f"moved {len(hist_rep.moved)} snapshots into {quilt.config.history}/texts/")
    if hist_rep.renamed:
        click.echo("renamed [quilt] drafts to drafting in config.toml (nothing moved)")
    if not refs_rep.retired and not hist_rep.done:
        click.echo("config.toml and the ledger need no migration")
