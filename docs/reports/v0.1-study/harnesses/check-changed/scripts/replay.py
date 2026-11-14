"""Replay a quilt's history: per open file, the sequence of states and who made each change.

Usage: loom-venv-python replay.py QUILT_DIR NAME OUT.pickle
NAME is relloc or quant (selects the agent transcript extract data/agent-NAME.jsonl).

Sources: loom's history texts (steps, page-writes, looks, tick `from`), the agent app's Edit/MultiEdit/Write calls (exact), hand-made snapshots of the copy (relloc), and the files as they are now. Between two exact states, the agent's ops are replayed; what they do not explain is a residual, classified by the loom acts and agent shell commands in that interval.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import pickle
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1]).resolve()
name = sys.argv[2]
out = sys.argv[3]
DATA = Path(__file__).resolve().parent.parent / "data"
hist = root / ".loom" / "history"
texts = hist / "texts"
PERSON = {"ikmartin", "The synthetic quilt"}
GENERATED = {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}
COPY_MOVE = ("drafting-ai/examples-shared.tex", ".loom/copies/examples-shared.tex", "2026-11-03T16:47:55Z")


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm(ts: str) -> str:
    return ts[:19] + "Z"


def text_of(h: str | None) -> str | None:
    if not h:
        return None
    h = h.split(":")[-1]
    for p in glob.glob(str(texts / (h + "*"))):
        return open(p, encoding="utf-8").read()
    return None


def sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


cfg = (root / "config.toml").read_text()
deny = re.findall(r'deny\s*=\s*\[([^\]]*)\]', cfg)
DENY = [d.strip().strip('"') for d in deny[0].split(",") if d.strip()] if deny else []


def denied(path: str) -> bool:
    return any(path.startswith(d) for d in DENY)


# ---- domain: open files now, plus every path that appears in looks, plus the copies (a variant)
import loom.looks as looks  # noqa: E402
from loom.scan.quilt import load_quilt  # noqa: E402

quilt = load_quilt(root)
now_texts = looks.open_texts(quilt)
domain = set(now_texts)
for f in glob.glob(str(root / ".loom/looked/*.json")):
    domain |= set(json.load(open(f))["files"])
COPIES = sorted(str(Path(p).relative_to(root)) for p in glob.glob(str(root / ".loom/copies/*.tex")))
domain |= set(COPIES)
from loom.files import is_latex_aux  # noqa: E402

domain = {p for p in domain if not is_latex_aux(p)}

anchors: dict[str, list[tuple[str, str | None, str]]] = {p: [] for p in domain}  # (time, text or None=absent, source)
ops: dict[str, list[tuple[str, str, dict]]] = {p: [] for p in domain}
acts: dict[str, list[tuple[str, str, str]]] = {p: [] for p in domain}  # (time, act, actor)


def anchor(path, t, text, src):
    if path in anchors:
        anchors[path].append((norm(t), text, src))


# ledger
for line in open(hist / "ledger.jsonl"):
    e = json.loads(line)
    t, a, who = e["when"], e["action"], e["actor"]
    if a == "page-write":
        p = e["path"]
        if p in anchors:
            if e.get("from"):
                anchor(p, t, text_of(e["from"]), "page-write-from")
            ops[p].append((norm(t), "loom-write", {"to": text_of(e["to"]), "actor": who}))
    elif a == "stamp":
        for p, h in (e.get("files") or {}).items():
            anchor(p, t, text_of(h), f"stamp:{e.get('message','')[:30]}")
    elif a == "tick":
        p = e["path"]
        if p in anchors:
            anchor(p, t, text_of(e["from"]), "tick-from")
            acts[p].append((norm(t), "tick", who))
    elif a in ("apply", "adopt", "keep", "move", "import"):
        ps = [e.get("path")] if e.get("path") else []
        if a == "adopt":
            ps = ["drafting/examples.tex"]
        if a == "keep" and e.get("paths"):
            ps = []  # a keep of a look moves no file
        if a == "keep" and e.get("path"):
            ps = []  # a keep of an in-place change moves the look, not the file
        for p in ps:
            if p in acts:
                acts[p].append((norm(t), a, who))
    if a == "import" and e.get("drafted"):
        pass

# step directories: the before-adopt and import texts
imp = hist / "0001-draft5" / "draft5.tex"
# looks: each file's text at take time (files later moved by a keep are left out)
moved_later = {}
for line in open(hist / "ledger.jsonl"):
    e = json.loads(line)
    if e["action"] == "keep" and e.get("path"):
        moved_later.setdefault(e["path"], []).append(norm(e["when"]))
for f in glob.glob(str(root / ".loom/looked/*.json")):
    d = json.load(open(f))
    for p, h in d["files"].items():
        if p in anchors and not any(t > norm(d["when"]) for t in moved_later.get(p, [])):
            # a look that predates a later `keep` of this file's in-place change is not the file's state
            if p == "drafting/examples.tex" and "synthetic" in d["who"]:
                continue
            anchor(p, d["when"], text_of(h), "look:" + d["who"])
    for p in anchors:
        # a look covers every open file: a path missing from it did not exist then (copies are never in a look)
        if p not in d["files"] and not p.startswith(".loom/"):
            anchor(p, d["when"], None, "look-absent:" + d["who"])

# agent app ops
for line in open(DATA / f"agent-{name}.jsonl"):
    r = json.loads(line)
    if r["tool"] not in ("Edit", "MultiEdit", "Write") or r.get("error"):
        continue
    p = r.get("path") or ""
    if p == COPY_MOVE[0]:
        p = COPY_MOVE[1]
    if p not in ops:
        continue
    t = norm(r["ts"])
    who = "agent-sub" if r["sub"] else "agent"
    if r["tool"] == "Edit":
        ops[p].append((t, "edit", {"edits": [(r["old"], r["new"], r.get("all"))], "actor": who}))
    elif r["tool"] == "MultiEdit":
        ops[p].append((t, "edit", {"edits": [(e["old"], e["new"], False) for e in r["edits"]], "actor": who}))
    else:
        ops[p].append((t, "write", {"to": r["content"], "actor": who}))

# relloc: hand-made snapshots of the copy, by their file time
if name == "relloc":
    snaps = glob.glob(str(root / ".loom/sessions/*/snapshot-*-examples-shared.tex")) + glob.glob(
        str(root / ".loom/build/s-2026-10-12-0001/examples-shared.before-*.tex")
    )
    for s in snaps:
        anchor(".loom/copies/examples-shared.tex", iso(os.path.getmtime(s)), open(s, encoding="utf-8").read(), "snapshot:" + os.path.basename(s))
    # the copy as made on 10-12 is the person's stub; the copy step's base
    anchor(".loom/copies/examples-shared.tex", "2026-10-12T17:10:34Z", (hist / "0002-copy-examples-shared/examples.tex").read_text(), "copy-base")
    anchor("drafting/examples.tex", "2026-10-12T17:10:34Z", (hist / "0002-copy-examples-shared/examples.tex").read_text(), "copy-base")
    anchor("drafting/examples.tex", "2026-11-04T19:01:05Z", (hist / "0003-examples-before-adopt-examples-shared/examples-before-adopt-examples-shared.tex").read_text(), "stamp:before-adopt")
    acts["drafting/examples.tex"].append(("2026-11-04T19:01:05Z", "adopt", "The synthetic quilt"))
    # draft5 as imported: received text with loom's ids; the drafted text is not kept, so the received text stands in
    anchor("drafting/draft5.tex", "2026-10-12T16:44:59Z", imp.read_text(), "import:received")
    acts["drafting/draft5.tex"].append(("2026-10-12T16:44:59Z", "import", "ikmartin"))

# now
for p in domain:
    fp = root / p
    if fp.is_file():
        try:
            anchor(p, iso(fp.stat().st_mtime), fp.read_text(encoding="utf-8"), "now")
        except UnicodeDecodeError:
            pass
    else:
        anchor(p, "2026-11-13T21:30:00Z", None, "now-absent")

# agent shell commands per path (by basename), for residuals
shell: list[tuple[str, str]] = []
for line in open(DATA / f"agent-{name}.jsonl"):
    r = json.loads(line)
    if r["tool"] == "Bash" and not r.get("error"):
        shell.append((norm(r["ts"]), r["cmd"]))
WRITEY = re.compile(r"sed -i|perl -[a-z]*i|write_text|open\([^)]*['\"][wa]|\.write\(|>\s*\S|\bcp\b|\bmv\b|loom (id|ai refresh|draft|adopt|write)")


def shell_touch(path: str, a: str, b: str) -> list[str]:
    base = os.path.basename(path)
    return [c for t, c in shell if a < t <= b and base in c and WRITEY.search(c)]


def apply_edit(text: str, edits) -> str | None:
    for old, new, al in edits:
        if old == "" and text == "":
            text = new
            continue
        if old not in text:
            return None
        text = text.replace(old, new) if al else text.replace(old, new, 1)
    return text


# ---- replay
states: dict[str, list[dict]] = {}
stats = {"ops": 0, "ops_failed": 0, "residuals": 0}
for p in sorted(domain):
    items = [(t, -1 if src in ("page-write-from", "tick-from") or src.startswith("stamp:") else 1, "anchor", (txt, src)) for t, txt, src in anchors[p]] + [(t, 0, "op", (k, d)) for t, k, d in ops[p]]
    items.sort(key=lambda x: (x[0], x[1]))
    seq: list[dict] = []
    cur: str | None = None
    known = False
    last_t = "0000"
    for t, _, kind, payload in items:
        if kind == "op":
            k, d = payload
            stats["ops"] += 1
            if k == "write":
                new = d["to"]
                if new is not None and new != cur:
                    seq.append({"t": t, "text": new, "by": d["actor"], "how": "write", "from_known": known})
                    cur, known, last_t = new, True, t
                continue
            if k == "loom-write":
                new = d["to"]
                actor = "agent-via-loom" if d["actor"] not in PERSON else "person-via-loom"
                if new is not None and new != cur:
                    seq.append({"t": t, "text": new, "by": actor, "how": "loom-write", "from_known": known})
                    cur, known, last_t = new, True, t
                continue
            if cur is None:
                stats["ops_failed"] += 1
                continue
            new = apply_edit(cur, d["edits"])
            if new is None:
                stats["ops_failed"] += 1
                seq.append({"t": t, "text": None, "by": d["actor"], "how": "edit-unplaced", "from_known": known})
                continue
            if new != cur:
                seq.append({"t": t, "text": new, "by": d["actor"], "how": "edit", "from_known": known})
                cur, last_t = new, t
            continue
        txt, src = payload
        if not seq and cur is None:
            seq.append({"t": t, "text": txt, "by": "origin", "how": src, "from_known": False})
            if txt is None:
                cur, known, last_t = None, True, t
                continue
            cur, known, last_t = txt, True, t
            continue
        if txt == cur:
            last_t = t
            continue
        if cur is None and txt is not None and seq and seq[-1]["text"] is None:
            # created between last_t and t by something the ops do not show
            pass
        # residual: what the replayed ops do not explain, between last_t and t
        stats["residuals"] += 1
        a = [x for x in acts[p] if last_t <= x[0] <= t]
        sh = shell_touch(p, last_t, t)
        if a:
            act, actor = a[-1][1], a[-1][2]
            by = {"adopt": "loom-adopt", "apply": "loom-keep", "tick": "person-tick", "import": "loom-import"}.get(act, "loom-" + act)
        elif p in GENERATED or p == "config.toml":
            by = "loom-housekeeping" if p in GENERATED else "person-or-settings"
        elif denied(p):
            by = "denied-residual"
        elif sh:
            by = "agent-shell"
        else:
            by = "unattributed"
        seq.append({"t": t, "text": txt, "by": by, "how": "residual:" + src, "since": last_t, "from_known": cur is not None, "shell": len(sh), "acts": [x[1] for x in a]})
        cur, last_t = txt, t
    states[p] = seq

pickle.dump({"states": states, "deny": DENY, "copies": COPIES, "stats": stats}, open(out, "wb"))
print(stats, "deny", DENY)
for p in sorted(states):
    seq = states[p]
    from collections import Counter

    c = Counter(s["by"] for s in seq[1:])
    print(f"{p:62s} states {len(seq):4d}  {dict(c)}")
