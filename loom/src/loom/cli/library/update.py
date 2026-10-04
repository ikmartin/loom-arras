"""`loom library update`: everything a machine can make about the works a quilt cites, every step or one (book 8.9; plan 0.18.5)."""

from __future__ import annotations

import click

from loom.cli._common import EnvError, NotFoundError, agent_marker
from loom.cli._quilt import open_quilt, open_scan, quilt_option
from loom.cli.library._works import works as resolve_works
from loom.cli.report import Progress
from loom.refs.build import STEPS, WORK_STEPS
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult


def _named(quilt: Quilt, result: ScanResult, needles: tuple[str, ...]) -> list[str]:
    """The citekeys the WORK arguments name, each through `_works.works`; one that names nothing is refused, and one gathering would add says so."""
    out: set[str] = set()
    for needle in needles:
        try:
            out |= resolve_works(result, (needle,))
        except NotFoundError:
            from loom.refs.scan import scan_bibliography

            if needle in {c.key for c in scan_bibliography(quilt, write=False).added}:
                raise NotFoundError(
                    "work",
                    f"{needle} is in a landmark's bibliography and not gathered yet: loom library update --only gather",
                ) from None
            raise
    return sorted(out, key=str.lower)


@click.command(name="update")
@click.argument("work_args", nargs=-1, metavar="[WORK]...")
@click.option(
    "--only",
    type=click.Choice(STEPS),
    default=None,
    help="Run one step: gather (the bibliography, from the landmarks and refs/), resolve, fetch, extract or map.",
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
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
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

    Each step is a no-op where its work is done, so a second run does only what is new. WORK narrows every step to the works it names (a citekey, a fragment of one or of an author or title, or a result id); naming works leaves gathering out, since it reads the whole bibliography. Looking up and fetching use the network only under `[library] online = true` or `--online`, and an agent only under the config's: it may not grant itself the network. Offline, every local step still runs. Progress shows on stderr.
    """
    from loom.refs.build import BuildReport, build_refs, plan_report, planned, survey
    from loom.refs.scan import scan_bibliography

    quilt = open_quilt(quilt_path)
    marker = agent_marker()
    if online and marker and not quilt.config.online:
        raise EnvError(
            f"--online is the author's to give, and an agent is running this shell ({marker} is set): "
            "the author sets online = true under [library] in config.toml, or runs this in a terminal of their own"
        )
    steps = (only,) if only else STEPS
    result = open_scan(quilt_path) if work_args else None
    named = _named(quilt, result, work_args) if result is not None else []
    gather = "gather" in steps and not work_args
    work_steps = tuple(s for s in WORK_STEPS if s in steps)
    allowed = quilt.config.online or online
    if dry_run:
        scanned = scan_bibliography(quilt, write=False) if gather else None
        result = result or open_scan(quilt_path)
        ws = [w for w in survey(result) if not named or w.citekey in set(named)]
        plan = planned(result, ws, steps=work_steps, redo=redo, candidates=not no_candidates, named=frozenset(named))
        plan_report(ws, plan, online=allowed, scan=scanned).emit(as_json)
        return
    scanned = scan_bibliography(quilt) if gather else None
    if result is None or (scanned is not None and (scanned.added or scanned.copied)):
        result = open_scan(quilt_path)
    # this run's consent, written nowhere: the config is the standing answer (DR-193)
    result.quilt.config.online = allowed
    if work_steps:
        with Progress(work_steps[0]) as progress:

            def tell(stage: str, item: str, n: int, total: int) -> None:
                if n == 1:
                    progress.next_stage(stage, total)
                progress.item(item)

            built = build_refs(
                result,
                only=tuple(named),
                refresh=redo,
                candidates=not no_candidates,
                force=redo,
                compile=not no_compile,
                steps=work_steps,
                progress=tell,
            )
    else:
        built = BuildReport(works=[w for w in survey(result) if not named or w.citekey in set(named)], steps=())
    built.scan = scanned
    built.report().emit(as_json)


#: The commands this module adds to `loom library`.
COMMANDS: list[click.Command] = [update_command]
