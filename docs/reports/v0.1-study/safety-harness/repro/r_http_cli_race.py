"""A Keep from the CLI while `loom serve` handles one, real processes, no injection: two suggested edits on one file, one kept over HTTP and one from the CLI at the same moment; then one edit placed after `\\end{remark}` kept from both.

usage: r_http_cli_race.py SYNTHETIC_SRC WORK PORT TRIALS
"""
import json, os, shutil, subprocess, sys, threading, time, urllib.request
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
BIN = Path("/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin")
src, work, port, trials = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
q = work / "q"; shutil.rmtree(q, ignore_errors=True); shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
NODE = q / "drafting/nodes/sy-000A.tex"
server = subprocess.Popen([str(BIN / "loom"), "serve", "--no-compile", "--port", str(port), "--quilt", str(q)], stdout=open(work / "serve.log", "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(600):
        try:
            token = json.loads((q / ".loom/serve.json").read_text())["token"]
            urllib.request.urlopen(f"http://127.0.0.1:{port}/_api", timeout=2).read(); break
        except Exception:
            time.sleep(0.2)
    while not (q / ".loom/build/manifest.json").is_file(): time.sleep(0.2)
    def http_keep(eid, out):
        req = urllib.request.Request(f"http://127.0.0.1:{port}/_api/change-keep", data=json.dumps({"changes": [eid]}).encode(), headers={"Content-Type": "application/json", "X-Loom-Token": token}, method="POST")
        try: out.append(json.loads(urllib.request.urlopen(req, timeout=120).read()).get("result"))
        except Exception as exc: out.append(repr(exc))
    def suggest(quote, new, where):
        r = subprocess.run([str(BIN / "loom"), "suggest", "sy-000A", "--quote", quote, "--with", new, where, "--as", "Agent Smith", "--json", "--quilt", str(q)], capture_output=True, text=True, env={**os.environ, "AI_AGENT": "1"})
        return json.loads(r.stdout)["edit"]
    def status(eid):
        st = None
        for line in (q / ".loom/edits/log.jsonl").read_text().splitlines():
            e = json.loads(line)
            if e["id"] == eid and e["event"] in ("kept", "discarded", "reopened"): st = e["event"]
        return st or "open"
    lost = dup = 0
    for t in range(trials):
        x_text, y_text = f"Xtrial{t} each swap fixes nothing.", f"Ytrial{t} by hand"
        X = suggest("with the swap.", x_text, "--after")
        Y = suggest("Gadgets exist:", y_text, "--before")
        out = []
        th = threading.Thread(target=http_keep, args=(X, out)); th.start()
        cli = subprocess.run([str(BIN / "loom"), "changes", "--keep", Y, "--quilt", str(q)], capture_output=True, text=True)
        th.join()
        text = NODE.read_text()
        res = (text.count(x_text), status(X), text.count(y_text), status(Y))
        if (res[1] == "kept" and res[0] == 0) or (res[3] == "kept" and res[2] == 0): lost += 1
        print("two edits:", res, out[0][:60] if out else None, "| cli:", (cli.stdout + cli.stderr).strip()[:80], flush=True)
    for t in range(trials):
        z_text = f"Ztrial{t}: a gadget with three points has one fixed point."
        Z = suggest("\\end{remark}", z_text, "--after")
        out = []
        th = threading.Thread(target=http_keep, args=(Z, out)); th.start()
        cli = subprocess.run([str(BIN / "loom"), "changes", "--keep", Z, "--quilt", str(q)], capture_output=True, text=True)
        th.join()
        n = NODE.read_text().count(z_text)
        dup += n > 1
        print("one edit after \\end:", n, "copies |", (out[0] or "")[:60], "| cli:", (cli.stdout + cli.stderr).strip()[:80], flush=True)
    print(f"lost a kept edit in {lost}/{trials}; wrote one edit twice in {dup}/{trials}")
finally:
    server.terminate(); server.wait(10)
