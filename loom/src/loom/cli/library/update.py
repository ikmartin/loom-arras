"""`loom library update`: everything a machine can make about the works a quilt cites, every step or one (plan 0.18.5)."""

from __future__ import annotations

import click

from loom.cli._common import EnvError, agent_marker
from loom.cli._quilt import open_quilt, open_scan, quilt_option
from loom.cli.report import Progress
from loom.refs.build import STEPS, WORK_STEPS


@click.command(name="update")
@click.argument("work_args", nargs=-1, metavar="[WORK]...")
@click.option(
    "--only",
    type=click.Choice(STEPS),
    default=None,
    help="Run one step: gather (the bibliography, from the documents and the landmarks), resolve, fetch, extract or map.",
)
@click.option(
    "--redo",
    is_flag=True,
    help="Do the steps again where they are done: ask the lookups again, re-extract, re-map; verified results are kept.",
)
@click.option(
    "--online",
    is_flag=True,
    help="Let this run look identifiers up and fetch documents, without setting [library] online in config.toml.",
)
@click.option(
    "--no-candidates", is_flag=True, help="Fetch only on identifiers an entry declares, never on a lookup's candidate."
)
@click.option(
    "--no-compile",
    is_flag=True,
    help="Extract without compiling each paper; its numbering is emulated, and the digest says so.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Say what each step would act on, from what is on disk; no network, nothing written.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def update_command(
    work_args: tuple[str, ...],
    only: str | None,
    redo: bool,
    online: bool,
    no_candidates: bool,
    no_compile: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Make what a machine can about the cited works: gather the bibliography, look up, fetch, extract digests, map pages.

    Each step is a no-op where its work is done, so a second run does only what is new. WORK narrows every step to the works it names (a citekey, its identifier, a fragment of one or of an author or title, or a result id); naming works leaves gathering out, since it reads the whole bibliography. Looking up and fetching use the network only under `[library] online = true` or `--online`, and an agent only under the config's: it may not grant itself the network. Offline, every local step still runs. Progress shows on stderr.
    """
    from loom.refs.build import plan_report, planned, survey
    from loom.refs.scan import scan_bibliography
    from loom.refs.update import named, update

    quilt = open_quilt(quilt_path)
    marker = agent_marker()
    if online and marker and not quilt.config.online:
        raise EnvError(
            f"--online is the author's to give, and an agent is running this shell ({marker} is set): "
            "the author sets online = true under [library] in config.toml, or runs this in a terminal of their own"
        )
    steps = (only,) if only else STEPS
    if dry_run:
        result = open_scan(quilt_path)
        chosen = named(quilt, result, work_args) if work_args else []
        gather = "gather" in steps and not work_args
        work_steps = tuple(s for s in WORK_STEPS if s in steps)
        scanned = scan_bibliography(quilt, write=False) if gather else None
        ws = [w for w in survey(result) if not chosen or w.citekey in set(chosen)]
        plan = planned(result, ws, steps=work_steps, redo=redo, candidates=not no_candidates, named=frozenset(chosen))
        plan_report(ws, plan, online=quilt.config.online or online, scan=scanned).emit(as_json)
        return
    with Progress("reading the quilt") as progress:

        def tell(stage: str, item: str, n: int, total: int) -> None:
            if n == 1:
                progress.next_stage(stage, total)
            progress.item(item)

        built = update(
            quilt,
            work_args,
            steps=steps,
            redo=redo,
            online=online,
            candidates=not no_candidates,
            compile=not no_compile,
            progress=tell,
        )
    built.report().emit(as_json)


#: The commands this module adds to `loom library`.
COMMANDS: list[click.Command] = [update_command]
