"""For each run, which published files changed from one step's settled build to the next; then what base and spike disagree on."""
import json, sys
from pathlib import Path
runs = {n: json.loads(Path(p).read_text()) for n, p in (a.split("=") for a in sys.argv[1:])}
names = list(runs)
steps = [s for s in runs[names[0]]["steps"] if all(s in r["steps"] for r in runs.values())]
for i in range(1, len(steps)):
    a, b = steps[i - 1], steps[i]
    ch = {}
    for n, r in runs.items():
        fa, fb = r["steps"][a]["second"]["files"], r["steps"][b]["second"]["files"]
        ch[n] = sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))
    print(f"{a} -> {b}: " + "; ".join(f"{n} {len(v)} changed" for n, v in ch.items()))
    base = set(ch[names[0]])
    for n in names[1:]:
        only_base, only_n = sorted(base - set(ch[n])), sorted(set(ch[n]) - base)
        print(f"   changed in {names[0]} only: {only_base[:8]}{' …' if len(only_base) > 8 else ''}")
        print(f"   changed in {n} only: {only_n[:8]}{' …' if len(only_n) > 8 else ''}")
