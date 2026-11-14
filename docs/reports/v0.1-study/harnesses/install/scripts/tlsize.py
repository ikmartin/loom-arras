import sys
db, custom = sys.argv[1], sys.argv[2]
extra = sys.argv[3].split(",")
arch = "universal-darwin"
pk = {}
cur = None
for line in open(db, encoding="utf-8", errors="replace"):
    line = line.rstrip("\n")
    if line.startswith("name "):
        cur = {"name": line[5:], "dep": [], "cs": 0, "runsize": 0, "binsize": 0}
        pk[cur["name"]] = cur
    elif cur is None:
        continue
    elif line.startswith("depend "):
        cur["dep"].append(line[7:])
    elif line.startswith("containersize "):
        cur["cs"] = int(line.split()[1])
    elif line.startswith("runfiles size="):
        cur["runsize"] = int(line.split("=")[1])
    elif line.startswith("binfiles ") and "size=" in line:
        cur["binsize"] = int(line.split("size=")[1])
    elif line.startswith("release ") and cur["name"] == "00texlive.config":
        pass
cfg = pk.get("00texlive.config", {})
def closure(names):
    seen = set()
    stack = list(names)
    while stack:
        n = stack.pop()
        n = n.replace("ARCH", arch)
        if n.endswith(".ARCH"): n = n[:-5] + "." + arch
        if n in seen or n not in pk: continue
        seen.add(n)
        for d in pk[n]["dep"]:
            stack.append(d.replace("ARCH", arch))
        a = n + "." + arch
        if a in pk: stack.append(a)
    return seen
def total(s):
    return sum(pk[n]["cs"] for n in s), sum(pk[n]["runsize"] + pk[n]["binsize"] for n in s)
base = ["scheme-infraonly", "latex-bin"]
c1 = [l.strip() for l in open(custom) if l.strip()]
s1 = closure(base + c1)
s2 = closure(base + c1 + extra)
for label, s in (("TinyTeX-1 approx", s1), ("plus loom extras", s2)):
    cs, sz = total(s)
    print(f"{label}: {len(s)} pkgs, download {cs/1e6:.0f} MB, runsize units {sz} (~{sz*4096/1e6:.0f} MB if 4k blocks)")
missing = [e for e in extra if e not in pk]
print("unknown names:", missing)
for e in ("make4ht", "tex4ht", "luaxml", "dvisvgm", "tex4ht."+arch, "dvisvgm."+arch):
    if e in pk: print(e, "dl", pk[e]["cs"]//1000, "kB")
