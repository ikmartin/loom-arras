"""Simulate the Changed list over a quilt's replayed history.

Usage: loom-venv-python simulate.py QUILT_DIR NAME STATES.pickle OUT.json

Step 1: each transition of each file is cut into units touched, each with who made it (per change for residuals).
Step 2: look moments from the person's own acts (strict) and from those plus their prompts to agents (loose), clustered into sittings.
Step 3: rows at each moment under each variant: deny rule, copies, unit, baseline.
"""
from __future__ import annotations

import bisect
import glob
import json
import pickle
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import units as U  # noqa: E402

root = Path(sys.argv[1]).resolve()
name = sys.argv[2]
D = pickle.load(open(sys.argv[3], "rb"))
out_path = sys.argv[4]
DATA = Path(__file__).resolve().parent.parent / "data"
states = D["states"]
DENY = D["deny"]
PERSON = {"ikmartin", "The synthetic quilt"}
GENERATED = {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}

# theorem-like environments declared anywhere in the quilt's own files
envs = set()
for p in glob.glob(str(root / "**/*.sty"), recursive=True) + glob.glob(str(root / "**/*.tex"), recursive=True) + glob.glob(str(root / ".loom/copies/*.tex")):
    if "/.loom/build/" in p or "/.loom/digests/" in p or "/.loom/sessions/" in p or "/.loom/history/" in p:
        continue
    try:
        envs |= set(re.findall(r"\\newtheorem\*?\{([A-Za-z]+)\}", open(p, encoding="utf-8", errors="replace").read()))
    except OSError:
        pass
U.set_envs(envs)


def denied(p):
    return any(p.startswith(d) for d in DENY)


# agent app activity: any tool call, for "coincides with a session"
agent_times = []
human_times = []
for line in open(DATA / f"agent-{name}.jsonl"):
    r = json.loads(line)
    t = r["ts"][:19] + "Z"
    if r["tool"] == "HUMAN":
        human_times.append(t)
    else:
        agent_times.append(t)
agent_times.sort()
human_times = sorted(set(human_times))


# loom's own records of agent activity: session messages, annotation and edit events, ledger acts, by anyone not the person
loom_agent_times = []
for f in glob.glob(str(root / ".loom/sessions/*/inbox.jsonl")):
    for line in open(f):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        w = e.get("from") or e.get("who") or e.get("author")
        if e.get("when") and w and w not in PERSON:
            loom_agent_times.append(e["when"][:19] + "Z")
for f in glob.glob(str(root / ".loom/annotations/log.jsonl")) + glob.glob(str(root / ".loom/edits/log.jsonl")):
    for line in open(f):
        e = json.loads(line)
        if e.get("when") and e.get("author") and e["author"] not in PERSON and e.get("kind") != "person":
            loom_agent_times.append(e["when"][:19] + "Z")
for line in open(root / ".loom/history/ledger.jsonl"):
    e = json.loads(line)
    if e["actor"] not in PERSON:
        loom_agent_times.append(e["when"][:19] + "Z")
loom_agent_times.sort()


def loom_session_active(a, b):
    i = bisect.bisect_right(loom_agent_times, a)
    return i < len(loom_agent_times) and loom_agent_times[i] <= b


def session_active(a, b):
    i = bisect.bisect_right(agent_times, a)
    return i < len(agent_times) and agent_times[i] <= b


# kept edits' texts (quant): a residual change carrying one is loom writing on the person's word
kept_texts = []
for f in glob.glob(str(root / ".loom/edits/log.jsonl")):
    for line in open(f):
        e = json.loads(line)
        if e.get("with") and len(e["with"].strip()) >= 12:
            kept_texts.append(e["with"].strip())
for f in glob.glob(str(root / ".loom/annotations/log.jsonl")):
    for line in open(f):
        e = json.loads(line)
        s = e.get("suggestion") or e.get("with")
        if isinstance(s, str) and len(s.strip()) >= 12:
            kept_texts.append(s.strip())

IMPORT_ONLY = re.compile(r"^(\s|\\label\{rl-[0-9A-Z]{4}\}|\\usepackage\{loom\})*$")


def residual_actor(p, s, prev, span):
    o0, o1, n0, n1 = span
    new = (s["text"] or "")[n0:n1]
    old = (prev["text"] or "")[o0:o1]
    by = s["by"]
    if by == "loom-adopt":
        return "loom-adopt"
    if by == "person-tick":
        return "person-tick"
    if p in GENERATED:
        return "loom-housekeeping"
    if p == "config.toml":
        return "person-settings"
    if by in ("loom-keep",) or (denied(p) and s.get("acts")):
        if any(k in new or (len(new.strip()) >= 12 and new.strip() in k) for k in kept_texts):
            return "loom-keep"
    if by == "loom-import" or p == "drafting/draft5.tex":
        # strip loom's own import additions from both sides; what is left is the person's
        strip = lambda x: re.sub(r"\\label\{rl-[0-9A-Z]{4}\}|\\usepackage\{loom\}|%[^\n]*", "", x).split()  # noqa: E731
        if strip(new) == strip(old):
            return "loom-import"
    if denied(p):
        return "person-denied"
    if by == "agent-shell":
        return "agent-shell"
    if session_active(s.get("since", "0"), s["t"]):
        return "agent-session"
    if loom_session_active(s.get("since", "0"), s["t"]):
        return "agent-loom-session"
    return "unattributed"


# ---- step 1: transitions -> (t, unit, actor)
TRUTH = {
    # what inspection of each class found (step 4 of the study): residuals in agent-written files while a session ran were agents' shell scripts
    "agent": "agent", "agent-sub": "agent", "agent-via-loom": "agent", "agent-shell": "agent", "agent-session": "agent", "agent-loom-session": "agent",
    "loom-adopt": "loom-on-person", "loom-keep": "loom-on-person", "person-tick": "person", "person-settings": "person",
    "person-denied": "person", "loom-import": "loom", "loom-housekeeping": "loom", "unattributed": "unknown",
}
events = []  # (t, path, ukind, key, actor)
trans_count = Counter()
for p, seq in states.items():
    prev = None
    for s in seq:
        if s["by"] == "origin" or s["how"] == "edit-unplaced":
            if s["by"] == "origin":
                prev = s
            continue
        if s["text"] is None and s["how"] != "edit-unplaced":
            if prev is not None and prev["text"] is not None:
                actor = residual_actor(p, {**s, "text": ""}, prev, (0, len(prev["text"]), 0, 0))
                events.append((s["t"], p, "gonefile", p, actor))
                trans_count[actor] += 1
            prev = s
            continue
        if prev is None:
            if s["text"] is not None:
                events.append((s["t"], p, "newfile", p, s["by"]))
                for u, k in U.touched(p, None, s["text"]):
                    events.append((s["t"], p, u, k, s["by"]))
            prev = s
            continue
        old, new = prev["text"], s["text"]
        if old is None:
            a0 = s["by"] if not s["how"].startswith("residual") else residual_actor(p, s, {"text": ""}, (0, 0, 0, len(new)))
            events.append((s["t"], p, "newfile", p, a0))
            for u, k in U.touched(p, None, new):
                events.append((s["t"], p, u, k, a0))
            prev = s
            continue
        if old == new:
            continue
        if s["how"] == "edit":
            sp = U.quick_span(old, new)
        else:
            sp = U.spans(old, new)
        un, uo = U.units(p, new), U.units(p, old)
        if s["how"].startswith("residual"):
            for span in sp:
                actor = residual_actor(p, s, prev, span)
                for u, k in U.touched(p, old, new, [span], uo, un):
                    events.append((s["t"], p, u, k, actor))
                trans_count[actor] += 1
        else:
            actor = s["by"]
            for u, k in U.touched(p, old, new, sp, uo, un):
                events.append((s["t"], p, u, k, actor))
            trans_count[actor] += 1
        prev = s
events.sort()


def state_at(p, t):
    seq = states[p]
    cur = None
    for s in seq:
        if s["t"] > t:
            break
        if s["how"] == "edit-unplaced":
            continue
        cur = s["text"]
    return cur


_TOUCH = {}


def touched_cached(p, sa, sb):
    k = (p, hash(sa), hash(sb))
    if k not in _TOUCH:
        _TOUCH[k] = U.touched(p, sa, sb)
    return _TOUCH[k]


# ---- step 2: look moments
acts = []
for line in open(root / ".loom/history/ledger.jsonl"):
    e = json.loads(line)
    if e["actor"] in PERSON:
        acts.append(e["when"][:19] + "Z")
for f in glob.glob(str(root / ".loom/annotations/*.jsonl")) + glob.glob(str(root / ".loom/edits/*.jsonl")):
    if f.endswith("before-0.30"):
        continue
    for line in open(f):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("author") in PERSON or e.get("kind") == "person":
            if e.get("when"):
                acts.append(e["when"][:19] + "Z")
for f in glob.glob(str(root / ".loom/looked/*.json")):
    acts.append(json.load(open(f))["when"][:19] + "Z")
acts.sort()


def sittings(ts, gap_min=30):
    from datetime import datetime

    out = []
    last = None
    for t in ts:
        dt = datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ")
        if last is None or (dt - last).total_seconds() > gap_min * 60:
            out.append(t)
        last = dt
    return out


NOW = "2026-11-13T21:30:00Z"
strict = sittings(acts) + [NOW]
loose = sittings(sorted(set(acts) | set(human_times))) + [NOW]

# ---- step 3: rows
files = sorted(states)
COPY = lambda p: p.startswith(".loom/copies/")  # noqa: E731
SHOWN_ACTORS_ABSORBED = {"loom-keep", "person-tick", "person-settings"}  # loom moves the look with these


def in_unit(u, p, unit):
    k = U.kind_of(p)
    if u in ("newfile", "gonefile"):
        return unit in ("U2", "U3") or (unit == "U1" and k == "tex")
    if u in ("block", "removed"):
        return True
    if u == "md":
        return unit in ("U2", "U3")
    if u in ("prose", "other"):
        return unit == "U3"
    return False


def rows_between(a, b, deny_rule, copies, unit, filter_person=True):
    rows = []
    for p in files:
        if COPY(p) and not copies:
            continue
        if U.kind_of(p) == "other" and unit != "U3" and not p.endswith(".tex"):
            # other files appear only as new/removed below
            pass
        ev = [e for e in events if e[1] == p and a < e[0] <= b]
        if not ev:
            continue
        sa, sb = state_at(p, a), state_at(p, b)
        if sa == sb:
            continue
        if sa is not None and sb is None:
            hit = {("gonefile", p)}
        elif sa is None and sb is not None:
            hit = {("newfile", p)} if unit != "U1" else {(u, k) for u, k in U.touched(p, None, sb) if u == "block"}
        else:
            hit = touched_cached(p, sa, sb)
        by_unit = defaultdict(set)
        for t, _, u, k, actor in ev:
            by_unit[(u, k)].add(actor)
        for u, k in hit:
            if not in_unit(u, p, unit):
                continue
            actors = by_unit.get((u, k)) or by_unit.get(("removed" if u == "block" else u, k)) or {"?"}
            truth = {TRUTH.get(x, "unknown") for x in actors}
            if filter_person:
                if denied(p) and deny_rule == "person" and not (actors & {"loom-adopt"}):
                    continue  # absorbed as the person's own; an adoption, which loom performs, still shows
                if actors <= SHOWN_ACTORS_ABSORBED:
                    continue  # loom wrote it on the person's word and moved the look
            rows.append({"path": p, "unit": u, "key": k, "actors": sorted(actors), "truth": sorted(truth)})
    return rows


def classify(r):
    t = set(r["truth"])
    if t <= {"person"}:
        return "person-own"
    if "agent" in t:
        return "agent"
    if t & {"loom-on-person"}:
        return "loom-taken-in"
    if t & {"loom"}:
        return "loom-housekeeping"
    return "unknown"


results = {}
# the first look loom actually took in this quilt: "never cleared since"
first_moment = min(json.load(open(f))["when"][:19] + "Z" for f in glob.glob(str(root / ".loom/looked/*.json")))
for moments_name, moments in (("strict", strict), ("loose", loose)):
    for deny_rule in ("person", "shown"):
        for copies in ((False, True) if any(COPY(p) for p in files) else (False,)):
            for unit in ("U1", "U2", "U3"):
                for base in ("M1", "M2", "ACC"):
                    series = []
                    prev = None
                    for m in moments:
                        if base != "M1" and m < first_moment:
                            continue
                        if base == "M1":
                            a = prev if prev is not None else "0000"
                        else:
                            a = first_moment
                        if base == "M1" and prev is None:
                            prev = m
                            continue
                        rows = rows_between(a, m, deny_rule, copies, unit, filter_person=(base != "ACC"))
                        comp = Counter(classify(r) for r in rows)
                        kinds = Counter(r["unit"] for r in rows)
                        series.append({"t": m, "n": len(rows), "by": dict(comp), "units": dict(kinds), "files": dict(Counter(r["path"] for r in rows))})
                        prev = m
                    key = f"{moments_name}|deny={deny_rule}|copies={copies}|{unit}|{base}"
                    ns = [s["n"] for s in series]
                    worst = max(series, key=lambda s: s["n"]) if series else None
                    results[key] = {
                        "moments": len(series),
                        "median": statistics.median(ns) if ns else 0,
                        "p90": sorted(ns)[int(0.9 * (len(ns) - 1))] if ns else 0,
                        "max": max(ns) if ns else 0,
                        "zero": sum(1 for n in ns if n == 0),
                        "person_own_total": sum(s["by"].get("person-own", 0) for s in series),
                        "rows_total": sum(ns),
                        "worst": worst,
                        "series": series,
                    }

json.dump({"envs": sorted(envs), "strict": strict, "loose": loose, "acts": acts, "trans": dict(trans_count), "events": len(events), "results": results}, open(out_path, "w"), indent=1)
print("envs", len(envs), "events", len(events), "transitions by actor", dict(trans_count))
print("strict moments", len(strict), strict)
print("loose moments", len(loose))
for k, v in results.items():
    w = v["worst"]
    print(f"{k:52s} n={v['moments']:3d} median={v['median']:6} p90={v['p90']:5} max={v['max']:5} zero={v['zero']:3d} own={v['person_own_total']:4d}  worst@{w['t'] if w else ''} {w['by'] if w else ''}")
