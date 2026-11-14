"""Run seeded sequences; record every failure, shrink the first of each signature.

usage: run_prop.py QUILT_SRC OUTDIR SEED0 COUNT LENGTH [inproc|http] [port] [variant] [track]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from safety_lib import draw_sequence, run_sequence, shrink  # noqa: E402

src, out = Path(sys.argv[1]), Path(sys.argv[2])
seed0, count, length = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
driver = sys.argv[6] if len(sys.argv) > 6 else "inproc"
port = int(sys.argv[7]) if len(sys.argv) > 7 else 0
variant = sys.argv[8] if len(sys.argv) > 8 and sys.argv[8] != "-" else ""
track = {"on": True, "off": False}.get(sys.argv[9]) if len(sys.argv) > 9 else None
do_shrink = "--no-shrink" not in sys.argv
out.mkdir(parents=True, exist_ok=True)
work = out / "work"
results = out / "results.jsonl"
shrunk: set[str] = {json.loads(x)["sig"] for x in (out / "shrunk.jsonl").read_text().splitlines()} if (out / "shrunk.jsonl").is_file() else set()
kw = {"driver": driver, "port": port, "variant": variant, "track_edits": track}
for seed in range(seed0, seed0 + count):
    acts = draw_sequence(seed, length)
    t = time.time()
    kw["port"] = port + (seed % 10) if port else 0
    fails, trace = run_sequence(src, work, acts, stop_at_first=False, **kw)
    sigs = sorted({f.sig() for f in fails})
    rec = {"seed": seed, "src": src.name, "driver": driver, "variant": variant, "secs": round(time.time() - t, 1), "acts": len(trace), "sigs": sigs,
           "first": [{"check": f.check, "i": f.act_index, "op": f.act.get("op"), "detail": f.detail[:400]} for f in fails[:40]]}
    with results.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(seed, rec["secs"], sigs, flush=True)
    for f in fails:
        if f.sig() in shrunk or not do_shrink or f.check == "harness-or-loom-crash":
            continue
        shrunk.add(f.sig())
        cut = acts[: f.act_index + 1]
        small = shrink(src, work, cut, f.sig(), **kw)
        fs, tr = run_sequence(src, work, small, **kw)
        with (out / "shrunk.jsonl").open("a") as fh:
            fh.write(json.dumps({"sig": f.sig(), "seed": seed, "acts": small, "trace": tr, "failures": [vars(x) for x in fs]}, default=str) + "\n")
        print("  shrunk", f.sig(), len(small), flush=True)
