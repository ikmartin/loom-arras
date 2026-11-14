"""Fraction of differing pixels between two PNGs of equal size, and the bounding box of the difference."""
import sys
from PIL import Image, ImageChops
a = Image.open(sys.argv[1]).convert("RGB"); b = Image.open(sys.argv[2]).convert("RGB")
if a.size != b.size: print("sizes differ", a.size, b.size); sys.exit()
d = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > 24 else 0)
n = sum(1 for v in d.getdata() if v)
print(f"{sys.argv[1].split('/')[-1]} vs {sys.argv[2].split('/')[-1]}: {n} of {a.size[0]*a.size[1]} pixels differ ({100*n/(a.size[0]*a.size[1]):.2f}%), box {d.getbbox()}")
if len(sys.argv) > 3 and d.getbbox():
    Image.composite(Image.new("RGB", a.size, (255, 0, 0)), b, d).save(sys.argv[3])
