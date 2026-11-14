import json, sys, collections
m = json.load(open(sys.argv[1]))
print("== Your Changes")
un = m.get("unresolved") or []
print("unresolved rows", len(un), collections.Counter(r["cause"] for r in un))
print("  refusals", collections.Counter((r.get("refusal") or "")[:60] for r in un))
ch = m.get("changes") or []
print("changes", len(ch), collections.Counter((c["kind"], c["state"]) for c in ch))
print("changes by author", collections.Counter(str(c.get("author")) for c in ch))
print("changes by doc", collections.Counter(tuple(c.get("documents") or []) for c in ch))
ann = m.get("annotations") or {}
print("annotations", len(ann))
print("== Proposed")
print("contributions", [(c.get("kind"), c.get("copy"), c.get("label")) for c in m.get("contributions") or []])
print("incoming", bool(m.get("incoming")))
res = {k: sum(1 for r in (v.get("results") or {}).values() if r.get("state") == "proposed") for k, v in (m.get("references") or {}).items()}
print("works with proposed results", {k: v for k, v in res.items() if v})
print("== Problems")
d = m.get("diagnostics") or []
print("diagnostics", len(d), collections.Counter(x["severity"] for x in d))
print("owner x severity", collections.Counter((x.get("owner"), x["severity"]) for x in d))
yours = [x for x in d if x["severity"] != "info" and x.get("owner") not in ("copy", "work")]
print("YOURS (counted)", len(yours))
for code, n in collections.Counter(x["code"] for x in yours).most_common():
    ex = next(x for x in yours if x["code"] == code)
    locs = collections.Counter((l["file"].split("/")[0] + "/" + l["file"].split("/")[1] if "/" in l["file"] else l["file"]) for x in yours if x["code"] == code for l in x["locations"][:1])
    print(f"  {n:4d} {code} [{ex['severity']}] {ex['message'][:110]!r} files={dict(locs)}")
print("ALL by code/owner/severity")
for (code, own, sev), n in sorted(collections.Counter((x["code"], x.get("owner"), x["severity"]) for x in d).items(), key=lambda t: -t[1]):
    print(f"  {n:4d} {code} {own} {sev}")
print("== Record")
print("sessions", [(s["id"], s["state"]) for s in m.get("sessions") or []])
print("history steps", len((m.get("history") or {}).get("steps") or []), "canon", len(m.get("canon") or []))
print("track_edits", (m.get("config") or {}).get("review"), "reviewer", m.get("reviewer"))
