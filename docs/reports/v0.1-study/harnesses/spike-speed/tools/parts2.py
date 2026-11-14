"""Serve-like steady state: one warm-up build, then N builds each after a one-word edit to a proof, in one process; wall time of each named step of the timed builds.

Usage: python parts2.py QUILT [--cache-git] [--n 2] [--no-tex]
"""

from __future__ import annotations

import collections
import functools
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import probe  # noqa: E402

TIMES: dict[str, list[float]] = collections.defaultdict(list)


def timed(mod, name, label=None):  # type: ignore[no-untyped-def]
    f = getattr(mod, name)
    label = label or f"{mod.__name__.split('.')[-1]}.{name}"

    @functools.wraps(f)
    def w(*a, **kw):  # type: ignore[no-untyped-def]
        t = time.perf_counter()
        try:
            return f(*a, **kw)
        finally:
            TIMES[label].append(time.perf_counter() - t)

    setattr(mod, name, w)


A, B = "has fibred products, for which", "has fibered products, for which"


def main() -> None:
    q = Path(sys.argv[1]).resolve()
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 2
    tex = "--no-tex" not in sys.argv
    probe.cache_git()
    import loom.adopt as AD
    import loom.records.store as RS
    import loom.render.build as Bu
    import loom.render.incoming as IN
    import loom.render.pending as PE
    import loom.render.review_compare as RC
    import loom.render.versions as VE
    import loom.render.fromhtml as FH
    import loom.render.fragments as FR
    import loom.review_queue as RQ
    import loom.scan.scan as SC
    import loom.section_drafts as SD
    import loom.render.publish as PU
    import loom.files as FI
    import loom.draft_lifecycle as DL
    from loom.scan.quilt import load_quilt

    for mod, name in [
        (Bu, "scan"), (Bu, "freeze_moved"), (Bu, "gone_annotations"), (Bu, "_marks_by_node"), (Bu, "load_history"), (Bu, "load_canon"),
        (Bu, "build_manifest"), (Bu, "attach_versions"), (Bu, "publish"), (Bu, "_write_source"), (Bu, "_write_transcripts"), (Bu, "_attach_spans"),
        (FH, "page_for"), (RS.Records, "apply"), (RS.Records, "resolved"), (RS.Records, "__init__"),
        (DL, "attach_closed"), (SD, "attach_context"), (RC, "attach_comparisons"), (IN, "attach_incoming"), (IN, "attach_adoptions"),
        (PE, "attach_pending"), (RQ, "rows_for"), (FI, "attach_files"), (FR.FragmentRenderer, "prepare"), (FR._Previews, "make"),
    ]:
        timed(mod, name)
    quilt = load_quilt(q)
    f = q / "drafting/draft5.tex"
    t = time.perf_counter()
    Bu.build(quilt, progress=probe.told, tex=tex)
    print(f"warm-up build {time.perf_counter() - t:.2f}s")
    for i in range(n):
        TIMES.clear()
        text = f.read_text()
        a, b = (A, B) if A in text else (B, A)
        f.write_text(text.replace(a, b, 1))
        p0 = len(probe.PROCS)
        t = time.perf_counter()
        r = Bu.build(load_quilt(q), progress=probe.told, tex=tex)
        total = time.perf_counter() - t
        import os

        print(f"build {i}: total {total:.2f}s rendered={len(r.rendered)} load={os.getloadavg()[0]:.2f}")
        for k, v in sorted(TIMES.items(), key=lambda kv: -sum(kv[1])):
            print(f"  {sum(v):7.2f}s  x{len(v):<4d} {k}")
        print("  subprocesses:", probe.proc_summary(probe.PROCS[p0:]))


if __name__ == "__main__":
    main()
