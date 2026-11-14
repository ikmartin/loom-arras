"""A suggested edit on a key named by place (FILE#proof:3) goes into another block once a block is put in before it and the edit's own block cannot be told apart by its text (here: three empty Answer proofs, as a homework file has before it is solved).

usage: r_wrong_block.py QUANT_COPY WORK
"""
import json, os, re, shutil, sys
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
from click.testing import CliRunner
from loom.cli import main
from loom.render.api import handle

src, work = Path(sys.argv[1]), Path(sys.argv[2])
q = work / "q"; shutil.rmtree(q, ignore_errors=True); shutil.copytree(src, q, ignore=shutil.ignore_patterns("build", "digests"))
F = "course/solutions/hwk2.tex"
from loom.records.edits import replay
old = [e.id for e in replay(q)[0] if e.status == "open"]
if old: handle(q, "change-discard", {"changes": old, "why": "clearing the copy"})
def suggest(key, new, *more):
    r = CliRunner().invoke(main, ["suggest", key, "--with", new, *more, "--as", "Agent Smith", "--json", "--quilt", str(q)], env={"AI_AGENT": "1"})
    return json.loads(r.stdout)["edit"]
answer3 = "Bayes' rule gives 0.008 / (0.008 + 0.0495), about 0.139. ANSWER-TO-PROBLEM-3"
a = suggest(F + "#proof:3", answer3)                       # the answer to Problem 3, in its empty proof
b = suggest(F, "\\section*{Problem 0: A warm-up}\nA fair coin is tossed twice. What is the chance of two heads?\n\\begin{proof}[Answer]\n\\end{proof}", "--quote", "\\maketitle", "--after")
print(handle(q, "change-keep", {"changes": [b]}))   # a problem put in before the others
print(handle(q, "change-keep", {"changes": [a]})["result"])
text = (q / F).read_text()
for m in re.finditer(r"\\section\*\{(Problem \d)", text):
    nxt = text.find("\\section*", m.end()); body = text[m.start(): nxt if nxt > 0 else len(text)]
    print(m.group(1), "holds the answer to Problem 3" if "ANSWER-TO-PROBLEM-3" in body else "")
