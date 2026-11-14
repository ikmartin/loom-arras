"""Summarise run directories: sequences, failing sequences, and each check's first failure per sequence, with the duplication class.

usage: analyze.py RUNDIR...
"""
import collections, json, re, sys
from pathlib import Path

def finding(check, op, detail):
    cls = (re.match(r"\[([a-z-?]+)\]", detail) or [None, None])[1]
    if check == "paragraph-repeated" and op in ("restore", "undo_keep_record"):
        return "restored a version that already held copies (quant history)"
    if check == "repeat-changed" and op == "repeat":
        return "keep-all pressed again kept what the first press refused (benign)"
    if check == "no-version-before-write" and op == "settings":
        return "SAFE-10 no version (settings)"
    if check == "no-version-before-write" and op in ("restore", "undo_keep_record"):
        return "SAFE-5 restore overwrote a file kept nowhere"
    if check == "no-version-before-write":
        return "SAFE-10 no version (keep into a conflicted or unread document)"
    if check == "undo-keep-not-exact":
        return "SAFE-9/10 undo of keep refused or inexact"
    if check in ("duplicated", "open-ready-but-in-text", "paragraph-repeated", "marker-count") or (check == "repeat-changed" and op != "repeat"):
        if check == "marker-count" and op == "concurrent_keep":
            return "SAFE-2 race"
        return f"SAFE-1 written twice [{cls or '?'}]"
    if check == "typed-bytes-lost":
        return "SAFE-2 save lost" if op == "save_during_keep" else "typed-bytes-lost (other)"
    if check == "kept-but-absent":
        return "SAFE-2 race" if op == "concurrent_keep" else "SAFE-9 record says kept, text gone (restore/undo)"
    if check == "phantom-taken": return "SAFE-8 taken, never written"
    if check == "config-mode-changed": return "SAFE-10 config mode"
    if check == "no-version-before-write": return f"SAFE-5/10 no version before write ({op})"
    if check in ("line-endings-rewritten", "version-not-byte-exact"): return "SAFE-6 bytes not kept/written exactly"
    if check in ("discard-left-change", "undo-discard-not-exact"): return "SAFE-7 discard in CRLF"
    if check == "restore-not-exact": return "SAFE-6 bytes not kept/written exactly"
    return f"{check}@{op}"

for d in (sys.argv[1:] if __name__ == '__main__' else []):
    rows = [json.loads(l) for l in open(Path(d) / "results.jsonl")]
    per = collections.Counter(); seqs_with = collections.Counter(); acts = 0
    for r in rows:
        acts += r["acts"]
        seen = set()
        for f in r["first"]:
            seen.add(finding(f["check"], f["op"], f["detail"]))
        for sig in r["sigs"]:  # every check@op, even past the details kept
            c, op = sig.split("@")
            k = finding(c, op, "")
            if not any(x.split(" [")[0] == k.split(" [")[0] for x in seen):
                seen.add(k)
        for k in seen: seqs_with[k] += 1
    failing = sum(1 for r in rows if r["sigs"])
    DAMAGE = ("SAFE-1 ", "SAFE-2 ", "SAFE-5 ", "SAFE-6 ", "SAFE-7 ")
    damage = organic = 0
    for r in rows:
        ks = {finding(f["check"], f["op"], f["detail"]) for f in r["first"]} | {finding(*sig.split("@"), "") for sig in r["sigs"]}
        damage += any(k.startswith(DAMAGE) for k in ks)
        organic += any(k.startswith(DAMAGE) and not k.startswith("SAFE-2 save lost") for k in ks)
    print(f"== {d}: {len(rows)} sequences, {acts} acts, {failing} with at least one failure, {damage} with damage to text, {organic} of them without the injected save")
    for k, n in seqs_with.most_common():
        print(f"   {n:4d} seqs  {k}")
