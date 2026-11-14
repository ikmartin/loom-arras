# v0.1 study: inventory of operations

Auditor: inventory. Checkout `v0.1-study` at 71621877. Every claim cites the study checkout; paths are from the repository root. Journeys: **L** learn, **E** explore, **P** proofread.

## 0. Counts and how the surfaces are built

- **CLI**: 77 runnable commands (groups that run alone, `history` and `library`, count once each), generated into `loom/docs/cli-reference.md` from the click tree registered at `loom/src/loom/cli/__init__.py:55-94`. Only two hidden commands exist, both dispatch helpers (`loom/src/loom/cli/history_cmds.py:965`, `loom/src/loom/cli/library/__init__.py:91`).
- **Agent commands**: 44, one hand-kept allowlist `AGENT_COMMANDS` (`loom/src/loom/ai/layout.py:21-38`); the other 33 are the author's, derived as the complement (`loom/src/loom/ai/layout.py:110-112`).
- **MCP**: 42 tools = `AGENT_COMMANDS - NOT_TOOLS`, `NOT_TOOLS = {mcp, serve}` (`loom/src/loom/mcp/tools.py:97-101`, `loom/src/loom/ai/layout.py:65`); `changes` loses `--keep/--discard/--keep-all/--discard-all/--why` (`loom/src/loom/ai/layout.py:61-63`); `--quilt`, `--as`, `--help` are supplied by the server and `--batch` is dropped (`loom/src/loom/mcp/tools.py:18-20`). Snapshot: `loom/docs/mcp-tools.json` (42 entries). Also 9 MCP prompts, one per mode (`loom/src/loom/mcp/prompts.py:23-30`), and resources for `quilt:` and `cited:` addresses (`loom/src/loom/mcp/resources.py:102-160`). Every tool call runs `python -m loom …` as a subprocess (`loom/src/loom/mcp/server.py:198-205`).
- **HTTP write API**: 48 POST endpoints, `CAPABILITIES` (47) plus `open` where the machine can open apps (`loom/src/loom/render/api.py:23-71`, `:354-358`), dispatched in `handle` (`loom/src/loom/render/api.py:694-982`); GETs `/_api`, `/_api/events`, `/_api/stream`, `/_api/here`, `/_api/jobs` and transcript pages (`loom/src/loom/render/serve.py:437-470`). `docs/specs/write-api.md` §2, §5 and the sync/adopt tables agree with the code's list.
- **Viewer**: 46 of the 48 POST endpoints have a caller in `arras/src`; `session-use` and `session-purpose` have none (grep of `arras/src` finds neither string). 24 routes under `arras/src/routes`.

## 1. Operations table

Health is from code and tests only: **solid** = exercised by named tests at the CLI or API level; **partial** = works, with a cited gap; **unknown** = no caller or no test found.

| # | operation | CLI | MCP | HTTP | viewer control (where) | for | J | health (one reason) |
|---|---|---|---|---|---|---|---|---|
| **Setup and upkeep** | | | | | | | | |
| 1 | Create a quilt | `init [DIR]` | — | — | none; empty quilt page lists commands (`arras/src/routes/+page.svelte:2`) | human | L E P | solid: `loom/tests/unit/test_init.py` |
| 2 | Create a quilt and import a paper in one step | `init --from FILE` | — | — | — | human | P | solid: `loom/tests/unit/test_init.py` |
| 3 | Bring a LaTeX draft into a quilt (received copy as landmark, working copy drafted) | `import FILE` | — | — | — | human | P | solid: `loom/tests/unit/test_paper.py` |
| 4 | Write the demo quilt | `init --demo` | — | — | — | human | none | solid: `loom/src/loom/assets/demo/` used by `loom/tests/unit/test_init.py` |
| 5 | Check toolchain and quilt | `doctor` | `loom_doctor` | — | — | both | none | solid: `loom/tests/unit/test_doctor.py` |
| 6 | Write the agent layer (orientation, rules, modes, CLAUDE.md/AGENTS.md/GEMINI.md, permission and MCP files) | `ai init` | — | — (`agents-update` refuses without it, `loom/src/loom/render/api.py:607`) | Settings › Agents prints `loom ai init` (`loom/src/loom/config_edit.py:469`) | human | L E P | solid: `loom/tests/unit/test_ai_layer.py` |
| 7 | Print an app's MCP entry (Claude Desktop, LM Studio, Zed, JetBrains) | `ai init --client` | — | — | — | human | L E P | solid: `loom/tests/unit/test_clients.py` |
| 8 | Refresh loom's own files after an update | `upgrade` | — | `agents-update` (permission files only) | Settings › Agents, update button (`arras/src/lib/shell/settings/Agents.svelte:26`) | human | none | solid: `loom/tests/unit/test_ai_layer.py` |
| 9 | Start the viewer server | `serve` | — (`NOT_TOOLS`) | — | — | human; agent in a shell | L E P | solid: `loom/tests/unit/render/test_serve.py` |
| 10 | Start the MCP server | `mcp --as NAME` | — | — | — | agent app | L E P | solid: `loom/tests/unit/test_mcp_server.py` |
| 11 | Name yourself (reviewer) | — (config/git) | — | `reviewer-settings` | Settings › Profile | human | P | solid: `loom/tests/unit/render/test_write_api.py` |
| 12 | Save quilt settings (`config.toml`) | — (edit the file) | — | `settings-save` | Settings › General, Documents, Agents, Library, Problems | human | none | solid: `loom/tests/unit/test_config_edit.py` |
| 13 | Save annotation types | — (edit `.loom/annotation-types.toml`) | — | `types-save` | Settings › Annotations; annotate bar "Save as new type" | human | L P | solid: `loom/tests/unit/records/test_types.py` |
| 14 | Browser-only preferences (typeface, format, ids in margin, hide aux files) | — | — | — | Settings › Appearance, Files (`arras/src/lib/shell/settings/catalog.ts:48-55`) | human | none | solid: `arras/src/lib/prefs.spec.ts` |
| **Reading and finding** | | | | | | | | |
| 15 | Build the site (scan, render, publish) | `build` | `loom_build` | — (serve rebuilds on change) | automatic under serve | both | L E P | solid: `loom/tests/unit/render/test_build.py` |
| 16 | Compile a document, or a key's closure, or a proposed diff | `compile` | `loom_compile` | — | compiled PDF opens from the tree | both | P E | solid: `loom/tests/tex/test_compile_runs.py` |
| 17 | Lint and compile everything (CI) | `check` | `loom_check` | — | — | both | none | solid: `loom/tests/tex/test_real_toolchain.py` |
| 18 | Read a key's or document's LaTeX, with closure or at a version | `source` | `loom_source`; resources `quilt:KEY` | — | — | agent | L E P | solid: `loom/tests/unit/test_source_cmd.py` |
| 19 | Find by id, alias, title, taxon, tag, citekey, printed number | `search` | `loom_search` | — | ⌘K palette, ids and titles only (`arras/src/lib/components/Palette.svelte:11`) | both | L E P | solid: `loom/tests/unit/test_numbered_search.py` |
| 20 | A link the viewer follows | `link` | `loom_link` | — | links in transcripts and pages | agent | L E P | solid: `loom/tests/unit/test_links.py` |
| 21 | Where the person is looking | `here` | `loom_here` | `here` (viewer posts), GET `/_api/here` | automatic from every tab (`arras/src/lib/here.svelte.ts`) | agent | L E P | partial: empty unless `loom serve` runs (`loom/src/loom/cli/here_cmd.py:36`) |
| 22 | What people did since the agent last looked | `since` | `loom_since` | — | — | agent | L E P | solid: `loom/tests/unit/test_since.py` |
| 23 | Every key's state, stale cause, filters | `status` | `loom_status` | — | ids in margin (Settings › Appearance), Your Changes | both | P | solid: `loom/tests/unit/test_review_queue.py` |
| 24 | Every diagnostic | `lint` | `loom_lint` | — | Review › Problems | both | none | solid: `loom/tests/unit/test_lint.py` |
| 25 | Direct dependencies / statement closure | `deps` | `loom_deps` | — | local graph panel, closure panel | both | L E P | solid: `loom/tests/unit/test_graph.py` |
| 26 | Everything downstream of a key | `downstream` | `loom_downstream` | — | — | both | E P | solid: `loom/tests/unit/test_graph.py` |
| 27 | The whole graph, four drawings | — | — | — | `/graph` (`arras/src/routes/graph/+page.svelte:2`) | human | L E | solid: `arras/tests/e2e/graph.e2e.ts` |
| 28 | Indexes: threads, tags, taxa, not in a document | `status --tag/--loose` | `loom_status` | — | Settings › Development shelf (`arras/src/lib/shell/views.ts:39-48`) | human | none | solid: `arras/tests/e2e/routes.e2e.ts` |
| 29 | Open a shown file or an app on the machine | — | — | `open` | file links (`arras/src/lib/workspace/links.ts`) | human | none | solid: `loom/tests/unit/test_files.py` |
| 30 | Tick a box in a Markdown file | — | — | `file-tick` | file pane (`arras/src/lib/workspace/items/FileItem.svelte`) | human | E | solid: `loom/tests/unit/test_tasks.py` |
| 31 | Compare two panes / two versions | `source --at REF --diff` | `loom_source` | `compare` | compare from history ▾, compare bar (`arras/src/lib/workspace/compare.svelte.ts`) | both | P | solid: `loom/tests/unit/render/test_compare.py` |
| **Annotations** | | | | | | | | |
| 32 | Annotate a key, document, work, PDF page (quote, box, ink) | `annotate TARGET MSG` | `loom_annotate` | `annotate` | Annotate and Comment tools, popup (`arras/src/lib/review/AnnotateBar.svelte:2`) | both | L E P | solid: `loom/tests/unit/records/test_review_commands.py` |
| 33 | Reply | `annotate --reply` | `loom_annotate` | `reply` | annotation popup | both | L E P | solid: same |
| 34 | Resolve / reopen | `annotate --resolve [--undo]` | `loom_annotate` | `resolve` | annotation popup | both | P | solid: same |
| 35 | Edit body, type, look, geometry | `annotate --edit` | `loom_annotate` | `edit` | annotation popup | both | L E P | solid: same |
| 36 | Delete one, undo the delete | `annotate --delete` | `loom_annotate` | `delete`, `restore` | popup Delete, toolbar Undo (`arras/src/lib/review/history.svelte.ts:65-69`) | both | L E P | solid: `loom/tests/unit/records/test_log_delete.py` |
| 37 | Bulk delete by author, target, date, version | `ai delete` | — | — | — | human | none | solid: `loom/tests/unit/test_ai_layer.py` |
| 38 | List annotations | `ai annotations`, `status --reading` | `loom_ai_annotations` | — | Comments and Notes lists beside one text (`arras/src/lib/review/SideList.svelte:2`) | both | L E P | partial: per text only; every-note view not built (`docs/work-queue/WQ-69-every-note.md`) |
| 39 | Take a PDF's own annotations into loom | — | — | `annotations-take` | PDF pane (`arras/src/lib/pdf/desk.svelte.ts`) | human | L | solid: `loom/tests/unit/records/test_pdf_annotations.py` |
| 40 | Locate a quotation on a work's page | `library locate` | `loom_library_locate` | `locate` | PDF reading, work preview (`arras/src/lib/pdf/Reading.svelte`) | both | L | solid: `loom/tests/unit/test_library_read.py` |
| 41 | Quote words to the agent (clipboard link, no record) | — | — | — | Quote chip on a selection (`arras/src/lib/review/QuoteChip.svelte:2`) | human | L E P | solid: `arras/tests/e2e/annotations.e2e.ts` |
| 42 | Ask an agent for a work's overview | — | — | `annotate` with a fixed message (`arras/src/lib/review/ask.ts:9-13`) | Ask an agent, work Info (`arras/src/lib/components/AskAgent.svelte:33`) | human | L | partial: an annotation only; nothing wakes an agent (`loom/src/loom/render/api.py:5`) |
| 43 | Edit PDF pages (turn, delete, reorder, insert) into a new file | — | — | `pdf-save` | PDF menu, pages editor (`arras/src/lib/pdf/PagesEditor.svelte:2`) | human | none | solid: `arras/tests/e2e-reading/marks.e2e.ts` |
| **Changes and acceptance** | | | | | | | | |
| 44 | File a suggested edit | `suggest KEY --quote --with` | `loom_suggest` | — | — | agent | P | solid: `loom/tests/unit/records/test_edits.py` |
| 45 | Withdraw one's own suggested edit | `suggest --withdraw` | `loom_suggest` | — | — | agent | P | solid: same |
| 46 | List what waits (suggested edits, tracked in-place edits) and print a patch | `changes [ID]` | `loom_changes` (read only) | — | Your Changes, Changes ▾, Comments list, change popup (`arras/src/lib/review/ChangePopup.svelte:2`) | both | P | solid: `loom/tests/unit/test_pending.py` |
| 47 | Keep / discard a change, all of a document's, undo | `changes --keep/--discard/--keep-all/--discard-all` | — | `change-keep`, `change-discard` (`undo`) | change popup, change cards, Changes ▾ Keep all/Discard all | human | P | solid: `loom/tests/unit/test_pending.py` |
| 48 | Start tracking in-place edits (take a look) | `changes --keep-all` first time | — | `settings-save review.track_edits`, `change-keep all` | Settings › Agents toggle | human | P | solid: `loom/tests/unit/test_looks.py` |
| 49 | Accept mathematics as correct | `accept KEYS` | — | `review-accept` | Your Changes Accept, review side panel (`arras/src/lib/review/ReviewPanel.svelte:2`) | human | P | solid: `loom/tests/unit/test_personal_acceptance.py` |
| 50 | See what changed since accepted, with why | `status --stale`, `status --explain KEY` | `loom_status` | — | Review › Your Changes (`arras/src/routes/review/+page.svelte:2`) | both | P | solid: `loom/tests/unit/test_review_queue.py` |
| **Versions and history** | | | | | | | | |
| 51 | Record a named version of a document | `stamp DOC -m NAME` | — | `history-record` | history ▾ "record this version…", The Record › Versions | human | P | solid: `loom/tests/unit/render/test_versions.py` |
| 52 | Record every moved key quilt-wide | `stamp` | — | — | — | human | none | solid: `loom/tests/unit/history/test_commands.py` |
| 53 | List steps, or a key's versions | `history [KEY]` | `loom_history` | — | history ▾, The Record (`arras/src/lib/workspace/HistoryMenu.svelte:2`) | both | P | solid: `loom/tests/unit/history/test_ledger.py` |
| 54 | Print a landmark | `history show` | `loom_history_show` | — | version tab (`arras/src/lib/review/VersionView.svelte`) | both | P | solid: `loom/tests/unit/history/test_commands.py` |
| 55 | Put a version back into its document, in place | — | — | `history-restore {document, version}` | version toolbar restore…, The Record › Versions (`arras/src/lib/workspace/VersionControls.svelte:2`) | human | P | solid: `loom/tests/unit/history/test_acts.py` |
| 56 | Start a new document from a landmark | `history restore NAME --to FILE` | — | — | — | human | none | solid: `loom/tests/unit/history/test_commands.py` |
| 57 | Print the patch reverting one key | `revert KEY@N` | — | — | — | human | P | solid: `loom/tests/unit/history/test_commands.py` |
| 58 | Put back the text an undo set aside | — | — | `history-restore {path, text}` | The Record › Everything recorded (`arras/src/routes/review/record/acts/+page.svelte:2`) | human | P | solid: `loom/tests/unit/history/test_acts.py` |
| 59 | Check history against its ledger | `history verify` | `loom_history_verify` | — | — | both | none | solid: `loom/tests/unit/history/test_ledger.py` |
| **Node and document surgery** | | | | | | | | |
| 60 | New node file or skeleton | `new TAXON` | `loom_new` | — | — | both (draft mode uses `--print`) | E | solid: `loom/tests/unit/test_writer.py` |
| 61 | Label untagged environments / next free id | `id [FILE]`, `id --next` | `loom_id` | — | — | both | P | solid: `loom/tests/unit/test_ids.py` |
| 62 | Split a document into a spine and node files | `atomize` | — | — | — | human | none | solid: `loom/tests/tex/test_reshape_real.py` |
| 63 | Give a document its own copy of a node | `fork` | — | — | — | human | none | solid: `loom/tests/tex/test_reshape_real.py` |
| 64 | Flatten a spine | `linearize` | — | — | — | human | none | solid: `loom/tests/tex/test_reshape_real.py` |
| 65 | Write a document with loom taken out | `deloom` | — | — | — | human | P (submission) | solid: `loom/tests/unit/test_deloom.py` |
| 66 | Move a document and its records | `mv` | — | — | — | human | none | solid: `loom/tests/unit/history/test_mv.py` |
| 67 | Make a superseded document live | `live` | — | — | — | human | none | solid: `loom/tests/unit/history/test_commands.py` |
| **Agent documents (copies)** | | | | | | | | |
| 68 | Draft an agent document from a working document | `draft DOC --ai NAME` | `loom_draft` | — | — | agent | E P | solid: `loom/tests/unit/test_agent_copies.py` |
| 69 | List agent documents and their staleness | `ai drafts` | `loom_ai_drafts` | — | Docs › Agent documents shelf | both | E P | solid: same |
| 70 | Refresh from the paper | `ai refresh` | `loom_ai_refresh` | `adopt-refresh` | draft actions (`arras/src/lib/components/DraftActions.svelte:35`) | both | P | solid: `loom/tests/unit/test_adopt.py` |
| 71 | Close / reopen an agent document | `ai close`, `ai reopen` | — | `adopt-close`, `adopt-reopen` | draft actions (`arras/src/lib/components/DraftActions.svelte:33-40`) | human | none | solid: `loom/tests/unit/render/test_write_api.py` |
| 72 | Preview a section draft inside the paper | — | — | `adopt-paper` | draft actions (`arras/src/lib/components/DraftActions.svelte:36`) | human | P | solid: `loom/tests/unit/test_section_drafts.py` |
| 73 | Review and apply an agent document | `adopt DOC [--incorporate TOKEN]` | — | `adopt-decision`, `adopt-preview`, `adopt-finish` | Proposed Changes › copy (`arras/src/lib/review/ContributionReview.svelte:2`) | human | P | solid: `loom/tests/unit/test_adopt.py` |
| **Library** | | | | | | | | |
| 74 | Report what cited works need | `library [WORK]` | `loom_library` | — | Review › Library (`arras/src/routes/review/library/+page.svelte:2`) | both | L | solid: `loom/tests/unit/refs/test_library_states.py` |
| 75 | Add a work by pasted DOI, arXiv id, BibTeX | — (edit a .bib, then `library update`) | — | `library-recognise`, `library-lookup`, `library-add` | Add work (`arras/src/lib/components/AddWork.svelte`) | human | L | solid: `loom/tests/unit/refs/test_added.py` |
| 76 | File a PDF or LaTeX source | `library add FILE [--for]` | — | `library-upload`, `library-file` (≤256 MB, `arras/src/lib/components/AddWork.svelte:43`) | Add work, drop a PDF | human | L | solid: `loom/tests/unit/refs/test_library_store.py` |
| 77 | Library run: gather, resolve, fetch, extract, map | `library update` | `loom_library_update` (network only by config, `loom/src/loom/ai/layout.py:67`) | `library-update` (needs serve, `loom/src/loom/render/api.py:132`) | run buttons (`arras/src/lib/components/LibraryRun.svelte`), Problems fixes | both | L | solid: `loom/tests/unit/test_jobs.py` |
| 78 | Delete a work for good | — | — | `library-delete` | Review › Library | human | L | solid: `arras/tests/e2e-write/library-acts.e2e.ts` |
| 79 | Stop asking for a work's document | `library ignore [--undo]` | — | `library-ignore` | Review › Library | human | none | solid: `loom/tests/unit/refs/test_library_upkeep.py` |
| 80 | Drop recorded results | `library drop` | — | — | — | human | none | solid: `loom/tests/unit/test_refs_layer.py` |
| 81 | Copy a digest from another quilt | `library import PATH` | — | — | — | human | none | solid: `loom/tests/unit/test_digest.py` |
| 82 | Read page text or a work's overview | `library read WORK [PAGES]` | `loom_library_read` | — | work Text (PDF) and Info views (`arras/src/lib/workspace/views.ts:13-17`) | both | L | solid: `loom/tests/unit/test_library_read.py` |
| 83 | Search results or page text | `library search [--pages]` | `loom_library_search` | — | — | agent | L E | solid: `loom/tests/unit/test_library_read.py` |
| 84 | Propose a result, quotation checked | `library propose` | `loom_library_propose` | — | — | agent | L | solid: `loom/tests/unit/refs/test_library_regrade.py` |
| 85 | List proposals | `library review` | `loom_library_review` | — | Proposed Changes › work (`arras/src/routes/review/proposed/+page.svelte:2`) | both | L | solid: `arras/tests/e2e/proposals.e2e.ts` |
| 86 | Verify / discard a proposal | `library verify`, `library discard` | — | `library-verify`, `library-discard` | proposal card (`arras/src/lib/review/ProposalCard.svelte:150-165`) | human | L | solid: `loom/tests/unit/render/test_write_api.py` |
| 87 | Relate two results / remove a relation | `library relate [--undo]` | `loom_library_relate` | — | — | agent | L | solid: `loom/tests/unit/scan/test_relations.py` |
| 88 | Provenance and relations of a result | `library why` | `loom_library_why` | — | work Info | both | L | solid: `loom/tests/unit/scan/test_relations.py` |
| 89 | Check the library for problems | `library check` | `loom_library_check` | — | Review › Problems, Library | both | none | solid: `loom/tests/unit/refs/test_library_upkeep.py` |
| 90 | Write the research state or a work's overview | `write state\|WORK TEXT --base` | `loom_write` | — | read-only page (`arras/src/routes/page/[id]/+page.svelte`) | agent | L E | solid: `loom/tests/unit/test_pages.py` |
| **Sessions and the agent's view** | | | | | | | | |
| 91 | Open a session | `session new` | `loom_session_new` | `session-new` | session picker, The Record › Sessions (`arras/src/lib/sessions/new.ts:17`) | both | none | solid: `loom/tests/unit/test_sessions.py` |
| 92 | Rename a session | `session rename` | `loom_session_rename` | `session-rename` | session picker | both | none | solid: same |
| 93 | List sessions | `session list` | `loom_session_list` | — | session picker | both | none | solid: same |
| 94 | Write in a transcript | `session say` | `loom_session_say` | — | transcript is read-only (`arras/src/lib/workspace/items/ChatView.svelte`) | agent | L E P (every report, `loom/src/loom/assets/ai/rules.md:41`) | solid: `loom/tests/unit/test_transcript.py` |
| 95 | Make a session current | `session use` | — | `session-use` (no caller) | picker select, browser-local (`arras/src/lib/sessions/sessions.svelte.ts:44`) | human | none | partial: two separate "current session" notions |
| 96 | Close / reopen a session | `session close`, `session use` | — | `session-close`, `session-reopen` | session picker | human | none | solid: `loom/tests/unit/test_sessions.py` |
| 97 | Delete / purge a session | `session delete [--purge]` | — | `session-delete` | delete dialog (`arras/src/lib/sessions/DeleteSession.svelte`) | human | none | solid: same |
| 98 | Say what a session is for | — | — | `session-purpose` (no caller) | — | — | none | unknown: no caller in `arras/src` |
| 99 | Orientation plus live state, join a session | `ai orient [--session]` | `loom_ai_orient`; server instructions (`loom/src/loom/ai/orient.py:134-156`) | — | — | agent | L E P | solid: `loom/tests/unit/test_ai_layer.py` |
| 100 | Read a mode | `ai mode NAME` | `loom_ai_mode`; 9 prompts | — | — | agent | L E P | solid: `loom/tests/unit/test_mcp_server.py` |
| **Overleaf (document workspace)** | | | | | | | | |
| 101 | Pair with a cloned workspace | `sync init DIR` | — | — | Settings › Overleaf shows the command (`arras/src/lib/shell/settings/Overleaf.svelte:2,22`) | human | P | solid: `loom/tests/unit/test_sync.py` |
| 102 | Fetch the workspace's changes | `sync fetch` | — | — | — | human | P | solid: same |
| 103 | Preview a fetched pull | `sync status --patch` | — | `sync-preview` | Proposed Changes › pull (`arras/src/lib/review/IncomingPull.svelte:2`) | human | P | solid: same |
| 104 | Apply a pull | `sync incorporate` | — | `sync-incorporate` | pull review Apply | human | P | solid: same |
| 105 | Choose which documents publish | `sync documents` | — | — | — | human | P | solid: same |
| 106 | Publish and push | `sync publish [--push]` | — | — | — | human | P | solid: same |
| 107 | Show workspace state | `sync status` | — | — | Settings › Overleaf (paired view) | human | P | solid: same |

## 2. The no-command gap

### 2a. What a human must still type

| operation | endpoint today | safe from a served page? | what a control needs | effort |
|---|---|---|---|---|
| Install loom | — | n/a | Docs say `pipx install git+https://github.com/ikmartin/loom` (`loom/README.md:21`) but this repository's remote is `ikmartin/loom-arras` with the package under `loom/`; check which URL works | hours |
| Start the viewer (`serve`) | none; not an MCP tool (`loom/src/loom/ai/layout.py:65`) | n/a, chicken and egg | have `loom mcp`, which every agent app starts by itself (`loom/src/loom/cli/mcp_cmd.py:35-37`), start or find a `loom serve` for its quilt and hand its URL to the agent; or a macOS launcher | a day |
| Choose which quilt to open | none; one server per quilt, port 8791 fixed and refused when busy (`loom/src/loom/render/serve.py:32`, `loom/src/loom/cli/serve_cmd.py:16`) | n/a | a quilt-less home server listing quilts, or automatic ports | days |
| Create a quilt (`init`) | none; serve needs a quilt (`loom/src/loom/cli/serve_cmd.py:31`), and so does `loom mcp` | yes if confined to a new directory the person names | the home server above, plus a form; or let the agent run it | days |
| Bring in a local draft (`import`, `init --from`) | none; not an agent command (`loom/src/loom/ai/layout.py:32` comment) | yes: never edits the source, writes new files | a path field (the server is local) or an agent tool | a day |
| Set up the agent layer (`ai init`) | none; `agents-update` refuses without `.loom/ai` (`loom/src/loom/render/api.py:607`) | yes for files in the quilt | an `agents-init` endpoint, or do it inside `init` | hours |
| Attach Claude Desktop | none; Desktop is configured outside the quilt (`loom/src/loom/ai/clients.py:57-63`) and its entry pins one quilt with `--quilt ABS` (`loom/src/loom/ai/clients.py:108`) | no: writes another app's global config; needs explicit consent | a button that shows the entry and, on consent, merges it into `claude_desktop_config.json` | a day |
| Pair with Overleaf (`sync init`) | none | partly: cloning needs the person's Overleaf Git credentials, which a page must not take | a guided clone in the person's own Git, then pairing by folder | days |
| Fetch from Overleaf (`sync fetch`) | none; only preview and incorporate exist (`loom/src/loom/render/api.py:746-788`) | yes: writes loom's refs only | `sync-fetch` endpoint and a button on Proposed Changes | hours |
| Publish to Overleaf (`sync publish --push`) | none | yes, with a confirm: pushes to coauthors | endpoint and confirm | hours |
| Upgrade quilt files after updating loom (`upgrade`) | partial (`agents-update`) | yes: loom's own files, edited mode files kept (`loom/src/loom/ai/layout.py:3`) | run on `serve`/`mcp` start when the version changed | hours |
| Diagnose setup (`doctor`) | none | yes: writes nothing (`loom/docs/cli-reference.md:82`) | a Setup or Settings page reading `doctor --json` | hours |
| Strip loom for submission (`deloom`) | none | yes: writes outside sources only | endpoint and a menu item | hours |
| Files over 256 MB | AddWork says to use `loom library add FILE` (`arras/src/lib/components/AddWork.svelte:171`) | — | none needed for v0.1 | irrelevant |

Places where the viewer itself tells a person to type a command: the empty quilt page (`arras/src/routes/+page.svelte:2`), Problems fixes "as a command to copy" (`arras/src/routes/review/problems/+page.svelte:2`), Settings › Agents (`loom/src/loom/config_edit.py:469`), Settings › Overleaf (`arras/src/lib/shell/settings/Overleaf.svelte:22`), the out-of-step notice (`arras/src/lib/components/OutOfStep.svelte:13`), and AddWork's size limit.

### 2b. Asymmetries that look accidental

Human in the viewer, not the agent:

- **Bringing a paper or draft in.** `library add`, `import` and `init` are not agent commands (`loom/src/loom/ai/layout.py:32`), and `library-add/-upload/-file` refuse an agent (`loom/src/loom/render/api.py:190`). "Add this paper" said to Codex or Claude Desktop fails, or the agent edits a `.bib` by hand and runs `library update`, which reaches the network only if config allows.
- **Deleting a work** (`library-delete`) exists only over HTTP: there is no CLI or MCP twin.
- **Comparing** is HTTP-only as `compare`; the agent's equivalent is `source --at --diff`, which takes keys and steps, not a document against a version.

The agent, not the human in the viewer:

- **Searching the library's results and page text**: `library search` exists for the agent; the viewer's only search is ⌘K over ids and titles (`arras/src/lib/components/Palette.svelte:11`). EXPLORE's "is this known" is agent-only.
- **Relating two results**: `library relate` has no endpoint, so a reader cannot record or remove a relation they noticed.
- **Writing the research state or an overview**: agent-only through `write` (`loom/src/loom/ai/layout.py:58`); the viewer shows them read-only, and a person edits the file elsewhere.

Same name, different act across surfaces:

- **Restore**: `loom history restore NAME --to FILE` writes a new document (`loom/src/loom/cli/history_cmds.py:1041-1057`); `/_api/history-restore` puts the version back into the document in place (`loom/src/loom/render/api.py:507-563` → `loom/src/loom/history/acts.py:123`); `revert` prints a per-key patch. The viewer's act has no CLI or MCP form.
- **Current session**: the CLI keeps an active session in the quilt (`session use`), while the viewer keeps its own selection in the browser (`arras/src/lib/sessions/sessions.svelte.ts:44`) and never calls `session-use`.

HTTP-only operations with no CLI or MCP form, against the goal of three surfaces over one set of operations: `library-delete`, `library-recognise`, `library-lookup`, `library-add` (by identifier), `annotations-take`, `pdf-save`, `file-tick`, `compare`, `adopt-paper`, `types-save`, `settings-save`, `reviewer-settings`, `history-restore`, `session-reopen`, `session-purpose`. CLI-only with a viewer equivalent missing: everything in 2a.

## 3. Serving no journey

| what | surfaces | recommendation |
|---|---|---|
| Node surgery: `atomize`, `fork`, `linearize`, `live` | CLI, author only | remove (no tester will restructure a paper into node files) |
| `mv` | CLI | hide (keeps records following a rename; agent could own it) |
| `new`, `id` | CLI + MCP | keep for agents only (draft mode uses `new --print` and `id --next`, `loom/src/loom/assets/ai/modes/draft.md:15-20`); hide from human help |
| `deloom` | CLI | defer (submission is after v0.1's journeys) |
| Quilt-wide `stamp`, `history verify`, `history restore --to`, `revert` | CLI (+MCP for verify) | hide; keep "record this version" and in-place restore |
| Review › The Record › Everything recorded | viewer | hide (bookkeeping of acts) |
| Sessions: `session *`, transcripts, the column's session footer and picker, The Record › Sessions, `session-purpose`, `session-use` | all four surfaces | hide in the viewer for v0.1; remove the two dead endpoints; see INV-20 before removing more, because the agent rules route every report into a transcript |
| Library bookkeeping: `library drop`, `library import`, `library ignore`, `library check`, Settings › Problems (silencing) | CLI, HTTP, viewer | hide |
| Review › Problems | viewer | hide except compile errors in the person's own files |
| Indexes: threads, tags, taxa, not in a document; context pages | viewer (Settings › Development) | remove from the viewer |
| PDF page editor (`pdf-save`) | viewer + HTTP | hide |
| `ai delete` (bulk), `annotate --batch` | CLI | keep for agents and scripts, hide from humans |
| `init --demo` | CLI | keep (cheap tour), not in the testers' path |

Second ways of doing one thing:

- `init --from FILE` versus `init` then `import FILE`.
- Three "go back" acts (section 2b).
- Six diagnostic reports: `doctor`, `lint`, `check`, `build` (lists errors), `status`, `library check`, plus Review › Problems and Review › Library.
- Three searches with different scopes: `search`, `library search`, ⌘K.
- Three channels for text an AI proposes: suggested edits (`suggest`), agent documents (`draft` then `adopt`), and in-place edits, which are allowed by default and seen only if `track_edits` is on (`loom/src/loom/cli/quilt.py:39-42`, `loom/src/loom/assets/ai/orientation.md:30`). Review splits them between Your Changes (suggested and in-place) and Proposed Changes (agent documents, Overleaf pulls, library proposals) (`arras/src/lib/review/sections.ts:32-33`).
- Two transcripts of one conversation: the agent app's chat and loom's session transcript (`loom/src/loom/assets/ai/orientation.md:64`).
- Two note stores beside annotations: Markdown files in the tree and the research state page.

## 4. Vocabulary

| word(s) | where a person meets it | what it means | verdict | must a tester learn it? |
|---|---|---|---|---|
| quilt | everywhere; CLI says it 208 times | the project directory | name for "project"; fine if said once | yes, once |
| work, paper, book | library, work views "Text · Info" | an item in the library | synonyms in practice; code keeps `paper` as an address (`arras/src/lib/workspace/views.ts:12`) | "paper" suffices |
| digest, digest node, result, node, key, block, id, label | CLI, agent text, margin ids, Your Changes "blocks" | a numbered statement, in your document or in a paper's digest | one idea, six words; `key` also covers sections and equations | only "result" |
| annotation | toolbar, popups, Settings › Annotations | anything left on text by a person or an agent | the umbrella | yes |
| comment | Comment tool, Comments list, an annotation's body | an annotation at a place, or its text | synonym of annotation in the list name | no: call the list Annotations |
| note | annotation type Note (`loom/src/loom/assets/init/annotation-types.toml`), Notes list, design's Zettelkasten notes, MCP "a note, which loom_since reports" (`loom/src/loom/mcp/resources.py:146`) | an annotation whose type is listed in Notes | real distinction (durable versus to-do), overloaded | yes |
| mark | PDF marks, `--mark` tool, Changes "Markup" | how an annotation is drawn on a page | internal | no |
| suggestion (type) versus suggested edit | annotation type Suggestion versus `loom suggest` records | an annotation recommending something versus a proposed text change with Keep/Discard | collision: same word, different objects | yes; rename the type |
| proposal, proposed | Proposed Changes; `library propose` | agent documents, pulls, library results awaiting the person | three kinds under one word | no if library proposals move to Library |
| change | Your Changes, Proposed Changes, Changes ▾, `loom changes` | suggested edits plus tracked in-place edits; but Your Changes also lists blocks to accept, which are not changes | overloaded | yes, narrowed |
| accept, keep, discard, verify, resolve, take, leave, apply, incorporate, adopt | Review, popups, CLI | accept = mathematics checked; keep/discard = a text change; verify = a digest copy is faithful; resolve = an annotation met; take/leave/apply = an agent document's changes; incorporate/adopt = CLI words for apply | four real distinctions, ten words | accept, keep/discard, resolve |
| version, landmark, stamp, step, canon, record, The Record | history ▾, The Record, CLI | a saved state of a document (landmark/version), a ledger entry (step/stamp) | one user-facing idea | "version" only |
| look | Settings › Annotations ("the look in hand"); `loom changes` ("your look") | an annotation's styling; the person's last-seen snapshot of files | collision | neither, if styling is "style" and the snapshot is invisible |
| agent document, copy, draft, contribution | Docs › Agent documents, DraftActions "Close draft", `loom draft`, code's ContributionReview | an agent's working copy of your document | four words for one thing; `draft` is also a mode and your own "drafting" document | only if agent documents stay |
| session, transcript, round, run, run.log, "writing in" | column footer, picker, The Record › Sessions, `session close` "round" | a stretch of work and its log; `run` is also a library run | bookkeeping | no for v0.1 |
| research state, overview, page | Settings › Documents, work Info | agent-kept pages | real, small | overview yes; research state optional |
| front door, outline, pane, tab, Docs, Review | shell | layout words | fine | yes, lightly |

**Smallest vocabulary for the three journeys** (nine words): **project** (or quilt, said once), **document**, **paper**, **result**, **annotation** (with its **type**; **note** is one type), **suggested edit** with **keep**/**discard**, **accept** (the mathematics is checked; "changed since accepted" is the stale state), **version**. Everything else stays internal or agent-facing. Two renames buy most of it: the annotation type Suggestion becomes something that is not "suggestion" (for example Idea), and "look" for styling becomes "style".

## 5. Modes

All nine live in `loom/src/loom/assets/ai/modes/`; `MODES` fixes their order (`loom/src/loom/ai/layout.py:18`).

| mode | what it is for (its "When it fits" line) | output | journeys |
|---|---|---|---|
| quick | a passing question worth finding again (`quick.md:3`) | one transcript message | L E |
| question | understanding: definitions, examples, edge cases (`question.md:3`) | transcript; annotations only on faults | L E |
| audit | what a result actually uses: hypotheses, citations, standalone (`audit.md:3`) | ledgers; annotations and suggested edits | P E |
| referee | whether the mathematics is right, hostile (`referee.md:3`) | verdict; Revision/Suggestion/Question annotations | P E |
| review | improving a text before others read it, every finding graded (`review.md:3`) | graded annotations plus suggested edits that answer them | P |
| simplify | shorter text, same mathematics (`simplify.md:3`) | one suggested edit per simplification; agent document for merges | P |
| flow | reading order and clarity for a named reader (`flow.md:3`) | suggested edits; agent document for structure | P |
| draft | new mathematics or text from the author's plan (`draft.md:3`) | an agent document by default | E |
| ingest | a cited paper to trust or understand: digest checked, results proposed, overview (`ingest.md:3`) | suggested edits on digest nodes, proposals, the work's overview | L |

How an agent is put into one today:

1. **The agent picks.** The orientation's section 6 tells it to reach for a mode when one fits, without waiting to be asked (`loom/src/loom/assets/ai/orientation.md:66-68`); the MCP server's instructions end with the mode index (`loom/src/loom/ai/orient.py:156`); the agent then reads the mode with `loom_ai_mode`.
2. **The person names one in the agent app.** Each mode is an MCP prompt taking one word, a target (`loom/src/loom/mcp/prompts.py:12-30`): `/mcp__loom__review KEY` in Claude Code. Whether Claude Desktop and Codex surface MCP prompts was not verified here.
3. **From the viewer: no.** The only viewer act that asks an agent for work is "Ask an agent" for a work's overview, which writes an annotation (`arras/src/lib/review/ask.ts:12`) and wakes nobody (`loom/src/loom/render/api.py:5`). Annotation types carry instructions for agents (`arras/src/lib/shell/settings/catalog.ts:64`), so an annotation of a type is a request an agent finds when it next calls `loom_since`.

Judgment: five of the nine serve PROOFREAD and overlap (audit and referee both "read the closure and check"; simplify and flow both "same mathematics, better text"). A tester needs at most five: **ask** (quick and question), **read** (ingest), **check** (referee, with audit as its narrower form), **proofread** (review, with simplify and flow as options), **write** (draft).

## 6. Findings

| id | finding | evidence | weight | effort | rec |
|---|---|---|---|---|---|
| INV-1 | Nothing starts the viewer without a terminal. `serve` is not an MCP tool, so a Claude Desktop agent cannot start it, and a Codex agent that runs it in its shell blocks on a process that never exits. | `loom/src/loom/ai/layout.py:65`; `loom/src/loom/cli/serve_cmd.py:64-68` | blocks | a day | fix: `loom mcp` starts or finds the quilt's server |
| INV-2 | Claude Desktop is attached by hand-editing a global JSON file, and the entry pins one quilt by absolute path, so a second quilt means editing it again. | `loom/src/loom/ai/clients.py:57-63`, `:108` | blocks | a day | fix |
| INV-3 | Creating a quilt and bringing in a draft are CLI-only, author-only, and need a quilt before any server can run. | `loom/src/loom/cli/serve_cmd.py:31`; `loom/src/loom/ai/layout.py:32` | blocks | days | fix: agent tools for `init`/`import`, or a quilt-less home server |
| INV-4 | The agent layer cannot be written from the viewer; Settings › Agents prints `loom ai init` and the one related endpoint refuses without it. | `loom/src/loom/config_edit.py:469`; `loom/src/loom/render/api.py:607` | blocks | hours | fix: fold into quilt creation |
| INV-5 | Overleaf pairing, fetching and publishing are CLI-only and none is an agent command; only preview and incorporate exist over HTTP. The Overleaf-only tester cannot complete PROOFREAD without a terminal and their own Git clone. | `loom/src/loom/cli/sync.py:114`; `loom/src/loom/render/api.py:746-788`; `loom/src/loom/ai/layout.py:21-38` | blocks (one tester) | days | fix fetch and publish now; defer pairing to a guided step |
| INV-6 | By default an agent may rewrite the person's drafts in place unseen: `deny = []` and `track_edits = false` in a new quilt, and the orientation lists the author's documents as editable. This breaks PROOFREAD's promise. | `loom/src/loom/cli/quilt.py:39-42`; `loom/src/loom/assets/ai/orientation.md:30` | blocks | hours | fix: default `track_edits = true`, or deny the person's documents |
| INV-7 | Text an AI proposes arrives by three channels (suggested edits, agent documents, in-place edits), and Review splits them across Your Changes and Proposed Changes, which also hold blocks to accept, Overleaf pulls and library proposals. The author wants exactly two things from Review. | `arras/src/lib/review/sections.ts:32-36`; `arras/src/routes/review/+page.svelte:2`; `arras/src/routes/review/proposed/+page.svelte:2` | hurts | days | fix: Review = changed mathematics + AI-proposed edits; library proposals to Library; hide The Record and Problems |
| INV-8 | Nothing shows whether an agent is attached or what it last did: the MCP server logs a call only into an active session's `run.log`, and Settings › Agents reports files and permissions only. | `loom/src/loom/mcp/server.py:331-347`; `loom/src/loom/config_edit.py:463-471` | hurts | a day | fix: "agent last seen" from the per-name markers `since` keeps |
| INV-9 | The agent cannot add a paper to the library, by design; in a no-command v0.1, "add this paper" said to the agent fails. | `loom/src/loom/ai/layout.py:32`; `loom/src/loom/render/api.py:190` | hurts | hours | fix: admit `library add` (attributed) for agents |
| INV-10 | Restore means three different acts: CLI writes a new document, HTTP restores in place, `revert` prints a patch; the viewer's act has no CLI/MCP form. | `loom/src/loom/cli/history_cmds.py:1041-1057`; `loom/src/loom/render/api.py:507-563` | hurts | hours | fix: one in-place restore on all surfaces; remove the others |
| INV-11 | Fifteen HTTP-only operations have no CLI or MCP twin (section 2b), so the "three surfaces over one set of operations" goal fails today. | `loom/src/loom/render/api.py:23-71` against `loom/src/loom/cli/__init__.py:55-94` | hurts | days | fix the ones kept; drop the rest |
| INV-12 | `session-use` and `session-purpose` are served and documented but no viewer code calls them; the viewer's "current session" is browser-local and differs from the CLI's. | `loom/src/loom/render/api.py:45,51,1103,1116`; `arras/src/lib/sessions/sessions.svelte.ts:44` | cosmetic | hours | remove |
| INV-13 | Sessions and transcripts are load-bearing in the agent rules: every report goes to `session say`. Hiding sessions in the viewer is cheap; removing them means rewriting the rules and the modes' "Report" sections. With Desktop or Codex the same conversation already lives in the app. | `loom/src/loom/assets/ai/rules.md:41-46`; `loom/src/loom/assets/ai/orientation.md:64` | hurts | hours to hide; days to remove | hide now, decide removal separately |
| INV-14 | Every MCP call is a fresh `python -m loom` subprocess that scans the quilt again. | `loom/src/loom/mcp/server.py:198-205` | hurts (slowness) | days | fix (likely shared with the speed auditor) |
| INV-15 | A human cannot search the library's results or page text, or relate two results, in the viewer; both are agent-only. | `arras/src/lib/components/Palette.svelte:11`; no `relate` endpoint in `loom/src/loom/render/api.py:23-71` | hurts | a day | defer relate; fix search if EXPLORE without an agent matters |
| INV-16 | No page lists every note; notes are annotations of the type listed in Notes, shown per text only. The research state and Markdown files are two more note stores. | `arras/src/lib/review/SideList.svelte:2`; `docs/work-queue/WQ-69-every-note.md` | hurts | a day | fix |
| INV-17 | Node surgery and history bookkeeping (`atomize`, `fork`, `linearize`, `live`, `mv`, quilt-wide `stamp`, `history verify`, `history restore --to`, `revert`) serve no journey; that is 9 of 33 author commands. | section 3 | cosmetic (testers never type) | hours to hide; days to remove | remove atomize/fork/linearize/live; hide the rest |
| INV-18 | Review › Problems and Settings › Problems show loom's own lint, including agent copies' and cited works' remarks; six commands overlap as diagnostics. | `arras/src/routes/review/problems/+page.svelte:2`; section 3 | hurts | hours | hide except compile errors in the person's files |
| INV-19 | Development indexes (threads, tags, taxa, not in a document) and the PDF page editor serve no journey. | `arras/src/lib/shell/views.ts:39-48`; `arras/src/lib/pdf/PagesEditor.svelte:2` | cosmetic | hours | remove indexes; hide the page editor |
| INV-20 | "Suggestion" is both a default annotation type and the everyday name for a suggested edit, two different objects with different buttons. | `loom/src/loom/assets/init/annotation-types.toml`; `loom/docs/cli-reference.md:265` | hurts | hours | fix: rename the type |
| INV-21 | Ten approval verbs for four acts, six words for "result", six for "version", four for "agent document"; "look" means both styling and the tracked-edits snapshot. | section 4 | hurts | a day (viewer strings) | fix: the nine-word vocabulary |
| INV-22 | A person cannot start a mode from the viewer; MCP prompts exist but their support in Claude Desktop and Codex is unverified, and "Ask an agent" wakes nobody. | `loom/src/loom/mcp/prompts.py:12-30`; `loom/src/loom/render/api.py:5` | hurts | a day | fix: per-mode "copy request for your agent" beside Quote |
| INV-23 | Nine modes overlap; five serve PROOFREAD. | section 5 | cosmetic | hours | fix: merge to five |
| INV-24 | `upgrade` and `doctor` are manual, though both are safe to run unattended (upgrade keeps edited mode files; doctor writes nothing). | `loom/src/loom/ai/layout.py:3`; `loom/docs/cli-reference.md:82` | hurts | hours | fix: run upgrade on start; show doctor in Settings |
| INV-25 | One server per quilt on a fixed default port, refused when busy. | `loom/src/loom/render/serve.py:32`; `loom/src/loom/cli/serve_cmd.py:16` | hurts | hours | fix: pick a free port |
| INV-26 | The install line names `github.com/ikmartin/loom`, while this repository is `ikmartin/loom-arras` with the package under `loom/`. | `loom/README.md:21`; `git remote -v` | blocks if the URL is wrong | hours | fix (check first) |
| INV-27 | The viewer reads and annotates but never edits text: documents, notes, the research state and overviews are edited elsewhere (`open` launches the file's app). The Overleaf-only tester edits on Overleaf. | no page or document write endpoint in `loom/src/loom/render/api.py:23-71`; `write` agent-only, `loom/src/loom/ai/layout.py:58` | irrelevant (design choice), but say it in onboarding | — | keep |
| INV-28 | `library-update` from the viewer needs `loom serve`'s job runner, while `loom library update` runs anywhere. | `loom/src/loom/render/api.py:132` | cosmetic | — | keep |

Not verified, for the lead: whether Claude Desktop and Codex show MCP prompts; whether a document drafted by `import` (which adds `\usepackage{loom}`, `loom/src/loom/reshape/importer.py:132`) compiles on Overleaf after `sync publish`, since `sync.py` does not mention `loom.sty`; and whether Overleaf's Git access requires a paid plan.
