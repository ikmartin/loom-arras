"""As repro_picture.py, but through loom's own _prepare and _pass, keeping make4ht's stdout and the output directory."""
import re, sys, shutil
from pathlib import Path
from loom.tex.tex4ht import _prepare, _pass
q = Path(sys.argv[1]); work = Path(sys.argv[2])
shutil.rmtree(work, ignore_errors=True); (work / "src").mkdir(parents=True)
doc = (q / "drafting/main-atomic.tex").read_text()
preamble = doc.split("\\begin{document}")[0]
display = "\\begin{equation*} \\xymatrix {F^{\\prime} \\ar[r]^{f^{\\prime}}\\ar[d] & G^{\\prime}\\ar[d]\\\\ F\\ar[r]^f& G.} \\end{equation*}"
lines = preamble.rstrip("\n").split("\n") + ["\\begin{document}", "\\loomsnippet{0}", "\\begingroup", display, "\\par\\endgroup", "\\loomsnippet{end}", "\\end{document}", ""]
shutil.copy(q / "drafting/loom.sty", work / "src/loom.sty")
_prepare(work / "src", work / "src", [], snippets=True, math="svg")
(work / "src/s.tex").write_text("\n".join(lines))
code, said = _pass(shutil.which("make4ht"), work / "src", "s.tex", work / "out", work / "home", "pdflatex", 300, math="svg")
print("exit", code); print("out:", sorted(p.name for p in (work / "out").glob("*")))
print("src:", sorted(p.name for p in (work / "src").glob("*")))
for ln in said.splitlines():
    if re.search(r"dvisvgm|svg|rror|warn|ghost|PostScript|\[", ln, re.I): print("  ", ln[:260])
