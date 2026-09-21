"""Build `manifest.json` from a scan, the numbering, the fragments written, and the records (docs/specs/manifest.md).

Every section of the specification is produced here; the states vocabulary is fixed; text never appears in the manifest except titles, excerpts, and rendered annotation bodies.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loom.refs.identity import declared, identify, primary
from loom.refs.pages import STORAGE, storage_root
from loom.refs.resolve import load as load_candidates
from loom.render.fragments import digest_macro_set, master_title, plain_text
from loom.render.threads import build_threads
from loom.scan.digests import extracted_from, loaded_packages, published_as, source_version
from loom.scan.directives import list_value
from loom.scan.hashing import child_marker, hash_text
from loom.scan.macros import compatibility_macros, declared_alphabets, package_macros, to_mathjax
from loom.scan.model import Diagnostic
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult
from loom.tex.aux import AuxNumber
from loom.version import INTERFACE_VERSION, __version__

STATE_LABELS = {
    "labels": {
        "draft": {"label": "draft", "color": "neutral"},
        "proposed": {"label": "proposed", "color": "info"},
        "accepted": {"label": "accepted", "color": "positive"},
        "stale": {"label": "stale", "color": "warning", "modifier": True},
        "incomplete": {"label": "incomplete", "color": "negative"},
        "conflicted": {"label": "conflicted", "color": "negative"},
    },
    "derived": {
        "proved": {"label": "proved", "color": "positive"},
        "settled": {"label": "settled", "color": "positive-strong"},
    },
}


def _sessions(root: Path) -> list[dict[str, Any]]:
    """Every session the index leaves standing, with what the viewer's selector shows: the title, the state, and the round it is on."""
    from loom.sessions import active, sessions

    here = active(root)
    return [
        {
            "id": s.id,
            "title": s.title,
            "state": s.state,
            "created": s.created,
            "opened": s.last_opened,
            "rounds": len(s.rounds),
            "active": s.id == here,
        }
        for s in sessions(root).values()
    ]


def _results_for(root: Path, citekey: str) -> dict[str, dict[str, Any]]:
    """The work's recorded results, as the viewer needs them (digest contract §9).

    `source_text` travels for every result read off a page, verified or not: it is what a link's two endpoints are compared by eye against (§7), and a verified transcription is exactly the case where that comparison is worth making. It does **not** travel for a mechanically extracted result, whose `source_text` is its own LaTeX and is already in the digest fragment -- carrying it would put the whole literature in the manifest twice.

    `statement` travels only for a proposal, because that is the one claim a person is being asked to make and the surface that must show both texts together (§5.3).
    """
    from loom.refs.proposals import PROPOSED, load_results, page_context
    from loom.refs.search import words_not_on_page

    out: dict[str, dict[str, Any]] = {}
    for rid, r in load_results(root, citekey).items():
        row: dict[str, Any] = {
            "state": r.state,
            "level": r.level,
            "class": r.cls,
            "page": r.anchor.page,
            "artifact": r.anchor.sha256[:12],
            "origin": r.origin,
        }
        if r.cls != "mechanical":
            row["source_text"] = r.source_text
        if r.anchor.kind == "tex" and r.cls != "mechanical":
            row["source_file"] = r.anchor.path
        if r.state == PROPOSED:
            row["statement"] = r.statement
            row["local"] = r.local
            row["taxon"] = r.taxon
            # what the rendering is judged against: the page around the quote, because an agent quotes only as much
            # as the anchor check needs, and a ten-line rendering beside one clause cannot be judged (§5.3)
            context, found = page_context(root, r)
            if found:
                row["page_text"] = context
            added = words_not_on_page(r.statement, r.source_text)
            if added:
                row["not_on_page"] = added
            if r.supersedes:
                row["supersedes"] = r.supersedes
        out[rid] = row
    return out


def _provided_by(result: ScanResult, file: str) -> list[str]:
    """The keys a file brings in when it is included: its outermost nodes, in order."""
    nodes = sorted(
        (n for n in result.nodes.values() if n.file == file and n.kind not in ("file", "master")),
        key=lambda n: n.start,
    )
    out: list[str] = []
    reach = -1
    for n in nodes:
        if n.start >= reach:
            out.append(n.key)
            reach = n.end
    return out


def _cuts(result: ScanResult, node: NodeRec) -> list[tuple[int, int, str]]:
    """(start, end, marker) for every child of `node` that its own text stands in for: a claimant cut out of the region, and an inclusion of a file whose nodes are children just the same."""
    cuts = [(result.nodes[k].start, result.nodes[k].end, child_marker(k)) for k in node.claimants]
    seen: set[int] = set()
    for expansion in result.expansions.values():
        for inc in expansion.inclusions:
            if inc.parent != node.file or inc.child is None or inc.site_start in seen:
                continue
            if not (node.start <= inc.site_start and inc.site_end <= node.end):
                continue
            if any(a <= inc.site_start < b for a, b, _ in cuts):
                continue  # inside a claimed child, which already stands for everything within it
            keys = _provided_by(result, inc.child)
            if keys:
                seen.add(inc.site_start)
                cuts.append((inc.site_start, inc.site_end, "".join(child_marker(k) for k in keys)))
    return sorted(cuts, key=lambda c: c[0])


def own_text(result: ScanResult, node: NodeRec) -> str:
    """The raw own text of a node with a child marker where each child was cut out or included, the text every hash is taken over (book 5.13).

    An inclusion line reads as the nodes the included file provides, so a node's hash is the same whether a child sits inline or in `nodes/<id>.tex`, and moving one there changes no state.
    """
    src = result.files[node.file]
    pieces: list[str] = []
    pos = node.start
    for start, end, marker in _cuts(result, node):
        if start > pos:
            pieces.append(src.text[pos:start])
        pieces.append(marker)
        pos = max(pos, end)
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


def _published_notes(root: Path) -> list[dict[str, Any]]:
    """Reference notes as the manifest carries them, with `from.run` spelled as the thread's id.

    The file records the run's path because that is what the command was given; a manifest has one grouping key for runs and every annotation already uses it, so a note that spelled it differently could not be joined to the run that proposed it.
    """
    from loom.ai.runs import thread_id
    from loom.refs.notes import read_notes

    out: list[dict[str, Any]] = []
    for note in read_notes(root):
        came = note.get("from")
        if isinstance(came, dict) and isinstance(came.get("run"), str):
            note = {**note, "from": {**came, "run": thread_id(came["run"])}}
        out.append(note)
    return out


# What a quilt has, never what a viewer should draw (specs/manifest.md §2, plan 0.9.5 §9). Every value is a property of
# loom, not of this quilt's current contents: a quilt with no documents yet is still a project that assembles into
# them, and "empty because not yet" is exactly what a viewer cannot tell from the data alone. A publisher whose corpora
# genuinely never have one says so, and a manifest that declares nothing leaves the viewer to derive from the data.
PUBLISHES = {"documents": True, "review": True, "bibliography": True, "discussions": True}


def build_manifest(
    result: ScanResult,
    numbers: dict[str, dict[str, AuxNumber]],
    fragments: dict[str, str],
    diagnostics: list[Diagnostic],
    records: Any | None = None,
    canon: list[Any] | None = None,
    canon_entries: list[dict[str, Any]] | None = None,
    history: Any | None = None,
) -> dict[str, Any]:
    asm = result.assembly
    root_name = result.quilt.name
    dm = result.default_master
    corpus_label = (master_title(result, dm) if dm else None) or root_name
    manifest: dict[str, Any] = {
        "interface_version": INTERFACE_VERSION,
        "publisher": {"name": "loom", "version": __version__},
        "publishes": PUBLISHES,
        "generated": _stamp(),
        "corpus": {"name": root_name, "root_label": corpus_label},
        "masters": [],
        "canon": list(canon_entries or []),
        "nodes": {},
        "keys": {},
        "regions": {},
        "edges": [],
        "relations": [],
        "inclusion": {},
        "states": STATE_LABELS,
        "annotations": {},
        "threads": build_threads(result.quilt.root),
        # The selector's data (plan 0.13 §5): which sessions exist, which is active, and how much is open in each.
        "sessions": _sessions(result.quilt.root),
        "reference_notes": _published_notes(result.quilt.root),
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
        if n.kind == "conflict":
            manifest["nodes"][key] = _conflict_entry(n)
            manifest["keys"][key] = _conflict_key(n)
            continue
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
        if n.kind == "section":
            entry["level"] = n.level  # the sectioning depth, so a viewer's contents can stop at subsubsection
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
    for rel in result.relations:
        # a relation is never a dependency, so it sits beside the edges rather than among them; the viewer derives per-node lists from this list
        manifest["relations"].append(
            {"from": rel.from_key, "to": rel.to_key, "kind": rel.kind, "src": {"file": rel.file, "line": rel.line}}
        )
    for m in result.masters:
        manifest["inclusion"][m] = _inclusion_tree(result, m)
    for taxon_name, group in _taxa(result).items():
        manifest["taxa"][taxon_name] = group
    cited_by: dict[str, list[str]] = {}
    for c in result.edges.cites:
        if c.file in asm.digest_files:
            continue  # cited by another paper's digest is not cited by the author: Brion read "cited 8" and was cited 0
        cited_by.setdefault(c.citekey, []).append(c.src)
    # A work can have two files claiming it: the digest a bundle inputs, and the shadow file holding proposals that
    # nothing inputs (plan 0.12 §4.1). They must not be confused -- a `{ck: f}` comprehension keeps whichever came
    # last, so `digest.fragment` would sometimes have pointed at the proposals.
    digests = {ck: f for f, ck in asm.digest_files.items() if not f.endswith(".proposed.tex")}
    proposals = {ck: f for f, ck in asm.digest_files.items() if f.endswith(".proposed.tex")}
    from loom.refs.links import read_links
    from loom.refs.unreadable import declarations

    manifest["links"] = [x.to_json() for x in read_links(result.quilt.root)]
    unreadable = declarations(result.quilt.root, "unreadable")
    for ck in sorted(set(result.bib) | set(digests) | set(proposals)):
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
                "source": extracted_from(ds),
                "extracted_from": extracted_from(ds),
                "published_as": published_as(ds),
                "method": ds.get("method", ""),
                "nodes": nodes,
            }
            sv = source_version(extracted_from(ds))
            if bib and bib.version and sv and bib.version != sv:
                version_mismatch = True
            manifest["macros"]["sets"][ck] = digest_macro_set(result, f)
        # Proposals ride in the same reference record, flagged, so the viewer meets them among the verified nodes
        # rather than in a queue of their own (§5.2). They are in no bundle and no closure.
        proposed_entry = None
        if ck in proposals:
            pf = proposals[ck]
            proposed_entry = {
                "file": pf,
                "fragment": fragments.get(f"digest:{pf}", ""),
                "nodes": [k for k, n in asm.nodes.items() if n.file == pf and n.kind == "environment"],
            }
            manifest["macros"]["sets"].setdefault(ck, digest_macro_set(result, pf))
        # what is on disk for this work, so the viewer can offer a PDF or say it has not been fetched.
        # Additive: the interface version is unchanged, as `relations` was in 0.2.
        wid = primary(bib) if bib else None
        home = storage_root(result.quilt.root) / wid.path if wid else None
        manifest["references"][ck] = {
            "citekey": ck,
            "slug": asm.prefix_of(ck),
            "bib": fields,
            "work": str(wid) if wid else "",
            "works": [str(w) for w in identify(bib)] if bib else [],
            "artifacts": {
                "dir": f"{STORAGE}/{wid.path}" if wid else "",
                "pdf": bool(home and (home / "paper.pdf").is_file()),
                "source": bool(home and (home / "src").is_dir()),
            },
            "digest": digest_entry,
            "proposed": proposed_entry,
            "results": _results_for(result.quilt.root, ck),
            "version_mismatch": version_mismatch,
            "cited_by": sorted(set(cited_by.get(ck, []))),
        }
        # the author's claim that there is no document to hold, so the reading view says so rather than showing an
        # empty pane and the digest as though it were the paper (plan 0.13 §4)
        said = unreadable.get(ck)
        if said is not None:
            manifest["references"][ck]["unreadable"] = {"why": said.why, "who": said.who, "when": said.when}
        # identifiers a lookup proposed for a work that states none: unconfirmed, and never the work's identity (8.9.1)
        if bib is not None and not declared(bib):
            found = load_candidates(result.quilt.root, bib)
            if found:
                manifest["references"][ck]["candidates"] = [
                    {
                        "id": c.id,
                        "source": c.source,
                        "confidence": c.confidence,
                        "strength": c.strength,
                        "title": c.title,
                    }
                    for c in found
                ]
    for doc, entry in zip(canon or [], manifest["canon"], strict=False):
        from loom.render.canon import macro_set

        published = macro_set(doc)
        if published:
            manifest["macros"]["sets"][f"canon:{doc.stem}"] = published
            entry["macros"] = f"canon:{doc.stem}"
        manifest["search"].append({"key": doc.path, "title": doc.title, "kind": "canon", "aliases": [], "tags": []})
    if history is not None:
        _versions(result, manifest, history)
    closure = result.closures.get(dm) if dm else None
    mathjax_macros = {
        k: v
        for k, v in (closure.macros.items() if closure else [])
        if v.kind != "let" and k not in ("uses", "incomplete", "nest")
    }
    # an alphabet declared with \DeclareMathAlphabet is a font the renderer has never heard of, and a body may use commands it does not implement; both are published as the nearest thing it can draw, so an author's own macro renders rather than reaching the page in error colour
    if closure is not None:
        for name, macro in declared_alphabets(closure.clean_text()).items():
            mathjax_macros.setdefault(name, macro)
        for name, macro in package_macros(loaded_packages(closure)).items():
            mathjax_macros.setdefault(name, macro)
    mathjax_macros.update(compatibility_macros(mathjax_macros))
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


def _conflict_entry(n: NodeRec) -> dict[str, Any]:
    """A doubly-defined id: published with the state `conflicted` and no text, so every view shows the id and none shows a winner (book 5.3.5)."""
    return {
        "id": n.key,
        "kind": "environment",
        "taxon": n.taxon or "",
        "style": n.style or "plain",
        "title": None,
        "aliases": list(n.aliases),
        "author": [],
        "created": None,
        "tags": [],
        "file": "",
        "src": [0, 0],
        "fragment": "",
        "numbers": {},
        "reached_by": list(n.reached_by),
        "parent": {},
        "children": [],
        "proofs": [],
        "external": False,
        "digest": None,
        "incomplete": [],
        "state": "conflicted",
        "derived": {"proved": False, "settled": False},
        "conflict": list(n.conflict),
    }


def _conflict_key(n: NodeRec) -> dict[str, Any]:
    return {
        "key": n.key,
        "node": n.key,
        "kind": "statement",
        "file": "",
        "src": [0, 0],
        "hash": "",
        "incomplete": [],
        "state": "conflicted",
        "reviews": {"latest_current": None, "latest_any": None, "open": {}, "detached": 0},
        "uses": [],
        "closure": [n.key],
        "previous_key_match": None,
        "conflict": list(n.conflict),
    }


def _versions(result: ScanResult, manifest: dict[str, Any], history: Any) -> None:
    """`keys[k].version` when a key's current text is one the history recorded: what the viewer shows as "text of @3" (book 17.5)."""
    from loom.history.versions import matching_version

    for key, entry in manifest["keys"].items():
        h = entry.get("hash")
        if not h:
            continue
        v = matching_version(history, key, h)
        if v is not None:
            entry["version"] = {"step": f"{v.step:04d}", "name": v.name}


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

    # The files currently being expanded. Only an INCLUSION enters one -- a section claimant lives in the file it was
    # already in, and guarding those would cut every master's own sections off the tree. `inclusion-cycle` is already
    # an error the scanner reports; a tree that follows the cycle turns that error into a traceback.
    including: set[str] = set()

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
                if inc.child in including:
                    # The cycle is named where it closes, so a reader of the tree can see why it stops.
                    out.append(
                        {
                            "key": inc.child,
                            "via": inc.kind,
                            "file": inc.child,
                            "shift": inc.shift,
                            "children": [],
                            "cycle": True,
                        }
                    )
                    continue
                including.add(inc.child)
                try:
                    kids = children_of(child, inc.shift)
                finally:
                    including.discard(inc.child)
                out.append({"key": inc.child, "via": inc.kind, "file": inc.child, "shift": inc.shift, "children": kids})
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
