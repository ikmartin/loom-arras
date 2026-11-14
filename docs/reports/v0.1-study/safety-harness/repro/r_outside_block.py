"""SAFE: a suggested edit placed after its block's `\\end{...}` (or before its `\\begin{...}`) lands outside the block, where the taken-test never looks: once its text stands and the edit is open, Keep writes it again.

usage: r_outside_block.py SYNTHETIC_SRC WORKDIR {typed|reopen|agent}
"""
import os, shutil, sys, json
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
from click.testing import CliRunner
from loom.cli import main
from loom.render.api import handle
from loom.records.edits import find, taken_how
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

src, work, how = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
q = work / "q"
shutil.rmtree(q, ignore_errors=True)
shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
node = q / "drafting/nodes/sy-000A.tex"
new = "A gadget with three points has one fixed point."
r = CliRunner().invoke(main, ["suggest", "sy-000A", "--quote", "\\end{remark}", "--with", new, "--after", "--as", "Agent Smith", "--json", "--quilt", str(q)], env={"AI_AGENT": "1"})
eid = json.loads(r.stdout)["edit"]
if how == "typed":  # the person (or the agent, in place) writes the suggested sentence in, then presses Keep
    t = node.read_text(); node.write_text(t.replace("\\end{remark}", "\\end{remark} " + new, 1))
else:  # keep, then the write API's undo of the keep, which reopens it
    print("keep 1:", handle(q, "change-keep", {"changes": [eid]})["result"])
    print("reopen:", handle(q, "change-discard", {"changes": [eid], "undo": True})["result"])
print("taken_how:", taken_how(scan(load_quilt(q)), find(q, eid)))
for n in ((2, 3) if how == "reopen" else (2,)):
    print(f"keep {n}:", handle(q, "change-keep", {"changes": [eid]}).get("result"))
    if how == "reopen":
        handle(q, "change-discard", {"changes": [eid], "undo": True})
print("copies in the file:", node.read_text().count(new))
