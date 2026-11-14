"""Words (outside tags, inside math stripped of spaces) that one fragment has more often than the other."""
import re, sys
from collections import Counter
from html import unescape
def bag(p):
    t = open(p, errors="replace").read()
    t = re.sub(r"<img[^>]*>", " ", t)
    t = re.sub(r"\\\((.*?)\\\)", lambda m: " MATH:" + re.sub(r"\s+", "", m.group(1)) + " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return Counter(unescape(t).split())
a, b = bag(sys.argv[1]), bag(sys.argv[2])
print("only/more in A:", sum((a - b).values()), list((a - b).items())[:25])
print("only/more in B:", sum((b - a).values()), list((b - a).items())[:25])
