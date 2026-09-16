"""`loom refs path | add` (book 8.9): where a cited work's fetched artifacts are, and how to put one there by hand."""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, EnvError, note
from loom.cli._quilt import open_scan, quilt_option
from loom.refs.identity import primary
from loom.scan.scan import ScanResult


def _home(result: ScanResult, citekey: str) -> Path:
    """The work's directory under `refs/`, or a refusal naming what is missing."""
    entry = result.bib.get(citekey)
    if entry is None:
        raise EnvError(f"{citekey} is not in the bibliography, so it has no identity to file under")
    wid = primary(entry)
    assert wid is not None  # identify() always yields at least a synthetic id for a real entry
    return result.quilt.root / "refs" / wid.path


@click.group(name="refs")
def refs() -> None:
    """Fetched works: where their artifacts are, and how to add one by hand."""


@refs.command(name="path")
@click.argument("citekey")
@click.option("--pdf", "want", flag_value="pdf", help="The PDF rather than the directory.")
@click.option("--src", "want", flag_value="src", help="The unpacked source rather than the directory.")
@quilt_option
@click.pass_context
def path_command(ctx: click.Context, citekey: str, want: str | None, quilt_path: str | None) -> None:
    """Print where CITEKEY's fetched artifacts live. Nothing under refs/ is meant to be navigated by hand."""
    result = open_scan(quilt_path)
    home = _home(result, citekey)
    target = home if want is None else (home / "paper.pdf" if want == "pdf" else home / "src")
    click.echo(target)
    if not target.exists():
        # printed anyway: the path is where it *would* go, which is what `refs add` and `digest fetch` need
        note(f"nothing there yet; loom digest fetch {citekey}" + (" --pdf" if want == "pdf" else ""))
        ctx.exit(EXIT_CONTENT)


@refs.command(name="add")
@click.argument("citekey")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--force", is_flag=True, help="Replace an artifact that is already there.")
@quilt_option
@click.pass_context
def add_command(ctx: click.Context, citekey: str, file: Path, force: bool, quilt_path: str | None) -> None:
    """File FILE as CITEKEY's PDF under refs/.

    A published PDF usually sits behind a subscription that loom cannot and should not automate past, so the author supplies the bytes and names the citekey they know; loom resolves the identifier and does the filing.
    """
    result = open_scan(quilt_path)
    if file.suffix.lower() != ".pdf":
        raise EnvError(f"{file.name} is not a PDF; only a work's PDF can be added by hand (its source is fetched)")
    home = _home(result, citekey)
    dest = home / "paper.pdf"
    if dest.exists() and not force:
        raise EnvError(f"{dest.relative_to(result.quilt.root)} exists; pass --force to replace it")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(file, dest)
    click.echo(f"Wrote {dest.relative_to(result.quilt.root)}")
    note("refs/ is not in version control: a collaborator cloning the quilt fetches or adds their own copy")
