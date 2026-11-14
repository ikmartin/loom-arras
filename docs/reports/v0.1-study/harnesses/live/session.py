"""One Claude Code conversation in a quilt, turn by turn: python3 session.py NAME QUILT MCPCONFIG MODE TURNS_JSON [PAUSE_JSON]
TURNS_JSON is a list of prompts; PAUSE_JSON maps a turn index to a shell command run before that turn (to change the world mid-conversation).
Writes S/sessions/NAME.jsonl (every event, with receive time) and prints a summary."""
import json, os, subprocess, sys, time
S = os.path.dirname(os.path.abspath(__file__))
name, quilt, mcp, mode, turns = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], json.loads(sys.argv[5])
pauses = json.loads(sys.argv[6]) if len(sys.argv) > 6 else {}
person_path = f"{S}/uv/bin:" + os.environ["PATH"]
env = {k: os.environ[k] for k in ("HOME", "USER", "LOGNAME", "TMPDIR") if k in os.environ}
env.update(LANG="en_US.UTF-8", TERM="xterm-256color", PATH=person_path,
           XDG_CONFIG_HOME=f"{S}/xdg/config", XDG_DATA_HOME=f"{S}/xdg/data", XDG_CACHE_HOME=f"{S}/xdg/cache")
if os.environ.get("FAKEAPI"):
    env.update(ANTHROPIC_BASE_URL=os.environ["FAKEAPI"], ANTHROPIC_API_KEY="sk-ant-local-fake-not-a-key", CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1")
if os.environ.get("LOOM_REAL"):
    env["LOOM_REAL"] = os.environ["LOOM_REAL"]
cmd = [os.path.expanduser("~/.local/bin/claude"), "-p", "--model", "haiku", "--input-format", "stream-json",
       "--output-format", "stream-json", "--verbose", "--no-session-persistence", "--max-budget-usd", "0.60",
       "--setting-sources", "project,local", "--permission-prompts", "none"]
if mcp != "-":
    cmd += ["--strict-mcp-config", "--mcp-config", mcp]
else:
    cmd += ["--strict-mcp-config"]
if os.environ.get("SETTINGS"):
    cmd += ["--settings", ".claude/settings.json"]
if mode != "default":
    cmd += ["--permission-mode", mode]
out = open(f"{S}/sessions/{name}.jsonl", "w")
t0 = time.time()
print(f"start {t0:.3f}")
p = subprocess.Popen(cmd, cwd=quilt, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
def events_until_result():
    while True:
        line = p.stdout.readline()
        if not line:
            return None
        ev = json.loads(line); ev["_t"] = time.time()
        out.write(json.dumps(ev) + "\n"); out.flush()
        yield ev
        if ev.get("type") == "result":
            return
for i, prompt in enumerate(turns):
    if str(i) in pauses:
        print(f"== pause before turn {i}: {pauses[str(i)]}")
        r = subprocess.run(pauses[str(i)], shell=True, capture_output=True, text=True)
        print((r.stdout + r.stderr)[-1500:])
    ts = time.time()
    out.write(json.dumps({"type": "_sent", "turn": i, "prompt": prompt, "_t": ts}) + "\n")
    p.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": prompt}}) + "\n"); p.stdin.flush()
    print(f"\n######## turn {i} sent at +{ts-t0:.1f}s: {prompt}")
    for ev in events_until_result():
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            print("INIT mcp_servers:", ev.get("mcp_servers"), "| permissionMode:", ev.get("permissionMode"))
            print("INIT slash_commands:", ev.get("slash_commands"))
            print("INIT tools with loom:", [x for x in ev.get("tools", []) if "loom" in x][:60], "count all tools", len(ev.get("tools", [])))
        elif t == "assistant":
            for c in ev["message"].get("content", []):
                if c.get("type") == "tool_use":
                    print(f"  [+{ev['_t']-t0:.1f}s] TOOL_USE {c['name']} {json.dumps(c.get('input'))[:400]}")
                elif c.get("type") == "text":
                    pass
            u = ev["message"].get("usage", {})
            print(f"  usage: in={u.get('input_tokens')} cache_create={u.get('cache_creation_input_tokens')} cache_read={u.get('cache_read_input_tokens')} out={u.get('output_tokens')}")
        elif t == "user":
            for c in ev["message"].get("content", []) if isinstance(ev["message"].get("content"), list) else []:
                if c.get("type") == "tool_result":
                    txt = c.get("content")
                    if isinstance(txt, list):
                        txt = " ".join(x.get("text", "") for x in txt if isinstance(x, dict))
                    print(f"  RESULT err={c.get('is_error')} {str(txt)[:300]!r}")
        elif t == "result":
            print(f"RESULT turn {i} at +{ev['_t']-t0:.1f}s: cost=${ev.get('total_cost_usd')} turns={ev.get('num_turns')} denials={json.dumps(ev.get('permission_denials'))[:800]}")
            print("usage:", json.dumps(ev.get("usage"))[:400])
            print("FINAL TEXT:\n" + str(ev.get("result")))
p.stdin.close()
p.wait(timeout=60)
print(f"\nclaude exited {p.returncode} at +{time.time()-t0:.1f}s; stderr: {p.stderr.read()[-800:]}")
