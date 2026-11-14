import sys
from collections import Counter
from pathlib import Path
src = open(Path(__file__).parent / "simulate.py").read()
cut_at = src.index("# ---- step 2: look moments")
g = {"__name__": "x", "__file__": str(Path(__file__).parent / "simulate.py")}
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3], "/dev/null"]
exec(compile(src[:cut_at], "head", "exec"), g)
for scope in ("open", "copies"):
    pop = [e for e in g["events"] if e[1].startswith(".loom/copies/") == (scope == "copies")]
    c = Counter(e[4] for e in pop)
    n = len(pop)
    print(g["name"], scope, n, {k: f"{v} ({100*v/n:.0f}%)" for k, v in c.most_common()})
    files = Counter((e[1], e[4]) for e in pop)
    if scope == "open":
        for (p, a), v in sorted(files.items()):
            print("    ", p, a, v)
