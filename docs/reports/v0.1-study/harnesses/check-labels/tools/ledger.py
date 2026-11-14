"""What the acceptance ledger says after co-author edits: accept some statements on a copy, apply a scenario, and read each block's state. Usage: ledger.py LOOM_BIN PAPER OUT"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harness as H  # noqa: E402
from loom.records.store import Records  # noqa: E402
from loom.scan.quilt import load_quilt  # noqa: E402
from loom.scan.scan import scan  # noqa: E402

loom, paper, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
base = out / "filed"
if out.exists():
    shutil.rmtree(out)
shutil.copytree(paper, base)
result = scan(load_quilt(base))
targets = [t for t in H.pick_targets(result) if t.kind in ("stmt-label", "stmt-none")]
keys = [t.key for t in targets]
# the writer `loom accept` and the unit tests share, called on this scratch copy as the tests do (the CLI refuses an agent's shell)
from loom.cli.review import write_acceptance  # noqa: E402

rows, _, _ = write_acceptance(result, keys, "Tester")
print("accepted rows:", [r.key for r in rows])
cfg_main = load_quilt(base).config.main
for name in ("insert-above", "insert-above+light-edit", "rename-label", "delete-statement", "label-reused", "duplicate-label", "rename-file"):
    work = out / name
    shutil.copytree(base, work)
    ws = H.apply_scenario(work, name, targets, result, cfg_main)
    res = scan(load_quilt(work))
    R = Records(work, reviewer="Tester")
    states = R.key_states(res, observe=False)
    accepted = {k for k, s in states.items() if s.row is not None}
    truths = {}
    for t in targets:
        blk = ws.anchors.get(f"blk:{t.tid}")
        n = H.node_at(res, blk[0], blk[1], "") if blk else None
        truths[t.tid] = n.key if n else None
    right = sum(1 for t in targets if truths[t.tid] in accepted)
    lost = sum(1 for t in targets if truths[t.tid] is not None and truths[t.tid] not in accepted)
    gone = sum(1 for t in targets if truths[t.tid] is None)
    wrong = sorted(k for k in accepted if k not in set(truths.values()))
    fresh = sum(1 for t in targets if truths[t.tid] in accepted and states[truths[t.tid]].fresh)
    diags = [d.code for d in R.diagnostics(res, states) if d.code in ("loom:retired-ledger-key", "loom:previous-key-match")]
    print(f"{paper.name:8s} {name:26s} rows on the right block={right} (fresh {fresh}), on no block though it stands={lost}, block deleted={gone}, rows on another block={len(wrong)} {[(k, 'stale' if not states[k].fresh else 'FRESH') for k in wrong]} diags={len(diags)}")
