"""Replay one seed of the seeded test outside pytest, printing every act. usage: trace.py SEED WORK"""
import shutil, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import test_write_safety as t
seed, work = int(sys.argv[1]), Path(sys.argv[2])
shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
mp = pytest.MonkeyPatch()
q = t.q._fixture_function(work, mp)
run = t.Run(q, seed)
for i in range(16):
    t.step(run)
    print(i, run.trail[-1][:300])
    if run.problems:
        print("PROBLEMS", run.problems); break
