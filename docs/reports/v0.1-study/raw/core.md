# v0.1 study: the Python core (`loom/src/loom/`)

Auditor: core architecture. Checkout: `.claude/worktrees/v01-study` at 71621877. Paths below are relative to `loom/src/loom/` unless they start with `docs/` or `demos/`. Measurements were taken with the repository's venv Python against this worktree's source, `HOME` and `XDG_CONFIG_HOME` in scratch, on a scratch copy of `demos/showcase`.

Weights: **blocks** (v0.1 cannot ship to the testers with it), **hurts** (they will feel it, or it slows the author's next two weeks), **cosmetic**, **irrelevant**. Effort: hours / a day / days / a week+. Recommendation: fix / hide / remove / defer / keep.

## Summary of findings

| id | finding | weight | effort | rec |
|---|---|---|---|---|
| CORE-1 | Domain logic lives in the CLI package; 21 non-CLI modules import `loom.cli`, including the HTTP API reaching into `cli/review.py` privates | hurts | a day | fix |
| CORE-2 | Layering is held together by 682 function-local imports (45% of all loom imports), which hide real cycles | hurts | days | fix (gradually) |
| CORE-3 | "Three surfaces over one set of operations" is true only for MCP=CLI; HTTP is a hand-written 289-line dispatcher with its own guards and side effects; several operations exist on one surface only | blocks (for the stated bar) | days | fix |
| CORE-4 | MCP tools are generated from click commands and run as a subprocess per call with a full rescan | hurts | days | fix after v0.1 (keep the generation) |
| CORE-5 | Keeping a suggested edit writes the file, then records it, in two steps; idempotence rests on a text-similarity heuristic while the `apply` ledger line it writes is never read | blocks | hours | fix |
| CORE-6 | Writes to the person's files: 15 code paths; most keep a version first, but `keep_versions` silently skips undatable documents and proceeds; `config.toml` writes keep nothing | hurts | hours | fix |
| CORE-7 | No quilt format version; `loom upgrade` migrates no record; one record silently resets on an unknown schema | hurts | hours | fix |
| CORE-8 | Same verb, different operations across surfaces (`restore`, `import`, `accept`); help text still says "loom never edits" the file | hurts | hours | fix |
| CORE-9 | Agent-copy (adoption) workflow is a second channel for AI-proposed edits beside suggested edits: ~2,900 lines in 45 files | hurts | days | hide now, remove after |
| CORE-10 | Atomized-node workbench commands (atomize, fork, live, mv, linearize, deloom, id, revert, history restore, new, import): ~3,000 lines serving no v0.1 task | hurts | hours (hide) | hide |
| CORE-11 | Git workspace sync (Overleaf git): ~1,700 lines | irrelevant unless the Overleaf tester uses Overleaf's git | hours (hide) | defer |
| CORE-12 | Session transcripts (`session say`, inbox, threads, transcript pages for a "viewer with no publisher"): ~650 lines | cosmetic | a day | remove |
| CORE-13 | Small dead code: `records/edits.apply`, a registered-but-never-emitted diagnostic, five unreferenced defs, legacy line shims, GEMINI.md | cosmetic | hours | remove |
| CORE-14 | Hotspots: 14 files over 800 lines, 15 functions over 150; complexity is concentrated in accidental places (CLI review module, API dispatcher, Records god object, manifest builder, lint monolith) | hurts | a week+ | fix after v0.1 |
| CORE-15 | Diagnostics: 74 codes; about 10 report a LaTeX problem any author would recognise, ~46 are loom-model hygiene, ~18 are loom's own difficulty or record integrity | blocks (Problems page) | a day | fix |
| CORE-16 | Extension costs 4–12 files per feature, and only the diagnostic recipe is written down | hurts | hours (doc) | fix |
| CORE-17 | Readability: strict mypy passes and 99.6% of functions are annotated, but 422 `dict[str, Any]`, docstrings that narrate history, 41 frozen `DR-` refs, 61 private cross-module imports, overloaded vocabulary | hurts | a day+ | fix after v0.1 |
| CORE-18 | Slowness is architectural: no persistent scan, 1–3 rescans per write, a full manifest rebuild after almost every write | hurts (relloc) | days | fix |

## 1. Module map and layering

### Packages and sizes (56,969 lines, 195 files)

| package | files | lines | responsibility | imports from siblings (module level / in functions) |
|---|---|---|---|---|
| `cli/` | 39 | 13,327 | click commands, report rendering, error types, identity, and a large share of the domain logic (`cli/review.py` 2,136) | scan 38, paths 15, records 13, reshape 13, history 8, tex 6, render 5 / refs 44, records 23, scan 20, render 10, ai 7, history 5, mcp 4 and 20 top-level modules |
| `render/` | 27 | 10,456 | "publisher": TeX4ht HTML to fragments (`fromhtml.py` 1,258), manifest (`manifest.py` 861), build, HTTP server (`serve.py` 964) and write API (`api.py` 1,301), six comparison/diff renderers | scan 61, tex 17, records 13, paths 10, refs 5, history 4 / refs 24, scan 15, records 9, history 7, **cli 5** and 17 top-level modules |
| `refs/` | 19 | 6,964 | the library: bibliography, fetch, PDF page text, identification, results and proposals, digest build, search, links | scan 25, paths 8, clock 5, **cli 2** / scan 11, **cli 8**, digest 2 |
| `scan/` | 25 | 5,367 | TeX scanner: files, nodes, labels, edges, preamble, macros, lint, quilt config, diagnostics registry | history 1, refs 2, paths 8 / **refs 9**, history 3, records 1, ai 1 |
| `records/` | 16 | 4,716 | annotation log, suggested-edit log, acceptance ledger, marks, types, snapshots, carry; `store.py` (1,258) is the `Records` facade | scan 17, paths 7, **render 1** (`store.py:26`), history 1 / refs 8, render 4, cli 1 |
| `tex/` | 8 | 1,803 | latexmk runner, TeX4ht, source–render alignment | scan 7 / reshape 2, render 1 |
| `reshape/` | 10 | 1,524 | atomize, fork, linearize, deloom, import, id insertion, anchoring | scan 25, paths 5, history 4 / render 1, top-level 4 |
| `history/` | 6 | 1,209 | ledger, stamps (versions), acts (keep_versions, restore), checks | scan 9, render 2 / records 2, **cli 1** |
| `digest/` | 4 | 1,008 | extract a digest of results from a paper's TeX | scan 17, tex 2 / refs 3 |
| `mcp/` | 6 | 956 | MCP server over the CLI | ai 2, scan 2 / ai 4, cli 2 |
| `ai/` | 4 | 865 | agent layer files, permission files, client configs, orientation | scan 3, records 2 / **cli 3**, agents 2 |
| top level | 31 | 8,774 | operations that fit nowhere else: `adopt.py` 1,133, `sync.py` 1,079, `doctor.py` 706, `pending.py` 682, `files.py` 505, `config_edit.py` 475, `mailbox.py` 459, `since.py` 416, `section_drafts.py` 344, `sessions.py` 303, `review_queue.py` 243, `links.py` 231, `agents.py` 202, `draft_lifecycle.py` 198, `incorporation_review.py` 197, `raw_html.py` 182, `looks.py` 177, `jobs.py` 172, `pages.py` 166, `locks.py` 149, `tasks.py` 144, `drafts.py` 140, `arras_bundle.py` 120, `paths.py` 104, … | mixed |

(Counts from an AST walk of every `import`; scratch script `imports.py`. "/" separates module-level from function-local imports.)

### CORE-1: the CLI package is a domain layer that everything imports

The intended layering is `paths/clock/locks → scan → tex/history/records/refs → render/reshape/top-level operations → cli → mcp`. What exists instead: error types (`EnvError`, `ContentError`, `NotFoundError`), identity (`is_agent`, `whoever`, `writer`, `refuse_under_agent`) and the report machinery live in `cli/_common.py` and `cli/report.py`, and core operations live in `cli/review.py`. 21 non-CLI modules import from `loom.cli`:

- `render/api.py` imports CLI privates in 7 handlers: `_annotator`, `_one_comment`, `edit_annotation`, `delete_annotation` (`render/api.py:410, 988, 1183, 1271`).
- `incorporation_review.py:11` imports `_acceptance_master, _owned` from `loom.cli.review` at module level; `review_queue.py:72, 94, 182` import `_owned`, `write_acceptance`.
- `ai/orient.py:196-219` imports `status_payload`, `agent_line` from `cli/review.py` and `tally` from `cli/diagnostics.py`; `refs/build.py:22-900` and `refs/scan.py:30` import `cli/report.py`; `refs/update.py:16-77` imports `cli/library/_works.py` and `cli/library/state.py`; `refs/proposals.py:526` imports `write_acceptance`; `records/marks.py:641` imports `_work_target`; `history/steps.py:136` and `locks.py:77` import `EnvError`; `since.py:325` imports `_cause_words`.
- The full diagnostic list a viewer shows is assembled in `cli/lint_cmd.py:48` (`all_diagnostics`) and imported back by `cli/library/upkeep.py:121`.
- The key hash, a scan-level primitive, lives in the publisher: `render/manifest.py` `key_hash`, `own_text`, imported at module level by `records/store.py:26` and by `cli/suggest.py:73`.

Weight: hurts. Every new operation has no obvious home, and a viewer change routinely edits a click module. Effort: a day for the mechanical move (errors + identity into `loom/errors.py` and `loom/identity.py`; annotation and acceptance operations into `records/`; `key_hash` into `scan/`). Rec: fix, before v0.1, because CORE-3 builds on it.

### CORE-2: cycles hidden by function-local imports

682 of 1,518 intra-loom imports (45%) sit inside functions; 1,040 indented `from loom…` lines in all. Real cycles they mask: `records ↔ render` (`records/store.py:26` imports `render.manifest`; render imports records 13 times), `scan ↔ refs` (`scan/lint.py:12-13` imports `refs.identity` and `refs.resolve`; refs imports scan 25 times), `cli ↔ render`, `cli ↔ refs`, `cli ↔ ai`, `history ↔ records`. Consequences: the dependency graph is invisible at the top of a file, an import error appears only on the code path that triggers it, and `render/api.py:1180` carries a comment explaining a local import as a start-up optimisation, which makes the two reasons indistinguishable. Weight: hurts. Effort: days, falling out of CORE-1 and CORE-3. Rec: fix gradually; add an import-linter style check once CORE-1 lands.

## 2. Three surfaces over one set of operations

### How each surface is built

- **CLI**: 77 leaf commands (click), none hidden. Each command validates its own options, often holds the operation's logic inline, and prints through `cli/report.Report`.
- **MCP**: generated from the CLI. `mcp/tools.py:97-101` takes `AGENT_COMMANDS - NOT_TOOLS` (`ai/layout.py:22-38`; 42 tools), builds a JSON schema from each command's click parameters (`mcp/tools.py:120-171`), and turns a call back into an argv (`mcp/tools.py:210-245`). `mcp/server.py:198-204` runs every call as `python -m loom <argv>` in a subprocess with `AI_AGENT=1`. Author-only options are subtracted by a hand list (`AUTHOR_OPTIONS`, `ai/layout.py:62-64`, only `changes`). Tool hints come from a second hand table (`ACTS`, `ai/layout.py:40-58`).
- **HTTP**: hand-written. `render/api.py:21-70` lists 47 capabilities; `handle` (`render/api.py:694-982`, 289 lines) is an if-chain that dispatches to 20 helpers or does the work inline (the `adopt-*` and `review-accept` branches contain business logic, including patching `manifest.json` in place at `render/api.py:878-891`). Each handler re-implements request validation, the author guard (`is_agent` on a declared name: 14 calls) and error mapping (one `ApiError` mapped from about twelve exception classes: `PendingRefused`, `EditRefused`, `RestoreRefused`, `TickRefused`, `MarkRefused`, `TypesRefused`, `ConfigRefused`, `NotDeletable`, `NotIgnorable`, `SyncError`, the three CLI errors). The CLI guards differently: `refuse_under_agent` checks the `AI_AGENT` marker as well as the name (`cli/_common.py:325-335`, 13 call sites).

### Trace of a dozen operations

| operation | CLI | MCP | HTTP | one function? |
|---|---|---|---|---|
| annotate (and note: notes are annotations since f68df874) | `annotate`, `cli/review.py:1113` → `_one_comment` `cli/review.py:429` | `loom_annotate` (subprocess of the CLI) | `annotate` → `_review` `render/api.py:1179` → same `_one_comment` | yes, but the core is a private function in a click module |
| suggest | `suggest`, `cli/suggest.py:15-140`: all validation and event construction inline in the click function | `loom_suggest` | **none** | CLI only; the viewer cannot suggest |
| accept | `accept`, `cli/review.py:172` (200-line command) → `write_acceptance` `cli/review.py:87` | none (author's) | `review-accept`, `render/api.py:927-981` → `review_queue.accept` `review_queue.py:177` → `write_acceptance` | shared core, **different behaviour**: HTTP requires a current built manifest (`review_queue.py:184`) and additionally folds accepted blocks into the look and stamps versions (`render/api.py:961-972`, `pending.keep_accepted`); `loom accept` does neither (`keep_accepted` has no other caller) |
| keep / discard a suggested edit | `changes --keep/--discard`, `cli/changes_cmd.py:62-99` → `pending.keep/discard` | excluded by `AUTHOR_OPTIONS` | `change-keep/discard`, `render/api.py:407-453` → `pending.keep/discard` | yes |
| undo a keep or discard | none | none | `change-discard` with `undo`, `render/api.py:463-482` (`_reopen`) | HTTP only |
| add a work to the library | `library add FILE`, `cli/library/add.py:69-232` (164-line orchestration of `identify`, `plan_new_work`, `plan_filing`, `file_document`) | excluded | `library-add/upload/file`, `render/api.py:157-275` → `refs/add.file_new`, `file_under` | two orchestrations over shared primitives; behaviour can drift |
| stamp | `stamp`, `cli/history_cmds.py:230` → `history/steps.stamp_document` | none | `history-record`, `render/api.py:532-551` → `stamp_document`, with its own name checks | core shared, validation duplicated |
| restore a version | `history restore` = start a **new** document from a landmark (`cli/history_cmds.py:1041-1108`); `revert` prints a patch (`cli/history_cmds.py:451-488`) | none | `history-restore` puts a version back **into** the document, `render/api.py:507-563` → `history/acts.restore` | three operations, one name; in-place restore is HTTP only |
| save settings | none (edit `config.toml` by hand) | none | `settings-save`, `render/api.py:591-638` → `config_edit.save`, plus a look taken when tracking turns on (`render/api.py:632-636`) | HTTP only; hand edits skip the side effect |
| init a quilt | `init`, `cli/quilt.py` | none | none | CLI only: a person must type `loom init` |
| sync fetch | `sync fetch`, `cli/sync.py` | none | none (only `sync-preview`, `sync-incorporate`) | CLI only |
| tick a task | none | none | `file-tick`, `render/api.py:485-504` → `tasks.tick` `tasks.py:105` | HTTP only |
| new session | `session new` → `sessions.create` | `loom_session_new` | `session-new`, `render/api.py:1095-1100` → `sessions.create` | yes |

HTTP-only besides those: `types-save`, `pdf-save`, `annotations-take`, `library-recognise/lookup/delete`, `session-purpose`, `restore` (undo an annotation delete), `edit`/`delete` with geometry. CLI-only author acts: `init`, `stamp` quilt-wide, `import`, all of `sync`, the workbench commands (CORE-10), `ai init`, `upgrade`.

### CORE-3: the stated bar is not true by construction

Weight: blocks the bar ("CLI, MCP tools and the HTTP write API are three surfaces over one set of operations"), and causes real divergence today (accept). Effort: days for the operations the viewer uses; a week+ for all.

Smallest refactor that makes it true by construction:

1. CORE-1's move (errors, identity, annotation and acceptance operations out of `cli/`).
2. An `ops` registry: each operation is one plain function `op(ctx, **typed_params) -> dict` under a decorator carrying `name`, `actor` (author / agent / any), `acts` (read / derive / write / replace) and `network`. `ctx` holds the root, a cached scan provider (the server's `offer_scan`, `render/api.py:97`) and the writer. One exception type `OpRefused(code, message, status)` replaces the dozen.
3. HTTP: one generic `POST /_api/<op>` that validates the JSON body against the function signature and applies the actor guard from the decorator; `handle` and its 20 helpers go. `CAPABILITIES`, `READS`, `NO_REBUILD` become decorator fields.
4. MCP: tools from the same registry, called in-process (schemas from type hints; descriptions written for an agent rather than for a shell). `AGENT_COMMANDS`, `ACTS`, `AUTHOR_OPTIONS` (`ai/layout.py:22-64`) become decorator fields; the permission files are still generated from them.
5. CLI: each click command becomes params → op → `Report`.

Do steps 1–3 for the write operations the viewer uses (annotate, edit, delete, keep, discard, accept, restore, record, tick, settings, sessions, library add) before v0.1; the rest after.

### CORE-4: MCP generated from click, run as subprocesses

Benefit: zero drift between CLI and MCP, and the K5 agent guard applies to every call through `AI_AGENT=1` (`mcp/server.py:202`). Cost: (a) each call pays Python start-up and imports (0.15 s measured for `loom --help`; `loom.cli` imports in 0.13 s) plus a **full scan** (no persistent scan cache: `scan/scan.py` has only `cached_property`s); `status --json` on the 29-file showcase copy took 0.85 s cold and 0.31 s warm, and scales with the quilt; (b) tool descriptions are shell help (flags, `-` for stdin), and stdin-reading options are unusable (`READS_STDIN`, `mcp/tools.py:20`); (c) results are CLI report text, structured only when the agent passes `json`; (d) author-only options must be listed by hand, and only `changes` is. Weight: hurts (speed on relloc; agent confusion). Effort: days, inside CORE-3 step 4. Rec: keep the generation idea, move it onto the registry, run in-process with the server's scan.

## 3. State on disk

### What loom writes in a quilt

From `paths.py`, `gitignore.py:22-32`, the write sites (232 across 62 files) and `demos/showcase`.

| path | class | notes |
|---|---|---|
| `*.tex` and other sources of the person | (a) person's | written by the paths in §4 |
| `config.toml` | (a) person's | `init`, `settings-save` (`config_edit.save`), `mv`/`atomize` via `set_main_forced`, sync rollback snapshot |
| root `.gitignore` | (a) person's | client-file lines added by `ai init`/`upgrade` (`gitignore.py:1-5`) |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | (a) person's root files | one loom line each, replaced in place (`ai/layout.py:67-81`) |
| `.claude/settings.json`, `.codex/rules/loom.rules` | (a)/(b) generated policy, committed | regenerated by `upgrade`, `agents-update` |
| `.mcp.json`, `.codex/config.toml` etc. | (b) machine-local client files | `ai/clients.py`; ignored |
| `research-state.md` (path from `[quilt] research_state`), `storage/**/overview.md` | (a)/(c) "pages" | `pages.py`; every write a `page-write` ledger line with texts kept |
| saved PDFs (`pdf-save`) | (a) new files only | `render/api.py:372-404`, opened `xb` |
| `.loom/build/**` (manifest, fragments, compiles, closures, crops, compare cache, `ids.lock`) | (b) derived | "deletable at any moment" (`paths.py:16`) |
| `.loom/build/uploads/<sha>/*.pdf` | **(c) in a (b) place** | a dropped PDF not yet filed lives in the derived directory (`render/api.py:194, 235`) |
| `.loom/last-seen.json` | (b) cache | versioned (`records/lastseen.py:25, 41`) |
| `.loom/serve.json` | runtime | port, pid, token |
| `.loom/ai/**` | (b) generated, but mode files become the person's once edited | `.loom-modes-version` hashes (`ai/layout.py:3-4`) |
| `.loom/digests/storage/**/pages/*.txt`, `sections.json`, `fetched.json`, `src.json`, `document.json` | (b) derived from a stored PDF/source, yet committed | `gitignore.py:22-32` commits page text on purpose |
| `.loom/digests/storage/**/paper.pdf`, `src/`, `cache/` | other people's documents | machine-local |
| `.loom/annotations/log.jsonl` (+ `annotations-before-delete.jsonl`) | (c) | append-only events |
| `.loom/edits/log.jsonl` | (c) | suggested edits and their fate |
| `.loom/state.toml` | (c) | acceptance ledger, `schema = 1` (`records/ledger.py:14`) |
| `.loom/history/ledger.jsonl`, `history/NNNN-<name>/`, `history/texts/`, `history/draft-context/` | (c) | versions, landmarks, content-addressed texts |
| `.loom/sessions/index.jsonl`, `sessions/<id>/inbox.jsonl`, `run.log`, `attached.json`, `cursors/` | (c), partly machine-local | |
| `.loom/since/<agent>.json`, `since/deleted.jsonl` | (c) machine-local | |
| `.loom/looked/<reviewer>.json` | (c) | "Your Changes" baseline (`looks.py:1-3`) |
| `.loom/review-decisions.json`, `review-origins.json`, `review-observations.json`, `adoption-decisions.json`, `source-sync.json` | (c) | Review, adoption and sync state |
| `.loom/annotation-types.toml` | (a)/(c) person-editable config | |
| `.loom/copies/` | (c) agent documents | CORE-9 |
| `.loom/retired/` | (c) | sources set aside by `atomize --retire` |
| `.loom/digests/<ck>.tex`, `<ck>.results.json`, `.proposals.jsonl`, `.proposed.tex`, `bibliography.bib`, `links.jsonl`, `links-removed.jsonl`, `unreadable.json`, `storage/copied.json` | (c), part machine-extracted, part human-verified | the library's records |

### CORE-7: no format version, no migration

There is no quilt-level format stamp. Three files carry their own: `state.toml` `schema = 1` (`records/ledger.py:14`), `last-seen.json` (`records/lastseen.py:25`), `review-decisions.json` `schema: 2`, which **resets to empty** on any other value (`review_queue.py:22-24`: a file from another schema is read as nothing and overwritten on the next write). `loom upgrade` (`cli/upgrade.py:17-60`) migrates no record: it rewrites `.loom/.gitignore`, writes default annotation types where missing, and refreshes the AI layer and client files. Record readers are tolerant: JSONL replays skip unparsable lines and unknown events and report each as a problem (`records/edits.py:100-118`, `records/log.py:190-240`), surfaced as `loom:foreign-annotations` / `loom:repeated-id`; unknown fields are ignored through `.get`. So an older loom reading a newer log drops the new event kinds with a warning, and some JSON state files are read with no `try` at all (`review_queue.py:22`), so a corrupt file is a traceback. Weight: hurts (testers will upgrade between v0.1.x builds). Effort: hours. Rec: fix: write `.loom/format` (an integer) at `init` and `upgrade`, refuse a newer one with a clear message, and make `review_queue._data` refuse rather than reset.

## 4. Writes to the person's files

### Every path that modifies a person's file

| # | code path | surfaces | guard | version first? |
|---|---|---|---|---|
| 1 | `pending.keep`, suggested edit (`pending.py:394-483`) | CLI `changes --keep`, HTTP `change-keep` | author only; state `ready` (placed, not "taken" by `taken_how` heuristic, `records/edits.py:406-445`); atomic `write_file` (`history/acts.py:115-120`); server's in-process lock only | `keep_versions(APPLY)` at `pending.py:442`, but it **skips** a document that cannot be stamped and proceeds (`history/acts.py:73-77`) |
| 2 | `pending.keep`, in-place change | same | look only, no file write | `keep_versions(KEEP)` |
| 3 | `pending.discard`, in-place change written back (`pending.py:486-566`) | CLI `changes --discard`, HTTP `change-discard` | author only | `keep_versions(UNDO)` + `undo` ledger line |
| 4 | `history.acts.restore` (`history/acts.py:123`) | HTTP `history-restore` only | author only; `cannot_restore` | current text kept as a version first |
| 5 | `history.acts.put_back` | HTTP `history-restore` with `path` | author only | text before kept |
| 6 | `tasks.tick` (`tasks.py:105-144`) | HTTP `file-tick` only | shown Markdown file, line hash must match | old text into `history/texts` (`write_raw`), `tick` ledger line |
| 7 | `adopt.incorporate` (`adopt.py:667-885`) | CLI `adopt`, HTTP `adopt-finish` | author, reviewer token, fingerprint | `stamp_document` first; snapshot and rollback on exception (`adopt.py:873-885`) |
| 8 | `sync.incorporate` (`sync.py:782-845`) | CLI `sync incorporate`, HTTP `sync-incorporate` | author; revision tokens | `_stamp` first; snapshot and rollback (`sync.py:791-845`) |
| 9 | `mv` (`cli/history_cmds.py:604-660`) | CLI | refuses unknown docs | moves the file; `move` ledger line; also rewrites `config.toml` main |
| 10 | `atomize --retire` (`cli/paper.py:618-627`) | CLI | identity-test compile first | source moved to `.loom/retired/`; `atomize` ledger line |
| 11 | new-file writers: `new` (`cli/nodes.py:142`, `open("x")`), `import`, `history restore --to`, `linearize --to`, `deloom --to`, `id --to`, `fork` node file, `pdf-save` | CLI / HTTP | `destination()` refuses an existing file unless `overwrite` (`cli/_common.py:132-170`) | n/a (new files) |
| 12 | `config_edit.save` (`config_edit.py:368`, atomic replace at `:266-272`) | HTTP `settings-save` | author only | **no version kept** |
| 13 | `ai init`, `upgrade`, HTTP `agents-update` (`ai/layout.py`, `ai/clients.py`, `gitignore.py:70, 88`) | CLI, HTTP | edited mode files kept with `.new` beside | root files edited in place, nothing kept |
| 14 | `loom write` pages (`pages.py`) | CLI, MCP (agent's `write`, act `replace`) | page targets only | texts kept in the ledger (`page-write`) |
| 15 | `set_main_forced` from `mv`/`atomize` | CLI | | none |

### CORE-5: Keep writes, then records, and guards with a heuristic

`pending.keep` writes each file (`pending.py:458`), appends an `apply` ledger line per edit (`pending.py:460`), rescans, and only then appends the `kept` event (`pending.py:466-474` → `records/edits.keep`, `records/edits.py:489-540`). The two writes are not one transaction and are not under one cross-process lock (the server serialises its own writes with `publication_lock`, `render/serve.py:365-367`; a CLI `changes --keep` beside it is not serialised). Whether an edit is already in the file is decided by text, not by record: `suggested()` marks an edit `taken` only when `taken_how` finds its words (twenty words or more: nine in ten in order; `records/edits.py:406-445`). The `apply` ledger lines that say exactly which edit was written are written and never read (`APPLY` has no reader: `grep` finds only writers at `pending.py:443, 460` and the dead `records/edits.py:483-485`). This is the shape behind the quant incident (commits 1ac44c5e and 2e106a45: written seven times without being recorded, then once more after the author edited inside the pasted body). Weight: blocks (it corrupts a tester's draft). Effort: hours. Rec: fix: before writing, refuse any edit that already has an `apply` line; take the edit log's lock (`locks.py`) across write and record; and make the dead `records/edits.apply` go (CORE-13).

### CORE-6: a version is not always kept

`keep_versions` keeps a version "unless" the document cannot be stamped, and then "the act it accompanies goes ahead" (`history/acts.py:63-85`): a document reaching a conflicted key has its file rewritten with no version. `config.toml` writes (12, 15) keep nothing, and root agent files (13) are edited in place. Weight: hurts. Effort: hours (fall back to `write_raw` of the whole file, as `tasks.tick` does, when a stamp is refused). Rec: fix.

### CORE-8: one name, several operations; stale "never edits"

`restore` means three things (new document from a landmark, put a version back in place, print a patch). `import` means three (a paper drafted into the quilt, `cli/paper.py:410`; a digest copied from another quilt, `cli/library/upkeep.py:188`; and `library add` is the actual "add a PDF"). `ai delete` deletes annotations (`cli/ai.py:34-58`). `revert` and `id` still tell the person "apply this patch to it, which loom never edits" (seven strings: `cli/history_cmds.py:410, 429, 476`; `cli/paper.py:179, 473, 717, 747`), while Keep, discard, restore and tick now edit files. Weight: hurts (agents read these strings). Effort: hours. Rec: fix with CORE-10's hiding; rename what stays.

## 5. Relics and dead weight

### CORE-9: agent copies (adoption), a second channel for AI-proposed edits

`loom draft DOC --ai NAME` makes an agent document in `.loom/copies/`; the person adopts it through a preview, decisions and incorporation. Code: `adopt.py` 1,133, `section_drafts.py` 344, `draft_lifecycle.py` 198, `drafts.py` 140, `cli/adopt.py` 116, `render/incoming.py` `attach_adoptions` (161), `cli/ai.py` drafts/refresh/close/reopen (~330), `cli/history_cmds.py` `draft` (~145), `render/api.py` `adopt-*` (~150), part of `incorporation_review.py`, three lint codes (`derived-id-in-person-document`, `agent-document-unrecorded`, `plain-id-in-agent-document`), mode `draft.md`; 45 files mention it. About 2,900 lines. The author wants Review to show "edits an AI proposed", which suggested edits (`records/edits.py`, `pending.py`) already are; two channels double Review's surface. Weight: hurts. Effort: hours to hide (drop `draft`, `ai drafts`, `ai refresh` from `AGENT_COMMANDS`; hide `adopt`, `ai close/reopen`; drop `adopt-*` from `CAPABILITIES`), days to remove. Rec: hide before v0.1, remove after.

### CORE-10: workbench commands of the atomized-node model

`atomize`, `fork`, `live`, `mv`, `linearize`, `deloom`, `id`, `revert`, `history restore`, `new`, `import`: `reshape/` 1,524, about 700 of `cli/paper.py`, about 800 of `cli/history_cmds.py`, about 150 of `cli/nodes.py`; roughly 3,000 lines, plus the scan's conflict and superseded-file machinery and a dozen diagnostics (CORE-15). None serves learning from papers, exploring, or proofreading a draft. `id` and `new` are agent tools today (`ai/layout.py:25-26`). Weight: hurts (help, tool list and orientation are longer than the job). Effort: hours to hide. Rec: hide (click `hidden=True`, drop from `AGENT_COMMANDS`); decide the node model after v0.1.

### CORE-11: git workspace sync

`sync.py` 1,079, `cli/sync.py` 437, `render/incoming.attach_incoming` 131, `sync-*` endpoints ~45: about 1,700 lines pairing a quilt with a git clone such as an Overleaf project (`sync.py:1-4`). It is the only route for the Overleaf tester, but only if that tester uses Overleaf's git integration, and every command is CLI only. Weight: irrelevant for most testers. Rec: defer (hide unless `[sync]` is configured).

### CORE-12: session transcripts

`session say`, `mailbox.py` 459 (`inbox.jsonl`, "the viewer's Transcript reads", `mailbox.py:1-4`), `render/threads.py` 114, and transcript pages in the build "so a viewer with no publisher running still reads the chat" (`render/build.py:345`), a static-host relic. About 650 lines. Weight: cosmetic. Effort: a day. Rec: remove (the decided direction is "viewer not a chat").

### CORE-13: small dead code

- `records/edits.apply` (`records/edits.py:457-486`): no caller; `pending.py:5` and `history/acts.py:20` still name it as the write path.
- `loom:interface-version` registered (`scan/diagnostics.py:60`) and never emitted.
- Unreferenced top-level defs (38 lines): `sessions.ensure_active` (`sessions.py:227`), `reshape/importer._insert_usepackage` (`:121`), `records/store._fact` (`:1065`), `ai/layout.settings_deny_paths` (`:406`), `scan/diagnostics.all_codes` (`:99`, test-only).
- Shims for older quilts: `OLD_LINES` (`ai/layout.py:76-81`), "an older loom" paths in 30 files (70 lines); no backwards compatibility is owed.
- `GEMINI.md` written by `ai init` for a client no tester uses.

Weight: cosmetic. Effort: hours. Rec: remove.

Lines removable: about 3,600 now (CORE-9, CORE-12, CORE-13) once hidden features are deleted, 6,600 with CORE-10, about 8,300 (15% of the package) with sync.

## 6. Hotspots

### Files of 800 lines or more (14)

| file | lines | judgment |
|---|---|---|
| `cli/review.py` | 2,136 | accidental: annotate, accept, status and their domain cores in one click module (CORE-1) |
| `render/api.py` | 1,301 | accidental: hand dispatcher (CORE-3) |
| `records/store.py` | 1,258 | accidental: `Records` is a god object (acceptance states, annotation resolution, diagnostics, manifest apply) |
| `render/fromhtml.py` | 1,258 | essential: TeX4ht HTML to fragments |
| `cli/history_cmds.py` | 1,167 | mostly workbench (CORE-10) |
| `adopt.py` | 1,133 | removable (CORE-9) |
| `sync.py` | 1,079 | deferrable (CORE-11) |
| `render/serve.py` | 964 | mixed: server, watcher, jobs, second origin for frames |
| `refs/build.py` | 935 | essential-ish: digest building and its report |
| `cli/paper.py` | 890 | workbench (CORE-10) |
| `refs/scan.py` | 889 | essential: library filing |
| `render/manifest.py` | 861 | accidental size: the whole viewer state in one function (below) |
| `digest/extract.py` | 826 | essential: TeX parsing |
| `scan/nodes.py` | 802 | essential: TeX parsing |

### Functions over 150 lines (15)

| function | lines | judgment |
|---|---|---|
| `scan/lint.py:181` `lint` | 419 | accidental shape: ~40 independent checks in one body; split into a table |
| `render/manifest.py:264` `build_manifest` | 346 | accidental: one function assembles every manifest section |
| `digest/extract.py:420` `extract_digest` | 291 | essential complexity, long |
| `render/api.py:694` `handle` | 289 | accidental (CORE-3) |
| `render/build.py:379` `build` | 247 | partly essential (pool, landmarks, compiles) |
| `adopt.py:667` `incorporate`, `adopt.py:427` `prepare` | 219, 218 | removable |
| `cli/review.py:172` `accept` | 200 | accidental: domain in the command |
| `cli/library/agent.py:63` `propose_command` | 196 | accidental: domain in the command |
| `cli/history_cmds.py:708` `_linearize` | 168 | workbench |
| `cli/paper.py:242` `run_import` | 166 | workbench |
| `cli/library/add.py:69` `add_command` | 164 | accidental: duplicates the HTTP orchestration |
| `mcp/server.py:34` `serve` | 162 | nested handlers in one closure |
| `render/incoming.py:207` `attach_adoptions` | 161 | removable |
| `refs/build.py:187` `report` | 160 | report formatting |

Complexity sits in TeX parsing (essential, about 6,000 lines in `scan/`, `digest/`, `render/fromhtml.py`, `tex/`) and in four accidental places: the CLI review module, the API dispatcher, `Records`, and the manifest builder. 45 functions exceed 100 lines out of 2,250. Weight: hurts. Effort: a week+. Rec: fix after v0.1, starting with what CORE-3 touches.

### CORE-18: why loom is slow, structurally

No scan survives a process: every CLI and MCP call rescans the whole quilt. In the server, about two thirds of handlers reuse the server's scan (`_scan`, 15 sites) and 7 rescan directly (`render/api.py`); `pending.keep` scans at least twice more (`pending.py:463, 481`, `_rescan` at `:582-586`). After every write except the 12 listed in `NO_REBUILD` (`render/api.py:76-92`), the server republishes the manifest. A persistent scan (per-file results keyed by hash) plus an in-process MCP would remove most of this. Weight: hurts (relloc). Effort: days. Rec: fix; the performance auditor should confirm the numbers.

## 7. Diagnostics

Production: the scanner and `scan/lint.py` emit `Diagnostic`s (`scan/model.py:73-96`); `cli/lint_cmd.all_diagnostics` (`cli/lint_cmd.py:48-57`) adds the records' (`records/store.py:780-890`) and the history walk's (`history/checks.py`); the renderer adds `snippet-failed` (`render/fragments.py:252`); `render/build.py:564, 609-613` merges them into the manifest; `scan/owners.py` stamps each `person`, `copy` or `work`. Every code must be in `scan/diagnostics.py` (a test checks it). The library has its own separate problem codes in `refs/check.py:68-87` (`file-gone`, `transcription-changed`, `no-page-text`, `version_mismatch`, `page-gone`), outside the registry.

Counts: 74 registered codes (6 reserved, 68 `loom:`). Five never reach the Problems page: `interface-version` is never emitted; `line-anchoring`, `atomize-target-exists`, `import-outside-tree`, `closure-failed` appear only inside CLI refusal text.

| class | count | codes |
|---|---|---|
| A LaTeX problem any author would recognise, actionable in their quilt | 10 | `duplicate-id`, `loom:duplicate-label`, `dangling-link`, `missing-include`, `inclusion-cycle`, `double-inclusion`, `loom:unknown-environment`, `loom:taxon-conflict`, `loom:non-utf8-source`, `loom:main-not-found` |
| Actionable only in loom's model (ids, `\uses`, nodes, digests, agent copies, config, records) | 46 | `environment-spans-files`, `line-anchoring`, `unattached-proof`, `multi-target-proof`, `reference-to-loose`, `macros-unloaded`, `macros-missing`, `macro-shadowed`, `prefix-is-citekey`, `unknown-directive`, `invalid-name`, `unknown-config-key`, `unlabelled-node`, `positional-proof-key`, `unexpected-proof`, `missing-proof`, `needs-classification`, `misplaced-basis`, `equation-in-proof-referenced`, `uses-missing`, `uses-unused`, `see-redundant`, `dependency-cycle`, `atomize-target-exists`, `import-outside-tree`, `cites-proposed-node`, `undigested-citekey`, `unmatched-postnote`, `postnote-from-another-version`, `unresolved-work`, `citekey-slug-collision`, `main-unset`, `superseded-file`, `no-live-document`, `derived-id-in-person-document`, `agent-document-unrecorded`, `plain-id-in-agent-document`, `agent-permissions-stale`, `home-missing`, `unreachable`, `retired-ledger-key`, `previous-key-match`, `detached-annotation`, `document-gone`, `id-reused`, `node-recovered` |
| Loom's own difficulty or record integrity: nothing the person did | 18 | `snippet-failed`, `closure-failed`, `unknown-theoremstyle`, `taxon-name-macro`, `missing-package` (in a digest), `version-mismatch`, `unverified-locators`, `digest-without-bib`, `no-readable-copy`, `interface-version`, `foreign-annotations`, `repeated-id`, `annotation-types`, `history-missing`, `history-edited`, `history-corrupt`, `history-interrupted`, `dangling-ancestry` |

### CORE-15: the Problems page mixes all three

Ten of 74 codes are what a mathematician would call a problem in their paper. Many model-hygiene codes are `error` severity although the document compiles (`reference-to-loose`, `unattached-proof`, `environment-spans-files`, `macros-*`, `citekey-slug-collision`, the three agent-document codes: `scan/diagnostics.py:18-90`). The owner stamp (`scan/owners.py:13-27`) separates the person from a copy or a work but not from loom itself: a `snippet-failed` in the person's document is stamped `person`. Weight: blocks (the author's own complaint; testers will read loom's misbehaviour as their errors). Effort: a day on the Python side. Rec: fix: add a `class` field (`latex` / `loom` / `internal`) to the registry, publish it in the manifest, show `latex` by default, and send `internal` to a log or `loom doctor`.

## 8. Extension

### CORE-16: files to touch per kind of change

| to add | Python files | also |
|---|---|---|
| a mode | `assets/ai/modes/<m>.md`, `MODES` in `ai/layout.py:18` (the MCP prompt follows) | snapshot tests |
| a record kind | `paths.py` (enforced by `tests/unit/test_paths.py`), a new `records/<kind>.py` (log, replay, lock), `records/store.py` (diagnostics), `gitignore.py` if machine-local, `render/manifest.py` + `render/build.py`, `since.py`, `render/api.py` (`CAPABILITIES`, handler, `NO_REBUILD`), a CLI command, `ai/layout.py` (`AGENT_COMMANDS`, `ACTS`) | `docs/specs/manifest.md`, `docs/specs/write-api.md`, arras types and store: about 12 files in two codebases |
| a CLI command with MCP tool and endpoint | `cli/<x>.py`, `cli/__init__.py`, `ai/layout.py` (`AGENT_COMMANDS`, `ACTS`, maybe `AUTHOR_OPTIONS`, `NETWORK`), `render/api.py` (`CAPABILITIES`, a branch in `handle`, `READS`/`NO_REBUILD`); the logic's home is unspecified | `docs/specs/write-api.md`, regenerated `loom/docs/cli-reference.md`, MCP snapshot test, the arras API client |
| a diagnostic | the emitter, `scan/diagnostics.py`, `scan/owners.py` if it is not the person's | `docs/specs/diagnostics.md`; a test must emit it |
| a kind of file the viewer opens | `files.py` (kinds, bodies), `render/build.py`/`manifest.py`, `render/serve.py` | arras components |

Only the diagnostic recipe is written down (`loom/CONTRIBUTING.md:6`); `docs/contributing.md` (78 lines) covers build, test and release. Weight: hurts (the author extends through agents, which follow written recipes). Effort: hours. Rec: fix with a short "adding X" section, rewritten once CORE-3 makes most rows one decorator.

## 9. Readability for a human contributor

### CORE-17

- **Types**: `mypy --strict` (`loom/pyproject.toml`) passes on all 195 files in about 5 s; 2,240 of 2,250 functions are fully annotated; 29 `type: ignore`. But boundaries are untyped: 422 `dict[str, Any]` and 664 `Any` mentions, covering events, the manifest, API bodies and answers.
- **Docstrings**: 1,610 of 2,250 functions have one (72%); median 138 characters, 90th percentile 526, longest 1,508; 128 source lines are over 400 characters. The register is dense and idiosyncratic ("its block reads as it taken already", `pending.py:291`). 82 lines narrate history against the repo's own rule (dates, "Found by", "until this stopped"); for example `is_agent` (`cli/_common.py:258-261`) and the comment at `render/api.py:1193`.
- **Citations**: 106 principle citations (`(P12)` 25, `(T2)` 10, …; all resolve in `docs/design/principles.md`), 82 `plan 0.x §y`, 96 spec references, and 41 `DR-NNN` references in 22 files pointing at the frozen decision records, which the repo says are never normative.
- **Naming**: vocabulary is overloaded: "import" ×3, "restore" ×3 (CORE-8), "keep" (a look, a suggested edit, `keep_versions`), "draft" (an agent copy or a draft), "publish" (the manifest or `sync publish`), "copy" / "agent document" / "draft" for one thing, "canon" / "landmark" / "stamp" / "version" / "step". 61 imports of underscore-private names across modules.
- **What a new contributor trips on first**: there is no rule for where an operation lives (a click module, a top-level module, `render/api.py`, or `records/`), and the function-local imports (CORE-2) hide what depends on what.

Weight: hurts. Effort: a day for a docstring and `DR-` sweep; the rest follows CORE-1 and CORE-3. Rec: fix after v0.1, except what CORE-1 moves anyway.

## Ten changes ranked by benefit per hour

| rank | change | effort | when |
|---|---|---|---|
| 1 | Make Keep idempotent by record: refuse an edit that has an `apply` ledger line, hold the edit-log lock across write and record, and delete `records/edits.apply` (CORE-5, CORE-13) | hours | before v0.1 |
| 2 | Hide agent copies, workbench commands, sync and transcripts from help, `AGENT_COMMANDS` and `CAPABILITIES` (CORE-9 to CORE-12); the MCP tool list drops from 42 to about 25 | hours | before v0.1 |
| 3 | Add a `class` field to the diagnostic registry and show only `latex` problems by default (CORE-15) | a day | before v0.1 |
| 4 | Move errors and identity out of `cli/` into `loom/errors.py` and `loom/identity.py`, and the annotation and acceptance cores out of `cli/review.py` into `records/`; `key_hash` into `scan/` (CORE-1) | a day | before v0.1 |
| 5 | A quilt format stamp, and refuse rather than reset in `review_queue._data` (CORE-7) | hours | before v0.1 |
| 6 | Keep a raw copy whenever `keep_versions` cannot stamp, and keep `config.toml` before writing it (CORE-6) | hours | before v0.1 |
| 7 | An `ops` registry with a generic HTTP dispatcher for the viewer's write operations, so guards and side effects are the same on every surface (fixes the accept divergence) (CORE-3) | days | start before v0.1 for the viewer's writes; finish after |
| 8 | A persistent scan, and MCP calls in-process on the server's scan (CORE-4, CORE-18) | days | before v0.1 if relloc speed is a tester blocker; otherwise just after |
| 9 | Delete the hidden agent-copy and transcript code, about 3,600 lines with the small dead code (CORE-9, CORE-12, CORE-13) | days | after v0.1 |
| 10 | Split `scan/lint.py:lint`, `render/manifest.build_manifest` and `records/store.Records` along their seams; sweep docstrings of history and `DR-` references; write the "adding X" recipes (CORE-14, CORE-16, CORE-17) | a week+ | after v0.1 |
