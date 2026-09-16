# 14. Tests

This chapter lists the tests the MVP must pass. It defines the tiers, the shim that makes the fast tier possible, the fixtures, the CI jobs, the Overleaf procedure, and then the tests themselves, grouped by chapter of the specification they verify. A test's name here is the name it should have in code, so that coverage of this chapter can be checked mechanically.

## 14.1 Tiers

**[decided]**

- Unit tier: pure functions and commands that need no LaTeX, run against the fake `latex`. Seconds. Runs on every push.
- TeX tier: everything that compiles, converts diagrams, or reads real `.aux` files. Minutes. Runs in a TeX Live container on every push.
- Paper tier: the Manolache and ACGS fixtures. Skipped unless `LOOM_PAPER_FIXTURES` names a directory containing them. Runs locally only.
- Manual tier: the Overleaf procedure and the agent sessions. Run per release; results recorded in the release notes.
- Arras tiers: unit (vitest) on components with hand-built manifests; end-to-end (Playwright) on the vendored fixture; prerender (the static build of the fixture, every route present).

## 14.2 The fake `latex`

**[decided]** `tests/fake_latex/` provides executables named `latexmk`, `pdflatex`, `latex`, `dvisvgm`, `bibtex`, `pdftotext` on the test `PATH`. They: parse the input file enough to find `\label`s and `\newtheorem` declarations, emit a plausible `.aux` with sequential numbering by section, emit an empty PDF placeholder, emit a fixed SVG for any `dvisvgm` call, and emit the source's text for `pdftotext`. They record every invocation to a log the tests can inspect. They must never be found on the real `PATH` outside tests.

## 14.3 Fixtures

**[decided]**

- `tests/quilts/demo/`: the quilt `loom init --demo` writes; small; every command runs on it in under a second on the shim.
- `tests/quilts/synthetic/`: the quilt described in `specs/fixture.md` §1; exercises every construct in the source contract and every diagnostic code.
- `tests/quilts/edge/`: small quilts each isolating one hard case: an environment spanning files; a `\begin` not alone on its line; a cycle; a double inclusion; a `\nest` inside a `\nest`; a digest with a nonempty macro block whose name collides with the quilt's; two masters with a taxon conflict; a beamer talk master.
- `tests/fixture/`: the vendored conformance snapshot.
- `tests/fixtures/` in the workspace: arXiv sources, uncommitted.

## 14.4 CI

**[decided]** Two workflows in `loom/`: `unit.yml` (Python matrix on the shim, ruff, mypy) and `tex.yml` (a TeX Live container image; the TeX tier; the Overleaf proxy: compile the demo and synthetic masters with `latexmk` from the root, an output directory, and an empty environment). One workflow in `arras/`: build, vitest, Playwright on the fixture, prerender, publish artefacts on tags. The workspace has a workflow that runs the dialect validator over `specs/fixture/`.

## 14.5 The Overleaf procedure

**[decided]** Manual, per release:

1. `loom init demo --demo`; `loom compile`; record `pdftotext` of the local PDF.
2. Zip the quilt without `build/` and `refs/pdf/`; upload to a new Overleaf project; set `drafts/main.tex` as the main document; compile.
3. Download the PDF; compare `pdftotext` with the local one; equal modulo whitespace is a pass.
4. Record the Overleaf TeX Live version and the result in the release notes.

## 14.6 Tests by chapter

Names are `test_<area>_<case>`. Each is one assertion set; where a test needs LaTeX it is marked (tex).

### Chapter 4: the quilt

- `test_quilt_discovery_walks_up`, `test_quilt_discovery_fails_outside`, `test_quilt_config_unknown_key_warns`, `test_quilt_config_missing_main_errors`
- `test_userconfig_author_resolution_order` (flag, user config, git, error with exact message)
- `test_init_creates_layout`, `test_init_refuses_in_quilt`, `test_init_refuses_nonempty_without_from`, `test_init_demo_writes_demo`, `test_init_git_init_unless_no_git`
- `test_loomsty_three_macros_only`, `test_loomsty_providecommand`, `test_nest_shifts_levels` (tex), `test_nest_composes` (tex)
- `test_ignore_directive_excludes_file`, `test_build_dir_deletable_and_regenerated`
- `test_never_modifies_author_files` (a property test: every command run on every fixture; author files' hashes unchanged afterwards)

### Chapter 5: the source contract

- Scanning: `test_scan_all_tex_recursively`, `test_scan_skips_build`, `test_scan_masters_only_in_drafts`, `test_scan_documentclass_outside_drafts_info`
- Nodes: `test_env_node_with_id`, `test_env_node_without_id_qualified_key`, `test_env_line_anchoring_error`, `test_env_spans_files_error`, `test_env_nested_lemma_in_proof`, `test_section_node_levels`, `test_section_label_next_line`
- Ids: `test_id_grammar_loomlocal`, `test_id_grammar_paperlocal_by_citekey`, `test_id_hyphenated_human_label_is_alias`, `test_alloc_next_base36`, `test_alloc_sees_ledger_annotations_references`, `test_alloc_reuses_untouched_id`, `test_alloc_never_reuses_referenced_id`, `test_alloc_per_prefix`, `test_duplicate_id_error_both_locations`
- Taxa: `test_taxa_newtheorem_forms`, `test_taxa_declaretheorem`, `test_taxa_style_class_default_plain`, `test_taxa_unknown_environment_error_and_directive_fix`, `test_taxa_conflict_between_masters_warning`, `test_missing_proof_warning_plain_only`, `test_external_node_by_cite_in_title`
- Proofs: `test_proof_adjacent`, `test_proof_by_reference_anywhere`, `test_proof_unattached_error`, `test_proof_multi_target_warning`, `test_proof_positional_keys_order`, `test_proof_labelled_is_node`, `test_proof_positional_key_info`
- Edges: `test_edge_ref_family`, `test_edge_uses`, `test_edge_alias_resolves`, `test_edge_classification_statement_proof_prose`, `test_edge_closure_definition`, `test_edge_dangling_error`, `test_edge_reference_to_loose`, `test_uses_missing_and_unused_info`, `test_equation_in_proof_referenced_warning`
- Regions: `test_region_equation_qualified_key`, `test_region_duplicate_label_error`, `test_region_prose_equation_belongs_to_master`
- Inclusion: `test_inclusion_input_include_nest`, `test_inclusion_regions_on_expanded_master`, `test_inclusion_subsection_after_input_belongs_to_file_section`, `test_inclusion_ownership_every_char_once`, `test_inclusion_double_error`, `test_inclusion_cycle_error_continues`, `test_inclusion_missing_error`, `test_inclusion_two_masters_ok`, `test_reached_by_and_loose`, `test_tex_root_hint_recorded`
- Numbering: `test_aux_read_plain_and_hyperref` (tex), `test_numbers_per_master` (tex), `test_numbers_absent_before_compile`
- Directives: `test_directive_three_forms`, `test_directive_scope_file_node_region`, `test_directive_list_values_commas`, `test_directive_unknown_warning`, `test_directive_never_changes_pdf` (tex: compile with and without directives, identical)
- Macros: `test_uses_no_output` (tex), `test_incomplete_overrides_state`, `test_macros_unloaded_error`, `test_macro_shadowed_warning`
- Hashing: `test_normalize_comments_whitespace`, `test_normalize_keeps_directives`, `test_preamble_closure_hash_includes_fragments`
- Examples: `test_example_single_file_paper` (5.15.1 verbatim), `test_example_two_proofs` (5.15.4)

### Chapter 6: bringing a paper in

- `test_import_closure_resolution`, `test_import_preserves_layout_moves_master`, `test_import_inserts_usepackage_loom`, `test_import_inserts_labels_before_existing`, `test_import_shows_diff_and_asks`, `test_import_refuses_line_anchoring`, `test_import_outside_tree_warning`, `test_import_sets_main`, `test_import_identity` (tex)
- `test_id_prints_patch`, `test_id_to_writes_copy`, `test_id_sections_default_levels`
- `test_atomize_requires_dest_exact_message`, `test_atomize_positional_and_to_equivalent`, `test_atomize_moves_node_with_adjacent_proof`, `test_atomize_deferred_proof_file_no_label`, `test_atomize_proofs_separate`, `test_atomize_sections`, `test_atomize_directives_travel`, `test_atomize_refuses_target_exists`, `test_atomize_no_ids_allocated`, `test_atomize_identity` (tex), `test_atomize_all_to_dir`
- `test_inline_reverses_atomize`, `test_inline_nest_shifts` (tex), `test_inline_identity` (tex)
- `test_identity_reports_first_diff` (tex), `test_identity_label_numbers_compared` (tex)
- Paper tier: `test_paper_manolache_import`, `test_paper_manolache_atomize_sections`, `test_paper_manolache_digest_extract`, `test_paper_acgs_import_with_documented_edits`, `test_paper_acgs_scan_time_and_memory`

### Chapter 7: review

- `test_ledger_append_only`, `test_ledger_latest_row_wins`, `test_ledger_refuses_without_author_exact_message`, `test_snapshots_content_addressed_never_overwritten`
- `test_accept_writes_closure_hashes`, `test_accept_proofs_flag`, `test_accept_stale_flag_lists_and_asks`, `test_accept_refuses_incomplete`, `test_accept_refuses_uncompiled_without_force`
- `test_comment_quote_must_be_unique`, `test_comment_quote_not_found_exit_1`, `test_comment_prefix_suffix_extracted`, `test_comment_run_author_and_log`, `test_comment_person_daily_file`, `test_comment_reply_and_resolve`, `test_comment_batch_stops_at_first_failure`, `test_comment_target_hash_recorded`, `test_comment_refuses_cross_node_quote`
- `test_selector_resolution_unique`, `test_selector_resolution_by_context`, `test_selector_detached_after_edit`, `test_selector_survives_atomize`
- `test_state_draft_accepted_stale_incomplete`, `test_stale_causes_each_kind`, `test_stale_diff_from_snapshot`, `test_derived_proved_settled`, `test_review_facts_counts_exclude_discarded`
- `test_status_filters`, `test_status_explain`, `test_status_json_shape`, `test_status_never_fails`
- `test_discard_flag_hides_everywhere`, `test_discard_undo`, `test_discard_by_before_author_target`
- `test_deletion_unravel_report`, `test_delete_refuses_exact_message`, `test_retired_key_info_and_status_retired`, `test_dependency_removed_cause`, `test_merge_by_alias`
- `test_positional_key_recovery_by_hash`
- `test_timeline_7_11` (the worked timeline as one scenario)

### Chapter 8: digests

- `test_digest_header_directives_required`, `test_digest_nodes_external_by_cite_title`, `test_digest_ids_prefixed_labels_prefixed`, `test_digest_setup_node`, `test_digest_uses_internal`
- `test_macro_block_group_at_extraction` (tex), `test_macro_block_let_undefined_collision` (tex), `test_macro_block_declaremathoperator_rewritten`, `test_requires_missing_package_warning`
- `test_postnote_normalization_table`, `test_postnote_match_and_edge`, `test_postnote_unmatched_warning`, `test_postnote_multiple_results`, `test_cite_without_postnote_no_edge`
- `test_version_mismatch_warning`, `test_undigested_listed`
- `test_extract_from_source` (tex), `test_extract_counter_emulation_when_compile_fails`, `test_extract_refuses_existing`, `test_extract_drops_proofs_keeps_uses`
- `test_fetch_refused_without_config`, `test_fetch_writes_gitignored_dirs` (network; skipped in CI)
- `test_import_digest_as_rewrites_prefix`, `test_import_digest_remaps_environments`
- `test_bundle_includes_digest_statement_grouped` (tex)

### Chapter 9: build and interface

- `test_build_layout`, `test_build_atomic_publish_interrupted`, `test_build_incremental_by_hash`, `test_build_exit_1_on_errors_still_publishes`
- `test_fragment_node_master_digest_kinds`, `test_fragment_no_shell_no_scripts`, `test_fragment_data_src_on_blocks`
- Converter: one test per construct in 9.4.1 (`test_convert_sectioning`, `test_convert_emph_lists_footnotes`, `test_convert_math_inline_display_labels`, `test_convert_env_and_proof`, `test_convert_refs_cites`, `test_convert_includegraphics` (tex), `test_convert_tikzcd_svg` (tex), `test_convert_table_simple`, `test_convert_text_macros_expanded`), `test_convert_fallback_per_block` (tex), `test_convert_nothing_dropped`
- `test_marks_placed_in_node_and_master`, `test_marks_block_level_when_markup_crossed`
- `test_manifest_conforms_to_spec` (schema when it exists; structural checks until then), `test_manifest_diagnostics_reserved_and_namespaced`, `test_manifest_states_declared`
- `test_bundle_contents_and_order`, `test_bundle_compiles` (tex), `test_bundle_failed_diagnostic` (tex), `test_bundle_with_diff_does_not_touch_quilt`, `test_bundle_with_bad_diff_exit_1`, `test_bundle_draft_unpromoted_node` (tex)
- `test_serve_republishes_on_change`, `test_serve_static_routes`, `test_serve_no_notification_sent`
- `test_fixture_matches_vendored`

### Chapter 10: arras (in the arras repository)

- Unit: `manifest_client_loads_and_hashes`, `unknown_state_renders_generic`, `unknown_code_renders_generic`, `version_mismatch_shows_only_diagnostic`, `badge_composition_rules`, `selector_from_selection` (for the deferred write API; skipped)
- End-to-end on the fixture: every route renders (`node`, `master`, `digest`, `review`, `problems`, `blockers`, `graph`, `threads`, `thread`, `tags`, `taxa`, `references`, `loose`, home); every diagnostic code appears on `/problems`; marks and boxes on the annotated node; discarded hidden by default; live reload on manifest change only; search finds by id, alias, title, tag
- Prerender: every route present in the static build; no external requests; works offline
- Guard: `no_forbidden_words_in_source` (the words of 10.8 absent from `src/`)

### Chapter 11: the AI layer

- `test_ai_init_layout_and_vendor_files`, `test_ai_init_permissions_generated`, `test_ai_init_skills_generated_pointer_only` (every stub names its mode file and contains no block definitions), `test_ai_init_gitignore_line`, `test_upgrade_preserves_edited_modes` (an edited mode file is untouched and a `.new` is written), `test_orient_static_plus_live`, `test_orient_run_includes_thread_and_log`
- `test_run_start_creates_dir_and_toml`, `test_run_log_appended_by_run_flag`, `test_run_launch_agent_if_configured` (with a fake agent command)
- `test_promote_draft_allocates_or_checks_id`, `test_promote_digest_refuses_existing`, `test_promote_never_touches_run_file`
- `test_ai_check_reports_outside_writes`
- `test_modes_templates_present_and_contracts_listed`
- Manual: the example session with Claude Code and with Codex on the demo quilt; recorded per release.

### Chapter 12: CLI

- `test_cli_exit_codes_contract`, `test_cli_json_single_document`, `test_cli_help_generated_matches_reference`, `test_cli_aliases_unravel`, `test_cli_withdrawn_commands_absent`

## 14.7 Coverage rule

**[decided]** Every test named here exists, and every diagnostic code in `specs/diagnostics.md` is emitted by at least one test on one fixture. A release with a missing test or an unemitted code fails the checklist.

## Open questions

- Whether the paper tier should run in a private CI with the sources stored as secrets. **[assumed]** No; local only, as decided.
- Whether Playwright should also run against a live `loom serve` rather than the vendored fixture. **[assumed]** One integration test in the loom repository does this on the demo quilt, with arras installed from its pip package.
