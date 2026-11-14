"""Wall time of each named step of one `build()`, unprofiled: python parts.py QUILT [--cache-git] [--reuse]."""

from __future__ import annotations

import collections
import functools
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import probe  # noqa: E402

TIMES: dict[str, list[float]] = collections.defaultdict(list)
DEPTH = threading.local()


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


def main() -> None:
    q = Path(sys.argv[1]).resolve()
    probe.cache_git()
    import loom.adopt as AD
    import loom.draft_lifecycle as DL
    import loom.files as FI
    import loom.records.store as RS
    import loom.render.build as B
    import loom.render.incoming as IN
    import loom.render.pending as PE
    import loom.render.review_compare as RC
    import loom.render.fromhtml as FH
    import loom.render.fragments as FR
    import loom.review_queue as RQ
    import loom.scan.owners as OW
    import loom.scan.scan as SC
    import loom.section_drafts as SD
    from loom.scan.quilt import load_quilt

    for mod, name in [
        (B, "scan"), (B, "freeze_moved"), (B, "gone_annotations"), (B, "_marks_by_node"), (B, "load_history"), (B, "load_canon"),
        (B, "build_manifest"), (B, "attach_versions"), (B, "publish"), (B, "_attach_spans"), (B, "_write_source"), (B, "_write_transcripts"),
        (SC, "landmark_documents"), (FH, "page_for"), (RS.Records, "apply"), (RS.Records, "resolved"),
        (DL, "attach_closed"), (SD, "attach_context"), (RC, "attach_comparisons"), (IN, "attach_incoming"), (IN, "attach_adoptions"),
        (PE, "attach_pending"), (RQ, "rows_for"), (FI, "attach_files"), (OW, "stamped"), (AD, "_flat_shape"),
        (FR.FragmentRenderer, "prepare"), (FR._Previews, "make"),
    ]:
        timed(mod, name)
    quilt = load_quilt(q)
    reuse = None
    if "--reuse" in sys.argv:
        reuse = SC.scan(quilt)
        TIMES.clear()
    t = time.perf_counter()
    r = B.build(quilt, reuse=reuse, progress=probe.told)
    total = time.perf_counter() - t
    print(f"total {total:.2f}s rendered={len(r.rendered)} skipped={len(r.skipped)}")
    for k, v in sorted(TIMES.items(), key=lambda kv: -sum(kv[1])):
        print(f"  {sum(v):7.2f}s  x{len(v):<4d} {k}")
    print("  subprocesses:", probe.proc_summary(probe.PROCS))


if __name__ == "__main__":
    main()
