"""Cost of a look that also covers the agent copies: take it, set the copy's text to an older snapshot, time in_place.

Usage: loom-venv-python copy_look_cost.py QUILT SNAPSHOT [SNAPSHOT ...]
Writes a look for a throwaway reviewer, times look_texts and in_place for each snapshot as the look's copy text, deletes the look.
"""
import sys
import time
from pathlib import Path

import loom.looks as looks
import loom.pending as pending
from loom.records.snapshots import write_raw
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

root = Path(sys.argv[1]).resolve()
snaps = sys.argv[2:]
WHO = "Study Copy Reviewer"
COPY = ".loom/copies/examples-shared.tex"
_orig = looks.open_texts


def open_texts(quilt):
    out = _orig(quilt)
    out[COPY] = (quilt.root / COPY).read_text(encoding="utf-8")
    return out


looks.open_texts = open_texts
quilt = load_quilt(root)
t = time.perf_counter()
look = looks.take(quilt, WHO)
print(f"take (open files + copy): {1000*(time.perf_counter()-t):.0f} ms, files {len(look.files)}")
result = scan(load_quilt(root))
try:
    for snap in snaps:
        old = Path(snap).read_text(encoding="utf-8")
        look.files[COPY] = write_raw(root, old, quilt.history_dir)
        looks._write(root, look)
        pending._TEXTS.clear()
        pending._INPLACE.clear()
        t = time.perf_counter()
        ch = pending.in_place(result, WHO)
        d = time.perf_counter() - t
        blocks = {b for c in ch for b in c.blocks}
        print(f"{Path(snap).name}: in_place {d:.1f} s, {len(ch)} changes, {len(blocks)} blocks touched")
finally:
    looks.look_path(root, WHO).unlink(missing_ok=True)
