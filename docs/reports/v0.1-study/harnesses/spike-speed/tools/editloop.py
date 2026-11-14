"""Drive edits against a running serveprobe and time save -> seen.

Usage: python editloop.py QUILT PORT LOG FILE OLD NEW FRAGMENT [--trials N] [--settle S]
Each trial replaces OLD by NEW (then back), polls FRAGMENT over HTTP until NEW's presence flips, then waits for the server to go quiet.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path


def events(log: Path, since: float) -> list[dict]:
    out = []
    for line in log.read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r["t"] >= since:
            out.append(r)
    return out


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def quiet(log: Path, since: float, settle: float, limit: float) -> None:
    """Wait until no event for `settle` seconds after `since` and no compile running."""
    end = time.time() + limit
    while time.time() < end:
        evs = events(log, since)
        last = max((e["t"] for e in evs), default=since)
        running = sum(1 for e in evs if e["ev"] in ("compile-begin", "html-begin")) - sum(
            1 for e in evs if e["ev"] in ("compile-end", "html-end")
        )
        if running <= 0 and time.time() - last > settle:
            return
        time.sleep(0.25)


def main() -> None:
    q, port, log, rel, old, new, frag = sys.argv[1:8]
    trials = int(sys.argv[sys.argv.index("--trials") + 1]) if "--trials" in sys.argv else 3
    settle = float(sys.argv[sys.argv.index("--settle") + 1]) if "--settle" in sys.argv else 6.0
    logp = Path(log)
    path = Path(q) / rel
    url = f"http://127.0.0.1:{port}/build/{frag}"
    results = []
    for n in range(trials):
        a, b = (old, new) if n % 2 == 0 else (new, old)
        text = path.read_text(encoding="utf-8")
        assert a in text, f"{a!r} not in {rel}"
        before = fetch(url) if frag != "-" else ""
        t0 = time.time()
        path.write_text(text.replace(a, b, 1), encoding="utf-8")
        seen = None
        if frag != "-":
            while time.time() - t0 < 600:
                try:
                    body = fetch(url)
                except Exception:  # noqa: BLE001
                    body = before
                if body != before:
                    seen = time.time() - t0
                    break
                time.sleep(0.1)
        quiet(logp, t0, settle, 900)
        evs = events(logp, t0)
        rel_evs = [(round(e["t"] - t0, 2), e["thread"], e["ev"], {k: v for k, v in e.items() if k not in ("t", "thread", "ev")}) for e in evs]
        results.append({"trial": n, "edit": f"{a!r}->{b!r}", "fragment_changed_s": round(seen, 2) if seen else None, "events": rel_evs})
        print(json.dumps(results[-1]))
        sys.stdout.flush()
        time.sleep(1)


if __name__ == "__main__":
    main()
