"""Discarding an agent's in-place edit in a CRLF file writes the old words back at offsets counted in another text.

usage: r_crlf_discard.py SYNTHETIC_SRC WORK
"""
import os, shutil, sys
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
from loom.config_edit import set_values
from loom.pending import pending
from loom.render.api import handle
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

src, work = Path(sys.argv[1]), Path(sys.argv[2])
q = work / "q"; shutil.rmtree(q, ignore_errors=True); shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
node = q / "drafting/sections/appendix.tex"
node.write_bytes(node.read_bytes().replace(b"\n", b"\r\n"))
set_values(load_quilt(q), {"review.track_edits": True})
handle(q, "change-keep", {"all": True})  # the person's look
original = node.read_bytes()
# an agent changes a few words near the end of the file, in place
text = original.decode()
at = text.rfind("the")
node.write_bytes((text[:at] + "AGENT-WORDS" + text[at + 3:]).encode())
ids = [c.id for c in pending(scan(load_quilt(q)), "Pat Tester") if c.kind == "edit" and c.path == "drafting/sections/appendix.tex"]
print(handle(q, "change-discard", {"changes": ids})["result"])
after = node.read_bytes()
print("restored exactly:", after == original, "| CRLF before/after:", original.count(b"\r\n"), after.count(b"\r\n"), "| AGENT-WORDS left:", b"AGENT-WORDS" in after)
if after != original:
    import difflib
    print("\n".join(list(difflib.unified_diff(original.decode().splitlines(), after.decode().splitlines(), lineterm="", n=0))[:12]))
