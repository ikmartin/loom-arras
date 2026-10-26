# Invariants

An invariant is a rule loom keeps because breaking it once caused a real failure that a simpler design would bring back; each entry gives the rule, the failure, the test that holds it and the old decision records, and its heading is the name a change cites it by. An invariant changes only by a dated line added to its entry (`**2026-11-02.** What changed.`), explained in the commit message; there is no other decision log.

## The author's authority

### The author's acts refuse any agent, whatever name it declares

**Rule.** The author's acts (`accept`; `library verify`, `discard`, `ignore`, `add`, `import` and `drop`; `session delete --purge`; `ai discard`; `sync publish --push` and `sync incorporate`) refuse a declared agent name, and under an agent marker refuse any name (K5). `refuse_under_agent` is the guard.

**Why.** In the first study an agent verified its own proposal and loom named the author as verifier, since the name came from git, which the agent's shell shares. Later, `accept --author …` and `refs verify --author …` from an agent's shell were accepted.

**Guard.** `loom/tests/unit/test_writer.py::test_every_act_that_is_the_authors_or_destroys_refuses_under_an_agent_marker`, `loom/tests/unit/test_writer.py::test_the_authors_verbs_refuse_a_declared_agent_whatever_shell_it_is_in`

**Record.** DR-185, DR-203, DR-325-ikmartin

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

**Rule.** `AGENT_COMMANDS` in `loom/src/loom/ai/layout.py` is the only list of what an agent may run. The Claude and Codex permission files and the list in `ai/rules.md` are generated from it, and under an agent marker every other command refuses before reading anything, so a new command is the author's until admitted.

**Why.** The rules' Never section and the permission file were two hand-kept deny lists, and they drifted: `loom upgrade` was in neither, and the alias `loom canonise` walked past the deny on `loom canonize`.

**Guard.** `loom/tests/unit/test_ai_layer.py::test_the_allow_list_and_the_permission_file_cannot_disagree`, `loom/tests/unit/test_ai_layer.py::test_codex_is_given_the_same_policy_as_claude`

**Record.** DR-154, DR-173, DR-333-ikmartin

### Loom never runs a command the quilt carries

**Rule.** Configuration that names a command for an agent client is the person's own and never committed. Today that is `ai/ai-config.toml`, gitignored and refused when git tracks it; a future MCP server entry, or anything loom hands a client that can carry commands, follows the same rule.

**Why.** No incident is recorded. `loom serve` runs the agent command when a message waits, so a tracked one would let cloning and serving someone's quilt run whatever they committed.

**Guard.** `loom/tests/unit/test_launch.py::test_no_turn_starts_when_it_should_not`, `loom/tests/unit/test_doctor.py::test_a_tracked_agent_config_is_a_fault`. Neither covers the tracked `.claude/settings.json`, which a launched turn is given with `--settings` unchecked, though Claude Code settings can carry hooks.

**Record.** DR-273-ikmartin

### Generated agent configuration is tested against the real client

**Rule.** A change to what loom generates for an agent client (permission files, Codex rules, launch commands, MCP settings when they exist) is tried with the client itself, run as loom runs it (`claude -p --settings …`), before it ships. Unit tests check only the shape loom believes right.

**Why.** The permission file's `Write` rules passed every unit test and were never enforced: Claude Code matches only `Edit` rules to paths. Then root-relative allows passed too, but under `--settings` a leading `/` means `.claude/`, so every write a launched agent made was refused.

**Guard.** The opt-in `client` tier, run by hand with `scripts/verify client` and never in CI, since it spends on the account of whoever runs it: `loom/tests/client/test_claude.py::test_a_launched_claude_writes_in_the_agents_drafting_directory_and_not_the_authors` and `::test_a_launched_claude_runs_the_agents_loom_commands_and_not_the_authors`. It covers Claude Code only; Codex has no path rules to try.

**Record.** DR-275-ikmartin, DR-343-ikmartin

### Agent instructions name only commands the agent may run

**Rule.** The orientation, the rules and the mode files tell an agent to run only commands in `AGENT_COMMANDS`; an author's command appears in them only where the text says it refuses the agent.

**Why.** The orientation told agents to run `loom linearize`, which the permission file denied and which, had it run, would have superseded the spine and every file it inlined and reassigned `main`.

**Guard.** `loom/tests/unit/test_ai_layer.py::test_every_command_the_agent_is_told_to_run_is_allowed`

**Record.** DR-155

### An agent deletes nothing from a session's directory

**Rule.** An agent never deletes a file in a session's directory, since an annotation or a note may point at it. Its scripts, backups and staging files go under `build/SESSION/`, and the permission file denies `Bash(rm *)`.

**Why.** An agent tidying a session cluttered with its own intermediates tried to `rm` a file one of its own annotations pointed at. A shell permission cannot be confined to one directory, so the fix was a separate place for intermediates.

**Guard.** `loom/tests/unit/test_ai_layer.py::test_an_agent_is_never_allowed_to_delete`

**Record.** DR-315-ikmartin

### Upgrade never destroys an author's edit

**Rule.** `loom upgrade` and `loom ai init` keep one line of loom's in `CLAUDE.md` and `AGENTS.md` and touch nothing else there. An edited mode file or orientation is kept, with the shipped text written beside it as `.new`; an edited `loom.sty` is kept as `loom.sty.old` before it is replaced.

**Why.** Upgrade wrote `CLAUDE.md` and `AGENTS.md` whole whenever they differed from the shipped copy, so an author who had added instructions lost them, and an edited orientation was overwritten with no warning and no backup.

**Guard.** `loom/tests/unit/test_ai_layer.py::test_root_files_carry_one_line_and_keep_the_authors`, `loom/tests/unit/test_ai_layer.py::test_upgrade_preserves_edited_modes`, `loom/tests/unit/test_ai_layer.py::test_upgrade_keeps_an_edited_loom_sty_as_old_and_says_so`

**Record.** DR-151, DR-170, DR-333-ikmartin

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

**Rule.** Every review event is one line appended to `annotations/log.jsonl`, and an annotation's state is the replay of its events. The history ledger and a session's inbox are appended the same way (P2).

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

**Rule.** `sync init` refuses a remote of the quilt's own repository however it is spelled, `sync publish --push` refuses a workspace that holds a quilt, and loom's Git runs only in its own clone under `.loom/workspace/`.

**Why.** `sync init` defaulted to `--remote origin --branch main`, usually the quilt's own repository, and `sync publish --push` then replaced that branch with the source-only projection, removing `config.toml`, `ai/` and `.loom/` from what a coauthor pulls.

**Guard.** `loom/tests/unit/test_sync.py::test_sync_init_refuses_the_quilt_s_own_upstream_however_it_is_spelled`, `loom/tests/unit/test_sync.py::test_publish_push_refuses_a_workspace_that_holds_a_quilt`, `loom/tests/unit/test_sync.py::test_the_quilt_s_own_repository_is_never_touched`

**Record.** DR-326-ikmartin, DR-333-ikmartin

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

**Rule.** A PDF is filed against a bibliography entry, by `library add` or by gathering `refs/`, only when its text holds the entry's identifier, or the entry's full title with its first author leading the byline. Anything weaker is skipped, and the reason given.

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
