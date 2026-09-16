# Appendix A. Decision records

## Format

**[decided]** One record per decision, appended to this file, never edited afterwards (a reversal is a new record citing the old one). Fields: number, date, title, the principle(s) concerned, the decision in one or two sentences, the reason in one or two sentences, what it replaced if anything, and status (`active`, `superseded by N`). Records from the design conversations are dated by the day the conversation settled them; implementation-time records will be dated by merge.

## Records

DR-1 · 2026-09-15 · Adopt the block-based workflow of arXiv 2609.05669 §1.2 · P1, P5 · Decompose a paper into atomic units with tracked dependencies and review status, under a master recording order. · The source paper reports a threefold acceleration from exactly this. · active

DR-2 · 2026-09-15 · Source is LaTeX; no outer markup · P1 · Nodes are ordinary LaTeX; forester, Markdown, MyST, org, and Typst are rejected as source languages. · Mathematicians know LaTeX; the submitted `.tex` must be the written `.tex`; models are fluent in LaTeX. · active

DR-3 · 2026-09-15 · Forester as source considered and set aside · P1 · Forester's structure (addresses, transclusion, scoped macro modules) is better for a corpus; the per-paper tool is built first, in LaTeX. · No forester-to-LaTeX export exists; opam-only install; the corpus is deferred. · active

DR-4 · 2026-09-15 · The graph is defined by labels and environments, never by paths · P5 · One-file-per-node and regions-in-files are one specification. · Removes the need for a file format and lets the Stacks-style author keep one file. · active

DR-5 · 2026-09-15 · Transclusion is `\input`; no `\transclude` macro · P4 · The master compiles with plain `pdflatex`. · LaTeX already has transclusion. · superseded in part by DR-27 (`\nest` added for level shifting)

DR-6 · 2026-09-15 · Ids are `<prefix>-<local>`, prefix chosen by the author, sequential base-36 · P1 · Replaces random tags. · Forester and the Stacks project set the convention; the author chooses the prefix scheme. · active

DR-7 · 2026-09-15 · The ledger records acceptances only · P2, P3 · Reviews are files; states are computed; agents never write the ledger. · Prevents pollution by garbage runs; keeps decisions human. · active

DR-8 · 2026-09-15 · "Reviewed" is not a state · P3 · Reviews appear as facts and counts. · The word did two jobs and failed at both. · active

DR-9 · 2026-09-15 · Snapshots stored with acceptance rows · P2 · Content-addressed text of accepted keys and closures. · A stale acceptance must be explainable with a diff without git. · active

DR-10 · 2026-09-15 · One write path for annotations: `loom comment` · P4 · Agents and humans both use it; record files are never hand-written. · Loom owns the format end to end and computes anchors. · active

DR-11 · 2026-09-15 · Text-quote selectors relative to a region · P5 · Not file and line. · Anchors survive atomize, inline, and edits elsewhere. · active

DR-12 · 2026-09-15 · Runs are directories per chat thread, mode-free · P2 · Modes are applied inside runs; no run lifecycle. · A chat may cover several modes; restricting runs to one mode was prohibitive. · active

DR-13 · 2026-09-15 · Loom contains no model client; local models only · P8, P9 · Runner is an external local command; deferred. · No credentials, no hosted APIs. · active

DR-14 · 2026-09-15 · Digests in LaTeX as external nodes · P1, P4 · Replaces `map.toml` and `map.md`. · Reuses scanner, viewer, bundles; `\cite[postnote]` becomes an edge with no new syntax. · active

DR-15 · 2026-09-15 · Digest statements verbatim by default, macro-free or scoped · P1 · Expansion where mechanical, macro block otherwise; proofs never copied; sharing subject to licenses. · Verbatim is mathematically safer; paraphrase was solving licensing and notation, which are handled otherwise. · active

DR-16 · 2026-09-15 · `\uses` adopted from leanblueprint · P4 · No-op macro recording dependencies the text does not name; lint reconciles with `\ref`. · Some dependencies are only in prose; digests need internal trees. · active

DR-17 · 2026-09-15 · `\incomplete` rather than `\block` · P1 · Beamer defines `block`. · A talk in `drafts/` is a plausible master. · active

DR-18 · 2026-09-15 · Arras is a static Svelte bundle reading a build directory; loom is Python · P11 · No code shared; no server in the viewer; the write API is loom's. · Enforces separation by language and by artefact. · active

DR-19 · 2026-09-15 · Watching, not notification · P11 · Arras's only trigger is the manifest changing. · The viewer must not learn event kinds. · active

DR-20 · 2026-09-15 · Sections are nodes; nodes include nodes · P5 · Sectioning units are nodes; `sections/` is dropped; inclusion trees per master; own-text ownership. · Unifies masters, spines, sections; matches forester's model; the master view becomes "render expanded". · active

DR-21 · 2026-09-15 · Loom never modifies an author file · P7 · Destinations required; patches printed; `loom delete` refuses. · In-place rewriting destroys work. · active

DR-22 · 2026-09-15 · Directives use the `% !TEX` magic-comment family: `% !LOOM key: value` · P10 · Declarations only; never change output; regions as `begin`/`end`. · Established TeX convention; editors recognise it; `% !TEX program` and `root` honoured. · active

DR-23 · 2026-09-15 · Masters live in the masters directory; compile from the root · P12 · Every file with `\documentclass` there is a master; `config.toml` names the directory and the default. · Multiple masters without clutter; Overleaf-compatible. · active

DR-24 · 2026-09-15 · No loose-files directory · P5 · Loose is computed; `% !LOOM ignore` for archived drafts. · Naming the directory revealed it was a property. · active

DR-25 · 2026-09-15 · "id" for identity, "tag" for theme · vocabulary · Replaces "tag" as identifier. · Matches forester and sitegen; supports the zettelkasten use. · active

DR-26 · 2026-09-15 · Digest ids are `<citekey>-<paper's label>` · P1 · Distinct shape from author ids. · Cleanly separates provenance of nodes. · active

DR-27 · 2026-09-15 · `\nest{file}` for level shifting; no config flag · P4, P10 · Per inclusion site; `\input` or `\nest` as written. · A comment cannot change the PDF; a config default had nothing to decide. · active

DR-28 · 2026-09-16 · `loom.sty` vendored; `\usepackage{loom}` per master · P12 · Replaces preamble blocks. · Three macros in every master's preamble was duplication. · active

DR-29 · 2026-09-16 · Author name in user config, not quilt config · P2 · `~/.config/loom/config.toml`; fallback to git; refusal with instructions. · A committed config would attribute one person's acceptances to another. · active

DR-30 · 2026-09-16 · Diagnostics: reserved codes in the interface, publisher codes namespaced · P11 · Arras renders unknown codes generically. · Arras must not know what a proof is. · active

DR-31 · 2026-09-16 · Names: distribution `loomtex`, command `loom`, viewer `arras` · naming · `loom` on PyPI is abandoned; PEP 541 request in parallel. · active

DR-32 · 2026-09-16 · Licenses: GPL-3.0-or-later (loom), AGPL-3.0-or-later (arras), MIT (`loom.sty`, demo) · policy · Copyleft prevents proprietary appropriation without forbidding use; the package travels with papers. · active

DR-33 · 2026-09-16 · Command vocabulary consolidated · P4 · `deps`/`unravel` for the graph; `ai init|orient|start|discard|promote`; `digest extract|fetch|import`; `id` replaces `tag`; `delete` refuses. · Six graph commands were one question. · active

DR-34 · 2026-09-16 · Workspace repository tracks docs and specs; tool repositories separate; fixtures uncommitted · P11 · `loom-arras/` is a git repository ignoring `loom/`, `arras/`, `tests/fixtures/`. · The book and the interface need history; arXiv sources must not be redistributed. · active

DR-35 · 2026-09-16 · Overleaf compatibility is a contract · P12 · Portability rules; manual test per release; CI proxy. · The quilt is an ordinary LaTeX project. · active

DR-36 · 2026-09-16 · Vendor wrappers are generated pointer-only stubs · P4, 11.10 · Skill stubs and slash commands may be generated per mode but contain no mode content; the layer works with every stub deleted; `upgrade` never overwrites an edited mode file. · Two copies of a procedure drift; Codex has no stub mechanism. · active

DR-37 · 2026-09-16 · `bundle --with` and `bundle --draft` · P7, 11.5 · A bundle may be built with a proposed diff or a substitute file in place of a key's text, or for a not-yet-promoted node file, without touching the quilt. · Simplify, referee, and draft outputs must be compilable before a person promotes or applies them; otherwise verification happens after the only cheap moment for it. · active

DR-38 · 2026-09-16 · Mode files derived from the chat rules by an explicit mapping · 11.5 · `docs/source/global-rules.md` holds the chat rules verbatim and `global-rules-mapping.md` maps each part to its loom destination; the four environmental differences (inputs by command, outputs as files, findings as annotations, code and compilation available) drive every adaptation. · Provenance: an edit to a mode can be traced to the rule it came from. · active


DR-39 · 2026-09-15 · The 10.8 forbidden-word list exempts "digest" and "proof" · P11, 10.8 · Arras's source may use the manifest's own field names (`proofs`, `digest`, `kind: proof`) and the spec's route `/digest/`; the guard test forbids "quilt", "atomize", "unravel", and every "loom <command>" phrase, and generic rendering of unknown labels, codes, and taxa stays enforced by tests. · The manifest specification and the route list name those words, and the Web Crypto API has `digest()`, so the rule as written could not be satisfied. · active
