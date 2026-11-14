"""Keep rewrites the whole file from the scan's text: a CRLF file comes back LF throughout, a Latin-1 file comes back as UTF-8 of a Mac Roman reading (every accented letter changed), and a symlinked file is replaced by a copy.

usage: r_encoding.py SYNTHETIC_SRC WORK {crlf|latin1|symlink}
"""
import json, os, shutil, sys
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
from click.testing import CliRunner
from loom.cli import main
from loom.render.api import handle

src, work, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
q = work / mode; shutil.rmtree(q, ignore_errors=True); shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
node = q / "drafting/nodes/sy-000A.tex"
if mode == "crlf":
    node.write_bytes(node.read_bytes().replace(b"\n", b"\r\n"))
elif mode == "latin1":
    node.write_bytes(node.read_bytes().replace(b"Gadgets exist:", "Gadgets exist (Schröder, Gödel):".encode("latin-1")))
elif mode == "symlink":
    real = q / "shared-remark.tex"; real.write_bytes(node.read_bytes()); node.unlink(); node.symlink_to(Path("../../shared-remark.tex"))
before = node.read_bytes()
r = CliRunner().invoke(main, ["suggest", "sy-000A", "--quote", "with the swap.", "--with", "Each swap fixes nothing.", "--after", "--as", "Agent Smith", "--json", "--quilt", str(q)], env={"AI_AGENT": "1"})
print(r.output[-400:]) if r.exit_code else None; eid = json.loads(r.stdout)["edit"]
print(handle(q, "change-keep", {"changes": [eid]})["result"])
after = node.read_bytes()
print("before:", before[:140])
print("after: ", after[:170])
if mode == "symlink": print("still a symlink:", node.is_symlink(), "| shared file changed:", (q / "shared-remark.tex").read_bytes() != before)
