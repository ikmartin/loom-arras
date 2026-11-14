"""Run `loom changes --keep ID` and kill the process (os._exit) at one point of the keep. usage: crash_child.py POINT QUILT ID"""
import os, sys
from pathlib import Path
point, quilt, eid = sys.argv[1], Path(sys.argv[2]).resolve(), sys.argv[3]
import loom.history.acts as acts
import loom.records.edits as edits

def person(p) -> bool:
    p = Path(p).resolve()
    return p.is_relative_to(quilt) and ".loom" not in p.relative_to(quilt).parts

if point == "after-write":
    orig = acts.write_file
    def wf(path, text):
        orig(path, text)
        if person(path): os._exit(9)
    acts.write_file = wf
elif point == "before-write":
    orig_kv = acts.keep_versions
    def kv(*a, **k):
        out = orig_kv(*a, **k)
        if a[2] == acts.APPLY: os._exit(9)
        return out
    acts.keep_versions = kv
elif point == "mid-write":
    real = os.replace
    def rp(src, dst, *a, **k):
        if str(src).endswith(".loom-tmp") and person(dst): os._exit(9)
        return real(src, dst, *a, **k)
    os.replace = rp
elif point == "after-record":
    orig_keep = edits.keep
    def kp(*a, **k):
        out = orig_keep(*a, **k)
        os._exit(9)
    edits.keep = kp
from loom.cli import main
main(["changes", "--keep", eid, "--quilt", str(quilt)])
