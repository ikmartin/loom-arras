"""One library update: gather, look up, fetch, extract and map, for every work or the ones named; what `loom library update` and a run started in the viewer both do."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loom.refs.build import STEPS, WORK_STEPS, BuildReport, OnProgress
from loom.scan.quilt import Quilt

if TYPE_CHECKING:
    from loom.scan.scan import ScanResult


def named(quilt: Quilt, result: ScanResult, needles: tuple[str, ...]) -> list[str]:
    """The citekeys the WORK arguments name, each through `_works.works`; one that names nothing is refused, and one gathering would add says so."""
    from loom.cli._common import NotFoundError
    from loom.cli.library._works import works as resolve_works

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


def update(
    quilt: Quilt,
    works: tuple[str, ...] = (),
    *,
    steps: tuple[str, ...] = STEPS,
    redo: bool = False,
    online: bool = False,
    candidates: bool = True,
    compile: bool = True,
    progress: OnProgress | None = None,
) -> BuildReport:
    """Make what a machine can about the cited works, and say what was made.

    Parameters
    ----------
    quilt : Quilt
        The quilt.
    works : tuple of str, default ()
        WORK arguments as `loom library update` takes them; () is every work, and only then is the bibliography gathered.
    steps : tuple of str, default STEPS
        The steps to take, in `STEPS`' order.
    redo : bool, default False
        Ask the lookups again, re-extract and re-map where done; verified results are kept.
    online : bool, default False
        This run may use the network though `[library] online` is off; written nowhere. The caller has already refused an agent this.
    candidates : bool, default True
        Fetch on a lookup's candidate, not only on an identifier the entry declares.
    compile : bool, default True
        Compile each paper to number its results; off, the numbering is emulated.
    progress : callable, optional
        Told `(stage, citekey, n, total)` as each work step moves, as `build_refs` tells it.

    Returns
    -------
    BuildReport
        What the run did, with its gathering and what is left for a person and an agent.

    Raises
    ------
    NotFoundError
        A WORK names nothing.
    """
    from loom.cli.library.state import left
    from loom.refs.build import build_refs, survey
    from loom.refs.scan import scan_bibliography
    from loom.scan.scan import scan

    result = scan(quilt) if works else None
    chosen = named(quilt, result, works) if result is not None else []
    gather = "gather" in steps and not works
    work_steps = tuple(s for s in WORK_STEPS if s in steps)
    scanned = scan_bibliography(quilt) if gather else None
    if result is None or (scanned is not None and scanned.added):
        result = scan(quilt)
    # this run's consent, written nowhere: the config is the standing answer (DR-193)
    result.quilt.config.online = quilt.config.online or online
    if work_steps:
        built = build_refs(
            result,
            only=tuple(chosen),
            refresh=redo,
            candidates=candidates,
            force=redo,
            compile=compile,
            steps=work_steps,
            progress=progress,
        )
    else:
        built = BuildReport(works=[w for w in survey(result) if not chosen or w.citekey in set(chosen)], steps=())
    built.scan = scanned
    built.left = left(result, built.works)
    return built
