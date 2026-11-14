"""Run loom serve in-process with timestamps on every stage; events go to a JSONL log.

Usage: python serveprobe.py QUILT PORT LOG [--no-compile] [--profile OUT]
Stop with SIGTERM.
"""

from __future__ import annotations

import json
import signal
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import probe  # noqa: E402  (patches subprocess for timing)

LOG = None
T0 = time.time()


def ev(kind: str, **kw) -> None:  # type: ignore[no-untyped-def]
    rec = {"t": round(time.time(), 4), "thread": threading.current_thread().name, "ev": kind, **kw}
    with probe._LOCK:
        LOG.write(json.dumps(rec) + "\n")
        LOG.flush()


def main() -> None:
    global LOG
    qpath, port, logp = Path(sys.argv[1]).resolve(), int(sys.argv[2]), sys.argv[3]
    no_compile = "--no-compile" in sys.argv
    LOG = open(logp, "a")
    ev("start")
    import cProfile

    prof = None
    if "--profile" in sys.argv:
        prof = cProfile.Profile()
        prof.enable()
    import loom.render.build as B
    import loom.render.serve as S
    import loom.tex.runner as R
    import loom.tex.tex4ht as T
    from loom.scan.quilt import load_quilt

    probe.cache_git()
    ev("imported")
    # stages of every build
    orig_build = S.build

    def build(*a, **kw):  # type: ignore[no-untyped-def]
        inner = kw.get("progress")
        last = {"stage": None}

        def told(stage, item="", n=0, total=None):  # type: ignore[no-untyped-def]
            if stage != last["stage"]:
                ev("stage", stage=stage, total=total)
                last["stage"] = stage
            if inner:
                inner(stage, item, n, total)

        kw["progress"] = told
        ev("build-begin", reuse=kw.get("reuse") is not None)
        r = orig_build(*a, **kw)
        ev("build-end", rendered=len(r.rendered), skipped=len(r.skipped))
        return r

    S.build = build
    orig_rebuild = S.ServeSession.rebuild

    def rebuild(self, changed=None, records=False, progress=None):  # type: ignore[no-untyped-def]
        ev("rebuild-call", changed=[str(p) for p in (changed or [])][:5], records=records)
        r = orig_rebuild(self, changed, records, progress)
        ev("rebuild-return")
        return r

    S.ServeSession.rebuild = rebuild
    orig_pub = S.Publications.published

    def published(self):  # type: ignore[no-untyped-def]
        ev("published", count=self.count + 1)
        return orig_pub(self)

    S.Publications.published = published
    orig_cd = S.compile_document

    def compile_document(*a, **kw):  # type: ignore[no-untyped-def]
        ev("compile-begin", doc=str(a[2]))
        r = orig_cd(*a, **kw)
        ev("compile-end", doc=str(a[2]), pdf=r.pdf is not None)
        return r

    S.compile_document = compile_document
    orig_ch = T.compile_html

    def compile_html(*a, **kw):  # type: ignore[no-untyped-def]
        ev("html-begin", doc=str(a[2]))
        r = orig_ch(*a, **kw)
        ev("html-end", doc=str(a[2]), html=r.html is not None)
        return r

    T.compile_html = compile_html
    import loom.render.watch as W

    orig_snap = W.snapshot

    def snapshot(root, shown=None):  # type: ignore[no-untyped-def]
        t = time.perf_counter()
        r = orig_snap(root, shown)
        d = time.perf_counter() - t
        if d > 0.05:
            ev("slow-snapshot", s=round(d, 3), n=len(r))
        return r

    W.snapshot = snapshot
    S.snapshot = snapshot

    quilt = load_quilt(qpath)
    bundle = S.locate_bundle()
    session = S.ServeSession(quilt, bundle, port, compile_masters=not no_compile)
    session.listen()
    ev("listening", url=session.url)

    def _term(*_):  # type: ignore[no-untyped-def]
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _term)
    try:
        session.start()
        ev("first-build-done")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ev("stopping")
    finally:
        session.stop()
        if prof:
            prof.disable()
            prof.dump_stats(sys.argv[sys.argv.index("--profile") + 1])
        Path(logp + ".procs.json").write_text(json.dumps([{**p, "start_abs": p["start"] + probe.T0} for p in probe.PROCS]))
        ev("stopped")


if __name__ == "__main__":
    main()
