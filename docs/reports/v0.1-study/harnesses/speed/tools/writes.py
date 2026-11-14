"""Time an annotation written through the HTTP write API and through the CLI, until the served manifest carries it.

Usage: python writes.py QUILT PORT KEY LOOM_EXE
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request


def manifest_has(base: str, text: str) -> bool:
    with urllib.request.urlopen(base + "/build/manifest.json", timeout=60) as r:
        return text.encode() in r.read()


def main() -> None:
    q, port, key, loom = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    base = f"http://127.0.0.1:{port}"
    with urllib.request.urlopen(base + "/_api") as r:
        token = json.loads(r.read())["token"]
    for n in range(3):
        msg = f"Study API note {time.time():.0f}-{n}."
        req = urllib.request.Request(
            f"{base}/_api/annotate",
            data=json.dumps({"target": key, "message": msg, "author": "Study Bench"}).encode(),
            headers={"Content-Type": "application/json", "X-Loom-Token": token},
            method="POST",
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=600) as r:
            r.read()
        answered = time.time() - t0
        while not manifest_has(base, msg):
            time.sleep(0.1)
        print(json.dumps({"via": "http", "answered_s": round(answered, 2), "in_manifest_s": round(time.time() - t0, 2), "load": os.getloadavg()[0]}))
        time.sleep(8)
    env = dict(os.environ, AI_AGENT="1")
    for n in range(3):
        msg = f"Study CLI note {time.time():.0f}-{n}."
        t0 = time.time()
        subprocess.run([loom, "annotate", key, msg, "--as", "Study Agent"], cwd=q, env=env, capture_output=True, check=True)
        cli = time.time() - t0
        while not manifest_has(base, msg):
            time.sleep(0.1)
        print(json.dumps({"via": "cli", "command_s": round(cli, 2), "in_manifest_s": round(time.time() - t0, 2), "load": os.getloadavg()[0]}))
        time.sleep(8)


if __name__ == "__main__":
    main()
