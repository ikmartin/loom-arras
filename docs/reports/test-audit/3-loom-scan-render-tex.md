# S3 · loom scan, render and TeX tests

Slice: `loom/tests/unit/scan/` (15 files + `helpers.py` + `fixtures/zk_proof_after_remark.tex`), `loom/tests/unit/render/` (7 files), `tests/unit/test_tex_layer.py`, `tests/unit/test_fake_latex.py`, `tests/tex/` (5 files), `tests/papers/test_papers.py`, `tests/fake_latex/fake_tex.py`, `tests/tools/validate_dialect.py`, `tests/fixture/`. **191 test functions, none parametrized.** Tiers: 171 unit (shim), 14 tex, 6 paper (marked `paper` and `tex`).

Every test runs under the autouse `isolated_env` (conftest.py): temporary HOME and XDG config, every `TEXMF*` tree an empty directory, git config off, agent markers unset, and PATH = the fake shim + `/usr/bin:/bin` (unit) or the real TeX bin dir + poppler's dir + `/usr/bin:/bin` (`tex`, skipped when there is no `latexmk`). The "assumes" column states only what goes beyond that.

Abbreviations: **mq** = `helpers.make_quilt` (writes `config.toml` with prefix `ab` plus the given files, then scans); **P** = `helpers.PREAMBLE`; **demo** = `loom init --demo` in tmp; **syn** = copy of `tests/quilts/synthetic`; **imp** = `init --from` of an inline paper then `draft` (prefix `pp`); **CLI** = click `CliRunner` with `os.chdir`; **shim** = the fake toolchain; **TeX** = real toolchain.

Measured anchors used for cost estimates below: the other job's full run (`scratchpad/audit/loom-pytest.txt`, `--durations=60`), plus my own timings outside pytest: on the shim `init --demo` 0.16 s, demo build cold 0.48 s / warm 0.20 s, synthetic build cold 1.26 s; with real TeX demo master compile 2.15 s, one bundle 0.86 s, synthetic `main` 2.97 s + `talk` 2.19 s, synthetic build 3.16 s.

## Inventory

| file::test | tier | tests | assumes | asserts |
|---|---|---|---|---|
| scan/test_basis.py::test_drafting_scan_classifies_five_bases_and_flags_uncertainty | unit | basis classification of nine blocks, then `accept` refusals | mq + bib; CLI `accept` | exact basis map; external flags; needs-classification only on ab-0006; misplaced-basis; bulk and per-key refusals; no state.toml |
| scan/test_basis.py::test_basis_controls_settlement_not_theorem_style | unit | `settled` follows basis; basis change stales a key | mq; `write_acceptance`; Records | settled for def/hypothesis/lemma/remark, not conjecture; rescan gives basis-changed cause |
| scan/test_basis.py::test_section_reference_is_context_not_a_settlement_obligation | unit | a section `\ref` is closure context, not a settlement dependency | mq; write_acceptance | ab-0001 in closure; exact proved/settled dict for four keys |
| scan/test_basis.py::test_accept_all_live_refuses_to_establish_an_open_claim | unit | `accept --all-live` refuses a conjecture | mq; CLI | exit ≠ 0 with "open claims cannot be accepted"; no state.toml |
| scan/test_basis.py::test_zk_proof_after_explanatory_remark_belongs_to_proposition | unit | proof after an explanatory remark attaches to the proposition (mZK regression) | fixtures/zk_proof_after_remark.tex; plan_atomize; acceptance | bases, proofs, edge, no missing-proof/needs-classification, atomize refusal text, derived before/after |
| scan/test_basis.py::test_inline_argument_in_remark_is_one_local_proof_acceptance | unit | remark with `basis: local-proof` carries its own proof | mq; write_acceptance twice | inline_proof, no proof keys, edge; proved-not-settled, then settled |
| scan/test_basis.py::test_proof_after_remark_needs_a_preceding_claim_or_explicit_reference | unit | proof after a bare remark is unattached; explicit ref wins | mq | ab-0001 no proofs; ab-0002 proof; unattached-proof diagnostic |
| scan/test_basis.py::test_legacy_definition_directive_maps_to_expository | unit | legacy `basis: definition` alias | mq | basis expository; "legacy" in reason |
| scan/test_bib.py::test_bib_entries_and_fields | unit | parse_bib: @comment, @string, parens, key with space | none | key set; fields; eprint and version; inner braces kept |
| scan/test_bib.py::test_citekey_slug | unit | citekey_slug | none | three exact slugs |
| scan/test_bib.py::test_the_quilts_bibliography_is_the_only_bib_read | unit | only `digests/bibliography.bib` is read | mq with three .bib files | `result.bib` keys == {Owned} |
| scan/test_conflicts.py::test_two_files_defining_one_id_leave_it_conflicted | unit | two masters define one id: conflict node | mq two masters | kind, files, no text, demoted keys, duplicate-id message/locations/three fixes, no unlabelled or duplicate-label |
| scan/test_conflicts.py::test_a_node_file_and_an_inline_copy_conflict | unit | node file + inline copy conflict | mq | conflict files; one duplicate-id |
| scan/test_conflicts.py::test_two_masters_sharing_one_node_file_is_not_a_conflict | unit | shared `\input` is not a conflict | mq | kind environment; reached_by both; no duplicate-id |
| scan/test_conflicts.py::test_a_proof_attaches_to_its_own_file_s_copy | unit | proof attaches to its own file's demoted copy | mq | one proof; `of` is main.tex#lemma:1; conflict node proofs [] |
| scan/test_conflicts.py::test_a_conflicted_id_is_still_a_reference_target | unit | refs to a conflicted id resolve | mq | no dangling-link; one edge ab-0002→ab-0001 |
| scan/test_conflicts.py::test_two_copies_in_one_file_keep_todays_message | unit | same-file duplicate keeps the plain message | mq | exact message; no fixes; kind environment |
| scan/test_directives.py::test_directive_three_forms | unit | bare, kv, begin/end, `% !TEX`, unknown key | one tmp file | form tuples; list_value; `src.ignored` |
| scan/test_directives.py::test_directive_scope_file_level | unit | file-level scope ends at first node | tmp file | only `author` is file-level |
| scan/test_edges_lint.py::test_edge_family_alias_classification_closure | unit | edges, graph direct/closure/downstream, cites, lints on SINGLE_FILE | mq + bib | edge tuples; graph lists; cite tuple; exact sorted lint-code list |
| scan/test_edges_lint.py::test_edge_dangling_loose_and_uses_lints | unit | dangling, loose, unreachable, uses and equation-in-proof lints | mq + loose node file | codes present, counts; eq edge target and kind |
| scan/test_edges_lint.py::test_missing_proof_external_unexpected_unknown_env | unit | missing-proof, needs-classification, unknown env, external | mq | code counts/presence; ab-0002 external |
| scan/test_edges_lint.py::test_directives_macros_prefix_disable | unit | macros-unloaded, shadowed, unknown directive, prefix-is-citekey, `[lint] disable` | mq custom config | codes present/absent |
| scan/test_edges_lint.py::test_dependency_cycle_and_slug_collision | unit | dependency cycle; citekey slug collision | mq + bib | both codes present |
| scan/test_edges_lint.py::test_labels_with_spaces_commas_and_wrapped_refs | unit | labels with spaces/commas, refs across newline, `\cref` lists | mq | no dangling-link; label kept; no `#1`; edge targets |
| scan/test_envtree.py::test_proof_adjacent_and_second_adjacent | unit | two proofs after comments attach adjacent | tmp file | via adjacent; same statement |
| scan/test_envtree.py::test_proof_by_reference_anywhere | unit | proof optarg `\ref`/`\cref` attach | tmp | via ref; ref_labels [t,u]; statement None |
| scan/test_envtree.py::test_proof_unattached_after_prose | unit | prose breaks adjacency | tmp | via none |
| scan/test_envtree.py::test_proof_by_enclosure | unit | proof inside example | tmp | via enclosure; statement |
| scan/test_envtree.py::test_statement_nested_in_proof | unit | nested lemma+proof inside a proof; own ranges | tmp | both adjacent; parent; outer own text excludes inner |
| scan/test_envtree.py::test_env_body_on_begin_line_and_one_line_env | unit | one-line environments | tmp | env names; `labels_in` offset |
| scan/test_envtree.py::test_env_spans_files_problem | unit | unclosed env | tmp | problems == [unclosed lemma] |
| scan/test_envtree.py::test_external_node_by_leading_cite | unit | leading `\cite` detection | tmp | true/false; optarg text |
| scan/test_envtree.py::test_body_start_skips_preamble_definitions | unit | body_start skips `\newenvironment` bodies | tmp | one env, after `\begin{document}` |
| scan/test_expand.py::test_inclusion_input_include_nest_and_span_map | unit | expansion, segment map, locate, sections across files | tmp files | reached, inclusions, shifts, segment round trip, locate/exp_offset, section units and parents |
| scan/test_expand.py::test_inclusion_exact_extension_braceless_and_system | unit | system / opaque / missing inclusions | tmp; shim kpsewhich knows `xy.tex` | problem map; one missing-include; opaque text not expanded |
| scan/test_expand.py::test_inclusion_double_and_cycle | unit | double inclusion and cycle | tmp | two codes; A expanded once |
| scan/test_expand.py::test_section_label_not_stolen_and_same_line | unit | heading_labels | none | label list per heading |
| scan/test_expand.py::test_kpsewhich_is_probed_once_per_name | unit | kpsewhich memoisation | monkeypatched which/subprocess; cache_clear | five calls → one subprocess |
| scan/test_labels_hashing.py::test_id_grammar_loomlocal_and_paperlocal | unit | is_id_shaped / split_id | none | truth table |
| scan/test_labels_hashing.py::test_alloc_next_base36 | unit | next_local | none | four cases incl. overflow |
| scan/test_labels_hashing.py::test_normalize_comments_whitespace | unit | normalize and hash invariances | none | exact normalized text; hash equal/unequal |
| scan/test_macros.py::test_macros_all_forms | unit | parse_macros forms (`\def`, `\let`, NewDocumentCommand, operators) | none | bodies, arity, default, kind, expand |
| scan/test_macros.py::test_macros_math_classification_and_mathjax | unit | is_math_macro; to_mathjax | none | classification; exact list |
| scan/test_macros.py::test_macros_later_definition_wins | unit | redefinition | none | body "2" |
| scan/test_macros.py::test_conditionals_a_math_renderer_cannot_evaluate_are_resolved | unit | `\ifinner`/`\ifmmode` rewriting | none | exact bodies |
| scan/test_macros.py::test_a_conditional_that_cannot_be_resolved_is_left_alone | unit | `\ifdim` untouched | none | body unchanged |
| scan/test_macros.py::test_declared_alphabets_become_the_nearest_alphabet_a_renderer_has | unit | DeclareMathAlphabet mapping | none | mathpzc→mathcal; unknown→mathrm |
| scan/test_macros.py::test_compatibility_macros_are_published_only_when_a_body_needs_them | unit | scalebox/ensuremath stand-ins | none | exact dict; empty when unused |
| scan/test_macros.py::test_package_commands_are_published_only_when_the_package_is_loaded | unit | package_macros gating | none | old-arrows body; graphicx empty |
| scan/test_macros.py::test_a_paired_delimiter_is_published_as_the_declaration_itself | unit | DeclarePairedDelimiter | none | scanner macro; mathjax body |
| scan/test_macros.py::test_package_commands_cover_the_fonts_accents_and_integrals_a_renderer_lacks | unit | bm/bbm/dsfont/esint, amsmath via mathtools | none | bodies; gating |
| scan/test_nodes.py::test_example_single_file_paper | unit | whole node model on SINGLE_FILE | mq | masters, sections, envs, aliases, taxa, proofs, own ranges, labels, no errors |
| scan/test_nodes.py::test_env_node_without_id_qualified_key_and_regions | unit | positional keys, regions | mq | qualified keys; alias; region `where`; two unlabelled-node |
| scan/test_nodes.py::test_example_two_proofs_and_positional_keys | unit | labelled vs positional proof keys | mq | proof lists; one positional-proof-key |
| scan/test_nodes.py::test_statement_nested_in_proof_and_enclosure_keys | unit | nesting and enclosure at node level; `\incomplete` | mq | `of`; enclosure; own text; incomplete list; no errors |
| scan/test_nodes.py::test_directives_file_and_node_level | unit | directive inheritance | mq + node file | directives dict; proof inherits author; reached_by; hash prefix |
| scan/test_nodes.py::test_duplicate_id_and_label_errors | unit | cross-file duplicate id, duplicate label, commented label ignored | mq | exact error codes; locations |
| scan/test_nodes.py::test_external_node_and_digest_file | unit | external via cite; digest nodes | mq + digest + bib | external flags; digest; reached_by []; bib |
| scan/test_nodes.py::test_declared_prefix_carries_the_id_grammar | unit | digest `prefix:` directive | mq, long citekey | node under prefix; no slug keys; `uses` edge |
| scan/test_preamble.py::test_taxa_newtheorem_forms | unit | newtheorem variants and styles | tmp | taxon fields; body newtheorem ignored; loads_loom false |
| scan/test_preamble.py::test_taxa_declaretheorem_and_directive | unit | thmtools, `environment:` directive, `% !TEX program` | tmp | taxa; loads_loom; engine lualatex |
| scan/test_preamble.py::test_taxa_transitive_sty_chain | unit | preamble closure through .sty files | tmp | file order; taxa; macros; one unknown-theoremstyle |
| scan/test_preamble.py::test_taxa_display_name_macro | unit | taxon name from a macro | tmp | names; taxon-name-macro only |
| scan/test_preamble.py::test_taxa_conflict_between_masters | unit | taxa union and conflict | tmp | union style plain; one conflict |
| scan/test_relations.py::test_directive_see_node_level | unit | `see:` at node level | mq via `_quilt` | one relation; file and line |
| scan/test_relations.py::test_directive_see_file_level_applies_to_all | unit | file-level `see:` | mq | two relations |
| scan/test_relations.py::test_see_resolves_alias_and_digest_id | unit | alias and digest id resolve | mq + digest | to_keys set |
| scan/test_relations.py::test_see_dangling_link_with_location | unit | dangling `see:` | mq | error diag, message, location, keys; no relation |
| scan/test_relations.py::test_see_redundant_info | unit | self and alias-duplicate relations | mq | two see-redundant infos; one relation |
| scan/test_relations.py::test_see_not_in_closure_bundle_or_acceptance | unit | `see:` makes no edge | mq | no edge; closure; downstream |
| scan/test_relations.py::test_manifest_relations_shape | unit | manifest §16 shape | mq; build_manifest | exact relations list; no node field |
| scan/test_source.py::test_blank_comments_preserves_offsets | unit | comment blanking with `\%`, `\verb`, verbatim | none | length; prefix; kept text |
| scan/test_source.py::test_scan_all_tex_recursively_skips_build | unit | discover_files skips build/, refs/, non-tex | tmp files | exact list |
| scan/test_source.py::test_non_utf8_source_decoded | unit | mac_roman fallback | raw bytes | encoding; en dash |
| scan/test_source.py::test_ignore_directive_and_lines | unit | ignore directive; line/col | tmp | ignored; line 3 col 1 |
| scan/test_source.py::test_scan_reads_an_unsaved_buffer_from_an_overlay | unit | overlay scan | hand-built quilt | titles; buffer text; disk untouched; unsaved file reached |
| scan/test_source.py::test_notes_is_the_authors_reference_material_and_never_scanned | unit | notes/ excluded | mq | no node; no notes files |
| scan/test_source.py::test_the_seed_space_and_the_store_are_not_the_quilts_text | unit | refs/ and digests/storage excluded | tmp | exact list |
| scan/test_tokenize.py::test_tokenize_basic_forms | unit | token kinds | none | membership |
| scan/test_tokenize.py::test_tokenize_begin_end_and_verbatim | unit | begin/end/verbatim tokens | none | lists; verbatim body |
| scan/test_tokenize.py::test_tokenize_verb_command | unit | `\verb` | none | verb token; no begin |
| scan/test_tokenize.py::test_match_group_crosses_newlines_and_escapes | unit | match_group | none | spans |
| scan/test_tokenize.py::test_read_optional_not_across_blank_line | unit | read_optional | none | three cases |
| scan/test_tokenize.py::test_read_args_spec | unit | read_args "mom" | none | values; span; end pos |
| scan/test_tokenize.py::test_env_tree_nesting_and_problems | unit | env_tree nesting, stray end, unclosed | none | root/children; problems |
| render/test_build.py::test_build_layout_and_manifest | unit | demo compile + build: layout and manifest | demo; shim compile | files exist; 19 fields; ~15 values; macro set |
| render/test_build.py::test_fragment_kinds_and_dialect_validity | unit | synthetic fragments' markup and dialect validity | syn; shim compile; validator subprocess | exit 1; exact-markup substrings; no script; validator 0; svg dir |
| render/test_build.py::test_build_incremental_by_hash | unit | incremental re-render sets | demo; five builds | rendered/skipped per edit; `--keys`; node count |
| render/test_build.py::test_a_change_in_looms_own_code_re_renders_everything | unit | code hash invalidates cache | demo; patched `_code_hash` | all re-rendered |
| render/test_build.py::test_force_renders_every_fragment_again | unit | `force` via API and CLI | demo | all re-rendered; ", 0 unchanged" |
| render/test_build.py::test_build_atomic_publish_interrupted | unit | publish is atomic | demo; patched write_atomic | manifest unchanged; no .tmp |
| render/test_build.py::test_publish_skips_identical_bytes_and_keeps_named_files | unit | publish() skip/keep/prune | tmp | mtime kept; keep survives; prune |
| render/test_build.py::test_warm_build_leaves_skipped_fragments_in_place | unit | warm build rewrites nothing | demo | mtimes and text equal |
| render/test_build.py::test_build_exit_1_on_errors_still_publishes | unit | error exit still publishes | demo + dup node | exit 1; diagnostic in manifest |
| render/test_build.py::test_build_dir_deletable_and_regenerated | unit | rebuild after rmtree | demo | manifest; rendered non-empty |
| render/test_build.py::test_a_display_that_is_a_picture_goes_to_the_fallback | unit | renders_as_math classifier | none | six truth cases |
| render/test_build.py::test_an_inclusion_cycle_is_an_error_and_not_a_traceback | unit | render survives inclusion cycles | demo + three cycle files | exit in (0,1); no RecursionError; code; two cycle marks |
| render/test_build.py::test_a_render_on_one_thread_does_not_see_another_threads_inclusions | unit | renderer state is thread-local | demo scan; private `_expanding`, `_sink` | per-thread stack; collecting sink |
| render/test_build.py::test_a_report_fragment_is_never_a_dotfile | unit | report fragment filename | private `_attach_reports` | no leading dot; mapping |
| render/test_build.py::test_a_document_shows_its_own_numbers_and_none_it_was_not_given | unit | per-master numbering | syn scan; FragmentRenderer | numbers present/absent; title fallback regex |
| render/test_canon.py::test_a_canon_document_is_a_fragment_without_identity | unit | canon fragment and manifest entry | imp (shim); LOOM_FIXED_TIME | markup substrings; entry fields; macro set; search |
| render/test_canon.py::test_the_project_name_is_the_corpus_name | unit | corpus name: dir, then config | imp | "q" then configured name |
| render/test_canon.py::test_a_canon_fragment_is_cached_and_pruned | unit | canon cache and prune | imp | not re-rendered; file and entry pruned |
| render/test_canon.py::test_a_conflicted_key_is_published_with_no_text | unit | conflicted key in manifest | imp + dup node | exit 1; node/key fields; label; fix; no fragment |
| render/test_canon.py::test_a_key_whose_text_a_landmark_recorded_carries_its_version | unit | key `version` from canonize | imp; canonize | version dicts; proof loses version after edit |
| render/test_convert.py::test_convert_paragraphs_and_inline_markup | unit | paragraphs, emph/bf, ligatures, `\S`, `~` | `make()` harness | substrings; data-src; no fallback/diags |
| render/test_convert.py::test_convert_math_inline_display_labels | unit | inline/display math, labels, tags, align | make with numbers | exact attribute strings; `\tag`; no `\label`; four displays |
| render/test_convert.py::test_convert_refs_cites_footnote_url | unit | refs, dangling, cites, footnote, url/href | make | exact anchor markup; regex; cite attrs |
| render/test_convert.py::test_convert_lists_and_sectioning | unit | lists, description, section | make | tags; li count; labelled item |
| render/test_convert.py::test_convert_env_fallback_diagram_verbatim_table | unit | tikzcd, parbox, verbatim, table, unknown env | make | fallback kinds; pre; table cells; three converter-fallback |
| render/test_convert.py::test_convert_text_macros_expanded_and_math_macros_left | unit | text macros expand; math macros stay | make + macros | text; `\Res` kept in math |
| render/test_convert.py::test_convert_nothing_dropped_unknown_command_falls_back | unit | unknown command falls back | make | one fallback; one p; diag |
| render/test_convert.py::test_convert_children_and_inclusions_become_placeholders | unit | child and `\input` placeholders in order | make with children | index order; paragraph regex |
| render/test_convert.py::test_convert_conditionals_definitions_starred_sections | unit | `\iffalse`, definitions, `\section*` | make | skipped text; no diags |
| render/test_convert.py::test_an_accent_without_braces_keeps_the_text_that_follows_it | unit | braceless accent mid-text | make | NFC text; no diags |
| render/test_convert.py::test_an_accent_without_braces_keeps_the_paragraph_it_starts | unit | braceless accent at paragraph start | make | NFC text; two p |
| render/test_convert.py::test_a_macro_inside_text_is_written_between_dollars | unit | macro in `\text{}` wrapped in `$` | make + macros | two substrings |
| render/test_convert.py::test_a_macro_already_inside_math_within_text_is_left_alone | unit | no double wrapping | make | one occurrence |
| render/test_convert.py::test_a_reference_inside_a_text_argument_is_not_wrapped_in_text | unit | `\ref` inside `\tag{}` | make with numbers | tag text; no `\text` in tag |
| render/test_convert.py::test_a_citation_prints_the_compiled_label | unit | cite label from compile | make with cite_labels | `[GP99, Theorem 1]`; key fallback |
| render/test_convert.py::test_a_comment_inside_a_formula_does_not_reach_the_renderer | unit | `%` in align and inline math | make | no `%`; label/number of live line only |
| render/test_convert.py::test_qedhere_is_dropped_from_a_formula | unit | `\qedhere` dropped | make | absent; formula kept |
| render/test_inline_env.py::test_inline_environment_renders_as_html_not_a_picture | unit | inline envs in a master render as HTML | `init` + master written; CLI build | no figure/pre; exact env markup substrings |
| render/test_inline_env.py::test_failed_fallback_is_cached_and_not_recompiled | unit | failed SVG remembered | FAKE_TEX_FAIL; FAKE_TEX_LOG | log non-empty; `.failed` exists; second build logs nothing |
| render/test_marks.py::test_marks_placed_inline_and_block_level | unit | place_marks inline, across `<em>` | literal HTML | exact mark strings; three marks |
| render/test_marks.py::test_two_comments_on_the_same_words_are_one_mark | unit | identical quotes merge | literal HTML | one mark with two ids |
| render/test_marks.py::test_overlapping_quotes_join_one_mark | unit | overlapping quotes merge | literal HTML | one mark; id order |
| render/test_marks.py::test_a_quote_around_math_takes_the_formula_whole | unit | mark wraps whole formula | literal HTML | exact string |
| render/test_marks.py::test_a_quote_inside_a_formula_never_puts_a_tag_inside_it | unit | quote inside formula / display | literal HTML | formula marked whole; display gets annotation-block |
| render/test_own_text_inclusions.py::test_moving_a_node_out_of_a_draft_changes_no_hash | unit | moving a node to nodes/ keeps every hash | syn; private atomize helpers | moved and all other hashes equal |
| render/test_own_text_inclusions.py::test_an_inclusion_of_a_child_reads_as_that_child | unit | own_text replaces `\input` by child marker | syn | marker present; `\input` absent |
| render/test_serve.py::test_serve_static_routes | unit | static routes, SPA fallback, ETag, traversal | `session` fixture (demo + ServeSession, fake bundle) | statuses; content type; 304; 404s |
| render/test_serve.py::test_serve_republishes_on_change | unit | watcher rebuild on edit | session; sleeps, 6 s deadline | ETag changes; new title; builds ≥ 2 |
| render/test_serve.py::test_serve_no_notification_sent | unit | no outbound HTTP on rebuild | session; patched HTTPConnection | no non-loopback calls |
| render/test_serve.py::test_serve_exit_2_without_bundle | unit | missing bundle exits 2 | demo; patched find_bundle | exit 2; "bundle" |
| render/test_serve.py::test_serve_spa_fallback_for_dotted_routes | unit | dotted route vs missing asset | session | 200 shell; 404; favicon 200-or-404 |
| render/test_serve.py::test_serve_offers_a_works_fetched_artifacts | unit | serves digests/storage files | session; fake PDF | 200 + content type; 404; traversal 400/404 |
| render/test_serve.py::test_the_write_api_binds_to_loopback_only | unit | bind address | session | 127.0.0.1 |
| render/test_serve.py::test_discovery_lists_what_this_publisher_serves | unit | `/_api` discovery | session | version; capabilities; unlisted endpoint 404 |
| render/test_serve.py::test_a_comment_written_over_http_is_the_same_comment | unit | comment/reply/edit/discard over HTTP | session; sessions.create | log entry fields; four 200s; event set |
| render/test_serve.py::test_the_manifest_is_current_when_a_write_answers | unit | write rebuilds before answering | session | renamed title on next GET |
| render/test_serve.py::test_a_refused_write_answers_rather_than_dying | unit | malformed writes get error JSON | session | 400 codes; 400/404 |
| render/test_serve.py::test_a_citation_suggestion_is_accepted_or_rejected_over_the_api | unit | refs-note accept | session | breadcrumb fields; resolved event; bad-field |
| render/test_serve.py::test_rejecting_a_citation_writes_no_breadcrumb | unit | refs-note reject | session | 200; notes file unchanged |
| render/test_serve.py::test_the_watcher_watches_what_the_write_api_writes | unit | snapshot includes .jsonl and config | hand-built dir | watched set membership |
| render/test_serve.py::test_the_watcher_does_not_chase_its_own_build | unit | no rebuild loop on last-seen.json | session; 2 s sleep | builds ≥ 2 then stable |
| render/test_serve.py::test_a_write_without_the_token_is_refused_over_the_wire | unit | token gate | session | 403 + message; token served; ≠ 403 with token |
| render/test_serve.py::test_a_link_into_the_running_viewer_is_offered_only_while_one_is_running | unit | open_url liveness check | tmp; fake pid 2^22 | URL while alive; "" when stale |
| test_tex_layer.py::test_aux_read_plain_and_hyperref | unit | parse_aux plain/hyperref/cref | none | numbers, pages; `@cref` dropped |
| test_tex_layer.py::test_compile_master_and_numbers_from_aux | unit | `loom compile` on shim | demo; FAKE_TEX_LOG | aux numbers; `-outdir=` in log |
| test_tex_layer.py::test_linearize_flattens_with_nest_shift | unit | assemble, shift_sectioning, `loom linearize` | hand-built quilt | flattened text; shifts; exit 0 then 2; "superseded" |
| test_tex_layer.py::test_bundle_contents_and_order | unit | build_bundle closure and order; bundle compile | demo | closure set; index order; PDF exists |
| test_tex_layer.py::test_source_prints_a_key_and_its_closure | unit | `loom source KEY` and `--closure` | demo; `ai start` | output prefix; no files; run.log; order |
| test_tex_layer.py::test_source_prints_a_whole_document_flattened | unit | `loom source PATH` | demo; `ai start` | flattened doc; nothing written; `--closure` refused; bad path |
| test_tex_layer.py::test_compile_with_diff_does_not_touch_quilt | unit | `compile --with` diff and replacement | demo | bundle text; node file unchanged |
| test_tex_layer.py::test_compile_with_bad_diff_exit_1 | unit | non-applying diff | demo | exit 1; "does not match" |
| test_tex_layer.py::test_compile_draft_unpromoted_node | unit | `compile --draft` | demo | bundle ids and text; bad ref exits 1 |
| test_tex_layer.py::test_check_lints_and_compiles | unit | `loom check` | demo | exact output lines; `--bundles all`; exit 1 on dup |
| test_tex_layer.py::test_compile_failure_reports_first_error | unit | compile failure message | demo; FAKE_TEX_FAIL | exit 1; "! LaTeX Error" |
| test_tex_layer.py::test_search_json_still_single_document | unit | `search --json` parses | demo | json.loads succeeds |
| test_tex_layer.py::test_a_statements_closure_covers_the_proof_it_prints | unit | statement closure includes proof deps (F2) | demo | dm-0002 present; order |
| test_tex_layer.py::test_with_names_a_file_first_and_then_an_annotation | unit | `--with` file vs annotation id (F15) | demo; `comment --payload` | message; no traceback; payload applied; wrong key refused |
| test_tex_layer.py::test_a_readable_pdf_is_not_a_failure | unit | CompileResult.usable / first_error | positional CompileResult | usable values; four first_error strings |
| test_tex_layer.py::test_stage_sources_leaves_the_build_products_behind | unit | stage_sources filtering | tmp tree | exact staged files; `../` resolves; .bbl kept without .bib |
| test_tex_layer.py::test_id_and_new_log_themselves_to_the_session | unit | `id --next` / `new` log to session | demo; `ai start` | run.log lines |
| test_tex_layer.py::test_citation_labels_come_from_the_compile | unit | parse_cite_labels | none | exact dict |
| test_fake_latex.py::test_fake_latex_emits_aux | unit | shim aux numbering | shim on PATH | five newlabel lines; pdf; log prefix |
| test_fake_latex.py::test_fake_pdftotext_round_trip | unit | shim pdftotext/pdfinfo | shim | text present; no commands; "Pages:" |
| test_fake_latex.py::test_fake_latex_failure_injection | unit | FAKE_TEX_FAIL | shim | exit 12; log line |
| test_fake_latex.py::test_fake_dvisvgm_and_kpsewhich | unit | shim dvisvgm, kpsewhich | shim | svg header; found/missing codes |
| tex/test_bundles_real.py::test_bundle_compiles | tex | three bundles compile | demo; TeX | exit 0 each |
| tex/test_bundles_real.py::test_demo_master_compiles_and_numbers | tex | demo master numbers | demo; TeX | exit 0; newlabel dm-0003 2.1 |
| tex/test_bundles_real.py::test_bundle_failed_diagnostic | tex | broken bundle reported | demo; TeX | exit 1; "FAILED bundle dm-0003" |
| tex/test_fallback_preamble.py::test_fallback_compiles_after_input_xy | tex | SVG fallback after `\input xy` | TeX (latex, dvisvgm) | svg produced; no .failed |
| tex/test_fallback_preamble.py::test_fallback_records_and_reuses_a_failure | tex | failure cached | TeX | first uncached error; .failed; second cached, same error |
| tex/test_fixture_vendored.py::test_fixture_matches_vendored | tex | synthetic build equals vendored fixture | syn; TeX; LOOM_FIXED_TIME; tests/fixture | normalised manifest equal; every fixture fragment equal modulo SVG |
| tex/test_real_toolchain.py::test_real_latexmk_compiles_minimal_document | tex | toolchain sanity | TeX | exit 0; two newlabels; pdf > 1000 B |
| tex/test_real_toolchain.py::test_real_pdftotext_extracts_text | tex | pdftotext sanity | TeX + poppler | text present |
| tex/test_reshape_real.py::test_import_is_flat_and_draft_labels_it | tex | import flat, draft labels | imp; TeX; pdftotext | no `\input`; no labels; identity pass; five labels |
| tex/test_reshape_real.py::test_atomize_identity_and_inline_identity | tex | atomize then inline keep identity | imp; TeX | identity pass ×2; node files; flat text |
| tex/test_reshape_real.py::test_canonize_writes_a_landmark_that_compiles_alone | tex | canon compiles standalone | imp; atomize; TeX | identity pass; latexmk exit 0; pdf |
| tex/test_reshape_real.py::test_inline_nest_shifts | tex | inline shifts `\nest` headings | imp; TeX | heading text; identity pass |
| tex/test_reshape_real.py::test_identity_reports_first_diff_and_label_numbers | tex | identity_test failure report | paper copies; TeX | first diff; summary text; changed number |
| tex/test_reshape_real.py::test_import_neither_reads_nor_writes_the_authors_build_files | tex | import ignores author's .bbl/.fdb | TeX; biber | fdb present; exit 0; author dir bytes unchanged |
| papers/test_papers.py::test_paper_manolache_import_is_a_verbatim_landmark | paper+tex | Manolache import verbatim | LOOM_PAPER_FIXTURES/0805.2065 | identity pass; canon == source; ledger |
| papers/test_papers.py::test_paper_manolache_draft_labels_the_working_copy | paper+tex | draft refuses, then `--fix-anchoring` | same | "51 violation(s)"; attach counts; 112 labels; lint clean |
| papers/test_papers.py::test_paper_manolache_atomize_sections | paper+tex | atomize `--sections` | same | identity pass; ≥ 96 node files; ledger; lint |
| papers/test_papers.py::test_paper_manolache_canonize_is_self_contained | paper+tex | canon compiles standalone | same | identity pass; ≥ 96 froze; pdf |
| papers/test_papers.py::test_paper_acgs_import_with_documented_edits | paper+tex | ACGS import and draft | 1709.09864 | identity pass; pspdftex figures; 0 dangling |
| papers/test_papers.py::test_paper_acgs_scan_time_and_memory | paper+tex | scan budget | ACGS imported | > 100 nodes; < 10 s; < 300 MB |

**Support files (no tests of their own).** `tests/fake_latex/fake_tex.py` is the shim: conftest copies it under twelve tool names into a session tmp dir with the shebang pinned to the test interpreter. It is exercised directly only by `test_fake_latex.py`, and implicitly by every unit test that compiles, builds or calls kpsewhich. `tests/tools/validate_dialect.py` is run only by `test_fragment_kinds_and_dialect_validity` (as a subprocess); it is byte-identical below its header to `docs/specs/tools/validate-dialect.py`. `tests/fixture/` (manifest, 40 fragments, `source/`, `svg/`, `diffs/`, `transcripts/`, `VERSION`) is read by one loom test, `test_fixture_matches_vendored`, and only its `manifest.json` and `fragments/`; arras reads its own copy (`arras/tests/fixture/`, identical today) in about ten e2e specs and two vitest specs. `docs/specs/fixture/` is a third identical copy. `tests/unit/scan/fixtures/zk_proof_after_remark.tex` is used only by `test_basis.py`.

## Critique

### Redundant or overlapping

Pairs, with the one to keep first.

- `test_source.py::test_scan_all_tex_recursively_skips_build` / `test_the_seed_space_and_the_store_are_not_the_quilts_text`: both assert `discover_files` exclusions on a tmp tree (build/, refs/, digests/storage/). Keep one, parametrized over the excluded prefixes with the reason as the id.
- `test_envtree.py::test_env_spans_files_problem` / `test_tokenize.py::test_env_tree_nesting_and_problems` (its second half): the same input `\begin{lemma}\nno end` and the same `("unclosed", 0, "lemma")`. Keep the tokenize one (env_tree owns the problem); drop the envtree test.
- `test_envtree.py::test_statement_nested_in_proof` / `test_nodes.py::test_statement_nested_in_proof_and_enclosure_keys`, and `test_envtree.py::test_proof_by_enclosure` / the enclosure half of the same nodes test: the node-level test re-asserts own-text exclusion and enclosure attach already pinned at envtree level. Keep both levels but drop the own-text assertion (test_nodes.py:139-145) from the node test; it adds nothing the envtree one lacks.
- `test_nodes.py::test_duplicate_id_and_label_errors` / `test_conflicts.py::test_a_node_file_and_an_inline_copy_conflict`: both build "inline copy + nodes/ file with the same id" and assert duplicate-id naming both files. Keep the conflicts test for duplicate-id; trim the nodes test to duplicate-label and the commented-out label.
- `test_build.py::test_build_exit_1_on_errors_still_publishes` / `test_canon.py::test_a_conflicted_key_is_published_with_no_text`: both add a duplicate id and build; the canon one asserts exit 1 and the manifest diagnostic too, plus more. The build test could go, or be reduced to "manifest.json exists after exit 1" folded into the canon test.
- The "warm build renders nothing" assertion appears in four demo tests (`test_build_incremental_by_hash`, `test_a_change_in_looms_own_code_re_renders_everything`, `test_force_renders_every_fragment_again`, `test_warm_build_leaves_skipped_fragments_in_place`), each paying a cold and a warm build. Keep it once (`test_warm_build_leaves_skipped_fragments_in_place` is the strongest form); the others can start from a pre-built copy.
- Closure order `dm-0002 < dm-0003 < dm-0003/proof` is asserted three times: `test_bundle_contents_and_order`, `test_source_prints_a_key_and_its_closure` (test_tex_layer.py:114-117) and `test_a_statements_closure_covers_the_proof_it_prints`. Keep the bundle test (API) and the F2 regression; drop lines 112-117 from the source test.
- `tex/test_real_toolchain.py::test_real_pdftotext_extracts_text` recompiles the same MINIMAL document as `test_real_latexmk_compiles_minimal_document`, and every identity test in `test_reshape_real.py` already fails if pdftotext is broken. Fold its one assertion into the first test.
- `tex/test_real_toolchain.py::test_real_latexmk_compiles_minimal_document` / `tex/test_bundles_real.py::test_demo_master_compiles_and_numbers`: both assert real-aux numbering. Keep both only if the minimal one is meant as the "is TeX installed correctly" canary (its failure message is clearer); otherwise keep the demo one, which goes through loom.
- `test_tex_layer.py::test_compile_master_and_numbers_from_aux` (shim) mirrors `tex/test_bundles_real.py::test_demo_master_compiles_and_numbers` (real): intentional tier pairing, keep both.
- `test_basis.py::test_drafting_scan_classifies_five_bases_and_flags_uncertainty` / `test_accept_all_live_refuses_to_establish_an_open_claim`: the first also drives `accept --all-live` and per-key refusals. Overlapping and overloaded; split the CLI half of the first test out, next to the second.
- `test_serve.py`: `_api` returning 200 is asserted in `test_serve_static_routes` (line 84), `test_discovery_lists_what_this_publisher_serves` and `test_a_write_without_the_token_is_refused_over_the_wire`. Drop line 84.
- `test_serve.py::test_a_citation_suggestion_is_accepted_or_rejected_over_the_api` / `test_rejecting_a_citation_writes_no_breadcrumb`: same setup, could be one parametrized test over `accept`/`reject`.

### Long or slow

Measured costs from the other job's full run (129 s wall for the whole loom suite): the TeX tier in this slice is about 48 s, the unit-tier part of this slice roughly 20-30 s, the paper tier minutes when enabled (skipped there).

- `tex/test_reshape_real.py` is the most expensive file (≈ 34 s over six tests): `test_import_neither_reads_nor_writes_the_authors_build_files` 11.35 s (a biblatex/biber compile plus an import identity test), `test_canonize_writes_a_landmark_that_compiles_alone` 6.55 s, `test_atomize_identity_and_inline_identity` 5.86 s, `test_inline_nest_shifts` 4.43 s, `test_import_is_flat_and_draft_labels_it` 3.27 s, `test_identity_reports_first_diff_and_label_numbers` 2.93 s. Four of the six redo `imported()`+`drafted()` (two identity tests, i.e. four real compiles, ≈ 2.5 s) from scratch, and two of them atomize the same drafted quilt. A module-scoped `drafted` fixture copied per test (`shutil.copytree`) saves ≈ 7-8 s; running atomize once and doing inline and canonize on it saves another ≈ 3 s.
- `tex/test_fixture_vendored.py::test_fixture_matches_vendored` 7.36 s: two real master compiles and a build with real SVG fallbacks. Necessary; it is the only conformance check.
- `tex/test_bundles_real.py`: `test_bundle_compiles` 2.30 s, `test_demo_master_compiles_and_numbers` 2.00 s, `test_bundle_failed_diagnostic` unlisted (< 0.4 s, failing fast). Fine.
- `render/test_serve.py`: every test using the `session` fixture pays **0.5 s in teardown** (twelve of them show exactly 0.50 s): `ServeSession.stop()` calls `httpd.shutdown()`, which waits out `serve_forever`'s default `poll_interval=0.5` (serve.py:466). About 7 s of pure waiting per run; pass `poll_interval=0.05` in serve.py or make the fixture module-scoped for the read-only tests. On top, `test_the_watcher_does_not_chase_its_own_build` 2.52 s is mostly a fixed `time.sleep(2)` plus 0.3 s, and `test_serve_republishes_on_change` 0.52 s carries a fixed `sleep(0.3)` (mtime granularity).
- Whole-quilt builds where a unit would do: `test_an_inclusion_cycle_is_an_error_and_not_a_traceback` (a full demo CLI build to test that the renderer and inclusion tree terminate on a cycle; a two-file quilt and `build()` would do), `test_build_dir_deletable_and_regenerated` (two demo builds), `test_inline_env.py` (two to three CLI builds each), and all five `test_canon.py` tests (each runs `init --from` with the shim identity test, `draft`, and one to three builds; ≈ 0.3-0.4 s each). Each is ≈ 0.3-1 s on the shim, so the unit-tier gain from rewriting is a few seconds; worth it mainly for clarity.
- Roughly 40 unit tests in this slice call `loom init --demo` (0.16 s) and then build or compile it. A session-scoped pristine demo copied per test would save little time (init is cheap) but a session-scoped *built* demo would save the ≈ 0.5 s cold build in the ten `test_build.py` tests that start by building.
- Paper tier: `import_paper` (init + draft, each with an identity test on a 60-page paper) is repeated by five of six tests, and atomize by two. A module-scoped imported/drafted Manolache quilt would roughly halve the tier.

### Delete or combine

- Delete `tex/test_real_toolchain.py::test_real_pdftotext_extracts_text` (fold into the minimal compile test; covered by every identity test). Also delete its `pytest.importorskip("shutil")` line, which cannot skip.
- Delete `test_envtree.py::test_env_spans_files_problem` (exact duplicate of the unclosed case in `test_env_tree_nesting_and_problems`; the name is also wrong, nothing spans files).
- Combine `test_scan_all_tex_recursively_skips_build` and `test_the_seed_space_and_the_store_are_not_the_quilts_text` into one parametrized test.
- Delete `test_build.py::test_build_exit_1_on_errors_still_publishes` if `test_canon.py::test_a_conflicted_key_is_published_with_no_text` keeps its exit-1 and diagnostic assertions (it does).
- Delete `test_tex_layer.py::test_search_json_still_single_document`, or move it to the search tests with an exit-code check: it asserts only that the output parses as JSON and has nothing to do with the TeX layer.
- Move, not delete: `test_build.py::test_a_display_that_is_a_picture_goes_to_the_fallback` is a pure converter test and belongs in `test_convert.py`; `test_tex_layer.py::test_id_and_new_log_themselves_to_the_session` and the two `test_source_*` tests belong with the session/CLI tests; the write-API tests in `test_serve.py` (comment, refs-note, token, refused writes; seven tests) belong with the write-API tests, since `render/` is the wrong home.
- Combine the two refs-note tests in `test_serve.py` via parametrize; combine the reshape TeX tests around one module-scoped drafted quilt (see above); combine the paper tests around one imported Manolache quilt.
- Dead code to remove: test_convert.py:67-68 (the first `make()` result is discarded and `ctx.regions` is mutated on a context that is never used again); test_inline_env.py:79 (`shutil.rmtree` on a file path with `ignore_errors`, immediately followed by the `unlink` that does the work); test_serve.py:147-148 (`status in (200, 404)` for favicon asserts nothing).

All of these are safe because each deleted assertion is made identically, on the same input, by the test that is kept, or asserts nothing.

### Missing

Behaviour in scan/render/tex, or in the dialect and manifest specs, that no test in the suite covers (checked by grepping all of `loom/tests`, not just this slice):

- **The dialect validator has no negative test.** tests/tools/validate_dialect.py:34-90 is only ever run on a build it is expected to pass. A validator that accepted everything would pass `test_fragment_kinds_and_dialect_validity`. Add a unit test feeding it `<script>`, an unknown class, a `p` without `data-src`, `div.include` without `data-key`, and an absolute `href` outside `a.url`, asserting each problem line. Also add a test that `tests/tools/validate_dialect.py` equals `docs/specs/tools/validate-dialect.py` below the header (they are identical today, with nothing keeping them so).
- **Dialect constructs covered only by the TeX-tier fixture comparison, never on the unit tier:** `\textcolor` → `span.tex-color[data-color]` (dialect.md §2.6; convert.py:946-951; `test_convert_text_macros_expanded_and_math_macros_left` only asserts "textcolor" is absent, so dropping the colour would pass), `\incomplete` → `span.incomplete[data-key]` (§2.10; convert.py:921), `blockquote` for quote/quotation/abstract (convert.py:623), `span.smallcaps` (convert.py:145), `a.ref-eq` (convert.py:1087), and `\includegraphics` → `figure > img[src]` (§2.11; fragments.py:299). One `make()` case each in test_convert.py.
- **The id slug rule for untagged keys** (dialect.md §2.2: `data-key` slugged by `[^A-Za-z0-9]+`, lowercased; convert.py:384) is only seen for simple ids (`id="sy-0003"`, `id="lem-a"`). Nothing asserts `drafting/main.tex#lemma:1` → `drafting-main-tex-lemma-1`.
- **render/assets.py has no direct test**: `publish_graphic` PDF→SVG via pdftocairo, fallback to `dvisvgm --pdf`, raster copied, not-found error (assets.py:24-57). The shim already answers `pdftocairo` (fake_tex.py:290), so a unit test is cheap.
- **render/fallback.py pure functions untested**: `namespace_ids` (fallback.py:46; prevents glyph-id collisions when several SVGs share a page), `resize_svg` (59), `_strip_prolog` (74).
- **A remembered SVG failure can never be cleared.** fallback.py:101 says "`loom build --force-svg` clears the cache", but `loom build --help` has no such option and `--force` only bypasses the fragment index (build.py:354). The cache key is preamble + body (fallback.py:34), so a block that failed because a package was missing stays failed after the author installs it. A test would have found this; either implement the flag or fix the comment, and test the chosen behaviour.
- **render/review_compare.py** (`_changed`, `attach_comparisons`) and **render/incoming.py** are not imported by any test; review fragments are covered only by the TeX-tier fixture (`fragments/review/*`) and one substring check in `records/test_review_commands.py:121`. `_changed` is a pure function worth a unit test.
- **tex/aux.py** `aux_path_for` fallback to the `.aux` beside the master (aux.py:62-69) and `read_cite_labels` reading the `.bbl` beside it (114-123): untested; only the parsers are.
- **tex/identity.py:56**: when pdftotext is missing, `identity_test` returns `passed=True` with `skipped`. Nothing tests that the CLI surfaces "skipped" rather than "pass", and `test_identity_reports_first_diff_and_label_numbers` would fail confusingly (`assert not res.passed`) on a machine without poppler instead of skipping.
- **scan/alloc.py** `visible_locals` sources other than source text and history: the annotation log (alloc.py:28-30) and git history (31-61). The history case is covered in `history/test_commands.py:194`; the other two are not.
- **scan/expand.py** handles `\include` (expand.py:18) but `test_inclusion_input_include_nest_and_span_map` uses only `\input` and `\nest`, despite its name.
- **scan/graph.py** `cycles()` (graph.py:76) is covered only as "the code appears" in `test_dependency_cycle_and_slug_collision`; nothing checks which keys the cycle names.
- **Manifest top level** (manifest.md §1): `test_build_layout_and_manifest` checks a hand-kept list of 19 fields that omits `publishes` (which must be all `true` for loom), `canon`, `relations`, `reference_notes`, `sessions`, `unresolved`. Nothing on the unit tier checks `publishes`. The list is a restatement of the spec that has already drifted; derive it from the spec or pin `publishes` explicitly.
- **The fixture comparison is partial.** test_fixture_vendored.py:61 iterates the fixture's fragments only, so a fragment loom newly emits but the fixture lacks passes; `source/`, `diffs/` and `transcripts/` are vendored (and read by arras) but never compared.

### Failure diagnostics

- **`exit_code in (0, 1)` passes on a crash.** `CliRunner.invoke` catches exceptions and reports `exit_code == 1`, so these assertions cannot tell a traceback from an error-severity diagnostic: test_canon.py:64, 86, 90, 96, 100, 129, 135; test_inline_env.py:52, 72, 81; test_build.py:297. test_build.py:298 guards only `RecursionError`. Better: a helper `built(r)` asserting `r.exception is None or isinstance(r.exception, SystemExit)`, with `r.output` as the message, and, where the expected code is known (the canon quilts have a known error count), assert that code exactly.
- **Exit-code assertions with no output message** (a failure prints `assert 1 == 0` and nothing else): test_build.py:57, 124; test_canon.py:52, 54, 113, 128; test_inline_env.py:45; test_tex_layer.py:76, 133, 184, 195, 306, 307; tex/test_fixture_vendored.py:56; tex/test_bundles_real.py:25, 34, 44; papers/test_papers.py:80-83. Add `, r.output` everywhere.
- **Unchecked commands**: tex/test_fixture_vendored.py:57 ignores `loom build`'s exit and output (a build that raises leaves a stale or missing manifest and the failure surfaces as a `FileNotFoundError` or a giant dict diff); test_tex_layer.py:103, 123, 304 take `sid` from `ai start` without checking its exit, so a failure there shows up later as a missing `run.log` path; test_tex_layer.py:207 `json.loads(r.output)` fails with a bare `JSONDecodeError` and no output.
- **Whole-manifest equality**: test_fixture_vendored.py:60 compares two ~100 KB dicts; pytest's diff is truncated and does not say which top-level section differs. Compare per section (`for k in sorted(keys): assert ours[k] == theirs[k], k`), and for fragments show a `difflib.unified_diff` limited to the first hunk instead of the full-string comparison at line 65.
- **Exact-markup substrings over attribute order**: test_build.py:129-131 (`node.startswith('<div data-fragment="node" class="env env-theorem" id="sy-0003" data-id="sy-0003"')`), test_build.py:138, 140; test_inline_env.py:55-60; test_convert.py:58, 72-74, 81; test_canon.py:66-71. A harmless attribute reorder fails them, and the failure prints two long strings with no hint of which attribute moved. Parse the first element with `html.parser` (the validator already has a parser) and assert on the attribute dict.
- **Negative substring checks that can pass or fail for the wrong reason**: test_inline_env.py:54 `"figure" not in master` also matches the word in prose; test_build.py:148-149 `"<script" not in html` duplicates the validator; test_convert.py:144 `"missing" not in out`.
- **Bare boolean chains**: test_nodes.py:30-32, 96-100, 140-145, 191-193; test_basis.py:65, 71 (`exit_code != 0 and phrase in output` reports `False` without the output). Split into separate asserts or add the value as the message.
- **Loose status sets**: test_serve.py:165, 266, 268 (`in (400, 404)`) and 377 (`!= 403`, which passes via a 400 `no-session` because the body names no session and targets `sy-0001` in a `dm-` demo). Pin the actual code.
- test_labels_hashing.py:20 writes the expected value as `"10000"[-5:]`, which is just `"10000"` and reads as though it computed something.
- test_tex_layer.py:250-264 builds `CompileResult` with up to ten positional arguments; a field reorder in runner.py:24 would produce confusing failures or silent passes. Use keywords.

### Other

- **The "known-failing" biber test passes.** `test_import_neither_reads_nor_writes_the_authors_build_files` passed in my isolated run (11.98 s; TeX Live 2024, biber 2.20 at `/usr/local/texlive/2024/bin/universal-darwin/biber`) and in the other job's full run (11.35 s; `scratchpad/audit/loom-pytest.txt` has no failures). The failure is therefore environment-specific rather than a loom bug. The most likely cause is TeX Live's macOS biber, a PAR-packed binary that unpacks itself under `$TMPDIR/par-<hex user>/` on first run: any environment where that cache is missing, stale or not writable (a sandbox, a cleaned TMPDIR, a different user) makes biber fail. The test's only guard is `shutil.which("biber")` (test_reshape_real.py:180), which does not show that biber runs. Two fixes, in order of preference. (a) The property under test (latexmk under `-outdir` reads a stale `.bbl` in the working directory) does not depend on biber, so rewrite the paper with `\bibliographystyle{plain}\bibliography{refs}` and bibtex; this removes the dependency and a third of the cost. (b) Otherwise, probe with `biber --version` (or a session-scoped tiny biber run) and skip with the probe's stderr as the reason. The test should not stay listed as known-failing.
- **Hermeticity hole: process-wide kpsewhich cache.** `loom.scan.expand._kpsewhich` is `@functools.cache` keyed on the name only (expand.py:83), not on PATH. In a mixed run, answers from the shim's fixed 14-name list (fake_tex.py:15-30) are reused by later `tex` and paper tests that expect the real kpsewhich, and vice versa. The shim also answers relative to the test's cwd (fake_tex.py:272), so answers depend on test order. Only `test_kpsewhich_is_probed_once_per_name` clears the cache, and not in a `finally`. Add an autouse fixture in conftest calling `_kpsewhich.cache_clear()`, or key the cache on `(name, os.environ["PATH"])`.
- **TeX trees are isolated** (all four `TEXMF*` variables point to an empty dir; `TEXINPUTS`/`BIBINPUTS`/`BSTINPUTS` unset), but the tex tier adds the whole poppler directory to PATH, on this machine `/opt/homebrew/bin`, which also holds git, python and every other Homebrew tool. `FAKE_TEX_FAIL_MATCH` is not in conftest's delenv list (conftest.py:78), so an exported value would leak into every unit test.
- **Tests of implementation rather than behaviour**: `test_a_render_on_one_thread_does_not_see_another_threads_inclusions` (private `_expanding`, `_sink`, `collecting`); `test_kpsewhich_is_probed_once_per_name` (memoisation; acceptable as a performance guard); `test_own_text_inclusions.py` reimplements atomize with private `_directive_start`/`_line_bounds` from `loom.reshape.atomize` instead of calling `plan_atomize` or `loom atomize`, so it tests a copy of atomize's line logic; `test_a_report_fragment_is_never_a_dotfile` calls private `_attach_reports` (acceptable: the public path needs a session run).
- **Timing-dependent serve tests**: `test_serve_republishes_on_change` and `test_the_watcher_does_not_chase_its_own_build` rely on sleeps (0.3 s mtime separation, 6 s deadlines, a 2 s "nothing happens" window); the second can only prove the absence of a rebuild loop within 2 s. They have not flaked in the recorded runs, but on a loaded CI runner the 0.2 s watcher interval against a 0.3 s sleep is marginal. `test_serve.py` builds URLs as `s.url + "/_api"` (lines 195, 200, 207, ...) where `s.url` already ends in `/`, so they request `//_api` and rely on the server normalising it.
- **Stale or wrong statements in tests**: test_build.py:126 says the synthetic quilt has "three intentional errors" (it has five: EXPECTED-LINT.txt); test_papers.py:22 points at `tests/fixtures/NOTES.md`, which does not exist in `loom/` (the book places it in the workspace, uncommitted); test_envtree.py:65 is named "spans files" but tests one unclosed environment; `test_inclusion_input_include_nest_and_span_map` never uses `\include`.
- **Stale in the book** (docs/book/14-tests.md, found while checking names; pass 1): line 129 lists `test_bundle_with_diff_does_not_touch_quilt`, `test_bundle_with_bad_diff_exit_1`, `test_bundle_draft_unpromoted_node` and `test_bundle_run_copy_and_log`, now `test_compile_*` or gone; chapter 4 lists `test_assemble_flattens_with_nest_shift` (now `test_linearize_flattens_with_nest_shift`); 14.1 says the paper tier has 4 tests (it has 6); 14.4 places the workflows in `loom/.github/workflows/unit.yml`/`tex.yml` and says "the workspace repository has no workflows", whereas they are `.github/workflows/loom-unit.yml` and `loom-tex.yml` in the workspace. Of 243 test names the chapter mentions, 63 match no `def` in loom or arras (some are listed deliberately as "not written").
- **Spec gap**: the manifest has a top-level `links` array (render/manifest.py:392; present in the vendored fixture) that manifest.md §1 does not name. The fixture test passes because both sides carry it, so the spec is the thing out of date.
- **Legacy shim despite the no-backwards-compatibility rule**: `test_legacy_definition_directive_maps_to_expository` pins a `basis: definition` alias. If no quilt uses the old spelling, the alias and its test can both go.
- **Markers**: the paper module is marked `paper` and `tex`, so CI's `-m tex` job collects it and skips all six on the missing env var, which is harmless. The paper tier never runs in CI (book 14.1 says so). `test_bundle_failed_diagnostic` is the only test in the slice checking a real-TeX failure path.
- **Three copies of the conformance fixture** (`docs/specs/fixture/`, `loom/tests/fixture/`, `arras/tests/fixture/`) are identical today and all modified in the working tree; nothing on the unit tier asserts they agree. A cheap unit test comparing loom's copy to `docs/specs/fixture/` would catch a partial refresh before the TeX tier or arras e2e does.
