"""usage: python3 pend.py PORT -- the pending changes and unresolved rows the manifest lists now."""
import json, sys, urllib.request
m = json.load(urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/build/manifest.json"))
for c in m.get("changes") or []:
    print("CHANGE", c["id"], c["kind"], c["state"], c["key"], repr(c["old"][:40]), "->", repr(c["new"][:50]), (c.get("why") or "")[:90])
un = m.get("unresolved") or []
import collections
print("UNRESOLVED", len(un), collections.Counter(r["cause"] for r in un))
for r in un:
    if r["cause"] != "never-accepted": print("  ", r["key"], r["cause"], (r.get("refusal") or "")[:60])
