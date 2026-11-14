import sys, time, threading, subprocess, json
quilt, port, eid, path, delay = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
def keep():
    t0 = time.time()
    out = subprocess.run(["python3", f"{sys.argv[0].rsplit('/',1)[0]}/api.py", quilt, port, "change-keep", json.dumps({"changes": [eid]})], capture_output=True, text=True).stdout
    print(f"keep answered after {time.time()-t0:.2f}s: {out.strip()[:200]}")
th = threading.Thread(target=keep); th.start()
time.sleep(delay)
with open(f"{quilt}/{path}", "a") as fh: fh.write("% PERSON'S EDIT SAVED DURING KEEP\n")
print(f"person saved at {delay}s")
th.join()
txt = open(f"{quilt}/{path}").read()
print("person's line survives:", "PERSON'S EDIT SAVED DURING KEEP" in txt)
