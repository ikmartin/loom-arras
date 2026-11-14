"""Draw one xymatrix display in loom's svg mode through loom's make_html and report what TeX4ht made and said.

Usage: <loom venv python> repro_picture.py QUILT OUTDIR   (PATH chooses the TeX)
"""

import re
import sys
from pathlib import Path

from loom.tex.tex4ht import make_html

q = Path(sys.argv[1])
out = Path(sys.argv[2])
doc = (q / "drafting/main-atomic.tex").read_text()
preamble = doc.split("\\begin{document}")[0]
display = "\\begin{equation*} \\xymatrix {F^{\\prime} \\ar[r]^{f^{\\prime}}\\ar[d] & G^{\\prime}\\ar[d]\\\\ F\\ar[r]^f& G.} \\end{equation*}"
lines = preamble.rstrip("\n").split("\n") + ["\\begin{document}", "\\loomsnippet{0}", "\\begingroup", display, "\\par\\endgroup", "\\loomsnippet{end}", "\\end{document}", ""]
page, log = make_html(q, "drafting", "loom-snippets", "\n".join(lines), math="svg", pictures=(out, "pics"))
print("page made:", page is not None)
if page:
    print(re.sub(r"\n\s*\n", "\n", page[page.index("<body") :])[:1200])
print("pictures:", sorted(p.name for p in out.glob("*")) if out.exists() else [])
print("---- log lines mentioning dvisvgm / error / ghostscript ----")
for ln in log.splitlines():
    if re.search(r"dvisvgm|rror|host|PostScript|libgs|^!|warn", ln, re.I):
        print("  ", ln[:240])
