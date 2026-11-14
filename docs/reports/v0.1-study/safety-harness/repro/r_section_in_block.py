"""A suggested edit whose new text opens a section inside a statement is never read as taken: typed in by hand (or reopened after a Keep), Keep writes it a second time."""
import os, shutil, sys, json
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
from click.testing import CliRunner
from loom.cli import main
from loom.render.api import handle
from loom.records.edits import find, taken_how
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

src, work = Path(sys.argv[1]), Path(sys.argv[2])
how = sys.argv[3] if len(sys.argv) > 3 else "typed"
q = work / "q"
shutil.rmtree(q, ignore_errors=True)
shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
node = q / "drafting/nodes/sy-000A.tex"
new = "\\section*{Part X}\nA paragraph of the agent's own that runs to well over twenty words so that it is long enough to count as a paragraph of the person's text.\n\\begin{proof}\nThe answer, in a few words.\n\\end{proof}"
r = CliRunner().invoke(main, ["suggest", "sy-000A", "--quote", "with the swap.", "--with", new, "--after", "--as", "Agent Smith", "--json", "--quilt", str(q)], env={"AI_AGENT": "1"})
eid = json.loads(r.stdout)["edit"]
if how == "typed":
    t = node.read_text(); node.write_text(t.replace("with the swap.", "with the swap. " + new, 1))
else:  # keep, then the API's undo of the keep (reopen)
    print("keep 1:", handle(q, "change-keep", {"changes": [eid]})["result"])
    print("reopen:", handle(q, "change-discard", {"changes": [eid], "undo": True})["result"])
print("taken_how:", taken_how(scan(load_quilt(q)), find(q, eid)))
print("keep 2:", handle(q, "change-keep", {"changes": [eid]})["result"])
print("copies of the new paragraph in the file:", node.read_text().count("A paragraph of the agent's own"))
