"""Adopt the synthetic quilt's agent copy through the CLI: preview, incorporate, incorporate again with the same token, then restore the version kept before adopting; check the person's files at each step.

usage: r_adopt.py SYNTHETIC_SRC WORK
"""
import json, os, shutil, subprocess, sys
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
BIN = Path("/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin")
src, work = Path(sys.argv[1]), Path(sys.argv[2])
q = work / "q"; shutil.rmtree(q, ignore_errors=True); shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
def files():
    return {p.relative_to(q).as_posix(): p.read_bytes() for p in q.rglob("*") if p.is_file() and ".loom" not in p.relative_to(q).parts}
def loom(*a):
    r = subprocess.run([str(BIN / "loom"), *a, "--quilt", str(q)], capture_output=True, text=True)
    return r
def agent(*a):
    return subprocess.run([str(BIN / "loom"), *a, "--quilt", str(q)], capture_output=True, text=True, env={**os.environ, "AI_AGENT": "1"})
print("draft:", agent("draft", sys.argv[3] if len(sys.argv) > 3 else "drafting/talk.tex", "--ai", "smith", "--as", "Agent Smith").stdout[:120])
copy = q / ".loom/copies/smith.tex"
t = copy.read_text()
i = t.find("\\begin{proof}")
j = t.find("\n", i)
copy.write_text(t[:j + 1] + "AGENT-PROOF-LINE: the agent's added sentence.\n" + t[j + 1:])
before = files()
pv = loom("adopt", ".loom/copies/smith.tex", "--json")
data = json.loads(pv.stdout) if pv.stdout.strip().startswith("{") else {}
token = (data.get("data") or data).get("token") or next((w for w in pv.stdout.split() if len(w) > 20), None)
print("preview:", pv.returncode, (pv.stdout + pv.stderr)[:200].replace("\n", " "))
print("token:", token)
r1 = loom("adopt", ".loom/copies/smith.tex", "--incorporate", token)
mid = files()
changed = sorted(k for k in set(before) | set(mid) if before.get(k) != mid.get(k))
print("incorporate:", r1.returncode, (r1.stdout + r1.stderr)[:200].replace("\n", " "), "| changed:", changed)
r2 = loom("adopt", ".loom/copies/smith.tex", "--incorporate", token)
print("same token again:", r2.returncode, (r2.stdout + r2.stderr)[:160].replace("\n", " "), "| files changed again:", files() != mid)
# every file it wrote: was its text before kept?
import hashlib
texts = q / ".loom/history/texts"
for k in changed:
    b = before.get(k)
    if b is None: continue
    ok = (texts / f"{hashlib.sha256(b).hexdigest()}.md").is_file()
    print("  before-text of", k, "kept in history texts:", ok)
