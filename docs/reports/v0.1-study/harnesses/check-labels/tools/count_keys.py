"""Count key kinds in each scratch quilt as scanned today: statements, proofs, sections, equation labels; by id / ordinary label / none; and how many keys are named by place."""

import re
import sys
from collections import Counter
from pathlib import Path

from loom.scan.labels import is_id_shaped
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

EQ_ENVS = ("equation", "align", "gather", "multline", "eqnarray", "flalign", "alignat")


def count(root: Path) -> dict:
    result = scan(load_quilt(root))
    slugs = result.assembly.citeslugs
    c = Counter()
    for key, n in result.nodes.items():
        if n.external or n.file.startswith(".loom"):
            continue
        if n.kind == "environment":
            first = n.labels[0] if n.labels else None
            kind = "id" if n.id else ("label" if first else "none")
            c[f"stmt_{kind}"] += 1
            c["place_keyed"] += 0 if n.id else 1
        elif n.kind == "proof":
            if n.id:
                c["proof_id"] += 1
            elif n.of is None:
                c["proof_unattached_label" if n.labels else "proof_unattached_none"] += 1
                c["place_keyed"] += 0 if n.labels else 1
                c["label_keyed_now"] += 1 if n.labels else 0
            else:
                st = result.nodes.get(n.of)
                c["proof_of_id" if st is not None and st.id else "proof_of_place"] += 1
                c["place_keyed"] += 0 if (st is not None and st.id) else 1
        elif n.kind == "section":
            first = n.labels[0] if n.labels else None
            kind = "id" if n.id else ("label" if first else "none")
            c[f"sec_{kind}"] += 1
            c["place_keyed"] += 1 if kind == "none" else 0
            c["label_keyed_now"] += 1 if kind == "label" else 0
    for r in result.assembly.regions.values():
        if r.file.startswith(".loom"):
            continue
        c["region_labels"] += 1
        cont = result.nodes.get(r.container)
        if cont is not None and not cont.id and "#" in cont.key:
            c["region_in_place_keyed"] += 1
    # equations in the source, labelled or not
    for path, src in result.files.items():
        if path.startswith(".loom") or src.ignored:
            continue
        for m in re.finditer(r"\\begin\{(" + "|".join(EQ_ENVS) + r")(\*?)\}(.*?)\\end\{\1\2\}", src.clean, re.S):
            c["eq_env"] += 1
            if "\\label" in m.group(3):
                c["eq_env_labelled"] += 1
    dup = [d for d in result.diagnostics + result.lint if d.code == "loom:duplicate-label"]
    c["dup_label_diags"] = len(dup)
    total = sum(c[k] for k in ("stmt_id", "stmt_label", "stmt_none", "proof_id", "proof_of_id", "proof_of_place", "proof_unattached_label", "proof_unattached_none", "sec_id", "sec_label", "sec_none"))
    c["pieces"] = total
    return dict(c)


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(Path(arg).name, count(Path(arg)))
