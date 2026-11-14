import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from safety_lib import draw_sequence, run_sequence
src, seed, n = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
driver = sys.argv[4] if len(sys.argv) > 4 else "inproc"
port = int(sys.argv[5]) if len(sys.argv) > 5 else 0
fs, tr = run_sequence(src, Path(sys.argv[6] if len(sys.argv) > 6 else "runs/show"), draw_sequence(seed, n), driver=driver, port=port, stop_at_first=False, track_edits=(None if "quant" in str(src) else True))
for t in tr:
    print(json.dumps({k: v for k, v in t.items() if k not in ("r","block")})[:260])
for f in fs:
    print("FAIL", f.check, f.act_index, f.detail[:300])
