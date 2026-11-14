"""Facts about labels in real papers that bear on label keys: restatements, place-shaped labels, a statement's first label being an equation's, duplicate labels."""

import difflib
import re
import sys
from collections import Counter
from pathlib import Path

from loom.records.store import Records
from loom.render.manifest import own_text
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

PLACE = re.compile(r"^[A-Za-z@*]+:[0-9]+$")


def words(t):
    return re.sub(r"% !LOOM child: \S+", "", t).split()


def main(root: Path) -> None:
    r = scan(load_quilt(root))
    c = Counter()
    stmts = [n for n in r.nodes.values() if n.kind == "environment" and not n.external and not n.file.startswith(".loom")]
    theorem_names = set(r.taxa)
    for n in stmts:
        if n.labels:
            src = r.files[n.file].clean
            body = src[n.start : n.end]
            head = re.match(r"\\begin\{[^}]*\}\s*(\[[^\]]*\])?\s*\\label", body)
            first_off = n.label_offsets.get(n.labels[0], n.start) - n.start
            # first label sits inside a math environment of the body
            inner = body[:first_off]
            if re.search(r"\\begin\{(equation|align|gather|multline|eqnarray)\*?\}", inner) and not head:
                c["first_label_is_equation"] += 1
            if PLACE.match(n.labels[0]) and n.labels[0].split(":")[0] in theorem_names | {"section", "subsection", "proof"}:
                c["place_shaped_label"] += 1
    # restatements: statements with another statement reading alike
    texts = {n.key: words(own_text(r, n)) for n in stmts}
    keys = list(texts)
    twins = set()
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            m = difflib.SequenceMatcher(None, texts[a], texts[b], autojunk=False)
            if m.real_quick_ratio() >= 0.6 and m.quick_ratio() >= 0.6 and m.ratio() >= 0.6:
                twins |= {a, b}
    c["statements"] = len(stmts)
    c["statements_with_near_twin"] = len(twins)
    c["dup_label_diags"] = sum(1 for d in r.assembly.diagnostics if d.code == "loom:duplicate-label")
    # files
    c["files"] = len([f for f in r.files if not f.startswith(".loom")])
    print(root.name, dict(c))


if __name__ == "__main__":
    for a in sys.argv[1:]:
        main(Path(a))
