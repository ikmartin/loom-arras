# S4 · loom CLI, AI layer, chat and fixture tests

Scope: 15 files in `loom/tests/unit/` plus `loom/tests/conftest.py` (the only conftest under `loom/tests`). 147 test functions, 173 collected items (two functions in `test_fixtures.py` are parametrized over 13 quilts, one in `test_quilts_match_generator.py` over 3). Timings are from the `--durations=60` run in `audit/loom-pytest.txt` (only tests at 0.40 s or more are listed there) plus a direct measurement: `loom init --demo` in process takes about 15 ms and `python -m loom --version` about 0.13 s.

## Inventory

`conftest.py` holds no tests. Its three fixtures: `fake_bin` (session scope; the fake TeX shim written under 12 tool names with this interpreter's shebang), `isolated_env` (autouse; PATH to shim or real TeX for `@tex`, HOME and XDG_CONFIG_HOME to a temp home, every TEXMF tree to an empty dir, deletes `TEXINPUTS BIBINPUTS BSTINPUTS LOOM_QUILT LOOM_RUN LOOM_ARRAS_BUNDLE FAKE_TEX_FAIL` and every `AGENT_MARKERS` variable, sets `FAKE_TEX_LOG`, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`, and asserts tmp is not under ~/notes) and `home` (alias returning that temp home).

"CliRunner" below means an in-process `CliRunner().invoke(main, ...)` wrapped in an `os.chdir` helper; "demo" means a fresh `loom init --demo` in tmp.

| file::test | tests | assumes | asserts |
|---|---|---|---|
| test_fixtures::test_lint_fixture_expected_codes[beamer-talk, begin-not-alone, cycle, demo, double-inclusion, macro-collision, nested-nest, node-conflict, showcase, spanning-env, superseded, synthetic, taxon-conflict] | `lint --json` against each committed quilt | copytree of the quilt, its EXPECTED-LINT.txt, CliRunner | sorted `severity code` pairs equal the file; exit 1 iff any error |
| test_fixtures::test_all_emitted_codes_are_known | every code in the EXPECTED-LINT files is registered | committed files only, `all_codes()` | each code in the registry |
| test_fixtures::test_init_demo_matches_fixture | `init --demo` reproduces tests/quilts/demo | init --demo; skips .gitignore, ai-config.toml, EXPECTED-LINT.txt | dict path to bytes equal |
| test_fixtures::test_nested_nest_levels | `\nest` levels and parents | scan of edge/nested-nest in place | levels map, two parent links, reached_by |
| test_fixtures::test_begin_not_alone_tolerated | proof attachment when `\begin` shares its line | scan of edge/begin-not-alone | proofs lists, title, one unattached-proof |
| test_fixtures::test_synthetic_structure | scan structure of the synthetic quilt | scan in place | levels, parents, proofs and attach_via, aliases, reached_by, directives, taxon, external digest node, ignored file, taxon style |
| test_fixtures::test_never_modifies_author_files[same 13 quilts] | about 23 commands never touch author files | copytree, sha256 snapshot, CliRunner per command | exit in 0/1/2; author files unchanged; config only `main`; ledger append-only; new files only under nodes/drafting/canon/.loom |
| test_fixtures::test_two_masters_share_one_set_of_nodes | one node input by two masters is not a duplicate | hand-built quilt with shipped loom.sty | no duplicate codes; reached_by both masters |
| test_paper::test_import_writes_one_flat_canon_document | `init --from` writes one flat canon doc and step 0001 | paper dir in tmp, fake TeX | files exist, inputs inlined, no loom package or ids, drafting empty, original untouched, identity pass, ledger row, history copy |
| test_paper::test_import_leaves_the_paper_directory_and_no_scratch_behind | import leaves the paper dir and TMPDIR clean | monkeypatch `tempfile.tempdir`, stale aux files | paper bytes unchanged; scratch dir empty |
| test_paper::test_import_refuses_an_existing_canon_document | second import refused | imported quilt | exit 1 and message; ledger still one line |
| test_paper::test_import_asks_before_writing | import needs `--yes` without a terminal | init, then import | exit 2 "needs confirmation", no canon; with --yes exit 0 and summary line |
| test_paper::test_draft_labels_the_copy_sets_main_and_records_it | draft inserts package and ids into the copy | imported quilt | package on line 2, ids in document order, aliases kept, canon untouched, config main, ledger draft row, dangling-link |
| test_paper::test_draft_refuses_a_second_copy_and_a_path_outside_drafting | three draft refusals | drafted quilt | exit 2 and message for existing, outside drafting, non-canon source |
| test_paper::test_draft_refuses_line_anchoring_and_fix_anchoring | draft refuses line anchoring; `--fix-anchoring` repairs | imported quilt with bad anchoring | exit 1, no file; then exit 0, fixed text, no violations |
| test_paper::test_anchoring_violation_reports_the_authors_line | reported line numbers are the canon file's | bad paper via init --from | exit 1; `line N: \begin{definition}` |
| test_paper::test_fix_anchoring_unit | `fix_anchoring` and `anchoring_violations` | pure functions | exact output; no violations after; violation lines [1,2,3,3] |
| test_paper::test_import_outside_tree_warning_and_in_place | init in the paper dir with a `../` input | paper dir as quilt root | exit 0 or 1; import-outside-tree code; canon exists; original and `../` input untouched |
| test_paper::test_id_prints_patch_and_to_writes_copy | `loom id` patch, `--all-levels --no-sections`, `--to` | drafted quilt plus extra node file | patch lines, paragraph unlabelled, copy written, source untouched, existing `--to` exit 2 |
| test_paper::test_atomize_requires_dest_moves_nodes_and_identity | whole-file atomize | drafted quilt | dest required (exit 2), spine inputs, 3 node files, proof file, ledger superseded, lint codes, main moved, re-atomize exit 1 |
| test_paper::test_live_makes_a_superseded_document_define_again | `loom live` | drafted then atomized | "is live"; duplicate-id appears; superseded-file gone; second live exit 2 |
| test_paper::test_atomize_retire_moves_the_source | `--retire` | drafted quilt | source moved to retired/, ledger fields, no duplicate-id |
| test_paper::test_atomize_proofs_separate_directives_sections_and_all | `--proofs separate` keeps a directive line | imported quilt with a directive, draft | lemma file starts with directive, no proof inside, separate proof file |
| test_paper::test_atomize_sections_and_inline_round_trip | `--sections` then `inline --all` | drafted quilt | spine inputs, section file content, round trip whitespace-equal, second inline exit 2 |
| test_paper::test_inline_nest_shifts_and_identity_on_master | inline shifts a `\nest`ed section | drafted quilt plus nested file | `\subsection`, no `\nest`, identity pass, flat file is a master |
| test_paper::test_linearize_refuses_shared_nodes_keeps_or_forks_them | linearize with a node two documents include | atomized quilt plus talk.tex | refusal exit 1 naming spine; `--keep-shared` marker; `--fork` new id; no duplicate-id |
| test_paper::test_selector_survives_atomize | quote-anchored comment survives atomize | drafted quilt, comment, status --explain | open question before and after, not detached, new file path, no detached lint |
| test_paper::test_id_next_prints_a_free_id_and_inserts_nothing | `id --next` | drafted quilt | fresh pp- id, source unchanged, `--json` shape, bare `id` exit 2 |
| test_paper::test_atomize_one_key_writes_the_node_and_leaves_the_source_to_the_author | `atomize --key` writes node, prints patch | drafted quilt, scan to pick key | node file, source unchanged, patch lines; after hand-applying: no duplicate-id, statuses unchanged |
| test_paper::test_atomize_key_json_writes_nothing_and_carries_the_edit | `atomize --key --json` plan | drafted quilt | keys, refusals, edit span and text, file text, nothing written |
| test_paper::test_atomize_key_refuses_what_it_cannot_move | `--key` refusals | drafted quilt, hand patch, unlabelled lemma appended | exit 1 and message for moved, section, unknown, unlabelled with `id --next` hint |
| test_paper::test_atomize_key_moves_an_attached_proof_with_its_statement | `--key` on a proof moves its statement | drafted quilt plus inserted proof | node file holds both |
| test_paper::test_an_indented_heading_ends_the_section_before_it | private `_line_bounds` span | pure | exact slice |
| test_paper::test_import_inlines_an_arxiv_bbl_when_the_bib_is_absent | `inline_bbl` | tmp .bbl then .bib | bbl inlined before `\end{document}`; a real .bib wins |
| test_launch::test_the_quilt_file_wins_over_the_user_config_key_by_key | `agent.load` merge and validation | demo, user config under tmp xdg | merged name/start; non-agent name problem; missing start problem |
| test_launch::test_placeholders_are_filled_item_by_item | `agent.argv` fill | pure (but requests the demo `q` fixture) | list equal, shell text left literal |
| test_launch::test_nothing_starts_while_launching_is_off | tick with `launch = false` | demo, configure, session, post | `running` empty |
| test_launch::test_a_message_starts_a_turn_and_the_next_one_resumes | a full start turn then a resume turn | fake agent script spawning three `python -m loom`; 0.1 s poll; 1.06 s | running state, echoed body, done/turns/name, run.log line, resume echo, turns 2, same conversation |
| test_launch::test_no_turn_starts_when_it_should_not | own message, other agent attached, tracked config, one turn at a time | fake agent, git init/add/rm | not running in each blocked case; running when untracked; same Popen object |
| test_launch::test_a_failed_turn_is_recorded_and_not_retried_until_the_next_message | failed turn state and retry rule | `python -c` exit 3 | failed/code/error; no retry; new message retries under a new conversation |
| test_launch::test_a_missing_command_is_named | start command not on PATH | demo | error text "not on PATH" |
| test_launch::test_stop_ends_a_turn | `Launcher.stop` | `sleep 60` child in its own group | stop True, process dead, state stopped, reap keeps it, second stop False |
| test_launch::test_the_viewer_is_told_what_the_agent_is_doing | `/_api/events` agent field and agent-stop | duck-typed `Fake` handler calling private methods, sleep child | agent `{launch,name}`, running state, stop answer 200 |
| test_launch::test_stop_is_refused_where_nothing_is_launched | agent-stop without a launcher | Fake handler | 409 |
| test_launch::test_agent_check_tests_the_command_without_running_it | `loom agent check` | demo, git init/add/rm | ok output; missing command, tracked config, empty start each exit 1 with message |
| test_launch::test_init_asks_which_ai_and_says_whether_it_will_be_started | `init --ai claude --launch-agents` and plain init | tmp dirs | preset config, launch true, settings allow/deny, .gitignore line, messages; plain: AI none, empty config |
| test_launch::test_the_showcase_referee_findings_are_the_agents | committed showcase log attributes referee findings | committed annotations/log.jsonl | first five created events are "Referee (Agent)", kind agent |
| test_launch::test_an_older_quilt_is_told_and_upgraded_to_keep_the_command_out_of_git | `agent check` note and `upgrade` adds IGNORED | demo with truncated .gitignore | note present, `unignored` empty after upgrade, note gone |
| test_launch::test_serving_starts_no_turn_for_what_was_already_said_nor_for_an_agent | `settle` and agent messages start nothing | fake agent | no turn for old or agent message; turn for new person message |
| test_launch::test_the_activity_is_what_this_turn_ran_not_the_last_line_of_the_log | `agent.activity` since turn start | hand-written run.log | "" then the newer command |
| test_launch::test_a_command_not_on_path_records_when_it_was_tried | failed launch records `started` | same setup as missing-command test | state failed, started set |
| test_launch::test_the_viewer_is_told_what_keeps_the_agent_from_starting | `agent.report` blocked | git track, bad name | no blocked; tracked blocked; name blocked |
| test_launch::test_a_turn_a_stopped_server_left_running_is_ended_and_said_to_be | `settle` kills an orphaned turn | Popen `sleep 60` new session, hand-written agent.json | orphan exits within 10 s; state stopped with error |
| test_launch::test_the_turn_after_a_stop_is_told_not_to_carry_on | AFTER_STOP only on the turn after a stop | `python -c` writing the prompt to a file | text present first, absent second; done |
| test_launch::test_serve_answers_a_transcript_page_from_the_inbox | `_page` serves transcript pages from the inbox | PAGE+3 posts, Fake handler | page 2 seqs; non-transcript path returns False |
| test_launch::test_the_log_says_where_the_turns_rules_came_from | agent.log first line names the policy | full fake agent with `--settings` | first line prefix |
| test_launch::test_codex_is_given_the_same_policy_as_claude | `codex_rules` renders the table; init --ai codex writes it | tmp | allow and forbidden rules; file equals render; no .claude settings |
| test_commands_m1::test_init_creates_layout | init layout | tmp | paths exist, no comments/, prefix, package line, lint exit 0 |
| test_commands_m1::test_init_refuses_in_quilt_and_nonempty | init refusals | tmp | exit 2 inside a quilt and in a non-empty dir |
| test_commands_m1::test_a_nonempty_directory_says_what_is_actually_wrong | three refusal messages differ | tmp, os.chdir | exit 2 and each message, "the current directory" |
| test_commands_m1::test_init_writes_gitignore_always_and_a_repository_only_when_asked | .gitignore always; `--git` makes a repo | tmp, git | .git presence, messages, ignore lines, no source ignored |
| test_commands_m1::test_init_demo_writes_demo_and_lints_clean | demo lints without errors | demo | two files exist, severities info/warning; last assert is `... or True` |
| test_commands_m1::test_init_minimal_master_declares_candidate_taxa | conjecture and question in the minimal master | tmp | declarations present; styles plain and remark |
| test_commands_m1::test_init_readme_orients_the_author_in_this_quilts_own_names | README uses configured names | user config in temp home | headings, example commands, contract, prefix, no default names |
| test_commands_m1::test_init_asks_for_an_author_name_and_writes_it | author name from flag, prompt, or empty | monkeypatch `quilt_cli.sys` and `click.prompt` | config name; prompts asked in order; `--yes` never asks |
| test_commands_m1::test_init_from_leaves_the_authors_preamble_alone | `init --from` copies verbatim | tmp paper | canon equals source, drafting empty, next hint |
| test_commands_m1::test_init_from_leaves_nothing_behind_when_the_import_fails | failed import leaves no skeleton | FAKE_TEX_FAIL | exit 1, no dir, no "created"; rerun succeeds |
| test_commands_m1::test_init_from_inside_a_paper_directory_keeps_the_paper_when_the_import_fails | rollback keeps author files | FAKE_TEX_FAIL | directory holds the two original files |
| test_commands_m1::test_demo_has_outline_master | demo outline master | demo, status/search json | candidates reached, taxa, conjecture proof incomplete, question owes none |
| test_commands_m1::test_deps_prints_see_also | `see:` relations in deps | copy of synthetic | printed section, `relations` json, not in closure |
| test_commands_m1::test_new_allocates_and_print | `loom new` | demo | `--print` skeleton, dm-0012, dm-0013 without proof, unknown taxon exit 2; dead `if False` branch |
| test_commands_m1::test_alloc_sees_references_and_never_reuses | allocation skips referenced ids | demo plus scratch ref | new id dm-0021 |
| test_commands_m1::test_search_deps_unravel_delete | search, deps, unravel, pop, delete, rm | demo | search entry and alias, deps proof/closure, closure lines, dependents (weak `or`), refusals, missing key exit 2 |
| test_commands_m1::test_lint_exit_codes | lint exit 1 on duplicate id | demo plus bad node | exit 1, code, summary line ending |
| test_commands_m1::test_documentclass_outside_drafts_and_bundle_failed | two lint codes | demo, FAKE_TEX_FAIL_MATCH, `check --bundles all` | codes present; master ok line |
| test_commands_m1::test_remaining_codes_have_a_test | foreign-annotations, main-not-found, unknown-config-key, atomize-target-exists | demo, edited log and config | codes present; atomize exit 1 |
| test_commands_m1::test_non_utf8_source_code_reported | non-utf8-source | demo plus Mac Roman file | code and path |
| test_commands_m1::test_retired_config_key_is_tolerated_and_upgrade_removes_it | retired `[ai]` keys | init, edit config | no unknown-config-key; upgrade removes, keeps launch, idempotent |
| test_commands_m1::test_unravel_reports_the_ledger_and_the_annotations_it_heads | unravel ledger and annotations blocks | demo, comment | json ledger keys, annotation fields; text shows message |
| test_ai_layer::test_ai_init_layout_and_vendor_files | `ai init` layout and root files | demo stripped of its AI layer | files exist, modes set, root files identical, no .claude, second init exit 2 |
| test_ai_layer::test_root_files_carry_one_line_and_keep_the_authors | root line kept once across upgrades | stripped demo, upgrade | one CLAUDE_LINE; author text kept; old wording replaced |
| test_ai_layer::test_ai_init_permissions_generated | `--permissions` settings | stripped demo | deny Edit paths, allow session/build, no Write rules, accept/upgrade denied |
| test_ai_layer::test_ai_init_skills_generated_pointer_only | `--skills` stubs point, never duplicate | stripped demo | stub frontmatter, short, no block names, $ARGUMENTS for target modes, commands |
| test_ai_layer::test_every_command_that_writes_outside_a_run_is_denied_to_the_agent | deny list covers named writers | `settings_deny_paths()` only (tmp_path unused) | 18 commands and 6 paths denied |
| test_ai_layer::test_modes_templates_present_and_contracts_listed | mode template structure | stripped demo | `len(MODES)==9`, headings, checklist line, no $LOOM_SESSION, output section |
| test_ai_layer::test_upgrade_preserves_edited_modes | edited modes and orientation kept, `.new` written | stripped demo, hand monkeypatch of `layout.tracked_docs` | kept messages, text untouched, `.new` files, versions file |
| test_ai_layer::test_review_mode_grades_every_finding_and_writes_no_pdf | review.md content | stripped demo | nine topic strings, flags, block name, rules.md phrases |
| test_ai_layer::test_orient_static_plus_live | `ai orient` | stripped demo | orientation header, live state lines, no open sessions |
| test_ai_layer::test_ai_start_opens_a_session_and_orient_prints_its_chat | `ai start`, say, source logging, orient --session | LOOM_FIXED_TIME | minted ids, index events, run.log, no .tex written, chat in orient |
| test_ai_layer::test_sessions_listed_by_title_and_addressed_by_part_of_one | session addressing | fixed time | runs listing, ambiguous exit 2, rename, findings by part, discard closes |
| test_ai_layer::test_run_log_appended_by_run_flag | `--session` and LOOM_SESSION log commands | fixed time | exit 0/1; logged command list |
| test_ai_layer::test_ai_check_reports_outside_writes | `ai check` outside writes | real clock, os.utime offsets | ok; nodes write flagged exit 1; not reverted; promote refused; digest write flagged |
| test_ai_layer::test_threads_from_sessions_in_manifest_and_sessions_not_scanned | sessions become manifest threads | fixed time, AI_AGENT, two builds | thread fields, transcript page, attachments, log, search entry, participants, lint (vacuous last line) |
| test_ai_layer::test_the_session_flag_works_from_a_subdirectory | `--session` from a subdir | cwd nodes/ | log lines; annotation log at root; nothing under nodes/ai |
| test_ai_layer::test_upgrade_keeps_an_edited_orientation | edited orientation kept | stripped demo | text unchanged, kept message, `.new` exists |
| test_ai_layer::test_ai_check_does_not_flag_the_annotations_the_agent_was_told_to_write | annotation log exempt from `ai check` | utime +60 | ok message; node write flagged |
| test_ai_layer::test_the_allow_list_and_the_permission_file_cannot_disagree | allow list, deny list, settings, rules.md share one table | stripped demo `--permissions` | set identities; settings equal `permissions_json()`; rules name every command |
| test_ai_layer::test_every_command_an_agent_writes_with_takes_as | agent commands with `--author` take `--as` | walks the click tree | none missing `--as` |
| test_ai_layer::test_every_command_the_agent_is_told_to_run_is_allowed | assets name no author verb except to refuse it | reads src assets | author verbs named are the refusal set; refs overview allowed |
| test_transcript::test_the_index_reads_from_where_new_events_start | `Transcript` incremental index | demo, session, hand-corrupted inbox | since() bodies, seqs [1,2,3], shorter file resets |
| test_transcript::test_a_line_still_being_written_waits_for_its_newline | partial line ignored | append without newline | one event |
| test_transcript::test_the_last_seq_is_read_from_the_tail | `last_seq` from tail | 300 posts, junk line | 0, 300, 300 |
| test_transcript::test_two_writers_never_draw_the_same_number | post lock | two subprocesses × 50 posts | seqs are 1..100 |
| test_transcript::test_a_post_needs_words_or_something_attached | empty post refused unless `changed` | demo | ValueError; changed carried |
| test_transcript::test_a_heartbeat_is_not_rewritten_every_wake | attach rewrite throttle | hand-edited attached.json | untouched within BEAT; new reader added; old beat renewed |
| test_transcript::test_say_is_the_agents_half_of_the_transcript | `session say` | AI_AGENT via env | refusals (no --as, person), said line, cursor, stdin, empty refused |
| test_transcript::test_a_packet_carries_the_whole_annotation | pending carries long body | comment 400 chars | body equals stripped or raw text |
| test_transcript::test_the_build_pages_the_transcript_beside_the_manifest | `pages()` and build pages | PAGE+50 posts, two builds, delete | page split, markdown html, page file, manifest seq, pages removed on delete |
| test_transcript::test_the_events_endpoint_reads_by_index_and_holds_the_id_to_its_shape | `_events` | local Fake handler | 200 body, attached; bad id 400 |
| test_transcript::test_no_agent_document_asks_for_a_journal | no asset mentions thread.md | reads src assets | absence |
| test_transcript::test_a_purpose_set_later_is_replayed | `sessions.purpose` replay | demo | purpose field |
| test_packets::test_the_packet_is_what_the_person_marked_and_nothing_else | `pending` rows | demo, comments incl. agent, reply, discard | own created+replied only; empty after a carrying post |
| test_packets::test_a_message_carries_only_its_senders_notes | packet per sender | two people, `session send` | sent carries mine; Wren's waits |
| test_packets::test_a_carried_annotation_is_whole | packet row fields | long comment with quote/payload/placement/severity | body and four fields |
| test_packets::test_the_preview_is_the_text_the_agent_reads | `render_changes` equals sent text | comment, send | preview phrases; rendered transcript ends with preview |
| test_packets::test_send_with_no_words_sends_the_packet_and_refuses_when_there_is_none | `send` with no text | demo | refused when empty; body "" with changed |
| test_packets::test_the_message_endpoint_takes_a_packet_alone | API `message` without text | `api.handle` | ApiError when empty; ok seq 1 |
| test_packets::test_the_packet_endpoint_previews_rows_and_text | `_packet` | local Fake handler | rows, text line; 400 bad id, 404 unknown |
| test_packets::test_the_agent_is_handed_the_packet_whole | `session next --json` carries packet | send, next as agent | changed body/quote/kind |
| test_packets::test_a_message_from_the_viewer_is_the_persons_whatever_shell_serve_runs_in | API message ignores shell agent marker | monkeypatch AI_AGENT | author is not an agent |
| test_links::test_each_kind_resolves | `links.resolve` kinds | demo ids a-/s- and bib entries | node, proof, document+place, annotation, session, work+page, arXiv |
| test_links::test_what_the_viewer_does_not_show_is_refused | nine refusals | demo | LinkError message per href |
| test_links::test_a_deleted_session_is_not_linkable | tombstoned session | `session delete` | LinkError |
| test_links::test_check_names_every_bad_link | `links.check` | demo | two messages in order; none for plain text |
| test_links::test_loom_link_prints_what_the_viewer_follows | `loom link` | demo | five exact links; two refusals non-zero |
| test_links::test_an_agent_posting_a_bad_link_is_refused_and_a_good_one_lands | link check in say and agent comment | AI_AGENT env | refusals name link and `loom link`; person's comment passes |
| test_links::test_the_formatting_document_is_in_force | formatting.md is not a stub | reads asset | three string checks |
| test_quilt::test_quilt_discovery_walks_up | `find_quilt` walks up | tmp | root |
| test_quilt::test_quilt_discovery_fails_outside | no `[quilt]` table | tmp | NoQuiltError |
| test_quilt::test_quilt_discovery_env_override | LOOM_QUILT | monkeypatch env, chdir | root |
| test_quilt::test_quilt_config_unknown_key_warns | unknown keys warn | tmp | two warnings, main, default prefix |
| test_quilt::test_a_table_that_is_not_a_table_warns | non-table section | `from_dict` | warning |
| test_quilt::test_a_retired_table_is_accepted_and_ignored | `[crawl]` retired | `from_dict` | no warnings |
| test_quilt::test_the_quilts_own_config_settles_the_author | quilt `[author]` in resolution | tmp config | quilt name, flag wins, empty refuses with message |
| test_cli::test_cli_version | `--version` | none | exact text |
| test_cli::test_doctor_ok_on_shim | doctor on shim | shim PATH (12 shim processes; 1.19 s) | exit 0, latexmk, "ok" on last line |
| test_cli::test_doctor_json_shape | `doctor --json` | shim | versions, tool names, arras field |
| test_cli::test_doctor_missing_tool_exit_2 | missing latexmk | partial symlinked PATH | exit 2, MISSING |
| test_numbered_search::test_a_number_names_what_every_document_numbers_so_the_default_first | search by number | demo plus hand-written .aux files | ordered hits, taxon narrowing, equation |
| test_numbered_search::test_in_asks_one_document | `--in` | same | hits per doc; two refusals non-zero |
| test_numbered_search::test_a_number_nothing_carries_says_so_and_words_are_still_words | unnumbered fallbacks | same | message, bare number as text, word search |
| test_sync::test_source_only_publication_and_incoming_fetch | whole source-sync round trip | two git repos plus bare remote, monkeypatched compile; 2.73 s | publish paths, privacy, fetch, diff, manifest incoming, refusals, API incorporate, commits, review baselines, local_changed, second pull |
| test_cli_reference::test_cli_reference_matches_checked_in | docs/cli-reference.md is generated | runs gen script in process | equal text (with regen hint); three headings |
| test_author::test_userconfig_author_resolution_order | `resolve_author` order | git init, user config in temp home | refusal message, git, config, flag |
| test_quilts_match_generator::test_the_checked_in_quilt_is_what_the_generator_writes[demo (tex), synthetic, showcase (tex)] | `gen_quilts.py NAME --check` | subprocess; demo/showcase need real poppler; showcase 8.11 s, synthetic 0.50 s | return code 0; prints stdout+stderr |
| test_quilts_match_generator::test_the_synthetic_quilt_carries_the_intended_errors | synthetic EXPECTED-LINT errors | committed file | five error codes |
| test_quilts_match_generator::test_the_showcase_carries_the_faults_it_is_meant_to_show | showcase EXPECTED-LINT faults | committed file | one duplicate-id error; four codes present |

## Critique

### Redundant or overlapping

- test_commands_m1::test_init_demo_writes_demo_and_lints_clean duplicates test_fixtures::test_init_demo_matches_fixture plus test_lint_fixture_expected_codes[demo], which pin the demo's files byte for byte and its lint exactly. Its only extra assert, `"loom:undigested-citekey" not in codes or True` (test_commands_m1.py:119), always passes. Keep the fixtures pair.
- test_transcript::test_a_packet_carries_the_whole_annotation (test_transcript.py:153) is a strict subset of test_packets::test_a_carried_annotation_is_whole (test_packets.py:79): same `"word " * 80` body, same `pending` call, and the packets version also checks quote, payload, placement and severity. Keep the packets test.
- test_ai_layer::test_upgrade_keeps_an_edited_orientation (test_ai_layer.py:481) repeats lines 197–207 of test_upgrade_preserves_edited_modes: same edit, same "kept ai/orientation.md (edited)", same `.new` file. Keep the modes test.
- test_launch::test_a_missing_command_is_named (:207) and test_a_command_not_on_path_records_when_it_was_tried (:390) have identical setup and one `tick`. Merge them into one test asserting `state == "failed"`, the error text and `started`.
- There are three deny-list tests over one table: test_ai_init_permissions_generated (:83), test_every_command_that_writes_outside_a_run_is_denied_to_the_agent (:123) and test_the_allow_list_and_the_permission_file_cannot_disagree (:516). The third proves `denied == every - AGENT_COMMANDS`. The second's hand list proves only that those 18 are not in `AGENT_COMMANDS`, and that is its real value. Keep the third and the second's semantic list, folded together. The first can shrink to the `Edit`-only and session/build allow checks.
- The two `ai check` tests (:367 and :494) both prove that a write to `nodes/dm-0002.tex` after the round opened is flagged. Merge them: one test covering the node write, the annotation-log exemption, a digest write and addressing by title.
- `thread.md` absence is asserted in three places: test_transcript::test_no_agent_document_asks_for_a_journal (every asset, the broadest), test_ai_layer::test_modes_templates_present_and_contracts_listed (:188) and test_ai_start_opens_a_session_and_orient_prints_its_chat (:292). Keep the transcript one.
- test_author::test_userconfig_author_resolution_order and test_quilt::test_the_quilts_own_config_settles_the_author both test `resolve_author` precedence ("flag wins" twice). Put them in one file, test_quilt.py.
- Retired config keys are tested twice at different layers: test_quilt::test_a_retired_table_is_accepted_and_ignored (`[crawl]`) and test_commands_m1::test_retired_config_key_is_tolerated_and_upgrade_removes_it (`[ai] runner/agent`). Parametrize one rule over both keys.
- test_paper::test_draft_refuses_line_anchoring_and_fix_anchoring and test_anchoring_violation_reports_the_authors_line both run a refused draft. The second adds only the line number, so fold it in as one more assert.
- test_launch overlaps with itself on the agent-config faults. A tracked config is refused by the Launcher (test_no_turn_starts_when_it_should_not), by `agent check` (test_agent_check_...) and by `report` (test_the_viewer_is_told_what_keeps_the_agent_from_starting). The "name must include Agent or AI" rule appears in test_the_quilt_file_wins... and in the report test. These cover different surfaces and are cheap, so keep them, but each could run one `git init` rather than three.
- test_commands_m1::test_init_from_leaves_the_authors_preamble_alone overlaps test_paper::test_import_writes_one_flat_canon_document ("drafting empty", "no loom package"). The m1 version adds only "verbatim when nothing to inline" and the next hint.
- Mailbox behaviour is split across files. The parked-agent wake test, the heartbeat-staleness test (`waiting_on`) and the viewer session tests live in test_refs_layer.py:2052, :2206 and :1473, beside test_transcript.py's mailbox tests. They are not duplicates, but they are in the wrong file.
- Where test_commands_m1.py's tests belong. The name records milestone M1 and says nothing about what is under test; dissolve it.
  - init (`test_init_*`, `test_a_nonempty_directory...`, the three `init --from` tests, `test_init_asks_for_an_author_name...`) goes to a new test_init.py, together with test_launch::test_init_asks_which_ai... and test_codex_is_given_the_same_policy_as_claude.
  - deps, search, unravel (`test_deps_prints_see_also`, `test_search_deps_unravel_delete`, `test_unravel_reports_the_ledger...`) go to test_graph.py beside test_numbered_search.
  - `test_new_allocates_and_print` and `test_alloc_sees_references...` go next to test_paper's `id --next` test (id allocation).
  - The lint-code tests go to scan/test_edges_lint.py, one test per code: `test_remaining_codes_have_a_test` is named for a coverage checklist and bundles four unrelated codes.
  - `test_demo_has_outline_master` goes to test_fixtures.py.
  - `test_retired_config_key...` goes to test_quilt.py.
- Other misplaced tests:
  - test_launch::test_the_showcase_referee_findings_are_the_agents checks committed fixture data and belongs in test_quilts_match_generator.py.
  - test_fixtures::test_two_masters_share_one_set_of_nodes builds its own quilt and uses no fixture, so it belongs in scan/test_nodes.py.
  - test_launch::test_codex_is_given_the_same_policy_as_claude belongs with the permission tests in test_ai_layer.py.

### Long or slow

The slice costs roughly 35–45 s of the 129 s suite. About 24.6 s of that is visible in the top-60 durations, and about 120 more tests run at under 0.4 s each.

- test_quilts_match_generator[showcase] takes 8.11 s: it is the most expensive test in the slice and the second most expensive in the suite. It is marked `tex`, but nothing deselects `tex` by default (pyproject `addopts = "-q"`), so it runs on every local run on a machine with TeX. Make the tier opt-in (`-m "not tex"` by default, with CI running it), or have the generator reuse one built quilt across `--check` names. [synthetic] costs 0.50 s and is fine.
- test_fixtures::test_never_modifies_author_files costs about 7.1 s over 13 quilts (0.46–1.08 s each). It runs 10–23 commands per quilt, mostly on edge quilts that exist for one lint code. Keep the full matrix on demo, synthetic and showcase, and run a reduced set (lint, search, stamp, new) on the ten edge quilts. That saves roughly 4 s.
- test_sync::test_source_only_publication_and_incoming_fetch takes 2.73 s. It is one monolith with about 40 git subprocesses and 8 builds. Splitting it with a module-scoped fixture that builds the repo pair once would not make it faster, but it would localise failures (see Failure diagnostics).
- test_cli doctor tests take about 1.2 s for the first run. `doctor` spawns every shim once (12 Python processes), and three tests invoke it. Merging the text and `--json` checks into one test saves one run. Low value.
- test_launch full fake-agent turns take 0.5–1.06 s each. `FAKE` spawns three nested `python -m loom` processes: next, source and say. Only test_a_message_starts_a_turn_and_the_next_one_resumes needs the real round trip. test_serving_starts_no_turn... (0.53 s), test_no_turn_starts_when_it_should_not (0.61 s) and test_the_log_says_where_the_turns_rules_came_from (0.50 s) assert only that a process started, or its first log line, so a `[sys.executable, "-c", "pass"]` start command would do. test_the_log_says... could also call `policy_line(cmd)` directly. That saves about 1.2 s.
- Sleeps and polls: `finish()` polls every 0.1 s for up to 60 s (test_launch.py:69), and `Launcher.stop` polls every 0.05 s for up to 3 s before SIGKILL. There is no fixed `time.sleep` in this slice. The fixed 1.5 s sleep is in test_refs_layer.py:2116, outside this slice.
- Repeated `loom init --demo` is not a cost problem. About 75 tests in the slice do it, but it measures 15 ms in process, and a copytree of the demo also takes 14 ms. Keep per-test quilts for hermeticity; do not introduce a shared session-scoped quilt.
- The high-volume mailbox tests (300 posts in test_the_last_seq_is_read_from_the_tail, PAGE+50 in the pages test, 2×50 cross-process) each sit under 0.4 s.

### Delete or combine

- Delete test_commands_m1::test_init_demo_writes_demo_and_lints_clean. It is safe: init --demo equality with the fixture is test_fixtures.py:57, the fixture's exact lint is test_fixtures.py:40, and its last assertion is a tautology.
- Delete test_transcript::test_a_packet_carries_the_whole_annotation. It is safe: test_packets.py:79 exercises the same code path with a strictly larger assertion.
- Delete test_ai_layer::test_upgrade_keeps_an_edited_orientation. It is safe: test_ai_layer.py:197–207 makes the same three assertions.
- Combine test_launch.py:207 and :390 into one missing-command test.
- Combine test_ai_layer.py:367 and :494 into one `ai check` test.
- Combine the deny-list tests at test_ai_layer.py:123 and :516, and trim :83.
- Fold test_author.py into test_quilt.py.
- Fold test_paper.py:196 into :182.
- In test_paper.py, delete `_quilt_from_paper` (:399), an alias for `drafted` that is used four times. Replace the four copies of `next(k for k, n in result.assembly.nodes.items() if n.kind == "environment" and n.file == "drafting/main.tex")` (:418, :439, :456, :482) with a helper.
- Share the three duck-typed `Fake` handler classes (test_launch.py:237, test_transcript.py:196, test_packets.py:164) and the twelve copies of the `run(*args, cwd)` chdir helper as conftest fixtures. A `loom` fixture that passes `--quilt`, or uses `monkeypatch.chdir`, removes the process-global `os.chdir`.
- Remove dead code and stale lines, each safe because none asserts behaviour:
  - test_commands_m1.py:283–287 is an `if False` branch.
  - test_commands_m1.py:334–336 is `A == B or A >= C`: the first disjunct is redundant, so state the superset.
  - test_ai_layer.py:448–450 asserts `bundle-dm-0003.tex` is absent from lint, but no bundle is copied into a session any more, since test_ai_layer.py:286 asserts reading writes no `.tex`. The assertion and its comment are vacuous.
  - test_launch.py:96 requests the `q` fixture and never uses it.
  - test_ai_layer.py:123 takes `tmp_path` and never uses it.

### Missing

The code first, then the documents.

- `agent.argv` re-expands placeholders (agent.py:181). Values are substituted one after another, so a value containing another placeholder is expanded again: `argv(["{prompt}"], prompt="see {agent_session}", agent_session="u")` returns `['see u']`. I verified this. test_placeholders_are_filled_item_by_item only checks that an unknown `{x}` survives, which is trivially true. Add a test that a filled value stays literal, then fix the function to a single-pass substitution.
- Launcher gaps:
  - `Launcher.stop` escalating to SIGKILL for a child that ignores SIGTERM (agent.py:455–470) is untested.
  - `Launcher.start`/`_loop` swallowing and printing tick exceptions (agent.py:314–330) is untested.
  - `tick` skipping closed sessions (`s.state != "open"`, agent.py:345) is untested.
  - `_launch`'s OSError branch (for example a non-executable file) is untested.
  - `_reap` with an empty agent.log ("exited with code N") is untested.
  - `policy_line` for the Codex branch (agent.py:258–271) is untested.
  - `load` on invalid TOML, and a `resume` that is not a list (agent.py:~150–165), are untested.
  - The `{quilt}` placeholder is untested.
- `loom serve` on SIGTERM ends its turns (serve_cmd.py:40–46, `ServeSession.stop` → `launcher.close`, serve.py:492–500; book 11.9, DR-278). Nothing tests it: test_a_turn_a_stopped_server_left_running... covers only the next server's `settle`.
- agent-stop gaps (serve.py:231–248): the case "launcher present, `launch = false`" is untested; test :280 covers only `launcher is None`. That agent-stop goes through `_csrf` before its own body parsing (serve.py:199–205) has no test over the wire.
- Write-API endpoints listed in `CAPABILITIES` (api.py:22–44) with no test anywhere under loom/tests:
  - `resolve`. The CLI `comment --resolve` is tested; the endpoint, and `undo: true` on it (write-api.md §2), are not.
  - `session-reopen` (api.py:~283).
  - `session-purpose` (api.py:~288).
  - The `purpose` field of `session-new`.
  - The `unknown-endpoint` 404 in `handle` (api.py:91).

  Separately, `session-reopen` and `session-purpose` are absent from specs/write-api.md's table. That is a missing fact in the spec (pass 2).
- `/_api/events` with no `session` returns 400 missing-field (serve.py:274–276), and `since=abc` falls back to 0. Neither is tested.
- `session` CLI commands untested anywhere:
  - `session delete --purge` (cli/session.py:173–190) rewrites the annotation log and the index. It is the one place loom rewrites a record, and nothing covers it: not the erase, not `_without` keeping unparsable lines, not the non-tty refusal without `--yes` (exit 2, book 12.1 `--yes` rule), not clearing the active session.
  - `session watch` (:381–409).
  - `session migrate` (:241–258).
  - `session next` returning "nothing yet" after `--wait N`, and `--since` (:330–379).
  - `session send`'s "listening:" line versus the `waiting_on` note (:291–295).
  - The CLI forms of `session use`, `rename`, `close` and `list`: only their API twins are tested.
- `mailbox.attached` dropping a row whose beat is older than STALE (mailbox.py:339–370) is tested only indirectly through `waiting_on` in test_refs_layer.py:2219. There is no direct test that an entry disappears from `/_api/events.attached`. `detach` on a session with no directory, `render`, and `work_of` (mailbox.py:401) are untested.
- links.py gaps:
  - A canon document link `quilt:canon/x.tex`, and its refusal with a place ("a landmark is linked whole", links.py:88–91).
  - An unknown scheme (links.py:63).
  - `quilt:` with an empty key.
  - The LINK regex (links.py:17) stops at the first `)`, so a DOI with parentheses (`10.1002/(SICI)…`) is cut short. That needs a test either way.
  - The property that every link `loom link` prints resolves back to the same target is untested.
- `ai` command gaps:
  - `ai start` refusing without `ai/` (cli/ai.py:154–155).
  - `ai orient` printing `rules.md` and `formatting.md` as well as the orientation (orient.py:12, STATIC; book 11.3.1). test_orient_static_plus_live checks only the orientation header.
  - `ai orient --session` truncating the chat to the last 20 with the "(the last 20 of N…)" line (orient.py:84–88; book 11.4.5).
  - `ai discard --author` (cli/ai.py:19–86), apart from the discard-closes-session path at test_ai_layer.py:341.
- Book 11.2 says `loom ai init` "appends `.loom/sessions/*/bundle-*.tex` to `.gitignore`". No code does this: there is no such string in src/loom, and `IGNORED` (agent.py:71) and assets/init/gitignore lack it. There is no test either. The book fact is stale (bundles moved to build/bundles/ with DR-148). Fix the book rather than add a test.
- Book 12.10 says `LOOM_QUILT`, `LOOM_SESSION`, `LOOM_FIXED_TIME`, `LOOM_PAPER_FIXTURES`, `LOOM_ARRAS_BUNDLE`, `LOOM_SVG_KEEP` and the FAKE_TEX_* variables are the only variables read, and "No other variable is read (M7)". The code also reads `LOOM_SERVE_LOG` (serve.py:132), `XDG_CONFIG_HOME` and the six `AGENT_MARKERS` (_common.py:104), and tests read `LOOM_NETWORK`. No test enforces the list. A test that scans `src/loom` for `os.environ.get`/`envvar=` names and compares them with 12.10 would have caught this drift.
- Book 12.1 says "`--json`: … nothing else on stdout". No test checks it: every test parses `r.output`, which under click 8.5 is stdout and stderr interleaved (verified). Walk the command tree for the `--json` commands a demo supports, and assert that `json.loads(r.stdout)` succeeds and that stderr carries any diagnostics.
- Book 11.4.4 says a refused comment is not logged to run.log (DR-277). test_did.py covers the arrow form, but no test posts a refused comment and checks the log is unchanged.
- Book 11.8 requires the author's verbs to refuse a declared agent over the API as well as the CLI. `review-finish` and `refs-note` with an agent-named `author` have no refusal test here; check test_refs_layer before adding one.

### Failure diagnostics

- In test_fixtures.py:76, `assert got == expected` compares two dicts of path to bytes. On failure pytest prints the dicts' byte blobs, truncated and unreadable, never says which file differs, and never says how to regenerate. Better:

  ```python
  diff = sorted(k for k in expected.keys() | got.keys() if expected.get(k) != got.get(k))
  assert not diff, f"loom init --demo differs from tests/quilts/demo in {diff}; regenerate both with `python scripts/gen_quilts.py demo` (it also writes src/loom/assets/demo)"
  ```

- test_fixtures.py:44–45 runs `json.loads(r.output)` with no guard. If lint crashes, or prints a note to stderr (which `r.output` includes), the failure is a bare JSONDecodeError with neither the quilt nor the output. Use `r.stdout`, and assert `r.exit_code in (0, 1), r.output` first. The equality at :46 should name the quilt. It should also say that for demo, synthetic and showcase EXPECTED-LINT.txt is written by `gen_quilts.py` (`_write_expected_lint`, gen_quilts.py:1425), while for edge quilts it is hand-kept. As it stands, a reader cannot tell whether to regenerate or edit.
- test_fixtures.py:169 accepts `exit_code in (0, 1, 2)`. CliRunner turns an uncaught exception into exit code 1, so a crashing command passes the invariance test silently. The same crash-blindness applies to `in (0, 1)` at test_paper.py:235, test_ai_layer.py:352 and test_transcript.py:176/:184, and to bare `== 1` or `!= 0` without an output check at test_paper.py:287, test_commands_m1.py:342, test_ai_layer.py:392 and test_links.py:105. Assert `r.exception is None or isinstance(r.exception, SystemExit)`, or match the refusal text.
- About 51 `assert run(...).exit_code == 0` lines in the slice carry no message. Examples: test_numbered_search.py:26, test_launch.py:47, test_packets.py:27, test_links.py:25, test_transcript.py:27 (each fixture's `init --demo`), and test_paper.py:292 and :359. When one fails the report is `assert 1 == 0`, with no output and no traceback. A shared helper:

  ```python
  def ok(r):
      assert r.exit_code == 0, r.output + ("".join(traceback.format_exception(r.exception)) if r.exception else "")
      return r
  ```

- The session-id helpers `sitting()` (test_launch.py:66, test_packets.py:40) and `quilt()` (test_transcript.py:29) never check the exit code. If `session new` fails, the "session id" becomes `Error:` and the test fails later with a confusing message. The same applies to `sid = run("ai", "start", ...).output.strip()` at test_ai_layer.py:348, :370 and :401.
- test_quilts_match_generator.py:35 prints the generator's stdout and stderr. That names each differing file ("differs: X", "only generated: X") and prints `run: python scripts/gen_quilts.py NAME`, which is good. It gives no content diff, and the built quilt lives in a TemporaryDirectory that is gone by the time anyone looks. Have `_differences` (gen_quilts.py:1455) append the first 20 lines of a unified diff for text files, or accept `--keep DIR`.
- In test_launch.py:69, `finish()` returns silently at its 60 s deadline. The next assertion then fails on something unrelated, such as the last event's body (:128, :140), and never shows `agent.log`, which holds the fake agent's traceback. `finish` should assert the process exited and attach `(session_dir(q, sid) / "agent.log").read_text()` to the message.
- test_sync.py:97–117 uses `try: …; except SyncError as exc: assert …; else: raise AssertionError(...)` three times. Use `pytest.raises(SyncError, match="awaiting incorporation")`. More importantly, one 135-line test means a failure at line 146 hides whether publish, fetch, incorporation or review-baseline tracking broke. Split it into four or five tests over a shared repo fixture.
- Weak equalities:
  - test_transcript.py:163 and test_packets.py:101 assert `body == long.strip() or body == long`. That pins neither behaviour; decide which one is right.
  - test_doctor_ok_on_shim (test_cli.py:26) checks `"ok" in last line`, which matches any line containing "ok" (such as "token").
- test_cli_reference.py:14 is good: equality with a "run scripts/gen_cli_reference.py" hint.

### Other

- Hermeticity: `LOOM_SESSION` leaks from the developer's shell (verified). conftest.py:78 deletes `LOOM_RUN`, a variable nothing reads any more, but not `LOOM_SESSION`, which about 20 options take as their envvar default. `Launcher._launch` sets `LOOM_SESSION` for every turn (agent.py:388), so an agent that `loom serve` launched and that runs `uv run pytest` fails every command taking `--session`. Running `LOOM_SESSION=s-2026-01-01-0099 uv run pytest tests/unit/test_commands_m1.py::test_search_deps_unravel_delete` fails with "no session matches 's-2026-01-01-0099'". `LOOM_FIXED_TIME` also leaks, and would break test_ai_layer.py:367 and :494, which rely on the real clock. So would `LOOM_SERVE_LOG` and `LOOM_SVG_KEEP`. Fix: in `isolated_env`, delete every environment variable that starts with `LOOM_`, rather than listing names, so a new variable cannot leak. The same leak reaches the `gen_quilts.py --check` subprocess, because the generator's `env()` overrides only its own keys.
- Hermeticity, redundant setup: test_launch.py:40–42's autouse `_user_config` redirects XDG_CONFIG_HOME a second time. conftest already isolates it, so the fixture can go, with test :81 writing under `home / ".config"`.
- `r.output` versus `r.stdout`: click 8.5's `Result.output` interleaves stderr (verified). Every `json.loads(r.output)` in the slice depends on no command writing a note to stderr, and `.output.split()[0]` id-scraping (test_launch.py:66, test_packets.py:40, test_transcript.py:29) breaks if a command emits a stderr note first. Use `r.stdout` for data.
- Process fragility in test_launch.py:
  - Launchers are never closed on failure. Only test :256 uses `try/finally`, so an assertion failure before `launcher.close()` leaves a `sleep 60` child or a fake agent running in its own process group. A fixture that yields a `Launcher` and closes it in teardown fixes all of them.
  - test :420 calls `os.killpg` on a pid from a hand-written agent.json; if the orphan exits early and the pid is reused, it signals an unrelated group. That is theoretical, but a fixture should reap `orphan` in `finally`.
  - The git-dependent tests assume `git` in /usr/bin. `tracked()` returns False when git is absent, so on such a machine the "git tracks" assertions fail rather than skip.
- Concurrency test that can pass without its lock: test_transcript::test_two_writers_never_draw_the_same_number passes whenever the two processes happen not to interleave. On a fast machine the first may finish before the second has imported loom (about 0.13 s). Start both behind a barrier, for example a file each waits for, or raise the count so the test actually exercises the lock.
- The ai_layer "bare quilt" is not bare. `demo()` (test_ai_layer.py:28) strips `ai/`, CLAUDE.md, AGENTS.md, `.claude`, annotations and sessions, but not `.codex/rules/loom.rules`, which the demo now ships. Every new AI-layer file the demo gains has to be added to this list by hand. Start from `loom init --prefix dm` plus the few nodes the tests reference, or add an `init --demo --no-ai` form.
- Tests of implementation rather than behaviour:
  - test_paper::test_an_indented_heading_ends_the_section_before_it calls private `_line_bounds`. Test through `atomize --sections` on a paper with an indented heading instead.
  - test_ai_layer.py:174 asserts `len(MODES) == 9`, a constant.
  - test_commands_m1.py:173 replaces the module's `sys` with a SimpleNamespace, which breaks as soon as quilt.py uses anything else from `sys` during init.
  - test_launch, test_transcript and test_packets call `LoomHandler._events`, `_packet`, `_page` and `_agent_stop` unbound on duck-typed fakes. That couples them to the private method names and to the attributes each reads. render/test_serve.py already has a live-server `session` fixture; the events, packet and agent-stop endpoints should go through it over HTTP, which would also exercise CSRF.
  - test_launch.py:60 imports private `_set_launch`.
  - test_transcript.py:49 asserts the index's internal `t.seqs`.
  - test_ai_layer.py:211–220 monkeypatches `layout.tracked_docs` by assignment. Use `monkeypatch.setattr`.
- Content-string tests on shipped assets make prose edits fail tests. test_review_mode_grades_every_finding..., test_modes_templates... and test_the_formatting_document_is_in_force (`"stub" not in text.lower()`) do this. That is intended as a contract, but these could read `src/loom/assets/ai/` directly instead of running `init --demo` and `ai init` first.
- Demo coupling: test_links, test_packets and test_numbered_search hard-code demo ids (a-2026-09-16-0001/0004, s-2026-09-16-0001/0002, Man12, Calloway14, dm-0012 as the next id). That is acceptable while `gen_quilts.py` pins the demo, but a regenerated demo with one more annotation shifts `dm-0012` and `a-…-0004`. Read the expected ids from the fixture where the test does not care which one.
- Formatting (CLAUDE.md pass 10): test_ai_layer.py:124–130's docstring is hard-wrapped, the only one in the slice. Comments that are changelog rather than current state are also against the house rule: test_commands_m1.py:42 ("replaced by annotations/log.jsonl four plans ago and still created") and test_ai_layer.py:88–89 and :183.
- Stale bytecode: tests/unit/__pycache__ holds `test_zz_dbg`, `test_zz_debug` and `test_zz_dump` .pyc files with no source. pytest does not collect them, but they suggest leftover debugging files; clear the cache.
