"""Same edit sequence, one process, as `loom serve` would build it; after each step a fingerprint of every published file.

Usage: python stale.py QUILT OUTJSON [--steps s1,s2,...]
Each step: edit, build (previews made from cache only where the code supports it, as a save's publication), fingerprint `first`; build again from the same scan with TeX for everything, fingerprint `second`.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import probe  # noqa: E402

DRAFT = "drafting/draft5.tex"
AUX = ".loom/build/drafting/draft5/draft5.aux"
WORD_A, WORD_B = "has fibered products, for which", "has fibered qzspike products, for which"
ANN_A, ANN_B = r"The torus \(T\) acts trivially on \(\mathfrak M\)", r"The torus \(T\) acts with no effect on \(\mathfrak M\)"
CITED = "prop:properties-of-the-fixed-stack"


def fingerprint(root: Path) -> dict[str, str]:
    b = root / ".loom/build"
    out = {}
    for p in sorted(b.rglob("*")):
        rel = p.relative_to(b).as_posix()
        if rel.startswith(("cache/", "drafting/", "examples", "draft5/", "s-20")) or not p.is_file() or rel == "compiles.json":
            continue
        if not rel.startswith(("fragments/", "source/", "spans/", "transcripts/", "diffs/", "files/")) and rel != "manifest.json":
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return out


def edit(root: Path, rel: str, a: str, b: str) -> None:
    p = root / rel
    t = p.read_text(encoding="utf-8")
    assert a in t, (rel, a)
    p.write_text(t.replace(a, b, 1), encoding="utf-8")


def main() -> None:
    q = Path(sys.argv[1]).resolve()
    outp = Path(sys.argv[2])
    probe.cache_git()
    import loom.render.build as B
    from loom.scan.quilt import load_quilt

    deferrable = "previews_tex" in inspect.signature(B.build).parameters
    aux = q / AUX
    aux_orig = aux.read_text(encoding="utf-8")
    pre_orig = (q / DRAFT).read_text(encoding="utf-8")
    snaps = Path(str(outp) + ".d")
    snaps.mkdir(parents=True, exist_ok=True)

    def page_shift() -> None:
        t = aux.read_text(encoding="utf-8")
        t = re.sub(r"^(\\newlabel\{[^\n]*?\}\{\{(?:[^{}\n]|\{[^{}\n]*\})*\})\{(\d+)\}", lambda m: f"{m[1]}{{{int(m[2]) + 1}}}", t, flags=re.M)
        aux.write_text(t, encoding="utf-8")

    def renumber() -> None:
        t = aux.read_text(encoding="utf-8")
        old = "\\newlabel{%s}{{2.7}" % CITED
        assert old in t
        aux.write_text(t.replace(old, "\\newlabel{%s}{{2.77}" % CITED), encoding="utf-8")

    def preamble() -> None:
        edit(q, DRAFT, "\\begin{document}", "\\newcommand{\\spikemacro}{x}\n\\begin{document}")

    def restore() -> None:
        aux.write_text(aux_orig, encoding="utf-8")
        (q / DRAFT).write_text(pre_orig, encoding="utf-8")

    steps = {
        "s0-warm": lambda: None,
        "s1-word": lambda: edit(q, DRAFT, WORD_A, WORD_B),
        "s2-annotation-words-gone": lambda: edit(q, DRAFT, ANN_A, ANN_B),
        "s3-annotation-words-back": lambda: edit(q, DRAFT, ANN_B, ANN_A),
        "s4-page-shift": page_shift,
        "s5-renumber-cited": renumber,
        "s6-preamble": preamble,
        "s7-restore": restore,
    }
    if "--steps" in sys.argv:
        want = sys.argv[sys.argv.index("--steps") + 1].split(",")
        steps = {k: v for k, v in steps.items() if k in want}
    report = {"quilt": str(q), "code": B.__file__, "deferrable": deferrable, "steps": {}}
    try:
        for name, act in steps.items():
            act()
            p0 = len(probe.PROCS)
            t = time.perf_counter()
            kw = {"previews_tex": False} if deferrable else {}
            r1 = B.build(load_quilt(q), **kw)
            t1 = time.perf_counter() - t
            f1 = fingerprint(q)
            (snaps / f"{name}-first-manifest.json").write_bytes((q / ".loom/build/manifest.json").read_bytes())
            tex1 = sum(1 for p in probe.PROCS[p0:] if p["exe"] == "make4ht")
            p1 = len(probe.PROCS)
            t = time.perf_counter()
            r2 = B.build(load_quilt(q), reuse=r1.result)
            t2 = time.perf_counter() - t
            f2 = fingerprint(q)
            (snaps / f"{name}-second-manifest.json").write_bytes((q / ".loom/build/manifest.json").read_bytes())
            for rel in ("fragments/nodes/rl-000G.html", "fragments/nodes/rl-001P.html"):
                if (q / ".loom/build" / rel).is_file():
                    shutil.copy(q / ".loom/build" / rel, snaps / f"{name}-{Path(rel).name}")
            tex2 = sum(1 for p in probe.PROCS[p1:] if p["exe"] == "make4ht")
            report["steps"][name] = {
                "first": {"s": round(t1, 2), "rendered": len(r1.rendered), "make4ht": tex1, "deferred": getattr(r1, "deferred", 0), "files": f1},
                "second": {"s": round(t2, 2), "rendered": len(r2.rendered), "make4ht": tex2, "files": f2},
                "load": os.getloadavg()[0],
            }
            print(name, {k: (v["s"], v["rendered"], v["make4ht"]) for k, v in report["steps"][name].items() if isinstance(v, dict)}, f"load {os.getloadavg()[0]:.1f}", flush=True)
            outp.write_text(json.dumps(report))
    finally:
        restore()


if __name__ == "__main__":
    main()
