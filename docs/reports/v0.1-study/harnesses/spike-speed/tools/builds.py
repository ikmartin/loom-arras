"""The build a save triggers in `loom serve`, timed in process: one warm-up build, then N edits of a never-seen word to a proof, each followed by the build the watcher would run.

Usage: python builds.py QUILT LABEL [--cache-git] [--n 3] [--tex 0|1] [--previews-tex 0|1]
Prints one JSON line per timed build: seconds, blocks rendered, make4ht runs, git forks, load.
"""

from __future__ import annotations

import inspect
import json
import os
import random
import string
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import probe  # noqa: E402

PHRASE = "has fibered products, for which"


def main() -> None:
    q = Path(sys.argv[1]).resolve()
    label = sys.argv[2]
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 3
    tex = sys.argv[sys.argv.index("--tex") + 1] != "0" if "--tex" in sys.argv else True
    ptex = sys.argv[sys.argv.index("--previews-tex") + 1] != "0" if "--previews-tex" in sys.argv else True
    probe.cache_git()
    import loom.render.build as B
    from loom.scan.quilt import load_quilt

    kw = {"tex": tex}
    if "previews_tex" in inspect.signature(B.build).parameters:
        kw["previews_tex"] = ptex
    f = q / "drafting/draft5.tex"
    t = time.perf_counter()
    B.build(load_quilt(q))
    warm = time.perf_counter() - t
    print(json.dumps({"label": label, "warmup_s": round(warm, 2), "flags": kw}), flush=True)
    cur = PHRASE
    try:
        for i in range(n):
            w = "".join(random.choice(string.ascii_lowercase) for _ in range(7))
            new = PHRASE.replace("fibered", w)
            text = f.read_text(encoding="utf-8")
            assert cur in text
            f.write_text(text.replace(cur, new, 1), encoding="utf-8")
            cur = new
            p0 = len(probe.PROCS)
            load = os.getloadavg()[0]
            t = time.perf_counter()
            r = B.build(load_quilt(q), **kw)
            s = time.perf_counter() - t
            procs = probe.PROCS[p0:]
            print(json.dumps({"label": label, "i": i, "s": round(s, 2), "rendered": len(r.rendered), "make4ht": sum(1 for p in procs if p["exe"] == "make4ht"), "git": sum(1 for p in procs if p["exe"] == "git"), "load": round(load, 2), "deferred": getattr(r, "deferred", None)}), flush=True)
    finally:
        text = f.read_text(encoding="utf-8")
        f.write_text(text.replace(cur, PHRASE, 1), encoding="utf-8")


if __name__ == "__main__":
    main()
