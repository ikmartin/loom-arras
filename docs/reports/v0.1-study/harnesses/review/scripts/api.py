"""usage: python3 api.py QUILT PORT ENDPOINT 'JSON'  -- posts like the viewer does; prints the answer."""
import json, sys, urllib.request
quilt, port, endpoint, body = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "{}"
token = json.load(open(f"{quilt}/.loom/serve.json")).get("token", "")
req = urllib.request.Request(f"http://127.0.0.1:{port}/_api/{endpoint}", data=body.encode(), method="POST", headers={"Content-Type": "application/json", "X-Loom-Token": token, "Origin": f"http://127.0.0.1:{port}"})
try:
    with urllib.request.urlopen(req, timeout=600) as r:
        print(r.status, r.read().decode()[:3000])
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode()[:3000])
