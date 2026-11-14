"""Run one snippet as loom's _one_run builds it (preamble, mark, group, text, mark) through loom's make_html, and print TeX4ht's raw page body and loom's normalised page.

Usage: <loom venv python> repro_snippet.py QUILT   (PATH chooses the TeX)
"""

import re
import sys
from pathlib import Path

from loom.render.normalise import normalise
from loom.tex.tex4ht import make_html

q = Path(sys.argv[1])
doc = (q / "drafting/main-atomic.tex").read_text()
preamble = doc.split("\\begin{document}")[0]
node = (q / "drafting/nodes/sh-000C.tex").read_text()
proof = node[node.index("\\begin{proof}") :].rstrip() + "\n"
lines = preamble.rstrip("\n").split("\n") + ["\\begin{document}"]
lines += ["\\loomsnippet{0}", "\\begingroup", *proof.split("\n"), "\\par\\endgroup", "\\loomsnippet{end}", "\\end{document}", ""]
page, log = make_html(q, "drafting", "loom-snippets", "\n".join(lines), envs=["theorem", "proof"])
body = page[page.index("<body") :] if page else "NO PAGE\n" + log[-2000:]
print("---- raw TeX4ht body ----")
print(re.sub(r"\n\s*\n", "\n", body)[:3000])
print("---- normalised ----")
print(normalise(page, {}).html[:3000] if page else "")
