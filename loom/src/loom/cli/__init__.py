"""The `loom` command group. Subcommands register themselves here so that `--help` and the generated CLI reference come from one tree."""

from __future__ import annotations

import click

from loom.cli.doctor import doctor
from loom.version import __version__

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, "--version", "-V", prog_name="loom", message="%(prog)s %(version)s")
def main() -> None:
    """loom: a tool for atomized mathematical development.

    Every command except `init` and `doctor` runs against the nearest quilt, found by walking up from the current directory to a `config.toml` with a [quilt] table.
    """


main.add_command(doctor)

__all__ = ["main"]
