"""Sum harness outcomes over papers: per scenario, per target kind, and per record type. Usage: aggregate.py RUN_DIR [RUN_DIR2] (two dirs print side by side)."""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAPERS = ["man12", "acgs", "kpsv", "quant", "showcase", "mzk", "relloc"]
OUT = ("right", "wrong", "detached", "lost")


def load(d: Path):
    per_sc = defaultdict(Counter)
    per_kind = defaultdict(Counter)
    detail = defaultdict(Counter)
    per_type = defaultdict(Counter)
    wrong_rows = []
    for p in PAPERS:
        f = d / f"{p}.json"
        if not f.exists():
            continue
        data = json.loads(f.read_text())
        for sc, rows in data["rows"].items():
            for r in rows:
                o = r.get("outcome", "error")
                per_sc[sc][o] += 1
                per_kind[r.get("kind", "?")][o] += 1
                per_type[(r.get("type"), r.get("quoted"))][o] += 1
                per_sc["ALL"][o] += 1
                if r.get("detail"):
                    detail[o + ":" + r["detail"]][sc] += 1
                    detail[o + ":" + r["detail"]]["ALL"] += 1
                if o == "wrong":
                    wrong_rows.append((p, sc, r["tid"], r["type"], r["quoted"], r.get("detail"), r.get("now"), r.get("truth")))
    return per_sc, per_kind, detail, per_type, wrong_rows


def fmt(c: Counter) -> str:
    return " ".join(f"{c[k]:4d}" for k in OUT)


if __name__ == "__main__":
    dirs = [Path(a) for a in sys.argv[1:] if not a.startswith("-")]
    loaded = [load(d) for d in dirs]
    print(f"{'scenario':30s} " + "  |  ".join(" ".join(f"{k[:4]:>4s}" for k in OUT) for _ in dirs))
    for sc in loaded[0][0]:
        print(f"{sc:30s} " + "  |  ".join(fmt(x[0][sc]) for x in loaded))
    print()
    for kind in sorted(loaded[0][1]):
        print(f"{kind:30s} " + "  |  ".join(fmt(x[1][kind]) for x in loaded))
    print()
    for t in sorted(loaded[0][3], key=str):
        print(f"{str(t):30s} " + "  |  ".join(fmt(x[3][t]) for x in loaded))
    print()
    for k in sorted(set().union(*[x[2] for x in loaded])):
        print(f"{k:30s} " + "  |  ".join(f"{x[2][k]['ALL']:4d}" for x in loaded))
    if "-w" in sys.argv:
        for i, x in enumerate(loaded):
            print(f"-- wrong rows in {dirs[i]}")
            for row in x[4]:
                print("  ", row)
