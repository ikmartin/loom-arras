# Manifest: `build/manifest.json`

The manifest is the only index a viewer reads. It carries the graph and everything non-textual: nodes, keys, edges, inclusion trees, numbering, states and causes, annotations, threads, diagnostics, tags, taxa, macros, search entries. Text lives in fragments. Interface version 1.

Field names are fixed; unknown fields must be ignored by viewers. All timestamps are ISO 8601 UTC. All hashes are `sha256:<hex>`.

## 1. Top level

**[decided]**

```json
{
  "interface_version": 1,
  "publisher": {"name": "loom", "version": "0.1.0"},
  "generated": "2026-09-16T14:40:02Z",
  "corpus": {"name": "relloc", "root_label": "Relative virtual localization"},
  "masters": [ ... ],
  "nodes": { "rl-0004": { ... }, "drafts/main.tex#section:3": { ... } },
  "keys": { "rl-0004": { ... }, "rl-0004/proof": { ... } },
  "regions": { "rl-0004#eq:main": { ... } },
  "edges": [ ... ],
  "inclusion": { "drafts/main.tex": { ... } },
  "states": { "labels": { ... } },
  "annotations": { "a-2026-09-16-0007": { ... } },
  "threads": { "2026-09-16T14-02-referee": { ... } },
  "diagnostics": [ ... ],
  "tags": { "localization": ["rl-0004", "rl-0012"] },
  "taxa": { "Lemma": {"style": "plain", "slug": "lemma", "count": 14} },
  "references": { "Man12": { ... } },
  "macros": { "default": [ ... ], "sets": { "Man12": [ ... ] } },
  "search": [ ... ]
}
```

`corpus.name` is the quilt name (or site name for another publisher); `root_label` a display title.

## 2. Masters

**[decided]**

```json
{
  "path": "drafts/main.tex",
  "title": "Relative virtual localization",
  "default": true,
  "fragment": "fragments/masters/main.html",
  "engine": "pdflatex",
  "compiled": "2026-09-16T14:39:10Z",
  "pdf": "main/main.pdf",
  "numbering_known": true
}
```

`compiled`, `pdf`, and `numbering_known` are absent or false before the first compile.

## 3. Nodes

**[decided]** Keyed by id, or by qualified key for untagged nodes.

```json
"rl-0004": {
  "id": "rl-0004",
  "kind": "environment",
  "taxon": "Lemma",
  "style": "plain",
  "title": "Residue independent of embedding",
  "aliases": ["lem:res-indep"],
  "author": ["Markas Hecht"],
  "created": "2026-09-15",
  "tags": ["localization", "residue"],
  "file": "nodes/rl-0004.tex",
  "src": [104, 1420],
  "fragment": "fragments/nodes/rl-0004.html",
  "numbers": { "drafts/main.tex": {"number": "3.4", "page": 12} },
  "reached_by": ["drafts/main.tex", "drafts/talk.tex"],
  "parent": { "drafts/main.tex": "rl-0020" },
  "children": [],
  "proofs": ["rl-0004/proof"],
  "external": false,
  "digest": null,
  "incomplete": [],
  "state": "accepted",
  "derived": {"proved": true, "settled": false}
}
```

Rules: `kind` is `environment`, `section`, or `proof` (for labelled proof nodes); a section node also carries `"level"`, its sectioning depth (1 for `\section`, 2 for `\subsection`, and so on, shifted by any `\nest`), so a viewer can stop a contents list at a chosen depth; `numbers` and `parent` are per master; `reached_by` empty means loose; `external` true for digest nodes, with `digest` naming the citekey and `locator` present; `incomplete` lists the `\incomplete` texts in the node's statement; `state` and `derived` summarize the statement key (see 4); `children` lists included nodes in order for section nodes and nested environments.

## 4. Keys

**[decided]** One entry per ledger-acceptable key.

```json
"rl-0004/proof": {
  "key": "rl-0004/proof",
  "node": "rl-0004",
  "kind": "proof",
  "ordinal": 1,
  "file": "nodes/rl-0004.tex",
  "src": [612, 1420],
  "hash": "sha256:5d2f...",
  "incomplete": ["The domination step needs the base to be quasi-compact."],
  "state": "incomplete",
  "acceptance": {
    "author": "Markas Hecht",
    "date": "2026-09-16T14:02:11Z",
    "fresh": false,
    "causes": [
      {"kind": "dependency-changed", "id": "rl-0002", "when": "2026-09-09",
       "diff": "diffs/rl-0004-proof-rl-0002.diff"}
    ]
  },
  "reviews": {
    "latest_current": {"author": {"kind": "run", "id": "2026-09-16T14-02-referee"},
                       "date": "2026-09-16T14:31:08Z"},
    "latest_any": {"author": {"kind": "person", "id": "Tom Graber"}, "date": "2026-09-10T09:00:00Z"},
    "open": {"objection": 2, "suggestion": 0, "question": 1, "ok": 0},
    "detached": 2
  },
  "uses": ["rl-0002", "Man12-thm-4.1"],
  "closure": ["rl-0004", "rl-0002", "rl-0001", "Man12-thm-4.1", "Man12-setup"],
  "previous_key_match": null
}
```

Rules: `state` is one of the publisher's state labels (section 8); `acceptance` absent when no row exists; `causes` present only when `fresh` is false, each with a `diff` path under the build directory to a unified diff (or `null` when no snapshot exists); `previous_key_match` names an old positional key whose acceptance row matches this text (7.10 in the book), else null; `uses` lists direct dependencies; `closure` the transitive statement closure.

## 5. Regions

**[decided]** Labelled equations, figures, tables, and items that are annotation targets or link targets.

```json
"rl-0004#eq:main": {
  "key": "rl-0004#eq:main",
  "container": "rl-0004",
  "in": "statement",
  "label": "eq:main",
  "numbers": { "drafts/main.tex": {"number": "3.2"} },
  "src": [301, 388]
}
```

`in` is `statement`, `proof:<key>`, or `prose`.

## 6. Edges

**[decided]**

```json
{"from": "rl-0004/proof", "to": "Man12-thm-4.1", "kind": "proof", "via": "postnote",
 "src": {"file": "nodes/rl-0004.tex", "line": 9}}
```

`from` is a key, a master path, or an untagged section's qualified key; `to` is a node id or qualified key; `kind` is `statement`, `proof`, or `prose`; `via` is `ref`, `eqref`, `cref`, `autoref`, `pageref`, `uses`, `postnote`. Inclusion is not an edge; see 7.

## 7. Inclusion

**[decided]** One tree per master, as nested objects.

```json
"drafts/main.tex": {
  "key": "drafts/main.tex",
  "children": [
    {"key": "rl-0020", "via": "section", "shift": 0, "children": [
      {"key": "rl-0011", "via": "input", "file": "nodes/rl-0011.tex", "shift": 0, "children": []},
      {"key": "rl-0030", "via": "nest", "file": "nodes/rl-0030.tex", "shift": 1, "children": [ ... ]}
    ]}
  ]
}
```

`via` is `section`, `input`, `nest`, `include`, or `nested-env`.

## 8. States

**[decided]** The publisher declares its state vocabulary so the viewer renders labels and colours without knowing meanings.

```json
"states": {
  "labels": {
    "draft":      {"label": "draft",      "color": "neutral"},
    "accepted":   {"label": "accepted",   "color": "positive"},
    "stale":      {"label": "stale",      "color": "warning", "modifier": true},
    "incomplete": {"label": "incomplete", "color": "negative"}
  },
  "derived": {
    "proved":  {"label": "proved",  "color": "positive"},
    "settled": {"label": "settled", "color": "positive-strong"}
  }
}
```

Reserved colour classes: `neutral`, `positive`, `positive-strong`, `warning`, `negative`, `info`. A key's `state` is a label name; `stale` is reported as `acceptance.fresh = false` and rendered as the modifier.

## 9. Annotations

**[decided]** Every non-discarded annotation, plus discarded ones with `discarded: true` so the viewer can offer to show them.

```json
"a-2026-09-16-0007": {
  "id": "a-2026-09-16-0007",
  "author": {"kind": "run", "id": "2026-09-16T14-02-referee", "label": "referee run, 16 Sep"},
  "created": "2026-09-16T14:31:08Z",
  "target": {"key": "rl-0004/proof", "hash": "sha256:5d2f..."},
  "kind": "objection",
  "body_html": "<p>No rigidity lemma exists in the quilt. ...</p>",
  "status": "open",
  "in_reply_to": null,
  "anchored": true,
  "detached": false,
  "quote": "the inclusion is open by the rigidity lemma",
  "record": "ai/runs/2026-09-16T14-02-referee/annotations.json",
  "discarded": false
}
```

`body_html` is the Markdown body rendered by the publisher into the dialect's inline subset.

## 10. Threads

**[decided]** Discussions the viewer displays read-only: runs, comment sessions, or anything else a publisher chooses.

```json
"2026-09-16T14-02-referee": {
  "id": "2026-09-16T14-02-referee",
  "kind": "run",
  "title": "referee rl-0004",
  "created": "2026-09-16T14:02:00Z",
  "participants": [{"kind": "person", "id": "Markas Hecht"}, {"kind": "agent", "id": "claude-code"}],
  "targets": ["rl-0004", "rl-0004/proof"],
  "messages": [
    {"author": {"kind": "agent", "id": "claude-code"}, "time": "2026-09-16T14:31:00Z",
     "body_html": "<p>Refereed rl-0004; three objections.</p>"}
  ],
  "attachments": [
    {"name": "bundle-rl-0004.tex", "kind": "bundle", "path": "ai/runs/.../bundle-rl-0004.tex"},
    {"name": "draft-rl-0019.tex", "kind": "draft", "path": "..."},
    {"name": "referee-rl-0004.annotations", "kind": "annotations", "count": 3}
  ],
  "log": [{"time": "...", "command": "loom bundle rl-0004"}],
  "discarded": false
}
```

`messages` comes from `thread.md` (rendered) or, later, from the write API; `log` from `run.log`. As published by loom (M6): every run under `ai/runs/` is a thread of `kind` `run` with `path` (the run directory), `title` from the first heading of `thread.md` or the slug, `participants` from `run.toml`'s agent and the annotations' authors, `targets` from the annotations, `attachments` named by file with kinds `annotations` (with `count`), `bundle`, `draft`, `proposal`, `digest`, `plan`, `notes`, `script`, or `file`; every comment session under `comments/` is a thread of `kind` `comments` whose messages are its annotations. Each thread also has a `search` entry with `kind` `thread`.

## 11. Diagnostics

**[decided]** See `diagnostics.md` for codes.

```json
{"severity": "error", "code": "double-inclusion",
 "message": "rl-0011 is included twice in drafts/main.tex (via rl-0020 and via rl-0031)",
 "locations": [{"file": "nodes/rl-0020.tex", "line": 14}, {"file": "nodes/rl-0031.tex", "line": 3}],
 "keys": ["rl-0011", "rl-0020", "rl-0031"]}
```

## 12. Tags and taxa

**[decided]** `tags` maps each tag to the ids (or keys) carrying it. `taxa` maps each display name to its style class, slug, and count.

## 13. References

**[decided]**

```json
"Man12": {
  "citekey": "Man12",
  "bib": {"author": "Manolache, Cristina", "title": "Virtual pull-backs", "year": 2012, "eprint": "0805.2065"},
  "digest": {"file": "refs/Man12.tex", "fragment": "fragments/digests/Man12.html",
             "source": "arXiv:0805.2065v2", "method": "extract", "nodes": ["Man12-setup", "Man12-thm-4.1"]},
  "version_mismatch": false,
  "cited_by": ["rl-0004/proof", "drafts/main.tex"]
}
```

`digest` is null for an undigested citekey. Each entry also carries `slug`, the citekey with every character outside `[A-Za-z0-9]` removed, which is the prefix of the digest's node ids (DR-45).

## 14. Macros

**[decided]** Each macro is `{"name": "Res", "args": 0, "body": "\\mathrm{Res}"}`. `macros.default` is the preamble closure's set; `macros.sets` holds per-fragment sets named in fragments' `data-macros`.

## 15. Search

**[decided]** Entries for the viewer's search box: `{"key": "rl-0004", "title": "...", "taxon": "Lemma", "aliases": [...], "tags": [...], "excerpt": "..."}` for every node and every digest node; masters and threads have entries with `kind`.

## Open questions

- Whether diffs should be inlined in the manifest or referenced by path. **[assumed]** By path, under `build/diffs/`, to keep the manifest small.
- Whether `search` should carry a full-text index. **[assumed]** Title, aliases, tags, excerpt only; full text is a later addition.
- Size limits. **[deferred]**; measure on the ACGS fixture; fragments are lazy, the manifest is not.
