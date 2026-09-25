# S2 · loom records, history and review tests

Slice: `loom/tests/unit/records/` (6 files), `loom/tests/unit/history/` (2 files), `loom/tests/unit/test_review_queue.py`, `test_reports.py`, `test_did.py`. 105 test functions, 107 collected items (one function parametrized three ways). Paths below are relative to `loom/tests/unit/` unless stated.

Shorthand used in the table:

- **demo(clean)**: `loom init --demo` into tmp_path, then `.loom/` and `annotations/` deleted (`test_review_commands.demo`, `test_lastseen.demo`).
- **demo(shipped)**: `loom init --demo` with its shipped ledger, sessions and annotation log kept.
- **synthetic**: `shutil.copytree` of `tests/quilts/synthetic` into tmp_path.
- **shim quilt**: `history/test_commands.quilt()`: `loom init --from` a 30-line inline paper with prefix `pp`, then `loom draft canon/main.tex --yes` (step 0001 is the import).
- **agent**: `env={"AI_AGENT": "1"}`, so the writer is recorded as `agent`.
- All CLI tests go through a per-file `run()` that `os.chdir`s and calls `CliRunner().invoke(main, ...)`; the autouse `isolated_env` in `tests/conftest.py` supplies the fake TeX shim, an empty HOME and no git identity.

## Inventory

| file::test | tests | assumes | asserts |
|---|---|---|---|
| records/test_hostile_log.py::test_a_well_formed_log_reports_nothing | `replay` of one valid `created` event | hand-written `annotations/log.jsonl` in tmp_path; no quilt | problems == []; first annotation kind `objection` |
| records/test_hostile_log.py::test_an_unknown_kind_is_reported_and_kept | unknown `annotation_kind` reported, not corrected | hand log, kind `catastrophe` | a problem mentions `catastrophe`; kind kept as written |
| records/test_hostile_log.py::test_a_missing_kind_is_reported_rather_than_assumed | hyphenated `annotation-kind` column reported | hand log without `annotation_kind` | some problem contains "is not one of" |
| records/test_hostile_log.py::test_an_id_that_is_a_path_is_reported | path-shaped id rejected by the id pattern | hand log, id `../../escape` | problem "is not an annotation id" |
| records/test_hostile_log.py::test_a_reply_to_nothing_is_reported | orphan reply reported; valid reply silent | hand log, rewritten twice in one test | "replies to unknown annotation"; second log gives [] |
| records/test_lastseen.py::test_an_edit_under_an_annotation_freezes_the_text_it_was_written_against | comment freezes its version; cache advances after an edit | demo(clean); `dm-0002` contains ORIGINAL; two fake-TeX builds | one file in `history/texts` holding ORIGINAL before and after edit; last-seen `dm-0002` moves off ORIGINAL |
| records/test_lastseen.py::test_an_edit_nobody_annotated_freezes_nothing | no annotation, no frozen text | demo(clean); build, edit, build | `history/texts` empty |
| records/test_lastseen.py::test_two_edits_between_scans_keep_what_loom_saw_and_not_what_it_did_not | unseen intermediate text never frozen | demo(clean); comment, build, two edits, build | exactly one frozen text; holds ORIGINAL, not the intermediate |
| records/test_lastseen.py::test_the_cache_survives_a_nondefault_history_directory | `[quilt] history` moves cache and texts together | demo `config.toml` has a `[refs]` line to insert before | `records/last-seen.json` exists; `records/history/texts` has one file with ORIGINAL |
| records/test_lastseen.py::test_a_version_written_against_between_scans_is_kept | comment freezes a never-scanned version | demo(clean); build, edit, comment, edit, build | some frozen text has "as we now check"; sole manifest annotation (detached, recorded, anchored) == (F, T, T) |
| records/test_ledger_selectors.py::test_ledger_append_only_and_latest_row_wins | `AcceptRow` TOML, `append_rows`, `latest_rows` | tmp_path only | exact file header; `[[accept]]` and closure tables; authors [A, B]; latest text `sha256:9`; two rows |
| records/test_ledger_selectors.py::test_snapshots_content_addressed_never_overwritten | `write_snapshot` normalises, dedupes, never overwrites | tmp_path only | equal hash for whitespace variants; written flags; normalised content; tampered file kept; unknown hash → None |
| records/test_ledger_selectors.py::test_selector_resolution_unique_by_context_and_detached | `make_selector`, `resolve_selector`, `find_quote` | pure strings | prefix/suffix; ambiguous make raises; context picks occurrence; missing → None; whitespace-normalised spans |
| records/test_ledger_selectors.py::test_a_quote_selected_on_the_page_finds_its_source | page-form quote (`$c$`, unwrapped `\emph`) maps to source | pure strings | returned slices are source text; selector exact is source form; unrelated quote → [] |
| records/test_ledger_selectors.py::test_a_selection_is_found_as_the_page_prints_it | typographic quotes, dashes, `~` as printed | pure strings | whole-source span; selector exact == src; ASCII quote still found |
| records/test_recorded.py::test_a_note_on_any_kind_of_key_is_recorded | `recorded` true on section, document, result, proof, equation | `q` fixture = demo(shipped) | all five resolved annotations recorded |
| records/test_recorded.py::test_a_version_written_against_survives_edits_before_any_build | comment-time freeze with no build | demo(shipped); edit, comment with quote, edit | annotation recorded |
| records/test_recorded.py::test_an_edit_restates_the_finding_against_the_text_as_it_is_now | `--edit` re-points `against` at current text | demo(shipped); edit `dm-0002` | body updated; target_hash == current `key_hash` |
| records/test_recorded.py::test_a_reply_records_the_text_it_was_written_against | reply records its own version, parent keeps old | demo(shipped) | parent hash == before; reply hash == now != before |
| records/test_recorded.py::test_a_note_whose_version_is_gone_is_not_pinned_to_the_new_text | unrecorded version → not recorded, not marked | demo(shipped); hand-appended event; private `render.build._marks_by_node` | kept recorded, lost not; lost span still resolves; only kept marked |
| records/test_recorded.py::test_an_edit_from_the_viewer_changes_the_body | API `edit` maps `message` to body | demo(shipped); first token of `session list` is a session id | resolved body updated |
| records/test_run_resolution.py::test_a_title_reaches_the_session_it_names | `--session TITLE` resolves to the id; no mkdir | demo ships ai layer; last line of `ai start` is the id | no `./early`; run.log in session; comment filed under sid; `ai findings` count 1 |
| records/test_run_resolution.py::test_an_unmatched_session_is_an_error_not_a_directory | unknown session refused | demo; one started session | exit 2; "no session matches"; root listing unchanged |
| records/test_run_resolution.py::test_a_session_is_never_a_path | `--session build` is not a path | demo; `build/` created | exit 2; "no session matches"; no `build/run.log` |
| records/test_run_resolution.py::test_an_ambiguous_title_names_its_matches | duplicate titles refused with matches named | demo; two "morning pass" sessions | exit 2; "matches 2 sessions" and title in output |
| records/test_review_commands.py::test_demo_ships_two_accepted_one_stale_and_a_finished_session | shipped demo review state | demo(shipped) | summary accepted 1, stale 1; cause `dm-0001`; open counts on `dm-0003` and proof; one notes file |
| records/test_review_commands.py::test_reaccepting_unchanged_intermediate_resolves_indirect_staleness | indirect `via` cause, first-observed date, re-accept clears | demo(clean); `LOOM_FIXED_TIME` set twice; edits to `dm-0002`, `dm-0001` | via cause; date stays 09-21; fresh after re-accept; settled False; direct cause after edit |
| records/test_review_commands.py::test_review_build_publishes_rendered_comparison_and_citation | `loom review` publishes the comparison pair | demo(shipped), `dm-0002/proof` stale | citation in master fragment; both HTMLs have "fixed locus"; `review-changed` class not on `<p>`; spans non-empty |
| records/test_review_commands.py::test_observation_date_resets_after_a_cause_disappears | cause date resets once cause clears | demo(clean); `LOOM_FIXED_TIME` 09-21 then 09-23 | date 09-21; fresh after revert; 09-23 after re-edit |
| records/test_review_commands.py::test_comparison_uses_preamble_saved_with_dependent_acceptance | comparison renders with the accepted preamble | demo(shipped); `\Fix` edited in master | saved macro set has old body; default set has new |
| records/test_review_commands.py::test_ledger_refuses_without_author_exact_message | accept with no author | demo(clean); empty HOME, no git name | exit 2; `NO_AUTHOR_MESSAGE` in output |
| records/test_review_commands.py::test_accept_writes_closure_hashes_and_proofs_flag | `accept --proofs` rows, closure, snapshots | demo(clean) | both "accepted" lines; 2 rows with author; proof closure; preamble/master; ≥3 snapshots; states fresh |
| records/test_review_commands.py::test_accept_all_live_selects_statements_and_proofs_and_tracks_changes | `--all-live` refusal, confirmation, selection | demo(clean); edits remove `\incomplete`, add basis directives, drop an outline input | exit 1 naming `dm-0005/proof`; exit 2 without `--yes`; per-key states; later dependency-changed |
| records/test_review_commands.py::test_accept_all_live_refuses_other_target_modes [extra = `("dm-0001",)`, `("--proofs",)`, `("--stale",)`] | `--all-live` mutual exclusion | demo(clean) | exit 2; "cannot be combined"; no `state.toml` |
| records/test_review_commands.py::test_state_draft_accepted_stale_incomplete_and_causes | every stale cause kind in sequence | demo(clean); successive edits, finally deleting `dm-0001` | incomplete/draft; dependency-changed; own-text; dependency-added; preamble-changed; dependency-removed; "stale" in text |
| records/test_review_commands.py::test_stale_diff_from_snapshot_and_accept_stale | `--explain` diff; `accept --stale` | demo(clean) | explain names cause and new words; (tautological `--stale` check); stale 0, accepted 2; 3 rows |
| records/test_review_commands.py::test_accept_refuses_incomplete_and_uncompiled | refusals: incomplete, no compile, unknown key; `--force` | demo(clean); `FAKE_TEX_FAIL=1` | exit 1 "incomplete"; exit 1 "does not compile"; `--force` 0; `dm-9999` exit 2 |
| records/test_review_commands.py::test_derived_proved_settled | `proved`/`settled` derivation | demo(clean) | exact derived dicts for three keys; a `%` comment keeps proved |
| records/test_review_commands.py::test_comment_quote_rules_and_records | comment output, event fields, quote errors, confirmation | demo(clean) | output line; event fields, anchor ≤32; not-found, ambiguous exit 1; outside-text exit 1; bogus kind exit 2; open counts |
| records/test_review_commands.py::test_comment_run_author_log_reply_resolve_batch | session comment, run.log, reply, resolve, failing batch | demo(clean); session; agent | run.log line; no annotations.json; author agent; events created/replied/resolved; "batch line 2"; only first batch line filed |
| records/test_review_commands.py::test_a_run_resolves_its_own_annotation | agent resolves its own finding | demo(clean); session; agent | "resolved <id>"; events [created, resolved]; open {} |
| records/test_review_commands.py::test_a_recheck_edits_a_finding_rather_than_replying | `--edit` keeps one finding; fields survive | demo(clean); session; agent | "objection major"; "edited <id>"; events [created, edited]; open 1; severity major; unknown id exit 1 |
| records/test_review_commands.py::test_a_finding_raised_in_error_is_discarded_not_resolved | `--discard` keeps its reason | demo(clean); session; agent | "discarded <id>"; open {}; events created/discarded; body == reason; unknown id exit 1 |
| records/test_review_commands.py::test_severity_and_placement_are_checked | bad severity; placement without payload | demo(clean) | exit 2; "give --payload too" |
| records/test_review_commands.py::test_discard_flag_hides_everywhere_and_undo | `ai discard` by session, author, target, date; undo | demo(clean); two sessions | open counts 2→1→0→1→2; last event discarded; "no matching records"; 2 runs listed |
| records/test_review_commands.py::test_reference_notes_accept_and_reject | `refs note --accept/--reject`; bib untouched | demo(clean); session; agent | one note with for/identifier/from/claim; reject writes none; open {}; `refs.bib` unchanged; list; non-citation exit 1 |
| records/test_review_commands.py::test_retired_key_dependency_removed_merge_by_alias | retired key listing, lint code, alias merge | demo(clean); remark `dm-0004` inline in main.tex | `status --retired` starts `dm-0004`; lint code; empty after alias; `deps dm-0004` → `dm-0005` |
| records/test_review_commands.py::test_positional_key_recovery_by_hash | previous-key-match after deleting a proof | synthetic; `sy-0006` has ≥2 unlabelled proofs | key gone; `previous_key_match`; status message; lint code |
| records/test_review_commands.py::test_status_filters_and_never_fails | every status filter exits 0 | synthetic | exit 0 per flag; incomplete/loose/undigested rows; exact JSON top-level key set; incomplete 1 |
| records/test_review_commands.py::test_timeline_7_11 | book 7.11 worked timeline end to end | demo(clean); session; agent; three builds | draft; open counts; 3 marks; 2 detached; agent latest; accepted/proved; stale list; diff file; stale 0; some detached |
| records/test_review_commands.py::test_status_json_answers_the_same_question_as_the_text_form | `--master` filter applies to JSON and summary | synthetic; last text line is the count | row counts equal; `reached_by`; subset of all; summary keys == rows |
| records/test_review_commands.py::test_status_carries_the_title_beside_the_taxon | title and taxon in status | demo(clean) | JSON title "Orbits", taxon Lemma; text line has "Orbits" |
| records/test_review_commands.py::test_status_filters_by_what_the_annotations_say | `--severity/--kind/--status/--detached` | demo(clean) | exact key lists |
| records/test_review_commands.py::test_findings_filter_and_withdrawn_ones_say_why | `ai findings` filters; discard reason shown | demo(clean); parses path printed by `ai start` | two live; discarded hidden; `--all` shows reason in JSON and text; severity filter |
| records/test_review_commands.py::test_batch_refuses_an_unknown_key | batch unknown key | demo(clean) | nonzero; "unknown key(s) messsage", "accepted:"; no events |
| records/test_review_commands.py::test_batch_carries_every_verb_one_to_a_line | batch edit, create, resolve; two verbs refused | demo(clean) | event order; "one verb per line" |
| records/test_review_commands.py::test_a_clean_read_takes_no_severity | severity on confirmation refused | demo(clean) | nonzero; message; no events |
| records/test_review_commands.py::test_a_reference_note_records_the_work_and_the_argument_for_it | citation without payload refused; work/claim split | demo(clean) | "proposes no work"; note `work`/`claim` prefixes |
| records/test_review_commands.py::test_every_verb_takes_its_message_as_the_one_positional | `--reply/--resolve` positional is the body | demo(clean) | replied and resolved bodies |
| records/test_review_commands.py::test_a_reply_refuses_what_it_cannot_carry | reply/resolve refuse payload, severity, quote | demo(clean); 6 combinations in a loop | nonzero with "<flag> would be lost"; event count unchanged |
| records/test_review_commands.py::test_a_verb_that_answers_nothing_is_refused | empty reply/edit refused; field-only edit, bare resolve allowed | demo(clean) | three messages; no writes; later exits 0; batch "nothing to change" |
| records/test_review_commands.py::test_a_finding_on_a_section_is_visible_where_the_author_looks | section finding in status, explain, filters; accept refused | synthetic; `sy-0003` already carries a major | kind section; empty state; open 1; text line; explain; severity list; accept nonzero; `sy-0200` absent |
| records/test_review_commands.py::test_status_is_the_authors_to_do_list_not_the_literatures | digest rows limited to reached keys | synthetic; appended unused digest theorem | kept ⊂ external; `digests` counts; summaries equal; tally text |
| records/test_review_commands.py::test_accept_refuses_a_digest_node_and_names_the_command_that_does_it | accept refuses an external node | synthetic | nonzero; "not yours to accept", names `refs verify`; `sy-0002` accepted |
| records/test_review_commands.py::test_verifying_a_digest_node_says_what_it_claims | `refs verify` wording; transcription-changed cause | synthetic; `refs build --only extract` first | verified text; source block; status label; stale transcription cause, not own-text |
| records/test_review_commands.py::test_an_annotations_display_math_is_a_block_not_a_div_inside_a_paragraph | `render_markdown` splits paragraph around `$$` | pure function | 2 `<p>`; closed before div; inline before display; ends `<p>follows.</p>` |
| records/test_review_commands.py::test_a_status_change_is_reversed_by_appending_its_undo | resolve/discard `--undo` | demo(clean) | output prefixes; open counts; event kinds and undo flags; bare `--undo` nonzero |
| records/test_review_commands.py::test_a_comment_on_an_equation_marks_its_display | region comment marks equation display | synthetic; session; agent; build (unchecked) | display chunk has `annotation-block` and id, no `<mark` |
| history/test_commands.py::test_canonize_writes_a_flat_landmark_and_a_step | canonize output, ledger line, step directory | shim quilt | refuses existing canon; macros inlined; ids kept; output; ledger fields, froze, of, reaches, parent; files; verify 0 |
| history/test_commands.py::test_canonize_requires_a_message_and_refuses_a_conflicted_key | `-m` required; conflicted id refused | shim quilt; duplicate `pp-0002` node file | exit 2; exit 1 naming "defined by two files"; no canon file |
| history/test_commands.py::test_stamp_records_only_what_moved | stamp refuses nothing; records one key | shim + canonize | exit 1 "nothing to stamp"; dir name; froze [`pp-0002`]; preamble None; dir listing; revised text |
| history/test_commands.py::test_history_lists_steps_and_a_key_s_versions | `loom history` and `history KEY` (text, JSON) | shim + canonize + stamp | step lines; `@2`, `@3`; head line; JSON head_is 3, two versions |
| history/test_commands.py::test_revert_prints_a_patch_and_records_it | revert prints, never applies; unknown step | shim + canonize + edit | patch lines; file untouched; ledger revert step 2; "no step 9" |
| history/test_commands.py::test_fork_gives_a_document_its_own_copy | fork writes node file, prints patch | shim + atomize + hand-written `talk.tex` | new file and label; patch lines; talk.tex unchanged; ledger new/from/in |
| history/test_commands.py::test_fork_from_a_recorded_version | `fork --from @2 --as`; taken id refused | shim + canonize + edit | old text in patch; ledger from.step 2; exit 1 "taken" |
| history/test_commands.py::test_an_id_the_history_recorded_is_never_allocated_again | removed id retired from allocator | shim + canonize + remove theorem + stamp | `removed` list; `id --next` == `pp-0004` |
| history/test_commands.py::test_a_retired_id_written_again_is_reuse_or_recovery | node-recovered vs id-reused | same setup as previous test | recovered, not reused; reused with message; lint exit 1 |
| history/test_commands.py::test_canon_edited_is_reported_with_its_fixes | canon-edited warning, subject, fixes | shim; comment appended to canon | lint codes; `--nodes` exit 0; JSON subject record, draft fix |
| history/test_commands.py::test_history_verify_reports_an_edited_record | history-edited then history-missing | shim + canonize | exit 1 with each code |
| history/test_commands.py::test_canonize_aliases_print_one_line | `canonicalize` alias notice | shim quilt | exit 0; "canonicalize → canonize" |
| history/test_ledger.py::test_empty_history_is_not_a_refusal | `load_history` on an absent directory | tmp_path | not exists; empty; next_step 1; empty versions/ids |
| history/test_ledger.py::test_steps_versions_and_addresses | step and version queries over a ledger | hand ledger, 4 lines | steps; next_step; resolve_step by number/name/dir; latest; state_at; versions_of; of; recorded/removed ids |
| history/test_ledger.py::test_a_malformed_line_is_reported_and_skipped | bad JSON and out-of-order step | hand ledger | only step 2 kept; "not JSON" and "does not follow" |
| history/test_ledger.py::test_append_is_a_line_and_the_cache_notices | `append_entry` line numbers; reload | tmp_path | lines 1, 2; reloaded entries; actor None allowed |
| history/test_ledger.py::test_supersession_and_live | `superseded_paths` minus `live` | hand ledger | == {`drafting/c.tex`} |
| history/test_ledger.py::test_parent_is_declared_inferred_or_unknown | `infer_parent` | hand ledger, two steps | declared; inferred step 2; unknown |
| history/test_ledger.py::test_names_addresses_and_slugs | `version_filename`, `parse_address`, `slug`, `step_dirname` | pure | exact values |
| test_review_queue.py::test_pending_ok_survives_build_and_waits_for_upstream | pending OK blocks finish while upstream unreviewed | synthetic (build ignored); API `handle` | decision ok; row ok after build; finish raises naming `sy-0001` |
| test_review_queue.py::test_requires_attention_returns_to_queue_when_block_changes | fingerprint invalidates a decision | synthetic; `decide()`; main.tex edit | requires-attention, then needs-review with invalidated |
| test_review_queue.py::test_transitive_attention_clears_after_upstream_ok_is_finished | provisional removal, invalidation, finish writes no redundant row | synthetic; `write_acceptance`; monkeypatched private `_master_compiles`, `_author`; 5 builds | fresh False + via; proof out of queue; ok set; needs-review after edit; fresh after finish; row unchanged |
| test_review_queue.py::test_fresh_pending_ok_remains_visible_until_finish | explicit OK on fresh key stays listed | synthetic; `write_acceptance` | row status ok |
| test_reports.py::test_math_survives_markdown | inline math protected from emphasis | pure `render_markdown` | two math spans; `<em>` outside math |
| test_reports.py::test_display_math_is_a_block_not_a_paragraph | `$$` becomes a div | pure | div present; no `<p><div` |
| test_reports.py::test_math_is_escaped_for_html | HTML escaping inside math | pure | `&lt;`, `&amp;` |
| test_reports.py::test_report_parses_into_its_blocks | `parse_report` blocks and findings | SAMPLE constant | names, titles, finding ids, per-block findings |
| test_reports.py::test_every_finding_is_an_anchor | finding `<li>` carries id attributes | SAMPLE | exact `<li` prefix; 2 `data-annotation-id` |
| test_reports.py::test_the_readers_view_is_free_of_the_agents_syntax | brackets and trailing ids stripped | SAMPLE | no `[summary]`; exact h2 with offsets; title; no "(a-…)"; attr present |
| test_reports.py::test_every_offset_lies_inside_the_file | `data-src` ranges within the file | SAMPLE | spans non-empty and in range |
| test_reports.py::test_blocks_carry_offsets_into_the_notes_file | section and root offsets | SAMPLE | decision section span; root span |
| test_reports.py::test_an_unparseable_report_is_one_block_not_an_error | headingless prose | pure | one block; empty name; prose in html |
| test_reports.py::test_a_second_pass_sorts_after_its_first | pass number from notes filename | private `render.threads._pass_of` | "1" and "2" |
| test_did.py::test_each_comment_logs_the_annotation_it_touched | run.log "→ id" per comment verb | demo(shipped); `session new`; batch via stdin | first 6 lines exact; 2 prefixes; refused comment not logged (8 lines) |
| test_did.py::test_the_manifest_carries_the_annotation_apart_from_the_command | `build_threads` splits command and annotation | demo(shipped); foreign run.log line appended | log[0] command/annotation; log[1] exact dict |
| test_did.py::test_refs_commands_log_their_arguments_as_typed | refs command logged as typed | demo(shipped); exit 0 or 1 both accepted | "loom refs coverage Calloway14" in log |
| test_did.py::test_code_is_quoted_as_written | code spans skip math processing | pure `render_markdown` | `<code>` keeps `$`; math outside converted |

## Critique

### Redundant or overlapping

- **`test_lastseen::test_two_edits_between_scans_…` vs `test_lastseen::test_an_edit_under_an_annotation_freezes_…`.** Since DR-284 `loom comment` freezes its version at write time (`cli/review.py:279-289`). So in the two-edits test ORIGINAL is already in `texts/` before any edit, and `freeze_moved` finds nothing new to write. Nothing ever asks for the intermediate text, so no code path could freeze it, and the "not what it did not see" assertion cannot fail. Both tests now assert the same thing: one frozen file that holds ORIGINAL. Keep the first; delete the second, or rewrite it as the missing `freeze_moved` test (see Missing).
- **`test_lastseen::test_a_version_written_against_between_scans_is_kept` vs `test_recorded::test_a_version_written_against_survives_edits_before_any_build`.** Both follow the same scenario (edit, comment, edit, no scan between) and assert `recorded`. The lastseen version also builds and reads the manifest's `anchored`. Keep the recorded one, which is cheaper and asserts closer to the unit. Fold the manifest `(detached, recorded, anchored)` check into `test_timeline_7_11`, which already builds.
- **`test_lastseen::test_the_cache_survives_a_nondefault_history_directory` vs `test_an_edit_under_an_annotation_freezes_…`.** These run the same flow, and the only difference is the config line. Parametrize one test over `history_dir in (None, "records/history")`.
- **`test_review_commands::test_stale_diff_from_snapshot_and_accept_stale` vs `test_timeline_7_11` (Day 9).** Both run the same edit ("Its \emph{fixed locus} is" → "…, a subset of $X$, is"), both check `--explain` for "+" and "a subset of", and both run `accept --stale --yes --force` and then assert stale == 0. The timeline also checks the manifest diff file. Keep the timeline; reduce `test_stale_diff…` to the one thing it adds (row count 3 after `--stale`), or delete it.
- **`test_state_draft_accepted_stale_incomplete_and_causes` vs `test_stale_diff…` vs `test_accept_all_live…` (tail) vs `test_timeline_7_11` vs `test_observation_date…` vs `test_reaccepting_…`.** All six make the same `dm-0001` edit to produce `dependency-changed dm-0001` on `dm-0002/proof`. The cause taxonomy test is the normative one (book 7.6.2). The trailing edit in `test_accept_all_live…` (lines 226-232) re-proves it and can go. Also factor the edit into a named helper (`touch_definition(d)`).
- **`test_derived_proved_settled` vs `test_timeline_7_11` (`proved is True`) vs `test_reaccepting_…` (`settled is False`).** The derived-state checks are spread across three tests. Keep `test_derived_proved_settled` as the owner; the timeline's `proved` line is fine as narrative.
- **`test_comment_run_author_log_reply_resolve_batch` vs `test_every_verb_takes_its_message_as_the_one_positional` vs `test_did::test_each_comment_logs_the_annotation_it_touched`.**
  - The first test checks reply/resolve output and event order, the second checks their bodies, and the third checks the run.log line for every verb.
  - run.log is asserted in both `test_review_commands.py:380` and `test_did.py:53`.
  - Merge the body checks into the first test, and leave run.log to `test_did`.
- **`test_a_run_resolves_its_own_annotation` vs `test_a_status_change_is_reversed_by_appending_its_undo` vs `test_comment_run_author_log_reply_resolve_batch`.** All three resolve and then assert `open == {}`. The "run resolves its own" case differs only in that the writer is the agent session. It is a legitimate regression guard, but it could be one parametrized case of the resolve test (writer ∈ {person, same session}).
- **`test_a_finding_raised_in_error_is_discarded_not_resolved` vs `test_findings_filter_and_withdrawn_ones_say_why` vs `test_a_status_change_is_reversed_by_appending_its_undo`.** All three discard one annotation and check that it is hidden. Two of them check that the reason is kept (`events_for[1]["body"]` and `discard_reason`). Keep `test_findings_filter…` for the reason, since it covers what a reader sees, and the undo test for undo. The first can shrink to the unknown-id refusal.
- **`test_batch_refuses_an_unknown_key`, `test_batch_carries_every_verb_one_to_a_line`, the batch tail of `test_a_verb_that_answers_nothing_is_refused`, and the batch part of `test_comment_run_author_log_reply_resolve_batch`.** Batch behaviour is split across four tests. Collect it into one batch test with a table of (stdin, expected exit, expected message, expected events).
- **`test_run_resolution::test_an_unmatched_session_is_an_error_not_a_directory` vs `test_a_session_is_never_a_path`.** These are the same refusal ("no session matches", exit 2). Parametrize over `("no-such-session-at-all", "build")` and keep both side-effect checks.
- **`test_reports::test_display_math_is_a_block_not_a_paragraph` vs `test_review_commands::test_an_annotations_display_math_is_a_block_not_a_div_inside_a_paragraph` vs `test_did::test_code_is_quoted_as_written` vs `test_reports::test_math_survives_markdown`.** All four are pure `records.store.render_markdown` tests scattered over three files, two of which are CLI/report files. The two display-math tests overlap; the one in `test_review_commands` is strictly stronger. Move all four into one `records/test_render_markdown.py` and drop the weaker display test.
- **`test_review_commands::test_review_build_publishes_rendered_comparison_and_citation` vs `test_comparison_uses_preamble_saved_with_dependent_acceptance`.** Each does `init --demo` plus `loom review` on the shipped state and reads the same manifest cause. They could share one module-scoped built demo (see Long or slow).
- **`history/test_commands::test_an_id_the_history_recorded_is_never_allocated_again` vs `test_a_retired_id_written_again_is_reuse_or_recovery`.** The setup is byte-for-byte identical: canonize, cut the theorem by index, stamp. Merge them into one test, or add a `retired` fixture.

### Long or slow

Timings measured on five representative tests (fake TeX): `init --demo` + one command ≈ 0.13 s; the shim quilt (`init --from` + `draft`) + one command ≈ 0.45 s; `test_timeline_7_11` 0.80 s; `test_transitive_attention_clears…` 1.06 s. From these, the slice costs roughly 20–25 s in total. About 70 % of that is repeated quilt creation and repeated `status --json` scans, not the behaviour under test.

- **`test_review_commands.py` (45 items).** Every test runs `loom init --demo` from scratch (≈0.1 s each, ~4.5 s total). Many then call `status_json` 3–8 times, and each call is a full scan plus a JSON dump: `test_state_draft…` has 6, `test_discard_flag…` has 6, `test_timeline_7_11` has 8 plus 3 builds. Cost ≈ 8–10 s for the file.
  - Fix: a session-scoped template built once (`init --demo`, then remove `.loom` and `annotations`), copied per test with `shutil.copytree`. That costs about 5 ms instead of about 100 ms.
  - The same template works for `test_lastseen`, `test_recorded`, `test_run_resolution` and `test_did`, which each run their own `init --demo` (another ~20 inits).
- **`history/test_commands.py` (12 items, ≈5 s).** Every test pays `init --from` + `draft` (≈0.35 s), and 8 of the 12 then run `canonize --to canon/v1.tex` as well. Build one session-scoped "canonized" template and copy it. The saving is ≈3.5 s.
- **`test_review_queue.py` (≈3 s).** Each test copies synthetic and runs `build(load_quilt(root))` 1–5 times; each build renders every fragment. `test_transitive_attention…` builds 5 times only to read `manifest["unresolved"]` and `manifest["keys"][k]["acceptance"]`. `review_queue.rows_for(result, manifest)` is the unit that decides queue membership.
  - Where the test is about queue logic, call `scan` + `rows_for` on a manifest from `render.manifest` (or on `Records.key_states`) and skip rendering.
  - Keep one build-level test to prove the manifest wiring.
- **`test_timeline_7_11` (0.8 s).** It is valuable as the executable form of book 7.11. It is also the most expensive test in the file, and it is fragile: three unchecked builds, and a conditional `json.loads(...) if run(...) == 0 else {}` that turns a build failure into a `KeyError`. Keep it, but make it the only end-to-end review narrative and delete the overlaps listed above.
- **`test_accept_all_live_refuses_other_target_modes`.** This is 3 × a full demo init to test a click-level argument conflict that is refused before any scan. It can run against one shared template with no copy, since it writes nothing.
- **`test_lastseen` and `test_recorded`.** These use builds and CLI where the unit (`freeze_moved`, `Records.resolved`) could be driven directly. `test_recorded` already uses `open_scan` + `Records`, which is the right level.

### Delete or combine

Each of these is safe because every assertion it makes is made elsewhere in the slice, or it cannot fail.

- **Delete `test_lastseen::test_two_edits_between_scans_keep_what_loom_saw_and_not_what_it_did_not`.** Its assertions are implied by `test_an_edit_under_an_annotation_freezes_…`, and the "never invents" check cannot fail (see Redundant). Replace it with a direct `freeze_moved` test.
- **Combine `test_lastseen::test_the_cache_survives_a_nondefault_history_directory` with `test_an_edit_under_an_annotation_freezes_…`** as a parametrization.
- **Reduce `test_review_commands::test_stale_diff_from_snapshot_and_accept_stale`** to its unique assertion (3 rows after `--stale`), or delete it. Its line 300 (`… or True`) asserts nothing.
- **Combine `test_every_verb_takes_its_message_as_the_one_positional` into `test_comment_run_author_log_reply_resolve_batch`**: assert bodies where replies and resolutions are already filed.
- **Combine the four batch tests** into one table-driven test (see Redundant).
- **Combine the two `test_run_resolution` refusal tests** into one parametrized test.
- **Combine the two history retired-id tests** (identical setup).
- **Move the four `render_markdown` tests** into one file and drop `test_reports::test_display_math_is_a_block_not_a_paragraph`. The stronger version lives in `test_review_commands.py:1003`.
- **Move or rename `test_reports::test_a_second_pass_sorts_after_its_first`.** It never sorts anything; it tests a private filename parser. Either test the public ordering (`build_threads` output order for two notes files) or rename it to `test_pass_number_from_filename`.
- **Drop the trailing stale-cause block of `test_accept_all_live…` (lines 226-232).** `test_state_draft…` owns causes.

### Missing

Concrete behaviour with no test anywhere under `loom/tests/` (checked by grep across `tests/unit`, `tests/tex`, `tests/papers`, not only the slice).

**records/**

- `records/log.py:98-99`: a non-JSON line in `replay` is only covered indirectly, through `test_commands_m1.py:373` as a lint code. `:101-103` (JSON that is not a review event), `:106-108` (`created` without an id), `:143-145` (`edited/resolved/discarded` naming an unknown annotation), and `:140` (a later event without an id) have no test. Book 7.4.1 names "not a review event" as one of the foreign-line cases. Add them to `test_hostile_log.py`, which is already the right cheap unit file.
- `records/log.py:130-138`: a whole-source `discarded` event and its `undo` at unit level, including the `source` field for a person's day-keyed record. Today this is only reached through `ai discard` in `test_discard_flag…`.
- `records/log.py:147-153`: `edited` carrying `severity/payload/placement` and re-pointing `against` at unit level. This is covered only via CLI in `test_recorded`.
- `records/lastseen.py:67-85` `freeze_moved`: no test reaches its snapshot write, because comment-time freezing gets there first. A unit test is needed: an annotation event whose `against` is the hash of the text in `last-seen.json` but not in `texts/` (as the API or an older log would produce), then a scan with changed text. Assert that the old text is written and the key is returned.
- `records/lastseen.py:40-41`: a corrupt or wrong-`version` cache reads as `{}`.
- `records/lastseen.py:88-95` `ensure_gitignore_line`: idempotence, and appending to a file without a trailing newline.
- `records/annotations.py:136` `next_id`: the quilt-wide counter (book 7.4.2, DR-60). `:132` `author_slug`: the slug rule of book 7.4.1. Neither is tested.
- `records/snapshots.py:30, :38-40`: the legacy `.loom/snapshots` fallback in `write_snapshot`/`read_snapshot` is untested. Per the no-backwards-compatibility memory it is also a candidate for deletion rather than testing.

**cli/review.py**

- `cli/review.py:234`: the accept summary line "snapshots: N written, M already present" (book 7.3 item 1) is never asserted. The per-row format `accepted <key> (<Taxon>) by <author> <date>` is asserted only by the prefix "accepted dm-0002".
- `cli/review.py:272-273`: writing to a deleted session is refused ("nothing new can be written to it"). No test.
- Book 7.3 item 3: `accept --stale` without `--yes` and without a terminal must exit 2. Only the `--all-live` form of that rule is tested (`test_review_commands.py:212`).
- Book 7.4.3 item 3: a `--kind` prefix (`--kind conf`) and an ambiguous prefix are not tested through `loom comment`; only `full_kind` is, in `test_refs_layer.py`. The default kinds are also untested: `objection` with a message, `confirmation` without one, `question` on a reply.
- Book 7.4.3 item 8: the "two verbs is an error **naming both**" rule is only asserted as "one verb per line", not as both names.
- Book 7.8: the positive `ai discard --before DATE` case (records whose earliest annotation predates the date) is untested; only a date matching nothing is. `--author` discarding a person's comment session is also untested, although the test uses `--author` against the author's session.
- Book 7.9: "annotations targeting [retired keys] are detached at the target level" is untested.

**history/**

- `history/checks.py:21-26`: `loom:history-corrupt` from `History.problems` is never checked through lint or `history verify`.
- `history/checks.py:118-122`: a missing step directory, and a ledger step whose `dir` is absent (the interrupted-step case of book 17.6).
- `history/checks.py:130-143`: an edited or missing `preamble.tex`, and an edited step document copy.
- `history/checks.py:144-186`: `loom:dangling-ancestry` for `fork`, `revert` and `draft`. There is no test of any kind.
- `history/versions.py:57-68` `materialize`: `% !LOOM child:` expansion on revert or fork, and the refusal when a child is gone (book 17.5: "refused when one does not"). No test reverts a key whose version has child markers.
- `history/versions.py:44-54` `read_version`: the "record … is missing" `LookupError` (version file deleted, then `revert`), and "KEY has no version at step N".
- `history/migrate.py:25-48` `migrate_history` (book 17.16, called by `loom upgrade`) is entirely untested. That covers the snapshot move, the `drafts` → `drafting` rename, the no-rename-when-`drafting`-exists rule, idempotence, and dedupe when the target exists.
- `history/steps.py:66-70, :155`: the `restored` list. Book 17.14 says "the next step records it as restored"; no test stamps after a recovery and checks `restored` or the "N restored" output (`cli/history_cmds.py:344`).
- `cli/history_cmds.py:316-326`: `stamp --in DOC` narrowing (book 17.9's worked example), and its refusal for a document that is not live.
- `cli/history_cmds.py:330-333`: `stamp` on a quilt with no steps ("nothing to stamp: no key has an id").
- Book 17.8, `canonize`:
  - `--parent N` is untested.
  - The `live: false` warning-and-proceed for a superseded, ignored or outside-drafting document is untested; only `live is True` is asserted.
  - The refusal of an environment spanning files is untested.
  - "Canonizing changes no acceptance and no review" is untested.
  - The `canonise` alias notice is untested; only `canonicalize` is, and `test_ai_layer` only checks that `canonise` is denied to agents.
- Book 17.5: "the preamble is recorded … when it differs from the last one". `stamp` asserts `preamble is None`, but nothing asserts that a changed preamble is recorded by a stamp.
- Book 17.10:
  - `fork` of a node defined inline "prints the patch and writes nothing": untested.
  - References to the old id outside the document are "left alone and reported": untested.
  - "Annotations are not copied": untested.
- `cli/history_cmds.py:691` `history verify --json`: untested.
- `History.step_for_path`, `History.last_preamble` (`history/ledger.py:109, :190`) and `versions.matching_version` have no direct unit test. The last is only reached through `history KEY`'s "head: the text of @3".

**review_queue.py**

- `review_queue.py:171-174`: `decide` rejects a bad status or a non-reviewable key (a section).
- `review_queue.py:184-185`: `pending` raises "changed since OK; review it again". `review-finish` after an OK'd block was edited is only exercised when the edit is reverted first.
- `review_queue.py:189` `clear_accepted`: asserted only indirectly (`after["unresolved"]`).
- Book 7.6.2: "Requires attention … can be reopened and marked OK" is untested.
- Book 7.6.2: "a transitive dependent … reappears if … another cause arises" is untested.

### Failure diagnostics

- **Exit-code asserts that pass when loom crashes.** `CliRunner.invoke` catches exceptions and reports `exit_code == 1`, and no `run()` helper passes `catch_exceptions=False` or shows `r.exception`. So these asserts pass on a traceback:
  - `test_review_commands.py:355` (`r4.exit_code == 1`, no message)
  - `:463` and `:484` (unknown id → `== 1`)
  - `:938` (`accept sy-0100` → `!= 0`)
  - `:1034` (`--undo` → `!= 0`)
  - `test_did.py:65` (`!= 0`)
  - `test_did.py:87` (`exit_code in (0, 1)` accepts both success and a crash)

  Better: `r = run(...); assert r.exit_code == 1 and r.exception is None or isinstance(r.exception, SystemExit), r.output; assert "no annotation a-nope-0001" in r.output`. Always pin the refusal message as well as the code.
- **Success asserts without output.** Dozens of `assert run(...).exit_code == 0` lines print nothing on failure, for example:
  - `test_review_commands.py:90, 100, 128, 245, 292, 322, 326, 587, 604, 718, 731`
  - `test_lastseen.py:50, 51, 59, 68, 70, 77, 78, 82, 96, 97, 101, 111, 114, 116`
  - `history/test_commands.py:52, 85, 103, 120, 123, 136, 152, 173, 186, 192, 200, 206`
  - `test_run_resolution.py:41, 54`
  - `test_did.py:43-51`

  A failing `accept` then reports only `assert 1 == 0`. `test_recorded.comment()` and `test_run_resolution.started()` already show the right form. Put one shared helper in a `tests/unit/conftest.py`: `def ok(*args, cwd, **kw): r = run(...); assert r.exit_code == 0, f"loom {' '.join(args)} exited {r.exit_code}\n{r.output}\n{r.exception!r}"; return r`.
- **Tautologies and near-tautologies.**
  - `test_review_commands.py:300`: `assert "dm-0002/proof" in r2.output and … or True` is always true. The intent (`--stale` lists the proof and not the statement) is never checked. Better: `rows = [ln.split()[0] for ln in r2.output.splitlines()[:-1]]; assert rows == ["dm-0002/proof"], r2.output`.
  - `test_review_commands.py:297` `"-" in r.output` and `:726` `"+" in explain.output` are satisfied by any key name (`dm-0002`). Assert a diff line: `assert "+Its \\emph{fixed locus}, a subset of $X$, is" in r.output`.
  - `history/test_commands.py:127`: `"draft" in r.output` is satisfied by the path `drafting/main.tex`. Assert the draft line itself, e.g. a regex `r"^\s+draft\b"`.
  - `test_review_commands.py:287`: `"stale" in r.output` also matches the summary line's "0 stale".
- **Bare `next(...)` and tuple unpacking over large structures.** When a row is missing, these fail with a bare `StopIteration` or "not enough values to unpack" and give no clue which key or which list:
  - `test_review_queue.py:25, 37, 44, 98` (`next(row for row in … if row["key"] == …)`)
  - `test_review_commands.py:756, 929, 992` (`next(ln for ln in … if ln.startswith(...))`)
  - `test_lastseen.py:120` (`(a,) = m["annotations"].values()`)
  - `test_review_commands.py:797` (`(gone,) = …`)

  Better: `rows = {r["key"]: r for r in manifest["unresolved"]}; assert "sy-0002" in rows, sorted(rows); assert rows["sy-0002"]["status"] == "ok", rows["sy-0002"]`.
- **Build results ignored, and a conditional that hides failures.**
  - `test_timeline_7_11` (`:693, :727`), `test_a_comment_on_an_equation_marks_its_display` (`:1044`) and `test_lastseen` (every `build`) either ignore the build result or check only `exit_code`. A failed build then surfaces as a `FileNotFoundError` on `build/fragments/…`.
  - `test_review_commands.py:734`: `m = json.loads(...) if run("build").exit_code == 0 else {}` turns a build failure into `KeyError: 'annotations'`, the least informative outcome possible. Assert the build first.
- **Equality over whole structures.** `assert set(j) == {"summary", "keys", …}` (`:638`) prints two sets, which is fine. `assert s["keys"][key]["reviews"]["open"] == {...}` is fine. `assert shown["summary"] == all_rows["summary"]` (`:963`) prints two dicts, which is acceptable. Where status JSON is indexed three levels deep (`s["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]["id"]`), a missing `acceptance` raises `TypeError: 'NoneType' is not subscriptable` with no key named. A small `cause_ids(s, key)` helper returning `[]` with an assert message would say which key had no acceptance.
- **Magic numbers.**
  - `len(snaps) >= 3` (`:175`) never says which three snapshots are expected (key text, proof text, preamble, closure). Assert on the hashes from the ledger rows instead: `{r.text for r in rows.values()} | {r.preamble} ⊆ {p.stem}`.
  - `count("[[accept]]") == 3` (`:305`) is also unexplained.
  - `step["step"] == 2` and `pp-0004` in history tests are explained by comments and are fine.
- **Opaque shared setup.** The helper `demo(tmp_path, clean=False)` means "keep the shipped ledger, stale acceptance and sessions", but three tests rely on specific contents of `assets/demo` (`dm-0002/proof` stale by `dm-0001`, a notes file named `referee-dm-0003.notes.md`). When the demo changes, the failures read as review bugs. Name the dependency, e.g. `demo_with_shipped_review(tmp_path)`, and assert the precondition with a message once in a fixture.
- **Test name disagrees with its assertion.** `test_demo_ships_two_accepted_one_stale_…` asserts `summary["accepted"] == 1`. That count is of *fresh* acceptances (`cli/review.py:964`), so it is not a bug, but a reader cannot tell. Add a comment, or assert `accepted + stale == 2`.

### Other

- **Hermeticity: `LOOM_SESSION` leaks from the developer's shell.** `tests/conftest.py:73` unsets `LOOM_RUN` but not `LOOM_SESSION`. The review commands read `LOOM_SESSION` as the default `--session` (`cli/review.py`, `cli/ai.py:117, :222`, `status --session envvar`). In a shell inside a loom session, every `comment` without `--session` in this slice resolves that foreign id and fails with "no session matches". Also unset `LOOM_FIXED_TIME`: the tests that monkeypatch it set it themselves, but every other test inherits whatever the shell has. Add both to the `delenv` list.
- **Hermeticity: synthetic copy includes stray build output.** `test_review_commands.synthetic()` copies `tests/quilts/synthetic` with no `ignore=`. `test_review_queue` ignores `build` and `.git`. A developer who once ran `loom build` in the fixture gets a stale `build/` copied into these tests. Use the same ignore everywhere, or one shared `synthetic` fixture.
- **Testing implementation rather than behaviour.**
  - `test_review_queue.py:82-83` monkeypatches private `loom.cli.review._master_compiles` and `_author`. The fake TeX shim already makes the master compile, and `write_acceptance`'s author could come from `[author] name` in the copied config. A rename of either private breaks the test with an `AttributeError` far from the behaviour.
  - `test_recorded.py:103` imports private `render.build._marks_by_node`.
  - `test_reports.py:92` imports private `render.threads._pass_of`.
  - Prefer the manifest (`build(...).manifest["annotations"][id]["anchored"]`, `build_threads` order).
- **Duplicated harness.** An identical `run()` (chdir + `CliRunner`) is defined in 6 files in the slice, plus `demo()`/`quilt()`/`q` variants in 5. Put one set in `tests/unit/conftest.py`: `run`, `ok`, `demo_template` (session-scoped), `demo`, `synthetic`. This removes about 80 lines and gives every CLI assert the same failure message.
- **Parsing CLI output to get ids.** `test_findings_filter…:776` takes `ai start` output, `strip()`s it and `rsplit("/")`s it. `test_run_resolution.started` takes its last line, and `test_recorded.py:134` takes the first token of `session list`. Each is a hidden contract on human-facing output. Use `--json` where the command has it, or `loom.sessions.sessions(q)` directly.
- **Prose violations of CLAUDE.md in the slice.**
  - The docstring of `test_a_run_resolves_its_own_annotation` (`test_review_commands.py:401-406`) is hard-wrapped. It also reads as a changelog ("the file-per-record store silently lost", "the two `--resolve` tests either side of this one"). The "either side" claim is no longer true: the next test is the `--edit` test.
  - `test_lastseen`'s `test_two_edits…` docstring describes the pre-DR-284 behaviour. So does the module docstring of `src/loom/records/lastseen.py:7` ("Two edits between two scans leave an annotation **unanchored**"), which is now false for any note written by `loom comment`.
  - The source under test has hard-wrapped comments at `records/log.py:52-53, 111-113, 119-120, 132-133, 155-157` and `cli/review.py:261-263`.
- **Fragile anchors on demo text.** More than twenty tests locate edits by exact demo sentences ("Every orbit of a widget has one or two points", "Its \emph{fixed locus} is", "the union of the one-point orbits"). `test_lastseen.edit` and `test_recorded.rewrite` assert that the old text is present, which is good. `test_review_commands` mostly uses bare `.replace` with no check (e.g. `:88, :92, :251, :259, :720`), so a demo rewording makes the replace a silent no-op, and the test then fails on a downstream state with no pointer. Route every edit through one `edit(path, old, new)` that asserts `old in text`.
- **Order within tests.** No cross-test shared state was found; every test uses `tmp_path`. `run()` restores cwd in `finally`, but `os.chdir` is process-global, so these files cannot run under a threaded runner. That is harmless with xdist's process model.
