"""Time the look's parts on a quilt copy: scan, open_texts, take, look_texts, in_place, patch_of.

Usage: loom-venv-python profile_look.py QUILT WHO [EXTRA_REL ...]
EXTRA_REL: extra quilt-relative files to include in the open texts (to simulate a look that covers e.g. .loom/copies/).
"""
import sys
import time
from pathlib import Path

import loom.looks as looks
import loom.pending as pending
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

root = Path(sys.argv[1]).resolve()
who = sys.argv[2]
extra = sys.argv[3:]

_orig = looks.open_texts


def open_texts(quilt):
    out = _orig(quilt)
    for rel in extra:
        p = quilt.root / rel
        if p.is_file():
            out[rel] = p.read_text(encoding="utf-8")
    return out


looks.open_texts = open_texts


def t(label, f, n=3):
    best = None
    out = None
    for _ in range(n):
        a = time.perf_counter()
        out = f()
        d = time.perf_counter() - a
        best = d if best is None or d < best else best
    print(f"{label:32s} {best*1000:9.1f} ms")
    return out


quilt = load_quilt(root)
print("track_edits", quilt.config.track_edits, "extra", extra)
result = t("scan", lambda: scan(load_quilt(root)), n=2)
texts = t("open_texts", lambda: open_texts(result.quilt))
print("  files", len(texts), "bytes", sum(len(v.encode()) for v in texts.values()))
look = looks.read_look(root, who)
print("  look", look.when if look else None, len(look.files) if look else 0)


def lt():
    pending._TEXTS.clear()
    return pending._look_texts(result, who)


lt_out = t("look_texts (read look+diff set)", lt)
print("  changed files", len(lt_out[0]) if lt_out else None)


def ip():
    pending._TEXTS.clear()
    pending._INPLACE.clear()
    return pending.in_place(result, who)


chs = t("in_place (cut by words+blocks)", ip)
print("  changes", len(chs))
blocks = set()
for c in chs:
    blocks.update((c.path, b) for b in c.blocks)
print("  blocks touched", len(blocks))


def patches():
    return [pending.patch_of(result, c, who) for c in chs]


t("patch_of for every change", patches, n=1)
