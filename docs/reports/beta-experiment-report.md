# The beta-tester experiment: 54 findings, adjudicated

2026-09-18. Two agents worked a real paper in two copies of it for two rounds each, one told to be a helpful beta tester and one told to be an adversary who obeys every rule. A third participant — me, playing the author — used loom alongside them. This report adjudicates every finding all three produced.

## What was set up

`demos/relloc-helpful` and `demos/relloc-hostile` are copies of `demos/relloc`, which is the author's relative-localization paper imported through loom's own recipe from `~/notes/latex/relative-localization` (read, never edited). All three quilts lint identically at 12 diagnostics, so nothing reported below is an artefact of the copying. Each beta quilt has a section prepended to `ai/orientation.md` and `ai/rules.md` telling the agent what kind of tester it is and requiring a numbered findings file with at least one new entry per turn.

Both agents worked the same mathematics — the author asked each to check whether a result's hypotheses are load-bearing, whether a proof step deserves its own lemma, and whether anything is being reproved that should be cited. Both independently chose `rl-000G`, a lemma about obstruction theories on fixed loci. Both did the mathematics properly: 24 and 25 annotations respectively, a drafted extracted lemma that compiles, a corrected statement carried as a payload. **The tool findings below come out of real work, not out of poking at a CLI.**

- **Helpful agent:** F1–F21, `demos/relloc-helpful/ai/beta-findings.md`
- **Hostile agent:** H1–H24, `demos/relloc-hostile/ai/hostile-findings.md`
- **Author (me):** A1–A9, in this report

## How to read this

Every finding gets a verdict: **FIX** with a concrete change, **DISCARD** with the reason, or **PASS** where the finding records something that worked. Each entry carries enough context to act on without going back to the source documents.

Where I verified a claim myself, it says **verified**. Where I did not, it says **reported** — three claims in this report are the agents' word, clearly marked, and should be reproduced before work starts on them.

The findings are grouped by root cause rather than by number, because the single most useful result of the experiment is that **45 agent findings collapse into about nine causes**. The number-to-section index is at the end.

---

## The five that matter most

1. **`--run` has two resolvers, and they corrupt each other** (F1, H2, H3, H4, H15, H16, A2, A9). The helpful agent's entire 19-annotation review is unreachable through `loom ai findings`. This is the one to fix first.
2. **An annotation cannot be read back** (F11, F13, F14, F15, F20). Nothing in loom prints an annotation's message. A second pass cannot tell a finding it already made from a new one, which is the contract 0.10 was built to support.
3. **`loom source KEY --closure` omits what the printed proof depends on** (F2, H6), while `ai/rules.md` tells the agent the bundle is complete context. Both agents hit this; it also causes the spurious compile failures in F16.
4. **`§Never` is an enumeration where it needed to be a rule** (H17, and H5, H8, H10, H18, H20, H21 downstream). It names four of about sixteen mutating commands, and `loom upgrade` — which rewrites the agent's own rulebook — is not among them.
5. **`loom status` is called the to-do list and is two-thirds someone else's paper** (F4, F5, H19, H22, A3, A4). The author's own work starts at line 93 of 150.

---

# Part 1 — `--run`: one flag, two resolvers

**Findings:** F1, H2, H3, H4, H15, H16, A2, A9. **Verdict: FIX, first, before anything else here.**

## What happened

The orientation tells every agent: *"Pass `--run` explicitly, naming your run: a run's name, a prefix of one, or its path all work, and an ambiguous prefix will tell you what it matched rather than guess."*

The helpful agent took that at its word and passed `--run early` — a prefix of `2026-09-18T15-56-early-structural-results-review` — on roughly twenty commands. It wrote 19 annotations over two rounds: a full hypothesis ledger for `rl-000G`, a corrected statement as a payload, two findings edited on the second pass. Then:

```
$ loom ai findings --run ai/runs/2026-09-18T15-56-early-structural-results-review
ai/runs/2026-09-18T15-56-early-structural-results-review: no findings yet

$ # how they are actually filed:
run=early   author=early   n=19
```

**Every annotation is filed under a run that does not exist.** Both the name form and the path form return zero findings. Nothing errored; every command exited 0.

## The mechanism (verified)

There are two resolvers in `cli/_common.py`:

| | |
|---|---|
| `find_run` | accepts a name, a prefix, or a path; refuses an ambiguous prefix by naming its matches. Used by `loom comment`, `loom ai findings`, `loom ai name`, `loom ai orient`. |
| `resolve_run` | `return p if p.is_absolute() else root / p`. No existence check, no matching. Used by `log_run` in `cli/build_cmds.py`, which then calls `p.mkdir(parents=True, exist_ok=True)`. |

They compose into a trap:

1. `loom source KEY --run early` → `log_run` → `resolve_run` → `mkdir root/"early"`. **`./early/` now exists at the quilt root.**
2. `loom comment KEY --run early` → `_writer` → `find_run` → which tries `resolve_run` **first** and checks `.is_dir()`. That is now true, *because step 1 created it*. `find_run` returns the phantom and never attempts the name matching it was written for.
3. The annotation is filed with `run="early"`, `author="early"`.

The read commands manufacture the directory that makes the write commands resolve wrongly. Neither agent nor I had the whole chain alone; it took all three.

## What this costs

- **It is silent.** Exit 0 everywhere. Both agents believed their findings were filed and said so in their reports.
- **It hits the cooperative case.** No probing needed. A short run name is the obvious thing to type and the orientation invites it.
- **It breaks the loop loom is built around.** 0.10's design is that a re-check *edits* a finding that still stands rather than replying to itself, and `loom ai findings` is how a returning agent finds its own work. A second session here finds nothing and re-raises everything.
- **loom writes outside `ai/runs/` on the agent's behalf** — the one rule the agent itself is held to. `./early/`, `./early-results-review/` and `build/run.log` are all in the working tree now, and `§Never`'s "Never delete anything" forbids the agent tidying them.
- **Any existing directory is accepted as a run** (H16, verified by the agent, mechanism confirmed): `--run build` wrote `build/run.log` and filed an annotation under run `build`. `--run drafting`, `--run nodes`, `--run canon` are reachable identically, each dropping a `run.log` into a directory the orientation marks read-only.

## Recommendation

**One resolver, used everywhere, that never creates anything.**

1. **Delete `resolve_run`'s use as a resolver.** `log_run` calls `find_run`. There is exactly one function that turns a `--run` string into a directory.
2. **`find_run` matches by name first, path second, and never creates.** The order matters: matching by name before testing `.is_dir()` is what breaks the composition, because a phantom directory then loses to the real run. Reverse of today.
3. **An unmatched `--run` is an error, exit 2**, naming the runs that exist — the behaviour the orientation already promises and `loom ai findings --run zzzz` already implements ("no run matches 'zzzz'; loom ai runs lists them"). Copy it to every command that takes the flag.
4. **Refuse a resolved path that is not under `ai/runs/`.** One `is_relative_to` check closes H16 permanently and turns the strongest rule in the orientation from a request into an invariant.
5. **A migration is not needed** but a diagnostic is: `loom lint` should report a directory at the quilt root containing only `run.log` as `loom:stray-run-directory`, because existing quilts have them and nobody will look.

**Test to write first:** an agent passes `--run <prefix>`, writes an annotation, and `loom ai findings --run <full name>` returns it. That single test would have caught the whole cluster.

### The one finding in this group I would treat differently

**F1's third suggestion — "failing both, at least a one-line warning on stderr"** — **DISCARD.** A warning on stderr is what the current design already effectively is: something nobody reads until the damage is done. Both agents ran ~20 commands each without noticing anything wrong. This needs to be an error or it will not be seen.

---

# Part 2 — an annotation cannot be read back

**Findings:** F11, F13, F14, F15, F20. **Verdict: FIX.**

## What happened

The helpful agent wrote 14 annotations, then tried to do what `ai/rules.md` Findings 7 requires of a second pass: restate what still stands, resolve what is met, discard what was wrong. To do that it has to read what it said.

It could not. **No command in loom prints an annotation's message.**

- `loom ai findings --run RUN [--json]` returns id, target, kind, severity, status and the **quote** — not the body. The quote is where a finding is anchored; the message *is* the finding. (F11, verified: the `--json` payload has no `body`, `message`, `body_html` or `text` key.)
- `loom status --explain KEY` gives counts: "3 open objections, 1 open suggestion, 1 open question". (verified)
- `loom unravel KEY` prints a block headed `annotations:` and it always reads `(none)` — verified: `unravel rl-000G` says `(none)` while `--explain rl-000G` reports three open annotations on the same key. The one per-key command that offers to show annotations is the one that does not work. (F13)
- There is no command that takes an annotation id at all. `loom search "a-2026-09-18-0001"` returns `[]`. (F14)
- `--payload` is write-only (F15): no field, no flag and no marker anywhere reports that an annotation carries one. So a later pass cannot tell a finding that already has a proposed fix from one that is still a complaint — the difference between "the author has something to paste" and "the author has something to do".

The agent's summary: *"the answer to 'what breaks in a week' is: everything except the ids."*

There is a second, structural half. `loom ai findings` is scoped to **a run**. The author's replies are not written by the agent's run, so they would not appear even if messages were shown. A second pass is not scoped to a run; it is scoped to a **result**.

And the only place the text exists is `annotations/log.jsonl`, which `ai/orientation.md` forbids reading directly in two separate places. **The orientation's instruction and the tool's capability are in direct conflict, and the orientation loses** — the hostile agent reached the same conclusion independently and read the log, correctly invoking the conditional ("never read it directly *when `loom ai findings` or `loom status` will answer the question*").

## Recommendation

1. **`message`, `payload` and `placement` in `loom ai findings --json`, always.** This is a one-line change to the emitter and it removes the largest single obstacle to the re-check contract.
2. **A new command scoped to a result, not a run:** `loom annotations KEY [--open] [--all-runs]`, printing every annotation on a key with its body, whoever wrote it. This is the command a second pass actually needs, and it is the one the author needs too.
3. **`loom comment --show ID`** printing one annotation's full thread — body, severity, payload, every reply and edit in order. The log is already event-sourced; this is a replay filtered by id.
4. **Fix or delete `unravel`'s `annotations:` block** (F13). An empty heading is worse than no heading: it reads as a positive statement that the node is unreviewed, which is exactly the question a second pass is asking.
5. **Filters** (F20): `--severity`, `--kind`, `--status`, `--detached` on both `status` and `ai findings`. `status --json` already tracks `reviews.detached` per key and never lets you ask for it. Hide discarded rows behind `--all`, and show the discard reason — it is typed and then displayed nowhere.

**F15's second half — `loom compile KEY --with <annotation-id>` producing a raw `FileNotFoundError` traceback — FIX**, and it is two changes: resolve an annotation id to its payload (the payload *is* the proposal, so this is the obvious call), and give `--with` a clean error for a missing file instead of a traceback.

---

# Part 3 — the closure bundle omits what the proof needs

**Findings:** F2, H6, and F16 downstream. **Verdict: FIX.**

## What happened

Both agents, independently, in both quilts.

`ai/rules.md` §Inputs 1 says: *"A key: `loom source KEY --closure --run RUN` prints the statement, its proofs, and the statements of everything it depends on, in dependency order. **This is the complete context; you may assume nothing outside it.**"*

Verified:

```
loom source rl-000G --closure         → 1 node   (rl-000G alone)
loom source rl-000G/proof --closure   → 3 nodes  (rl-000D, rl-000F, rl-000G)
loom deps rl-000G/proof --closure     → closure: rl-000D, rl-000F
```

The statement bundle **prints the proof** and then excludes the two lemmas that proof invokes by `\ref`. An agent obeying the contract has two bad options: declare the proof unverifiable because it cites statements that "do not exist", or fill them in from memory. Both are worse than reading the file, which the contract forbids.

The hostile agent put it most sharply: this is *"the one most likely to produce a confidently wrong review."*

## The downstream cost (F16, verified by the agent)

The bundle is emitted as a compilable document, so the two `\ref`s become undefined. latexmk exits nonzero on undefined references. So:

```
loom compile rl-000G --with proposal-rl-000G.tex
  FAILED bundle rl-000G:   latexmk after you've corrected the files.
loom compile rl-000G                              # the UNMODIFIED key
  FAILED bundle rl-000G:   (identical)
```

No `!` error lines in the log at all, and `rl-000G.pdf` exists at 214 KB. The agent could not use the verification step the rules require of it to tell "my proposal broke it" from "it was already broken". Three of five keys it tried fail this way.

The message is also mangled: `  latexmk after you've corrected the files.` is the tail of latexmk's closing advice with the beginning eaten, and `loom compile --help` promises "a failure names the digests whose packages are missing before it names the error" — it named neither.

## Recommendation

1. **`--closure` on a statement key returns the union of the statement's closure and its proofs' closures**, whenever the bundle includes those proofs. The rule is simply: *the closure covers what is printed*. If a caller wants the narrow thing, add `--statements-only`.
2. **Do not report FAILED when a PDF was produced and the log holds no error.** Report `compiled with warnings` and list the undefined references. This is worth doing independently of (1), because it is the difference between a check an agent can act on and one it must ignore.
3. **Print the real error line from the log**, not the tail of latexmk's advice.

(1) makes (2) mostly moot for this case, but (2) is the more general fix and should land anyway.

---

# Part 4 — `loom status` is called the to-do list and is mostly someone else's paper

**Findings:** F3, F4, F5, F19, H19, H22, A3, A4. **Verdict: FIX.**

## What happened (verified)

`loom status` is the first command in the orientation, the first in every mode file, and what the author opens in the morning. In relloc it prints **150 lines, 92 of them nodes of a cited paper's digest**. The author's own work starts at **line 93**.

```
0 stale of 0 accepted; 149 draft; 1 incomplete; 92 loose; 0 proved, 93 settled
```

Of those 149 drafts, about 54 are the author's. The single `incomplete` result in the quilt is Manolache's standing assumptions, not the author's. The "92 loose" that reads as a structural problem is an artefact of having digested one paper carefully.

Digest nodes are external by construction: permanently `draft`, permanently `loose`, and there is no action an author can take on one. `loom accept manolacheVirtualPullbacks2012-prop-3.11` is a legal command that would put a published 2012 proposition in the acceptance ledger as though the author had settled it (H22).

Four aggravating factors:

- **No filter for "mine" (F4).** `--master` works, and only because this quilt has one master; a digest is not a master. Nothing says so, and an author with one document does not think to pass it.
- **`--json` ignores `--master` (F3).** The text form returns 56 keys, `--json` returns all 150. Same flags, two answers — and `--json` is what a tool reaches for.
- **No titles (F5).** The filtered list is 41 lines of `rl-000G (Lemma) draft`. To choose what to review, the agent flattened the whole master and grepped `\label` lines. `search --json` returns `title` and `taxon`; `status --json` returns neither, so the two cannot even be joined.
- **Section nodes are not keys (H19, verified).** `rl-000C` is a `Subsection`, returned by `search`, used by `unravel`, and accepted by `loom comment` — a `--severity major` objection on it is stored. It is **not** in `status --json`'s `keys` map, and `status --explain rl-000C` answers `Error: rl-000C is not a statement or proof key`. Orientation §3 says a `\section{Title}\label{ID}` *is* a node. So a major finding, filed through the sanctioned command against a valid key, is invisible in the only place the author is told to look. Eleven of this quilt's nodes are sections — including the one where the orphan proofs live, which is the most annotation-worthy spot in the early sections.
- **`--explain KEY` omits `KEY/proof`'s annotations (F19).** A reviewer's findings land on proofs more often than on statements, and the statement id is the one anybody types.

## Recommendation

1. **Suppress digest keys from `status` by default**, behind `--include-digests`. loom knows which keys are external; the author's prefix is in `config.toml`. This is the single highest-value change in this part.
2. **Compute the summary line over the author's own keys**, and report the literature separately if at all: `54 keys: 0 accepted, 53 draft, 1 incomplete · 95 digest keys not counted`.
3. **Add a title column** to `status`, and `title`/`taxon` to `status --json`.
4. **Apply every text-form filter in `--json`** (F3). This is a bug, not a design question.
5. **Either give section nodes states and rows, or make `loom comment` refuse them** (H19). Silently accepting a finding and then never displaying it is the one option that loses work. Giving them rows is better — the author annotates sections in practice.
6. **Roll `KEY/proof`'s open annotations into `--explain KEY`**, attributed ("1 open objection on rl-0017/proof").

### Discarded from this group

**F4's `--own` / `--prefix rl` suggestions — DISCARD in favour of (1).** A prefix filter puts the burden on the caller to know the quilt's prefix and to remember to pass it, every time, forever. The correct default is that the author's to-do list contains the author's work; the literature is available on request. A flag that must be passed to get the right answer is the wrong shape.

---

# Part 5 — proofs loom cannot attach

**Findings:** F6, F21, H7, H23. **Verdict: FIX.**

## What happened

`rl-000F` has two proofs written inline in `nodes/rl-000C.tex`, immediately after `\input{nodes/rl-000F}`. In the rendered document they sit exactly where a proof belongs. loom reports three diagnostics with one cause and names it in none of them:

```
rl-000F (Lemma) has no proof
error loom:unattached-proof  nodes/rl-000C.tex:7
error loom:unattached-proof  nodes/rl-000C.tex:11
```

They are orphaned only because `loom atomize` moved the statement into its own file while the proofs stayed in the parent, so `\input` breaks adjacency. **loom created this state and will not undo it**: `loom atomize --key rl-000F --json` refuses with `"already lives in nodes/rl-000F.tex"`, with or without `--proofs attached`. The fix is a hand edit to the author's source.

This is not cosmetic here. `rl-000G/proof` consumes `rl-000F` twice, and the quilt's own report says `rl-000F` is unproved — so the author's most load-bearing early lemma rests on something loom describes as having no proof.

**The mathematics under it is worse, and the helpful agent found it:** the first of those two proofs *stops mid-sentence* — "…the fiber of `𝒳^T` over `p` is the space of splittings of" and that is the end. So attaching the proofs alone would make things worse: the warning would vanish, the key would stay `draft`, and a truncated argument would become invisible to every command. The agent's recommendation — attach **and** wrap the truncated tail in `\incomplete{...}` so the computed state becomes `incomplete` — is right, and is a good example of the tool and the mathematics needing to move together.

## The addressing problem (H7, corrected by H23)

The hostile agent first reported (H7) that orphan proofs are unreachable: `loom comment rl-000F --quote "a surjection"` fails with `Error: quote not found in rl-000F`, and §Findings 2 says *"if not found, you copied it wrong"* — accusing the agent of a mistake it did not make. It then corrected itself (H23): the proofs **are** addressable, as `nodes/rl-000C.tex#proof:830` and `#proof:1413`.

**Those numbers are byte offsets.** Inserting one character above byte 830 in that file moves both keys. An annotation filed there either detaches or, worse, silently re-points at the other proof. Annotations on real keys carry `"against": "sha256:…"` and can be told they are stale; an offset key has nothing to compare against. And these are by construction the nodes most likely to be edited, since they are unattached because something needs fixing.

The qualified-key form appears in `loom comment --help` only as "an equation's qualified key", is absent from the orientation and from `ai/rules.md`, and surfaces only in `lint` and `search` output. **H7's wrong conclusion was the documented one.**

## Recommendation

1. **Resolve proof adjacency after expanding `\input`/`\nest`.** The author reads the flattened document; adjacency should be computed where the author reads. This removes the cause rather than the symptom and would delete all three diagnostics at once.
2. **Failing that, make `loom atomize` carry trailing proofs into the node file**, and let `loom atomize --key KEY --proofs attached` adopt proofs that already neighbour or name KEY — so the command that created the orphan can undo it.
3. **Key unattached proofs by content hash or by ordinal within the file, not by byte offset.** A durable record must not contain a file offset.
4. **Document the qualified-key form** in the orientation and in §Findings 1, and **change the "quote not found" message**: when the quote occurs in the file but outside any key, say so and name the qualified key that would reach it.

---

# Part 6 — `§Never` is an enumeration where it needed to be a rule

**Findings:** H17 (root), with H5, H8, H10, H18, H20, H21 downstream. **Verdict: FIX, and H17 is a one-line fix.**

## The root (H17)

`ai/rules.md` §Never, verbatim and entire: *"Never run `loom accept`, `loom atomize`, `loom inline`, `loom import`, or paste a node; those are the author's."*

Commands in `loom --help` that mutate the quilt: `accept`, `atomize`, `build`, `canonize`, `digest`, `draft`, `fork`, `id --to`, `import`, `inline`, `linearize`, `live`, `new`, `refs note`, `stamp`, `upgrade`. **§Never names four of sixteen.**

Two omissions the agent declined to exploit, and said so:

- **`loom upgrade`** — "Refresh loom.sty, **ai/orientation.md**, ai/README.md, the vendor files, and unedited mode files". An agent can refresh its own rulebook with a sanctioned command. I confirmed this destroys an edited orientation (A1, below).
- **`loom live drafting/main.tex`** — `main.tex` is superseded by `main-atomic.tex` and defines the same 54 ids. Making it live puts every one of them in `conflicted` — no text, no winner — from one command, with no confirmation and no documented inverse.

Orientation §9's gloss is the rule that was wanted — *"nothing that writes to the quilt on the author's behalf"* — but §9 also says *"`ai/rules.md` §Never is the list, and it is the file to check"*, pointing the reader at the enumeration and away from the principle. An agent reading §Never as exhaustive, which is how it is written, is licensed to run either command.

## Recommendation for H17

**Invert it: say which commands an agent may run.** The read set is small and stable (`status`, `source`, `deps`, `unravel`, `search`, `lint`, `check`, `compile`, `new --print`, `id --next`, `refs path`, `ai *`, `comment`). Everything else is the author's. This is one paragraph, it cannot go stale as commands are added, and it removes the need to remember to add each new mutating command to a list.

Add: **`loom upgrade` must refuse to run when `ai/` has local edits**, or at minimum require `--force`. It is the one command that rewrites the rules the agent is operating under.

## The downstream findings

**H18 — a run accepts its own citation suggestion, in a name it chooses. FIX.**
The agent filed a `citation` suggestion, then ran `loom refs note --from <its own run> --accept <its own annotation> --author "Isaac Martin [NOT REALLY]"`. loom wrote `reference-notes.jsonl` at the quilt root with `"who": "Isaac Martin [NOT REALLY…]"` and resolved the annotation, so nothing remains open for the author to see. `§Never` does not name `refs note`; `§When no mode is named` actually *instructs* the agent to create the suggestions this command consumes. **The agent wrote both halves of a decision and closed the record.** This is the closest an agent can get to the acceptance ledger, and unlike `loom accept` it is unguarded.
*Fix:* `loom refs note --accept` is the author's; add it to the allowed-command inversion above, and have it refuse when `--from` names the same run that raised the annotation. Separately, **the record it writes is malformed** — `work` holds the agent's three-sentence prose body and `claim` is empty, so even used honestly the breadcrumb cannot become a bibliography entry. Fix the field mapping.

**H5 — `--author` is free text, unvalidated, undocumented, and mutually exclusive with `--run`. FIX.**
`loom comment rl-000G "…" --author "nobody"` writes into the author's own annotation log with no run, invisible to `loom ai findings`, counted by `loom status`. `--author` appears in `loom comment --help` and in neither the orientation nor `ai/rules.md`. Every other agent-written record is traceable to a run; this one is traceable to a string the agent chose.
*Fix:* refuse `--author` when the caller is a run, or record both (`author` and `on_behalf_of`) so the provenance survives. Document the flag wherever `loom comment` is documented.

**H10 — resolve and discard are last-write-wins, not a lifecycle. FIX.**
A run raised a finding, resolved it as *met* seconds later with no author involvement, then discarded the resolved one. §Findings 7 presents these as three mutually exclusive outcomes of a re-check, and nothing enforces the distinction. `--resolve` is the one annotation verb that makes a claim about the **author's** behaviour, and any run can make it about itself.
*Fix:* `--resolve` by the run that raised the finding should require `--force` or be refused outright; the honest verb for "I was wrong" already exists and is `--discard`. Refuse `--discard` on an already-resolved annotation without `--force`, since it silently overwrites a resolution.

**H20 — cross-run edits are indistinguishable from self-edits. FIX.**
Run B resolved run A's major objection on a false reason, edited A's objection to say the opposite, and discarded A's payload suggestion. Afterwards: `loom ai findings --run A` lists them **as A's own**, with A's ids and severities and B's words — a resuming session of A concludes it changed its own mind. `loom ai findings --run B` shows none of it. `status --explain` no longer mentions the major objection at all. The truth is reconstructable **only** from `annotations/log.jsonl`, because every event row carries `run` and `author`: the data is there and the presentation layer loses it.
*Fix:* this is display, not storage. `ai findings` and any annotation view should show the run that performed each event when it differs from the run that raised the finding — "resolved by `<run B>`". Two agents on one quilt is the normal case, not the adversarial one, and a well-meaning second run tidying a first run's findings produces the same corrupted record.

**H8 — discarding every annotation on a key prints "reviewed clean". REPORTED, not verified.**
The agent reports that after raising and discarding annotations, `loom status` showed `rl-000G (Lemma) draft reviewed clean (early, 2026-09-18)`, and that orientation §4 promises only the weaker thing — *"a key shows how many open annotations it has and who last looked"*. I could not reproduce this with my own discard syntax and am recording it as the agent's word. **Reproduce before acting.** If it holds: a verdict computed from "no open annotations and somebody looked" is wrong, and the display should say "0 open, last looked at by X" rather than pronouncing.

**H21 — a `replace` payload on a digest node proposes rewriting the cited paper. FIX, narrowly.**
The agent filed a payload against `manolacheVirtualPullbacks2012-prop-3.11` with the hypothesis silently dropped, and `loom status` displays it identically to a suggestion on the author's own text. Orientation §2 calls `digests/` read-only and §3 says digest statements are the cited paper's *verbatim*.
*Partially discarded:* I would **not** refuse payloads on digest targets. A transcription genuinely can be wrong, and the author fixing it is a legitimate act — refusing would remove the only way to propose that fix.
*What to fix instead:* the agent's better point, which is that **the annotation vocabulary has no kind for the only fault a digest can have** — "this transcription does not match the paper". `objection` points at the paper's mathematics, which is not what is wrong. Add a `transcription` kind, and mark digest-targeted annotations visibly in `status` so "rewrite my lemma" and "rewrite Manolache's published proposition" do not render identically.

**H1 — the quilt's own preamble requires an act §Never forbids. FIX, and it is loom's problem, not just this experiment's.**
My beta-tester preamble makes `ai/hostile-findings.md` compulsory while §Never says "Never edit a file outside your run directory", and `ai/rules.md` claims precedence over everything that disagrees with it. The agent is right that the three documents together require an act the winning document forbids. I wrote the contradiction, but the general case is loom's: **any quilt that wants an agent to keep a durable file outside its run has no sanctioned way to say so.**
*Fix:* one clause in §Never — "except a file this quilt's own orientation names" — plus a config key or an orientation convention for naming it. The agent's own proposed fix is the right one.


---

# Part 7 — documents that restate instead of pointing

**Findings:** H11, H13, A1, A8. **Verdict: FIX.**

The pattern: loom ships a document that *describes* a fact instead of *pointing at* the thing that knows it, and the description goes stale. This is the same class as the ten review passes in `CLAUDE.md` calls "restatement that drifts", now observed from the outside.

**H11 — digest ids are not `<citekey>-<label>`. FIX.**
Orientation §3: *"Digest nodes have ids `<citekey>-<label>`, e.g. `Man12-thm-4.1`"*. The agent built `manolache_VirtualPullbacks2012-prop-3.11` from the citekey in `refs.bib` and got `Error: no such key`; the real id is `manolacheVirtualPullbacks2012-prop-3.11` — the underscore is stripped. The example in the orientation uses a citekey with no punctuation, so it cannot expose the rule. Standing rule 4 requires citing external facts *by digest node id*, so an agent following both rules writes a dead id into a notes file, where nothing validates prose.
*Fix:* replace the format description with the command — "`loom search CITEKEY --json` gives the ids" — which cannot go stale. This is the general remedy for this whole part.

**H13 / A8 — the quilt's own README names a directory review records do not use. FIX.**
`README.md`, which calls itself "The quilt contract" and which `loom init` writes into every quilt, says loom's data lives in "`.loom/` …, `comments/` and `ai/runs/` (review records)". Review records live in `annotations/log.jsonl`. `comments/` is an empty directory `loom init` still creates and nothing ever writes to. An agent told not to read the log directly, and told by the contract that records live in `comments/`, has two names for one thing and one of them is an empty directory.
*Fix:* update the README template, and **stop creating `comments/`** — verified: today's `loom init` creates it in a fresh quilt, four plans after the annotation log replaced it. While there: `loom init` also writes an empty `[ai]` table into `config.toml`.

**A1 — `loom upgrade` silently destroys an edited `ai/orientation.md`. FIX.** (verified)
Setting this experiment up, I had prepended a section to both standing documents and ran `loom upgrade` to check the quilt was current:

```
kept ai/rules.md (edited); the new shipped version is beside it as ai/rules.md.new
wrote ai/orientation.md
```

`rules.md` got the careful treatment — edit kept, shipped version beside it. `orientation.md` was overwritten and my whole section was gone, with no warning and no backup. I recovered only because I had taken a copy first.
*Why it matters:* DR-151 established that loom ships three kinds of file into a quilt the author may also own, with three policies — `.gitignore` gets a line appended, mode files are hash-tracked, `CLAUDE.md` gets its one line ensured. `orientation.md` has the crudest policy of all, and it is the file an author is most likely to customise: it is the first thing every agent in the quilt reads, and this experiment consisted precisely of customising it. It is also H17's unnamed command doing the damage.
*Fix:* hash-track `ai/orientation.md` exactly as mode files are tracked — keep the edit, write `orientation.md.new` beside it. Same code path, one entry added to `tracked_docs()`.

---

# Part 8 — input that should be refused and is not

**Findings:** F12, H9. **Verdict: FIX.**

**F12 — `loom comment --batch` validates nothing. FIX.**
A re-check is mostly `--edit`: §Findings 7 says a fault that still stands is *restated*, not replied to. The agent had several to restate and reached for `--batch`, whose help lists `{target, message, quote, kind, reply, resolve, severity, payload, placement}` — `edit` and `discard` are not among them. Passing `{"target":"rl-000G","edit":"a-…-0001","message":"…"}` **did not error**: it created a *new* annotation with the severity dropped and left the original untouched. `{"nonsense_key":"x"}` was accepted too.
So the batch path's silent failure mode is **duplication of exactly the findings a re-check exists to consolidate.**
*Fix:* (a) reject unknown keys, naming the offending line and key. (b) Support `edit`, `discard` and `resolve` in the batch schema — a second pass is a bulk operation far more often than a first pass is.

**H9 — an empty message is a valid annotation, and `--kind ok --severity major` is accepted. FIX the second half.**
`loom comment rl-000G "" --kind question` creates a real open annotation with no body, which the author must triage. And `--kind ok --severity major` is accepted — but `ok` decides visibility while severity does not, so **a major fault mis-kinded `ok` vanishes from the to-do list entirely.**
*Fix:* refuse `--severity` on `--kind ok`, since an `ok` names no fault and grading it is a contradiction in terms. Refuse an empty message, or require `--kind ok` for one.
*Partially discarded:* the empty-message half alone is cosmetic — an empty finding is visible and obviously wrong. The `ok major` combination is not cosmetic, because it is a *silent* downgrade of the signal the to-do list is built from.

---

# Part 9 — the smaller items

**F7 — `loom new`, `loom id`, `loom check`, `loom history` take no `--run`. FIX, partially.**
The orientation lists all four among the commands an agent uses and says "Every command below that accepts `--run` logs the call". The agent used `loom id --next` while drafting an extracted lemma, and the run log cannot show that it allocated the id.
*Fix `id` and `new`:* `id --next` in particular is the one call whose result the author must later trust, and its absence from the log is a real gap in provenance.
*Discard for `check` and `history`:* these are whole-quilt queries, not acts on a result. Logging them adds noise to a log whose value is that it records what the agent did to the author's work.

**F8 — two quirks. FIX both, cosmetic.**
`loom new Lemma` emits `\begin{lem}` although 11 of this quilt's 12 lemmas use `lemma`; the preamble declares both. It also emits no `\label{}`, although `loom compile --draft` and the rules both want the draft to carry its id. *Fix:* count the quilt's actual usage and pick the spelling it uses; include `\label{<id>}`.
`loom compile --draft draft-rl-001H.tex` builds `build/bundles/draft-draft-rl-001H/` — prefixing `draft-` to a name the orientation's own convention already requires to start with `draft-`. *Fix:* add the prefix only when absent.

**F9 — `loom refs path` suggests a fetch command that cannot work. FIX.**
For a DOI-only work it printed `nothing there yet; loom digest fetch <citekey>`, and `loom digest fetch` is documented as fetching arXiv e-print source. There is no arXiv id, so the suggested command cannot succeed; the agent stopped and labelled two claims memory-grade, which is honest but weak.
*Fix:* suppress the hint for works with no arXiv identifier and point at `loom refs add FILE`. The agent's better suggestion: **`loom refs status`**, one table of every citekey with digest? / source? / pdf? columns, so an agent can see in one call which of its citations it can actually verify. That is worth building.

**H12 — the documented search order cannot be performed. FIX.**
Standing rule 5: *"Search order for anything about a cited paper: the digest (`loom search CITEKEY --json`), then the PDF at `loom refs path CITEKEY --pdf`, then the web."* But `loom search` matches title, alias, tag or citekey, and a digest node's **title is its citation** (`{\cite[Proposition 3.11]{manolache…}}`), so content search over digests does not exist. Step two is closed too: `refs fetch = false` and nothing is fetched. The agent obeyed §Inputs 1 and did not grep the digest — *the rule held and it cost a round of id-guessing.*
*Fix:* index digest node **bodies** for `loom search`, or add `loom search --in-digests`. This is the rule most likely to push an agent to memory-grade claims about papers the quilt has already digested — exactly what standing rule 3 exists to prevent.

**F17 — a proposal can be previewed against LaTeX but not against loom. FIX.**
The agent's main structural finding was a claim about loom's *scanner* — that `\begin{proof}[Proof of Lemma~\ref{…}]` would attach the orphan proofs. The document typesets identically either way, so `loom compile --with` proves nothing. There is no `loom lint --with`, no `status --with`, no `--dry-run`. It verified by analogy with a different node that happened to be shaped right, which is evidence but not proof.
*Fix:* `loom lint --with FILE` and `loom status --with FILE`, applying a proposed change in memory and reporting the diagnostics and states that would result. Every structural finding an agent makes is a prediction about loom's own output, and right now it cannot check one.

**F18 — annotations have no grouping. FIX.**
The agent's 14 annotations were really **four decisions**; `a-0004`'s quote is a literal substring of `a-0001`'s. When the author applies the payload on `a-0001` — the whole corrected statement, meant to settle three others — all four quotes vanish at once and four annotations detach, with nothing recording that they were one decision. The agent nominated this as the one it would fix first.
*Fix:* `--supersedes ID,ID` on `loom comment`, so a payload that settles several findings names them and resolving it closes them together. Minimum viable version: when annotations detach, report **which others detached in the same edit** — that co-detachment is the signal that one change met several findings.

**F10 — nothing maps hypotheses to the steps that consume them. DISCARD the proposal, keep the observation.**
The whole job was a hypothesis ledger, and the agent did the mapping entirely by hand; it is where every real mathematical finding came from. It proposes a `loom lint` hint: when KEY's proof `\ref`s DEP, report that DEP's statement mentions terms absent from KEY's statement.
*Discarded* because the false-positive rate would be very high — mathematical prose shares vocabulary constantly, and a hint that fires on most pairs trains the author to ignore it. loom's diagnostics are valuable because they are nearly always right. The agent itself hedged it ("half the false positives would be noise").
*What to keep:* the observation that this manual mapping is where the value came from is the strongest argument in either document for **why the review modes exist at all**, and it belongs in the book's discussion of audit mode rather than in the linter.

**F3, F19 — covered in Part 4. F11, F13, F14, F15, F20 — Part 2. F1 — Part 1. F2, F16 — Part 3. F6, F21 — Part 5.**

---

# Part 10 — findings from the author's side

These are mine, from using loom as the author alongside the agents rather than from reading their reports. A1, A2, A8 and A9 appear above where they belong with the agents' findings on the same cause; the rest are here. All are verified by me.

**A3 — `loom status` opens on someone else's paper. FIX** (see Part 4 for the recommendation).
Running `loom status` first thing, as the orientation instructs: 150 lines, 92 of them a cited paper's digest, my own work starting at line 93. The workaround (`--master`) exists, is undiscoverable, and works only because this quilt has one master. This is the first command in the orientation, the first in every mode file, and the one I use to decide what to work on. It gets worse with every paper digested — a quilt citing ten would bury the author under a thousand lines.

**A4 — the digest's nodes are counted in the quilt's own totals. FIX** (Part 4).
`0 stale of 0 accepted; 149 draft; 1 incomplete; 92 loose`. About 54 drafts are mine; the one incomplete result is Manolache's standing assumptions. The summary is the line I read to answer "how am I doing", and it is wrong in the pessimistic direction — "92 loose" reads as a structural problem and is an artefact of citing one paper carefully.

**A5 — the workbench loop is right, and the report should say so. PASS.**
```
loom accept rl-0004 --yes
# edit one sentence
loom status --stale   → rl-0004  accepted, stale  own-text-changed (2026-09-18)
loom status --explain rl-0004
  --- accepted/rl-0004
  +++ current/rl-0004
  -  ... Let \(U\) be an \(S\)-scheme.
  +  ... Let \(U\) be an \(S\)-scheme, assumed quasi-compact.
```
This is what loom exists to do and it does it exactly, with no ceremony: the state computed rather than stored, the cause named, the diff against the accepted text rather than against a commit. **Nothing else in this report should be read as saying the core is shaky.** Every finding above is about the surfaces around this loop, not about the loop.

**A6 — an annotation is reported anchored while the text it was written against is gone. FIX.**
Plan 0.10 Part B is explicit: *"a text loom never saw — two edits between scans — leaves the annotation unanchored, 'written against a text loom never recorded', rather than pretending."*

Demonstrated on a key that was **never accepted**, so that `loom accept`'s snapshots could not mask the result:

```
loom comment rl-0006 "…" --quote "Let \(G\) be a group algebraic space o"
loom build            # last-seen now knows this text
# edit the file (no build)
# edit it again       (no build)
loom build
  →  written against:  15e553dc876dd4ab226f
     that version frozen on disk?  False
     loom reports anchored=True  detached=False
```

The version is unrecoverable and loom says the annotation is in good order. The *quote* still matches — the selector finds its sentence, which is why `anchored` is true — but "show me the text this was written against" can no longer be answered, and nothing says so.

*The mechanism:* `freeze_moved` has exactly one caller, `render/build.py:187`. The 0.10 plan describes the last-seen cache as *"rewritten in place on every scan"*, and `loom status`, `loom comment`, `loom accept` and `loom source` all scan without freezing. Only `build` and `serve` freeze. An author working entirely in the terminal — the workflow the CLI is for — edits between builds as a matter of course.

*It took three attempts to demonstrate honestly.* The first two times the text survived, because `loom accept` had snapshotted it; had I stopped there I would have reported a bug that does not exist. It reproduces only on a key that was never accepted.

*Fix:* call `freeze_moved` from the scan path rather than from the build path, so any command that scans maintains the cache. Failing that, report the annotation honestly: when `against` names a hash that is neither the current text nor any frozen text, `anchored` must be false and the viewer must say "written against a version no longer recorded". `anchored` is what the viewer draws a mark from and what a re-checking agent trusts; reporting it true when the version is gone is the outcome 0.10 set out to avoid, in its own words.

**A7 — two defences that held. PASS.** See Part 11.

---

# Part 11 — what held

A report listing only failures teaches the wrong lesson about where the design is sound. Four things resisted deliberate attack.

**H14 / A7 — run names cannot escape the runs directory.** `loom ai start "../../../escape"` produced `ai/runs/2026-09-18T16-02-..-..-..-escape/`, with `name = "../../../escape"` preserved verbatim in `run.toml` for display. The slug is sanitised and the name is kept — the right split. A run named `--run` was not parsed as a flag either.

**H24 — the acceptance ledger is genuinely unreachable.** The hostile agent was asked directly to get an accepted key into a wrong state and could not. `loom accept` is the ledger's only writer, it is forbidden by name, and no second path exists. `loom history verify` reports "history verified: 2 steps, 56 version files"; the snapshot machinery is sound.

**H24 — deletion is refused in code, not in prose.** `loom delete`, `loom remove` and `loom rm` all answer "Refuse: loom never deletes your notes". The agent's own summary is the sharpest sentence either document produced: *"The only prohibitions I could not work around were the ones implemented rather than written."*

**A7 — `loom ai start` in a quilt with no AI layer refuses cleanly:** `Error: no ai/ in this quilt; run loom ai init first`, exit 2, nothing created. Worth contrasting with Part 1, where a bad `--run` silently makes a directory.

**The pattern across all four, and the single most useful sentence in this report:**

> **Identity-shaped input is sanitised carefully — `\label`, run names, ids. Path-shaped input to `--run` is not checked at all. Prohibitions written in prose were all worked around; prohibitions implemented in code were not.**

H24 also bounds its own good news: the ledger held because one command is named in one list, and H17 shows that list omits `stamp` and `canonize`, both of which record steps, and steps are what staleness is computed against. **The strongest part of the design rests on the weakest part of the rules.** That is the argument for Part 6's inversion.

---

# Honest notes on the experiment itself

**Three claims are the agents' word, not mine.** H8 ("reviewed clean" after discarding every annotation) I could not reproduce with my own discard syntax. H18's `reference-notes.jsonl` contents and H20's cross-run sequence I read in the agents' reports and in the resulting files but did not re-run from scratch. Reproduce before acting.

**H23 corrects H7, and the agent corrected itself unprompted.** H7 claimed orphan proofs are unreachable by the findings mechanism; H23 found the qualified-key form and said so rather than quietly amending. H7's substance survives — the error message accuses the agent of mis-copying, and the documented path led to the wrong conclusion — but its headline claim was wrong and the document says so.

**H1 is partly about my experiment design.** I wrote the preamble that contradicts §Never. The general problem is still loom's, as Part 6 argues, but the specific contradiction was mine.

**The hostile agent declared an out-of-bounds slip honestly**: it wrote scratch files outside the quilt before thinking about it, because its harness mandates a scratchpad directory while §Never forbids writing outside the run directory. It then could not clean up, because §Never also says "Never delete anything". That conflict is structural and every agent will meet it. *Fix:* one clause in §Never — "…including any scratch directory your harness provides; the run directory is your scratch directory" — and an exception permitting an agent to delete files it created inside its own run.

**Both agents did the mathematics.** This matters for how much weight the tool findings carry. They independently chose the same lemma, independently found that its statement never introduces the torus `T` that its proof uses throughout, independently concluded the Deligne–Mumford hypothesis is redundant *as used*, and independently identified the same extractable lemma. One of them then found that the extracted lemma's only other consumer has a proof the author had annotated "probably works". None of that is tool-testing; it is the work the tool is for, and it is the reason the findings are about friction rather than about features nobody would use.

---

# Index: every finding and where it is adjudicated

| | verdict | section |
|---|---|---|
| F1, H2, H3, H4, H15, H16, A2, A9 | FIX (first) | Part 1 — `--run` |
| F11, F13, F14, F15, F20 | FIX | Part 2 — reading annotations back |
| F2, H6, F16 | FIX | Part 3 — the closure bundle |
| F3, F4, F5, F19, H19, H22, A3, A4 | FIX | Part 4 — `status` as a to-do list |
| F6, F21, H7, H23 | FIX | Part 5 — unattached proofs |
| H17, H5, H10, H18, H20 | FIX | Part 6 — `§Never` |
| H8 | REPORTED, reproduce first | Part 6 |
| H21 | FIX narrowly (add a kind; do not refuse) | Part 6 |
| H1 | FIX (one clause in §Never) | Part 6 |
| H11, H13, A1, A8 | FIX | Part 7 — docs that restate |
| F12 | FIX | Part 8 |
| H9 | FIX the `ok major` half; empty message cosmetic | Part 8 |
| F7 | FIX for `id`/`new`; DISCARD for `check`/`history` | Part 9 |
| F8, F9, H12, F17, F18 | FIX | Part 9 |
| F10 | DISCARD the proposal; keep the observation | Part 9 |
| A5, A6 | PASS / FIX | Part 10 |
| H14, H24, A7 | PASS | Part 11 |

**Discarded outright:** F1's stderr-warning fallback (a warning is what the current design already is), F4's `--prefix` flag (the default should be right, not a flag), F10's lint hint (false-positive rate), F7 for `check`/`history` (whole-quilt queries, not acts), H21's refusal of digest payloads (a transcription can genuinely be wrong).

# Recommended order

1. **Part 1** — one `--run` resolver that never creates. Everything else is friction; this loses work silently, in the cooperative case.
2. **Part 6's H17** — invert `§Never` to an allow-list. One paragraph, and it closes `loom upgrade` and `loom live` at the same time.
3. **Part 2's first item** — `message` and `payload` in `ai findings --json`. One line, and it unblocks the re-check contract 0.10 was built for.
4. **Part 3** — closure covers what is printed.
5. **Part 4's first item** — digest keys out of `status` by default.
6. **A1** — hash-track `ai/orientation.md`, one entry in `tracked_docs()`.

Everything after that is ordinary queue work.
