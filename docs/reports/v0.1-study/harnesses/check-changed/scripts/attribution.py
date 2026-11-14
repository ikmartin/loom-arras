"""Which source of attribution classifies which changes, on the replayed history.

Usage: loom-venv-python attribution.py QUILT_DIR NAME STATES.pickle
Population: every (transition, unit) change event in the open files (and, separately, the copies). Sources, in order:
 S1 loom's own records of a write (adopt, keep of a suggested edit, tick, `loom write`, import);
 S4 the agent app's report of a file tool write (Edit/Write/MultiEdit; what a PostToolUse hook sees);
 S2 the deny list: a change in a denied file is the person's;
 S3 coincidence with loom-side agent activity (session messages, annotations, edits, ledger acts) within W minutes.
"""
import bisect
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.argv = sys.argv  # noqa
root = Path(sys.argv[1]).resolve()
name = sys.argv[2]
# reuse simulate's event building without its variants
src = open(Path(__file__).parent / "simulate.py").read()
cut_at = src.index("# ---- step 2: look moments")
g = {"__name__": "attr", "__file__": str(Path(__file__).parent / "simulate.py")}
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3], "/dev/null"]
exec(compile(src[:cut_at], "simulate_head", "exec"), g)
events, TRUTH, denied, loom_agent_times = g["events"], g["TRUTH"], g["denied"], g["loom_agent_times"]

S1 = {"loom-adopt", "loom-keep", "person-tick", "agent-via-loom", "loom-import", "loom-housekeeping", "person-settings"}
S4 = {"agent", "agent-sub"}


def near(t, w):
    dt = datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ")
    a = (dt - timedelta(minutes=w)).strftime("%Y-%m-%dT%H:%M:%SZ")
    b = (dt + timedelta(minutes=w)).strftime("%Y-%m-%dT%H:%M:%SZ")
    i = bisect.bisect_left(loom_agent_times, a)
    return i < len(loom_agent_times) and loom_agent_times[i] <= b


for scope in ("open files", "copies"):
    pop = [e for e in events if (e[1].startswith(".loom/copies/")) == (scope == "copies") and e[2] in ("block", "md", "prose", "other", "newfile", "gonefile", "removed")]
    if not pop:
        continue
    print(f"== {name} {scope}: {len(pop)} change events (unit x transition)")
    truth = Counter(TRUTH.get(a, "unknown") for _, _, _, _, a in pop)
    print("   truth:", dict(truth))
    for W in (10, 30):
        res = Counter()
        for t, p, u, k, a in pop:
            tr = TRUTH.get(a, "unknown")
            if a in S1:
                res[("S1 loom record", "right")] += 1
            elif a in S4:
                res[("S4 agent app tool report", "right")] += 1
            elif denied(p):
                res[("S2 deny list", "right" if tr in ("person", "loom-on-person") else "WRONG")] += 1
            elif near(t, W):
                res[(f"S3 session within {W} min", "right" if tr == "agent" else "WRONG")] += 1
            else:
                res[("none", tr)] += 1
        n = len(pop)
        print(f"   W={W}:", ", ".join(f"{k[0]} {k[1]} {v} ({100*v/n:.0f}%)" for k, v in sorted(res.items())))
    # without the agent app (loom alone): S1, S2, S3
    for W in (10, 30):
        res = Counter()
        for t, p, u, k, a in pop:
            tr = TRUTH.get(a, "unknown")
            if a in S1:
                res["S1"] += 1
            elif denied(p):
                res["S2"] += 1
            elif near(t, W):
                res["S3"] += 1
            else:
                res["unattributed"] += 1
        n = len(pop)
        print(f"   loom alone W={W}:", {k: f"{v} ({100*v/n:.0f}%)" for k, v in res.items()})

# the person's own saves: does loom-side agent activity coincide with them?
print("== person saves (file mtimes of the person's last edit) vs loom-side agent activity")
for p in sorted(g["states"]):
    if not denied(p):
        continue
    fp = root / p
    if fp.is_file():
        t = datetime.utcfromtimestamp(fp.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%SZ")
        print("  ", p, t, "agent within 10 min:", near(t, 10), "within 30 min:", near(t, 30))
