# Manifest: `build/manifest.json`

The manifest is the only index a viewer reads. It carries the graph and everything non-textual: nodes, keys, edges, inclusion trees, numbering, states and causes, annotations, threads, diagnostics, tags, taxa, macros, search entries. Text lives in fragments. Interface version 1.

Field names are fixed; unknown fields must be ignored by viewers. All timestamps are ISO 8601 UTC. All hashes are `sha256:<hex>`.

## 1. Top level

**[decided]**

```json
{
  "interface_version": 1,
  "publisher": {"name": "loom", "version": "0.1.0"},
  "publishes": {"documents": true, "review": true, "bibliography": true, "discussions": true},
  "generated": "2026-09-16T14:40:02Z",
  "corpus": {"name": "Relative localization", "root_label": "Relative virtual localization"},
  "masters": [ ... ],
  "canon": [ ... ],
  "nodes": { "rl-0004": { ... }, "drafting/main.tex#section:3": { ... } },
  "keys": { "rl-0004": { ... }, "rl-0004/proof": { ... } },
  "regions": { "rl-0004#eq:main": { ... } },
  "edges": [ ... ],
  "relations": [ ... ],
  "inclusion": { "drafting/main.tex": { ... } },
  "states": { "labels": { ... } },
  "annotations": { "a-2026-09-16-0007": { ... } },
  "threads": { "2026-09-16T14-02-referee": { ... } },
  "reference_notes": [ ... ],
  "diagnostics": [ ... ],
  "tags": { "localization": ["rl-0004", "rl-0012"] },
  "taxa": { "Lemma": {"style": "plain", "slug": "lemma", "count": 14} },
  "references": { "Man12": { ... } },
  "macros": { "default": [ ... ], "sets": { "Man12": [ ... ] } },
  "search": [ ... ]
}
```

`corpus.name` is the project's name — what a viewer shows as the corpus's name — and `root_label` the default document's display title. They are different things: the first names the body of work, the second names one document in it.

**[decided]** `reference_notes` lists works an agent proposed citing and a person accepted: `{"work": "…the work the suggestion named", "for": ["rl-0004"], "claim": "…the argument for citing it", "identifier": {"verified": false}, "accepted": {"when": "…", "who": "…"}, "from": {"run": "…", "annotation": "a-…"}}`. **[decided]** `work` is the work and `claim` is what the agent said it supports, in that order and not the other way round: a note whose `work` held the argument could never become a bibliography entry, which is the one thing the breadcrumb exists for (DR-170). It is a **breadcrumb and never a second source of identity truth**: `identifier.verified` is false until a person confirms it in the bibliography, and nothing here enters `references`, the bibliography, or any closure. A viewer shows them on the keys in `for`. Optional, like every other section.

**[decided]** Beside `manifest.json` and `fragments/`, a publisher may write **`source/<key>.tex`**: one file per key holding that key's own source text before macro expansion, which a viewer fetches lazily for a verbatim view. It is beside the manifest rather than inside it because the manifest is loaded whole on every poll and already runs to hundreds of kilobytes, while source is wanted one key at a time and only when a reader asks. Optional: a viewer that finds nothing there shows the rendered form and no toggle.

**[decided]** `publishes` is the read side's capability block, and it answers a question the data cannot: **what this corpus *has*, never what a viewer should draw.** Four booleans — `documents`, `review`, `bibliography`, `discussions` — each saying whether the corpus is the kind of thing that has one. `"documents": false` says this corpus is not assembled into documents; it does not say "hide the read view", and a viewer decides what to make of it, as `GET /_api`'s capability list works on the write side (`write-api.md` §1).

It exists because deriving the answer from emptiness cannot distinguish **empty because not yet** from **empty because never**. A quilt with no runs yet would lose a view and get it back later, and since the manifest is re-polled every second the furniture would move while someone worked. A publisher declares once instead.

The values are properties of the publisher and its corpora, not of this corpus's current contents: loom writes all four `true` for every quilt, because a quilt with no documents yet is still a project that assembles into them. `publishes` is optional, and a manifest that omits it leaves the viewer to derive what it can from the data — which is what every version 1 manifest written before this field gets. Additive, so `interface_version` is unchanged.

**[decided]** **A publisher may omit any top-level section it has nothing to say about, and a viewer treats an absent section as an empty one.** `interface_version` and `publisher` are the two exceptions; everything else may be missing. A publisher with no masters, no review ledger or no bibliography writes no `masters`, no `annotations` and no `references`, and is conforming. This is what makes the interface publisher-neutral rather than loom-shaped: a corpus tool and a site generator publish very different subsets of it, and neither should have to write empty objects to prove it read the specification. Absence and emptiness mean the same thing, so a viewer must never distinguish them, and a publisher may use whichever is more natural. A malformed *value* is a different matter and remains the publisher's error. `docs/specs/fixture-minimal/` is the fixture that holds this floor.

## 2. Masters and canon

**[decided]** `masters` lists the documents a reader may work in; `canon` lists the landmarks, in the order the publisher recorded them, oldest first. A document the publisher considers superseded appears in neither.

```json
"canon": [
  {"path": "canon/paper-v1.tex", "stem": "paper-v1", "title": "Relative virtual localization",
   "fragment": "fragments/canon/paper-v1.html", "hash": "3f9a...",
   "step": "0002", "name": "paper-v1", "message": "Submitted to the Journal", "when": "2026-09-13T09:00:00Z",
   "macros": "canon:paper-v1"}
]
```

`path`, `stem`, `title` and `fragment` are required; the rest are present when the publisher knows them. `macros` names an entry of `macros.sets` (§14). A canon fragment carries no identity at all: no element in it has `data-id` or `data-key`, nothing in it appears in `nodes` or `keys`, and a viewer renders it as a document and nothing more.

## 2a. Masters

**[decided]**

```json
{
  "path": "drafting/main.tex",
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

**[decided]** A node whose id two files define is published with `"state": "conflicted"`, an empty `fragment` and `file`, `"src": [0, 0]`, no children and no proofs, and an additional `conflict` listing the files that define it. It has no text: a publisher that cannot say which of two definitions is the node's says neither. Its key entry carries the same `state` and `conflict`, an empty `hash`, an empty `uses`, and no acceptance.

```json
"rl-0011": {
  "id": "rl-0011", "kind": "environment", "taxon": "Lemma", "title": null,
  "file": "", "src": [0, 0], "fragment": "", "state": "conflicted",
  "conflict": ["drafting/main.tex", "drafting/talk.tex"],
  "reached_by": ["drafting/main.tex", "drafting/talk.tex"], "proofs": [], "children": []
}
```

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
  "numbers": { "drafting/main.tex": {"number": "3.4", "page": 12} },
  "reached_by": ["drafting/main.tex", "drafting/talk.tex"],
  "parent": { "drafting/main.tex": "rl-0020" },
  "children": [],
  "proofs": ["rl-0004/proof"],
  "external": false,
  "basis": "local-proof",
  "basis_reason": "inferred from environment Lemma",
  "digest": null,
  "incomplete": [],
  "state": "accepted",
  "derived": {"proved": true, "settled": false}
}
```

Rules: `kind` is `environment`, `section`, or `proof` (for labelled proof nodes); a section node also carries `"level"`, its sectioning depth (1 for `\section`, 2 for `\subsection`, and so on, shifted by any `\nest`), so a viewer can stop a contents list at a chosen depth; `numbers` and `parent` are per master; `reached_by` empty means loose; `external` true for cited-result blocks and digest nodes, with `digest` naming the citekey for the latter and `locator` present when available; `basis` on environment nodes is `expository`, `local-proof`, `cited-result`, `assumption`, `open-claim`, or `unclassified`, with `basis_reason` explaining the scan's choice or uncertainty; `inline_proof` is true when an explicitly `local-proof` remark or comment has its whole argument inside the block and no separate attached proof; `incomplete` lists the `\incomplete` texts in the node's statement; `state` and `derived` summarize the statement key (see 4); `children` lists included nodes in order for section nodes and nested environments. The basis fields are additive in interface version 1 (DR-198); DR-199 replaces the `definition` value with `expository` and adds `inline_proof`.

## 4. Keys

**[decided]** One entry per ledger-acceptable key.

**[decided]** A key may carry `version`, `{"step": "0002", "name": "paper-v1"}`, when its current text is one the publisher has recorded: what a viewer shows as "text of @2". Its absence says nothing is wrong — a key whose text has moved on since the last landmark is the ordinary case. Sections and qualified keys never carry it.

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
  "numbers": { "drafting/main.tex": {"number": "3.2"} },
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
"drafting/main.tex": {
  "key": "drafting/main.tex",
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
    "incomplete": {"label": "incomplete", "color": "negative"},
    "conflicted": {"label": "conflicted", "color": "negative"}
  },
  "derived": {
    "proved":  {"label": "proved",  "color": "positive"},
    "settled": {"label": "settled", "color": "positive-strong"}
  }
}
```

Reserved colour classes: `neutral`, `positive`, `positive-strong`, `warning`, `negative`, `info`. A key's `state` is a label name; `stale` is reported as `acceptance.fresh = false` and rendered as the modifier. Two labels may share a colour class — `incomplete` and `conflicted` are both negative — and a viewer that wants to tell them apart does so by name, not by colour.

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
  "recorded": true,
  "quote": "the inclusion is open by the rigidity lemma",
  "severity": "major",
  "payload": "\\begin{lemma}\\label{rl-0021}...",
  "placement": "after",
  "run": "ai/runs/2026-09-16T14-02-referee",
  "record": "ai/runs/2026-09-16T14-02-referee",
  "discarded": false,
  "discard_reason": null
}
```

`body_html` is the Markdown body rendered by the publisher into the dialect's inline subset.

**[decided]** Three fields say how well the annotation is still attached, and they answer different questions. `detached` is false while the quoted text is still found in the target. `recorded` is false when the text the annotation was written against — the `target.hash` — is neither the target's current text nor a version the publisher kept, so a reader cannot be shown what was being objected to. `anchored` is the conjunction a viewer draws a margin mark from: an annotation is anchored when it has a selector, that selector still resolves, and the version it names can still be produced. A publisher that keeps no versions reports `recorded: false` and `anchored: false` on everything it cannot show, which is the honest answer; it never reports `anchored: true` for an annotation whose subject it has lost.

**[decided]** `discard_reason` is the text given when the annotation was withdrawn, or null. Discarding is the one state change that carries a reason, because withdrawing a finding says the finding should not have been raised and the record is worth nothing without the why.

**[decided]** `severity` grades the fault a finding names — `major`, `moderate`, `minor` — and is null where the annotation names no fault. It is unrelated to a diagnostic's `severity`, which grades a message. `payload` is text the annotation proposes and `placement` (`replace`, `after`, `before`) is a hint for where a viewer shows it relative to the anchor; a viewer previews a payload and never applies one.

**[decided]** `run` is the run or comment session the annotation belongs to, and is the key a viewer groups by. `record` carries the same string and is deprecated: it once named the file an annotation lived in, and annotations now live in one append-only log per corpus, so a path would name the same file for every one of them. A viewer that treated `record` as an opaque grouping key needs no change.

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
    {"name": "referee-rl-0004.notes.md", "kind": "notes", "path": "ai/runs/.../referee-rl-0004.notes.md"},
    {"name": "draft-rl-0019.tex", "kind": "draft", "path": "..."},
    {"name": "referee-rl-0004.annotations", "kind": "annotations", "count": 3}
  ],
  "log": [{"time": "...", "command": "loom source rl-0004 --closure"}],
  "discarded": false
}
```

**[decided]** A thread of kind `run` also carries `pipeline`: the modes the run applied, in order, each `{mode, target, report}` with `pass` when it is a numbered re-run, `fragment` naming the rendered report fragment, and `blocks` indexing that fragment as `{name, title, findings}`. It is **derived, not declared** — every mode writes `<mode>-<target>.notes.md` without exception, so the run directory already says which modes ran and against what, and says it retroactively for runs written before the field existed. The order is the files' own, a numbered second pass after its first; name order rather than clock order, because two builds of one quilt must not disagree about it. A publisher with no modes emits no `pipeline`, and a viewer must not recover a mode by parsing a filename itself.

`messages` comes from `thread.md` (rendered) or, later, from the write API; `log` from `run.log`. As published by loom (M6): every run under `ai/runs/` is a thread of `kind` `run` with `path` (the run directory), `title` from the first heading of `thread.md` or the run's name, `participants` from the run's name and the annotations' authors, `targets` from the annotations, `attachments` named by file with kinds `annotations` (with `count`), `draft`, `proposal`, `digest`, `plan`, `notes`, `script`, or `file`; every comment session — one author on one day, replayed from the annotation log — is a thread of `kind` `comments` whose messages are its annotations. Each thread also has a `search` entry with `kind` `thread`.

## 11. Diagnostics

**[decided]** See `diagnostics.md` for codes.

```json
{"severity": "error", "code": "double-inclusion",
 "message": "rl-0011 is included twice in drafting/main.tex (via rl-0020 and via rl-0031)",
 "locations": [{"file": "nodes/rl-0020.tex", "line": 14}, {"file": "nodes/rl-0031.tex", "line": 3}],
 "keys": ["rl-0011", "rl-0020", "rl-0031"]}
```

**[decided]** Two optional fields. `subject` says what the diagnostic is about: `"source"` (the default when absent) or `"record"`, the publisher's own account of the source. `fixes` is a list of commands that would resolve it, each `{"label": "...", "command": "..."}`; they are data, and a viewer offers them to be copied and runs nothing.

```json
{"severity": "error", "code": "duplicate-id",
 "message": "rl-0011 is defined by drafting/main.tex and drafting/talk.tex; it has no text until one definition remains",
 "locations": [{"file": "drafting/main.tex", "line": 88}, {"file": "drafting/talk.tex", "line": 12}],
 "keys": ["rl-0011"],
 "fixes": [{"label": "fork the copy in drafting/talk.tex", "command": "loom fork rl-0011 --in drafting/talk.tex"}]}
```

## 12. Tags and taxa

**[decided]** `tags` maps each tag to the ids (or keys) carrying it. `taxa` maps each display name to its style class, slug, and count.

## 13. References

**[decided]**

```json
"Man12": {
  "citekey": "Man12",
  "slug": "Man12",
  "bib": {"author": "Manolache, Cristina", "title": "Virtual pull-backs", "year": 2012, "eprint": "0805.2065"},
  "work": "doi:10.1090/S1056-3911-2011-00606-1",
  "works": ["doi:10.1090/S1056-3911-2011-00606-1", "arXiv:0805.2065v2"],
  "artifacts": {"dir": "digests/storage/doi/10.1090_S1056-3911-2011-00606-1", "pdf": true, "source": false},
  "digest": {"file": "digests/Man12.tex", "fragment": "fragments/digests/Man12.html",
             "source": "arXiv:0805.2065v2", "extracted_from": "arXiv:0805.2065v2",
             "published_as": "doi:10.1090/S1056-3911-2011-00606-1",
             "method": "extract", "nodes": ["Man12-setup", "Man12-thm-4.1"]},
  "version_mismatch": false,
  "cited_by": ["rl-0004/proof", "drafting/main.tex"]
}
```

`digest` is null for an undigested citekey. Each entry also carries `slug`, the prefix of the digest's node ids: the prefix the digest declares in its header, or the citekey with every character outside `[A-Za-z0-9]` removed when it declares none (DR-45, DR-109).

**[decided]** `work` is the work's global identifier and `works` every identifier its bibliography entry states, each written `scheme:value` with the scheme one of `doi`, `arxiv`, `mr`, `zbl`, or `work` (a deterministic hash of author, title and year, for an entry stating none). `artifacts.dir` is where what loom holds for the work lives, under `digests/storage/` (book 8.16, DR-192), servable under the viewer's origin, and the two flags say which of the source and the PDF are present; both are false until someone fetches, adds or drops a copy, and neither the PDF nor the source is in version control, so another reader's copy of the corpus may have neither. `digest.extracted_from` and `digest.published_as` distinguish the artifact whose numbering the digest carries from the work the bibliography cites; `digest.source` repeats `extracted_from` and is retained for readers written before 0.5. All of these are additive and the interface version is unchanged (DR-108, DR-109, DR-110).

**[decided]** `candidates`, present only on a reference whose bibliography entry states no identifier and only once a lookup has run, lists identifiers a lookup proposed, best first: `{"id": "doi:10.1353/ajm.1998.0020", "source": "zbMATH Open", "confidence": 1.0, "strength": "strong", "title": "…"}`. They are unconfirmed and never the reference's `work`, which changes only when the bibliography states the identifier. A viewer may show them, marked as unconfirmed. Additive; the interface version is unchanged (DR-122).

## 14. Macros

**[decided]** Each macro is `{"name": "Res", "args": 0, "body": "\\mathrm{Res}"}`. `macros.default` is the preamble closure's set; `macros.sets` holds per-fragment sets named in fragments' `data-macros`.

## 15. Search

**[decided]** Entries for the viewer's search box: `{"key": "rl-0004", "title": "...", "taxon": "Lemma", "aliases": [...], "tags": [...], "excerpt": "..."}` for every node and every digest node; masters, canon documents and threads have entries with `kind` (`master`, `canon`, `thread`).

## 16. Relations

**[decided]** Links between nodes that are not dependencies. A relation enters no closure, no bundle, no acceptance row and no staleness computation; it exists so that a viewer can show two nodes as related. `\uses` remains the only way to declare a dependency the text does not name.

```json
"relations": [
  {"from": "rl-0071", "to": "rl-0004", "kind": "see",
   "src": {"file": "nodes/rl-0071.tex", "line": 1}}
]
```

`from` is the node that declared the relation, so the declaring side is known; display is symmetric and a viewer shows the relation on both nodes. `kind` is `see` in this version. Adding a kind is a decision-record event, and a viewer renders a kind it does not know as a labelled list of links. Nodes gain no field: a viewer derives per-node lists from this one.
