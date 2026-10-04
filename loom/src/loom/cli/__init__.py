"""The `loom` command group. Subcommands register themselves here so that `--help` and the generated CLI reference come from one tree."""

from __future__ import annotations

import click

from loom.cli.adopt import adopt
from loom.cli.ai import ai
from loom.cli.build_cmd import build_command
from loom.cli.build_cmds import check, compile, source
from loom.cli.doctor import doctor
from loom.cli.graph import deps, downstream
from loom.cli.help import LoomGroup
from loom.cli.history_cmds import (
    draft,
    fork,
    history,
    linearize,
    live,
    mv,
    revert,
    stamp,
)
from loom.cli.library import library
from loom.cli.link_cmd import link_command
from loom.cli.lint_cmd import lint_command
from loom.cli.nodes import new, search
from loom.cli.paper import atomize, deloom_command, id_command, import_command
from loom.cli.quilt import init
from loom.cli.review import accept, annotate, status
from loom.cli.serve_cmd import serve
from loom.cli.session import session
from loom.cli.sync import sync
from loom.cli.upgrade import upgrade
from loom.version import __version__

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(cls=LoomGroup, context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, "--version", "-V", prog_name="loom", message="%(prog)s %(version)s")
def main() -> None:
    """loom: a tool for atomized mathematical development.

    Every command except `init` and `doctor` runs against the nearest quilt, found by walking up from the current directory to a `config.toml` with a [quilt] table; `doctor` checks that quilt too when there is one.
    """


main.add_command(doctor)
main.add_command(session)
main.add_command(init)
main.add_command(new)
main.add_command(id_command)
main.add_command(import_command)
main.add_command(atomize)
main.add_command(deloom_command)
main.add_command(search)
main.add_command(deps)
main.add_command(downstream)
main.add_command(lint_command)
main.add_command(link_command)
main.add_command(library)
main.add_command(build_command)
main.add_command(compile)
main.add_command(check)
main.add_command(source)
main.add_command(serve)
main.add_command(accept)
main.add_command(annotate)
main.add_command(status)
main.add_command(ai)
main.add_command(upgrade)
main.add_command(draft)
main.add_command(adopt)
main.add_command(stamp)
main.add_command(fork)
main.add_command(revert)
main.add_command(live)
main.add_command(mv)
main.add_command(linearize)
main.add_command(history)
main.add_command(sync)

__all__ = ["main"]
