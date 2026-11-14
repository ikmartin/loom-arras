"""Kill a Keep at each point, then look at the quilt as loom finds it on its next start, and press Keep again.

usage: crash.py SYNTHETIC_SRC WORK
"""
import json, os, shutil, subprocess, sys
from pathlib import Path
for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"): os.environ.pop(m, None)
BIN = Path("/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin")
src, work = Path(sys.argv[1]), Path(sys.argv[2])
NODE = "drafting/nodes/sy-000A.tex"
CASES = {
    # name: (quote, with, placement, person edit inside before the second press)
    "in-block-short": ("with the swap.", "Each swap fixes nothing.", "--after", None),
    "in-block-short-edited": ("with the swap.", "Each swap fixes nothing.", "--after", ("Each swap fixes nothing.", "Each swap fixes no point.")),
    "after-end": ("\\end{remark}", "A gadget with three points has one fixed point.", "--after", None),
    "in-block-long": ("with the swap.", " ".join(["The swap on two points has no fixed point, and so the fixed locus is empty; this is the smallest gadget that is not trivial, and every other one contains it."]), "--after", None),
}

def loom(q, *args, agent=False):
    env = dict(os.environ)
    if agent: env["AI_AGENT"] = "1"
    return subprocess.run([str(BIN / "loom"), *args, "--quilt", str(q)], capture_output=True, text=True, env=env)

out = {}
for point in ("before-write", "mid-write", "after-write", "after-record"):
    for case, (quote, new, where, edit_inside) in CASES.items():
        q = work / f"{point}-{case}"
        shutil.rmtree(q, ignore_errors=True)
        shutil.copytree(src, q, ignore=shutil.ignore_patterns("build"))
        r = loom(q, "suggest", "sy-000A", "--quote", quote, "--with", new, where, "--as", "Agent Smith", "--json", agent=True)
        eid = json.loads(r.stdout)["edit"]
        before = (q / NODE).read_bytes()
        cp = subprocess.run([str(BIN / "python"), str(Path(__file__).parent / "crash_child.py"), point, str(q), eid], capture_output=True, text=True, env=dict(os.environ))
        after_crash = (q / NODE).read_text()
        tmp = sorted(str(p.relative_to(q)) for p in q.rglob("*.loom-tmp") if ".loom" not in p.relative_to(q).parts)
        log = [json.loads(x) for x in (q / ".loom/edits/log.jsonl").read_text().splitlines() if x.strip()]
        status = "kept" if any(e.get("event") == "kept" and e["id"] == eid for e in log) else "open"
        ledger = [json.loads(x) for x in (q / ".loom/history/ledger.jsonl").read_text().splitlines() if x.strip()]
        applied = any(e.get("action") == "apply" and (e.get("edit") == eid or (e.get("data") or {}).get("edit") == eid) for e in ledger)
        # what loom says on its next start
        ch = loom(q, "changes", "--json")
        try:
            listed = {c["id"]: c["state"] for c in json.loads(ch.stdout).get("changes", [])}
        except Exception:
            listed = ch.stdout[-300:]
        doctor = loom(q, "doctor")
        lint = loom(q, "lint")
        noticed = [w for w in ("loom-tmp", "apply", eid) if w in doctor.stdout + doctor.stderr + lint.stdout + lint.stderr]
        if edit_inside:
            t = (q / NODE).read_text(); (q / NODE).write_text(t.replace(*edit_inside))
        k2 = loom(q, "changes", "--keep", eid)
        final = (q / NODE).read_text()
        copies = final.count(new) + (final.count(edit_inside[1]) if edit_inside else 0)
        out[f"{point}/{case}"] = {"exit": cp.returncode, "copies_after_crash": after_crash.count(new), "tmp_left": tmp, "status_after_crash": status, "apply_line": applied,
                                  "listed_as": listed.get(eid) if isinstance(listed, dict) else listed, "doctor_or_lint_noticed": noticed,
                                  "second_keep": (k2.stdout + k2.stderr).strip()[-120:], "copies_final": copies}
        print(f"{point:13} {case:22} exit={cp.returncode} copies_after_crash={after_crash.count(new)} tmp={tmp} status={status} apply_line={applied} listed={out[f'{point}/{case}']['listed_as']} noticed={noticed} copies_final={copies}", flush=True)
json.dump(out, open(work / "crash.json", "w"), indent=1)
