import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from safety_lib import draw_sequence, run_sequence
from loom.records.edits import find, taken_how, home, replay
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
src, seed, n, eid = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
work = Path("runs/debug")
fs, tr = run_sequence(src, work, draw_sequence(seed, 40)[:n], stop_at_first=False, track_edits=True)
q = work / "q"
e = [x for x in replay(q)[0] if eid in x.with_text][0]
r = scan(load_quilt(q))
print(e.target_key, e.placement, repr(e.selector.exact if e.selector else None), e.status)
print("with:", repr(e.with_text[:200]))
node = home(r, e)
print("home:", node.key if node else None, node.file if node else None, node.start if node else None, node.end if node else None)
print("taken_how:", taken_how(r, e))
print("file:\n", (q / node.file).read_text()[max(0,node.start-200):node.end+600] if node else "")
