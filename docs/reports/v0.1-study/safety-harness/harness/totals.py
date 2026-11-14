"""Totals across run directories: sequences, acts, failing, damage, and each finding's share of failing sequences and of SAFE-1 by class."""
import collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from analyze import finding
DAMAGE = ("SAFE-1 ", "SAFE-2 ", "SAFE-5 ", "SAFE-6 ", "SAFE-7 ")
EXCLUDE = {("A-showcase", 3077)}  # the harness typed one suggestion in twice itself (person's duplicate)
seqs = acts = failing = damage = organic = 0
by = collections.Counter(); safe1 = collections.Counter()
for d in sys.argv[1:]:
    for l in open(Path(d) / "results.jsonl"):
        r = json.loads(l)
        seqs += 1; acts += r["acts"]
        ks = {finding(f["check"], f["op"], f["detail"]) for f in r["first"]}
        for sig in r["sigs"]:
            k = finding(*sig.split("@"), "")
            if not any(x.split(" [")[0] == k.split(" [")[0] for x in ks): ks.add(k)
        if (Path(d).name, r["seed"]) == ("H-synthetic", 2037):  # traced in process: a reopened kept edit
            ks = {k.replace("[?]", "[reopened-after-keep]") for k in ks}
        if (Path(d).name, r["seed"]) in EXCLUDE:
            ks = {k for k in ks if not k.startswith("SAFE-1 ")}
        failing += bool(ks)
        damage += any(k.startswith(DAMAGE) for k in ks)
        organic += any(k.startswith(DAMAGE) and not k.startswith("SAFE-2 save lost") for k in ks)
        for k in ks:
            by[k.split(" [")[0] if k.startswith("SAFE-1 ") else k] += 1
            if k.startswith("SAFE-1 "): safe1[k] += 1
print(f"{seqs} sequences, {acts} acts; {failing} failing; {damage} with damage to text; {organic} with damage other than the injected save")
for k, n in by.most_common(): print(f"  {n:4d} ({100*n/max(failing,1):4.1f}% of failing)  {k}")
print("SAFE-1 by class:")
for k, n in safe1.most_common(): print(f"  {n:4d}  {k}")
