"""The `loom` command group. Subcommands register themselves here so that `--help` and the generated CLI reference come from one tree."""

from __future__ import annotations

import click

from loom.cli.ai import ai
from loom.cli.build_cmd import build_command
from loom.cli.build_cmds import assemble, bundle, check, compile
from loom.cli.doctor import doctor
from loom.cli.graph import deps, unravel
from loom.cli.lint_cmd import lint_command
from loom.cli.nodes import delete, new, search
from loom.cli.quilt import init
from loom.cli.review import accept, comment, status
from loom.cli.serve_cmd import serve
from loom.version import __version__

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, "--version", "-V", prog_name="loom", message="%(prog)s %(version)s")
def main() -> None:
    """loom: a tool for atomized mathematical development.

    Every command except `init` and `doctor` runs against the nearest quilt, found by walking up from the current directory to a `config.toml` with a [quilt] table.
    """


main.add_command(doctor)
main.add_command(init)
main.add_command(new)
main.add_command(search)
main.add_command(delete)
main.add_command(delete, name="rm")
main.add_command(delete, name="remove")
main.add_command(deps)
main.add_command(unravel)
main.add_command(unravel, name="downstream")
main.add_command(unravel, name="reach")
main.add_command(unravel, name="pop")
main.add_command(lint_command)
main.add_command(build_command)
main.add_command(bundle)
main.add_command(compile)
main.add_command(assemble)
main.add_command(check)
main.add_command(serve)
main.add_command(accept)
main.add_command(comment)
main.add_command(status)
main.add_command(ai)

__all__ = ["main"]
