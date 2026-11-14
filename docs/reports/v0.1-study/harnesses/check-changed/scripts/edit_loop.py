"""Time loom serve's edit loop: write a one-word edit to a file and wait for the published manifest to change.

Usage: python3 edit_loop.py QUILT PORT REL N
Starts `loom serve --no-compile` on PORT, waits for the first build, then N times: edits REL (adds then removes a word), and times the manifest rewrite. Stops the server.
"""
import os
import signal
import subprocess
import sys
import time
import urllib.request

quilt, port, rel, n = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
LOOM = "/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin/loom"
man = os.path.join(quilt, ".loom/build/manifest.json")
start_m = os.stat(man).st_mtime_ns if os.path.exists(man) else 0
proc = subprocess.Popen([LOOM, "serve", "--no-compile", "--port", str(port)], cwd=quilt, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
try:
    t0 = time.time()
    while True:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/build/manifest.json", timeout=2).read()
            break
        except Exception:
            time.sleep(0.5)
        if time.time() - t0 > 300:
            raise SystemExit("server did not come up")
    while (os.stat(man).st_mtime_ns if os.path.exists(man) else 0) == start_m:
        time.sleep(0.2)
        if time.time() - t0 > 300:
            raise SystemExit("first build never published")
    print(f"first build published after {time.time()-t0:.1f}s")
    time.sleep(10)
    path = os.path.join(quilt, rel)
    orig = open(path, encoding="utf-8").read()
    marker = "\\begin{proof}"
    i = orig.find(marker)
    times = []
    for k in range(n):
        before = os.stat(man).st_mtime_ns
        text = orig[: i + len(marker)] + f" Study{k}" + orig[i + len(marker) :] if k % 2 == 0 else orig
        a = time.time()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        while os.stat(man).st_mtime_ns == before:
            time.sleep(0.05)
            if time.time() - a > 120:
                break
        times.append(time.time() - a)
        time.sleep(12)
    with open(path, "w", encoding="utf-8") as f:
        f.write(orig)
    print("edit-to-manifest seconds:", " ".join(f"{x:.2f}" for x in times))
finally:
    os.killpg(proc.pid, signal.SIGTERM)
    proc.wait(timeout=30)
