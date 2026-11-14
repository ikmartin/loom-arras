# Lean formalization, done once for real (v0.1 study, raw, second wave)

Investigator: Lean trial. Machine: macOS 26.5.2 on arm64, 8 cores, 16 GB, 25 GB free at the start (not 29), shared with other agents (load average 5–15 throughout). Skills repository at `1837b95` (the same commit the paper study read), cloned into scratch. Loom at `71621877` (study checkout), run with `XDG_CONFIG_HOME` in scratch on a copy of `demos/showcase`. Lean `leanprover/lean4:v4.36.0-rc2`, Mathlib `9d581dfff2e4` (tag `v4.36.0-rc2`). Wall clock 14:25:51 to about 15:25, of which the Lean workflow for the main lemma took 20 minutes. Paths below starting `scratch/` are under `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/lean-trial/`.

**Nothing a person decides was decided by a person.** Every approval, ruling and attestation below was made by me as a stand-in and is marked **SIMULATED for the trial** where it appears, including inside the manifest the skills require (`approved_by: "SIMULATED-FOR-TRIAL (no person approved this)"`). The audits were run by subagents on a different model (Sonnet; I am Opus) in the same session: different model, fresh context, same vendor and same session, so their independence is declared, not checked.

## Headline findings

- **LTRIAL-1. The install took 3 minutes 35 seconds, asked nothing, and costs 10.7 GB.** `brew install elan-init` took 35 s; `lake +leanprover-community/mathlib4:lean-toolchain init ShowcaseFormal math` in an empty `lean/` took 180 s and did everything else: toolchain (29 s download, 18 s unpack), Mathlib clone (35 s), seven dependencies (17 s), and the build cache through Mathlib's post-update hook (80 s, 9,081 files). No prompt, no profile edit, no Xcode dialog (git was already present). On disk: toolchain 3.0 GB in `~/.elan`, project `.lake` 7.2 GB (149,150 files), and a compressed cache of 455 MB in `~/.cache/mathlib`, outside the project. The network interface received 1.27 GB during those 180 s (system-wide, so an upper bound). The paper study's "30–60 minutes, 6–10 GB" was pessimistic on time and at the top of its range on disk.
- **LTRIAL-2. The agent work for one lemma took 20 minutes, and the proof was the smallest part.** For Proposition `sh-0007` (Saturation), the time from choosing the lemma to a sealed declaration that a second auditor had re-checked was 14:36 to 14:56. That includes two independent audits and a graph review by subagents, 6.5 minutes in total. The proof took one compile. A harder lemma, `sh-0006` (Support: a nonnegative nonzero balanced weighting's support contains a directed cycle), took about 10 minutes for its statement, an independent audit and a complete proof (a pigeonhole walk argument, three compile cycles). I left out the freeze, graph and seal steps for that one. The paper study estimated 1–6 hours per lemma. That holds only when Mathlib lacks a definition. Even then, sh-0006 shows the time goes on the person's ruling, not on the agent.
- **LTRIAL-3. Loom's closure misses the definitions that give the stamp its meaning.** Loom's statement closure for `sh-0007` is `["sh-0007"]` alone (`loom status --json`), and `loom downstream sh-0003` does not list `sh-0007`. The statement reaches Definitions sh-0002, sh-0003 and sh-0004 only through the macros `\Zcyc`, `\bd` and `W(\quiv)`, never through `\ref`. Saturation holds for the kernel of *any* homomorphism into a torsion-free group. A wrong divergence, even one with the sign flipped, would therefore still build, audit as `EXCESS 0` and seal. All the meaning is in the two definitions, and loom's acceptance-style staleness would not watch them. R3 and R6 must take their closure from the evidence record (Lean definition → source key), not from loom's graph.
- **LTRIAL-4. The skills' records do not notice the paper changing; loom's history does, but loom's status does not.** I edited `sh-0007` from "some integer $n \neq 0$" to "some integer $n$", which makes the printed statement false. `check_frozen_anchors.py` still printed OK and `proof_depgraph.py --check` passed. It passed even after the edited file was copied into the source snapshot, because it checks only that the cited line ranges exist. `lake build` was clean. `loom history sh-0007` reported at once "its text now differs from every version", and `loom source sh-0007 --at flows-v1 --diff` showed the exact change. `loom status` still listed `sh-0007` as plain `draft`, because staleness exists only for accepted keys. R6 must compute staleness from the version recorded in the evidence, whether or not anyone accepted the key.
- **LTRIAL-5. Running the skills' linters inside a quilt breaks the quilt.** Both linters need one root that holds the paper and the Lean together. Manifest paths are relative to the Lake root, and `--source-root` must contain the source and the frozen files. A symlink resolves outside the root and is rejected as escaping it. With the Lake project at `lean/` inside the quilt, I had to copy the paper's node files into `lean/source/`. Loom then scanned that copy as quilt source: `sh-0001`–`sh-0004` and `sh-0007` became **conflicted** ("defined by drafting/nodes/sh-0007.tex and lean/source/sh-0007.tex"), three keys turned loose, and the key count went from 26 to 27. R1 as written (prune `.lake`) does not prevent this. R1 must prune the whole Lake project, meaning any directory holding `lakefile.*` and `lean-toolchain`.
- **LTRIAL-6. A Lake project in a quilt costs 2.4× on `loom status` and 120× on an idle `loom serve`.** `loom status`, in five interleaved pairs: 0.40–0.46 s without `lean/`, 0.97–1.03 s with it. `loom serve --no-compile`, idle after a 20 s settle and measured over 60 s: 0.7% of a core without `lean/` and **84% of a core** with it. Its first 20 s took 17.2 s of CPU (0.9 s without), and its RSS was 86 MB against 66 MB. 113 files under `.lake` carry suffixes the watcher watches (`.json` 49, `.md` 48, `.toml` 11, `.sty` 4, `.bib` 1). This confirms LEAN-4 with figures. R1 is a precondition of any pilot, not an optimisation.
- **LTRIAL-7. The seal rule decides the statement's shape, and nothing says so at freeze time.** `check_frozen_anchors.py` accepts a sealed body only if it is exactly `by exact <Provider.export>` (or `simpa using`). That closes the goal only when the frozen theorem has no binders before the colon. My audited, "approved" v1 had the usual Mathlib shape, `theorem … (s t : A → V) (w …) (hn : n ≠ 0) (h : …) : …`, and could not be sealed (`typeclass instance problem is stuck`). The skills' remedy is a versioned successor and a fresh approval. So v2, the same type with the binders written after `∀`, needed a second **SIMULATED** approval for a purely formatting reason. A person would be asked to approve the same theorem twice. The `formalize` mode must tell the agent this rule before the first approval.
- **LTRIAL-8. The skills' "author approval" and "ABI hash" are unchecked strings.** The guard accepted `manifest_state: "AUTHOR_APPROVED"` together with `approved_by: "SIMULATED-FOR-TRIAL …"`. The ABI hash is only format-checked; the skills never say how to compute it, and their own tests use `"a"*64`. My stand-in, sha256 of the `pp.all` signature, changed between v1 and v2 although the types differ only in binder names. Told plainly that approval was simulated, the re-auditor still wrote "**PROVED** … with the standing caveat". This confirms LEAN-2 and LEAN-10: loom must compute its state from records it can check and must never copy a status word out of an agent's report.
- **LTRIAL-9. Independent review earned its cost on the graph, not on the statement.** The graph reviewer (70 s, then a 22 s re-review) found three real defects in my 11-node graph: a missing edge to `sh-0004` in the first route, a missing edge to `sh-0003` in the second, and an unstated bridge that needed a `SOURCE_GAP` step node. The two statement audits found no fault, correctly. They checked the divergence's sign by evaluating it on a concrete quiver with `decide`, so neither needed to read the misleading line in LTRIAL-10.
- **LTRIAL-10. Lean's printer drops the parentheses that carry the definition's meaning.** I wrote `(∑ a with t a = v, w a) - ∑ a with s a = v, w a`, and `#print` shows it as `∑ a with t a = v, w a - ∑ a with s a = v, w a`. That is correct (the big operator binds at precedence 67), but a mathematician reads it as one sum of differences. A rendering for attestation must re-insert the parentheses or use the paper's notation. It must never show Lean's pretty-printed text as "the statement".
- **LTRIAL-11. The person's real work is a mathematical ruling, and only the harder lemma needed one.** For sh-0007 the person's decisions were approvals of three exact declarations, a re-approval and a split ruling, all mechanical once rendered. For sh-0006 the paper uses "directed cycle" without defining it. The auditor listed five rulings; the central one is simple cycle, closed walk or trail, with loops counting as length 1 and `supp` meaning the arrow support. That ruling is mathematics the person owns. The rendering must put "terms the paper does not define" first.
- **LTRIAL-12. A loom quilt's agent permissions will prompt on every Lean step.** The quilt's generated `.claude/settings.json` allows 55 `loom …` patterns and nothing for `lake`, `lean`, `leanchecker`, `git` or `python3`. The workflow ran about 45 commands under 8 prefixes (`brew`, `lake init/build/env lean/env leanchecker`, `git add/commit/rm/diff`, `python3 -I`). `loom accept` was refused to me, as designed ("an agent is running this shell (AI_AGENT is set)"). Each kind of step needs one approval from the person, or allow rules that loom writes when formalization is turned on.
- **LTRIAL-13. Kernel replay is free and local.** The toolchain ships `leanchecker` (also `lean4lean` and `nanoda_bin`). `lake env leanchecker <Module>` replayed each project module in 12–18 s with exit 0 and no output. A record can therefore carry `replay: leanchecker` as an agent-reported fact at no extra install. A missing module gets an "uncaught exception" message, so the record should keep the command's output too.

## 1. Install, measured

| step | exact command | wall clock | download | on disk | prompts or decisions |
|---|---|---|---|---|---|
| elan | `HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_UPGRADE=1 HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1 brew install elan-init` | 35.7 s | bottles, a few MB | 5.9 MB keg; `elan`, `elan-init`, `lean`, `lake`, `leanc`, `leanchecker`, `leanmake`, `leanpkg` linked into `/opt/homebrew/bin` | none; but see side effects below |
| toolchain | pulled by the next command (`lean-4.36.0-rc2-darwin_aarch64.tar.zst`) | 29 s download + 18 s unpack | part of the 1.27 GB | 3.0 GB `~/.elan/toolchains/leanprover--lean4---v4.36.0-rc2` | none |
| Lake project + Mathlib | `cd quilt/lean && lake +leanprover-community/mathlib4:lean-toolchain init ShowcaseFormal math` | 35 s Mathlib clone (`--filter=blob:none`) + 17 s for 7 dependencies | part of the 1.27 GB | `.lake/packages/mathlib` 6.8 GB of 7.2 GB | none |
| build cache | run by Mathlib's post-update hook inside the same command (`lake exe cache get` was not typed) | 80 s (2 s building the cache tool, about 55 s downloading, 25 s decompressing) | 455 MB compressed (`~/.cache/mathlib`) | in `.lake` above, plus 455 MB in `~/.cache/mathlib` | none |
| total | | **215 s** | **≤ 1.27 GB** | **10.7 GB** | **none** |

Side effects nobody asked for. Despite the three environment variables, `brew install elan-init` upgraded its dependency `coreutils` (9.9 → 9.12_1) and refreshed `ca-certificates`. It also ran the 30-day automatic `brew cleanup`, which deleted superseded kegs (`coreutils 9.9`, `readline 8.3.3`, `xz 5.8.3`, an old `ca-certificates`) and some Homebrew caches. Newer versions of all of them stayed installed. Adding `HOMEBREW_NO_INSTALL_CLEANUP=1` would have prevented the cleanup but not the dependency upgrade. Brew's elan puts `lean` and `lake` on `PATH` with no `source ~/.elan/env`, and none of `~/.zshrc`, `~/.zprofile` or `~/.profile` mentions elan. elan also wrote `~/.elan/known-projects`, which lists the scratch project's path.

`lake init` inside a directory that is already a git repository does not create a nested `.git` (tested in scratch). In a directory outside git it creates one, which is what happened here because the showcase copy is not a git repository.

Cold and warm costs once installed: the first `lake env lean` probe took 41–43 s wall clock (2.4 s user, 6.2 s sys, so mostly loading `.olean` files under I/O contention) with a peak RSS of 1.06 GB. Later probes took 8.6–13 s. A targeted `lake build` of a project module took 4–12 s, and a `leanchecker` replay 12–18 s per module.

**Who can do what.** An agent can run every command above, and none of them asks a question. The person's part is a permission prompt per command family in their agent app, and the disk. A mathematician never needs a terminal, provided the agent app may run `brew` (or the official installer with `--no-modify-path`) and `lake`. Loom itself should run none of it (LEAN-12 stands). `loom doctor` should say "about 11 GB for the first Lean project, 7.2 GB for each further one at the same pins".

## 2. The lemma and loom's context

Chosen: **Proposition `sh-0007` (Saturation)**: "$\Zcyc(\quiv)$ is a saturated sublattice of $W(\quiv)$: if $n w \in \Zcyc(\quiv)$ for some $w \in W(\quiv)$ and some integer $n \neq 0$, then $w \in \Zcyc(\quiv)$." It is self-contained, Mathlib has every ingredient, and the paper gives it two proofs. `sh-0006` (Support) was the second, harder lemma (LTRIAL-2, LTRIAL-11). `sh-0009` (Rank) was out of reach in the time: it needs connected components of the underlying graph and the rank of an image lattice.

What `loom source sh-0007 --closure` gave an agent: the preamble (with `\usepackage{flows}` but not its contents), Definition `sh-0004` (pulled in only because the *second proof* `sh-0010` says `\uses{sh-0004}`), the statement and both proofs. It did not give Definition `sh-0003` (divergence, the formula everything rests on), Definition `sh-0002` (what a quiver and $W(\quiv)$ are), Convention `sh-0001` (finiteness, loops), or the macro file. I found those by reading `flows.sty` and the node files. `loom deps sh-0007` reports "0 through its statement, 1 through its proof". This is LTRIAL-3 seen from the agent's side.

## 3. The workflow as the skills specify, with timeline

| clock | stage (skill) | produced | departures |
|---|---|---|---|
| 14:30–14:36 | read `lean-workflow`, then `lean-project-architecture`, `lean-statement-audit`, `lean-orchestrator`, `build-proof-dependency-graph`, `machine-resources.md`, `landing-guards.md`, and both helper scripts in full (`check_frozen_anchors.py` 644 lines, `proof_depgraph.py` 1,043 lines; both are pure file checkers with no subprocess or network) | — | read while the install ran |
| 14:36 | source reconstruction | premises, quantifiers, carriers; Mathlib search (`rg` in `.lake/packages/mathlib`; found `AddSubmonoid.ker_saturated`, `IsAddTorsionFree`) | transcription kept in notes, not a tracked file |
| 14:37–14:38 | exact declarations, elaborated in an untracked file | `divergence` (an `AddMonoidHom`), `cycleLattice := (divergence s t).ker`, `cycleLattice_saturated` with `sorry` | one fix (`ring` not imported; `abel` instead) |
| 14:39–14:44 | independent statement audit (`lean-statement-audit`, Sonnet subagent, 4.5 min) | `scratch/audit-work/audit-report.md`: SOURCE 4, STANDING 0, TYPING 6, RULED 0, EXCESS 0; both definitions PASS; DECLARATION_FIDELITY PASS; probes on a 2-vertex quiver with a loop | the candidate was one file; the frozen layout splits it into three, byte-identical declarations |
| 14:44 | **person approves the exact declarations: SIMULATED for the trial** | — | — |
| 14:44–14:46 | freeze (`lean-orchestrator`): three module files under `ShowcaseFormal/Frozen/`, provider stub, `formal/frozen-anchors.json` (`DRAFT_SORRY`), guard OK, commit `0ddd188` | build 12 s | ABI hash by my own convention (LTRIAL-8); `source.revision` is a loom version (`loom sh-0007@1`) since the quilt copy has no git |
| 14:46–14:50 | dependency graph (`build-proof-dependency-graph`): `DEPGRAPH.md` and coverage manifest; linter; Sonnet review, 3 disputes accepted, re-review ACCEPT; `--require-reviewed … --check` passes | 11 nodes, 15 edges, 2 routes (the two proofs), 1 `SOURCE_GAP` step, 3 externals | source copied into `lean/source/` (LTRIAL-5); one writer and one reviewer instead of parallel extractors and a separate global reviewer |
| 14:50 | proof (provider `ShowcaseFormal.Internal.cycleLattice_saturated`) | 6 lines: unfold kernel, `map_zsmul`, pointwise `mul_eq_zero` | first attempt used `smul_eq_zero`, unknown in this Mathlib |
| 14:51–14:52 | seal fails (LTRIAL-7); versioned successor v2; **re-approval SIMULATED for the trial**; commit `8add1c6` | `Frozen/SaturationV2.lean` | v1 file removed rather than kept quarantined |
| 14:52–14:54 | seal, build, `#print axioms` from an untracked probe, guard, `leanchecker` on all four modules; commit `ec5feef` | axioms `[propext, Classical.choice, Quot.sound]` for all four constants; replay exit 0 | — |
| 14:54–14:56 | fresh re-audit (Sonnet, 95 s) | `scratch/audit-work/reaudit-report.md`: seal diff is proof-body-only, hashes recomputed, exact-type probe compiles; "PROVED … approval simulated, absent" | — |

Writes the skills asked for and I made: the frozen files, the manifest, `DEPGRAPH.md` and `DEPGRAPH_COVERAGE.md` with a generated dashboard, and three git commits. No errata ledger (no errata) and no campaign status report (one lemma). The status fields would read `DRAFT_ANCHORS: 0`, `UNREGISTERED_SORRIES: 0`, `DRAFT_IMPORT_VIOLATIONS: 0`, `SEALED_THIS_TURN: 1 (ShowcaseFormal.cycleLattice_saturated)`.

Skipped as Linux- or campaign-only: the compile gate (it would have replaced the toolchain's `lean` binary in `~/.elan`), overlay builds, worktrees, Comparator, mutation suites. Parallelism stayed at one niced Lean process at a time, as `machine-resources.md` asks of a worker, and the subagents ran their probes one at a time too.

## 4. The person's part

| # | where the skills require the person | what they would have been shown | time for a mathematician who does not read Lean (estimate) |
|---|---|---|---|
| 1 | approve the exact declarations before freezing (`lean-orchestrator` "Show the author the complete exact declaration") | the three declarations below, imports included, beside the source | 20–40 min raw, with a real risk of misreading; 5–10 min from the rendering below |
| 2 | approve the split policy (`split_policy.ruling_ref`, required for every anchor) | "NOT_SPLIT" for each of the three | seconds, if explained |
| 3 | re-approve v2 after LTRIAL-7 | the same theorem with the binders moved after `∀` | seconds if told "identical meaning"; that claim is the agent's |
| 4 | the match between formal statement and paper, which the skills fold into #1 and loom would make the attestation | rendering and gloss | 5 min for sh-0007; for sh-0006, the ruling on "directed cycle" |
| — | install and command approvals in the agent app | about 8 command families | a minute in all |

Source and Lean as they stood at approval (v1):

```latex
% sh-0003
(\bd w)(v) \;=\; \sum_{a \colon t(a) = v} w(a) \;-\; \sum_{a \colon s(a) = v} w(a),
... The resulting homomorphism $\bd \colon W(\quiv) \to \ZZ^{V}$ is the \emph{divergence map}.
% sh-0004
A weighting $w$ is \emph{balanced} if $\bd w = 0$, and the balanced weightings form the sublattice
\Zcyc(\quiv) \;=\; \ker \bd \;\subseteq\; W(\quiv),
% sh-0007
$\Zcyc(\quiv)$ is a saturated sublattice of $W(\quiv)$: if $n w \in \Zcyc(\quiv)$ for some $w \in W(\quiv)$ and some integer $n \neq 0$, then $w \in \Zcyc(\quiv)$.
```

```lean
def divergence {V A : Type*} [Fintype V] [Fintype A] [DecidableEq V] (s t : A → V) :
    (A → ℤ) →+ (V → ℤ) where
  toFun w v := (∑ a with t a = v, w a) - ∑ a with s a = v, w a
  map_zero' := by ext v; simp
  map_add' w₁ w₂ := by ext v; simp only [Pi.add_apply, Finset.sum_add_distrib]; abel

def cycleLattice {V A : Type*} [Fintype V] [Fintype A] [DecidableEq V] (s t : A → V) :
    AddSubgroup (A → ℤ) :=
  (divergence s t).ker

theorem cycleLattice_saturated {V A : Type*} [Fintype V] [Fintype A] [DecidableEq V]
    (s t : A → V) (w : A → ℤ) (n : ℤ) (hn : n ≠ 0) (h : n • w ∈ cycleLattice s t) :
    w ∈ cycleLattice s t := by
  sorry
```

The rendering the paper study proposes, drafted for this lemma (the gloss is mine, an agent's reading):

| Lean | paper | gloss |
|---|---|---|
| `{V A : Type*}` | "$V$ and $A$ finite sets" (sh-0002) | vertices and arrows, of any kind |
| `[Fintype V] [Fintype A]` | "finite" (sh-0002, Convention sh-0001) | both are finite |
| `[DecidableEq V]` | nothing | Lean's bookkeeping, so that arrows can be sorted by endpoint; no mathematical content |
| `(s t : A → V)` | "$s, t \colon A \to V$ the source and target maps" | the quiver $(V, A, s, t)$ |
| `(w : A → ℤ)` | "$w \in W(\quiv)$" | a weighting |
| `(n : ℤ)`, `n ≠ 0` | "some integer $n \neq 0$" | read as *every* such $n$ |
| `n • w ∈ cycleLattice s t` | "$n w \in \Zcyc(\quiv)$" | $n$ times $w$, arrow by arrow, is balanced |
| conclusion `w ∈ cycleLattice s t` | "$w \in \Zcyc(\quiv)$" | $w$ is balanced |
| **definition** `divergence s t w v = (∑ a with t a = v, w a) - (∑ a with s a = v, w a)` | (sh-0003) incoming minus outgoing | parentheses restored (LTRIAL-10); checked on a loop: contributes 0 |
| **definition** `cycleLattice s t = ker (divergence s t)` | (sh-0004) $\Zcyc = \ker \bd$ | — |
| conventions that differ | none here: subtraction and multiplication are on ℤ, no division | the theorem is stated for finite types in any universe, which is more general and harmless |
| not stated | "sublattice" | $\Zcyc$ is a subgroup by construction; rank and freeness are not formalized, and the claim does not need them |

**Could a mathematician attest from this?** For sh-0007, yes, in a few minutes, *provided the definitions' rows are part of what is attested*. **What could slip through:**

1. The definition rows are where the mathematics lives. A rendering that shows only the theorem's hypotheses looks perfect even over a wrong divergence (LTRIAL-3).
2. Every gloss is an agent's sentence that nothing checks against the Lean. The audit checked the Lean, not the gloss.
3. The paper's "for some $w$ … and some integer $n$" is a universal statement in existential wording, and a careless gloss could carry the misreading either way.
4. A row the agent omits is invisible. Loom cannot parse Lean binders, so it cannot prove that the table covers the whole signature. It can at least check that every binder name in the frozen statement region appears in the table.
5. For sh-0006, the rendering cannot settle "directed cycle". The person has to choose, and the record must keep the choice as the person's ruling.

## 5. Loom's side

### (a) The evidence record (R1 of the study's section 3), filled by hand

```json
{
  "id": "f-2026-11-13-trial01",
  "key": "sh-0007", "step": "@1 (flows-v1)",
  "key_hash": "sha256:19b17e19f1a0df720e884384a24a12e9fa147396b7973c4448b3a2760b133342",
  "closure_loom": {},
  "closure_needed": {"sh-0004": "@1", "sh-0003": "@1", "sh-0002": "@1", "sh-0001": "@1"},
  "preamble": "drafting/flows.sty sha256:2a30c64e4d77ab7d…",
  "decl": "ShowcaseFormal.cycleLattice_saturated", "kind": "theorem",
  "project": "lean/", "file": "lean/ShowcaseFormal/Frozen/SaturationV2.lean",
  "statement_hash": "sha256:dd616b5958319ba4… (frozen prefix region, FROZEN_ANCHOR_PREFIX_BEGIN … PROOF_BEGIN)",
  "definitions": {"ShowcaseFormal.divergence": {"key": "sh-0003", "file_sha256": "912e7a589e16d734…"},
                  "ShowcaseFormal.cycleLattice": {"key": "sh-0004", "file_sha256": "7bb9630d7edf0cba…"}},
  "commit": "ec5feefb4be788c6f7029db496f251749e143019", "clean": true,
  "toolchain": "leanprover/lean4:v4.36.0-rc2",
  "manifest_hash": "sha256:c9e47f6ef88f5aa9… (lake-manifest.json)",
  "mathlib": "9d581dfff2e41de989072ea63abf3daf69311520 (v4.36.0-rc2)",
  "status": "proved",
  "axioms": ["propext", "Classical.choice", "Quot.sound"],
  "replay": "leanchecker, 4 modules, exit 0 (agent-reported)",
  "audit": {"by": "Sonnet subagent, same session (declared independent)",
            "verdict": "DECLARATION_FIDELITY PASS; seal proof-body-only",
            "bins": {"SOURCE": 4, "STANDING": 0, "TYPING": 6, "RULED": 0, "EXCESS": 0},
            "report": "session dir: reaudit-report.md"},
  "mapping": "the table in section 4", "gloss": "the gloss column in section 4 (agent's reading)",
  "by": "Claude Code Agent (Opus)", "when": "2026-11-13T14:56",
  "attestation": {"SIMULATED_FOR_THE_TRIAL": true, "author": null, "from": "rendering",
                  "note": "no person attested anything"}
}
```

Easy to obtain, because they are files or command output: `decl`, `file`, `commit`, `clean`, `toolchain`, the Mathlib revision and `manifest_hash` (from `lake-manifest.json`), the axioms (verbatim `#print axioms`), the replay, and the frozen prefix hash (the skills' markers make the statement region exact). The skills do not produce:

- the loom key, version and hash (I took them from `.loom/history`; the version text hash covers statement and first proof together, while a formal stamp needs the statement alone);
- the definition closure in source terms (the skills' `definition_closure` lists Lean files; mapping them to `sh-0003` and `sh-0004` was my judgment, and loom's closure is empty);
- the preamble hash;
- the mapping and gloss (the audit's binder table cites source keys but has no plain-language column; the "likely misreadings" sections of the audit reports were the closest thing);
- machine-readable audit bins (the report is free Markdown);
- any attestation (the skills' approval is a free string, LTRIAL-8).

The ABI hash the skills want is not something loom should record as a check (LTRIAL-8).

### (b) Staleness: one hypothesis dropped

Edit: in `drafting/nodes/sh-0007.tex`, "some integer $n \neq 0$" became "some integer $n$" (statement now false). Reported:

| tool | after the edit |
|---|---|
| `loom history sh-0007` | "its text now differs from every version", with `loom stamp` or `loom revert sh-0007@1` as the next steps |
| `loom source sh-0007 --at flows-v1 --diff` | the one-line diff |
| `loom status` | `sh-0007` still `draft`, with no cause shown |
| `check_frozen_anchors.py` | FROZEN-ANCHOR GUARD OK |
| `proof_depgraph.py … --require-reviewed … --check` | rc 0, with the pinned snapshot and also after copying the edited file into the snapshot |
| `lake build` | Build completed successfully |

The edit was reverted afterwards (byte-identical to the demo). Loom already holds what R6 needs, a version and its text hash per key, but computes staleness only for accepted keys. The skills cannot hold it, by design: their pin is a copied range.

### (c) The skills' graph against loom's graph

| fact | skills' graph (after review) | loom |
|---|---|---|
| `sh-0007` has two proofs (routes) | yes | yes: `sh-0007/proof` and `sh-0010` |
| proof → `sh-0004` | yes, both routes | only through `sh-0010`'s `\uses` |
| proof → `sh-0003` (divergence) | yes, both routes | no |
| statement → definitions | `sh-0004` → `sh-0003` → `sh-0002`, `sh-0001` | no (closure `["sh-0007"]`) |
| external facts (ℤ^V torsion-free, first isomorphism theorem, torsion-free quotient ⇒ saturated) | 3 `external` nodes | no counterpart, no citation |
| unstated bridge | 1 `step` node with `SOURCE_GAP` | no |
| locators | `source/sh-0007.tex#sh-0007@L4-L6` | file and offsets known per key |

Loom could have supplied the skeleton: ids, kinds, both routes, the `sh-0004` edge, and locators. That is about 4 of the 11 nodes and 3 of the 15 edges. The rest came from reading proofs and macros. The reviewer's three disputes were all in that part. R11 would save typing, not judgment. For a single lemma the graph phase (writing, linting, review and re-review) took about as long as the statement audit and produced no input to the proof.

### (d) The Lake project inside the quilt

Figures in LTRIAL-5 and LTRIAL-6. The source snapshot the linters needed caused the conflicts; `.lake` caused the time and CPU. `loom status` with both present took 0.99–1.08 s. Loom's own `% !LOOM ignore` line would keep a snapshot file out of the scan, but it changes the snapshot's bytes. The clean fixes are to prune the Lake root, or to keep the snapshot out of the quilt tree.

## 6. What the trial changes

| req | verdict | how |
|---|---|---|
| R1 | **needs changing** | prune every Lake project root (a directory holding `lakefile.lean`/`lakefile.toml` and `lean-toolchain`), not only `.lake`, in the scan, the watcher, and Files if it lists them. Measured stakes: 2.4× `status`, 84% of a core idle in `serve`, 5 conflicted keys from the snapshot |
| R2 | confirmed | add disk to the doctor line: about 11 GB for the first project and 7.2 GB per further project; Homebrew's `elan-init` needs no profile edit (note that it can upgrade shared dependencies); the official script with `--no-modify-path` is the alternative |
| R3 | **needs changing** | statement hash = the skills' frozen prefix region; record the **definition closure as source keys** (Lean definition → key and version), since loom's closure misses them; record axioms verbatim and the replay with its output; do not import `abi_sha256` or `author_approval` as facts |
| R4 | confirmed | — |
| R5 | **needs changing** | the attestation covers the frozen definitions as well as the theorem (one act, every row of the rendering); keep `from: rendering` |
| R6 | **needs changing** | compute from the versions recorded in the evidence, for accepted and unaccepted keys alike; causes include `definition-changed` for the record's own definition closure; `declaration-changed` from the prefix hash |
| R7 | confirmed | — |
| R8 | confirmed, with rendering rules | definitions first; parentheses restored; "terms the paper does not define" first of all; a check that every binder name in the frozen region appears in the mapping; never Lean's pretty-printed text as the statement |
| R9 | confirmed, with content | the mode must say: binders after the colon (LTRIAL-7); one niced Lean process at a time; graph phase only on request; expect one permission prompt per command family |
| R10 | confirmed, but scope it | vendor unmodified, but the mode should route a single lemma through `lean-workflow` → search → statement audit → freeze, seal and re-audit, and skip `build-proof-dependency-graph`, whose linters need the paper inside the Lake root (LTRIAL-5) |
| R11 | unnecessary for v0.1 | loom supplies about a third of the graph; the judgment part is the review's |
| R12 | useful, still optional | the directive would also name the definitions' Lean counterparts (`% !LOOM lean: ShowcaseFormal.divergence` on sh-0003) |
| R13 | confirmed | — |
| R14 | partly done | done: Claude Code over shell on macOS with Lean installed; still needed: MCP, Codex, a person |

**Cut line.** Keep the study's smallest cut, with R1 widened and R3, R5 and R6 changed as above. Make the graph phase opt-in. That removes the vendored graph linter from the default path rather than adding work. The R6 change makes the cut no smaller, since staleness for unaccepted keys is new code.

**What a pilot's machine needs, measured.** macOS arm64 with git present. About 11 GB free for the first Lean project (3.0 GB toolchain, 7.2 GB project, 0.46 GB cache), plus 7.2 GB for each further project, and a new 3 GB toolchain whenever the Mathlib pin moves. About 1.3 GB of download, which took 3.6 minutes here. About 1 GB of memory per Lean process. Python 3 for the skills' helpers. A model tier that can run subagents for the audits. The agent time for one lemma was 20 minutes with the skills' full ceremony, or about 10 minutes for a harder lemma without the freeze, graph and seal steps.

**The smallest thing that lets a pilot mathematician truthfully say "loom showed me that this lemma is formally checked":**

1. R1 widened, so the project does not damage the quilt.
2. A record per R3 that names the frozen statement region, the definitions with their source keys, the axioms and the commit.
3. The person's attestation from a rendering that includes the definitions.
4. A computed state that goes stale when the lemma's text or any definition in the record changes.
5. A badge that says who checked what, for example: "Lean: proved, standard axioms (reported by Claude Code Agent at ec5feef); statement and definitions matched by you from the rendering".

**What I would refuse to ship:**

1. Any badge drawn from evidence without the person's attestation.
2. Any badge whose staleness ignores the definitions (LTRIAL-3).
3. Any state word copied from a skill manifest or an audit report: "AUTHOR_APPROVED", "PROVED", "independently audited" (LTRIAL-8).
4. A rendering that shows only the theorem's hypotheses.
5. A default install of the graph linter that needs the paper copied into the Lean project.

## 7. What is installed, and how to remove it

Nothing was removed; the author may keep the toolchain.

| what | where | size | remove with |
|---|---|---|---|
| elan 4.2.4 (Homebrew) | `/opt/homebrew/Cellar/elan-init/4.2.4`, links `elan`, `elan-init`, `lean`, `lake`, `leanc`, `leanchecker`, `leanmake`, `leanpkg` in `/opt/homebrew/bin` | 5.9 MB | `brew uninstall elan-init` |
| side effects of that install | `coreutils` 9.9 → 9.12_1, `ca-certificates` 2026-11-05, superseded kegs and caches cleaned | — | not reversible simply; newer versions are what remain installed |
| Lean toolchain and elan state | `~/.elan` (`toolchains/leanprover--lean4---v4.36.0-rc2`, `settings.toml`, `known-projects`, `tmp/`) | 3.0 GB | `elan toolchain uninstall leanprover/lean4:v4.36.0-rc2`, then after `brew uninstall elan-init`: `rm -rf ~/.elan` |
| Mathlib compressed cache | `~/.cache/mathlib` (9,081 files) | 455 MB | `rm -rf ~/.cache/mathlib` |
| Lake project with Mathlib, the quilt copy, skills clone, audits, probes, logs | `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/lean-trial/` | 7.2 GB | `rm -rf /private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/lean-trial` |

Shell profiles were not edited, and nothing was written under `~/.claude/skills`, `~/.agents/skills`, `~/notes` or `~/quilts`. Every server I started is stopped (`lsof -nP -iTCP:48300-48349` is empty). The `loom serve` processes still on the machine belong to other sessions. Free disk at the end was 15 GB, against 25 GB at the start; other agents also wrote to the disk meanwhile.

Artifacts, all in scratch:

- the Lean project and its git history: `quilt/lean/`, commits `0ddd188`, `8add1c6`, `ec5feef`;
- the manifest: `quilt/lean/formal/frozen-anchors.json`;
- the graph: `quilt/lean/DEPGRAPH.md`, `quilt/lean/DEPGRAPH_COVERAGE.md`;
- the audit and review reports: `audit-work/audit-report.md`, `audit-work/graph-review.md`, `audit-work/reaudit-report.md`, `audit-work/audit2-report.md`;
- the Support proof: `probes/Support.lean`;
- install and status logs: `logs/`;
- the CPU probe: `scripts/serve_cpu.py`.
