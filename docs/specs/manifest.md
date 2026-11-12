# Manifest: `.loom/build/manifest.json`

The manifest is the only index a viewer reads. It carries the graph and everything non-textual: nodes, keys, edges, inclusion trees, numbering, states and causes, annotations, threads, diagnostics, tags, taxa, macros, search entries. Text lives in fragments.

Field names are fixed; unknown fields must be ignored by viewers. All timestamps are ISO 8601 UTC. All hashes are `sha256:<hex>`.

## 1. Top level

**[decided]**

```json
{
  "publisher": {"name": "loom", "version": "0.1.0"},
  "publishes": {"documents": true, "review": true, "bibliography": true, "discussions": true},
  "generated": "2026-09-16T14:40:02Z",
  "corpus": {"name": "Relative localization", "root_label": "Relative virtual localization", "home": "README.md", "directory": "relloc"},
  "masters": [ ... ],
  "canon": [ ... ],
  "history": { "steps": [ ... ] },
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
  "search": [ ... ],
  "files": [ ... ],
  "notes": { "n-2026-11-02-0001": { ... } },
  "changes": [ ... ],
  "changes_since": { "who": "…", "when": "…" },
  "config": { "quilt": { ... }, "library": { ... }, "lint": { ... }, "agents": { ... }, "sync": { ... } }
}
```

`corpus.name` is the project's name — what a viewer shows as the corpus's name — and `root_label` the default document's display title. They are different things: the first names the body of work, the second names one document in it. `corpus.home` is the front door, the file a viewer opens on when it remembers no place: the file `[quilt] home` names when the viewer shows it, else the root `README.md`, else `null`. It may name a LaTeX document, the research state's file, or any other entry of `files`. `corpus.directory` is the name of the directory the project is, its root's own name (`relloc` for a quilt at `~/quilts/relloc`), whatever `name` says; a viewer names what `files` lists a view of by it. Optional and additive.

**[decided]** **Files** (plan 0.22.7) are the project's files the viewer shows, one entry each, sorted by path: `{"path", "kind", "bytes", "body"?, "denied"}`. `path` is quilt-relative. `kind` says what a viewer does with it: `document` (a LaTeX document of `masters`), `tex` (any other `.tex` file, which a viewer opens as the document that reads it), `markdown`, `html`, `pdf`, `image`, `notebook`, `text` (UTF-8 up to 1 MB), or `other`. A publisher hides what the person would call noise, and loom hides a path with any segment starting with `.` (its own `.loom/` among them), tools' directories, the history and sync directories, and what the quilt's `.gitignore` files ignore. `body`, on a `markdown` or `notebook` entry, is the build-relative path of its rendered HTML (`files/<path>.html`): a Markdown file rendered as a page is, with an `id` on each heading and its relative links resolved (a link to a shown file becomes `quilt:PATH`, an image `/_files/PATH`), and the HTML it holds through the allowlist of specs/dialect.md §1; a notebook drawn from its saved cells, its Markdown cells as a Markdown file is, an HTML or script output by its plain form. A body is beside the manifest for the reason `source/` is. `denied` says whether agents may edit the file: `null` where they may, and on a file none may write `{"by", "always"}`, `by` being what keeps them out, the `[agents] deny` entry as written (`drafting/`) or the path loom protects (`config.toml`, the research state's file), and `always` true for a protection that holds whatever the list says. Loom answers it with the predicate its own commands ask, so a viewer never matches the list itself; an entry with no `denied` is from a publisher that does not say, and a viewer marks nothing for it. A viewer reads a file's bytes from the publisher at `/_files/PATH` (`write-api.md` §3). Optional and additive: a viewer that finds no `files` shows the documents alone.

**[decided]** **Notes** (plan 0.22.8), by id, are what someone wants kept beside a thing the viewer shows, a quote among them: `{"id", "when", "author": {"kind", "id"}, "session", "target", "body", "quote"?, "page"?, "rects"?, "kept"?, "mark"?, "strokes"?, "artifact"?, "origin"?, "erased"?, "hides"?, "faded", "detached"}`. `target` is one of `{"key"}` (a node, a region or a document), `{"work", "citekey"}` (a cited work: with `page`, one of its pages; without, the whole work, which a note says something about and quotes nothing of), `{"file"}` (a shown file, with `page` on a PDF), `{"message": {"session", "seq"}}` or `{"session"}`. `quote` is the words it quotes and `rects` where it is, each `[x0, y0, x1, y1]`, in points from a page's top left or in an image's pixels. A note has no kind, severity or resolution. `faded` is computed when the manifest is published: not `kept`, not a mark, older than 14 days, and linked from no annotation, message, page or kept note. `detached` says its words are no longer in what it is on. A viewer hides a faded note until asked, and draws a session's notes in its transcript by time.

**[decided]** **A mark** (plan 0.28) is a note drawn on a page of a PDF, a shown file or a cited work's copy. `mark` is how: `highlight`, `underline` or `strike` on words (`rects`, one per line), `pin` or `text` saying its `body` in its one rectangle, `box` or `oval` in its one rectangle, `ink` or `arrow` along its `strokes`, each stroke `x, y, x, y…` with `rects` the one rectangle round them all. `color` is the colour it was given, `yellow`, `green`, `blue`, `pink` or `purple`, and is absent on a neutral mark; what a colour means is its reader's. A mark's `session` is empty unless its writer named one, and it never fades. `artifact` is the hash of the PDF the note was written on, present on any note on a PDF's page. When the file's hash differs a note with a `quote` is found again on its page, and published with the `rects` found there; one that is not found, or that has no quote, is `detached`, and a viewer draws a detached note nowhere and lists it (A3). `origin` is where a mark taken in from a PDF came from, `{"by"?, "subtype", "color"?, "ref"?, "sha"?}`: its own author, annotation subtype and colour, and for one taken in from the file it is on, its reference in that file and the file's hash. `hides` is that reference while the file is still that one: a viewer leaves that annotation off the page, since the note stands for it. An erased note is published only while it `hides` something, carrying `erased`, the time; a viewer treats it as gone but goes on hiding the annotation. A plain note with `rects` on a page is drawn faintly, an underline for a quote and an outline for a region.

**[decided]** **Changes** (plan 0.22.8) are the open files changed since the reviewer's look, `[{"path", "kind": "changed"|"new"|"gone", "diff"?, "hash", "hunks", "blocks", "documents"}]`, with `diff` the build-relative path of a unified diff (`changes/<path>.diff`, three lines of context), `hash` the file's hash now (null for a gone file), which a keep or an undo sends back as `seen`, and `hunks` how many `@@` groups the diff holds, each kept or undone alone by its number from 0 (plan 0.25.1), `blocks` the keys of the statements and proofs each of those groups touches, by that number and in the file's order, empty for text outside any block, and `documents` the person's documents whose text the file is part of, empty for a file in none; `changes_since` is that look, `{"who", "when"}`, its time that of the reviewer's last look at every file. Both are absent before the reviewer's first look. A viewer offers keep and undo through the write API (`changes-keep`, `changes-undo`).

**[decided]** **Config** (plan 0.23) is what the quilt's configuration holds and what follows from it, for a viewer's Settings: `{"editable", "read_only", "quilt", "library", "lint", "agents", "sync", "warnings"}`. `quilt` is `{"name", "main", "home", "prefix", "engine", "history", "research_state"}`, `library` `{"online", "contact"}`, and `lint` `{"disable", "codes"}`, `codes` being every diagnostic code that can be silenced. `agents` is `{"deny", "protected", "layer", "variant", "stale", "command", "clients"}`: the deny list as loom accepted it; what is always protected, as the orientation names it; whether the quilt has an agent layer; how its agents reach loom, `"mcp"`, `"shell"` or null; whether Claude Code's permission file lags the list (`loom:agent-permissions-stale`); and per agent app with a file in the quilt, `{"key", "label", "file", "set_up", "command"}`. `sync` is `{"paired": true, "directory", "workspace", "branch", "documents"}` or `{"paired": false, "command"}`. `editable` and `read_only` are the `table.key` names a viewer may change through `settings-save` and the ones it shows only (`write-api.md`). `warnings` are the configuration's own. Each `command` is what a person runs for what the viewer cannot do, given here because a viewer names no command of its own; empty when there is nothing to run. Optional and additive: a viewer that finds no `config` shows its own preferences alone.

**[decided]** **Pages** (plan 0.21.3) are a reading loom keeps for one thing, which a person edits and an agent writes through the publisher, never a source. Each is `{"path", "hash", "body_html", "by": {"kind": "agent"|"person", "id"}, "when", "edited_since", "links": {"broken": [{"href", "why"}], "moved": [{"href", "key"}]}}`: `hash` the exact text's, `body_html` its Markdown rendered as a transcript message's (§10.1), `by` and `when` the last write through the publisher (absent when there was none), `edited_since` true when the text has changed since that write, `broken` the links that name nothing now and `moved` the linked results whose text has changed since the write. `research_state`, at the top level, is the quilt's; a work's is `references[CK].overview` (§13). Both are optional, and absent until one is written.

**[decided]** `reference_notes` lists works an agent proposed citing and a person accepted: `{"work": "…the work the suggestion named", "for": ["rl-0004"], "claim": "…the argument for citing it", "identifier": {"verified": false}, "accepted": {"when": "…", "who": "…"}, "from": {"session": "s-…", "annotation": "a-…"}}`. **[decided]** `work` is the work and `claim` is what the agent said it supports, in that order and not the other way round: a note whose `work` held the argument could never become a bibliography entry, which is the one thing the breadcrumb exists for (DR-170). It is a **breadcrumb and never a second source of identity truth**: `identifier.verified` is false until a person confirms it in the bibliography, and nothing here enters `references`, the bibliography, or any closure. A viewer shows them on the keys in `for`. Optional, like every other section.

**[decided]** Beside `manifest.json` and `fragments/`, a publisher may write **`source/<key>.tex`**: one file per key holding that key's own source text before macro expansion, which a viewer fetches lazily for a verbatim view. It is beside the manifest rather than inside it because the manifest is loaded whole on every poll and already runs to hundreds of kilobytes, while source is wanted one key at a time and only when a reader asks. Optional: a viewer that finds nothing there shows the rendered form and no toggle.

**[decided]** `publishes` is the read side's capability block, and it answers a question the data cannot: **what this corpus *has*, never what a viewer should draw.** Four booleans — `documents`, `review`, `bibliography`, `discussions` — each saying whether the corpus is the kind of thing that has one. `"documents": false` says this corpus is not assembled into documents; it does not say "hide the read view", and a viewer decides what to make of it, as `GET /_api`'s capability list works on the write side (`write-api.md` §1).

It exists because deriving the answer from emptiness cannot distinguish **empty because not yet** from **empty because never**. A quilt with no sessions yet would lose a view and get it back later, and since the manifest is re-polled every second the furniture would move while someone worked. A publisher declares once instead.

The values are properties of the publisher and its corpora, not of this corpus's current contents: loom writes all four `true` for every quilt, because a quilt with no documents yet is still a project that assembles into them.

**[decided]** **loom writes every top-level section**, an empty one as empty, and the viewer reads the manifest as written: it fills in nothing.

## 2. Masters and landmarks

**[decided]** `masters` lists the documents a reader may work in; `canon` lists the landmarks — documents as they stood at a recorded moment, fixed and never worked in — in the order the publisher recorded them, oldest first. A document the publisher considers superseded appears in neither. Loom builds one entry from each step that keeps a document's text, an import or a stamp given a document, and its `path` is that text's file in the step's directory.

```json
"canon": [
  {"path": ".loom/history/0002-paper-v1/paper-v1.tex", "stem": "paper-v1", "title": "Relative virtual localization",
   "fragment": "fragments/canon/paper-v1.html", "hash": "3f9a...",
   "step": "0002", "name": "paper-v1", "message": "Submitted to the Journal", "when": "2026-09-13T09:00:00Z",
   "in": "drafting/paper.tex", "macros": "canon:paper-v1"}
]
```

`path`, `stem`, `title` and `fragment` are required; the rest are present when the publisher knows them. `in` is the live document the landmark's step was about (the draft a stamp kept, the working document an import drafted), where the history's moves have taken it; it is absent when no live document leads to the landmark. `kept_for` names the act a version was kept at: `adopt` before an adoption, `sync` before incorporating or publishing a pull, `keep` when the author kept an edit in Changes, `undo` for the text an undo set aside, `restore` for the text a restore replaced, `apply` before a suggestion was written in; it is absent for a version the author recorded or imported. `message` says the act in the person's words ("Kept an edit", "Before taking changes from the copy “x”") or is the name the author gave. `action` is the step's (`import` or `stamp`), and `cannot_restore` why the version cannot be put back into its document (the paper as received, which has no ids; a version kept as one flat text of a document now of several files; a document no longer the person's), `""` when it can. `macros` names an entry of `macros.sets` (§14). A landmark's fragment carries no identity at all: no element in it has `data-id` or `data-key`, nothing in it appears in `nodes` or `keys`, and a viewer renders it as a document and nothing more.

`history` lists the history's steps, oldest first, and every line of it: `{steps: [{step, action, name, when, actor?, message?, document?, in?, landmark?}], acts: [{action, when, actor?, step?, path?, paths?, in?, landmark?, message?, hunks?, kept_for?, copy?, page?, from?, to?, version?, line?, done?}]}`. An act is any ledger line (`keep`, `undo`, `restore`, `apply`, `page-write`, `move`, `tick`, a step…); `in` is the document as it is now named, `from` and `to` a text's hash for the acts that set one aside or wrote one, `version` the landmark a restore put back, and `line` and `done` the source line and state of a box set in the viewer. `action` is `import`, `stamp`, `copy` or `adopt`; `document` is the document the step concerns as the ledger names it, and `in` that document where it is now, absent when it is no longer live; `landmark` is the path of the landmark the step kept, matching a `canon` entry's `path`. A step of the whole quilt (a `loom stamp` with no document) has no `document`.

## 2a. Masters

**[decided]**

```json
{
  "path": "drafting/main.tex",
  "title": "Relative virtual localization",
  "default": true,
  "fragment": "fragments/masters/drafting/main.html",
  "engine": "pdflatex",
  "compiled": "2026-09-16T14:39:10Z",
  "pdf": "drafting/main/main.pdf",
  "numbering_known": true
}
```

`compiled`, `pdf`, and `numbering_known` are absent or false before the first compile. `compiled` is the PDF's own time, so it changes with every compile that makes one, and a viewer that shows the PDF reads it again when it does. A document is named by its path without `.tex`, kept as a path: `fragment` is `fragments/masters/<name>.html` and `pdf` is `<name>/<stem>.pdf`, both under the build directory, so two documents that share a file name in two directories never share either; a viewer addresses a document by the same name. An agent's document is one that carries `copy_of`, the document it was copied from, where the history's moves have taken it; only one of the person's is the default, has a Review tab, or is selected by the document workspace, and the list holds the person's documents first. A viewer shows a copy beside the document `copy_of` names.

## 3. Nodes

`derived_of`, when present, marks an agent document's node: the plain key its derived id corresponds to (`"zk-0001"` for `zk-0001-ai`). Such a node also carries `base`, `{"key", "step", "hash", "math"}`, the version of its plain key it began from, unless the agent wrote it new; `math` is that version's hash as fragments' `data-hash` takes it (specs/dialect.md §2.4), so a viewer can tell a node changed on both sides since, and is absent when the version cannot be read. Such a node is in `nodes` and `keys` like any other, and in neither `tags` nor `search`; a viewer's whole-quilt views leave it out and a view scoped to its document shows it.

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

Rules: `kind` is `environment`, `section`, or `proof` (for labelled proof nodes); a section node also carries `"level"`, its sectioning depth (1 for `\section`, 2 for `\subsection`, and so on, shifted by any `\nest`), so a viewer can stop a contents list at a chosen depth; `numbers` and `parent` are per master; `reached_by` empty means loose; `external` true for cited-result blocks and digest nodes, with `digest` naming the citekey for the latter and `locator` present when available — carrying the page the result is printed on, `Proposition 2.1, p.~7`, wherever extraction could locate it in the work's filed copy (DR-224); `basis` on environment nodes is `expository`, `local-proof`, `cited-result`, `assumption`, `open-claim`, or `unclassified`, with `basis_reason` explaining the scan's choice or uncertainty; `inline_proof` is true when an explicitly `local-proof` remark or comment has its whole argument inside the block and no separate attached proof; `incomplete` lists the `\incomplete` texts in the node's statement; `state` and `derived` summarize the statement key (see 4); `children` lists included nodes in order for section nodes and nested environments.

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

Rules: `state` is one of the publisher's state labels (section 8); `acceptance` is absent when no row exists; `causes` appear only when `fresh` is false. A cause may carry `when` (first observation date), `via` (immediate dependency for an indirect cause), `citation` (an anchor in the dependent document), and `comparison` with `accepted`, `current`, `accepted_macros`, `accepted_spans`, and `current_spans`. The fragment paths resolve under the build directory; spans are source offsets in each normalized text. A cause may also carry `diff`, a unified diff path or null if unavailable. A cause of kind `document-gone` says the document the acceptance was recorded against is gone and no recorded move leads to a live document; its `id` is that document's last known path rather than a key, and its `diff` is null (DR-297-ikmartin). Viewers tolerate absent optional fields and draw an unfamiliar cause kind by its name. `previous_key_match` names an old positional key whose acceptance row matches this text (7.10 in the book), else null; `uses` lists direct dependencies; `closure` the transitive statement closure.

An optional top-level `incoming` object presents an external source revision for review without changing any key state. It has `workspace` (the URL of the sync directory's remote when the quilt was paired), `branch`, and the `base` and `commit` Git identifiers, `observed` (first fetch time), `files` (`status`, `path`, and optional text `diff` for TeX and bibliography inputs), optional `issues`, and `changes`. Each change has `key`, `kind` (`added`, `edited`, or `removed`), `local_changed`, `conflict` (both local and incoming edited the block differently from the base), `already_local`, optional local and incoming fragment paths, `incoming_macros`, and `affected` entries (`key`, optional citation anchor). Fragment paths resolve under the build directory. A viewer treats the section as prospective source, never as a mathematical acceptance or stale cause.

An optional top-level `unresolved` array lists every statement and proof of the person's (reached by one of their own documents, neither a digest's nor an agent copy's) that the selected reviewer has not freshly accepted, in dependency order. Each row has `key`; `cause`: `earlier-change` when its acceptance went stale, `adopted` or `incoming-pull` when it was taken in from an agent's copy or a pull, `never-accepted` when it has no acceptance; `pull`, the pull commit when applicable; `changed_text`; `local_changed`; `source_label`, where it was taken in from, in the person's words; and `refusal`, why loom cannot accept it (incomplete, a conjecture or question, its basis not said, a dependency it cannot identify), `""` when it can. For pull rows, `local_changed` is true when the block or its dependency context has changed locally since its post-pull baseline; null means no baseline was recorded; for every other row it is true. A block taken in and left unchecked stays listed even when an upstream acceptance makes its own fresh again. `review-accept` (write API) accepts only what this lists.

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
  "payload_html": "<div class=\"env env-lemma\" ...>...</div>",
  "placement": "after",
  "run": "s-2026-09-16-0001",
  "discarded": false,
  "discard_reason": null
}
```

`body_html` is the Markdown body rendered by the publisher as CommonMark with tables, raw HTML not passed through and alignment not carried, so a table is the dialect's (§2.12 of specs/dialect.md) and its cells hold inline markup and math.

**[decided]** `author.kind` is `agent` or `person` and `author.id` is the **name the writer declared**; `run` is the **session** the annotation belongs to, which is where it was written rather than who wrote it. The two were one field: an agent's annotation recorded its run directory as its author, so the log could say who only by naming a place (DR-199). The field keeps the name `run` because viewers read it by that name.

**[decided]** `target.key` is a key in the corpus, or — for a note on a page of a cited work (DR-209) — the work's identifier as `references[].work` spells it; `target.work` is then the citekey and `target.page` the page, so a viewer needs no lookup to say where the note is, and `basis` is `text` (the quotation locates in the page's committed text) or `box` (a drawn rectangle is the record). Both are null on a note on a key. The rectangles are in the work's sidecar (§13) under `marks`; the body is here, with every other annotation.

**[decided]** `in` is the document a claim about a node is read in, as a master path, or null for the node wherever it appears (plan 0.15, decision 9). It is published where the history's moves have taken the document, not as the record wrote it, so a viewer draws the annotation on the document as it is now; a document that is gone is published as written, and the annotation is `detached`. A `target.key` that is a master path is published the same way (DR-297-ikmartin). A viewer draws an annotation that names a document in that document only, lists it on the node's own page with the document named, and shows it in no other document; the publisher bakes its mark into that document's fragment alone. An annotation whose document no longer holds the node is `detached`.

**[decided]** `kind` is one of five — `objection`, `suggestion`, `question`, `citation`, `note`. The first four **await an answer** and are what an open count counts; `note` records rather than ask, and is where "this checks out" goes (DR-204; plan 0.15, decision 2).

## 9.1 Sessions

**[decided]** `sessions` lists every session the index leaves standing, for the viewer's selector.

```json
"sessions": [
  {"id": "s-2026-09-16-0001", "title": "referee pass", "state": "open",
   "created": "2026-09-16T14:02:00Z", "opened": "2026-09-16T14:02:00Z", "rounds": 1, "active": true,
   "seq": 4, "last": "2026-09-17T09:12:00Z"}
]
```

The **id** is minted once and is the address; the **title** is the author's and may change. `opened` is when the current round began, which is what "changed since last time" is measured from; `last` is when the session was last written in, the newest of its logged commands (§10), the annotations and notes written in it, and its transcript's last message, `""` when nothing was. `active` marks the session a command run at a terminal writes in; a viewer's writes name their own (specs/write-api.md). A tombstoned session is not published at all.

**[decided]** Three fields say how well the annotation is still attached, and they answer different questions. `detached` is false while the quoted text is still found in the target. `recorded` is false when the text the annotation was written against — the `target.hash`, taken over the key's own text with its children's places marked — is neither the target's current text nor a version the publisher kept, so a reader cannot be shown what was being objected to. Loom keeps every version a note is written against, so this is a version lost outside loom, or a paper on file that is not the one the note was written on; a fragment marks no unrecorded annotation, which is counted beside its key instead (DR-284-ikmartin). `anchored` is the conjunction a viewer draws a margin mark from: an annotation is anchored when it has a selector, that selector still resolves, and the version it names can still be produced. A publisher that keeps no versions reports `recorded: false` and `anchored: false` on everything it cannot show, which is the honest answer; it never reports `anchored: true` for an annotation whose subject it has lost.

**[decided]** `discard_reason` is the text given when the annotation was withdrawn, or null. Discarding is the one state change that carries a reason, because withdrawing a finding says the finding should not have been raised and the record is worth nothing without the why.

**[decided]** `severity` grades the fault a finding names — `major`, `moderate`, `minor` — and is null where the annotation names no fault. It is unrelated to a diagnostic's `severity`, which grades a message. `payload` is text a suggestion proposes, and `placement` says where it goes: `replace` takes exactly the quoted words' place, and `after` and `before` go right beside them; on a suggestion with no quote, they are of the key's body, its own text inside its environment's head (`\begin`, title, `\label`, leading `\uses`) and before its `\end`. An empty payload with `replace` deletes the quoted words. On a citation, `payload` is the work proposed. A viewer never applies a payload; the author does. `payload_html` is the payload as TeX makes it (the dialect, without element ids), made as a snippet under the preamble of the result the annotation is on, else of the default document, so a proposal that is a whole theorem and its proof reads as the document would print it; it is null where there is no payload or TeX refused it or made nothing of it, and a viewer then renders the TeX as prose.

**[decided]** An open suggestion carrying a payload has a `change`, its key as it would read with the suggestion taken, rendered at build so a static host shows it too:
- `{"state": "ready", "fragment", "diff", "moved"}`: `fragment` is the key with the payload in place, its changed words marked as Review marks them; `diff` is the patch that takes it, as `loom suggestion` prints it; both are paths under the build directory. `moved` is true when the key has changed since the suggestion was written, though the words it quotes still stand.
- `{"state": "taken"}`: the key already reads as the suggestion taken.
- `{"state": "unplaced", "why"}`: the payload has no place in the text now, said as the author is told: the quoted words no longer stand once, or there is no placement.

`resolved_why` is the text given when the annotation was resolved, or null. `applied` is `{"hash"}` on a suggestion resolved as applied: the hash of its key's own text once the suggestion was taken; null otherwise.

**[decided]** `run` is the id of the session the annotation belongs to, and is the key a viewer groups by.

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
    {"name": "orbit-counts.py", "kind": "file", "path": ".loom/sessions/s-2026-09-16-0002/orbit-counts.py"},
    {"name": "annotations", "kind": "annotations", "count": 3}
  ],
  "log": [{"time": "...", "command": "loom source rl-0004 --closure", "names": [{"key": "rl-0004"}]},
          {"time": "...", "command": "loom annotate rl-0004 --quote --kind objection", "annotation": "a-2026-09-16-0001"}],
  "discarded": false
}
```

A thread carries no conversation: that is its transcript (§10.1). `log` comes from `run.log`, one entry per line; `annotation` is the annotation a `loom annotate` line made or changed, written after an arrow in the log, and absent on every other line. `names` lists the keys (`{key}`) and files (`{path}`) a line's command names, each once, a document under where the history's moves have taken it; a word naming nothing in the quilt is left out, nothing is read from the command's verb, and the field is absent when the line names nothing. As published by loom (M6): every session is a thread of `kind` `session` with `path` (the session directory), `title` the session's title, `participants` from the annotations' authors, `targets` from the annotations, `attachments` named by file with kinds `annotations` (with `count`), `draft`, `proposal`, `digest`, `plan`, `notes`, `script`, or `file`. Each thread also has a `search` entry with `kind` `thread`.

## 10.1 Transcripts

**[decided]** A session's conversation is published beside the manifest, never in it, because every viewer polls the manifest and a long conversation would make every poll pay for it. The build writes `transcripts/<session>/<n>.json`, page `n` (from 1) holding the events numbered `100(n-1)+1` to `100n`:

```json
{"session": "s-2026-09-17-0002", "page": 1, "events": [
  {"seq": 1, "kind": "message", "who": "A. Author", "when": "2026-09-17T11:00:00Z",
   "body": "Have a look at Theorem 3.2.", "body_html": "<p>Have a look at Theorem 3.2.</p>",
   "changed": [{"id": "a-2026-09-17-0001", "kind": "question", "target": "Bellamy19-thm-3.2", "act": "created", "by": "A. Author", "body": "…"}]}
]}
```

The session's `seq` in `sessions` is the last event's number, so a viewer knows which pages exist without an index. `body` is what was written and `body_html` its rendering, by the same rules as an annotation's body, except that a report's blocks — each `## [NAME]` heading an agent wrote and what follows it — are each a `<section data-block="NAME">` headed by the name without its brackets, which a viewer may fold after the first (specs/dialect.md §2.1); `changed` lists the annotations a message carried, each whole: `id`, `kind`, `target`, `work` and `page` for a note on a page, `act` (`created` or `replied`), `by`, `body`, and `quote`, `severity`, `payload` and `placement` where the annotation has them. A publisher that serves live answers the pages itself, from the inbox, so they are never stale under it, and adds new events through its own channel (specs/write-api.md; DR-278-ikmartin).

## 11. Diagnostics

**[decided]** See `diagnostics.md` for codes.

```json
{"severity": "error", "code": "double-inclusion",
 "message": "rl-0011 is included twice in drafting/main.tex (via rl-0020 and via rl-0031)",
 "locations": [{"file": "nodes/rl-0020.tex", "line": 14}, {"file": "nodes/rl-0031.tex", "line": 3}],
 "keys": ["rl-0011", "rl-0020", "rl-0031"]}
```

**[decided]** Three optional fields. `subject` says what the diagnostic is about: `"source"` (the default when absent) or `"record"`, the publisher's own account of the source. `owner` says whose it is to put right: `"person"` (the default when absent), `"copy"` for an agent's copy, or `"work"` for a cited work's digest (plan 0.25.3; `diagnostics.md` §1 says how each is decided, and governs). `fixes` is a list of commands that would resolve it, each `{"label": "...", "command": "..."}`, with `"act": {"endpoint", "body"}` on one a viewer may do itself through the write API; a viewer copies any other, and runs no command. Loom stamps `owner` once over the whole list, lint's, the renderer's and the records' alike, so `loom lint --json` says the same.

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
  "digest": {"file": ".loom/digests/Man12.tex", "fragment": "fragments/digests/Man12.html",
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

**[decided]** `work` is the work's global identifier and `works` every identifier its bibliography entry states, each written `scheme:value` with the scheme one of `doi`, `arxiv`, `mr`, `zbl`, or `work` (a deterministic hash of author, title and year, for an entry stating none). `artifacts.dir` is the address of what loom holds for the work, `digests/storage/<scheme>/<id>` under the viewer's root, which a publisher serves from its store wherever that sits (DR-192), and the two flags say which of the source and the PDF are present; both are false until someone fetches, adds or drops a copy, and neither the PDF nor the source is in version control, so another reader's copy of the corpus may have neither. `digest.extracted_from` and `digest.published_as` distinguish the artifact whose numbering the digest carries from the work the bibliography cites; `digest.source` repeats `extracted_from` and is retained for readers written before 0.5.

**[decided]** `spans` points at a **sidecar** holding the geometry of the work's anchors: `{"artifact": <sha256>, "pages": {"2": {"width": 612, "height": 792, "rotate": 0}}, "quads": {"<result id>": [[x0, y0, x1, y1], …]}, "marks": {"<annotation id>": [[x0, y0, x1, y1], …]}}`, one rectangle per line — `quads` for the work's results by result id, `marks` for the notes on its pages by annotation id (DR-209). `rotate` is the page's own rotation in degrees, read from the document. `reading` on the reference counts those notes, and how many still await an answer, since they are in no key's row. It stands **beside** the manifest rather than inside it, for the reason `source` does: the manifest is loaded whole on every poll and geometry is wanted for the one paper being read. The pointer carries the sidecar's own hash, so a stale copy is noticed while the publisher rebuilds underneath. **Quads are derived and never recorded for a text anchor**: an anchor says where it is in the page's text, and the rectangles are computed from the word boxes at build time; a box anchor's rectangles are the anchor itself and are recorded. A work whose PDF is not on the publishing machine gets no sidecar, and the viewer has nothing to draw, which is the honest state.

**[decided]** **Coordinates are points with a top-left origin** — what `pdftotext -bbox-layout` emits — and never PDF user space, whose origin is at the bottom left. A viewer that hands these to a renderer's own transform draws every highlight mirrored about the middle of the page.

**[decided]** `overview`, present only where one has been written, is the work's overview, a page (§1): a reading of the paper, never the paper, kept beside the work's page text in the store. A digest's own `\\section*{Overview}` is the paper's opening paragraphs, copied at extraction, and is a different thing.

**[decided]** `added`, present only on a work the person added to the library by hand (plan 0.24.2), is `{"when": …, "who": …}`, read from the entry's `loom-added` field in loom's bibliography. Such a work need not be cited by anything, and its `cited_by` may be empty; it is a work of the library like any other.

**[decided]** `bibtex` is the work's bibliography entry as a person pastes it into a `.bib` (plan 0.24.4): its entry type and its bibliographic fields (author, title, year, journal, booktitle, publisher, volume, number, pages, doi, eprint, archiveprefix, zbl, mrnumber, isbn, url), never the publisher's own `loom-*` fields nor a field such as `file` or `abstract` that names a local file or carries notes. `bib` stays the few fields a viewer reads.

**[decided]** `unreadable`, present only where the author has declared one, is `{"why": …, "who": …, "when": …}`: the standing claim that the work has no document to hold at all. Nothing in a bibliography entry says so, which is why it is declared and never inferred, and a viewer says it rather than showing an empty pane (DR-198).

**[decided]** `proposed`, null when the work has none, is `{"file": …, "fragment": …, "nodes": [...]}` for the work's proposals: results an agent read off a page that nobody has vouched for yet. They live in `.loom/digests/<citekey>.proposed.tex`, which nothing inputs, so their nodes are in no bundle and no closure and can be neither cited nor compiled; a viewer shows them among the digest's nodes, flagged (DR-178). Their `fragment` is a page of its own, `fragments/digests/<citekey>.proposed.html`, never the digest's.

**[decided]** `results`, by result id, is what `.loom/digests/<citekey>.results.json` records for each of the work's results (`digests.md`), as a viewer needs it:

```json
"Man12-thm-4.1": {"state": "extracted", "level": 3, "class": "mechanical", "page": 12, "artifact": "4b8db624054b",
                  "origin": [{"act": "extracted", "by": "loom library update", "when": "2026-09-16T00:00:00Z"}],
                  "version": {"extracted_from": "arXiv:0805.2065v2", "cited": "doi:10.1090/S1056-3911-2011-00606-1"}}
```

- `state` is one of `proposed` (written, not yet vouched for), `extracted` (loom's own reading of the paper's source, which no person has vouched for), `verified` (a person compared the rendering with the source text and accepted it) and `discarded`. It is derived when the manifest is written, not copied from the record: a `mechanical` result is `verified` only once its `origin` carries a person's `verified` or `edited` act, and `extracted` otherwise (DR-332-ikmartin).
- `level` is 1 for a main result and deeper for the rest; `class` is `mechanical` (parsed from a source), `anchored` (read off a page, re-checkable) or `declared` (no check available).
- `page` is the page the statement was read from, 0 for a result read out of LaTeX; `artifact` is the first twelve characters of the sha256 of the document the anchor names.
- `origin` lists every party who made or changed the result, in order, each `{"act", "by", "when"}`.
- `source_text`, the page's own words, is present for every result that is not `mechanical`; a mechanical result's source is its own LaTeX, already in the digest's fragment. `source_file` is present for one quoted from the paper's LaTeX rather than a page.
- `statement`, `local`, `taxon`, `page_text` (the page around the quoted span), `not_on_page` (prose words of the statement found nowhere in `page_text`, or in the quotation when the page round it was not found; a viewer marks them in the rendering) and `supersedes` are present only on a `proposed` result: it is the one claim a person is being asked to make, and the surface that offers it must show both texts.
- `version`, present only on a `mechanical` result whose digest was read off another version than the one the bibliography cites, is `{"extracted_from", "cited"}`: the artifact extracted (`''` when the digest does not say) and the identifier the bibliography cites, which is a `work:` identifier when the entry states none and the source was a preprint a lookup found. Its numbers and pages are then the other version's.

A viewer that knows only `proposed` reads every other state as settled, so `extracted` and `version` change nothing it already draws.

**[decided]** `versions`, present only on a work that has other versions, lists them, each `{"citekey", "work", "artifacts"}` as the version's own reference carries them; `version_of`, present only on a version, is the citekey of its work. A version is a reference of its own as well, so a viewer that knows neither field still shows every document; one that knows them shows a work once, with its versions under it (DR-332-ikmartin). Both are additive.

**[decided]** `candidates`, present only on a reference whose bibliography entry states no identifier and only once a lookup has run, lists identifiers a lookup proposed, best first: `{"id": "doi:10.1353/ajm.1998.0020", "source": "zbMATH Open", "confidence": 1.0, "strength": "strong", "title": "…"}`. They are unconfirmed and never the reference's `work`, which changes only when the bibliography states the identifier. A viewer may show them, marked as unconfirmed.

## 14. Macros

**[decided]** Each macro is `{"name": "Res", "args": 0, "body": "\\mathrm{Res}"}`. `macros.default` is the preamble closure's set; `macros.sets` holds per-fragment sets named in fragments' `data-macros`.

## 15. Search

**[decided]** Entries for the viewer's search box: `{"key": "rl-0004", "title": "...", "taxon": "Lemma", "aliases": [...], "tags": [...], "excerpt": "..."}` for every node and every digest node; masters, landmarks and threads have entries with `kind` (`master`, `canon`, `thread`).

## 16. Relations

**[decided]** Links between nodes that are not dependencies. A relation enters no closure, no closure document, no acceptance row and no staleness computation; it exists so that a viewer can show two nodes as related. `\uses` remains the only way to declare a dependency the text does not name.

```json
"relations": [
  {"from": "rl-0071", "to": "rl-0004", "kind": "see",
   "src": {"file": "nodes/rl-0071.tex", "line": 1}}
]
```

`from` is the node that declared the relation, so the declaring side is known; display is symmetric and a viewer shows the relation on both nodes. `kind` is `see` in this version. Adding a kind is a decision-record event, and a viewer renders a kind it does not know as a labelled list of links. Nodes gain no field: a viewer derives per-node lists from this one.


## Personal review metadata

`reviewer?: {name: string, source: string}` identifies the build perspective; empty name means no local identity. `keys[K].acceptance` remains the selected reviewer's acceptance, and optional `keys[K].acceptances` lists each author's latest `{author, date, fresh}` for author-owned blocks. Each summary uses the same freshness rules, without writing another reviewer's caches. External verification retains shared acceptance semantics. Nodes, derived states, counts and unresolved rows all use the selected perspective; structural incompleteness and errors remain independent.

Unknown metadata remains optional for backward compatibility. Static viewers label the named perspective once; when absent, they show an unspecified perspective only if acceptance information exists.

## Incoming contribution inventory

`contributions` is an optional array of incoming sources. The existing optional `incoming` workspace-pull object remains available for compatible clients. Its inventory entry has `kind: "workspace"` and a readable `label`, plus the existing pull fields. AI entries have `kind: "adopt"`, `copy`, `source`, `label`, a comparison `fingerprint`, `issues`, `changes`, `document_changed`, `document_conflict`, `document_diff`, and `choices: {keys, document}` for the displayed reviewer. Each change carries `class`: `new`, `proposal-only`, `removed`, `separate-result`, `merged` (the person and the copy both changed it and the edits fall apart line by line; `merged` is the text that would be written, and its `incoming` fragment draws it), or `conflict` (their edits clash: published so the viewer can say why, never offered). `proposed_key` is the copy's own key for the result (`zk-0001-ai`), which names it as the copy has it; `math_changed` ignores the `% !LOOM` lines a result opens with (plan 0.25.2). An unreadable AI contribution carries its copy, label, empty changes and issues; clients must not offer writes for it.

Each AI change contains `key`, `name`, `class`, `current`, `proposed`, `base`, `offered`, `math_changed`, `documents`, nullable rendered-fragment paths `local` and `incoming`, and `affected: [{key, citation}]`. Classes distinguish unchanged, identical, author-only, proposal-only, conflict, new, removed and separate-result; only offered rows are published. The document diff uses node placeholders to distinguish prose and ordering from node bodies. The preview endpoint returns the final patch restoring actual source representation.

An unresolved row taken in from a copy has `cause: "adopted"` and `contribution` (the agent document's path); `pull` carries a pull's commit, and for adoption the internal provenance identifier. Neither inventory entries nor unresolved rows imply mathematical acceptance.

## Precise review evidence (DR-314-luisa)

`keys[K].review_macros?: string`, cause `current_macros`, and comparison `current_macros` select the current document’s macro set. Cause `current_fragment` provides current dependency evidence even when no historical comparison exists. `keys[K].review_fragment?: string` renders the current acceptance unit without attached proofs. Causes may carry stable `identity`, readable `label`, and structural `owner`; equation cause IDs use `equation:<label>`. `dependency-baseline-unavailable` means no exact historical display was recovered, while `dependency-scope-unavailable` means the current full display is unsupported. Existing structural `uses`, `closure`, regions and edges retain their navigation contract; mathematical acceptance uses the publisher's separate versioned dependency context.

Incoming may carry `affected: string[]`, the mathematical keys whose context changes across the fetched revision, including display or preamble edits outside mathematical blocks. This prospective list supplies post-incorporation provenance without making prose rows acceptance keys. Incoming changes may carry `category: "prose"`, a readable `name`, and `current`/`proposed` source fallbacks. These are inspection rows, not acceptance keys. AI `choices` may include `kept: string[]` to distinguish an explicit Keep current from no selection. `document_comparison` optionally carries `local`, `incoming`, `incoming_macros`, `current` and `proposed` for the single prose/document group; `document_diff` remains the exact source-level disclosure.

## Scoped and closed AI drafts (DR-323-luisa)

An AI master may carry `scope: {kind: "section", key, title, level, keys}`, `scope_keys` (canonical labels in its baseline and current source subtree), `context_when`, `context_changed`, `context_document` and `macros`. The source `copy_of` remains the whole paper. Compare filters that source to the scope and the draft's own pairs. A `context_only` master is a saved paper view, outside the active-document inventory. Scoped node fragments may name `draft_macros`; external reference links carry `data-context-document` and `data-context-anchor` and open the saved context instead of current definitions.

A closed master keeps its original path with `closed: true`, `closed_at`, a frozen `fragment`, `macros`, `closed_keys` and `closed_annotations`. It defines no live nodes and offers no annotation or incorporation tools. These entries belong in a collapsed Closed AI drafts list; their node keys resolve to that saved document. Saved contexts and closed fragments render standalone.

Adoption contributions may carry `scope`, `preamble_changed`, `preamble_conflict`, `preamble_current` and `preamble_proposed`. Their choices include independent `document` and `preamble` booleans and a monotonically increasing `revision`; `invalidated` lists affected previous decisions. Proposed edits and the preview's affected-mathematics queue are separate stages. A mathematics item's `dependencies` lists the changed support that explains its review reason; unchanged dependent text is not another AI source proposal.
