"""`history-restore` with a path writes wherever the path points when no file is there: `../x` lands outside the quilt.

usage: r_put_back_path.py SYNTHETIC_SRC WORK
"""
import os, shutil, sys
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
from loom.render.api import handle
src, work = Path(sys.argv[1]), Path(sys.argv[2])
q = work / "q"; shutil.rmtree(q, ignore_errors=True); shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
digest = "sha256:" + next((q / ".loom/history/texts").glob("*.md")).stem
out = work / "outside-the-quilt.txt"; out.unlink(missing_ok=True)
print(handle(q, "history-restore", {"path": "../outside-the-quilt.txt", "text": digest}))
print("written outside the quilt:", out.is_file())
