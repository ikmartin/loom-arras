# S1 · loom refs tests

Slice: `loom/tests/unit/test_refs_layer.py` (109 tests), `loom/tests/unit/refs/test_resolve.py` (14), `loom/tests/unit/refs/test_scan.py` (10), `loom/tests/unit/test_digest.py` (20), `loom/tests/unit/test_refs_identity.py` (8). 161 tests, none parametrized. `refs/__init__.py` is empty; `refs/resolve_responses.json` is the recorded zbMATH/Crossref fixture.

Legend for the "assumes" column. **demo**: `loom init --demo` into tmp_path via CliRunner with `os.chdir` (about 30 ms). **mapped**: demo plus a `Vir12` entry, hand-written `pages/0001.txt` and `0012.txt` and a fake `sections.json` (sha `deadbeef`×8), no PDF. **showcase**: `shutil.copytree` of `tests/quilts/showcase` (972 KB, carries real PDFs). **digest-demo** (test_digest.py): demo plus a `Ref20` entry and the `REF` source filed with `refs add`. **unit**: no filesystem. Every test also gets the autouse `isolated_env` (HOME, PATH to the fake TeX shim, agent markers unset). `[tex]` marks tests that get real latexmk on PATH (and poppler if present) or are skipped.

## Inventory

| file::test | tests | assumes | asserts |
|---|---|---|---|
| test_refs_layer::test_a_jstor_eprint_is_not_an_arxiv_id | `arxiv_id` honours eprinttype/archiveprefix | unit | plain, `arXiv:`-prefixed and archiveprefix eprints give the id; jstor, doi eprint and no eprint give None |
| test_refs_layer::test_a_candidate_is_enough_to_fetch_with_and_never_the_identity | `identifier_for` declared vs candidate | demo; `resolve.save` writes a candidate | bare entry (None,""); after save ("0805.2065","candidate"); a declared eprint wins |
| test_refs_layer::test_the_arrival_check_reads_the_papers_own_title | `source_title`, `arrival_score` | tmp src dir with a `\title[short]{…}` | title read verbatim; right entry scores >= ARRIVAL; wrong entry < ARRIVAL |
| test_refs_layer::test_a_source_with_no_title_is_kept_not_rejected | untitled source is not a mismatch | tmp src dir, no `\title` | `source_title` == ""; `arrival_score` is None |
| test_refs_layer::test_build_says_what_is_off_and_what_is_left | `refs build` report with nothing opted in | demo | exit 0; "(lookup off)", "(fetching off)", "needs you", "needs an agent" in output |
| test_refs_layer::test_build_json_orders_by_how_often_a_work_is_cited | `refs build --json` ordering | demo (cites only Calloway14) | `cited_by` list sorted descending; some work has `digest` truthy |
| test_refs_layer::test_match_lists_only_what_a_person_must_look_at | `refs match` output | demo | exit 0; "loom refs add" or "nothing needs you" in output |
| test_refs_layer::test_an_agent_may_run_the_mechanical_pass_and_not_the_authors_verbs | AGENT_COMMANDS allowlist | unit; imports `loom.ai.layout` | five refs verbs included; "digest fetch" and "accept" excluded |
| test_refs_layer::test_a_contents_page_is_skipped_whole | `find_sections` skips a TOC page | unit (tmp_path unused) | sections == [("1",2),("2",4)] |
| test_refs_layer::test_a_run_in_heading_is_cut_at_its_first_sentence | run-in heading title | unit | [("1","Introduction")] |
| test_refs_layer::test_mathematics_is_not_a_heading | math lines not headings | unit | `find_sections` == [] |
| test_refs_layer::test_section_numbers_do_not_go_backwards | monotone section numbers | unit | numbers == ["1","2","3"] |
| test_refs_layer::test_a_numbered_bibliography_is_not_a_section_list | numbered references not sections | unit | ["1","2","3","References"] |
| test_refs_layer::test_map_and_coverage_need_no_pdf_to_be_useful | `refs map`, `refs coverage` with no PDF | demo | map exit 0 and "0 mapped"; coverage exit 0 and "have page text" |
| test_refs_layer::test_the_page_text_is_committed_and_the_pdf_is_not | init's .gitignore rules | demo | ignores storage PDF and src, `refs/`; no rule mentions pages; no `refs/pdf/` |
| test_refs_layer::test_the_demo_gitignore_agrees_with_the_one_init_writes | demo .gitignore matches init's | package assets | if demo .gitignore exists, every `refs/`/`digests/storage` line of init's is in it |
| test_refs_layer::test_normalisation_joins_hyphenation_and_folds_ligatures | `normalize`, `find_in_page` | unit | hyphen join, ligature fold, whitespace collapse, soft hyphen dropped, case kept; find across hyphen |
| test_refs_layer::test_locate_reads_bbox_output_that_is_not_valid_xml | `locate_span` tolerates U+000F | unit, inline bbox XML | span found; quad (10,20,80,28), 3 words; absent phrase None |
| test_refs_layer::test_grep_searches_every_work_before_truncating | grep does not stop early | reads source of `grep_command` via inspect | "break" absent from source; "searched" and "shown" present |
| test_refs_layer::test_a_quotation_that_is_not_on_the_page_is_refused_with_the_page | propose refuses unquoted text | mapped | exit 1; page text in output; no results.json written |
| test_refs_layer::test_the_level_one_gate_is_about_order_not_derived_data | level-1-first rule | mapped | level 3 first refused "no level-1 result yet"; after a level 1, level 3 succeeds |
| test_refs_layer::test_a_proposal_is_in_no_bundle_and_no_closure | proposals file never input | mapped; one propose | `.proposed.tex` exists, `.tex` does not; no .tex in quilt names the shadow |
| test_refs_layer::test_verifying_moves_it_into_the_digest_and_records_both_parties | `refs verify` with edited statement | mapped; propose with session | exit 0; both labels in output; shadow gone; "Z" in digest; origin acts proposed, edited, verified |
| test_refs_layer::test_an_edit_never_touches_the_anchor | verify edits statement only | mapped; propose + verify | statement rewritten; source_text and anchor unchanged |
| test_refs_layer::test_a_discard_is_returned_to_whatever_proposes_it_again | discard reason returned | mapped; propose, discard | re-propose exit 1 with reason and "--supersedes"; with --supersedes exit 0 |
| test_refs_layer::test_the_manifest_keeps_the_digest_and_its_proposals_apart | manifest references split | mapped; propose, verify, propose; `loom build` | digest.file is `.tex`, proposed.file `.proposed.tex`; statement only on proposal; source_text on both; state verified |
| test_refs_layer::test_proposed_is_a_state_the_whole_viewer_can_read | `proposed` state label in manifest | mapped; propose; `loom build` | "proposed" in states.labels; key state == proposed |
| test_refs_layer::test_a_link_needs_a_kind_from_the_vocabulary_two_ends_and_a_reason | `add_link` validation, `remove_link` | mapped; two proposals | bad kind, blank why, self-link raise ValueError; id link-0001; KINDS set; removal empties |
| test_refs_layer::test_links_are_never_citable_and_never_in_a_digest | links stay out of tex and edges | mapped; two proposals, add_link; `loom build` | no .tex names link-0001; manifest links kinds ["depends-on"]; no edge via link |
| test_refs_layer::test_the_link_cli_refuses_an_end_that_is_not_a_result | `refs link` end validation | mapped; one proposal | exit != 0; "not a result" in output |
| test_refs_layer::test_recheck_makes_transcription_verified_falsifiable | `refs recheck` detects moved page text | mapped; propose, verify; edits page file | clean: exit 0, "1 … re-read; 0 moved"; after edit exit != 0, "transcription-changed", "1 moved" |
| test_refs_layer::test_recheck_never_re_reads_a_verified_rendering | recheck ignores statement | mapped; verify with different statement | exit 0 and "0 moved" |
| test_refs_layer::test_every_search_says_how_much_of_the_corpus_it_could_search | `refs find` coverage line and miss hint | mapped; one proposal | hit lists id, "coverage:", "works digested"; miss "results: 0" and "loom refs grep" |
| test_refs_layer::test_a_more_specific_title_is_not_the_same_paper | `title_ratio` prefix rule | unit | longer-title variant < 0.85; trailing period and ", I" subtitle == 1.0 |
| test_refs_layer::test_the_title_block_is_not_the_whole_page | `title_lines` limited to TOP_LINES | unit | early title found; line 45 title not found |
| test_refs_layer::test_a_filename_is_author_year_title | `filename_title` | unit | two "Author - Year - Title" stems parsed; plain stem returned as is |
| test_refs_layer::test_a_near_tie_is_a_question_not_an_answer | ingest `Candidate.ambiguous/attachable` | unit | clear lead attachable; near tie ambiguous, not attachable; lone doi signal attachable |
| test_refs_layer::test_a_pdf_on_disk_does_not_stop_loom_looking_for_the_source | resolve/fetch steps do not skip PDF works | inspect source of `build._resolve_step/_fetch_step` | substring checks: no "w.pdf" before "continue", "if w.source:", "w.pdf or got.pdf" |
| test_refs_layer::test_an_agent_cannot_vouch_for_its_own_reading | agent guard on verify/discard/accept | mapped; manual MonkeyPatch AI_AGENT=1; demo key dm-0002 | verify, discard, bare accept refused; "Referee Agent" refused; named author accepted; propose works; nothing verified |
| test_refs_layer::test_verifying_on_a_terminal_shows_both_texts_first | verify prints page and rendering | mapped; two proposals | --yes exit 0 with page and rendering headings; without --yes (no tty) exit != 0 |
| test_refs_layer::test_the_page_around_the_quote_is_what_a_rendering_is_judged_against | `page_context` shows more than the quote | mapped; short quote proposal | found; context contains "perfect obstruction theory" |
| test_refs_layer::test_a_result_stated_under_two_numbers_is_citable_by_either | `numbers_of`; alias labels | mapped; propose with `--number "1.1, 1.2"` | numbers_of splits "," and "-", keeps dotted; shadow has both labels |
| test_refs_layer::test_coverage_finds_a_work_by_author_and_refuses_what_it_cannot | `refs coverage FRAGMENT` | mapped | "manolache" finds Vir12; unknown fragment exit != 0 "not a citekey" |
| test_refs_layer::test_a_pdf_link_in_the_bibliography_is_fetchable | `pdf_url` | unit | .pdf and .PDF?query accepted; landing page, file://, missing url give "" |
| test_refs_layer::test_the_session_is_named_the_same_way_in_every_record | session id in origin | mapped; `loom ai start` | origin[0].by == printed session id |
| test_refs_layer::test_a_fresh_digest_is_not_called_thin | build does not call fresh digests thin | demo; `refs build --only extract,map` | exit 0; "too thin to trust" absent |
| test_refs_layer::test_a_statement_that_brings_its_own_environment_is_refused | statement body-only rule | mapped | three wrapped/labelled statements refused "body only"; no shadow; enumerate body accepted |
| test_refs_layer::test_an_agents_link_is_the_runs_never_the_authors | link attribution under agent | mapped; two proposals; manual MonkeyPatch | without --session refused naming "--session"; with it exit 0; link.by == session |
| test_refs_layer::test_a_statement_over_a_page_break_is_anchored_to_both_pages | two-page anchor | mapped; rewrites pages 12, 13 | single page refused; "12-13" exit 0 "pp.12-13"; anchor page 12 last 13; context has continuation; "p.~12--13" in shadow |
| test_refs_layer::test_a_run_may_correct_its_own_unverified_proposal | self-supersede by same session | mapped | same-session supersede replaces (one record, "second"); other session refused |
| test_refs_layer::test_an_authors_edit_is_kept_and_shown | `refs why` diff; re-verify rewrites digest | mapped; propose, verify twice | diff lines shown; second diff from proposal once; digest and `loom source` carry latest |
| test_refs_layer::test_findings_for_a_run_include_what_the_author_decided | `ai findings` shows discards | mapped; ai start, propose, discard | id and "discarded -- wrong theorem" in output |
| test_refs_layer::test_source_on_an_equation_label_prints_what_holds_it | `loom source` on equation label | demo; appends equation to Calloway14.tex | exit 0, no "KeyError", "inside" in output |
| test_refs_layer::test_a_book_length_map_with_almost_no_sections_says_it_is_a_guess | `PageMap.suspect` | unit | 679-page 2-section map suspect; 44-page paper not |
| test_refs_layer::test_a_folio_number_at_a_page_join_is_not_part_of_the_text | `read_pages` drops folios at joins | mapped; writes pages 5, 6 | "345"/"346" gone; inner "7" kept; cross-page propose exit 0; single page verbatim |
| test_refs_layer::test_words_the_page_does_not_have_are_named | `words_not_on_page` and propose warning | mapped | propose names Deligne, Mumford; math/commands and hyphen splits not flagged |
| test_refs_layer::test_a_pending_proposal_carries_the_words_its_page_does_not_have | manifest `not_on_page` | mapped; propose; `loom build` | row not_on_page == ["nice"]; no page_images |
| test_refs_layer::test_a_work_with_no_pdf_gets_no_geometry | `_attach_spans` without PDF | [tex]; mapped; private `render.build._attach_spans` | no "spans" key; files dict empty |
| test_refs_layer::test_local_names_are_the_papers_numbering | `--local` grammar | mapped | invented suffix refused naming cor-2.3.1 and star-; word local refused; five valid forms accepted |
| test_refs_layer::test_propose_does_not_hand_an_agent_the_authors_verb | propose wording under agent | mapped; manual MonkeyPatch | "waiting for the author", no "loom refs verify"; help text lacks "verified" phrasing |
| test_refs_layer::test_the_author_can_correct_the_locator_when_verifying | verify `--local/--taxon` rename | mapped | record renamed cor-1.1.1, taxon corollary, origin "renamed" with was; digest has new id |
| test_refs_layer::test_the_ingest_mode_says_one_thing_about_a_work_with_no_source | ingest.md has one such section | package asset `ai/modes/ingest.md` | heading count == 1 |
| test_refs_layer::test_the_write_api_verifies_renames_and_discards_a_proposal | API `digest-verify`/`digest-discard` | mapped; two proposals; AI_AGENT set; `_sid` creates session | ok responses; records verified/renamed and discarded; unknown node raises ApiError |
| test_refs_layer::test_a_work_with_a_source_is_quoted_from_its_source | `propose --source-file` tex anchor | mapped; writes latin-1 src/main.tex | tex anchor bytes match quote; taxon equation; shadow title; absent quote and page+file refused |
| test_refs_layer::test_grep_is_a_phrase_and_says_so | grep refuses regex syntax | mapped | regex-like input exit != 0 "literal phrase"; "widget" exit 0 |
| test_refs_layer::test_a_source_fetched_on_a_preprint_id_says_so_in_the_digest | `record_source` feeds extracted-from | mapped; writes src; `digest extract --no-compile` | exit 0; header has "extracted-from: arxiv:1607.00001" |
| test_refs_layer::test_a_read_command_logs_to_the_session_it_is_given | page/coverage/grep log to session | mapped; ai start | each exit 0; run.log contains the three command lines |
| test_refs_layer::test_locate_matches_across_the_two_extractions_of_one_page | `locate_span` spacing/hyphen tolerance | unit, inline XML | superscript split and hyphen split located; absent phrase None |
| test_refs_layer::test_a_quotation_over_two_lines_is_one_rectangle_per_line | `Span.lines` per line | unit | union quad; two line rects, subscript kept on first |
| test_refs_layer::test_the_anchor_check_stays_strict_while_geometry_is_loose | `find_in_page` strict on spaces | unit | "rank of the" found; "rankofthe" not |
| test_refs_layer::test_an_anchor_carries_only_its_own_kind_of_keys | `Result.to_json` anchor keys by kind | unit | pdf key set; tex key set; box anchor round-trips, no start |
| test_refs_layer::test_offsets_and_box_text_come_from_the_page_as_committed | `locate_offsets`, `words_in_boxes` | unit | raw offsets for exact and spacing-variant quotes; None for absent; words in box "inside the" |
| test_refs_layer::test_locate_refuses_what_it_cannot_answer | API `locate` refusal codes | mapped (no PDF) | four bodies raise ApiError with no-such-work, missing-field, bad-field, not-readable |
| test_refs_layer::test_a_selection_on_a_real_page_becomes_an_anchor | API `locate` on real PDF, text and box | [tex], needs poppler; showcase | text basis, page 2, quads, offsets slice == text, page_box 612×792; box basis, hint words |
| test_refs_layer::test_extract_refuses_a_source_outside_the_store | extract store gate | demo; loose tex outside store | exit != 0; "not in loom's store", "loom refs add" |
| test_refs_layer::test_extract_with_no_source_says_how_to_get_one | extract with no source | demo minus Calloway14 store and digest | exit != 0; "holds no source", fetch and add hints |
| test_refs_layer::test_a_digest_with_no_readable_copy_warns_and_never_errors | `loom:no-readable-copy` severities | two demos: store removed; PDF+pages removed, source kept | warning, exit 0, message names `refs unreadable`; source-only is info "no PDF" |
| test_refs_layer::test_declaring_a_work_unreadable_suppresses_the_lint_and_undo_restores_it | `refs unreadable` and `--undo` | demo minus store | declare exit 0, lint code gone; undo exit 0, code back |
| test_refs_layer::test_the_declaration_is_appended_and_never_edited | unreadable log append-only fold | demo minus store; exit codes unchecked | two events; declarations empty |
| test_refs_layer::test_unreadable_refuses_under_an_agent_and_without_a_reason | unreadable guard | demo; writes os.environ AI_AGENT directly | missing --why message; bare refused; named person ok; "Agent" refused |
| test_refs_layer::test_forget_is_keyed_by_citekey_or_by_a_prefix_of_a_stored_hash | `refs forget` keys | demo; `record_copy` fake ledger row | hash prefix and citekey accepted; declarations keyed sha256:/citekey; unknown refused |
| test_refs_layer::test_source_alone_is_enough_to_extract_from_and_a_work_with_neither_is_blocked | `WorkState.blocked` with source only | demo minus store; writes src | source true, pdf false, blocked ("","") |
| test_refs_layer::test_an_extracted_result_is_located_on_the_page_it_is_printed_on | committed showcase results carry pages | [tex] marker but reads only committed JSON/pages | prop-2.1 locator p.~1, page 1, text basis; cor-3.2 page 2; span starts "Proposition 2.1"; labels on pages |
| test_refs_layer::test_a_work_with_no_filed_copy_keeps_its_source_anchor | `_extracted_anchor` fallback | private function; tmp_path empty | kind tex, page 0 |
| test_refs_layer::test_the_viewer_can_switch_retitle_and_tombstone_a_session | API session-use/rename/delete | demo; two `session new` | active switches; title changes; delete removes, active None; no session-purge capability |
| test_refs_layer::test_a_message_lands_with_nobody_listening_and_is_read_not_consumed | mailbox cursors | demo; session new | no attached; message read once per reader cursor, still visible to another reader |
| test_refs_layer::test_presence_goes_stale_rather_than_being_believed_forever | attached heartbeat expiry | demo; rewrites attached.json beat | attached lists agent; stale beat hides it; detach empties |
| test_refs_layer::test_an_agent_that_has_not_said_who_it_is_is_refused_rather_than_guessed_at | `writer` identity | demo; os.environ AI_AGENT | agent/person by name; undeclared under marker raises; declared wins |
| test_refs_layer::test_the_write_api_refuses_a_post_from_another_page | `LoomHandler._csrf` | unit; fake handler object | good headers ""; bad origin, form content-type, missing token named |
| test_refs_layer::test_the_composer_posts_and_says_whether_anyone_heard | API `message` reports listeners | demo; session new; attach | attached [] then ["Referee Agent"]; event body stored |
| test_refs_layer::test_an_anchor_round_trips_in_both_bases | anchor to_json/from_json | unit (tmp_path unused) | text, box, tex anchors round-trip all fields; no cross-kind keys |
| test_refs_layer::test_a_hyphenated_line_and_a_ligature_both_place | hyphen split across lines | unit (tmp_path unused); no ligature in data | span found; two line rects |
| test_refs_layer::test_a_resumed_session_starts_a_new_round | session resume rounds | demo; sessions API | one round; close marks closed; resume opens, two rounds, last_opened matches |
| test_refs_layer::test_a_kind_is_named_by_any_unambiguous_prefix_and_severity_only_grades_a_fault | `full_kind` prefixes; comment severity rule | demo; `loom comment` | prefixes resolve; "c" ambiguous None; question with severity refused |
| test_refs_layer::test_a_post_carries_what_changed_since_the_last_one | message `changed` block | demo; comment then two messages | first carries dm-0002 created by author; second empty |
| test_refs_layer::test_a_note_on_a_page_round_trips_through_the_log | page-anchor annotations parse | demo; appends raw log events | no problems; text/box anchors parsed; key note has no anchor; to_dict shapes |
| test_refs_layer::test_a_note_on_a_page_resolves_against_the_store_and_not_against_a_key | recorded/detached; status --reading; findings | demo; fake sections/pages; raw events | resolved flags per note; status json reading rows; `--reading` listing; findings (work,page) |
| test_refs_layer::test_a_note_on_a_page_is_written_by_citekey_or_identifier_and_refused_legibly | `loom comment --page/--quote/--box` | [tex], needs poppler; showcase | three writes recorded with offsets/quads/target; six refusals' messages; batch box line |
| test_refs_layer::test_the_endpoint_and_the_record_map_a_place_the_same_way | locate preview == comment record | [tex]; showcase | recorded anchor equals preview minus quads; box comment ok "(box)" |
| test_refs_layer::test_the_sidecar_carries_the_notes_on_a_page_and_the_reference_counts_them | build sidecar marks and reading counts | [tex]; showcase; two comments; `loom build` | reading totals; annotation target shape; basis; marks per note; quads kept; page rotate/width; Arden24 zero |
| test_refs_layer::test_a_session_is_named_on_the_spot_and_closed_from_the_page | API session-new/close | demo | new active with title; close clears active; second close raises "is closed" |
| test_refs_layer::test_a_locator_by_offsets_lights_the_same_place_a_selection_would | API `locate` by span | [tex]; showcase | span and text give same quads; start and text echoed |
| test_refs_layer::test_an_agent_parked_on_session_next_wakes_when_a_message_lands_with_what_changed | `session next --wait` wakes on post | demo; real subprocess `python -m loom`; sleep 1.5 s; timing | still running before post; exit 0; wakes < 5 s; text and changed body in JSON |
| test_refs_layer::test_a_declared_agent_is_an_agent_however_its_name_is_punctuated | `is_agent` tokenisation | unit | seven agent spellings true; four person names false |
| test_refs_layer::test_the_authors_verbs_refuse_a_declared_agent_whatever_shell_it_is_in | name-based guard | [tex] marker, unneeded; showcase; CliRunner env | unreadable and verify refused "is an agent"; named author under AI_AGENT ok |
| test_refs_layer::test_a_browser_write_is_the_person_at_the_browser_not_the_servers_shell | API comment author under agent shell | demo; config author appended; os.environ AI_AGENT | human note by config author; named agent recorded kind agent |
| test_refs_layer::test_a_reader_who_is_working_is_not_a_reader_who_was_never_here | `waiting_on` messages | demo; attached.json beat rewritten | never: "nobody is attached" + watch hint; attached: ""; stale: "probably working", no watch hint |
| test_refs_layer::test_refs_locate_names_the_place_and_not_only_the_page | `refs locate` JSON and open link | [tex]; showcase; `write_serve_json` | basis/start/end; slice == quote; `span=` link printed; box or span for second |
| test_refs_layer::test_a_change_carries_an_address_its_reader_can_use | `pending` adds work/page; `render` | [tex]; showcase; two comments; fake event type | page note work Bellamy19 p.2, doi target; key note work None; render names "Bellamy19 p.2" |
| refs/test_resolve::test_a_query_is_the_entry_without_its_markup | `query_for` strips braces, surnames | unit | title unbraced; surnames tuple; "and others" dropped; year |
| refs/test_resolve::test_scoring_is_by_title_then_author_then_year | `score` weights and thresholds | unit | exact 1.0; subtitle-less >= STRONG; title only in [POSSIBLE,STRONG); wrong title < POSSIBLE |
| refs/test_resolve::test_a_formatted_reference_is_scored_by_what_it_contains | free-text query scoring | unit | matching record 1.0; unrelated < POSSIBLE |
| refs/test_resolve::test_zbmath_answers_with_a_doi_and_the_preprint_it_knows | zbMATH parsing and short-circuit | recorded JSON; fake transport; SPACING 0 | one doi candidate, also ordered arxiv then zbl, strong, source; one request with ti: |
| refs/test_resolve::test_crossref_is_asked_for_a_doi_when_zbmath_has_none_and_picks_the_book_not_its_chapters | Crossref fallback and merge | recorded JSON | only book DOI; zbl pooled in also; source joined; two requests |
| refs/test_resolve::test_a_404_is_no_match_rather_than_a_failure | NothingFound handled | inline transport | candidates == [] |
| refs/test_resolve::test_biblatex_dates_count_as_years | `date` field year | unit | year "1998" |
| refs/test_resolve::test_one_service_failing_is_not_a_failed_lookup_but_both_are | partial failure tolerance | recorded JSON | Crossref alone answers; both failing raises ResolveRefused |
| refs/test_resolve::test_an_answer_is_cached_and_not_asked_for_twice | resolver disk cache, refresh | tmp cache dir | second resolver asks nothing; refresh asks again |
| refs/test_resolve::test_contact_goes_to_crossref_only_when_set | mailto only to Crossref | recorded JSON | mailto in Crossref URL not zbMATH; absent when unset |
| refs/test_resolve::test_candidates_are_kept_with_the_entry_they_answer_and_forgotten_when_it_changes | save/load keyed by synthetic id | tmp root | path under storage/synthetic; load returns id; year edit forgets; as_workid provenance |
| refs/test_resolve::test_resolving_is_refused_until_the_author_allows_it | `refs resolve` consent gate | demo + Edi98 cited | exit 2, "resolve = true"; no resolved.json under `refs/` (wrong directory) |
| refs/test_resolve::test_the_command_proposes_lint_names_the_proposal_and_the_manifest_carries_it | resolve CLI, lint, manifest | demo + Edi98; config edited; `http_get` monkeypatched | lint unresolved; resolve output; bib untouched; json lookups 0; lint names candidate; build exit 0; manifest candidate dict |
| refs/test_resolve::test_the_resolve_flag_is_one_runs_consent_and_writes_no_config | `--resolve` one-run consent | demo + Edi98; fake http | refused exit 2 naming --resolve; with flag exit 0 and candidate; config unchanged |
| refs/test_scan::test_a_bibitem_yields_its_identifiers_and_a_heuristic_title_author_and_year | `bibitems`, `bibitem_fields` | unit | keys order; GP99 title/author/year/eprint/heuristic; Inline title/doi/year |
| refs/test_scan::test_an_entry_that_italicises_nothing_still_yields_author_title_and_year | plain-convention bibitem | unit | author, title, year parsed |
| refs/test_scan::test_scan_copies_named_bib_entries_verbatim_and_converts_bibitems | `scan_bibliography` adds | hand-built minimal quilt | added order; note kept verbatim; provenance comment; three keys |
| refs/test_scan::test_scan_only_appends_and_never_rewrites_a_corrected_entry | append-only | minimal quilt | re-scan adds nothing, present 2, file unchanged; deleting canon removes nothing |
| refs/test_scan::test_two_canon_documents_disagreeing_on_a_key_keep_the_first_and_say_so | conflict reporting; write=False | minimal quilt, three canon docs | one conflict tuple; no file written; "conflict: GP99" line |
| refs/test_scan::test_a_document_in_the_seed_space_is_copied_once_and_offered_an_entry | seed copy-once by hash | minimal quilt; hand-written PDF read by the shimmed `pdftotext` | copied once to storage; entry title and loom-source; rescan, rename, delete copy nothing |
| refs/test_scan::test_a_document_the_store_holds_and_no_entry_names_is_adopted_once | orphan adoption once | minimal quilt; hand PDF; entry deleted by string surgery | no adoption while named; one adoption after delete with title/source and report line; none after |
| refs/test_scan::test_a_forgotten_document_is_not_offered_again | forget tombstone honoured | minimal quilt; `declare` | adopted [], forgotten 1, report line, bib unchanged; undo re-offers |
| refs/test_scan::test_a_bib_file_in_the_seed_space_is_read_like_one_a_document_names | seed .bib read | minimal quilt | Dropped added with title |
| refs/test_scan::test_a_document_that_states_no_identifier_is_reachable_from_its_own_entry | `loom-file` overrides synthetic id | minimal quilt; hand PDFs | filed PDF; loom-file path; primary differs; work_dir == filed; arXiv case only if detected |
| test_digest::test_postnote_normalization_table | `postnote.normalize/parts` | unit | fourteen normalisation and split cases |
| test_digest::test_postnote_match_edge_unmatched_and_no_postnote | postnote edges and lint | digest-demo; edits dm-0002 and digest | comment-hidden cite no edge; prop and section edges; unmatched lint; alias clears it; bare cite no diag |
| test_digest::test_version_mismatch_and_missing_package_and_undigested | version-mismatch, missing-package, --undigested | digest-demo; hand digest and bib edits | both lint codes with details; `status --undigested` == ["Ref20"] |
| test_digest::test_extract_from_source_drops_proofs_keeps_uses_and_refuses_existing | full extraction output | digest-demo; fake TeX shim produces .aux | header lines; requires; no proofs; env names, uses, emulated numbers, macros, sections, overview, setup; report; refuses existing; deps; bundle groups |
| test_digest::test_extract_counter_emulation_when_compile_fails | emulated numbering on compile failure | digest-demo; FAKE_TEX_FAIL=1 | "numbering: emulated" header and report; six labels present |
| test_digest::test_import_digest_as_rewrites_prefix | `digest import --as` | digest-demo; extract; second demo | prefix, labels, uses, cite, eqref rewritten; no Ref20; digest-without-bib reported; no overwrite |
| test_digest::test_fetch_refused_without_config | fetch consent gate | digest-demo | exit 1 "fetch = true"; no .tex under `refs/` (wrong directory) |
| test_digest::test_build_runs_with_the_network_off | build report offline | digest-demo | exit 0; same four phrases as the refs_layer build test |
| test_digest::test_build_refuses_an_unknown_step | `--only` validation | digest-demo | exit 2 "unknown step" |
| test_digest::test_fetch_writes_gitignored_dirs | real arXiv fetch | network marker plus LOOM_NETWORK env; real network | exit 0; src and paper.pdf under `digests/arxiv/…` (stale path) |
| test_digest::test_requires_missing_package_named_first_on_bundle_failure | compile prints missing-package first | digest-demo; extract; FAKE_TEX_FAIL | exit 1; first line missing-package xy; last "FAILED bundle" |
| test_digest::test_unverified_locators_when_the_artifact_and_the_cited_work_differ | `loom:unverified-locators` | digest-demo; hand digest three ways | preprint alone clean; published-as fires; missing extracted-from fires with message |
| test_digest::test_a_wrapper_around_a_theorem_environment_is_one_and_shares_its_counter | wrapped defn counted | fresh digest-demo via `_extract` | Bf97-def-1.2, lem-1.3 present, lem-1.2 absent |
| test_digest::test_a_theorem_declared_after_begin_document_is_still_a_theorem | body-declared newtheorem | fresh digest-demo | thm-1.1 and lem-1.2 present |
| test_digest::test_a_wrapper_takes_its_name_from_what_it_prints_when_the_counter_has_none | name from `{\bf Name.}` | fresh digest-demo | `\begin{theorem}` or Ro22-thm present; Ro22-lem present |
| test_digest::test_a_parameter_glued_to_a_control_word_stays_separate | macro expansion spacing | unit | space inserted after control word; none before backslash |
| test_digest::test_a_macro_that_is_a_program_is_kept_not_expanded | `is_simple`, `expand_macros` | unit | trap and self-reference not simple; Hom expanded; Bbb kept; used == {Hom} |
| test_digest::test_the_setup_node_carries_the_papers_own_conventions | setup from conventions heading/Throughout | three fresh digest-demos | setup has the sentence, no incomplete/label; no-conventions paper incomplete |
| test_digest::test_standing_assumptions_stated_as_sentences_are_found | gathered assumption sentences | fresh digest-demo | two sentences kept; section/proof-scoped excluded; "check each one's scope" |
| test_digest::test_a_step_that_is_off_with_work_waiting_says_how_to_turn_it_on | off-switch advice lines | digest-demo | exit 0; exact resolve and fetch advice sentences |
| test_refs_identity::test_resolution_order_and_paths | `identify` DOI, `path` sanitised | unit | one doi id, published; path with underscore |
| test_refs_identity::test_arxiv_doi_is_a_preprint_not_a_publication | 10.48550 DOI treated as arXiv | unit | single arXiv id; preprint not published |
| test_refs_identity::test_synthetic_id_is_deterministic_across_machines | `synthetic` normalisation | unit | whitespace-insensitive equality; 8-char work id; year changes it; identify falls back |
| test_refs_identity::test_identifier_round_trips_through_its_written_form | `parse(str(w))` | unit | three schemes round-trip; junk and unknown scheme None |
| test_refs_identity::test_sanitise_is_path_safe | `sanitise` | unit | no "/"; math/0605234 → math_0605234 |
| test_refs_identity::test_migrate_moves_digests_and_splits_provenance | `migrate` layout and header split | hand-built legacy tree | digests moved; published-as vs extracted-from; prefix added; artifacts to `refs/<scheme>/<id>`; idempotent |
| test_refs_identity::test_migrate_drops_retired_config_and_keeps_the_comments | retired config removal | hand config.toml | retired list; crawl/runner removed; comments and tables kept; no triple newline; idempotent |
| test_refs_identity::test_primary_is_none_without_an_entry | None entry | unit | primary None; identify [] |

## Critique

### Redundant or overlapping

- `test_refs_layer.py:105 test_build_says_what_is_off_and_what_is_left` and `test_digest.py:240 test_build_runs_with_the_network_off` assert the same four substrings on `refs build` in a demo quilt. Keep one; the digest-demo variant is the better home because `test_digest.py:502` sits beside it and already runs the same command with stronger assertions. Merge all three into one test.
- `test_refs_layer.py:1155 test_an_anchor_carries_only_its_own_kind_of_keys` and `:1591 test_an_anchor_round_trips_in_both_bases` both pin the per-kind key stripping of `Result.to_json` and the round trip; their docstrings describe the same bug. Keep `:1591`, the fuller one, and move the exact-key-set assertion from `:1155` into it.
- `:1106 test_locate_matches_across_the_two_extractions_of_one_page`, `:1129 test_a_quotation_over_two_lines_is_one_rectangle_per_line` and `:1615 test_a_hyphenated_line_and_a_ligature_both_place`: the third is the first's hyphen case plus the second's line count. It also has no ligature in its data, although its name and docstring say it does. Delete `:1615`, or give it a real `ﬃ` word so it tests what it says.
- Agent-guard tests, which exercise one guard (`refuse_under_agent`/`writer`) five times: `:606` (verify, discard, accept), `:1362` (unreadable), `:1537` (`writer` directly), `:2149` (declared name, markers unset), `:2169` (API). Keep `:1537` as the unit and `:2149` as the one CLI check, and fold `:1362`'s "--why is required" assertion into the unreadable tests. `:606` also tests `loom accept`, which is not a refs verb.
- Session and mailbox tests: `:1473` and `:2020` both drive the session API (use/rename/delete vs new/close). `:1516` and `:2206` both backdate `attached.json` beats. `:1499`, `:1575` and `:1666` all post and read mailbox events. They overlap each other, and with `tests/unit/test_packets.py:211`, which tests the same "viewer message is the person's under an agent shell" property as `:2169`. None of these are about refs; see Delete or combine.
- Locate: `:1219`, `:1929`, `:2039` and `:2230` each assert `page_text[start:end] == "…"` for a text anchor on showcase page 2. `:1929` checks that preview and record agree, which implies `:1219`'s text half. Keep `:1219`'s box half, `:1929` and `:2039`, and trim `:2230` to the `span=` link it exists for.
- `:201 test_the_page_text_is_committed_and_the_pdf_is_not` and `:212 test_the_demo_gitignore_agrees_with_the_one_init_writes` both read the gitignore rules. Combine them into one test with two assertions.
- `:56` (candidate via `resolve.save`) and `refs/test_resolve.py:160` both exercise `save`/`load`. They are complementary rather than duplicates. Keep both, but `:56` could build its root with a bare `tmp_path` instead of `quilt()`.
- `:355 test_verifying_moves_it_into_the_digest_and_records_both_parties` and `:699 test_the_session_is_named_the_same_way_in_every_record` both read `origin[0]["by"]`/acts. Small overlap; `:699` is justified by the `ai start` spelling.

### Long or slow

Measured single-test timings on this machine: `init --demo` about 30 ms; a mapped test with `loom build` 0.35 s; `test_extract_from_source…` 0.22 s; `test_import…` 0.11 s; the showcase comment test 0.21 s; the subprocess test 1.76 s. The slice is cheap overall, probably under 15 s. Cost comes from:

- `:2052 test_an_agent_parked_on_session_next…` costs 1.76 s, 1.5 s of it a fixed `time.sleep`. It is the slowest test in the slice by 5×. Replace the sleep with a poll on `loom.mailbox.attached(q, sid)` (the parked process heartbeats), which usually finishes in about 0.3 s and makes "was parked" a fact rather than an assumption (see Other).
- Tests that run a full `loom build` only to read one manifest field: `:409`, `:429`, `:463`, `:916`, and `refs/test_resolve.py:201`. Each is about 0.3 s. `:429` and `:916` could assert against `render.build` manifest assembly for references alone, if such an entry point exists, or share one built quilt through a module-scoped fixture.
- `test_digest.py:455 test_the_setup_node_carries_the_papers_own_conventions` builds three demo quilts in a loop, and `_extract` rebuilds the whole digest-demo (init plus `refs add` of REF) for every source string (`:378`, `:385`, `:391`, `:491`). Extraction depends only on the source and a bibliography entry, so one module-scoped quilt with several entries added would do.
- `test_digest.py:216 test_import_digest_as_rewrites_prefix` inits two demo quilts. That is acceptable.
- Six showcase tests `copytree` 972 KB each. This is cheap, but `_showcase` and the inline copy at `:1228` duplicate each other.

### Delete or combine

- **Move out of this file** (they test sessions, mailbox, records, serve and CLI identity, not refs): `:1473`, `:1499`, `:1516`, `:1537`, `:1554`, `:1575`, `:1634`, `:1649`, `:1666`, `:1718`, `:1769`, `:2020`, `:2052`, `:2135`, `:2169`, `:2206`, plus `:851` (`loom source`) and `:841` (`ai findings`). That is about 18 tests, a sixth of the file, and they belong in `records/`, a sessions or mailbox module, and `render/test_serve.py`. Moving them is safe and costs nothing; it makes `test_refs_layer.py` about refs.
- **Delete, vacuous:** `:708 test_a_fresh_digest_is_not_called_thin`. The demo's only stored work already has a digest and two pages, and `WorkState.thin` (`src/loom/refs/build.py:55`) needs `pages >= 8`, so the phrase can never appear whatever the code does. Replace it with a real test (see Missing).
- **Delete or rewrite, vacuous:** `:127 test_match_lists_only_what_a_person_must_look_at` accepts either of two outcomes, which covers every non-crashing run. `:114 test_build_json_orders_by_how_often_a_work_is_cited` sorts `[2, 0, 0]` over Calloway14, Har77 and Man12, which alphabetical order also produces. Its docstring cites relloc's 22 entries, which is not the fixture. Add a second cited work with more citations and alphabetically later, so the order can only come from counts.
- **Delete or rewrite, tests source text:** `:256 test_grep_searches_every_work_before_truncating` (`"break" not in inspect.getsource(...)`) and `:592 test_a_pdf_on_disk_does_not_stop_loom_looking_for_the_source` (asserts substrings like `"if w.source:"`). Both fail on a harmless rename and pass on a real regression written differently. Replace them with behavioural tests: two mapped works each holding more hits than `--limit`, checking that both appear in the "searched" count; and a `survey`/`build_refs` run with `_get` monkeypatched, checking that a work with `paper.pdf` still resolves and fetches source.
- **Delete, stale and unused:** `test_digest.py:254 test_fetch_writes_gitignored_dirs` asserts `q / "digests" / "arxiv" / "0805.2065v2"`, but `work_dir` files under `digests/storage/…` (`src/loom/refs/pages.py:82`). It would fail if anyone ran it. It is double-gated (marker plus `LOOM_NETWORK`). Replace it with an offline `fetch_work` test, or fix the path.
- **Ask the author:** `test_refs_identity.py:74` and `:113` pin `loom upgrade`'s migration. The first asserts artifacts are moved into `refs/arxiv/…` (`src/loom/refs/migrate.py:124`), which book 8.16 now calls the author's seed space that loom "never writes". Under the no-backwards-compatibility rule the migration and its tests are candidates for removal. If kept, the target should be `digests/storage`.
- **Combine** the three `refs build` report tests (`test_refs_layer.py:105`, `test_digest.py:240`, `:502`). Combine `:1155`+`:1591` and `:201`+`:212` as above.

### Missing

Refs code with no test anywhere in `loom/tests`:

- `fetch_work` (`src/loom/refs/fetch.py:232`) is untested offline. Four behaviours need a test: the arrival check discarding a wrongly titled source and returning `discarded` (fetch.py:~297); `allow_candidate=False` refusing (~282); a source-less entry with only a PDF url routed to `_fetch_url`; and `record_source` being written only on arrival. Monkeypatch `loom.refs.fetch._get`.
- `_get` retrying 406/429/5xx twice with a pause (fetch.py:~113, book 8.9 DR-77), and `_unpack` refusing paths that escape `src/` (book 8.9). Both are security- or robustness-relevant and untested.
- `_fetch_url` (fetch.py:~365): non-`%PDF` refused, title-mismatch PDF deleted, `fetched.json` written with hash.
- `refs ingest` and `ingest.look_at`/`identifiers_in` (`src/loom/refs/ingest.py:110`, `:117`; `cli/refs.py:1565`). The book 8.9 rule "two agreeing signals attach" is tested only on a hand-built `Candidate`. Nothing exercises `--dry-run`, the "already has a PDF" skip, or the JSON.
- `refs drop` (`cli/refs.py:1237`) has no test: the exactly-one-of guard, the three selection modes, the non-tty refusal without `--yes`, and "verified nodes in digests/ untouched".
- `refs links --depth` (`cli/refs.py:1352`, book 8.14 "walks them") and `refs unlink` CLI (`:1392`) have no test. `touching` is also untested.
- `refs path` (`cli/refs.py:80`): `--pdf`/`--src`, and exit 1 with the "nothing there yet" hint. It is only named in the AGENT_COMMANDS assertion.
- `refs add` refusals (`cli/refs.py:118-131`): non-PDF/non-tex file, existing artifact without `--force`, `--force` replacing, and a directory copied as source.
- `refs scan --dry-run` CLI (`cli/refs.py:305`): nothing checks that the dry run writes nothing through the CLI (`write=False` is tested at function level only).
- `refs page` ranges `N-M`, `--json` and out-of-range pages (`cli/refs.py:668`). It is only invoked once, for logging.
- `refs overview` "no Overview" exit (`cli/refs.py:1645`).
- `refs resolve` (`cli/refs.py:150`): unknown citekeys refused (`:173`), a failed lookup exiting 1 (`:219`), "every cited work states an identifier", `--refresh` through the CLI, and `[refs] contact` from config reaching `Resolver`. `Resolver.candidates` raising on an empty title (`src/loom/refs/resolve.py:250`) is also untested. Request spacing (`SPACING`, book 8.9.1 "at least a second apart") is disabled by the autouse fixture and never asserted. A test with a fake clock could check that two requests to one service are spaced.
- `merge` pooling by title and year when identifiers differ (`resolve.py:280`), and tie-breaking by identifier rank.
- `WorkState.thin` and `needs_an_agent` (`build.py:50`, `:77`): a digest with, say, 1 result on 12 pages must be reported as needing an agent. Nothing covers the positive case.
- Book 8.9 "every step is keyed on a hash, so a second run redoes only what changed" (`build_refs`, `build.py:395`) is untested. So is `pages.is_current`/`write_map` re-mapping when the PDF hash changes (`pages.py:291`, `:352`).
- Book 8.16 "a document arriving for a work that already has one is filed beside it, under a sibling entry `<key>A`" has no test in `refs/test_scan.py`.
- `search.statement_span` (`src/loom/refs/search.py:289`), which places extracted results on pages (DR-224), is covered only indirectly through the committed showcase JSON (`:1420`), which does not run the code.

Digest (book 8.4, 8.5, 8.8, 8.10) rules with no test:

- `numbering: mixed` (DR-180, 8.4).
- `\newtheorem*` → `<slug>-<abbrev>-star-<n>` with an `(unnumbered)` title (DR-67).
- `\appendix` lettering.
- A duplicate number skipped and reported.
- A paper with no introduction getting `\incomplete{Overview not extracted…}`.
- The 1,500-character cap on the setup node.
- `digest extract --to`.
- `loom:digest-without-bib` on extract (only `import` covers it).
- The pre-0.5 `source:` header still read (8.4).
- A version taken from the entry's `version` field (8.8).
- The postnote exemption inside the cited work's own digest (DR-66, 8.7).
- The `-setup` node answering `\cite[Standing assumptions]` (it is tested in `parts` only, not as an edge).
- `digest import --as` rewriting `\cref`/`\Cref`/`\autoref` and reporting `loom:unknown-environment` (8.10).

`test_digest.py:391` asserts `"\\begin{theorem}" in text or "Ro22-thm" in text`. That passes if any theorem appears, but DR-180's claim is exact numbering, so assert `Ro22-thm-1.1` and `Ro22-lem-1.2`.

### Failure diagnostics

- **An exit code of 1 hides crashes.** `EXIT_CONTENT == 1` (`src/loom/cli/_common.py:15`), and CliRunner also returns 1 for an uncaught exception. So `assert run("build", cwd=q).exit_code in (0, 1)` (`:415`, `:432`, `:473`, `:922`, `:1999`) accepts a traceback, then fails later at `json.loads(... manifest.json)` with a FileNotFoundError that says nothing about the build. Likewise a bare `!= 0` accepts a crash as a refusal: `:650`, `:779`, `:803`, `:953`, `:1284`. Better: in the shared `run` helper, re-raise `r.exception` when it is not a `SystemExit` (`if r.exception and not isinstance(r.exception, SystemExit): raise r.exception`), or invoke with `catch_exceptions=False`. Then assert `r.exit_code == 1, r.output`.
- **Around 60 exit-code asserts print nothing on failure**, for example `assert propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y").exit_code == 0`, repeated about 30 times from `:340` to `:1014`. When the setup propose fails, the reader sees only `assert 1 == 0`. Make `propose` itself assert (`def propose_ok(...)`, `r = propose(...); assert r.exit_code == 0, r.output; return r`). The same applies to `refs/test_resolve.py:228` (`run("build").exit_code == 0`), `test_refs_layer.py:196`/`:198` (`r.exit_code == 0 and "0 mapped" in r.output`, which does not show which half failed), `:1356`/`:1357` (exit codes not checked at all before counting events), and `:2257`/`:2274` (comments whose results are discarded).
- **Compound `and` asserts** such as `assert r.exit_code != 0 and "the author's" in r.output and "AI_AGENT" in r.output, r.output` (`:620`) are fine because they carry the output. Many do not: `:339`, `:403`, `:486`, `:499`, `:506`, `:530-533`, `:1074`, `:1399`. Split them, or add `, r.output`.
- **Bare asserts over big structures:** `refs/test_resolve.py:230` compares a whole candidate dict (acceptable; pytest diffs dicts). `test_refs_layer.py:1827` checks `not any("a-2026-09-21" in json.dumps(e) for e in j["keys"].values())`, which on failure does not say which key carried it. `:1831` joins four substrings in one `and`. `:2002-2008` compares a dict to itself partly (`"hash": manifest[...]["hash"]`). Say "has keys key/work/page with these values" instead.
- **Magic numbers with no explanation:** `"deadbeef" * 8`, `"pages": 12, "chars": 120` in `mapped()` (`:316`). `sha = "9f2c" + "0"*60` (`:1390`). The quad `(10.0, 20.0, 80.0, 28.0)` (`:252`) is derivable from the XML above it, and a comment saying "xMin of first word to xMax of third" would help. `page_box == {"width": 612.0, "height": 792.0}` (`:1236`) is US Letter; say so.
- **Opaque fixture:** `mapped()` builds its store path with `__import__("loom.scan.scan", fromlist=["scan"]).scan(__import__("loom.scan.quilt", ...).load_quilt(q)).bib[ck]` (`:299-304`), has a dead `_ = write_map` (`:323`) and imports json as `_json`. `_home()` (`:871`) already does the same thing readably. Use `_home` in `mapped`. `:676` `_ = node_tex` is also dead.
- **JSON parsing that tolerates noise:** `refs/test_resolve.py:220` does `json.loads(r.output[r.output.index("{"):])`. This hides a stray line printed before JSON on stdout, which is exactly what `--json` consumers break on. Assert that the output parses whole, and send notes to stderr (`CliRunner(mix_stderr=False)` or `r.stdout`).
- **Messages that are good examples to copy:** `:124`, `:208`, `:365` and `:1454` (`f"{r['id']} claims {label} on page {page}"`). The guard tests at `:2158-2159` (`(verb, r.output)`) show the right register.

### Other

- **Vacuous negative checks against the wrong directory.** `refs/test_resolve.py:198` asserts no `resolved.json` under `q/"refs"`, but candidates are saved under `digests/storage/<synthetic>/resolved.json` (`src/loom/refs/resolve.py:313`), and the line's `if … else True` makes it pass whenever `refs/` is absent. `test_digest.py:237` does the same for fetched `.tex`. Both would pass if the gate were removed. Assert on `storage_root(q)` instead. The book is stale in the same way: 8.9 says artifacts go to `refs/<scheme>/<identifier>/`, 8.9.1 says `refs/work/<hash>/resolved.json` and `refs/cache/resolve/`, and chapter 14 line 43 says `refs/**/paper.pdf`. The code uses `digests/storage/…` (`cli/refs.py:179`). This is pass 1 (stale fact) for the doc owner.
- **Wrong marker for the page-geometry tests.** The `[tex]` tests at `:1219`, `:1848`, `:1929`, `:1974`, `:2039`, `:2230` and `:2251` need poppler (`pdftotext -bbox-layout`), not TeX. `conftest.py:64-69` skips them when latexmk is absent and runs them without poppler when poppler is absent, so they fail rather than skip. `:931`, `:1420` and `:2149` need neither and are skipped for no reason on a TeX-less machine. A `poppler` marker gated on `REAL_POPPLER_BIN` would fix all ten.
- **Timing fragility in `:2052`.** After `sleep(1.5)` the test asserts only that the process has not exited. If Python start-up plus import takes longer than 1.5 s (a cold CI box), the post lands before the process parks. The process then returns immediately from the pending cursor, the test passes, and the wake path is never exercised. Poll `attached(q, sid)` for the agent before posting. `woke < 5` is also a wall-clock threshold that a loaded machine can break.
- **Environment handled by hand.** `:1369`, `:1544` and `:2179` write `os.environ["AI_AGENT"]` directly with try/finally `del`. `:612`, `:744`, `:964` and `:1015` construct `pytest.MonkeyPatch()` manually, and `:592`/`:606` even declare an unused `monkeypatch: object` parameter. Use the `monkeypatch` fixture. The autouse `isolated_env` already clears markers, so this is style, not a leak today.
- **`os.chdir` in the shared `run` helper**, copied into three files (`test_refs_layer.py:28`, `refs/test_resolve.py:173`, `test_digest.py:58`) along with `quilt`/`demo`, makes the slice unsafe under pytest-xdist threads and duplicates code. Pass `--quilt` or use `CliRunner().invoke(main, args, catch_exceptions=False)` with `cwd` isolated, and put the helpers in a `tests/unit/refs/conftest.py`.
- **Tests of private functions or implementation:** `:931` (`render.build._attach_spans`), `:1457` (`proposals._extracted_anchor`), `:1554` (`LoomHandler._csrf` on a hand-made fake), and `:256`/`:592` (source text). `:1420` tests a committed fixture rather than code: extraction regressions show up only when the showcase is regenerated.
- **Conditionally vacuous:** `:212` (the `if demo.is_file()` guard makes it pass if the demo's file is deleted) and `refs/test_scan.py:239` (the arXiv half runs only if the hand-written PDF's id was detected). Replace the `if` with an assertion.
- **Hermeticity:** no leaks found. HOME, PATH, git config and TeX trees are isolated by `conftest.py:55`. On the default PATH `pdftotext` and `pdfinfo` are the fake shim (`conftest.py:16-29`), so `refs/test_scan.py`'s hand-written PDFs are read by the shim, not poppler. Their titles come from the filename convention, and "a title is never guessed from page one" (book 8.16) is never tested against a real text layer. The one network test is double-gated and stale (above).
- **Docstrings against CLAUDE.md** ("document the current state only"): `:1365` narrates that "this test asserted the opposite until 2026-09-21". `:932-934` ("The image pipeline it replaces…"), `:1719` ("`Selector.from_dict` used to swallow…"), `:2136` and `:2170` are changelog prose. Incident narration in test docstrings is house style, but these read as diffs.
