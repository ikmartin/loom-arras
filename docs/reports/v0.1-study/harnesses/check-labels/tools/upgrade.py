"""Records filed by today's code, read by the prototype after an upgrade: the quilt as filed, then with co-author edits. Usage: upgrade.py BASE_RUN_DIR PAPER OUT"""

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import harness as H  # noqa: E402
from loom.scan.quilt import load_quilt  # noqa: E402
from loom.scan.scan import scan  # noqa: E402

base_run, paper, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
data = json.loads((base_run / f"{paper}.json").read_text())
targets = []
for d in data["targets"]:
    d = dict(d)
    d.pop("file_hits", None)
    targets.append(H.Target(**d))
recs = data["records"]
filed = base_run / paper / "filed"
cfg_main = load_quilt(filed).config.main
result = scan(load_quilt(filed))
H.SCENARIOS["as-filed"] = []
for name in ("as-filed", "light-edit", "insert-above", "insert-above+light-edit", "rename-label", "delete-statement"):
    work = out / paper / name
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(filed, work)
    ws = H.apply_scenario(work, name, targets, result, cfg_main)
    rows = H.classify(work, targets, recs, ws)
    c = Counter(r["outcome"] for r in rows)
    print(f"{paper:9s} {name:26s} " + " ".join(f"{k}={c[k]}" for k in ("right", "wrong", "detached", "lost") if c[k]))
