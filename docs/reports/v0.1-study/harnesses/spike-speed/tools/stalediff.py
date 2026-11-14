"""Compare two stale.py reports step by step: which published files differ, and how the manifests differ.

Usage: python stalediff.py BASE.json MOD.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def walk(a, b, path="", out=None, limit=12):  # type: ignore[no-untyped-def]
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}/{k}: {'missing in base' if k not in a else 'missing in mod'}")
            else:
                walk(a[k], b[k], f"{path}/{k}", out, limit)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", out, limit)
    elif a != b:
        out.append(f"{path}: {str(a)[:80]!r} -> {str(b)[:80]!r}")
    return out


def main() -> None:
    A, B = json.loads(Path(sys.argv[1]).read_text()), json.loads(Path(sys.argv[2]).read_text())
    for step in A["steps"]:
        if step not in B["steps"]:
            continue
        for phase in ("first", "second"):
            fa, fb = A["steps"][step][phase]["files"], B["steps"][step][phase]["files"]
            diff = sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))
            ta, tb = A["steps"][step][phase], B["steps"][step][phase]
            print(f"{step} {phase}: base {ta['s']}s r={ta['rendered']} tex={ta['make4ht']} | mod {tb['s']}s r={tb['rendered']} tex={tb['make4ht']} deferred={tb.get('deferred', '-')} | {len(diff)} files differ")
            for k in diff[:15]:
                print(f"    {k}  base={fa.get(k)} mod={fb.get(k)}")
            if "manifest.json" in diff:
                ma = json.loads((Path(sys.argv[1] + '.d') / f"{step}-{phase}-manifest.json").read_text())
                mb = json.loads((Path(sys.argv[2] + '.d') / f"{step}-{phase}-manifest.json").read_text())
                for line in walk(ma, mb):
                    print("      manifest", line)


if __name__ == "__main__":
    main()
