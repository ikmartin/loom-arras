"""Two Keeps at once with no lock between them (the CLI beside `loom serve`; in-process here, two threads, the first slowed between its write and its record).

usage: r_race.py SYNTHETIC_SRC WORK {same|two}
same: both keep one edit placed after `\\end{remark}` -> written twice.
two:  one keeps edit X, the other edit Y, both in one file -> the second write is made from a scan taken before the first, and X is lost while recorded kept.
"""
import json, os, shutil, sys, threading, time
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
from click.testing import CliRunner
from loom.cli import main
from loom.render.api import handle
import loom.pending as pending
from loom.records.edits import find

src, work, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
q = work / "q"; shutil.rmtree(q, ignore_errors=True); shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
NODE = q / "drafting/nodes/sy-000A.tex"
def suggest(quote, new):
    r = CliRunner().invoke(main, ["suggest", "sy-000A", "--quote", quote, "--with", new, "--after", "--as", "Agent Smith", "--json", "--quilt", str(q)], env={"AI_AGENT": "1"})
    return json.loads(r.stdout)["edit"]
X = suggest("\\end{remark}", "A gadget with three points has one fixed point.")
Y = suggest("with the swap.", "Each swap fixes nothing.") if mode == "two" else X
orig = pending._rescan
first = threading.Event()
def slow(result):
    if threading.current_thread().name == "A" and not first.is_set():
        first.set(); time.sleep(1.0)   # A has written its file and not yet recorded the edit kept
    return orig(result)
pending._rescan = slow
out = {}
def go(name, eid):
    try: out[name] = handle(q, "change-keep", {"changes": [eid]}).get("result")
    except Exception as exc: out[name] = repr(exc)
if mode == "same":
    a = threading.Thread(target=go, args=("A", X), name="A"); a.start()
    first.wait(5); b = threading.Thread(target=go, args=("B", Y), name="B"); b.start()
else:  # B scans first and is slow to write (keeping its version); A keeps X meanwhile; B then writes from its old scan
    pending._rescan = orig
    import loom.history.acts as acts
    kv = acts.keep_versions
    def slow_kv(*args, **kw):
        res = kv(*args, **kw)
        if threading.current_thread().name == "B" and args[2] == acts.APPLY:
            first.set(); time.sleep(1.5)
        return res
    acts.keep_versions = slow_kv
    b = threading.Thread(target=go, args=("B", Y), name="B"); b.start()
    first.wait(10); a = threading.Thread(target=go, args=("A", X), name="A"); a.start()
a.join(); b.join()
text = NODE.read_text()
print(out)
print("X stands", text.count("A gadget with three points"), "time(s); recorded", find(q, X).status)
if mode == "two": print("Y stands", text.count("Each swap fixes nothing."), "time(s); recorded", find(q, Y).status)
