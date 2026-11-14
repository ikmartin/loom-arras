#!/usr/bin/env python3
"""Stand between the agent's client and loom's MCP server: log argv, env, every line each way, and how and when the server ends."""
import os, sys, time, json, signal, subprocess, threading
L = "/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/presence/%d-%d" % (time.time(), os.getpid()); os.makedirs(L)
meta = open(L + "/meta", "a", buffering=1)
def note(s): meta.write(f"{time.time():.3f} {s}\n")
note("start argv=" + " ".join(sys.argv[1:]) + f" cwd={os.getcwd()} ppid={os.getppid()} pgid={os.getpgid(0)} sid={os.getsid(0)}")
for k, v in sorted(os.environ.items()):
    if k.startswith(("CLAUDE", "AI_AGENT", "CODEX", "MCP")) and "TOKEN" not in k: note(f"env {k}={v}")
note("env PATH=" + os.environ.get("PATH", ""))
real = os.environ.get("LOOM_REAL") or "/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/uv/tools/loomtex/bin/loom"
child = subprocess.Popen([real, *sys.argv[1:]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
note(f"child pid={child.pid} {real}")
def on_sig(n, f):
    note(f"signal {signal.Signals(n).name} received; forwarding"); child.send_signal(n)
for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP): signal.signal(s, on_sig)
inl = open(L + "/stdin.jsonl", "ab"); outl = open(L + "/stdout.jsonl", "ab")
def pump_in():
    for line in sys.stdin.buffer:
        inl.write(line); inl.flush()
        try: child.stdin.write(line); child.stdin.flush()
        except BrokenPipeError: break
    note("stdin EOF from client"); 
    try: child.stdin.close()
    except Exception: pass
threading.Thread(target=pump_in, daemon=True).start()
for line in child.stdout:
    outl.write(line); outl.flush()
    try: sys.stdout.buffer.write(line); sys.stdout.buffer.flush()
    except BrokenPipeError: note("client stdout closed"); break
rc = child.wait(); note(f"server exited rc={rc}")
