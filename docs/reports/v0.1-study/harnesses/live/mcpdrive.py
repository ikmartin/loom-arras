"""Drive a stdio MCP server: python3 mcpdrive.py CALLS_JSON -- cmd...; CALLS_JSON is a list of [tool, args]. Prints timings and result heads."""
import json, subprocess, sys, time
calls = json.loads(sys.argv[1]); cmd = sys.argv[sys.argv.index("--") + 1:]
t0 = time.time()
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
def send(o): p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
def recv(i):
    while True:
        line = p.stdout.readline()
        if not line:
            return None
        m = json.loads(line)
        if m.get("id") == i: return m
send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "0"}}})
r = recv(1)
print(f"initialize {time.time()-t0:.2f}s:", (json.dumps(r)[:300] if r else "NO REPLY; stderr: " + p.stderr.read()[:2000]))
if not r: sys.exit(1)
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}); r = recv(2); print("tools:", len(r["result"]["tools"]))
for n, (tool, args) in enumerate(calls, start=3):
    t = time.time()
    send({"jsonrpc": "2.0", "id": n, "method": "tools/call", "params": {"name": tool, "arguments": args}})
    r = recv(n)
    res = r.get("result", r.get("error"))
    txt = " ".join(c.get("text", "") for c in res.get("content", [])) if isinstance(res, dict) and "content" in res else json.dumps(res)
    print(f"--- {tool} {json.dumps(args)} [{time.time()-t:.2f}s] isError={res.get('isError') if isinstance(res, dict) else None} meta={res.get('_meta') if isinstance(res, dict) else None}\n{txt[:900]}")
p.stdin.close(); p.wait(timeout=20)
print("exit", p.returncode, "stderr:", p.stderr.read()[:500])
