# 14. Tests

This chapter lists the tests the MVP passes. It defines the tiers, the shim that makes the fast tier possible, the fixtures, the CI jobs, the Overleaf procedure, and then the tests themselves, grouped by chapter of the specification they verify. The names in 14.6 are the test functions as they exist in the repositories at the end of M7 (collected with `pytest --collect-only` in loom and read from the spec files in arras), so that coverage of this chapter can be checked mechanically; where the book's original list named a test that was not written, or was folded into another, the chapter says so.

## 14.1 Tiers

**[decided]**

- Unit tier: `tests/unit/`, everything that needs no real LaTeX, run against the fake toolchain of 14.2; 213 tests after the 0.3 round (183 at M7). `uv run pytest tests/unit`, or in CI `uv run pytest -m "not tex and not paper and not network"`. Runs on every push.
- TeX tier: `tests/tex/`, marked `tex`: bundles and the demo master compiled with the real toolchain, the reshape identity tests, the vendored fixture rebuilt and compared, and two smoke tests of `latexmk` and `pdftotext`; 12 tests after the 0.3 round (10 at M7). `conftest.py` gives these tests the real `latexmk` and `pdftotext` directories on `PATH` and skips them when no `latexmk` is installed; HOME and every TeX tree still point at empty directories. Runs in a TeX Live container on every push.
- Paper tier: `tests/papers/`, the Manolache and ACGS fixtures; 4 tests. The module is marked both `paper` and `tex`, so its tests run only with the real toolchain and only when `LOOM_PAPER_FIXTURES` names a directory holding `0805.2065/` and `1709.09864/`; skipped otherwise, and never in CI.
- Network: one test, `test_fetch_writes_gitignored_dirs`, marked `network` and skipped unless `LOOM_NETWORK=1`; excluded from CI.
- Manual tier: the Overleaf procedure and the agent sessions. Run per release; results recorded in the release notes. The Claude Code session was performed at M6 on the demo quilt and at M7 as the referee runs of the relloc migration; the Overleaf procedure and the Codex session have not been performed (`docs/demonstrations/M7.md`).
- Arras tiers: unit (vitest, 20 tests: the specs beside the modules under `src/lib/` and the guard in `tests/unit/`); end-to-end (Playwright, 43 tests, on the vendored fixture, which `scripts/stage-fixture.mjs` copies into `static/build/` so `vite preview` serves it where `loom serve` would); screenshots (`npm run shots`, one run that writes the book's reference figures from the same fixture, 15.9); prerender (`npm run build:prerender` writes the static site of the fixture, 50 routes at M2, but no test checks it and CI does not run it).

## 14.2 The fake `latex`

**[decided]** One script, `tests/fake_latex/fake_tex.py`, which `conftest.py` copies into a temporary directory under the names `latexmk`, `pdflatex`, `latex`, `lualatex`, `xelatex`, `dvisvgm`, `bibtex`, `biber`, `pdftotext`, `pdfinfo`, `kpsewhich`, and `pdftocairo`, and prepends to the test `PATH`. It parses the input enough to find `\newtheorem` declarations, sectioning, theorem-like environments, equations, and `\label`s through expanded `\input`, `\include`, and `\nest` (shifting levels under `\nest` as `loom.sty` does), emits a plausible `.aux` with sequential numbering by section, writes a placeholder PDF carrying the document's plain text so the fake `pdftotext` returns it, emits a fixed SVG for any `dvisvgm` call, and answers `kpsewhich` for a fixed list of system files. Every invocation is appended to the file `FAKE_TEX_LOG` names. `FAKE_TEX_FAIL=1` makes every engine call fail with a `! LaTeX Error` line and exit 12; `FAKE_TEX_FAIL_MATCH=<substring>` fails only the inputs whose path contains the substring, so a test can have the master compile while every bundle fails (`bundles/`). The shim is never found on the real `PATH`: it exists only in the per-session directory the fixture creates, and tests marked `tex` get the real toolchain instead. The shim is itself tested: `test_fake_latex_emits_aux`, `test_fake_pdftotext_round_trip`, `test_fake_latex_failure_injection`, `test_fake_dvisvgm_and_kpsewhich`.

## 14.3 Fixtures

**[decided]**

- `tests/quilts/demo/`: the quilt `loom init --demo` writes, asserted byte-equal to it by `test_init_demo_matches_fixture`; small; every command runs on it in well under a second on the shim.
- `tests/quilts/synthetic/`: the quilt described in `specs/fixture.md` §1; exercises every construct in the source contract and every diagnostic code the scanner emits on a quilt; the conformance fixture is generated from it.
- `tests/quilts/edge/`: eight small quilts each isolating one hard case: `spanning-env` (an environment spanning files), `begin-not-alone` (a `\begin` not alone on its line), `cycle`, `double-inclusion`, `nested-nest` (a `\nest` inside a `\nest`), `macro-collision` (a digest with a nonempty macro block whose name collides with the quilt's), `taxon-conflict` (two masters declaring one environment differently), `beamer-talk` (a beamer master).
- Every quilt above carries an `EXPECTED-LINT.txt`, the frozen `loom lint` output, which `test_lint_fixture_expected_codes` checks; `test_all_emitted_codes_are_known` checks that every code in those files is in loom's diagnostics table.
- `tests/fixture/`: the vendored conformance snapshot (`manifest.json`, `fragments/`, `svg/`, `diffs/`, `VERSION`), refreshed by `docs/specs/tools/refresh-fixture.sh` in the workspace.
- `tests/fixtures/` in the workspace: the paper sources, uncommitted, with `NOTES.md` and `VERSIONS`.

## 14.4 CI

**[decided]** Two workflows in `loom/.github/workflows/`, both on every push and pull request. `unit.yml` has a `unit` job over a Python matrix of 3.11, 3.12, and 3.13 (`uv sync`, `ruff check`, `ruff format --check`, `mypy`, `pytest -m "not tex and not paper and not network"`) and an `install-from-clone` job that runs `pipx install .` on a bare runner, then `loom --version`, and checks that `loom doctor` exits 2 there because no TeX is installed. `tex.yml` runs the TeX tier in the `texlive/texlive:latest` container with poppler installed (`uv run pytest -m tex`). One workflow in `arras/.github/workflows/ci.yml`: Node 22, `npm ci`, `svelte-check`, vitest, `npm run build`, Playwright on Chromium over the fixture, and the built `build/` uploaded as the `bundle` artefact of every commit. Not built: an Overleaf proxy job (compiling the demo and synthetic masters from the root with an empty environment), a publish job on tags, a prerender job, and a workspace workflow running the dialect validator; the validator runs inside `refresh-fixture.sh` and in loom's `test_fragment_kinds_and_dialect_validity` instead, and the workspace repository has no workflows.

## 14.5 The Overleaf procedure

**[decided]** Manual, per release; not yet performed (`docs/demonstrations/M7.md`, "Blocked on the user"):

1. `loom init demo --demo`; `loom compile`; record `pdftotext` of the local PDF.
2. Zip the quilt without `build/`, `refs/pdf/`, and `refs/src/`; upload to a new Overleaf project; set `drafts/main.tex` as the main document; compile.
3. Download the PDF; compare `pdftotext` with the local one; equal modulo whitespace is a pass.
4. Record the Overleaf TeX Live version and the result in the release notes.

## 14.6 Tests by chapter

Names are the test functions as written. Unmarked tests are unit tier on the shim; (tex) marks `tests/tex/`, (paper) marks `tests/papers/` (whose tests are also (tex)). Several planned tests were written as one function; the grouping below keeps the book's headings and lists the function that covers each.

### Chapter 4: the quilt

- Discovery and config: `test_quilt_discovery_walks_up`, `test_quilt_discovery_fails_outside`, `test_quilt_discovery_env_override`, `test_quilt_config_unknown_key_warns`
- Author: `test_userconfig_author_resolution_order` (flag, user config, git, error with exact message)
- Init and new: `test_init_creates_layout`, `test_init_refuses_in_quilt_and_nonempty`, `test_init_demo_writes_demo_and_lints_clean`, `test_init_writes_gitignore_always_and_a_repository_only_when_asked` (DR-105), `test_init_from_leaves_nothing_behind_when_the_import_fails` and `test_init_from_inside_a_paper_directory_keeps_the_paper_when_the_import_fails` (DR-106), `test_init_demo_matches_fixture`, `test_new_allocates_and_print`, `test_demo_ships_two_accepted_one_stale_and_a_finished_run`
- `\nest`: `test_nested_nest_levels` (the scanner's levels under a nested `\nest`), `test_assemble_flattens_with_nest_shift`, `test_inline_nest_shifts` (tex), `test_real_latexmk_compiles_minimal_document` (tex)
- Ignore and build directory: `test_ignore_directive_and_lines`, `test_build_dir_deletable_and_regenerated`
- Author files: `test_never_modifies_author_files`, parametrised over the ten fixture quilts: every command run on each, author files' hashes unchanged afterwards
- The fake toolchain of 14.2: `test_fake_latex_emits_aux`, `test_fake_pdftotext_round_trip`, `test_fake_latex_failure_injection`, `test_fake_dvisvgm_and_kpsewhich`

Not written: `test_quilt_config_missing_main_errors` (the condition became the warning `loom:main-not-found`, DR-52, which no test asserts); `test_loomsty_three_macros_only` and `test_loomsty_providecommand` (the package is loaded by every TeX-tier compile but no test reads it); `test_nest_composes` as its own compile (the `nested-nest` quilt covers the scanner side).

### Chapter 5: the source contract

- Files and comments: `test_scan_all_tex_recursively_skips_build`, `test_non_utf8_source_decoded` (DR-47), `test_blank_comments_preserves_offsets` (DR-48), `test_body_start_skips_preamble_definitions`
- Tokenizer: `test_tokenize_basic_forms`, `test_tokenize_begin_end_and_verbatim`, `test_tokenize_verb_command`, `test_match_group_crosses_newlines_and_escapes`, `test_read_optional_not_across_blank_line`, `test_read_args_spec`, `test_env_tree_nesting_and_problems`
- Nodes: `test_env_node_without_id_qualified_key_and_regions`, `test_env_body_on_begin_line_and_one_line_env` (DR-40; in place of the planned `test_env_line_anchoring_error`, since the scanner reads such environments and only `import` and `atomize` refuse them), `test_env_spans_files_problem`, `test_statement_nested_in_proof`, `test_statement_nested_in_proof_and_enclosure_keys` (DR-41), `test_section_label_not_stolen_and_same_line` (DR-43), `test_duplicate_id_and_label_errors`, `test_begin_not_alone_tolerated`
- Ids and allocation: `test_id_grammar_loomlocal_and_paperlocal`, `test_alloc_next_base36`, `test_alloc_sees_references_and_never_reuses`, `test_citekey_slug` (DR-45)
- Taxa: `test_taxa_newtheorem_forms`, `test_taxa_declaretheorem_and_directive`, `test_taxa_transitive_sty_chain` (DR-46), `test_taxa_display_name_macro`, `test_taxa_conflict_between_masters`, `test_missing_proof_external_unexpected_unknown_env` (DR-53), `test_external_node_by_leading_cite` (DR-42), `test_external_node_and_digest_file`
- Proofs: `test_proof_adjacent_and_second_adjacent`, `test_proof_by_reference_anywhere`, `test_proof_unattached_after_prose`, `test_proof_by_enclosure` (DR-41), `test_example_two_proofs_and_positional_keys`
- Edges: `test_edge_family_alias_classification_closure`, `test_edge_dangling_loose_and_uses_lints`, `test_labels_with_spaces_commas_and_wrapped_refs` (DR-50), `test_dependency_cycle_and_slug_collision`
- Inclusion: `test_inclusion_input_include_nest_and_span_map`, `test_inclusion_exact_extension_braceless_and_system` (DR-44; also the `missing-include` case), `test_inclusion_double_and_cycle`, `test_nested_nest_levels`
- Numbering: `test_aux_read_plain_and_hyperref` (on the shim's `.aux`), `test_compile_master_and_numbers_from_aux`, `test_demo_master_compiles_and_numbers` (tex)
- Directives: `test_directive_three_forms`, `test_directive_scope_file_level`, `test_directives_file_and_node_level`, `test_directives_macros_prefix_disable` (also `loom:unknown-directive`, `loom:macros-unloaded`, and `loom:macro-shadowed`)
- Macros: `test_macros_all_forms`, `test_macros_math_classification_and_mathjax`, `test_macros_later_definition_wins`
- Bibliography: `test_bib_entries_and_fields`
- Hashing: `test_normalize_comments_whitespace` (also checks that a directive line survives normalisation)
- Examples: `test_example_single_file_paper` (5.15.1 verbatim), `test_example_two_proofs_and_positional_keys` (5.15.4)
- Fixture quilts: `test_lint_fixture_expected_codes`, parametrised over the ten quilts against their `EXPECTED-LINT.txt` (this is where `loom:multi-target-proof`, `loom:equation-in-proof-referenced`, `unreachable`, and `loom:taxon-conflict` are asserted), `test_all_emitted_codes_are_known`, `test_synthetic_structure` (two masters, `reached_by`, loose nodes)
- Commands: `test_search_deps_unravel_delete`, `test_lint_exit_codes`, `test_documentclass_outside_drafts_and_bundle_failed`

Not written: `test_taxa_style_class_default_plain` (the default is asserted inside the taxa tests, not on its own); `test_proof_labelled_is_node`; `test_region_prose_equation_belongs_to_master`; `test_inclusion_subsection_after_input_belongs_to_file_section`; `test_inclusion_ownership_every_char_once` (DR-49 restated ownership per file; no test walks a file's characters); `test_tex_root_hint_recorded`; `test_numbers_absent_before_compile`; `test_directive_never_changes_pdf` (tex); `test_uses_no_output` (tex); `test_incomplete_overrides_state` as a scanner test (the state is tested in chapter 7); `test_preamble_closure_hash_includes_fragments` (the closure hash is asserted only through `test_accept_writes_closure_hashes_and_proofs_flag`); `test_alloc_reuses_untouched_id`; `test_alloc_per_prefix`; `test_id_hyphenated_human_label_is_alias` as its own test (aliases are asserted in the edge and example tests).

### Chapter 6: bringing a paper in

- Import: `test_import_closure_layout_labels_main_and_identity` (closure resolution, layout preserved and the master moved, `\usepackage{loom}` inserted, labels inserted before existing ones, `main` set, identity on the shim), `test_import_shows_diff_and_asks`, `test_import_refuses_line_anchoring_and_fix_anchoring` (DR-40), `test_anchoring_violation_reports_the_authors_line`, `test_fix_anchoring_unit`, `test_import_outside_tree_warning_and_in_place`, `test_import_identity` (tex)
- Id: `test_id_prints_patch_and_to_writes_copy` (DR-64)
- Atomize: `test_atomize_requires_dest_moves_nodes_and_identity` (the exact refusal message, positional and `--to` forms, a node with its adjacent proof, a deferred proof), `test_atomize_proofs_separate_directives_sections_and_all`, `test_atomize_sections_and_inline_round_trip`, `test_atomize_identity_and_inline_identity` (tex), `test_selector_survives_atomize`
- Inline: `test_inline_nest_shifts_and_identity_on_master` (DR-65), `test_inline_nest_shifts` (tex), `test_assemble_flattens_with_nest_shift`
- Identity: `test_identity_reports_first_diff_and_label_numbers` (tex)
- Paper tier (paper): `test_paper_manolache_import`, `test_paper_manolache_atomize_sections`, `test_paper_acgs_import_with_documented_edits` (its hand-edit list is empty), `test_paper_acgs_scan_time_and_memory`

Not written: `test_id_sections_default_levels`; `test_atomize_refuses_target_exists` (`loom:atomize-target-exists` has no test); `test_atomize_no_ids_allocated`; `test_paper_manolache_digest_extract` (the extraction on Manolache is the M5 demonstration, not a test).

### Chapter 7: review

- Ledger and snapshots: `test_ledger_append_only_and_latest_row_wins`, `test_ledger_refuses_without_author_exact_message`, `test_snapshots_content_addressed_never_overwritten`
- Accept: `test_accept_writes_closure_hashes_and_proofs_flag`, `test_stale_diff_from_snapshot_and_accept_stale`, `test_accept_refuses_incomplete_and_uncompiled`
- Comment: `test_comment_quote_rules_and_records` (unique quote, quote not found exits 1, prefix and suffix, the person's daily file), `test_comment_run_author_log_reply_resolve_batch`
- Selectors: `test_selector_resolution_unique_by_context_and_detached`, `test_selector_survives_atomize`
- States: `test_state_draft_accepted_stale_incomplete_and_causes`, `test_derived_proved_settled` (DR-59)
- Status: `test_status_filters_and_never_fails` (also the `--json` shape)
- Discard: `test_discard_flag_hides_everywhere_and_undo`
- Deletion and retired keys: `test_retired_key_dependency_removed_merge_by_alias`, `test_search_deps_unravel_delete` (the unravel report and the refusal of `delete`)
- `test_positional_key_recovery_by_hash`
- `test_timeline_7_11` (the worked timeline as one scenario, including `status --explain`); `test_demo_ships_two_accepted_one_stale_and_a_finished_run`

Not written: `test_comment_target_hash_recorded`; `test_comment_refuses_cross_node_quote`; `test_review_facts_counts_exclude_discarded` as its own test (the counts are asserted inside the discard test); `test_discard_by_before_author_target`; `test_status_explain` as its own test.

### Chapter 8: digests

- Digest files: `test_external_node_and_digest_file` (header directives, external nodes, prefixed ids and labels), `test_citekey_slug`, the `macro-collision` quilt through `test_lint_fixture_expected_codes[macro-collision]`
- Postnotes: `test_postnote_normalization_table`, `test_postnote_match_edge_unmatched_and_no_postnote` (a match is an edge, an unmatched postnote is the warning, a `\cite` without a postnote is neither, and an alias id names the result under another numbering, DR-75)
- Versions and packages: `test_version_mismatch_and_missing_package_and_undigested`, `test_requires_missing_package_named_first_on_bundle_failure`
- Extraction: `test_extract_from_source_drops_proofs_keeps_uses_and_refuses_existing` (on the shim: proofs dropped, `\uses` kept, macros expanded, the macro block written, refusal when the file exists), `test_extract_counter_emulation_when_compile_fails` (under `FAKE_TEX_FAIL`, DR-68)
- Fetch: `test_fetch_refused_without_config`, `test_fetch_writes_gitignored_dirs` (network)
- Import: `test_import_digest_as_rewrites_prefix`
- Bundles: `test_bundle_contents_and_order` (the digest statements a bundle carries, on the shim)
- Macros: `test_macros_all_forms` (including `\DeclareMathOperator` and `\let`)

Not written: `test_digest_setup_node`; `test_digest_uses_internal`; `test_macro_block_group_at_extraction` (tex) and `test_macro_block_let_undefined_collision` (tex) (the collision is covered by the `macro-collision` quilt on the shim only); `test_macro_block_declaremathoperator_rewritten`; `test_postnote_multiple_results`; `test_import_digest_remaps_environments`; `test_bundle_includes_digest_statement_grouped` (tex) and `test_extract_from_source` (tex) (the compile of a bundle with a digest statement inside it and the extraction with the real toolchain are the M5 and M7 demonstrations, not tests).

### Chapter 9: build and interface

- Build: `test_build_layout_and_manifest` (layout, manifest structure, states declared, macros), `test_build_atomic_publish_interrupted`, `test_build_incremental_by_hash`, `test_build_exit_1_on_errors_still_publishes`
- Fragments: `test_fragment_kinds_and_dialect_validity` (node, master, and digest kinds; every fragment passes the vendored dialect validator, which forbids scripts and shells and requires `data-src` on blocks)
- Converter: `test_convert_paragraphs_and_inline_markup`, `test_convert_math_inline_display_labels`, `test_convert_refs_cites_footnote_url`, `test_convert_lists_and_sectioning`, `test_convert_env_fallback_diagram_verbatim_table`, `test_convert_text_macros_expanded_and_math_macros_left`, `test_convert_nothing_dropped_unknown_command_falls_back`, `test_convert_children_and_inclusions_become_placeholders`, `test_convert_conditionals_definitions_starred_sections`
- Marks: `test_marks_placed_inline_and_block_level`
- Bundles: `test_bundle_contents_and_order`, `test_bundle_run_copy_and_log`, `test_bundle_with_diff_does_not_touch_quilt`, `test_bundle_with_bad_diff_exit_1`, `test_bundle_draft_unpromoted_node`, `test_bundle_compiles` (tex), `test_bundle_failed_diagnostic` (tex), `test_documentclass_outside_drafts_and_bundle_failed` (`loom:bundle-failed` from `loom check` under `FAKE_TEX_FAIL_MATCH`)
- Compile and check: `test_compile_master_and_numbers_from_aux`, `test_compile_failure_reports_first_error`, `test_check_lints_and_compiles`, `test_demo_master_compiles_and_numbers` (tex), `test_real_pdftotext_extracts_text` (tex)
- Serve: `test_serve_static_routes`, `test_serve_republishes_on_change`, `test_serve_no_notification_sent`, `test_serve_exit_2_without_bundle`, `test_serve_spa_fallback_for_dotted_routes` (DR-78)
- Fixture: `test_fixture_matches_vendored` (tex; the manifest structurally minus timestamps, the fragments textually with SVG bodies normalised; the only test that exercises `\includegraphics`, the tikz-cd route, and the per-block SVG fallback with the real toolchain)

Not written: `test_convert_includegraphics`, `test_convert_tikzcd_svg`, and `test_convert_fallback_per_block` as their own TeX-tier tests (covered through the vendored fixture as noted); `test_manifest_conforms_to_spec` against a schema (no `manifest.schema.json` exists; the structural checks live in `test_build_layout_and_manifest`); `test_manifest_diagnostics_reserved_and_namespaced` as its own test (`test_all_emitted_codes_are_known` checks every emitted code against the table).

### Chapter 10: arras (in the arras repository)

- Unit (vitest; `src/lib/manifest/loader.spec.ts`, `src/lib/badges.spec.ts`, `src/lib/diagnostics.spec.ts`, `tests/unit/forbidden-words.spec.ts`): manifest loader "hashes text deterministically", "accepts interface version 1", "rejects a version it does not accept with a single diagnostic", "rejects unreadable JSON"; badge composition "shows the state label and the stale modifier", "renders an unknown state label generically", "incomplete overrides everything", "combines statement, best proof, and derived labels"; diagnostics grouping "groups by code, errors first, and gives unknown codes the generic affordance"; boundary "src/ contains none of the forbidden words" (DR-39)
- End-to-end (Playwright on the vendored fixture; `tests/e2e/home.e2e.ts`, `tests/e2e/routes.e2e.ts`): "home page renders the fixture manifest"; "route <path> renders" for fifteen routes (`/node/sy-0003`, `/node/sy-0200`, `/master/main`, `/digest/Kre99`, `/review`, `/problems`, `/blockers`, `/graph`, `/threads`, `/tags`, `/tag/orbits`, `/taxa`, `/taxon/lemma`, `/references`, `/loose`); "node page shows the fragment with typeset math and its proofs"; "master view expands inclusions in place"; "problems page lists every diagnostic code"; "unknown state labels and codes render generically"; "interface version mismatch shows one diagnostic and nothing else"; "search finds by id, alias, title, and tag"; "live reload follows the manifest only"; "marks and boxes on the annotated node; discarded hidden by default"; "review panel shows stale causes with diff links and detached counts"; "digest page lists results with their citers, and the references index counts them"; "thread page shows the run's messages, attachments, and log"

Not written: `selector_from_selection` (the write API is deferred); the prerender tests (every route present in the static build, no external requests, works offline): `npm run build:prerender` was run by hand at M2 and the MathJax component was bundled in full at M7 so no request leaves the page, but no test checks either.

### Chapter 11: the AI layer

- `test_ai_init_layout_and_vendor_files`, `test_ai_init_gitignore_line`, `test_ai_init_permissions_generated` (DR-71), `test_ai_init_skills_generated_pointer_only` (every stub names its mode file and contains no block definitions), `test_modes_templates_present_and_contracts_listed`, `test_upgrade_preserves_edited_modes` (an edited mode file is untouched and a `.new` is written), `test_orient_static_plus_live`
- `test_run_start_creates_dir_and_toml_and_orient_run` (also `orient --run` with the thread and the log), `test_run_log_appended_by_run_flag`, `test_run_launch_agent_if_configured` (with a fake agent command, and the refusal when it is not on `PATH`; DR-72), `test_bundle_run_copy_and_log`
- `test_promote_draft_allocates_or_checks_id`, `test_promote_digest_refuses_existing`
- `test_ai_check_reports_outside_writes`
- `test_threads_from_runs_in_manifest_and_runs_not_scanned` (DR-70)
- Manual: the Claude Code session was performed on the demo quilt at M6 and as the referee runs of the relloc migration at M7; the Codex session has not been performed (`docs/demonstrations/M6.md`).

Not written: `test_promote_never_touches_run_file`.

### Chapter 12: CLI

- `test_cli_version`, `test_doctor_ok_on_shim`, `test_doctor_json_shape`, `test_doctor_missing_tool_exit_2`, `test_cli_reference_matches_checked_in` (the checked-in `docs/cli-reference.md` equals what `scripts/gen_cli_reference.py` generates from the command tree), `test_lint_exit_codes`, `test_search_json_still_single_document`, `test_serve_exit_2_without_bundle`

Not written: `test_cli_exit_codes_contract` as one test (exit codes 0, 1, and 2 are asserted per command throughout the suite); `test_cli_aliases_unravel`; `test_cli_withdrawn_commands_absent`.

### Chapter 16: the editor clients

**[decided]** The clients have their own suites in their own repositories; loom's checklist does not run them, and nothing in loom depends on them passing.

- `loom-lsp`: seventeen tests. The server is driven in process against a copy of the synthetic quilt — the published diagnostics match `loom lint --json`, a dangling reference is an error at the command rather than at the line, an unsaved buffer produces diagnostics the disk does not justify and closing it takes them away again, definitions resolve for a reference and an inclusion, references find every site, hover carries the state, the symbol tree nests proofs under their statements, completion offers ids, directive keys, taxa and citekeys in the right places, and a code action arrives as an edit for the missing `\uses` and as a confirmed command for the rest. Three tests cover the position encoding, over an astral character and a CRLF file. One drives the real binary over stdio, and one asserts that the transport flag clients append is accepted.
- `loom-nvim`: seventeen busted tests under plenary, over root detection, the key under the cursor, every command's argument vector, and the client configuration. They start nothing: the browser opener is injected and no loom process runs. Two scripts drive the real server against a real quilt, one printing the diagnostics after `LspAttach` and one asking for a hover and a definition.
- `loom-vscode`: twenty tests across two integration passes in a real VS Code, one inside a copy of the synthetic quilt where the client must reach *running* and one in a plain LaTeX folder where no client may start.

## 14.7 Coverage rule

**[decided]** Every test named in 14.6 exists, and every diagnostic code in `specs/diagnostics.md` is emitted by at least one test on one fixture. A release with a missing test or an unemitted code fails the checklist.

The check made for this revision, on 2026-09-16, with the collected test ids against the two code tables: the 48 codes of `docs/specs/diagnostics.md` and the 48 codes of `loom/src/loom/scan/diagnostics.py` are the same set; 47 of them are emitted somewhere in loom's source, and the forty-seventh, `loom:interface-version`, is emitted by arras (`src/lib/manifest/loader.ts`) as the specification says and is tested by its loader spec; `test_all_emitted_codes_are_known` keeps every code the fixture quilts emit inside the table. Five codes gained their first test during M7: `loom:documentclass-outside-drafts` and `loom:bundle-failed` in `test_documentclass_outside_drafts_and_bundle_failed`; `loom:atomize-target-exists`, `loom:foreign-annotations`, `loom:main-not-found`, and the new `loom:unknown-config-key` in `test_remaining_codes_have_a_test`; and `loom:non-utf8-source` in `test_non_utf8_source_code_reported`, so every code in the table is asserted by a test and the rule above holds; 14.6 names the tests that were planned and not written.

## Open questions

- Whether the paper tier should run in a private CI with the sources stored as secrets. **[decided]** No; local only: `unit.yml` deselects `paper` and `network`, and the paper tier ran with `LOOM_PAPER_FIXTURES` on the implementing machine (`docs/demonstrations/M4.md`).
- Whether Playwright should also run against a live `loom serve` rather than the vendored fixture. **[decided]** Not as a test. `test_serve_static_routes` serves the vendored bundle without a browser, and criterion 8 of M7 visited every page kind of the served relloc quilt in a headless browser by hand (`docs/demonstrations/M7.md`); arras reaches loom as the vendored bundle, not through the pip package.
