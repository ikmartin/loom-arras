"""Instrumentation for timing loom: subprocess log, per-thread cProfile, stage stamps.

Usage: python probe.py build QUILT [--force] [--no-tex] [--profile OUT]
       python probe.py scan QUILT
"""

from __future__ import annotations

import cProfile
import json
import os
import pstats
import subprocess
import sys
import threading
import time
from pathlib import Path

T0 = time.perf_counter()
PROCS: list[dict] = []
_LOCK = threading.Lock()
_orig_init = subprocess.Popen.__init__
_orig_handle = subprocess.Popen._handle_exitstatus


def _init(self, args, *a, **kw):  # type: ignore[no-untyped-def]
    self._probe_start = time.perf_counter()
    argv = args if isinstance(args, (list, tuple)) else [str(args)]
    self._probe_argv = [str(x) for x in argv]
    _orig_init(self, args, *a, **kw)


def _handle(self, *a, **kw):  # type: ignore[no-untyped-def]
    r = _orig_handle(self, *a, **kw)
    if not getattr(self, "_probe_done", False):
        self._probe_done = True
        end = time.perf_counter()
        argv = getattr(self, "_probe_argv", ["?"])
        with _LOCK:
            PROCS.append(
                {
                    "exe": os.path.basename(argv[0]),
                    "argv": " ".join(argv[:6])[:200],
                    "start": self._probe_start - T0,
                    "end": end - T0,
                    "thread": threading.current_thread().name,
                }
            )
    return r


subprocess.Popen.__init__ = _init  # type: ignore[method-assign]
subprocess.Popen._handle_exitstatus = _handle  # type: ignore[attr-defined]

PROFILES: list[cProfile.Profile] = []
_orig_run = threading.Thread.run
PROFILE_THREADS = False


def _run(self):  # type: ignore[no-untyped-def]
    if not PROFILE_THREADS:
        return _orig_run(self)
    p = cProfile.Profile()
    with _LOCK:
        PROFILES.append(p)
    p.enable()
    try:
        return _orig_run(self)
    finally:
        p.disable()


threading.Thread.run = _run  # type: ignore[method-assign]

STAGES: list[tuple[float, str, str, int, int | None]] = []


def told(stage: str, item: str = "", n: int = 0, total: int | None = None) -> None:
    STAGES.append((time.perf_counter() - T0, stage, item, n, total))


def union(intervals: list[tuple[float, float]]) -> float:
    total, cur_s, cur_e = 0.0, None, None
    for s, e in sorted(intervals):
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s
    return total


def proc_summary(procs: list[dict], since: float = 0.0, until: float = 1e18) -> dict:
    by: dict[str, list[dict]] = {}
    for p in procs:
        if p["start"] >= since and p["start"] < until:
            by.setdefault(p["exe"], []).append(p)
    out = {}
    for exe, ps in sorted(by.items(), key=lambda kv: -sum(p["end"] - p["start"] for p in kv[1])):
        out[exe] = {
            "n": len(ps),
            "sum_s": round(sum(p["end"] - p["start"] for p in ps), 2),
            "wall_s": round(union([(p["start"], p["end"]) for p in ps]), 2),
            "max_s": round(max(p["end"] - p["start"] for p in ps), 2),
        }
    allp = [p for p in procs if p["start"] >= since and p["start"] < until]
    out["ALL"] = {"n": len(allp), "wall_s": round(union([(p["start"], p["end"]) for p in allp]), 2)}
    return out


def stage_summary() -> list[tuple[str, float, float]]:
    """(stage, start, duration) collapsing repeated stage ticks."""
    out = []
    last = None
    for at, stage, _item, _n, _t in STAGES:
        if last is None or last[0] != stage:
            if last is not None:
                out.append((last[0], last[1], at - last[1]))
            last = (stage, at)
    return out, last


PIN_CODE = "7bb8d97985fec8c8"
PIN_SNIP = "0f39562ac7a34c268c68745d15eed12c7353021d3978939a20c90fc10a053429"


def pin_code() -> None:
    """Spike harness: hold the rendering-code fingerprints at the unmodified code's values, so a code change does not re-render every cached fragment, snippet and preview (measures steady state, not the one-off invalidation)."""
    if os.environ.get("NO_PIN"):
        return
    import loom.render.build as B
    import loom.render.keys as K
    import loom.render.snippets as SN

    f = lambda: PIN_CODE  # noqa: E731
    K.code_hash = f
    B.code_hash = f
    SN._CODE[:] = [PIN_SNIP]


def cache_git() -> None:
    """With --cache-git: one `git config user.name` per process, as if the loom author name were configured."""
    pin_code()
    if "--cache-git" not in sys.argv:
        return
    import functools

    import loom.scan.quilt as Q

    Q.git_user_name = functools.lru_cache(maxsize=None)(Q.git_user_name)


def main() -> None:
    global PROFILE_THREADS
    mode, qpath = sys.argv[1], Path(sys.argv[2]).resolve()
    force = "--force" in sys.argv
    tex = "--no-tex" not in sys.argv
    prof_out = None
    if "--profile" in sys.argv:
        prof_out = sys.argv[sys.argv.index("--profile") + 1]
        # Python 3.13: one cProfile (sys.monitoring) already sees every thread
    from loom.scan.quilt import load_quilt

    cache_git()
    t_import = time.perf_counter() - T0
    main_prof = cProfile.Profile() if prof_out else None
    quilt = load_quilt(qpath)
    if main_prof:
        main_prof.enable()
    started = time.perf_counter()
    if mode == "build":
        from loom.render.build import build

        report = build(quilt, force=force, progress=told, tex=tex)
        info = {"rendered": len(report.rendered), "skipped": len(report.skipped)}
    elif mode == "scan":
        from loom.scan.scan import scan

        told("scanning")
        scan(quilt)
        info = {}
    else:
        raise SystemExit(mode)
    total = time.perf_counter() - started
    if main_prof:
        main_prof.disable()
    stages, last = stage_summary()
    end_at = time.perf_counter() - T0
    if last:
        stages.append((last[0], last[1], end_at - last[1]))
    print(json.dumps({"mode": mode, "quilt": str(qpath), "import_s": round(t_import, 2), "total_s": round(total, 2), **info}))
    for name, at, dur in stages:
        print(f"  stage {name:12s} at {at:7.2f}  took {dur:7.2f}")
    renders = [s for s in STAGES if s[1] == "rendering"]
    if renders:
        print(f"  rendering ticks: {len(renders)}, total {renders[-1][4]}")
    # TeX per stage
    bounds = [(name, at, at + dur) for name, at, dur in stages]
    for name, a, b in bounds:
        ps = proc_summary(PROCS, a, b)
        if ps["ALL"]["n"]:
            print(f"  subprocesses during {name}: {json.dumps(ps)}")
    print(f"  subprocesses all: {json.dumps(proc_summary(PROCS))}")
    if prof_out:
        st = pstats.Stats(main_prof)
        for p in PROFILES:
            try:
                st.add(p)
            except TypeError:
                pass
        st.dump_stats(prof_out)
        Path(prof_out + ".procs.json").write_text(json.dumps(PROCS))


if __name__ == "__main__":
    main()
