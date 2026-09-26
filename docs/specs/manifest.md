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

**[decided]** `reference_notes` lists works an agent proposed citing and a person accepted: `{"work": "…the work the suggestion named", "for": ["rl-0004"], "claim": "…the argument for citing it", "identifier": {"verified": false}, "accepted": {"when": "…", "who": "…"}, "from": {"session": "s-…", "annotation": "a-…"}}`. **[decided]** `work` is the work and `claim` is what the agent said it supports, in that order and not the other way round: a note whose `work` held the argument could never become a bibliography entry, which is the one thing the breadcrumb exists for (DR-170). It is a **breadcrumb and never a second source of identity truth**: `identifier.verified` is false until a person confirms it in the bibliography, and nothing here enters `references`, the bibliography, or any closure. A viewer shows them on the keys in `for`. Optional, like every other section.

**[decided]** Beside `manifest.json` and `fragments/`, a publisher may write **`source/<key>.tex`**: one file per key holding that key's own source text before macro expansion, which a viewer fetches lazily for a verbatim view. It is beside the manifest rather than inside it because the manifest is loaded whole on every poll and already runs to hundreds of kilobytes, while source is wanted one key at a time and only when a reader asks. Optional: a viewer that finds nothing there shows the rendered form and no toggle.

**[decided]** `publishes` is the read side's capability block, and it answers a question the data cannot: **what this corpus *has*, never what a viewer should draw.** Four booleans — `documents`, `review`, `bibliography`, `discussions` — each saying whether the corpus is the kind of thing that has one. `"documents": false` says this corpus is not assembled into documents; it does not say "hide the read view", and a viewer decides what to make of it, as `GET /_api`'s capability list works on the write side (`write-api.md` §1).

It exists because deriving the answer from emptiness cannot distinguish **empty because not yet** from **empty because never**. A quilt with no sessions yet would lose a view and get it back later, and since the manifest is re-polled every second the furniture would move while someone worked. A publisher declares once instead.

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

`name`, when present on a node, is an optional plain-text display name from its own `% !LOOM name:` directive. It is not unique, a reference alias, or a replacement for `id` or `title`. Display prefers `name`, then `title`, then type and document number in an explicitly selected document, then ID. Search entries prefer the name as their title and retain the original title in the excerpt; aliases are unchanged (DR-301-luisa).

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

Rules: `kind` is `environment`, `section`, or `proof` (for labelled proof nodes); a section node also carries `"level"`, its sectioning depth (1 for `\section`, 2 for `\subsection`, and so on, shifted by any `\nest`), so a viewer can stop a contents list at a chosen depth; `numbers` and `parent` are per master; `reached_by` empty means loose; `external` true for cited-result blocks and digest nodes, with `digest` naming the citekey for the latter and `locator` present when available — carrying the page the result is printed on, `Proposition 2.1, p.~7`, wherever extraction could locate it in the work's filed copy (DR-224); `basis` on environment nodes is `expository`, `local-proof`, `cited-result`, `assumption`, `open-claim`, or `unclassified`, with `basis_reason` explaining the scan's choice or uncertainty; `inline_proof` is true when an explicitly `local-proof` remark or comment has its whole argument inside the block and no separate attached proof; `incomplete` lists the `\incomplete` texts in the node's statement; `state` and `derived` summarize the statement key (see 4); `children` lists included nodes in order for section nodes and nested environments. The basis fields are additive in interface version 1 (DR-212); DR-213 replaces the `definition` value with `expository` and adds `inline_proof`.

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
    "latest_current": {"author": {"kind": "agent", "id": "Referee Agent"},
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

Rules: `state` is one of the publisher's state labels (section 8); `acceptance` is absent when no row exists; `causes` appear only when `fresh` is false. A cause may carry `when` (first observation date), `via` (immediate dependency for an indirect cause), `citation` (an anchor in the dependent document), and `comparison` with `accepted`, `current`, `accepted_macros`, `accepted_spans`, and `current_spans`. The fragment paths resolve under the build directory; spans are source offsets in each normalized text. A cause may also carry `diff`, a unified diff path or null if unavailable. Viewers tolerate absent optional fields. `previous_key_match` names an old positional key whose acceptance row matches this text (7.10 in the book), else null; `uses` lists direct dependencies; `closure` the transitive statement closure.

An optional top-level `incoming` object presents an external source revision for review without changing any key state. It has `remote`, `branch`, `base` and `commit` Git identifiers, `observed` (first fetch time), `files` (`status`, `path`, and optional text `diff` for TeX and bibliography inputs), optional `issues`, and `changes`. Each change has `key`, `kind` (`added`, `edited`, or `removed`), `local_changed`, `conflict` (both local and incoming edited the block differently from the base), `already_local`, optional local and incoming fragment paths, `incoming_macros`, and `affected` entries (`key`, optional citation anchor). Fragment paths resolve under the build directory. A viewer treats the section as prospective source, never as a mathematical acceptance or stale cause.

An optional top-level `unresolved` array lists blocks awaiting a mathematical decision after incorporation or an earlier edit. Each row has `key`, `status` (`needs-review`, `ok`, or `requires-attention`), `cause` (`incoming-pull` or `earlier-change`), `pull` commit when applicable, `changed_text`, `local_changed`, and `invalidated`. For pull rows, `local_changed` is true when the block or its dependency context has changed locally since its post-pull baseline. An older sync record can recover that baseline from the most recent incorporation's local source commit; null means it cannot establish one. For earlier changes it is true. `ok` is pending and does not change the key's recorded state. A changed fingerprint invalidates either saved decision and returns the block to `needs-review`. A block with an already fresh acceptance is omitted even when an earlier choice was `requires-attention`; an explicit pending `ok` stays until Finish review clears it. A transitive dependent is provisionally omitted while every active review cause is indirect through a block with a current pending OK; it reappears if that OK is invalidated or an independent cause remains.

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
  "author": {"kind": "agent", "id": "Referee Agent", "label": "Referee Agent"},
  "created": "2026-09-16T14:31:08Z",
  "target": {"key": "rl-0004/proof", "hash": "sha256:5d2f...", "work": null, "page": null},
  "in": null,
  "basis": null,
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
  "run": "s-2026-09-16-0001",
  "record": "s-2026-09-16-0001",
  "discarded": false,
  "discard_reason": null
}
```

`body_html` is the Markdown body rendered by the publisher into the dialect's inline subset.

**[decided]** `author.kind` is `agent` or `person` and `author.id` is the **name the writer declared**; `run` is the **session** the annotation belongs to, which is where it was written rather than who wrote it. The two were one field: an agent's annotation recorded its run directory as its author, so the log could say who only by naming a place (DR-199). The field keeps the name `run` because viewers read it by that name.

**[decided]** `target.key` is a key in the corpus, or — for a note on a page of a cited work (DR-209) — the work's identifier as `references[].work` spells it; `target.work` is then the citekey and `target.page` the page, so a viewer needs no lookup to say where the note is, and `basis` is `text` (the quotation locates in the page's committed text) or `box` (a drawn rectangle is the record). Both are null on a note on a key. The rectangles are in the work's sidecar (§13) under `marks`; the body is here, with every other annotation.

**[decided]** `in` is the document a claim about a node is read in, as a master path, or null for the node wherever it appears (plan 0.15, decision 9). A viewer draws an annotation that names a document in that document only, lists it on the node's own page with the document named, and shows it in no other document; the publisher bakes its mark into that document's fragment alone. An annotation whose document no longer holds the node is `detached`.

**[decided]** `kind` is one of five — `objection`, `suggestion`, `question`, `citation`, `note`. The first four **await an answer** and are what an open count counts; `note` records rather than ask, and is where "this checks out" goes (DR-204; plan 0.15, decision 2).

## 9.1 Sessions

**[decided]** `sessions` lists every session the index leaves standing, for the viewer's selector.

```json
"sessions": [
  {"id": "s-2026-09-16-0001", "title": "referee pass", "state": "open",
   "created": "2026-09-16T14:02:00Z", "opened": "2026-09-16T14:02:00Z", "rounds": 1, "active": true}
]
```

The **id** is minted once and is the address; the **title** is the author's and may change. `opened` is when the current round began, which is what "changed since last time" is measured from. `active` marks the one session writing lands in. A tombstoned session is not published at all.

**[decided]** Three fields say how well the annotation is still attached, and they answer different questions. `detached` is false while the quoted text is still found in the target. `recorded` is false when the text the annotation was written against — the `target.hash`, taken over the key's own text with its children's places marked (book 5.13) — is neither the target's current text nor a version the publisher kept, so a reader cannot be shown what was being objected to. Loom keeps every version a note is written against, so this is a version lost outside loom, or a paper on file that is not the one the note was written on; a fragment marks no unrecorded annotation, which is counted beside its key instead (DR-284-ikmartin). `anchored` is the conjunction a viewer draws a margin mark from: an annotation is anchored when it has a selector, that selector still resolves, and the version it names can still be produced. A publisher that keeps no versions reports `recorded: false` and `anchored: false` on everything it cannot show, which is the honest answer; it never reports `anchored: true` for an annotation whose subject it has lost.

**[decided]** `discard_reason` is the text given when the annotation was withdrawn, or null. Discarding is the one state change that carries a reason, because withdrawing a finding says the finding should not have been raised and the record is worth nothing without the why.

**[decided]** `severity` grades the fault a finding names — `major`, `moderate`, `minor` — and is null where the annotation names no fault. It is unrelated to a diagnostic's `severity`, which grades a message. `payload` is text the annotation proposes and `placement` (`replace`, `after`, `before`) is a hint for where a viewer shows it relative to the anchor; a viewer previews a payload and never applies one.

**[decided]** `run` is the id of the session the annotation belongs to, and is the key a viewer groups by. `record` carries the same string and is deprecated: it once named the file an annotation lived in, and annotations now live in one append-only log per corpus, so a path would name the same file for every one of them. A viewer that treated `record` as an opaque grouping key needs no change.

## 10. Threads

**[decided]** Sessions as the viewer displays them, keyed by session id. Loom publishes one thread of `kind` `session` per session; `kind` is an open string, and a viewer shows a kind it does not know generically.

```json
"s-2026-09-16-0002": {
  "id": "s-2026-09-16-0002",
  "kind": "session",
  "title": "referee rl-0004",
  "created": "2026-09-16T14:02:00Z",
  "participants": [{"kind": "person", "id": "Markas Hecht"}, {"kind": "agent", "id": "claude-code"}],
  "targets": ["rl-0004", "rl-0004/proof"],
  "attachments": [
    {"name": "referee-rl-0004.notes.md", "kind": "notes", "path": ".loom/sessions/s-2026-09-16-0002/referee-rl-0004.notes.md"},
    {"name": "draft-rl-0019.tex", "kind": "draft", "path": "..."},
    {"name": "annotations", "kind": "annotations", "count": 3}
  ],
  "log": [{"time": "...", "command": "loom source rl-0004 --closure"},
          {"time": "...", "command": "loom annotate rl-0004 --quote --kind objection", "annotation": "a-2026-09-16-0001"}],
  "discarded": false
}
```

**[decided]** A thread of kind `session` also carries `pipeline`: the modes applied in the session, in order, each `{mode, target, report}` with `pass` when it is a numbered re-run, `fragment` naming the rendered report fragment, and `blocks` indexing that fragment as `{name, title, findings}`. It is **derived, not declared** — every mode writes `<mode>-<target>.notes.md` without exception, so the session's directory already says which modes ran and against what. The order is the files' own, a numbered second pass after its first; name order rather than clock order, because two builds of one quilt must not disagree about it. A publisher with no modes emits no `pipeline`, and a viewer must not recover a mode by parsing a filename itself.

A thread carries no conversation: that is its transcript (§10.1). `log` comes from `run.log`, one entry per line; `annotation` is the annotation a `loom annotate` line made or changed, written after an arrow in the log, and absent on every other line. As published by loom (M6): every session is a thread of `kind` `session` with `path` (the session directory), `title` the session's title, `participants` from the annotations' authors, `targets` from the annotations, `attachments` named by file with kinds `annotations` (with `count`), `draft`, `proposal`, `digest`, `plan`, `notes`, `script`, or `file`. Each thread also has a `search` entry with `kind` `thread`.

## 10.1 Transcripts

**[decided]** A session's conversation is published beside the manifest, never in it, because every viewer polls the manifest and a long conversation would make every poll pay for it. The build writes `transcripts/<session>/<n>.json`, page `n` (from 1) holding the events numbered `100(n-1)+1` to `100n`:

```json
{"session": "s-2026-09-17-0002", "page": 1, "events": [
  {"seq": 1, "kind": "message", "who": "A. Author", "when": "2026-09-17T11:00:00Z",
   "body": "Have a look at Theorem 3.2.", "body_html": "<p>Have a look at Theorem 3.2.</p>",
   "changed": [{"id": "a-2026-09-17-0001", "kind": "question", "target": "Bellamy19-thm-3.2", "act": "created", "by": "A. Author", "body": "…"}]}
]}
```

The session's `seq` in `sessions` is the last event's number, so a viewer knows which pages exist without an index. `body` is what was written and `body_html` its rendering, by the same rules as an annotation's body; `changed` lists the annotations a message carried, each whole: `id`, `kind`, `target`, `work` and `page` for a note on a page, `act` (`created` or `replied`), `by`, `body`, and `quote`, `severity`, `payload` and `placement` where the annotation has them. A publisher that serves live answers the pages itself, from the inbox, so they are never stale under it, and adds new events through its own channel (specs/write-api.md; DR-278-ikmartin). `messages` was dropped from threads when transcripts arrived; the interface version stays 1 because no corpus outside the fixtures carried it (DR-264-ikmartin).

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
  "spans": {"path": "spans/doi/10.1090_S1056-3911-2011-00606-1.json", "sha256": "…"},
  "reading": {"total": 2, "open": 1},
  "version_mismatch": false,
  "cited_by": ["rl-0004/proof", "drafting/main.tex"]
}
```

`digest` is null for an undigested citekey. Each entry also carries `slug`, the prefix of the digest's node ids: the prefix the digest declares in its header, or the citekey with every character outside `[A-Za-z0-9]` removed when it declares none (DR-45, DR-109).

**[decided]** `work` is the work's global identifier and `works` every identifier its bibliography entry states, each written `scheme:value` with the scheme one of `doi`, `arxiv`, `mr`, `zbl`, or `work` (a deterministic hash of author, title and year, for an entry stating none). `artifacts.dir` is where what loom holds for the work lives, under `digests/storage/` (book 8.16, DR-192), servable under the viewer's origin, and the two flags say which of the source and the PDF are present; both are false until someone fetches, adds or drops a copy, and neither the PDF nor the source is in version control, so another reader's copy of the corpus may have neither. `digest.extracted_from` and `digest.published_as` distinguish the artifact whose numbering the digest carries from the work the bibliography cites; `digest.source` repeats `extracted_from` and is retained for readers written before 0.5. All of these are additive and the interface version is unchanged (DR-108, DR-109, DR-110).

**[decided]** `spans` points at a **sidecar** holding the geometry of the work's anchors: `{"artifact": <sha256>, "pages": {"2": {"width": 612, "height": 792, "rotate": 0}}, "quads": {"<result id>": [[x0, y0, x1, y1], …]}, "marks": {"<annotation id>": [[x0, y0, x1, y1], …]}}`, one rectangle per line — `quads` for the work's results by result id, `marks` for the notes on its pages by annotation id (DR-209). `rotate` is the page's own rotation in degrees, read from the document. `reading` on the reference counts those notes, and how many still await an answer, since they are in no key's row. It stands **beside** the manifest rather than inside it, for the reason `source` does: the manifest is loaded whole on every poll and geometry is wanted for the one paper being read. The pointer carries the sidecar's own hash, so a stale copy is noticed while the publisher rebuilds underneath. **Quads are derived and never recorded for a text anchor**: an anchor says where it is in the page's text, and the rectangles are computed from the word boxes at build time; a box anchor's rectangles are the anchor itself and are recorded. A work whose PDF is not on the publishing machine gets no sidecar, and the viewer has nothing to draw, which is the honest state.

**[decided]** **Coordinates are points with a top-left origin** — what `pdftotext -bbox-layout` emits — and never PDF user space, whose origin is at the bottom left. A viewer that hands these to a renderer's own transform draws every highlight mirrored about the middle of the page.

**[decided]** `unreadable`, present only where the author has declared one, is `{"why": …, "who": …, "when": …}`: the standing claim that the work has no document to hold at all. Nothing in a bibliography entry says so, which is why it is declared and never inferred, and a viewer says it rather than showing an empty pane (DR-198).

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
