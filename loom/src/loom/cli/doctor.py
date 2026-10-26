"""`loom doctor`: the one command to run when something is off -- the machine's tools, the author name and the arras bundle, and the quilt's own setup when run inside one."""

from __future__ import annotations

import click

from loom.cli._quilt import quilt_option
from loom.doctor import run_doctor


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Machine-readable report on stdout.")
@click.option("--strict", is_flag=True, help="Count a warning as a failure: exit 2 when any item warns.")
@quilt_option
def doctor(as_json: bool, strict: bool, quilt_path: str | None) -> None:
    """Check the TeX toolchain and what loom needs of it, poppler, git, the author name and the arras bundle; inside a quilt, also its engine, its generated files, its .gitignore and its config.

    Each item is ok, warn (works, but you will hit it) or fail (a command you need will refuse), with the command that fixes it. Exits 0 when nothing fails and 2 when anything does; under --strict a warning counts as a failure. Writes nothing; a tool is run only to ask its version or test what loom needs of it, and one that has not answered in 10 s is reported as hung.
    """
    run_doctor(quilt_path, strict=strict).report().emit(as_json)
