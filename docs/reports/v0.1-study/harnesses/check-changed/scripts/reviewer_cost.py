"""Count and time the reviewer-name lookups in one `loom build --no-compile`, as the author runs it when no loom author name is configured (the git fallback).

Usage: XDG_CONFIG_HOME=<dir without loom/config.toml> loom-venv-python reviewer_cost.py QUILT
"""
import sys
import time

import loom.scan.quilt as Q

stats = {"git": [0, 0.0], "resolve": [0, 0.0]}
_git, _res = Q.git_user_name, Q.resolve_author


def git(*a, **k):
    t = time.perf_counter()
    try:
        return _git(*a, **k)
    finally:
        stats["git"][0] += 1
        stats["git"][1] += time.perf_counter() - t


def res(*a, **k):
    t = time.perf_counter()
    try:
        return _res(*a, **k)
    finally:
        stats["resolve"][0] += 1
        stats["resolve"][1] += time.perf_counter() - t


Q.git_user_name = git
Q.resolve_author = res
sys.argv = ["loom", "build", "--no-compile", "--json", "--quilt", sys.argv[1]]
from loom.cli import main  # noqa: E402

t0 = time.perf_counter()
try:
    main()
except SystemExit:
    pass
sys.stdout = sys.__stdout__
print(f"\nwall {time.perf_counter()-t0:.1f}s; git user.name calls {stats['git'][0]} taking {stats['git'][1]:.2f}s; resolve_author calls {stats['resolve'][0]} taking {stats['resolve'][1]:.2f}s")
