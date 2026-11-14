"""Restoring a version writes every file the version holds, but keeps first only the files the document reaches now: a file taken out of the document since (an \\input commented out) is overwritten, and the person's text in it is kept nowhere.

usage: r_restore_unreached.py SYNTHETIC_SRC WORK
"""
import os, shutil, sys
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
from loom.render.api import handle

src, work = Path(sys.argv[1]), Path(sys.argv[2])
q = work / "q"; shutil.rmtree(q, ignore_errors=True); shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
results, node = q / "drafting/sections/results.tex", q / "drafting/nodes/sy-0006.tex"
results.write_text(results.read_text().replace("\\input{nodes/sy-0006}", "% \\input{nodes/sy-0006}  % working on it apart"))
node.write_text(node.read_text() + "\n% MY-NEW-PARAGRAPH: a week of work on this proof.\n")
print(handle(q, "history-restore", {"document": "drafting/main.tex", "version": "widgets-v1"})["result"])
print("my paragraph in the file:", "MY-NEW-PARAGRAPH" in node.read_text())
print("my paragraph kept anywhere in .loom/history:", any(b"MY-NEW-PARAGRAPH" in p.read_bytes() for p in (q / ".loom/history").rglob("*") if p.is_file()))
