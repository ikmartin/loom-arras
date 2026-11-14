"""How often a loom-side agent record falls within W minutes of the person's own exactly-timed acts (the false-positive rate of attributing by coincidence)."""
import sys
from pathlib import Path
src = open(Path(__file__).parent / "simulate.py").read()
cut_at = src.index("# ---- step 3: rows")
g = {"__name__": "x", "__file__": str(Path(__file__).parent / "simulate.py")}
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3], "/dev/null"]
exec(compile(src[:cut_at], "head", "exec"), g)
import bisect
from datetime import datetime, timedelta
L = g["loom_agent_times"]; A = g["agent_times"]
def near(xs, t, w):
    dt = datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ")
    a = (dt - timedelta(minutes=w)).strftime("%Y-%m-%dT%H:%M:%SZ"); b = (dt + timedelta(minutes=w)).strftime("%Y-%m-%dT%H:%M:%SZ")
    i = bisect.bisect_left(xs, a)
    return i < len(xs) and xs[i] <= b
acts = sorted(set(g["acts"]))
for w in (10, 30):
    print(g["name"], "person acts", len(acts), f"W={w}", "loom-side agent record near:", sum(near(L, t, w) for t in acts), "agent-app tool call near:", sum(near(A, t, w) for t in acts))
