"""Run `loom build --no-compile` in-process with timers on the look's functions; print totals.

Usage: loom-venv-python time_build.py QUILT
"""
import functools
import sys
import time

import loom.pending as P
import loom.render.pending as RP

acc: dict[str, list[float]] = {}
depth = {"n": 0}


def wrap(mod, name, label):
    f = getattr(mod, name)

    @functools.wraps(f)
    def g(*a, **k):
        outer = depth["n"] == 0
        depth["n"] += 1
        t = time.perf_counter()
        try:
            return f(*a, **k)
        finally:
            depth["n"] -= 1
            d = time.perf_counter() - t
            e = acc.setdefault(label, [0.0, 0, 0.0])
            e[1] += 1
            if outer:
                e[0] += d  # outermost only, so nested calls are not counted twice
            e[2] += d

    setattr(mod, name, g)


for name in ("in_place", "kept_own", "look_texts", "suggested"):
    wrap(P, name, "pending." + name)
wrap(RP, "attach_pending", "render.pending.attach_pending")

sys.argv = ["loom", "build", "--no-compile", "--json", "--quilt", sys.argv[1]]
from loom.cli import main  # noqa: E402

t0 = time.perf_counter()
try:
    main()
except SystemExit:
    pass
wall = time.perf_counter() - t0
sys.stdout = sys.__stdout__
print(f"\nwall {wall:.2f}s")
for k, (outer, n, total) in sorted(acc.items()):
    print(f"{k:34s} calls {n:5d}  outermost {outer*1000:8.1f} ms")
