# Audit of the AI prompt layer (orientation, rules, modes), from an agent session

- **Date:** 2026-10-02
- **Author:** Claude Code agent (Claude Fable 5.1), at the request of the quilt's author
- **Quilt audited:** `relloc` (`/Users/isaac/Desktop/relloc`); loom 0.1.0.dev0, interface 1
- **Files read:** `ai/orientation.md` (3,894 words), `ai/rules.md` (3,422), `ai/formatting.md` (610), the nine files in `ai/modes/` (144–975 words each), `ai/README.md`, `ai/ai-config.toml`, `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json`, and the `--help` of `loom ai`, `ai orient`, `ai start`, `ai check`, `annotate` and `session`.
- **Live evidence:** the agent's own behaviour in the same session, which began with `loom ai orient` and went on to file PDFs, inspect the digest and write the companion report `refs-audit-critique-from-agent-2026-10-02.md`.

Questions asked: what succeeds and what fails; what is too verbose; which essential loom features are not introduced cleanly; how the prompt/mode system, the orientation and the supporting CLI could improve; and how far tighter integration between modes and the CLI would improve rigour and usefulness.

## Verdict

The mode templates are the strongest part, and the orientation plus rules are the weakest. Together they print about 7,900 words every session, repeat themselves heavily, contradict the permissions file in several places, and still don't get an agent to do the first thing the protocol requires. More CLI integration would help a lot, but only for the mechanical half of rigour (shape, provenance, anchoring), not the mathematics.

## What succeeds

- **Boundaries are enforced by code, not by prose.** `.claude/settings.json` denies writes to `drafting/`, `nodes/`, `digests/` and the author-only commands. `loom accept` and `loom refs verify` refuse an agent. `loom ai check SESSION` reports files written outside the session. These hold whatever the agent read or missed.
- **Checks happen at the moment of writing.** `loom annotate --quote` refuses text that is not in the node. `loom refs propose` checks `--source-text` against the page and names the words in `--statement` the quotation does not contain. `loom compile KEY --with proposal.diff` compiles a proposal without touching the quilt. This is the most effective rigour mechanism in the system.
- **The mode templates.** At 150–500 words each (ingest is the exception), each has a clear purpose, input, procedure, output and checklist. The audit / referee / review distinction is sharp and useful: audit assumes correctness and hunts stated-versus-used mismatches, referee hunts for a reason to reject, and review grades everything for improvement.
- **Small rules that change behaviour.** Epistemic labels (`file-verified`, `memory-grade`, `proved-here`); "distinguish what the author asked for from what you noticed"; "never invent a locator"; on a re-check, edit a standing finding rather than replying to yourself; `--discard` versus `--resolve`.
- **"When no mode is named"** (rules.md) is the right idea: compose blocks to fit the question rather than forcing a template.
- **Live state appended to `loom ai orient`**, and `loom link` printing correct viewer links.

## What fails

### 1. The orientation did not produce the required behaviour

After reading the full orientation, the agent in this session:

- never opened a session (`loom ai start`), though live state said "open sessions: none";
- never named itself with `--as`;
- never posted to the chat with `loom session say`;
- wrote its first audit as a chat reply and then as a file in another repository, not as a notes file in a session.

Nothing in the opening lines says "if no session is open, run `loom ai start` before anything else". The instruction to start a session is in §5 under "Your session", after about 2,500 words.

### 2. The terminal conversation is not covered, and §6 points the wrong way

Every rule assumes the author talks through the viewer's Chat. §6 says: "**If the author started you**, park on `next` as below" (orientation.md:101). In a terminal conversation, where the author started the agent and is typing to it directly, parking on `loom session next --wait 120` would block the agent from answering the person in front of it. It is unclear what `loom session say` is for in that setting, so the agent skips the session protocol entirely.

### 3. The prose and the permissions disagree

| Prose | Permissions / code |
|---|---|
| §5 (orientation.md:84): "the author runs `loom refs build`, `verify`, `discard`, `unreadable` and `forget`; those five refuse you" | `loom refs build` is on the rules.md "Run only these" list and allowed in settings.json; the code does not refuse it |
| §7 (orientation.md:117): "you rejoin one with `loom session use`" | `Bash(loom session use*)` is denied |
| §8: "You never write a digest" | `loom digest extract` is allowed, and without `--to` it writes into `digests/`; only a sentence in rules.md §Never stops it |
| — | `loom refs ingest` (files many PDFs) is allowed while `loom refs add` (files one) is denied, including `loom refs add --help` |

There are three lists of what an agent may run (orientation §5, rules.md §Never, settings.json). The rules.md list and settings.json agree with each other; the orientation's prose is what drifted.

### 4. Stale or unresolvable references

- rules.md Findings 4: "Any unambiguous prefix names one, so `conf` is enough", and audit.md: "so `--kind conf` is enough". No kind begins with `conf` (the kinds are objection, suggestion, question, citation, note); this looks like a leftover from a retired kind.
- "rules 5 to 7" (orientation §8) and "rule 7" (every mode's re-check section): rules.md has two numbered lists that both run 1–7 (Standing rules and Findings), so the reference is ambiguous.
- References an agent cannot follow: "DR-173" (ingest.md), "in the second study run five of six corrections…" (orientation.md:77), "book chapter 11" (ai/README.md).
- orientation §2: "`refs/` — what was fetched for each cited work". The code treats `refs/` as the author's drop folder and stores fetched artifacts under `digests/storage/` (see the refs audit).
- ingest.md has two items numbered 6 (Notes on the page, Macros).

### 5. Checklists are self-attested

Every mode ends with "copy into the notes and tick". Nothing checks that a notes file has the required blocks, that the annotation ids it lists exist, that every review finding carries `--severity`, that a diff applies and compiles, or that a `.check.py` exists for each trial. A ticked box is a claim, which the orientation itself warns against for verification ("an agent that 'requested verification' is one summary away from reporting that it verified").

### 6. A mode has no entry point

`ai/README.md` lists `.claude/skills/loom-*/SKILL.md` and `.claude/commands/*.md` as regenerated "when they exist"; in this quilt `.claude/` holds only `settings.json`. "Review rl-0004" therefore depends on the agent finding and reading `ai/modes/review.md` by itself, and on it substituting SESSION and KEY correctly into every command.

## What is too verbose

- **Size.** `loom ai orient` printed 47.3 KB. It overflowed the agent harness's tool-output limit and had to be read back from a saved file before any work started.
- **Repetition.**
  - "session's directory" occurs 30 times across orientation, rules and the nine modes.
  - The five author-only commands are listed four times (orientation §5 and §6, rules Inputs 2, rules Never).
  - `--as` and "include Agent or AI" are explained seven times.
  - "Messages" is a section in both orientation (§6) and rules.
  - Every mode repeats the same "Before you begin" block.
- **The block catalogue.** 32 block definitions load every session. Seven are used by no mode: `[overview]`, `[proof-basics]`, `[dependencies]`, `[reconstruction-plan]`, `[notation]`, `[worked-numerical-examples]`, `[follow-up]`. A given mode uses five to seven.
- **Mode-specific detail in the general document.** The `loom refs propose` bullet in orientation §5 is a single 253-word line of ingest-mode instructions.
- **Rhetoric that does no work.** Standing rule 1 ("a professional mathematician with thirty years of research experience… Superficiality, passive thinking, hand-waving… is failure") adds no actionable constraint beyond rules 2–3.

## Essential features not introduced cleanly

- **The viewer (arras).** It is referenced throughout (annotations "render in place", payloads appear "beside what they would replace", proposals surface "in the proposal box") but never described. An agent cannot picture what the author sees, so it cannot judge what is worth annotating versus saying.
- **States.** Live state reports `loose`, `proved` and `settled`; §4 defines only `draft`, `accepted`, `stale`, `incomplete` and `conflicted`.
- **History.** Steps, stamps and landmarks get one clause in §2 and nothing on how they bear on a review.
- **The copy workflow.** `loom draft DOC --ai NAME`, `loom ai drafts`, `loom ai refresh` and the author's `loom adopt` are spread across §2, draft.md and a stray paragraph appended to §11.
- **Graph commands.** `downstream`, `pop`, `reach` and `unravel` share an identical help line ("Everything downstream of ID…") and are never told apart.
- **Allowed but unexplained commands.** `refs fetch`, `map`, `match`, `recheck`, `resolve`, `session send`, `session watch`, `ai discard`, `build`, and the difference between `loom check` and `loom ai check`.

## Recommendations for the prompt layer and the CLI

1. **Shrink `loom ai orient` to about 600 words, with live state first.**
   - What a quilt is, in a paragraph.
   - The write boundary, once.
   - "No session open: run `loom ai start NAME`."
   - The five or six commands every task needs (`status`, `search`, `source --closure`, `annotate`, `link`, `session say`).
   - Everything else behind `loom ai orient --topic refs|copies|messages|formatting|blocks`.
2. **Generate the permitted-command list, the orientation's command prose and settings.json from one source**, so they cannot drift. Allow `--help` on every command, including author-only ones.
3. **Lower the session ceremony.** Open a session automatically on the first write if none is active, and take the agent's name from an environment variable set by the agent's settings rather than `--as` on every call.
4. **State the two channels.** In a terminal conversation, answer in the terminal and record only durable things (findings, proposals, notes files) through loom. Park on `loom session next` only when started by `loom serve`.
5. **Fix the stale references.** Remove `conf`; name rules instead of numbering them (`rules.md §Findings/re-check`); drop internal document ids or link them; renumber ingest; correct `refs/`.
6. **Prune the block catalogue** to blocks some mode uses, and load each mode's blocks with the mode.

## How far mode–CLI integration would help

Substantially, by extending the pattern that already works in `refs propose`: loom checks whatever can be checked at the moment of writing.

- **`loom ai mode MODE KEY`** prints the template with SESSION, KEY and output file names filled in, the closure commands ready to run, the blocks that mode uses, and any earlier notes and open findings on that key in this session. This replaces "find the file and substitute placeholders" and makes the sequential-application rule ("read the earlier notes first") automatic.
- **`loom ai finish`** validates the output contract:
  - required blocks present in the notes file;
  - every annotation id listed exists and belongs to this session;
  - every finding in review mode has `--severity`;
  - the diff applies and compiles;
  - a `.check.py` exists for each trial mentioned.

  The checklist becomes a check rather than a claim.
- **Ledgers as records.** A `[citation-ledger]` row written through the CLI, checked against a real digest id or a page quote, with `file-verified` refused unless the source resolves. The same for `[uses-ledger]` rows, which could become `\uses` suggestions directly.
- **`loom ai recheck KEY`** lists the session's open findings on a key and whether each anchored quote still exists in the changed text, so a re-check starts from evidence.
- **Mode entry points** (`.claude/commands/review.md` and so on) that call `loom ai mode`, so "review rl-0004" works without the agent hunting for files.

**The limit.** None of this checks the mathematics. It guarantees shape, provenance and anchoring, which is the part an author currently has to police by reading. Quick, question and brainstorm should stay loose: forcing structure there fits the answer to the form, which rules.md already warns against.

## Not checked

- No mode was run end to end; the findings on modes come from reading them, not from executing review or referee on a key.
- Codex (`.codex/rules/loom.rules`, `AGENTS.md`) was not tested; only the Claude Code settings were.
- The behaviour of a `loom serve`-launched agent (one turn per waiting message) was not observed.
- The evidence for §1 is one agent in one session.
