"""Run a command in a pty, answer each prompt with the given answers (default: Enter), print the transcript and timing."""
import os, pty, sys, time, select, re
answers = sys.argv[1].split("|") if sys.argv[1] else []
cmd = sys.argv[2:]
t0 = time.time()
pid, fd = pty.fork()
if pid == 0:
    os.execvp(cmd[0], cmd)
buf = b""; log = b""; n = 0
while True:
    r, _, _ = select.select([fd], [], [], 3.0)
    if r:
        try:
            data = os.read(fd, 4096)
        except OSError:
            break
        if not data:
            break
        buf += data; log += data
        continue
    # idle 3 s: assume a prompt waits
    try:
        wpid, status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        break
    if wpid:
        break
    ans = answers[n] if n < len(answers) else ""
    n += 1
    log += f"<<ANSWER {ans!r}>>".encode()
    os.write(fd, (ans + "\n").encode())
    if n > 12:
        os.kill(pid, 9); break
try:
    _, status = os.waitpid(pid, 0)
except ChildProcessError:
    status = 0
print(log.decode(errors="replace").replace("\r", ""))
print(f"[{time.time()-t0:.1f}s, {n} answers, status {status}]")
