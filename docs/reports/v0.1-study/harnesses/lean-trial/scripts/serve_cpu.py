"""Start `loom serve --no-compile` on a port, let it settle, then measure its CPU seconds over a window; stop it. Usage: serve_cpu.py QUILT PORT LABEL SETTLE WINDOW"""
import os, subprocess, sys, time, socket, signal
quilt, port, label, settle, window = sys.argv[1], int(sys.argv[2]), sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
loom = "/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin/loom"
log = open(os.path.join(os.path.dirname(quilt), "logs", f"serve-{label}.log"), "w")
t0 = time.time()
p = subprocess.Popen([loom, "serve", "--no-compile", "--port", str(port)], cwd=quilt, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
def cpu():
    out = subprocess.run(["ps", "-o", "time=", "-g", str(os.getpgid(p.pid))], capture_output=True, text=True).stdout.split()
    total = 0.0
    for t in out:
        parts = t.split(":"); secs = float(parts[-1]); mins = int(parts[-2]) if len(parts) > 1 else 0; hrs = int(parts[-3]) if len(parts) > 2 else 0
        total += hrs * 3600 + mins * 60 + secs
    return total
ready = None
while time.time() - t0 < 120:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.5).close(); ready = time.time() - t0; break
    except OSError:
        time.sleep(0.25)
time.sleep(settle)
c1, w1 = cpu(), time.time()
time.sleep(window)
c2, w2 = cpu(), time.time()
rss = subprocess.run(["ps", "-o", "rss=", "-p", str(p.pid)], capture_output=True, text=True).stdout.strip()
os.killpg(os.getpgid(p.pid), signal.SIGINT)
try: p.wait(timeout=15)
except subprocess.TimeoutExpired: os.killpg(os.getpgid(p.pid), signal.SIGKILL); p.wait()
print(f"{label}: ready_after={ready:.1f}s cpu_at_settle={c1:.1f}s window={w2-w1:.0f}s cpu_in_window={c2-c1:.1f}s => {100*(c2-c1)/(w2-w1):.1f}% of one core; rss_kb={rss}")
