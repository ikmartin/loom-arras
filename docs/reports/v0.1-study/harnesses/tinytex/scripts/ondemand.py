"""Prototype of loom's on-demand package install: compile a document with loom (PDF + HTML), read the missing files from what the tools said, find each file's TeX Live package with tlmgr, install, retry.

Usage: python3 -I ondemand.py QUILT DOC LABEL [MAXROUNDS]   (PATH and XDG_CONFIG_HOME come from the caller's environment)
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

LOOM = "/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin/loom"
LOGS = Path("/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/tinytex/logs")

PATTERNS = [
    (re.compile(r"! LaTeX Error: File `([^']+)' not found"), None),
    (re.compile(r"! I can't find file `([^']+)'"), None),
    (re.compile(r"! Font \S+?=(\S+?)(?: at [\d.]+pt)? not loadable: Metric \(TFM\) file not found"), ".tfm"),
    (re.compile(r"kpathsea: Running mktextfm (\S+)"), ".tfm"),
    (re.compile(r"Latexmk: Missing input file '([^']+)'"), None),
    (re.compile(r"! Package \w+ Error: File `([^']+)' not found"), None),
    (re.compile(r"--- error --- Can't find/open file `([^']+)'"), None),
    (re.compile(r"! LuaTeX error .*?module '([^']+)' not found"), ".lua"),
    (re.compile(r"I looked for files named (tikzlibrary\S+?\.code\.tex)"), None),
    (re.compile(r"Package \w+ Error: Package `([^']+)' not installed"), ".sty"),
    (re.compile(r"!pdfTeX error: \S+ \(file (\S+)\): Font \S+ at \d+ not found"), ".tfm"),
]


def missing(text: str) -> list[str]:
    names = []
    for pat, ext in PATTERNS:
        for m in pat.finditer(text):
            n = m.group(1).strip()
            if ext and not n.endswith(ext):
                n += ext
            if n not in names:
                names.append(n)
    return names


def search(name: str) -> list[str]:
    base = name.rsplit("/", 1)[-1]
    tries = [base] if "." in base else [base + ".sty", base + ".tex", base + ".cls", base]
    for t in tries:
        out = subprocess.run(["tlmgr", "search", "--global", "--file", "/" + t], capture_output=True, text=True).stdout
        pkgs = []
        cur = None
        for line in out.splitlines():
            if line and not line.startswith("\t") and line.endswith(":") and not line.startswith("tlmgr"):
                cur = line[:-1]
            elif line.startswith("\t") and cur and line.strip().endswith("/" + t):
                if cur not in pkgs:
                    pkgs.append(cur)
        if pkgs:
            return pkgs
    return []


def main() -> None:
    quilt, doc, label = sys.argv[1], sys.argv[2], sys.argv[3]
    maxrounds = int(sys.argv[4]) if len(sys.argv) > 4 else 15
    rounds = []
    installed: list[str] = []
    stem = Path(doc).with_suffix("")
    t_all = time.monotonic()
    for r in range(1, maxrounds + 1):
        t0 = time.monotonic()
        p = subprocess.run([LOOM, "compile", doc, "--html", "--json"], cwd=quilt, capture_output=True, text=True)
        t_compile = time.monotonic() - t0
        (LOGS / f"{label}-r{r}.json").write_text(p.stdout + "\n--stderr--\n" + p.stderr)
        try:
            rep = json.loads(p.stdout)
        except json.JSONDecodeError:
            rep = {}
        log = Path(quilt) / ".loom/build" / f"{stem}" / f"{stem.name}.log"
        text = "\n".join(rep.get("errors", []) + rep.get("html", {}).get("errors", []))
        if log.is_file():
            text += "\n" + log.read_text(errors="replace")
        names = missing(text)
        row = {
            "round": r,
            "compile_s": round(t_compile, 1),
            "state": rep.get("state"),
            "html_made": rep.get("html", {}).get("made"),
            "html_said": rep.get("html", {}).get("said", "")[:200],
            "first_error": (rep.get("errors") or [""])[0][:200],
            "missing": names,
        }
        if not names:
            rounds.append(row)
            break
        t1 = time.monotonic()
        found = {n: search(n) for n in names}
        row["search_s"] = round(time.monotonic() - t1, 1)
        row["found"] = found
        pkgs = []
        for n, ps in found.items():
            if ps and not any(x in installed for x in ps):
                pkgs.append(ps[0])
        pkgs = [x for i, x in enumerate(pkgs) if x not in pkgs[:i]]
        row["install"] = pkgs
        if not pkgs:
            rounds.append(row)
            break
        t2 = time.monotonic()
        ip = subprocess.run(["tlmgr", "install", *pkgs], capture_output=True, text=True)
        row["install_s"] = round(time.monotonic() - t2, 1)
        row["install_exit"] = ip.returncode
        (LOGS / f"{label}-r{r}-tlmgr.txt").write_text(ip.stdout + ip.stderr)
        row["download_k"] = sum(int(k) for k in re.findall(r"install: \S+ \[(\d+)k\]", ip.stdout + ip.stderr))
        row["containers"] = len(re.findall(r"install: \S+ \[", ip.stdout + ip.stderr))
        installed += pkgs
        rounds.append(row)
        print(json.dumps(row), flush=True)
    summary = {"label": label, "rounds": rounds, "installed": installed, "total_s": round(time.monotonic() - t_all, 1)}
    (LOGS / f"{label}-summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(rounds[-1]))
    print("installed:", " ".join(installed), "total_s:", summary["total_s"])


main()
