"""A scripted stand-in for the Messages API on 127.0.0.1:PORT, so the real Claude Code client runs its real MCP start-up and permission checks on tool calls chosen in advance.
Main-loop requests (those carrying tools) take the next step of S/fake/script.json: {"tool": NAME, "input": {...}} or {"text": "..."}; every main request is saved to S/fake/req/NNN.json."""
import json, os, sys, time, itertools
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
D = os.path.dirname(os.path.abspath(__file__))
port = int(sys.argv[1])
counter = itertools.count(1)
state = {"step": 0, "script": None, "mtime": 0}
def script():
    p = f"{D}/script.json"; m = os.path.getmtime(p)
    if m != state["mtime"]:
        state.update(script=json.load(open(p)), mtime=m, step=0)
    return state["script"]
def log(msg):
    with open(f"{D}/api.log", "a") as f: f.write(f"{time.time():.3f} {msg}\n")
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        log(f"GET {self.path}"); self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(b"{}")
    def do_HEAD(self):
        self.send_response(200); self.end_headers()
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("content-length", 0)))
        try: req = json.loads(body)
        except Exception: req = {}
        n = next(counter)
        if "count_tokens" in self.path:
            self._json({"input_tokens": len(body) // 4}); log(f"#{n} count_tokens {len(body)}"); return
        tools = req.get("tools") or []
        main = len(tools) > 5
        if main:
            with open(f"{D}/req/{n:03d}.json", "wb") as f: f.write(body)
            steps = script(); i = state["step"]
            step = steps[i] if i < len(steps) else {"text": "(script ended)"}
            state["step"] = i + 1
        else:
            step = {"text": "ok"}
        last = req.get("messages", [{}])[-1] if req.get("messages") else {}
        lc = last.get("content")
        lhead = json.dumps(lc)[:200] if lc is not None else ""
        log(f"#{n} {self.path} main={main} bytes={len(body)} tools={len(tools)} msgs={len(req.get('messages', []))} step={step if main else '-'} last={lhead}")
        content = [{"type": "tool_use", "id": f"toolu_{n:04d}", "name": step["tool"], "input": step.get("input", {})}] if "tool" in step else [{"type": "text", "text": step["text"]}]
        stop = "tool_use" if "tool" in step else "end_turn"
        usage = {"input_tokens": len(body) // 4, "output_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
        if not req.get("stream"):
            self._json({"id": f"msg_{n}", "type": "message", "role": "assistant", "model": req.get("model", "x"), "content": content, "stop_reason": stop, "stop_sequence": None, "usage": usage}); return
        self.send_response(200); self.send_header("content-type", "text/event-stream"); self.end_headers()
        def ev(t, d): self.wfile.write(f"event: {t}\ndata: {json.dumps(d)}\n\n".encode()); self.wfile.flush()
        ev("message_start", {"type": "message_start", "message": {"id": f"msg_{n}", "type": "message", "role": "assistant", "model": req.get("model", "x"), "content": [], "stop_reason": None, "stop_sequence": None, "usage": usage}})
        c = content[0]
        if c["type"] == "text":
            ev("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}})
            ev("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": c["text"]}})
        else:
            ev("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": c["id"], "name": c["name"], "input": {}}})
            ev("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": json.dumps(c["input"])}})
        ev("content_block_stop", {"type": "content_block_stop", "index": 0})
        ev("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None}, "usage": {"output_tokens": 10}})
        ev("message_stop", {"type": "message_stop"})
    def _json(self, o):
        b = json.dumps(o).encode(); self.send_response(200); self.send_header("content-type", "application/json"); self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b)
ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
