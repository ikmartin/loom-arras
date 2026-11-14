import re,sys
tot=0;n=0
for f in sys.argv[1:]:
    for m in re.finditer(r"(?:install|update): (\S+) \[(\d+)k\]", open(f).read()):
        tot+=int(m.group(2)); n+=1
print(f"{n} containers, {tot/1024:.1f} MiB")
