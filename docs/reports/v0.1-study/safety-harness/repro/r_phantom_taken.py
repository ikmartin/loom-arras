"""An insertion whose words already stand anywhere in its block reads as taken before anyone writes it: Keep records it kept and writes nothing.

usage: r_phantom_taken.py SYNTHETIC_SRC WORK
"""
import json, os, shutil, sys
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
from click.testing import CliRunner
from loom.cli import main
from loom.render.api import handle
from loom.records.edits import find

src, work = Path(sys.argv[1]), Path(sys.argv[2])
q = work / "q"; shutil.rmtree(q, ignore_errors=True); shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
node = q / "drafting/nodes/sy-000A.tex"
before = node.read_bytes()
# the agent proposes citing Kre99 at the claim too; the block already cites it further on
r = CliRunner().invoke(main, ["suggest", "sy-000A", "--quote", "Gadgets exist:", "--with", "\\cite[Theorem 2.1]{Kre99}", "--after", "--as", "Agent Smith", "--json", "--quilt", str(q)], env={"AI_AGENT": "1"})
eid = json.loads(r.stdout)["edit"]
ch = CliRunner().invoke(main, ["changes", "--json", "--quilt", str(q)])
print("listed as:", [c["state"] for c in json.loads(ch.stdout)["changes"] if c["id"] == eid])
print(handle(q, "change-keep", {"changes": [eid]})["result"])
print("recorded:", find(q, eid).status, "| file changed:", node.read_bytes() != before)
