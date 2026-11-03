# Invariants

An invariant is a rule loom keeps because breaking it once caused a real failure that a simpler design would bring back; each entry gives the rule, the failure, the test that holds it and the old decision records, and its heading is the name a change cites it by. An invariant changes only by a dated line added to its entry (`**2026-11-02.** What changed.`), explained in the commit message; there is no other decision log.

## The author's authority

### The author's acts refuse any agent, whatever name it declares

**Rule.** The author's acts (`accept`; `library verify`, `discard`, `ignore`, `add`, `import` and `drop`; `session delete --purge`; `ai discard`; `sync publish --push` and `sync incorporate`) refuse a declared agent name, and under an agent marker refuse any name (K5). `refuse_under_agent` is the guard.

**Why.** In the first study an agent verified its own proposal and loom named the author as verifier, since the name came from git, which the agent's shell shares. Later, `accept --author …` and `refs verify --author …` from an agent's shell were accepted.

**Guard.** `loom/tests/unit/test_writer.py::test_every_act_that_is_the_authors_or_destroys_refuses_under_an_agent_marker`, `loom/tests/unit/test_writer.py::test_the_authors_verbs_refuse_a_declared_agent_whatever_shell_it_is_in`

**Record.** DR-185, DR-203, DR-325-ikmartin

### The network is the person's to allow

**Rule.** Loom looks works up and fetches them only under `[library] online = true` or a run the person allows: `--online` in a terminal of their own, or "Allow and run" in the viewer, which sends `online` with `library-update`. Neither is written anywhere. Under an agent marker `--online` is refused without the standing consent, and `library-update` refuses a declared agent, so an agent never grants itself the network.

**Why.** Looking a work up tells a service what the person is reading, and a fetch brings files into their quilt; that is consent only they can give, and an agent asking for it on their behalf is exactly the case to stop.

**Guard.** `loom/tests/unit/refs/test_library_store.py::test_online_is_refused_under_an_agent_without_standing_consent`, `loom/tests/unit/render/test_write_api.py::test_each_endpoint_writes_and_refuses_over_the_wire[library-update]`

**Record.** DR-193; plan 0.24.1

### Identity is never stored in the quilt

**Rule.** The person acting is named by `--as`, then their own user config, then git, and never by anything the quilt tracks. An `[author]` table in `config.toml` identifies nobody.

**Why.** DR-189 made the quilt's tracked `config.toml` settle whom its records name, so cloning a quilt made Bob review and accept under Alice's name.

**Guard.** `loom/tests/unit/test_personal_acceptance.py::test_local_identity_settings_and_missing_identity`

**Record.** DR-189 (reversed), DR-304-luisa

### A passing check is never called verification

**Rule.** The test that a quotation is on its page is "the anchor check", and a proposal that passes it is checked. "Verified" is only the state the author's act produces: loom never prints it for a check, and never hands an agent the author's verify command (P15).

**Why.** `refs propose --help` said "verified against the page", and an agent then told its author "All 13 verified" of thirteen proposals nobody had read.

**Guard.** `loom/tests/unit/test_refs_layer.py::test_propose_does_not_hand_an_agent_the_authors_verb`

**Record.** DR-183

### Overlooking is never accepting

**Rule.** In Incoming every mathematical item starts pending, and only an explicit Accept records an acceptance. Incorporating the source accepts nothing; an item never visited, an item held, and an unchanged proof under a revised statement all stay pending.

**Why.** No incident is recorded. Incoming applies a coauthor's pull whole, so the short path is to accept what was applied, which would record as read every item the author scrolled past.

**Guard.** `loom/tests/unit/test_adopt.py::test_incoming_explicit_acceptance_keeps_unvisited_dependents_pending`

**Record.** DR-314-luisa, DR-316-luisa

## Agents and configuration

### One table says what an agent may run, and everything else refuses

**Rule.** `AGENT_COMMANDS` in `loom/src/loom/ai/layout.py` is the only list of what an agent may run. The MCP server's tools, the Claude and Codex permission files in both variants, and the list in `ai/rules.md` are generated from it. The server's prompts and resources run only commands from it that read. Under an agent marker every other command refuses before reading anything, so a new command is the author's until admitted.

**Why.** The rules' Never section and the permission file were two hand-kept deny lists, and they drifted: `loom upgrade` was in neither, and the alias `loom canonise` walked past the deny on `loom canonize`.

**Guard.** `loom/tests/unit/test_ai_layer.py::test_the_allow_list_and_the_permission_file_cannot_disagree`, `loom/tests/unit/test_ai_layer.py::test_codex_is_given_the_same_policy_as_claude`, `loom/tests/unit/test_mcp_tools.py::test_the_tools_are_the_agent_commands_and_none_of_the_authors`, `loom/tests/unit/test_mcp_resources.py::test_every_command_a_prompt_or_resource_runs_is_an_agent_command_that_only_reads`

**Record.** DR-154, DR-173, DR-333-ikmartin

### Loom never runs a command the quilt carries

**Rule.** Configuration that names a command for an agent's app is generated on the machine that runs it and never committed. `loom ai init` writes the MCP client files (`.mcp.json`, `.codex/config.toml`, `.gemini/settings.json`, `.cursor/mcp.json`) with this machine's absolute paths, and they are gitignored. `ai init` writes over no client file that git tracks or that holds anything but loom's server, and `loom doctor` fails when git tracks one.

**Why.** No incident is recorded. While `loom serve` ran the agent command when a message waited, a tracked one would have let cloning and serving someone's quilt run whatever they committed. A client reading a committed config file runs it the same way (`claude -p` loads a project `.mcp.json` without asking).

**Guard.** `loom/tests/unit/test_clients.py::test_every_client_file_is_gitignored`, `loom/tests/unit/test_clients.py::test_a_client_file_git_tracks_is_not_written`, `loom/tests/unit/test_doctor.py::test_a_client_file_git_tracks_fails`

**Record.** DR-273-ikmartin

**2026-10-26.** Loom starts no agent (plan 0.20.1): `ai/ai-config.toml`, `[ai] launch` and the launcher are gone, and with them this rule's two guards and the unchecked `.claude/settings.json` a launched turn was given.

**2026-10-28.** The client files live in the quilt, gitignored, rather than being passed to the client by name. Only Claude Code takes a file by name; every other app reads one in the project or in the person's home. So the guard moved from where the file is to whether git tracks it (plan 0.21.6).

### Generated agent configuration is tested against the real client

**Rule.** A change to what loom generates for an agent client (permission files, Codex rules, MCP client files) is tried with the client itself, run as a person starting an agent in the quilt would run it (`claude -p --settings …`), before it ships. Unit tests check only the shape loom believes right.

**Why.** The permission file's `Write` rules passed every unit test and were never enforced: Claude Code matches only `Edit` rules to paths. Then root-relative allows passed too, but under `--settings` a leading `/` means `.claude/`, so every write a launched agent made was refused.

**Guard.** The opt-in `client` tier, run by hand with `scripts/verify client` and never in CI, since it spends on the account of whoever runs it:
- `loom/tests/client/test_claude.py::test_a_launched_claude_writes_where_the_quilt_lets_it_and_not_where_it_protects`;
- `::test_a_launched_claude_runs_the_agents_loom_commands_and_not_the_authors`, on the shell variant;
- `::test_a_claude_attached_over_mcp_writes_as_its_agent_and_runs_no_loom_in_a_shell`, on the MCP variant.

`loom/tests/client/test_codex.py` and `test_gemini.py` try the server each app's file names, and skip where the app is not installed. Neither has run yet.

**Record.** DR-275-ikmartin, DR-343-ikmartin

**2026-10-26.** Launch commands are gone with launching (plan 0.20.1); the client tier runs `claude -p` itself, as a person starting an agent in the quilt would.

**2026-11-01.** The boundary test writes an open file, the agent's copies, a directory `[agents] deny` names and one of loom's records, in the mode that accepts edits, since outside the protected paths whether the client asks is the person's setting (plan 0.22.6).

### Where an agent may write is one table, which loom's own commands enforce in every client

**Rule.** `loom/src/loom/agents.py` holds the boundary: the agent's own places (its session, `.loom/build/`, `.loom/copies/`), what is always protected (loom's records under `.loom/`, the history, `config.toml`, the research state), and the person's `[agents] deny`. Every loom command that writes a path an agent chose refuses an agent a protected one by its one predicate, and Claude Code's permission file is rendered from its tables. Every `.loom/` path loom names is an agent's place or protected.

**Why.** Only Claude Code's file can refuse an edit by path, so a boundary kept only there held for one client of four. And a record added under `.loom/` without a deny of its own would be open to an agent's edits, since the agent's places sit beside the records there and a deny on `.loom/` would beat their allows.

**Guard.** `loom/tests/unit/test_paths.py::test_every_path_under_loom_is_an_agents_place_or_protected`, `loom/tests/unit/test_destination.py::test_an_agent_is_refused_what_the_quilt_protects_and_a_person_is_not`, `loom/tests/unit/test_ai_layer.py::test_the_deny_list_is_rendered_into_the_permission_file_beside_what_is_always_protected`

**Record.** Plan 0.22.6

**2026-11-02.** The viewer's Settings edits `[agents] deny` and rewrites Claude Code's permission file to it, each only on the author's act: `settings-save` and `agents-update` refuse a declared agent like every other author act over the API (plan 0.23).

### Agent instructions name only commands the agent may run

**Rule.** The orientation, the rules and the mode files tell an agent to run only commands in `AGENT_COMMANDS`; an author's command appears in them only where the text says it refuses the agent.

**Why.** The orientation told agents to run `loom linearize`, which the permission file denied and which, had it run, would have superseded the spine and every file it inlined and reassigned `main`.

**Guard.** `loom/tests/unit/test_ai_layer.py::test_every_command_the_agent_is_told_to_run_is_allowed`

**Record.** DR-155

### An agent deletes nothing from a session's directory

**Rule.** An agent never deletes a file in a session's directory, since an annotation or a note may point at it. Its scripts, backups and staging files go under `.loom/build/SESSION/`, and the permission file denies `Bash(rm *)`.

**Why.** An agent tidying a session cluttered with its own intermediates tried to `rm` a file one of its own annotations pointed at. A shell permission cannot be confined to one directory, so the fix was a separate place for intermediates.

**Guard.** `loom/tests/unit/test_ai_layer.py::test_an_agent_is_never_allowed_to_delete`

**Record.** DR-315-ikmartin

### Upgrade never destroys an author's edit

**Rule.** `loom upgrade` and `loom ai init` keep one line of loom's in `CLAUDE.md`, `AGENTS.md` and `GEMINI.md`, replacing the other variant's line where it stands, and touch nothing else there. An edited mode file or orientation is kept, with the shipped text written beside it as `.new`; an edited `loom.sty` is kept as `loom.sty.old` before it is replaced.

**Why.** Upgrade wrote `CLAUDE.md` and `AGENTS.md` whole whenever they differed from the shipped copy, so an author who had added instructions lost them, and an edited orientation was overwritten with no warning and no backup.

**Guard.** `loom/tests/unit/test_ai_layer.py::test_root_files_carry_one_line_and_keep_the_authors`, `loom/tests/unit/test_ai_layer.py::test_upgrade_preserves_edited_modes`, `loom/tests/unit/test_ai_layer.py::test_upgrade_keeps_an_edited_loom_sty_as_old_and_says_so`

**Record.** DR-151, DR-170, DR-333-ikmartin

### Where the person is looking is never written down

**Rule.** The place a viewer tab reports to `loom serve` (`here`) is held in the server's memory and nowhere else: no file under the quilt, no log line, no build output. `GET /_api/here` serves it only with the server's token and to its own origin, and stopping the server forgets it.

**Why.** Where a person is reading, and the words they selected, are where they are, not a record of anything they did (P2). Written down, they would be committed by the next `git add`, or read by whoever opens the quilt after them.

**Guard.** `loom/tests/unit/render/test_here.py::test_the_place_is_held_in_memory_and_served_only_with_the_token`

**Record.** plan 0.21.8

## Records, history and sync

### Posting to an inbox takes a lock

**Rule.** `post` holds an exclusive lock on the session's `inbox.jsonl` from reading the last sequence number to appending the new event, so two writers never draw the same number.

**Why.** `post` read the last number and appended with nothing between, which was harmless while one party wrote at a time and a race once an agent could answer while the author typed in the viewer.

**Guard.** `loom/tests/unit/test_transcript.py::test_two_writers_never_draw_the_same_number`

**Record.** DR-265-ikmartin

### Resolving a name never creates anything

**Rule.** One resolver turns a `--session` value into a session. A value that matches nothing, or several, is an error that says what it saw, and nothing on disk changes; making a session is an act of its own.

**Why.** A second resolver took a run's name as a path and created that directory, which then shadowed the real run in every later lookup. The beta experiment lost nineteen findings this way: `loom ai findings` said "no findings yet", and nothing was an error.

**Guard.** `loom/tests/unit/records/test_run_resolution.py::test_an_unmatched_session_is_an_error_and_never_a_path`

**Record.** DR-167

### A write that says nothing is refused

**Rule.** A reply with no message, an edit that changes nothing, and an edit to an empty body are refused with a non-zero exit and write nothing. A bare resolution, and a note that only records a reading, stay legal.

**Why.** `--reply` and `--resolve` read their one argument as a target, so the author's answers to findings were filed as `body: ""`, with exit 0 and no warning. Loom's own fixture generator did it twice, and the synthetic quilt shipped two empty replies nobody saw.

**Guard.** `loom/tests/unit/records/test_review_commands.py::test_a_verb_that_answers_nothing_is_refused`

**Record.** DR-171

### Review records are appended, never rewritten

**Rule.** Every review event is one line appended to `.loom/annotations/log.jsonl`, and an annotation's state is the replay of its events. The history ledger and a session's inbox are appended the same way (P2).

**Why.** Records were files rewritten whole. When an agent resolved its own finding, the parent and the writer were two copies of one file and the second write clobbered the resolution, which is the case an agent hits on every re-check.

**Guard.** `loom/tests/unit/records/test_review_commands.py::test_a_run_resolves_its_own_annotation`

**Record.** DR-147 (the annotation log, 2026-09-18; a second DR-147 is about base paths)

### A re-check edits a finding; it does not reply to it

**Rule.** A finding that still stands is restated with an `edited` event, which supersedes its body and keeps the earlier one in the log. A reply is for talking to the author.

**Why.** Before `edited` existed a re-check could only reply, and three passes over a finding that still stood left it wearing three restatements of itself.

**Guard.** `loom/tests/unit/records/test_recorded.py::test_an_edit_restates_the_finding_against_the_text_as_it_is_now`

**Record.** DR-147 (the annotation log, 2026-09-18)

### The log's columns use underscores, and a line that does not read is reported

**Rule.** Log lines carry `annotation_kind` and `reply_to`. A line with an unknown or missing kind, a malformed id, or a reply to nothing is reported as `loom:foreign-annotations`, never silently defaulted.

**Why.** The only written column list, in plan 0.10, spelled `annotation-kind` and `reply-to`. A log written from it lost its kind and its parent on every line and said nothing, because a missing kind silently became `objection`.

**Guard.** `loom/tests/unit/records/test_hostile_log.py::test_a_missing_kind_is_reported_rather_than_assumed`

**Record.** DR-165

### Printing a patch records nothing

**Rule.** `loom revert` prints a patch and writes nothing to the history; applying the patch is the author's act. The same holds for any command that prints a patch (K4).

**Why.** `loom revert` appended a revert to the history every time it printed a patch, applied or not, with `--json` and with nothing to change, so four runs left four reverts of a file that never changed.

**Guard.** `loom/tests/unit/history/test_commands.py::test_revert_prints_a_patch_and_records_nothing`

**Record.** DR-326-ikmartin

### The index is written last

**Rule.** What points at other files is written after them: a history step's version files before its ledger line, and every build fragment, written beside its target and renamed into place, before `manifest.json`, itself written by rename.

**Why.** No incident is recorded. An interrupted step must leave a directory nothing refers to, not a ledger line naming files that do not exist; and arras reloads when the manifest changes, so a manifest written first would name fragments that are not there yet.

**Guard.** `loom/tests/unit/history/test_commands.py::test_a_step_is_written_whole_before_the_ledger_line_that_names_it`, `loom/tests/unit/render/test_build.py::test_the_manifest_is_renamed_into_place_after_every_file_it_publishes`

**Record.** DR-83, DR-134

**2026-10-26.** Both orderings are now tested, each failing when its order is reversed.

### No step is recorded beside an interrupted one

**Rule.** A step directory no ledger line names, left by a step interrupted before it was recorded, is reported by `loom history verify` as `loom:history-interrupted` with the command that removes it; every command that records a step (stamp, draft, import, adopt) refuses while one is there, writes nothing, and names that command. Loom removes nothing itself (P13).

**Why.** The test that proved a step's files are written before its line found that `history verify` never reported the directory such an interruption leaves, that retrying the stamp crashed on it with a traceback, and that a stamp under another name wrote a second directory with the same step number.

**Guard.** `loom/tests/unit/history/test_commands.py::test_a_step_is_never_recorded_beside_an_interrupted_one`

**Record.** Commit `3310c343`.

### Two definitions of one id leave it conflicted

**Rule.** When an id is defined twice, by two files or within one, the id has no text and no winner; `duplicate-id` names every file, and whatever needs the text (accept, annotate, closure, stamp, revert) refuses until one definition goes.

**Why.** Picking one by walk order publishes a copy chosen by filename while a closure inlines the other, records acceptances against a text nobody chose, and lets an agent edit one copy while the other silently disagrees. Later, `loom inline` defined every id twice and reported "Identity test: pass".

**Guard.** `loom/tests/unit/scan/test_conflicts.py::test_two_files_defining_one_id_leave_it_conflicted`, `loom/tests/unit/scan/test_conflicts.py::test_two_copies_in_one_file_are_conflicted_too`, `loom/tests/unit/render/test_canon.py::test_a_conflicted_key_is_published_with_no_text`

**Record.** DR-135, DR-326-ikmartin

**2026-10-26.** Two definitions within one file are conflicted too. The later one used to hold the id silently; the only fix offered is a fresh id (`loom id --next`), since forking splits documents, not one file. Commit `becf7258`.

### Sync never writes to the quilt's own repository

**Rule.** Loom's Git runs only in the sync directory the record names, the person's clone of the workspace. `sync init` refuses a directory that is the quilt's own repository or a worktree of it, holds a quilt, follows a remote of the quilt's own repository however that is spelled, or sits inside one of loom's own directories; `sync publish --push` refuses a workspace that holds a quilt.

**Why.** `sync init` defaulted to `--remote origin --branch main`, usually the quilt's own repository, and `sync publish --push` then replaced that branch with the source-only projection, removing `config.toml`, `ai/` and `.loom/` from what a coauthor pulls.

**Guard.** `loom/tests/unit/test_sync.py::test_sync_init_refuses_the_quilt_s_own_upstream_however_it_is_spelled`, `loom/tests/unit/test_sync.py::test_init_refuses_the_quilt_s_repository_and_loom_s_own_directories`, `loom/tests/unit/test_sync.py::test_publish_push_refuses_a_workspace_that_holds_a_quilt`, `loom/tests/unit/test_sync.py::test_the_quilt_s_own_repository_is_never_touched`, `loom/tests/unit/test_sync.py::test_the_sync_directory_s_files_and_branch_are_never_touched`

**Record.** DR-326-ikmartin, DR-333-ikmartin

**2026-10-31.** Loom no longer clones the workspace into `.loom/workspace/`. The person clones it into a directory of their own and names it with `sync init DIR`, and loom runs Git there as it did in its clone, moving only its own refs and the remote's branch (plan 0.22.2). The guards moved to pairing: what used to be one URL check now covers the directory itself.

## The library

### A digest records what it was read from

**Rule.** A digest's `extracted-from` names the artifact its statements were read from, apart from `published-as`, the work the bibliography cites; a fetched source records the identifier it was fetched on. When the two differ, `loom:unverified-locators` says so.

**Why.** Preprints fetched into the directory named for the published DOI were labelled by that directory, so 11 of the study's 16 digests claimed the DOI and the version warning never fired; one gave the preprint's Theorem 3.4, which is the published Theorem 3.5 with a different conclusion.

**Guard.** `loom/tests/unit/test_refs_layer.py::test_a_source_fetched_on_a_preprint_id_says_so_in_the_digest`, `loom/tests/unit/test_digest.py::test_unverified_locators_when_the_artifact_and_the_cited_work_differ`

**Record.** DR-109, DR-181

### A proposal is never a dependency

**Rule.** The scan makes no edge to a proposed result from outside its own file, whether by `\cite[postnote]`, `\ref` or `\uses`: `loom:cites-proposed-node` (warning) reports the citation, and verifying the proposal makes it a dependency. So nobody's unchecked statement enters a closure, a closure document or a compile (P15).

**Why.** Every postnote match became an edge, proposals included, so `loom source --closure` and `loom compile KEY` carried statements nobody had vouched for, while `refs/proposals.py` promised, as "a structural guarantee", that a proposal could enter no closure. Found by the review of the relloc quilt on 2026-10-26.

**Guard.** `loom/tests/unit/test_refs_layer.py::test_a_cited_proposal_is_no_dependency_until_it_is_verified`

**Record.** Commit `3f38e7c9`.

### A document is filed only on a strong match

**Rule.** A PDF is filed against a bibliography entry, by `library add`, only when its text holds the entry's identifier, or the entry's full title with its first author leading the byline. Anything weaker is skipped, and the reason given.

**Why.** A handbook that named Olsson fifth and shared half the title of his 2003 paper was filed as that paper on those two weak signals, and the real paper was then skipped because the slot was taken.

**Guard.** `loom/tests/unit/refs/test_library_store.py::test_a_weak_match_is_skipped_with_its_reason`, `loom/tests/unit/refs/test_scan.py::test_gathering_files_a_document_against_an_entry_only_on_a_strong_match`

**Record.** DR-331-ikmartin

### Redoing a step keeps what a person verified

**Rule.** `library update --redo` and `library drop` keep every result a person verified: its record, and its text in the digest byte for byte.

**Why.** `loom refs build --force` rewrote a digest from the paper's source and deleted every result the author had verified into it, while `results.json` still said `verified` and `refs recheck` reported nothing moved.

**Guard.** `loom/tests/unit/refs/test_library_store.py::test_redo_keeps_a_verified_result_byte_identical`, `loom/tests/unit/refs/test_library_regrade.py::test_drop_then_redo_keeps_the_authors_verified_text`

**Record.** DR-326-ikmartin, DR-331-ikmartin, DR-333-ikmartin

### A paper outside the quilt is compiled from a clean copy

**Rule.** Importing a paper and extracting a cited work's source compile a scratch copy of the paper's directory without its build products (a `.bbl` stays only when there is no `.bib`). latexmk never runs in the paper's own directory.

**Why.** latexmk rewrites `.bbl` and `.fdb_latexmk` in its working directory even under `-outdir`. On the author's relative localization paper, an editor's leftovers made it run bibtex where the paper uses biber, the import refused a paper that compiles, and the run rewrote the author's own `.bbl`.

**Guard.** `loom/tests/unit/test_paper.py::test_import_leaves_the_paper_directory_and_no_scratch_behind`

**Record.** DR-186

## Rendering and the viewer

### A transcription is judged against the page itself

**Rule.** Where the author verifies a proposed result, the viewer shows the PDF page itself at the anchor, quotation marked, beside the rendering, and names the rendering's words the quotation lacks. The text layer is shown only as what the anchor check read.

**Why.** The text layer drops sub- and superscripts and keeps one `X` for a stack and its space. In the study three wrong renderings passed every text check, one moving a hypothesis from the space to the stack, and the author, editing against page text, twice deleted the paper's own words.

**Guard.** `arras/tests/e2e/library.e2e.ts::a proposal shows the page itself, and names the words of the rendering the page does not have`

**Record.** DR-179, DR-201

### A mark never splits a formula

**Rule.** An annotation's mark takes a formula whole or not at all: a quote inside a displayed formula marks the whole display, and no tag is ever placed inside `\(…\)`.

**Why.** A mark's tag inside `\(…\)` stopped MathJax reading the formula at all, and a quote that crossed markup fell back to a bar down its block's left edge, which read as punctuation in the text.

**Guard.** `loom/tests/unit/render/test_marks.py::test_a_quote_inside_a_formula_never_puts_a_tag_inside_it`, `loom/tests/unit/render/test_marks.py::test_a_quote_around_math_takes_the_formula_whole`

**Record.** DR-244-ikmartin

### Every write to the viewer's server carries a token

**Rule.** `loom serve` refuses a POST unless it is `application/json`, carries the `X-Loom-Token` written to `.loom/serve.json` and served to the viewer, and names no Origin but this server. This is CSRF protection, not a login.

**Why.** No incident is recorded. A browser blocks a cross-origin response but never the request, so without the token any page the author had open could POST into the quilt and create, resolve or discard annotations.

**Guard.** `loom/tests/unit/render/test_write_api.py::test_a_write_without_the_token_is_refused_over_the_wire`, `loom/tests/unit/render/test_write_api.py::test_the_write_api_refuses_a_post_from_another_page`

**Record.** DR-203

### A page the quilt holds never runs as the viewer

**Rule.** `loom serve` sends everything but the viewer's own bundle, which is every file under `/build/` and `/digests/storage/` and every JSON answer, with `Content-Security-Policy: sandbox` and `X-Content-Type-Options: nosniff`, so a page there runs no script and has an opaque origin. `GET /_api` gives the token only to a request that no browser says came from another page (`Origin`, `Sec-Fetch-Site`). Over the API, `review-decision` and `review-finish` refuse a declared agent, like the author's other acts there (K5).

**Why.** Found 2026-10-30 by reading the code for the open-quilt study, and reproduced before it was fixed. An agent writes the build output, served at `/build/`, and an HTML or SVG page it left there ran as the viewer when the author opened it, for instance from a link in a transcript. The page read the token from `/_api` and posted a write naming no author, which the publisher takes for the author's own click; `review-finish` posted that way records the author's acceptance. The token kept other sites out but not a page served from the viewer's own origin.

**Guard.** `loom/tests/unit/render/test_write_api.py::test_a_page_the_quilt_holds_is_served_with_no_origin_of_the_viewers`, `loom/tests/unit/render/test_write_api.py::test_the_token_is_served_only_to_the_viewers_own_origin`, `loom/tests/unit/render/test_write_api.py::test_each_endpoint_writes_and_refuses_over_the_wire` (`review-decision`, `review-finish`), `loom/tests/unit/render/test_files_served.py::test_a_shown_file_is_served_sandboxed_on_the_viewers_origin`, `loom/tests/unit/render/test_files_served.py::test_an_html_page_runs_on_the_frames_origin_with_the_bridge_and_nothing_of_looms`, `arras/tests/e2e-write/origin.e2e.ts`, `arras/tests/e2e-write/files.e2e.ts`

**Record.** `docs/reports/open-quilt-study.md`

**2026-11-02.** The project's shown files are served sandboxed on the viewer's origin too, at `/_files/`. An HTML file the viewer frames runs on a second loopback origin, the frames origin, where its scripts and embedded players work: that origin serves shown files and nothing of loom's, answers only its own host, and is refused by the write API like any other page, so a framed page still never runs as the viewer (plan 0.22.7).

### Loom opens only documents in their application

**Rule.** `POST /_api/open` opens an application by a plain name, or a shown file whose suffix is on `loom.files.OPENABLE` (notebooks, spreadsheets, office documents, Anki packages, audio, video, books) and that has no executable bit. Any other file, a hidden one, and a name that could be a path or an option are refused.

**Why.** An agent may write nearly anywhere in the quilt, so it can write a file and a link to it that the person clicks. A click that opened a script, a `.command` or an application bundle would run the agent's code as the person.

**Guard.** `loom/tests/unit/test_files.py::test_loom_opens_an_application_or_a_document_and_never_a_file_that_runs_code`, `loom/tests/unit/render/test_files_served.py::test_open_is_the_persons_click_and_never_runs_code`

**Record.** Plan 0.22.7

### Undo writes a person's file only on their act, with what it replaces kept first

**Rule.** `loom changes --undo` and the API's `changes-undo` write an open file back as it was at the person's look only when the person asks, never an agent (K5), and store the file's text now in the history's texts before writing, with a ledger line naming both hashes. A file new since the look has no undo.

**Why.** Since plan 0.22.6 agents edit open files in place, and Review's Changes is where the person keeps or throws away what they did. An undo is loom writing a person's file, which P7 allows only on the person's act and only with the old text kept, so a wrong undo can itself be undone from the history.

**Guard.** `loom/tests/unit/test_looks.py::test_undo_puts_the_text_back_and_keeps_what_it_replaced`, `loom/tests/unit/test_looks.py::test_keeping_and_undoing_are_the_authors`, `loom/tests/unit/render/test_write_api.py::test_each_endpoint_writes_and_refuses_over_the_wire` (`changes-undo`), `arras/tests/e2e-write/meta.e2e.ts`

**Record.** Plan 0.22.8

### A note's fading is computed, never stored

**Rule.** Whether a note has faded is computed each time the manifest is published, from its age (more than 14 days), whether it is kept, and whether an annotation, a message, the research state or a kept note links to it. Nothing records that a note faded, and nothing deletes one.

**Why.** P3: a state stored is a state that goes stale. A note linked tomorrow must come back without anyone writing that it did.

**Guard.** `loom/tests/unit/test_notes.py::test_a_note_fades_after_two_weeks_unless_kept_or_linked`

**Record.** Plan 0.22.8

