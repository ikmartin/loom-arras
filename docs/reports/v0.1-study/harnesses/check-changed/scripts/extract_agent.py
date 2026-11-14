"""Extract every agent tool call touching a quilt from Claude Code transcripts.

Usage: python3 -I extract_agent.py QUILT OUT.jsonl  (QUILT is relloc or quant)
Writes one line per tool call: ts, session, sub (subagent file?), tool, path (quilt-relative or None), cmd, old, new, content_len, error.
Also one line per human prompt: tool='HUMAN'.
"""
import glob
import json
import os
import re
import sys

quilt = sys.argv[1]
out = sys.argv[2]
roots = {
    "relloc": ["/Users/isaac/quilts/relloc/", "/Users/isaac/notes/quilts/relloc/"],
    "quant": ["/Users/isaac/quilts/quant/"],
}[quilt]
dirs = {
    "relloc": ["-Users-isaac-quilts-relloc", "-Users-isaac-notes-quilts-relloc"],
    "quant": ["-Users-isaac-quilts-quant"],
}[quilt]


def rel(p):
    if not p:
        return None
    for r in roots:
        if p.startswith(r):
            return p[len(r):]
    if not p.startswith("/"):
        return p
    return "OUTSIDE:" + p


files = []
for d in dirs:
    base = os.path.expanduser("~/.claude/projects/" + d)
    files += glob.glob(base + "/*.jsonl") + glob.glob(base + "/*/subagents/*.jsonl") + glob.glob(base + "/*/*/*.jsonl")
files = sorted(set(files))
rows = []
seen = set()
for f in files:
    sub = "/subagents/" in f or f.count("/") > len(os.path.expanduser("~/.claude/projects/x/y.jsonl").split("/")) - 1 and not f.endswith(".jsonl") is False and "/subagents/" in f
    session = f.split("/projects/")[1]
    errors = {}
    uses = []
    agent_name = None
    for line in open(f, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        t = d.get("type")
        if t == "user":
            msg = d.get("message", {})
            content = msg.get("content")
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        errors[c.get("tool_use_id")] = bool(c.get("is_error"))
            origin = (d.get("origin") or {}).get("kind")
            if origin == "human" and not d.get("isSidechain"):
                text = content if isinstance(content, str) else " ".join(
                    c.get("text", "") for c in (content or []) if isinstance(c, dict) and c.get("type") == "text"
                )
                rows.append({"ts": d["timestamp"], "session": session, "sub": "/subagents/" in f, "tool": "HUMAN", "len": len(text)})
        elif t == "assistant":
            for c in d.get("message", {}).get("content", []) or []:
                if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                    continue
                name = c["name"]
                inp = c.get("input") or {}
                row = {"ts": d["timestamp"], "session": session, "sub": "/subagents/" in f, "tool": name, "id": c.get("id")}
                if name in ("Edit", "Write", "MultiEdit", "NotebookEdit", "Read"):
                    row["path"] = rel(inp.get("file_path") or inp.get("notebook_path"))
                    if name == "Edit":
                        row["old"] = inp.get("old_string", "")
                        row["new"] = inp.get("new_string", "")
                        row["all"] = bool(inp.get("replace_all"))
                    elif name == "MultiEdit":
                        row["edits"] = [{"old": e.get("old_string", ""), "new": e.get("new_string", "")} for e in inp.get("edits", [])]
                    elif name == "Write":
                        row["content"] = inp.get("content", "")
                elif name == "Bash":
                    row["cmd"] = inp.get("command", "")
                elif name.startswith("mcp__"):
                    row["mcp"] = {k: (v if len(json.dumps(v)) < 400 else "…") for k, v in inp.items()}
                else:
                    if name not in ("Read", "Grep", "Glob", "TodoWrite"):
                        row["inp"] = {k: str(v)[:200] for k, v in inp.items()}
                uses.append(row)
    for row in uses:
        uid = row.pop("id")
        if uid in seen:
            continue
        seen.add(uid)
        row["error"] = errors.get(uid, None)
        rows.append(row)
rows.sort(key=lambda r: r["ts"])
with open(out, "w") as fh:
    for r in rows:
        fh.write(json.dumps(r) + "\n")
print(len(files), "files,", len(rows), "rows")
