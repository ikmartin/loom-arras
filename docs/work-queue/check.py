#!/usr/bin/env python3
"""Check the work queue and the book's freedom from unfinished business.

Run during the end-of-round walk, alongside `docs/deviations.md`. Exits 0 when everything holds, 1 with one line per fault otherwise. The workspace repository has no CI workflows (book 14.4); this is meant to be run by hand or by whatever walks the round.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CAP = 20
HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
ROW = re.compile(r"^\|\s*\[?(WQ-\d+)\]?[^|]*\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$")
LINK = re.compile(r"\]\(([^)#]+)(?:#[^)]*)?\)")
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
RETIRED = re.compile(r"^\|\s*(WQ-\d+)\s*\|")


def main() -> int:
    faults: list[str] = []
    readme = (HERE / "README.md").read_text(encoding="utf-8")
    closed = (HERE / "closed.md").read_text(encoding="utf-8")

    # 1. every active row has an id, a trigger and a file; every item file has a row
    active: dict[str, str] = {}
    for line in readme.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        wq, _repo, _item, trigger = m.group(1), m.group(2), m.group(3), m.group(4)
        active[wq] = trigger.strip()
        if not trigger.strip():
            faults.append(f"{wq}: the trigger column is empty; an item without an observable trigger is a wish")
    for wq, trigger in active.items():
        if not list(HERE.glob(f"{wq}-*.md")):
            faults.append(f"{wq}: listed in README.md with no {wq}-*.md file")
    for path in sorted(HERE.glob("WQ-*.md")):
        wq = path.name.split("-")[0] + "-" + path.name.split("-")[1]
        if wq not in active:
            faults.append(f"{path.name}: an item file with no row in README.md")

    # 2. ids unique across active and closed, and never reused
    retired = {m.group(1) for line in closed.splitlines() if (m := RETIRED.match(line))}
    for wq in sorted(active.keys() & retired):
        faults.append(f"{wq}: active and closed at once; ids are never reused")

    # 3. the cap
    if len(active) > CAP:
        faults.append(f"{len(active)} active items, cap is {CAP}; promote, merge or drop one before adding another")

    # 4. every relative pointer in the queue resolves. Anything carrying a URI scheme is not a path:
    # http, mailto, and loom's own `loom:arxiv:…` reference links, which an item may quote as an example.
    for path in sorted(HERE.glob("*.md")):
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if SCHEME.match(target):
                continue
            if not (path.parent / target).exists():
                faults.append(f"{path.name}: link to {target} does not resolve")

    # 5. the book carries no unfinished business.
    # The marker form is bold -- **[deferred]** -- so naming a withdrawn marker in prose or in a
    # decision record, where it is written `[deferred]`, is not a fault. DR-107 does exactly that.
    for tree in (DOCS / "book", DOCS / "specs"):
        for path in sorted(tree.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            for marker in ("deferred", "assumed"):
                n = len(re.findall(rf"\*\*\[{marker}\]\*\*", text))
                if n:
                    rel = path.relative_to(DOCS.parent)
                    faults.append(
                        f"{rel}: {n} occurrence(s) of the [{marker}] marker. The book describes what is "
                        f"implemented; unfinished work belongs in the work queue with a trigger (DR-107)."
                    )
            if re.search(r"^#+\s*Open questions\s*$", text, re.M):
                faults.append(f"{path.relative_to(DOCS.parent)}: an 'Open questions' section; these moved to the work queue")

    for fault in faults:
        print(fault, file=sys.stderr)
    if faults:
        print(f"\n{len(faults)} fault(s)", file=sys.stderr)
        return 1
    print(f"work queue ok: {len(active)} active (cap {CAP}), {len(retired)} closed; book and specs carry no unfinished business")
    return 0


if __name__ == "__main__":
    sys.exit(main())
