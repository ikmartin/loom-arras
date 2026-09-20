"""The `loom` command group. Subcommands register themselves here so that `--help` and the generated CLI reference come from one tree."""

from __future__ import annotations

import click

from loom.cli.ai import ai
from loom.cli.build_cmd import build_command
from loom.cli.build_cmds import check, compile, source
from loom.cli.digest import digest
from loom.cli.doctor import doctor
from loom.cli.graph import deps, unravel
from loom.cli.history_cmds import canonicalize, canonise, canonize, draft, fork, history, linearize, live, revert, stamp
from loom.cli.lint_cmd import lint_command
from loom.cli.nodes import delete, new, search
from loom.cli.paper import atomize, id_command, import_command, inline_command
from loom.cli.quilt import init
from loom.cli.refs import refs
from loom.cli.review import accept, comment, status
from loom.cli.serve_cmd import serve
from loom.cli.upgrade import upgrade
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
main.add_command(id_command)
main.add_command(import_command)
main.add_command(atomize)
main.add_command(inline_command)
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
main.add_command(refs)
main.add_command(build_command)
main.add_command(compile)
main.add_command(check)
main.add_command(source)
main.add_command(serve)
main.add_command(accept)
main.add_command(comment)
main.add_command(status)
main.add_command(ai)
main.add_command(digest)
main.add_command(upgrade)
main.add_command(draft)
main.add_command(canonize)
main.add_command(canonicalize)
main.add_command(canonise)
main.add_command(stamp)
main.add_command(fork)
main.add_command(revert)
main.add_command(live)
main.add_command(linearize)
main.add_command(history)

__all__ = ["main"]
