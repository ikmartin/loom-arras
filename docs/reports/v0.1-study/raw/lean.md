# Lean formalization skills in loom (v0.1 study, raw)

Auditor: Lean. Studied: the skills repository at commit `1837b95` (2026-10-25), cloned read-only into scratch and never run; loom at `71621877` (branch v0.1-study). Paths prefixed `skills/` are in the skills checkout (`skills/skills/<name>/...` there is written `<name>/...` here); unprefixed paths are in the loom repository. Web facts are from generic searches and are listed under Sources, marked where unverified.

The lead's scope change (formalization is to be built in v0.1) is answered in section 7, a build specification. Sections 1–6 answer the original questions; section 6's "worth doing before the pilot" question is superseded by section 7.

## Headline findings

- **LEAN-1. The skills' central safety gate is a human reading Lean.** The orchestrator requires the author to see "the complete exact declaration: imports, explicit/implicit/instance binders, result" and says "Approval of a topic or prose summary is not approval of unseen Lean code" (`lean-orchestrator/SKILL.md:99-101`). The author's premise is that mathematicians do not read Lean. Loom's job in this pairing is exactly to make that approval possible for someone who does not read Lean, and to say honestly that it was given from a rendering (section 3).
- **LEAN-2. The philosophies already agree.** The skills keep "source topology separate from evidence that Lean results are proved" (`skills/README.md:177-178`), make `PROVED` a two-key result (`lean-orchestrator/SKILL.md:231-235`), and say "Compilation is not a fidelity verdict" (`:183`); loom keeps acceptance and annotations apart (`docs/design/model.md:47`) and holds that nothing unchecked looks checked (`docs/design/principles.md:137-139`). Neither has a third key: a person attesting that the formal statement is the theorem in the paper, recorded so an agent cannot forge it. The skills record approval as a JSON field any agent can write (`lean-orchestrator/assets/frozen-anchor-manifest.template.json:8-13`); loom already refuses agents the author's acts (`docs/design/agents.md:36-55`, `loom/src/loom/cli/_common.py:325`). That refusal is loom's contribution.
- **LEAN-3. Loom already detects the drift the skills cannot.** A frozen anchor pins its source as `"range": "paper.tex:100-120"` at a revision (`frozen-anchor-manifest.template.json:15-18`); when the author edits the paper nothing in the skills notices. Loom pins by key and text hash and computes staleness with causes (`loom/src/loom/records/store.py:286-418`), so loom is the right home for "this stamp no longer describes your current statement".
- **LEAN-4. A Lake project inside a quilt today costs every scan and every second of `loom serve`.** The scanner walks the whole tree with `rglob` and filters afterwards, skipping only `.git`, `node_modules`, `.loom`, `.svelte-kit`, `.claude` (`loom/src/loom/scan/source.py:16,28`); the watcher's `os.walk`, polled every second, prunes `.git`, `node_modules`, `.svelte-kit` but not `.lake` (`loom/src/loom/render/watch.py:41,54-63`). Mathlib's `.lake` holds tens of thousands of files (a full cache is about 5 GB, unverified for late 2026). Any `.tex` under `.lake` would also be scanned as quilt source. Fix: hours.
- **LEAN-5. "Stamp" is already a loom word.** `loom stamp DOC -m NAME` records a step and a landmark (`docs/design/model.md:25,41`); K7 forbids a second meaning. "Verified" is taken too (`loom library verify`, P15 wording). This report says "formal stamp" for the study only; the shipped name should be something like **formalized** for the state and **attest the match** for the act.
- **LEAN-6. The skills were built on a Linux workstation with a capable account.** The compile gate replaces the toolchain's `lean` binary and uses `flock` slots under `/run` (`lean-orchestrator/assets/lean-compile-gate.sh:10-13,22,52-53`); shared builds need overlayfs, "normally root" (`lean-orchestrator/references/machine-resources.md:63-68`); the performance report uses GNU `/usr/bin/time -v` and `rm -rf` on build trees (`lean-elaboration-test/SKILL.md:71-77`), and loom's generated Claude Code settings deny `Bash(rm *)` (`loom/src/loom/ai/layout.py:189`). The suggested orchestrator models are Fable 5.1 or Opus 5.5 with Sonnet workers and native subagents (`skills/README.md:125-129,180-186`). A pilot on a Mac with a Pro-tier account meets the single-lemma path fine and the multi-agent campaign path poorly.

## 1. What the skills do

| skill | purpose | inputs | writes | helpers | assumes |
|---|---|---|---|---|---|
| `lean-workflow` | router; Lake/Mathlib hygiene (`SKILL.md:8-19,21-28`) | repo's AGENTS.md/CLAUDE.md, lakefile, toolchain (`:32`) | edits; report of commands, placeholders, mismatches (`:38`) | none | Lake + Mathlib project; never `lake clean`/update pins (`:26`); `#print axioms` from an untracked probe (`:37`) |
| `lean-project-architecture` | choose the small "constitutional surface", freeze exact declarations, module layout (`SKILL.md:12-40`) | pinned source, errata, author rulings | one-declaration frozen files, manifest entries (`:35-36`) | `scripts/check_lean_modules.py` (reads git index, `:133-138`) | module-system toolchain where adopted; git |
| `build-proof-dependency-graph` | source-level proof dependency database anchored to frozen declarations (`SKILL.md:6-11`) | source corpus (LaTeX/Markdown, line-addressable), frozen files + manifest only (`:15-18`) | `DEPGRAPH.md`, `DEPGRAPH_COVERAGE.md`, generated dashboard (`:52-57,287-309`) | `scripts/proof_depgraph.py` (1,043 lines; "never reads Lean files", `:1-7`); templates; `references/agent-packets.md` | parallel extractor subagents, one writer, fresh reviewers (`:156-182,250-283`); frozen anchors exist first (`:63-114`) |
| `lean-orchestrator` | run a multi-agent campaign: freeze, graph, bounded proof tasks, seal, audit, land (`SKILL.md:1-13`) | plan, ledgers, manifest, graph | frozen files, provider modules, status reports with fixed fields (`:239-244`), errata ledger then `docs/ERRATA-AND-DEVIATIONS.md` (`:273-282`) | `scripts/check_frozen_anchors.py` (no accept/rebaseline command, `:1-5`), `assets/lean-compile-gate.sh`, manifest template, three references | subagents/worktrees, git, Linux machine resources (LEAN-6), Comparator for landing guards (`references/landing-guards.md:73-88`) |
| `lean-statement-audit` | fail-closed audit of one frozen declaration against its pinned source (`SKILL.md:6-15`) | manifest entry, raw source statement (not its proof), rulings (`:35-66`) | audit report: five-bin binder table (`:73-98`), definition verdict lines (`:154-161`), draft verdicts (`:217-223`), status (`:231-240`) | none (transient Lean probes) | an auditor independent of the declaration's author (`:68-69`); Lean to compile probes |
| `lean-search-discovery` | find Mathlib declarations before proving (`SKILL.md:8`) | the goal | nothing | references only | local Mathlib checkout; optional Loogle/LeanSearch online (`:44-46`) |
| `lean-proof-patterns` | translate informal steps into maintainable tactics; statement hygiene (`SKILL.md:10-90`) | proof text | Lean proofs | references only (MIT-adapted `math-to-lean.md`) | a building project |
| `lean-naming-style` | Mathlib naming and file conventions (`SKILL.md:10-57`) | code | renames | references only | none |
| `lean-learnings` | analysis/PDE/probability lessons, carriers (`SKILL.md:8-44`) | situation | nothing | five references | Mathlib analysis |
| `lean-elaboration` | measured elaboration performance repair (`SKILL.md:17-75`) | profiles | A/B'd edits | `references/evidence.md` | `lean --profile`; repeated builds |
| `lean-elaboration-test` | dated repo-wide elaboration snapshot (`SKILL.md:6-17`) | repo at a commit | `ELABORATION_REPORT_<date>.md` (`:151`) | `scripts/count_lean_lines.py` (git ls-tree) | GNU time, `rm -rf` of project build trees (`:71-77`) |
| `lean-public-release` | scrub and publish a formalization repo (`SKILL.md:8-12`) | private repo | public tree, README, CI workflows, errata doc (`:116-195`) | none | GitHub CI, Comparator with bubblewrap (`:177-187`) |

Collection-wide: Python 3.10+ for helpers (`skills/README.md:22-26`); a Lean/Lake project with its declared toolchain; installation by symlinking whole folders into `~/.claude/skills` or `~/.agents/skills`, or `--project` into `.claude/skills`/`.agents/skills` (`skills/README.md:69-87`, `scripts/install_skills.py:47-51`); tmux optional (`:131-136`); experimental agent teams optional (`:209-224`). No skill writes a "progress record" template; durable handoffs are asked for in prose (`skills/README.md:194-196`, `lean-orchestrator/SKILL.md:298`).

**The workflow in ten lines.**

1. Pin the source and its errata; choose a small surface of main theorems, gates and the definitions that change their meaning.
2. Transcribe each target's premises, quantifier order, conclusion and constant scope from the source; search Mathlib.
3. Write the exact final Lean declaration; elaborate it in a transient, untracked file.
4. An independent agent audits it against the source: five-bin binder table, definition body and carrier, axioms.
5. The author approves the exact Lean command; it is frozen in a one-declaration file with body `by sorry`, manifest state `DRAFT_SORRY`, hashes, provider and quarantine.
6. Extract the source dependency graph (parallel extractors, one writer), with coverage manifest, `SOURCE_GAP` nodes and alternative routes; fresh reviewers try to refute it; the linter passes.
7. The orchestrator assigns bounded proof tasks from the dependency-ready frontier; workers write provider modules below the anchors.
8. Seal: replace `by sorry` with `by exact Provider.result`; compile, `#print axioms`, kernel replay, landing guards.
9. A fresh auditor re-audits; `PROVED` needs both keys; status reports and the errata ledger are kept.
10. Release: scrub, fresh-checkout build, CI, errata document, optional Comparator challenges.

## 2. Same idea, or two sources of truth

| skills artifact | loom counterpart | verdict |
|---|---|---|
| `DEPGRAPH.md` nodes, `DEPS`, `ROUTES` (`build-proof-dependency-graph/assets/DEPGRAPH.template.md:35-64`) | nodes and edges read from `\ref`, `\uses`, `\cite[...]` (`docs/specs/source-contract.md:103-116`) | Same idea, two truths if hand-kept (LEAN-7) |
| `KIND: external`, `assumption`, `SOURCE_GAP:` | digest nodes (`cited-result`), basis `assumption`, `\incomplete` (`source-contract.md:30-44`) | Same idea |
| route nodes, "one route may suffice" (`build-proof-dependency-graph/SKILL.md:208-213`) | several proofs per statement, `S/proof/2` (`source-contract.md:101`); `proved` needs any one accepted proof (`store.py:490-497`) | Same idea |
| step nodes `parent#slug` (`build-proof-dependency-graph/SKILL.md:130-133,191-196`) | none below environment level; a theorem-like environment inside a proof is an edge (`source-contract.md:110`) | Loom is coarser (LEAN-8) |
| coverage manifest of every environment, display, citation (`:143-154`) | the scan's node list; diagnostics for unlabelled and unclassified blocks | Loom can generate it |
| `lean-statement-audit` verdicts, `REVIEWER` fields | an agent's report and annotations; never acceptance | Agent claims (LEAN-9) |
| author approval in the manifest (`frozen-anchor-manifest.template.json:8-13`) | `loom accept`, refused to agents (`docs/design/agents.md:40,51`) | Loom gives it teeth (LEAN-2) |
| frozen declaration + `source.range` + `abi_sha256` (`:15-18,31`) | key, `rl-0004@3` versions (`loom/src/loom/history/versions.py:1`), text and closure hashes (`loom/src/loom/records/ledger.py:18-29`) | Complementary (LEAN-3) |
| `LEAN_STATUS` field written into the graph (`DEPGRAPH.template.md:60`) | states computed, never stored (P3, `principles.md:89-91`) | Do not import (LEAN-10) |
| status reports, handoffs, errata ledger (`lean-orchestrator/SKILL.md:239-244,273-282,298`) | session transcript (`loom session say`, `model.md:132`), session files, annotations | Map onto loom records (LEAN-11) |

- **LEAN-7. One graph, seeded by loom.** The skills prefer source labels as node IDs (`build-proof-dependency-graph/SKILL.md:130-133`) and a locator `path#anchor@Lx-Ly` (`build-proof-dependency-graph/scripts/proof_depgraph.py:25-26`); loom ids are labels and loom knows each node's file and offsets. Loom can therefore emit a `DEPGRAPH.md` skeleton (ids, kinds, locators, statement and proof edges, digest nodes as `external`, `CORPUS` a landmark, Lean fields initialised) for the skill's review phases to refine. A dependency the reviewers find that the text does not name goes back to the author as a suggested `\uses` edit (`loom suggest`), so the author's source remains the one graph (P1, P4). Step nodes stay Lean-side planning unless the author labels them as `claim` environments.
- **LEAN-8. Digests cannot seed proof graphs of cited papers.** Digests copy statements only; "Proofs are never copied" (`docs/specs/digests.md:46`). Formalizing a cited result from its proof needs the work's LaTeX in the store (`digests.md:118`), not its digest.
- **LEAN-9. Independence is declared, never checked, in both systems.** The linter only checks that reviewer strings differ (`build-proof-dependency-graph/SKILL.md:280-283`). Over MCP every subagent of one Claude Code session writes to loom under the one server name, "Claude Code Agent" (`docs/design/agents.md:73-80`). Loom should record and show who declared the audit, and never present "independently audited" as checked.
- **LEAN-10. `LEAN_STATUS` and `PROVED` are stored states.** Brought into loom they would be a second truth that can disagree with the Lean project (P3). Loom should compute a formal state from evidence and attestation records.
- **LEAN-11. Handoffs map onto existing records.** Status reports go in the transcript; scripts, audit reports and build logs in the session directory (`docs/design/agents.md:17`); each erratum is an annotation of the quilt's revision type on the digest node or the author's key (it is "a public claim that named authors made an error", `lean-orchestrator/references/errata-and-deviations.md:31-32`, so it stays an annotation until the person decides).

## 3. The crux: a stamp that never overstates

A Lean build certifies the formal statement. Three separate claims stand between that and "this lemma is formalized": the build and its axioms (machine, but run by an agent), the statement audit (an agent's judgment), and the match (a person's judgment). Loom must keep all three visible and let only the third be a person's act.

**The evidence record** (written by an agent or a person through one command, append-only, P4):

| field | example | why |
|---|---|---|
| `id` | `f-2026-11-20-k2m9xq` | random token, as annotations (`model.md:158`) |
| `key`, `key_hash`, `step` | `rl-0012`, `sha256:…`, `@7` | the informal statement it formalizes, as loom hashes it (`source-contract.md:122`) |
| `closure` | `{rl-0003: sha256:…}` | statement closure only (definitions the statement uses), as `AcceptRow.closure` (`loom/src/loom/records/ledger.py:25`); proof text is irrelevant to a formal stamp |
| `preamble` | `sha256:…` | macros change meaning |
| `decl`, `kind` | `Paper.lemma_3_2`, theorem | Lean name |
| `project`, `file` | `lean/`, `lean/Paper/Frozen/Lemma32.lean` | where |
| `statement_hash`, `statement_text` | hash and text of the declaration's statement region, read by loom from the file | the exact formal statement attested; loom reads, never runs |
| `commit`, `clean` | git SHA, working tree clean | reproducibility |
| `toolchain`, `manifest_hash`, `mathlib` | contents of `lean-toolchain`, hash of `lake-manifest.json`, Mathlib rev | pins, read by loom |
| `status` | `statement` / `proved` | `statement` before freezing or while `by sorry` |
| `axioms` | `[propext, Classical.choice, Quot.sound]` | verbatim `#print axioms` output; `sorryAx` or anything else is never `proved` without a named trust boundary |
| `replay` | `leanchecker` / `none` | an axiom report is not a kernel check (`lean-orchestrator/references/landing-guards.md:9-21`) |
| `audit` | `{by, verdict, bins: {SOURCE, STANDING, TYPING, RULED, EXCESS}, report}` | the five-bin result (`lean-statement-audit/SKILL.md:73-98`), report path in the session directory |
| `mapping` | each Lean hypothesis beside the source premise it renders | what the person reads instead of Lean |
| `gloss` | the formal statement in mathematical prose | likewise; labelled as the agent's reading |
| `by`, `when` | `Claude Code Agent`, time | P15 |

**The attestation** (the person's act, author-only like `loom accept`): `key`, `key_hash`, `closure`, `preamble`, the `statement_hash` attested, the evidence `id` it was given from, `author`, `date`, and `from`: `lean` (they read the Lean) or `rendering` (they read the mapping and gloss). Attestation is per person, as acceptance is (`model.md:59`).

**Computed state** (P3), one axis beside acceptance, never feeding `accepted`, `proved` or `settled` in v0.1:

- `formal statement proposed`: evidence with `status: statement`, no attestation of that statement hash.
- `statement attested, unproved`: attested, latest evidence still `statement` (the skills' `FROZEN_UNPROVED`).
- `formalized`: attested statement hash equals the latest `proved` evidence's statement hash, axioms within the standard three, nothing below stale.
- `formalized, conditional`: as above with a named extra axiom or trust boundary, shown by name.
- `formalized, stale` with causes: `own-text-changed`, `dependency-changed` (a definition in the statement closure), `preamble-changed`, `declaration-changed` (the file's statement region no longer hashes to what was attested, read on every query), `evidence-gone` (commit missing). A Mathlib or toolchain bump is shown as "evidence at older pins", not stale; a failed rebuild is new evidence.

**What the person sees.** A badge part on the node only when the state is `formalized`, worded with who checked what, for example "Lean: proved (reported by Claude Code Agent); match attested by you". Unattested evidence never draws a badge part; it appears as a card in Review › Proposed Changes. The card and the node's panel show the informal statement as rendered at the attested version (with the diff when stale) beside the Lean statement, the hypothesis-by-hypothesis mapping with any `EXCESS` row in red, the gloss, Lean's conventions that differ from the paper's (`x / 0 = 0`, truncated subtraction, as `lean-orchestrator/references/errata-and-deviations.md:19-22` lists them), and folded pins, axioms and audit report. One act: **Attest the match**; the alternative is an annotation ("not the theorem: …") that reaches the agent through `loom since`.

**What loom lacks for this** (each built in section 7): a record kind and command for evidence; an author act and its ledger; a computed formal state and its causes; manifest fields and a viewer surface; a reader for a declaration's statement region in a `.lean` file; knowledge of Lake projects; `.lake` pruning (LEAN-4). It also lacks any way to rerun Lean itself, and should keep lacking it in v0.1 (LEAN-12).

- **LEAN-12. Loom should not run Lean in v0.1.** Building a Lean project executes arbitrary code at elaboration time (`run_cmd`, macros, `initialize`; the landing guards exist because of this, `landing-guards.md:23-44`). Running agent-written Lean under loom's identity would breach the invariant that loom never opens a file that runs code (`docs/design/agents.md:53`) and the deferral of running code (`docs/design/README.md:62`). The agent runs builds under the person's own permission prompts; loom records, reads files and checks git.
- **LEAN-13. A stamp on a digest node chains through the transcription.** For a cited result the chain is Lean ⇒ formal statement, person ⇒ formal ≡ loom's copy, and loom's copy ≡ the paper only if `transcription verified` (`docs/specs/digests.md:89-98`, `arras/src/lib/badges.ts:18-25`). The panel must show both links.

## 4. Skills as modes, and licences

Loom's mode mechanism: a fixed list `MODES` in code, and a file in a quilt's `.loom/ai/modes/` whose name is not listed "is not a mode" (`loom/src/loom/ai/layout.py:17-18`); each mode is one Markdown file (`loom/src/loom/ai/orient.py:98-105`); its MCP prompt takes one word of target (`loom/src/loom/mcp/prompts.py:12-13,24-30`). A mode carries no scripts, templates or references. The design says "Nothing is shaped for one vendor's skill or command files" (`docs/design/agents.md:116`).

| skill | as a loom mode? |
|---|---|
| `lean-statement-audit` | Cleanest fit: one file, no scripts, a report with fixed blocks like loom's `audit` mode (`loom/src/loom/assets/ai/modes/audit.md`). Still needs Lean for its probes. |
| `lean-workflow` | Its routing role is what a loom `formalize` mode does; its Lake hygiene is Lean craft. |
| `build-proof-dependency-graph` | No: 1,043-line linter, templates, packet specs; and loom should seed it (LEAN-7). |
| `lean-orchestrator`, `lean-project-architecture` | No: scripts, templates, references, subagents. |
| search, proof patterns, naming, learnings | No: Lean craft in large references (380–473 lines each); loom adds nothing. |
| elaboration, elaboration-test, public-release | Out of scope for loom. |

- **LEAN-14. One loom mode plus the skills as skills.** Ship one mode, `formalize`, holding only what is loom's: orient, find the key's closure, find or create the Lean project, use the skills for the Lean work, file evidence with loom's command, never attest, report in the transcript. Install the twelve skills unmodified as skills for the clients that read `SKILL.md` (Claude Code `.claude/skills/`, Codex `.agents/skills/`, `skills/README.md:69-82`); the mode names their vendor-neutral copy so an agent of another app can read them as files. This is a deliberate, stated exception to `agents.md:116`, justified because the format is shared by both main clients.
- **LEAN-15. Licences.** Loom is GPL-3.0-or-later (`LICENSE`, `loom/pyproject.toml:7-8`). The skills' original parts are CC BY 4.0 (`skills/README.md:363-370`), which the FSF lists as compatible with GPLv3; adapted MIT material sits in three references (`skills/THIRD_PARTY_NOTICES.md:9-16`) and Apache-2.0-derived material is cited (`:42-50`). Vendoring requires: the attribution line the README suggests, the copyright and licence notices and a link to the licence, retaining the disclaimer, and saying if and how it was changed; the MIT notice kept with the MIT-adapted files; the Apache licence text and change notices with Apache-derived parts. Vendoring unmodified, pinned to a commit, with `LICENSE`, `LICENSES/`, `THIRD_PARTY_NOTICES.md` and `PROVENANCE.md` copied beside, and a line in `loom/NOTICE`, discharges all of it; loom's own glue lives in the `formalize` mode, which is loom's text. Adapting skill text into a mode instead adds the "indicate changes" duty and forks the collaborator's maintained source. Not legal advice; the author should confirm with the collaborator, who is the licensor.

## 5. Where the Lean project lives

Recommended: a Lake project in a subdirectory of the quilt (for example `lean/`), committed with the quilt, its `.lake/` gitignored. Coauthors get it in the same clone; one commit pins both texts; loom reads `lean-toolchain` and `lake-manifest.json` for pins; the viewer shows `.lean` files as text in Files, since only dot-directories are hidden (`loom/src/loom/files.py:173,196-204`). Alternatives: a sibling repository (does not travel with a clone; the record must carry a remote and commit), a submodule (pins but adds git friction a pilot will not want), or the quilt inside a Lean repository as a blueprint (natural for formalization-first projects; loom's `\uses` already means what leanblueprint's does, while its hand-written `\leanok` is a stored claim loom should not read as a state).

What loom must know: each project's root (found by its `lakefile.lean`/`lakefile.toml` and `lean-toolchain`, computed rather than configured, P6), its toolchain and Mathlib pins, the git commit and cleanliness at which evidence was produced, and the file and declaration each stamp names. It must not need the build command, which is the agent's. Prerequisite: LEAN-4's pruning, and Claude Code's `Bash(rm *)` deny (`layout.py:189`) left as it is; the skills' `rm -rf` steps are only in the performance skill.

## 6. Three sizes (original question)

- **(a) Smallest seam, hours.** Prune `.lake` (LEAN-4); let an agent record evidence as an annotation of a quilt-local type with the fields of section 3. Gains: evidence attached to the lemma, attributed, with no state. Costs: nothing for a pilot who never touches Lean, provided the type is not shipped by default.
- **(b) First real integration, days.** Evidence record, attestation, computed formal state, viewer badge and Proposed Changes card, the `formalize` mode, vendored skills. Section 7's smallest cut.
- **(c) The full workflow, weeks.** Graph hand-off, frozen-anchor manifest bound to loom attestations, a declaration directive, stale stamps in Your Changes, stamps on digest nodes from Mathlib, loom-side kernel replay or Comparator once running code is decided, campaign status in the viewer.

The lead has settled the question of timing: formalization is to be implemented in v0.1. Section 7 specifies it.

## 7. Build specification

### A. Requirements

| # | what | where (existing code extended) | effort | depends on |
|---|---|---|---|---|
| R1 | Prune `.lake` (and any `lakefile`-rooted build dir) from the scan and the watcher; walk with pruning instead of `rglob` | `loom/src/loom/scan/source.py:16,28`; `loom/src/loom/render/watch.py:41,54-63` | hours | none |
| R2 | Find Lake projects and their pins; `loom doctor` reports a missing `elan`/`lake` with the official install line, and a project's toolchain and Mathlib rev | new `loom/src/loom/formal/projects.py`; `loom/src/loom/doctor.py` | hours | R1 |
| R3 | Evidence record: `loom formal record KEY --decl NAME --file PATH --status statement\|proved --axioms … --replay … --audit PATH --gloss - --mapping FILE --as NAME`, appending to `.loom/formal/evidence.jsonl`; loom reads the statement region (between the skills' frozen-file markers `FROZEN_ANCHOR_PREFIX_BEGIN`…`PROOF_BEGIN`, `lean-orchestrator/scripts/check_frozen_anchors.py:18-20`, else up to the declaration's `:=`), hashes it, reads pins, checks the commit exists and the declaration is in the file at it; refuses `proved` with `sorryAx` or unnamed extra axioms | new `loom/src/loom/records/formal.py` modelled on `records/edits.py`; constant in `loom/src/loom/paths.py:46-50`; command in a new `loom/src/loom/cli/formal.py` | days (2) | R2 |
| R4 | Agent command and MCP tool: add `formal record` to `AGENT_COMMANDS` and `ACTS` as `write`; the tool `loom_formal_record` then follows, as do the Claude Code and Codex allow rules; regenerate `loom/docs/mcp-tools.json` | `loom/src/loom/ai/layout.py:21-38,51-57`; `loom/src/loom/mcp/tools.py:97-101` | hours | R3 |
| R5 | Attestation: `loom formal attest KEY [--evidence ID] [--from lean\|rendering]`, refused to agents by the same guard as `loom accept` (`loom/src/loom/cli/review.py:186-188`, `loom/src/loom/cli/_common.py:325`); its own append-only ledger `.loom/formal/attest.toml` (P4 keeps `.loom/state.toml` to `loom accept`, `records/ledger.py:1-3`); write endpoint `formal-attest`, author-only like `review-accept` | `loom/src/loom/render/api.py:22-70,933`; `docs/specs/write-api.md:85` | a day | R3 |
| R6 | Computed formal state and causes, reusing the acceptance machinery (`closure_hashes`, `same_mathematics`, preamble hash) plus `declaration-changed` read from the file on each query; `loom status` counts; `loom since` reports new evidence, attestations and stale stamps to agents | `loom/src/loom/records/store.py:286-418`; `loom/src/loom/cli/review.py` (status); `loom/src/loom/since.py:169` | days (2) | R3, R5 |
| R7 | Manifest: `keys[K].formal` with state, causes, evidence and attestation summaries, and a `formal` list of proposals | `loom/src/loom/render/manifest.py`; `docs/specs/manifest.md:155-191` | a day | R6 |
| R8 | Viewer: a badge part only for `formalized` (`arras/src/lib/badges.ts:21-30`); a Proposed Changes card kind `formal` (`arras/src/lib/review/proposed.ts:5-8`, `ProposalCard.svelte`, `ProposalQueue.svelte`) with informal beside formal, mapping, gloss, folded pins and audit, and **Attest the match**; the same panel from the node; an "Ask for a Lean check" button that files the person's annotation, as `AskAgent.svelte` does for overviews | `arras/src/lib/components/AskAgent.svelte`, `arras/src/lib/review/ask.ts`; new `FormalPanel.svelte` | days (3) | R7, R5 |
| R9 | The `formalize` mode and its prompt `/loom:formalize KEY` | `loom/src/loom/assets/ai/modes/formalize.md`; `MODES` in `layout.py:18`; `prompts.py:24-30` picks it up | hours–a day | R4 |
| R10 | Skills vendored unmodified at a pinned commit with their licences, written into `.claude/skills/` and `.agents/skills/` (and a vendor-neutral copy the mode names) when the person turns formalization on (Settings, or `loom ai init --formal`); refreshed by `loom upgrade` with the same edited-file rule as modes | `loom/src/loom/assets/lean-skills/`; `layout.py:274-298,301-374`; `loom/src/loom/cli/ai.py:220-236`; `loom/NOTICE` | a day | R9 |
| R11 | Graph hand-off: `loom formal graph KEY…` prints a `DEPGRAPH.md` skeleton and coverage manifest that pass the skills' linter structurally (ids, kinds, `path#id@Lx-Ly` locators, edges with use-site locators, digest nodes `external`, `CORPUS` a landmark, Lean fields initialised); tested by running the vendored `proof_depgraph.py` in loom's tests | `loom/src/loom/cli/graph.py:146,308`; `loom/src/loom/cli/build_cmds.py:633` | a day | R10 |
| R12 | Optional declaration directive `% !LOOM lean: Name` (author data, P10), so the correspondence is visible in the source and survives a lost record | `loom/src/loom/scan/directives.py:13-31` | hours | R6 |
| R13 | Design and spec: a "Formal stamps" section in `docs/design/model.md`, the act in `docs/design/agents.md:36-49`, a new `docs/specs/formal.md`, diagnostics codes, the name (LEAN-5) | docs | a day | R3–R8 |
| R14 | Real-client trial on a Mac with Lean installed, over MCP and shell, Claude Code and Codex, as the client tier requires (`docs/design/agents.md:85`) | — | a day plus setup (B) | all above |

Review's place: the skills' statement seal, the author approving the exact declaration before it is frozen, is the Proposed Changes card (R8). After the person attests, the agent freezes the file and may record the attestation's id as the manifest's `approval_ref` (`frozen-anchor-manifest.template.json:12`), so the skills' approval record points at loom's. When the proof later lands with the same statement hash, the state turns `formalized` with no second act. A changed statement goes back to Proposed Changes. Stale formal stamps belong in Your Changes' To do in the fuller version.

### B. What a pilot's machine and account need

| need | detail | who can do it |
|---|---|---|
| Lean toolchain | `elan` via `curl https://elan.lean-lang.org/elan-init.sh -sSf \| sh`, then `source $HOME/.elan/env`; needs `git` and `curl` (official manual) | the agent, on the person's approval of a download-and-run command; macOS may pop the Xcode Command Line Tools dialog for `git`, a click |
| Lake project with Mathlib | `lake +leanprover-community/mathlib4:lean-toolchain new NAME math`, then `lake exe cache get` | the agent; first run waits on the Mathlib download |
| Disk | full Mathlib cache about 5.1 GB to download (Jan 2025), build artifacts about 4.3 GB per project (2024); expect 6–10 GB per project in late 2026 (unverified); the Mathlib wiki describes one shared Mathlib for tight disks | nobody can make this smaller per project in v0.1 |
| Time | download minutes to tens of minutes depending on bandwidth (unverified); a new project's first `lake build` of its own files is short when the cache hit | the agent waits; the person must keep the machine awake |
| Memory | each Lean compile 1–2 GB (`lean-orchestrator/assets/lean-compile-gate.sh:5-6`); 16 GB is comfortable for one agent, tight for several parallel workers (estimate) | — |
| Multiplexer, long sessions | tmux optional (`skills/README.md:131-136`); a lemma is one long agent session, a campaign is many over days | the person's app; no tmux needed for one lemma |
| Agent app and models | Claude Code with native subagents is the documented path; suggested orchestrators Fable 5.1 or Opus 5.5, Sonnet workers (`skills/README.md:125-129,180-186`). Codex reads the skills too but delegation is "your available delegation mechanism" (`:205-207`), and its default sandbox may block the network that `lake exe cache get` needs (unverified) | the person chooses; an independent auditor on Codex may need a second session the person starts |
| Python 3.10+ | for the skills' helpers (`skills/README.md:22-23`) | present on most Macs with developer tools |
| Agent cost per lemma | reported 2026 runs: 111 kernel-checked lemmas in 10 days for $200 under one supervising mathematician; larger API-billed projects $6,300–$15,000 (secondary reports, unverified). For one research-paper lemma whose definitions Mathlib already has: an estimated 1–6 hours of agent time across statement, audit, proof and re-audit, from a few to tens of dollars; if Mathlib lacks a definition the lemma needs, days, or a definition the person must also attest | estimate, unverified |

The bar "no human types a loom command" can be met: every loom step is a viewer control or an agent tool. The bar "no human types any command" cannot be fully met: the person must approve the agent's install and download commands in their app, may click through the Xcode tools dialog, and must have the disk and a model tier able to run long sessions. `loom doctor` (R2) should say what is missing and that the agent can install it; loom itself should install nothing (LEAN-12's reasoning applies to fetching and running installers too).

### C. The person's journey: one lemma stamped while proofreading

1. **Person, viewer:** opens Lemma 3.2 (`rl-0012`) and presses "Ask for a Lean check", which files their annotation on the key. *(not built: R8)*
2. **Person, agent app:** types `/loom:formalize rl-0012`, or says "check loom". *(prompt mechanism exists; mode not built: R9)*
3. **Agent:** `loom_ai_orient`, `loom_since`, `loom_source rl-0012 --closure`. *(exists)*
4. **Agent:** finds no `lake`; asks to install elan; **person** approves; macOS may show the Xcode tools dialog, **person** clicks. *(agent capability; `loom doctor` hint not built: R2)*
5. **Agent:** creates `lean/` with Mathlib and fetches the cache; **person** approves the commands and waits. *(agent capability; `.lake` pruning not built: R1)*
6. **Agent:** with `lean-workflow`, search and architecture skills, writes the exact declaration of the lemma and of any definition it needs; elaborates it transiently. *(skills installed by loom not built: R10)*
7. **Agent (fresh subagent):** `lean-statement-audit`; writes the five-bin table, mapping and gloss into the session directory. *(skills)*
8. **Agent:** `loom_formal_record rl-0012 --status statement …`. *(not built: R3, R4)*
9. **Loom:** a card appears in Review › Proposed Changes. *(not built: R6–R8)*
10. **Person, viewer:** reads the lemma beside the Lean statement and the mapping; presses **Attest the match**, or annotates why it is not the lemma. *(not built: R5, R8)*
11. **Agent:** learns of it from `loom_since`; freezes the file with `by sorry`, the manifest naming the attestation. *(since line not built: R6)*
12. **Agent and subagents:** prove below the anchor, build, `#print axioms`, replay, seal, re-audit. *(skills)*
13. **Agent:** `loom_formal_record rl-0012 --status proved --axioms …`; writes a transcript summary with `loom_session_say`. *(record not built; transcript exists)*
14. **Loom:** computes `formalized`; the lemma's badge shows who checked what. *(not built: R6–R8)*
15. **Later, person:** edits the lemma's hypothesis; the badge reads stale with cause `own-text-changed`; `loom since` tells the next agent. *(not built: R6)*

### D. The cut line

**Smallest truthful "formalization supported in v0.1":** R1, R2 (doctor line only), R3, R4, R5, R6 (without `since`), R7, R8 (badge, Proposed Changes card with Attest, node panel; no Ask button), R9, R10, R13, R14. No graph hand-off, no directive. About **9–11 working days** for one person by these estimates, perhaps 5–7 with heavy agent assistance, plus a Lean install for testing (F). In a two-week schedule whose other work is Review, speed, library import, and install and first-run clarity, it displaces roughly half of that schedule: library import and the speed work are the natural casualties, and it competes directly with install clarity, since Lean adds a second, heavier install to explain. R8 touches Review's Proposed Changes, so it should be planned with the Review work, not beside it.

**Fuller version (another 1–2 weeks):** R11 graph hand-off, R12 directive, R6's `since` lines, the Ask button, stale stamps in Your Changes' To do, stamps on digest nodes that point at Mathlib declarations, a Codex trial, doctor guidance for every missing piece.

**Waits:** loom rerunning Lean or Comparator (blocked on deciding to run code, LEAN-12); campaign dashboards (draft anchors, frontier); worker orchestration and machine-resource gating (Linux-specific, LEAN-6); errata turned into annotations automatically; formal stamps counting toward `settled`; elaboration and release skills.

### E. Risks specific to this pairing

- **A stamp that overstates.** Extra or bundled hypotheses, a weaker conclusion, a changed quantifier order, Lean's total-function conventions, `sorry`, added axioms, a kernel-check bypass (`landing-guards.md:9-21`). Mitigations: loom refuses `proved` with `sorryAx` or unnamed axioms (R3); the mapping shows every hypothesis and marks `EXCESS`; the badge names who reported the build and whether a replay ran; attestation records whether the person read Lean or the rendering; nothing feeds `settled`. Residual: the evidence is the agent's report until loom can check it (LEAN-12), and the badge must say so.
- **Silent staleness.** Not silent in loom, since states are computed from the text on every query; but the skills' manifest pins line ranges (LEAN-3), and a Lean file edited after attestation is caught only because loom reads the statement region on each query (R6). A definition the statement depends on that is not a `\ref` in the statement escapes the closure: the mode must have the agent add `\uses` suggestions for them.
- **A rendering attested as if it were Lean.** LEAN-1. The record's `from: rendering` must show, and the gloss is labelled the agent's reading.
- **Naming.** "Stamp" and "verified" are taken (LEAN-5); the wrong word makes an unchecked thing look checked.
- **Licences.** Shipping adapted text without the change notice or the MIT/Apache notices (LEAN-15). Vendor unmodified.
- **Capabilities the pilot's app lacks.** No subagents means no independent auditor; Codex's sandbox may block downloads; Linux-only gating (LEAN-6); smaller model tiers fail harder lemmas and burn quota. The mode must degrade to "statement only, audit by a second session" and say so in the record.
- **Disk and time.** 6–10 GB per project on laptops that may not have it; a long download in the middle of a proofreading session. `loom doctor` should say this before the agent starts.
- **Load on loom.** Without R1, `loom serve` walks Mathlib's build tree every second (LEAN-4).

### F. What a hands-on trial in a later wave needs

This machine has no `elan`, `lean` or `lake`, 29 GB free, 16 GB of memory and 8 cores; Python 3.13 and git are present. A trial needs: elan installed into `~/.elan` (it edits the shell profile unless told not to), one Mathlib project with its cache (6–10 GB, leaving about 20 GB), the skills installed into that project's `.claude/skills` (no change to `~/.claude`), and a throwaway quilt. Time: about 30–60 minutes to install and fetch, then 2–6 hours of agent time to take one lemma through statement, audit, proof and re-audit (estimate). Undo: `elan self uninstall` and deleting the project. The author's approval is needed because it changes the home directory and uses about a third of the free disk.

## Sources

- [Lean manual: installation](https://lean-lang.org/install/manual): elan install line, Mathlib project creation, `lake exe cache get`, git and curl required; gives no sizes.
- [Lean community: install on macOS](https://leanprover-community.github.io/install/macos.html): points to the official manual.
- [Zulip: lake exe cache get](https://leanprover-community.github.io/archive/stream/287929-mathlib4/topic/lake.20exe.20cache.20get.html) and [Zulip: saving disk space](https://leanprover-community.github.io/archive/stream/113488-general/topic/Saving.20disk.20space.3F.html): full cache about 5.1 GB (2025), build artifacts about 4.3 GB per project (2024); dated, unverified now.
- [Mathlib wiki: globally shared Mathlib](https://github.com/leanprover-community/mathlib4/wiki/Project-setup:-globally-shared-mathlib-installation): one shared copy for tight disks.
- [leanblueprint](https://github.com/PatrickMassot/leanblueprint): `\lean`, `\leanok` (hand-written), `\uses`, `\mathlibok`; `checkdecls` checks only that names exist.
- Agent cost reports, secondary and unverified: [arXiv 2603.15929](https://arxiv.org/html/2603.15929), [arXiv 2606.14000](https://arxiv.org/pdf/2606.14000), [Clawristotle](https://reservoir.lean-lang.org/@Vilin97/Clawristotle).
- FSF's licence list (CC BY 4.0 compatible with GPLv3) is from general knowledge, not fetched in this study.
