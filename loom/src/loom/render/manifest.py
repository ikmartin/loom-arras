"""Build `manifest.json` from a scan, the numbering, the fragments written, and the records (docs/specs/manifest.md).

Every section of the specification is produced here; the states vocabulary is fixed; text never appears in the manifest except titles, excerpts, and rendered annotation bodies.
"""

from __future__ import annotations

import re
from typing import Any

from loom.render.fragments import digest_macro_set, master_title, plain_text
from loom.render.threads import build_threads
from loom.scan.bib import citekey_slug
from loom.scan.digests import source_version
from loom.scan.directives import list_value
from loom.scan.hashing import child_marker, hash_text
from loom.scan.macros import to_mathjax
from loom.scan.model import Diagnostic
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult
from loom.tex.aux import AuxNumber
from loom.version import INTERFACE_VERSION, __version__

STATE_LABELS = {
    "labels": {
        "draft": {"label": "draft", "color": "neutral"},
        "accepted": {"label": "accepted", "color": "positive"},
        "stale": {"label": "stale", "color": "warning", "modifier": True},
        "incomplete": {"label": "incomplete", "color": "negative"},
    },
    "derived": {
        "proved": {"label": "proved", "color": "positive"},
        "settled": {"label": "settled", "color": "positive-strong"},
    },
}


def own_text(result: ScanResult, node: NodeRec) -> str:
    """The raw own text of a node with a child marker where each claimant was cut, the text every hash is taken over (book 5.13)."""
    src = result.files[node.file]
    pieces: list[str] = []
    kids = [result.nodes[k] for k in node.claimants]
    pos = node.start
    for c in sorted(kids, key=lambda x: x.start):
        if c.start > pos:
            pieces.append(src.text[pos : c.start])
        pieces.append(child_marker(c.key))
        pos = max(pos, c.end)
    if node.end > pos:
        pieces.append(src.text[pos : node.end])
    return "".join(pieces)


def key_hash(result: ScanResult, key: str) -> str:
    return hash_text(own_text(result, result.nodes[key]))


def _numbers(node: NodeRec, numbers: dict[str, dict[str, AuxNumber]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for master, table in numbers.items():
        if master not in node.reached_by:
            continue
        for lab in [node.id, *node.labels]:
            if lab and lab in table:
                entry: dict[str, Any] = {"number": table[lab].number}
                if table[lab].page is not None:
                    entry["page"] = table[lab].page
                out[master] = entry
                break
    return out


def _parent_of(result: ScanResult, node: NodeRec) -> dict[str, str]:
    out: dict[str, str] = {}
    if node.kind == "section":
        return {m: p for m, p in node.parent.items() if p}
    for master, exp in result.expansions.items():
        if master not in node.reached_by:
            continue
        off = exp.exp_offset(node.file, node.start)
        if off is None:
            continue
        best: NodeRec | None = None
        for s in result.nodes.values():
            if s.kind != "section" or master not in s.exp_ranges:
                continue
            a, b = s.exp_ranges[master]
            if a <= off < b and (best is None or (b - a) < (best.exp_ranges[master][1] - best.exp_ranges[master][0])):
                best = s
        if best is not None:
            out[master] = best.key
    return out


def _locator(node: NodeRec) -> str | None:
    if not node.title:
        return None
    m = re.search(r"\\cite\s*\[([^\]]*)\]", node.title)
    return m.group(1).strip() if m else None


def build_manifest(
    result: ScanResult,
    numbers: dict[str, dict[str, AuxNumber]],
    fragments: dict[str, str],
    diagnostics: list[Diagnostic],
    records: Any | None = None,
) -> dict[str, Any]:
    asm = result.assembly
    root_name = result.quilt.root.name
    dm = result.default_master
    corpus_label = (master_title(result, dm) if dm else None) or root_name
    manifest: dict[str, Any] = {
        "interface_version": INTERFACE_VERSION,
        "publisher": {"name": "loom", "version": __version__},
        "generated": _stamp(),
        "corpus": {"name": root_name, "root_label": corpus_label},
        "masters": [],
        "nodes": {},
        "keys": {},
        "regions": {},
        "edges": [],
        "inclusion": {},
        "states": STATE_LABELS,
        "annotations": {},
        "threads": build_threads(result.quilt.root),
        "diagnostics": [d.to_dict() for d in diagnostics],
        "tags": {},
        "taxa": {},
        "references": {},
        "macros": {"default": [], "sets": {}},
        "search": [],
    }
    for m in result.masters:
        closure = result.closures.get(m)
        entry: dict[str, Any] = {
            "path": m,
            "title": master_title(result, m) or m,
            "default": m == dm,
            "fragment": fragments.get(f"master:{m}", ""),
            "engine": (closure.engine if closure and closure.engine else result.quilt.config.engine),
        }
        pdf = result.quilt.root / "build" / _stem(m) / f"{_stem(m)}.pdf"
        aux_known = bool(numbers.get(m))
        if pdf.exists():
            entry["compiled"] = _iso(pdf.stat().st_mtime)
            entry["pdf"] = f"{_stem(m)}/{_stem(m)}.pdf"
        entry["numbering_known"] = aux_known
        manifest["masters"].append(entry)
    for key, n in asm.nodes.items():
        if n.kind not in ("environment", "section") and not (n.kind == "proof" and n.id):
            continue
        tags = list_value(n.directives.get("tags", ""))
        authors = list_value(n.directives.get("author", ""))
        entry = {
            "id": key,
            "kind": n.kind,
            "taxon": n.taxon or "",
            "style": n.style or ("plain" if n.kind == "environment" else None),
            "title": plain_text(n.title) if n.title else None,
            "aliases": list(n.aliases),
            "author": authors,
            "created": n.directives.get("created"),
            "tags": tags,
            "file": n.file,
            "src": [n.start, n.end],
            "fragment": fragments.get(key, ""),
            "numbers": _numbers(n, numbers),
            "reached_by": list(n.reached_by),
            "parent": _parent_of(result, n),
            "children": [c for c in n.claimants if asm.nodes[c].kind in ("environment", "section") or asm.nodes[c].id],
            "proofs": list(n.proofs),
            "external": n.external,
            "digest": n.digest,
            "incomplete": list(n.incomplete),
            "state": "draft",
            "derived": {"proved": False, "settled": False},
        }
        if n.external:
            entry["locator"] = _locator(n)
        manifest["nodes"][key] = entry
        for tag in tags:
            manifest["tags"].setdefault(tag, []).append(key)
        if n.kind == "environment" or n.kind == "proof":
            manifest["keys"][key] = _key_entry(result, n)
        if n.kind == "environment":
            for pk in n.proofs:
                if pk not in manifest["keys"]:
                    manifest["keys"][pk] = _key_entry(result, asm.nodes[pk])
    for qkey, r in asm.regions.items():
        container = asm.nodes.get(r.container)
        entry = {
            "key": qkey,
            "container": r.container,
            "in": r.where,
            "label": r.label,
            "numbers": {},
            "src": [r.offset, r.offset],
        }
        if container is not None:
            for master, table in numbers.items():
                if master in container.reached_by and r.label in table:
                    entry["numbers"][master] = {"number": table[r.label].number}
        manifest["regions"][qkey] = entry
    for e in result.edges.edges:
        manifest["edges"].append(
            {"from": e.src, "to": e.to, "kind": e.kind, "via": e.via, "src": {"file": e.file, "line": e.line}}
        )
    for m in result.masters:
        manifest["inclusion"][m] = _inclusion_tree(result, m)
    for taxon_name, group in _taxa(result).items():
        manifest["taxa"][taxon_name] = group
    cited_by: dict[str, list[str]] = {}
    for c in result.edges.cites:
        cited_by.setdefault(c.citekey, []).append(c.src)
    digests = {ck: f for f, ck in asm.digest_files.items()}
    for ck in sorted(set(result.bib) | set(digests)):
        bib = result.bib.get(ck)
        fields = {
            k: v
            for k, v in (bib.fields.items() if bib else [])
            if k in ("author", "title", "year", "eprint", "version", "doi", "journal")
        }
        if "year" in fields and fields["year"].isdigit():
            fields["year"] = int(fields["year"])  # type: ignore[assignment]
        digest_entry = None
        version_mismatch = False
        if ck in digests:
            f = digests[ck]
            ds = {d.key: d.value for d in asm.directives.get(f, []) if d.form == "kv"}
            nodes = [k for k, n in asm.nodes.items() if n.file == f and n.kind == "environment"]
            digest_entry = {
                "file": f,
                "fragment": fragments.get(f"digest:{f}", ""),
                "source": ds.get("source", ""),
                "method": ds.get("method", ""),
                "nodes": nodes,
            }
            sv = source_version(ds.get("source", ""))
            if bib and bib.version and sv and bib.version != sv:
                version_mismatch = True
            manifest["macros"]["sets"][ck] = digest_macro_set(result, f)
        manifest["references"][ck] = {
            "citekey": ck,
            "slug": citekey_slug(ck),
            "bib": fields,
            "digest": digest_entry,
            "version_mismatch": version_mismatch,
            "cited_by": sorted(set(cited_by.get(ck, []))),
        }
    closure = result.closures.get(dm) if dm else None
    mathjax_macros = {
        k: v
        for k, v in (closure.macros.items() if closure else [])
        if v.kind != "let" and k not in ("uses", "incomplete", "nest")
    }
    manifest["macros"]["default"] = to_mathjax(mathjax_macros)
    for key, entry in manifest["nodes"].items():
        manifest["search"].append(
            {
                "key": key,
                "title": entry["title"] or key,
                "taxon": entry["taxon"],
                "kind": entry["kind"],
                "aliases": entry["aliases"],
                "tags": entry["tags"],
                "excerpt": _excerpt(result, asm.nodes[key]),
            }
        )
    for m in manifest["masters"]:
        manifest["search"].append({"key": m["path"], "title": m["title"], "kind": "master", "aliases": [], "tags": []})
    for tid, t in manifest["threads"].items():
        manifest["search"].append({"key": tid, "title": t["title"], "kind": "thread", "aliases": [], "tags": []})
    return manifest


def _key_entry(result: ScanResult, n: NodeRec) -> dict[str, Any]:
    assert result.graph is not None
    return {
        "key": n.key,
        "node": n.of if n.kind == "proof" and n.of else n.key,
        "kind": "proof" if n.kind == "proof" else "statement",
        **({"ordinal": n.ordinal} if n.kind == "proof" else {}),
        "file": n.file,
        "src": [n.start, n.end],
        "hash": key_hash(result, n.key),
        "incomplete": list(n.incomplete),
        "state": "incomplete" if n.incomplete else "draft",
        "reviews": {"latest_current": None, "latest_any": None, "open": {}, "detached": 0},
        "uses": result.graph.direct(n.key),
        "closure": result.graph.closure(n.key),
        "previous_key_match": None,
    }


def _taxa(result: ScanResult) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for n in result.nodes.values():
        if n.kind != "environment" or not n.taxon:
            continue
        entry = out.setdefault(
            n.taxon,
            {"style": n.style or "plain", "slug": re.sub(r"[^a-z0-9]+", "-", n.taxon.lower()).strip("-"), "count": 0},
        )
        entry["count"] += 1
    return out


def _inclusion_tree(result: ScanResult, master: str) -> dict[str, Any]:
    asm = result.assembly
    exp = result.expansions[master]
    sites = {(inc.parent, inc.site_start): inc for inc in exp.inclusions if inc.child and inc.child in asm.nodes}

    def children_of(container: NodeRec, shift: int) -> list[dict[str, Any]]:
        src = result.files[container.file]
        events: list[tuple[int, str, Any]] = []
        for ck in container.claimants:
            events.append((asm.nodes[ck].start, "claimant", ck))
        for (parent, off), inc in sites.items():
            if parent == container.file and any(a <= off < b for a, b in container.own):
                events.append((off, "include", inc))
        events.sort(key=lambda e: e[0])
        out: list[dict[str, Any]] = []
        for _, kind, payload in events:
            if kind == "claimant":
                c = asm.nodes[payload]
                if c.kind == "proof" and not c.id:
                    continue
                via = "section" if c.kind == "section" else "nested-env"
                out.append({"key": c.key, "via": via, "shift": shift, "children": children_of(c, shift)})
            else:
                inc = payload
                child = asm.nodes[inc.child]
                entry = {
                    "key": inc.child,
                    "via": inc.kind,
                    "file": inc.child,
                    "shift": inc.shift,
                    "children": children_of(child, inc.shift),
                }
                out.append(entry)
        _ = src
        return out

    return {"key": master, "children": children_of(asm.nodes[master], 0)}


def _excerpt(result: ScanResult, n: NodeRec, limit: int = 160) -> str:
    src = result.files[n.file]
    text = "".join(src.clean[a:b] for a, b in n.own)
    text = re.sub(r"\\begin\{[^}]*\}(\[[^\]]*\])?|\\end\{[^}]*\}|\\label\{[^}]*\}|\\uses\{[^}]*\}|%[^\n]*", " ", text)
    text = re.sub(r"\\(section|subsection|subsubsection|paragraph)\*?\{[^}]*\}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _stem(path: str) -> str:
    return path.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def _stamp() -> str:
    from loom.clock import stamp

    return stamp()


def _iso(mtime: float) -> str:
    import os
    from datetime import UTC, datetime

    if os.environ.get("LOOM_FIXED_TIME"):
        return _stamp()
    return datetime.fromtimestamp(mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
