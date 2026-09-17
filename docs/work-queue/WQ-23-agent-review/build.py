"""Build page.html from template.html and demo-data.json.

The data is the two runs under runs/ plus fragments rendered by arras from the demo quilt, gathered once by hand; rebuild the page after editing the template, then publish page.html as an artifact.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "demo-data.json").read_text(encoding="utf-8"))
macros = {m["name"]: (m["body"] if not m["args"] else [m["body"], m["args"]]) for m in data["macros"]["default"]}
page = (HERE / "template.html").read_text(encoding="utf-8")
page = page.replace("__DATA__", json.dumps(data).replace("</", "<\\/")).replace("__MACROS__", json.dumps(macros))
(HERE / "page.html").write_text(page, encoding="utf-8")
print(f"page.html {len(page) // 1024} KB")
