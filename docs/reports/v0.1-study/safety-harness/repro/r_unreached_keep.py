"""Keep into a file no document reads (a scratch .tex of the person's) writes it and keeps no version first.

usage: r_unreached_keep.py SYNTHETIC_SRC WORK
"""
import hashlib, json, os, shutil, sys
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
from click.testing import CliRunner
from loom.cli import main
from loom.render.api import handle
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
src, work = Path(sys.argv[1]), Path(sys.argv[2])
q = work / "q"; shutil.rmtree(q, ignore_errors=True); shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
f = q / "drafting/scratch.tex"
f.write_text("\\begin{lemma}\\label{sy-7777}\nEvery widget of odd order has a fixed point, MY-OWN-WORDS.\n\\end{lemma}\n")
before = f.read_bytes()
r = CliRunner().invoke(main, ["suggest", "sy-7777", "--quote", "MY-OWN-WORDS", "--with", "as the count shows", "--as", "Agent Smith", "--json", "--quilt", str(q)], env={"AI_AGENT": "1"})
print(r.output.strip()[:200])
eid = json.loads(r.stdout)["edit"]
print(handle(q, "change-keep", {"changes": [eid]}))
print("file changed:", f.read_bytes() != before, "| its text before kept anywhere in .loom/history:", any(b"MY-OWN-WORDS" in p.read_bytes() for p in (q / ".loom/history").rglob("*") if p.is_file()))
whole = (q / ".loom/history/texts" / f"{hashlib.sha256(before).hexdigest()}.md").is_file()
print("the whole file before the write kept (byte-exact):", whole)
print("where the words are kept:", [str(p.relative_to(q)) for p in (q / ".loom/history").rglob("*") if p.is_file() and b"MY-OWN-WORDS" in p.read_bytes()])
