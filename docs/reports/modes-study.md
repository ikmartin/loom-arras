# Modes: a study of the agent contract before MCP

A study of loom's mode templates and the guidance around them — `loom/src/loom/assets/ai/`: `rules.md`, `formatting.md`, `orientation.md` and the nine files in `modes/`, at commit `9f55f919` (2026-10-27) — against the author's own chat prompt, from which the modes came, and against two quilts of real use. It was asked for on 2026-10-27, before plan 0.21 replaces the orientation with an MCP server: the server's instructions will carry the modes, so what the modes should say had to be settled first. A discussion with the author preceded it, and the decisions taken there are part four. No code was changed.

The deliverables are part five (the recommendations) and part six (what they touch). Part seven is what is left open.

## Part one: the verdict

Loom carried the author's prompt over carefully, and the accuracy machinery it carried works. What went wrong is where the output goes and how tightly the templates bind.

- **Nothing a mode writes for the author reaches the author.** Every mode writes `MODE-TARGET.notes.md`. The publisher renders each into a report fragment and indexes its blocks on the session thread's `pipeline`, and arras never reads `pipeline`: the field appears in `arras/src/lib/manifest/types.ts` and nowhere else. `formatting.md` says so itself: a session's notes and diffs "are files the viewer does not display". relloc's one session holds 18 notes files, 11 check scripts and 15 diffs, 874 KB in all. The author has seen them only where an agent's chat message retold them. In particular `[rejected]` and `[meaning-drift-check]`, the two blocks that make a simplify pass trustworthy, have never been read. The author reads the transcript.
- **Most of the ceremony is spent on the agent's own document.** 123 of relloc's 126 annotations sit on keys of the agent document. About a hundred were filed by referee and simplify subagents and resolved minutes later by the main agent, "Applied with the simplify diff": each change was recorded three times — a notes entry, an annotation and a diff — then applied by the agent.
- **Flow is missing.** The author's mode 8, one of the four they reach for most in editing, never reached loom, and relloc's agents rebuilt it three different ways. Two smaller pieces of the prompt also lost their home: mode 1's comprehension of a paper, when ingest became digest verification, and the `[variable-defs]`/`[intuition]` pair.
- **The accuracy machinery works and should be kept whole**: epistemic labels, trials reported with their outputs, typed changes that each state what licenses them, `[rejected]`, `[meaning-drift-check]`, and leaving a suspect passage alone rather than polishing it.
- **Five of fifteen real requests fit no mode.** The global rules carry as much of the work as the templates do.
- **The templates bind too tightly, in the wrong places**: one key per run where the author asks for a section; "follow the template exactly"; prohibitions written for the author's text that contradict the agent document; a checklist to copy and tick.

## How the study was made

- **The contract**: all of `assets/ai/` at `9f55f919`, 11,890 words (orientation 4,074, rules 3,482, formatting 633, the nine modes 3,701).
- **The author's prompt, in two versions.** The one loom imported in September, kept verbatim as `docs/source/global-rules.md` with a part-by-part mapping (DR-38) until both were deleted in `67f0c67b`; it has modes 1–6. And the one the author pasted on 2026-10-27, which adds mode 7 (Review), mode 8 (Flow), the sub-mode `[flow layout]` and a pipeline note. Review reached loom separately, when the author supplied it (DR-153); Flow never did.
- **relloc** (`~/notes/quilts/relloc`), read-only: session `s-2026-10-12-0001` (2026-10-12 to 2026-10-28; 43 transcript messages, 126 annotations, 44 working files), and the author's own prompts from the agent terminal transcripts for that quilt, with the agents' replies and subagent reports where they explain what happened. The work there is an agent document, `drafting-ai/examples-shared.tex`: a standalone set of localization computations for a future section 5.2.
- **The earlier relloc**, restored from a backup at `~/Desktop/relloc`, read-only: one proofreading session on the author's own `drafting/draft4.tex` (2026-10-02), 45 annotations. relloc's annotations rarely touch the author's text because the author has not used it for that yet; this quilt is where they did.
- **The discussion** with the author on 2026-10-27 (part four).

## Part two: the author's prompt, as loom holds it

| the prompt | in loom | verdict |
|---|---|---|
| persona; never bluff; depth over breadth; conceptual simplicity | standing rules 1–2 | kept |
| differentiate fact from speculation | standing rule 3: `file-verified`, `memory-grade`, `proved-here` | sharpened |
| cite exact source text | standing rule 4, cite by id; standing rule 5, the search order | adapted |
| report numerical trials explicitly | standing rule 7: `MODE-TARGET.check.py`, output appended | adapted; the file is unseen, so a trial reaches the author only when a message reports it |
| formatting rules 1–12 | `formatting.md` | the rules were workarounds for the chat window's KaTeX and are obsolete; their purpose is kept — the viewer typesets with MathJax and the quilt's own macros, and `loom link` stands in for `\ref` |
| the pre-send checklist | every mode's `## Checklist`, copied into the notes and ticked | ceremony (part five, §7) |
| the blocks | `rules.md` §Blocks, nearly verbatim, with `[summary]`, `[notation]`, `[uses-ledger]` and brainstorm's four added | kept |
| `[variable-defs]`, a table of every symbol, opening each answer | `[notation]`, for cited papers only | lost for answers: an answer's new symbols are defined nowhere |
| `[intuition]`, the conceptual core in one or two exact sentences, closing each answer | `[summary]`, three lines opening each notes file | changed purpose: the summary says what was done and what the author must decide; the conceptual core is gone |
| nested tags, run inner first, with a divider | §Sequential applications | adapted |
| an untagged query: apply a mode if it fits, or compose blocks | §When no mode is named | kept in `rules.md`, contradicted by orientation §8: "The author asks for a mode by name … Follow the template exactly" |
| mode 1, ingest: `[overview]`, `[proof-basics]`, `[dependencies]`, `[reconstruction-plan]` | `ingest.md` checks a mechanically extracted digest against its paper (DR-173, DR-178) | the comprehension purpose is lost; the four blocks are catalogued and no mode uses them |
| modes 2–6: referee, question, quick, audit, simplify | the mode files of those names; audit gains `[uses-ledger]` | kept |
| mode 7, review | `review.md`; the red-interjection PDF became annotations drawn in place | kept |
| mode 8, flow, and `[flow layout]` | — | missing |
| the pipeline audit → simplify | §Sequential applications | kept |
| the pipeline referee → simplify → flow, and a second referee after a flow that moved a proof | — | missing |
| — | `draft.md`, `brainstorm.md` | loom's own |

One finding is about the process rather than the text. The prompt went on changing after loom copied it, and DR-38's mapping was a one-time translation: nothing carries a later change across. Review came back because the author asked for it; Flow did not.

## Part three: what the evidence shows

### relloc: an agent document under heavy editing

**The author asks for modes in plain words, often several in a row.** "Run each example through referee-> simplify modes before committing the final version, and then once those modes have been completed, edit each for flow and clarity." "Make the change, pass it through referee and simplify and flow/clarity edit, then put it in our shared file." "Edit all of section 8 for clarity and flow while maintaining mathematical accuracy. Make a list of potential places where clarity can be enhanced, then audit the change list and make the edits which survive." The main agent ran referee and simplify as subagents, one key each, named Referee Agent and Simplify Agent, and applied their diffs to the agent document itself.

**Agents already choose a mode unasked.** When the author asked how the procedure changes if a type is fixed first, the terminal agent read `ai/modes/question.md` and answered in its five blocks. When the hypotheses on the target came up, it read `audit.md` and ran the whole audit — six ledgers and four annotations — where `rules.md`'s own example says a question about whether a hypothesis is load-bearing "wants `[hypothesis-ledger]` and nothing else".

**The accuracy machinery did its job.** The referee of Lemma rl-003L-ai found its existence half false as stated, with a counterexample, and supplied the two missing hypotheses with examples showing each is needed. The referees of the examples recomputed every contribution three independent ways. Simplify left suspect passages unsimplified and filed each as an objection, as its rule says. Its `[rejected]` entries were real decisions: "citing Remarks rl-0034-ai and rl-001X-ai for reducedness would save about 45 words, but it would make the closing 'independent' check circular"; "deleting the direct check: the referee added it on purpose, so I compressed it".

**Flow was rebuilt three ways.** A `flow-rl-0035-ai.diff` with no notes at all. A `clarity-rl-003B-ai.notes.md` that borrowed audit's `[patch-list]` and simplify's `[rejected]` and `[meaning-drift-check]`, built a 42-item change list, audited it, and then had a fresh reader — an agent that knew draft 5 and was told not to use Sections 6–7 — read the result, which found 24 more. And, for the Section 7 rewrite at the author's request ("List an explicit rubric to grade the obtuseness/simplification … with explicit examples of good and bad … The primary objective is clarity to ME"), a rubric of ten clarity criteria and seven accuracy guards with good and bad examples taken from the text, the section graded 2/20 before and 19/20 after.

**The annotations recorded what the agent had already done.** Of 126 annotations, 123 are on `-ai` keys: Referee Agent 62, Simplify Agent 48, the main agent 12, the author 4. Of the 107 resolved, the main agent resolved 104; the commonest resolutions are "Applied with the simplify diff (proposal-\*.2.diff) in examples-shared.tex" (32) and "Applied: the referee, simplify and flow revisions of the procedure are now in examples-shared" (28). The 19 still open are exactly what needs the author: their own four questions, the agents' questions to them, "checked" notes, and the choices only they can make — whether the target is smooth or the text should be restated with Cartier divisors (`a-2026-10-27-0001` to `-0004`).

**The work was invisible.** 18 notes files, 11 check scripts and 15 diffs, none shown. The author knew a `[rejected]` entry existed only when the main agent's message repeated it.

**Subagents cost what they cost.** Each ran `loom ai orient`, about 48 KB, five of them within twenty seconds at 20:28; and the author asked "how is it going", "are the background agents stuck?" and "how about now, how goes it" while they ran. That is plan 0.21's business rather than the modes', and is recorded here because it is what running modes as subagents costs today.

### The earlier relloc: the author's own text

One request, after a first message on what the draft must provide for the van Garrel–Siebert paper that cites it: "Please provide annotations on the document text now. Suggest drop in text for every modification you suggest."

- **45 annotations, all on draft4**: 25 objections, 18 suggestions, 2 questions. Every objection and suggestion is graded, and 43 carry a payload (33 `replace`, 8 `after`, 2 `before`).
- **Payloads ran from 9 characters to 2,164.** The smallest fix a typo; the largest is a gloss of the main theorem's symbols with a list of the paper's contributions. Eleven suggestions ran to 700 characters or more (a twelfth is one of them filed again), and every one drops in at one place: a section opening, a status paragraph, a recount of Edidin–Graham, a block of standing hypotheses. Eight of the eleven are resolved, five of them confirmed by the agent as applied in the text, and three are open. The author found these long paragraphs hard to read in the box. The session came before plan 0.20.7's in-place view, which shows a suggestion taken in its key; a whole document read with its suggestions folded in is [WQ-62](../work-queue/WQ-62-suggestions-folded-in.md).
- **There was no notes file at all.** The transcript carried the reports, and the author read and answered them: the first message was 11,669 characters, a table of what the draft owes the paper that cites it.
- **The friction was in anchoring.** Four annotations had to be filed again because their quote began with `\S~` or `\noindent{`, or was `\end{theorem}`, and the viewer marked the whole section; three were resolved twice, once by the author and again by the agent ("Applied"). WQ-60 covers the first.

## Part four: the decisions this study rests on

Taken by the author on 2026-10-27.

1. **A mode is like a skill**: a prompt for a kind of work. It exists for legibility (no garbled LaTeX, visible definitions, a predictable shape the author need not ask for), for mathematical accuracy, and for mathematical clarity.
2. **The agent reaches for a mode on its own when one fits**, without the author naming it, and the modes must not become restrictive. **The agent says in one line of its reply which mode it used.**
3. In editing the author uses audit, flow, simplify and referee most; in learning, question and quick. They often have the agent write an example document and then make dozens of edit requests in the review-style modes.
4. **No new modes now.** Flow is the author's, so it is restored rather than added. Brainstorm is to be scrutinized: it has only ever lived in loom, and the author has never called it.
5. **Vendor-neutral**: nothing shaped for one vendor, such as skill files.
6. **The transcript is what the author reads.** What the viewer does not show is never seen, so a mode writes where the transcript is shown.
7. **Flow and clarity are one mode.**
8. **The pipeline is not enforced.** A mode does not object to being run out of order; that would be too restrictive.
9. **On an agent document the agent has full privilege.** It edits directly and says what it changed, annotates with intention, and may resolve annotations there, another agent's included. The one thing it never does is merge an agent document into the author's.
10. **Short changes are suggestions, and so are drop-in paragraphs.**
11. **Ingest survives to aid the digest, and a work's overview is a page of its own** attached to the work, built in plan 0.21 (decided after the study's first draft, which left mode 1 open).

## Part five: recommendations

### 1. Every output has one home, and the author sees it

| output | on an agent document | on the author's text |
|---|---|---|
| the report: `[summary]` and the mode's blocks | the transcript, one message per piece of work | the transcript |
| a change | made in the document, and listed in the report | a suggestion carrying it; changes that only work together, an agent document (§2) |
| a drafted node | written into the document | a suggestion carrying it, or an agent document when there are several |
| a fault the agent can fix | fixed, and listed in the report | an objection, with the fix as its payload |
| what needs the author: a question, a choice that is theirs, a place they should look | an annotation | an annotation |
| a trial | the script in the session's directory, cited by path; its inputs and exact outputs in the report | the same |

So the notes file, the `proposal-KEY.diff` and the `draft-ID.tex` stop being outputs. The report opens with the mode's name in one line, which is also the one line of the agent's reply in its own app (decision 2), then `[summary]`, then the mode's blocks under their bracketed headings. A report runs long — relloc's referee notes ran 14 to 38 KB — so the viewer should fold a long message after its first block. The publisher's report machinery has no reader and goes with the notes files (part six).

An annotation on an agent document is written because the author must see that place: never one per change already made. Any agent may resolve or discard one there.

### 2. Suggestion or agent document

**A suggestion is a change the author can take or refuse on its own: it lands at one place in one key, however long it is. A change that only makes sense with others, or that moves, merges, splits or reorders results, is an agent document of the passage it touches.** The test is whether the author could take this one and refuse its neighbours.

Length is not the boundary: draft4's drop-in paragraphs ran to 2,164 characters and were taken. Applied to the modes on the author's text, flow's dissolve, a reordering, and a hypothesis moved from one result to another are agent-document work, as is simplify's merge-or-delete across results. A condensation, a lead-in, a new citation in place of an argument, or one symbol split into two are suggestions. Simplify's `[revised]` as a whole is never one suggestion.

### 3. The modes

| mode | verdict | when it fits — the line the index carries |
|---|---|---|
| quick | keep | a question asked in passing whose answer is worth finding again: a definition, a step, a constant ("what is $W_\chi$ a subscheme of?") |
| question | keep; loosen | a question that wants understanding: definitions, examples, edge cases, what breaks without a hypothesis ("how does the procedure change if a type is fixed first?") |
| audit | keep | what a result actually uses: which hypotheses are needed, whether a citation covers its use, whether a statement stands alone ("what are the needed hypotheses on the target?") |
| referee | keep | whether the mathematics is right, before anyone relies on it: new or changed mathematics, a computation to check |
| review | keep | improving a text before someone else reads it: errors, citations, wording and clarity, every finding graded, drop-in text for each |
| simplify | keep | shorter text with the same mathematics |
| flow | restore (§4) | reading order and clarity for a named reader, with the same mathematics ("edit for clarity and flow", "clarity to ME") |
| draft | keep; rewrite (§6) | new mathematics or text from the author's plan or request ("implement each example in section 8", "restate Section 7 for $M(X,\tau)$") |
| ingest | keep; restore its comprehension half (§6) | a cited paper to trust or to understand: its digest checked against the paper, and an overview of what it proves and how |
| brainstorm | retire (§5) | — |

When the author asks for several, they run in the order asked, each reading the report of the one before.

**What a mode file holds**: when it fits, in the one line the index repeats; what it is for, with its guards; the blocks it reports, core and optional; and, where it differs from §1, where its changes go. **What it drops**: `## Before you begin`, since the rules arrive with the server; the checklist to copy and tick; output file names and numbered passes; the single key — a mode's target is whatever the author named, a key, a passage, a section or a document; and the re-check paragraph, which `rules.md` states once.

**The blocks each reports.** Core blocks always appear and optional ones when they apply; this is the predictable shape of decision 1 without decision 2's restriction.

| mode | core | optional |
|---|---|---|
| quick | `[answer]` | `[follow-up]` |
| question | `[intuition]`, `[definition]`, `[worked-examples]`, `[answer]` | `[edge-cases]`, `[stress-test]`, `[follow-up]` |
| audit | `[hypothesis-ledger]`, `[citation-ledger]`, `[self-containedness]` | `[uses-ledger]`, `[sharpenings]`, `[patch-list]` |
| referee | `[gaps-and-ambiguities]`, `[worked-examples]`, `[counterexample]`, `[decision]` | `[referee-review]` |
| review | `[referee-review]` | `[citation-ledger]`, `[self-containedness]`, `[sharpenings]` |
| simplify | `[simplifications]`, `[rejected]`, `[meaning-drift-check]` | — |
| flow | `[structure-map]`, `[flow-edits]`, `[rejected]`, `[meaning-drift-check]` | `[rubric]`, `[fresh-reader]` |
| draft | what was asked, what was done, `[could-not-do]` | `[worked-examples]` |
| ingest | one section per check; on the work's page, `[overview]`, `[proof-basics]`, `[dependencies]`, `[reconstruction-plan]` | — |

Each also opens with `[summary]`, except quick, whose answer is shorter than a summary of it, and question, which opens with `[intuition]`. Where the changes are edits or suggestions, `[patch-list]`, `[referee-revised]` and `[revised]` are those changes, listed, not a second copy of the text.

`[intuition]` returns to question because it is the author's and serves the Learner. It is one or two sentences giving the conceptual core in exact language, never an analogy. The prompt put it last; in loom it opens the report, in place of `[summary]`, because a long message folds after its first block and the conceptual core is what should show while it is folded. `[variable-defs]` does not return as a table, and appears in the viewer as no block at all. Its purpose — that a reader can see what each symbol means — becomes a rule for every answer (§7): a symbol is defined in the sentence that introduces it, or linked to the node that defines it, and the link reads as that node's name and shows its statement on hover.

### 4. Flow, restored

From the author's mode 8, with what relloc's agents added when they rebuilt it.

- **Purpose**: the reading order and clarity of a passage for a named reader, with the mathematics unchanged. The reader is whoever the author names — "someone who understands everything in draft5.tex", "clarity to ME" — and is the author when nobody is named.
- **Guards**: no hypothesis added, dropped or weakened; no argument replaced by a citation; no statement changed; an error that surfaces is flagged and its passage left alone; every original sentence kept, or its removal recorded in `[rejected]` or `[flow-edits]`; the words an open annotation quotes left unchanged, so it stays anchored, as relloc's agents did unasked.
- **Structure before sentences.** When the organization is in question, `[structure-map]` and the structural types come first (the author's `[flow layout]`), and sentences are polished once, in their final place.
- **Types**: hypothesis-placement, essence-first, lead-in, forward-reference, one-symbol-one-meaning, dissolve, condensation, each as mode 8 defines it; a new type is named in the same style and defined in one clause.
- **A rubric** when the pass is large or the author asks for one: criteria each with a good and a bad example taken from the text, graded before and after. relloc's ten are a starting set, not a fixed list: answer first; the reader's own sequence; output first; compute, justify and check kept apart; special cases said once; one name per object; a running example; status visible in one place; a sentence budget; no unflagged forward reference.
- **A fresh reader** at the end: an agent given only what the named reader knows reads the result and lists what still fails.
- **Where changes go**: on an agent document, edited in; on the author's text, the sentence-level types are suggestions and the structural ones an agent document of the passage (§2).

Two pieces of mode 8 do not come across. "Run it only after the mathematics of the passage is settled" and the pipeline note would object to order, which decision 8 rules out. And the compiled `.tex`/`.pdf` pair is the agent document itself, which compiles.

### 5. Brainstorm retires

It was never called in either quilt. Its habits are good for any exploration, so they move to the global rules:

- restate the author's idea as a statement with explicit hypotheses before judging it;
- compute the small cases before giving an opinion;
- search the digests before calling anything new or known;
- record what was tried and why it failed, when it fails;
- offer an idea of your own in one sentence, and do not pursue it unless asked.

What it records becomes plan 0.21.1's notes: a dead end, a counterexample or a decision is a `note` annotation where it was found, and the research-state page holds the rest. Its ceremony goes with it: "stop until they confirm", a `draft-cand-*.tex` per candidate, a notes file. So does its broken sentence, "Never run `loom accept` or paste it; the author decides".

### 6. Draft and ingest, rewritten

**Draft** was used twice in relloc, both times into the agent document. It keeps its guard: the plan's strategy is the author's, and where the plan is wrong the agent says so and stops at that step with `\incomplete`. The plan is the author's message, so there is no plan file. On an agent document the node is written there; on the author's text, one node is a suggestion carrying it, and several are an agent document. `draft-ID.tex` in the session's directory goes, and with it the rule that the author pastes a drafted node.

**Ingest** gets two halves, both aiding the digest.

- **Trust**, as now: the mechanically extracted digest is checked against the paper for completeness, dropped hypotheses, standing assumptions, missing `\uses`, locators and macros. The corrections become suggestions on the digest's nodes, like any other text's, rather than a `proposal-CITEKEY.diff` nobody sees.
- **Understanding**, the author's mode 1, restored: what the paper proves and why it is new, its key definitions and results with their locators, the dependencies between them and where each hypothesis is used, and a plan to rebuild the main proofs. Nothing does this today. A digest's `\section*{Overview}` is only a seed, the first two paragraphs of the paper's introduction copied at extraction (`digest/extract.py`, `_overview`), although `rules.md` tells agents it "is written to be read whole".

The understanding half's home is **a page of its own, attached to the work**, decided with the author on 2026-10-27 and built in plan 0.21 beside the research-state page, as one mechanism for both. A page is Markdown written as messages are, with `$…$` mathematics and links to the work's results, which read as their names and show their statements on hover. The author edits it, an agent writes it through one loom command, and it shows at the top of the work's Info view, where everything about the work rather than of it already stands. Three other homes were weighed and refused:

- **inside the digest**, which holds the paper's words checked against its source, so an agent's reading there would make unchecked text look like the paper (P15);
- **a node**, whose id, label, compile and ledger state are friction for a reading nobody proves or accepts, and whose TeX would have to compile against the paper's macros (WQ-38). What a node would give, links that resolve and a warning when a linked result changes, a page gets from its links;
- **the transcript**, which is found from its session, where a reader looks for an overview from the paper (V7).

The digest's extracted seed stays where it is, as the paper's own words.

### 7. The global guidance

**The contract, kept and stated once**: standing rules 1–7 (with rule 7's script naming loosened, below); naming oneself with `--as`; the author's acts and that they refuse the agent; never claim a result proved with a step missing; never invent a locator; quotes copied exactly; one change per suggestion; what was asked kept apart from what was noticed (standing rule 6).

**Added**:

- define every symbol an answer introduces, or link the node that defines it (from `[variable-defs]`);
- reach for a mode when one fits, compose blocks when none does, and say in one line which;
- the exploring habits from brainstorm (§5);
- full privilege on an agent document, short of merging it (decision 9);
- the homes of §1 and the boundary of §2.

**Ceremony, cut**:

- orientation §8's "Follow the template exactly, and tick its checklist in your notes file", and every checklist;
- `MODE-TARGET` file names and numbered second passes;
- `## Before you begin` in each mode, and "Read `ai/rules.md` once this session" in eight of the nine;
- standing rule 7's per-mode `MODE-TARGET.check.py` (`docs/design/agents.md` already says "no per-mode check scripts"): a script is saved where it can be cited, and named for what it computes;
- §When no mode is named's "Ask which the author wants when it is not obvious", which asks the author a question about loom's filing;
- "Do not insert dividers", which only made sense against the chat.

**Restatement, replaced by a pointer**:

- orientation §8's list of modes, which has drifted: it says review is the mode "the author reaches for most", and that "Findings are annotations". The index in the server's instructions replaces it;
- the author's acts, listed three times (orientation §6, `rules.md` §Inputs item 2 and §Never), kept once;
- orientation §5's command reference, which the MCP tool list replaces (already plan 0.21.1).

**Stale or contradicting**, by the review passes in `CLAUDE.md`:

- orientation §8, "The author asks for a mode by name", against `rules.md` §When no mode is named and decision 2 (pass 5);
- every mode's "Never edit source" and simplify's "you apply nothing", true on the author's text and stated as universal, against orientation §2's agent document and decision 9 (pass 4);
- review "The author reaches for this most" (pass 1);
- brainstorm's broken sentence (pass 9);
- `ingest.md` numbers two items 6 and cites DR-173 in a shipped string, which shipped text never does;
- §Sequential applications names only audit → simplify;
- quick's line "if the author would want to re-read it next week it is quick; if it is a clarification … it is chat and nothing is written": under decision 6 both are in the transcript, and the difference is only how much is written.

`formatting.md` is right as it stands. It gains the definitions rule, and its "a file in your session's directory is not displayed" becomes the reason the notes files go.

### 8. Delivery over MCP

- **The server's instructions carry the index**: each mode's name and its "when it fits" line, and one sentence — reach for a mode when it fits, compose blocks when none does, and say in one line which you used.
- **The full text through a read tool** (`mode NAME`), and the same for a shell agent through the command line (`loom ai mode NAME`), so nothing reads `ai/modes/` by path. The agents in relloc already did this by hand, with `cat` and `sed`.
- **Each mode is also an MCP prompt**, the author's explicit shortcut. A prompt is chosen by the person and a tool by the model, which is why the index and the read tool, not the prompts, are what makes the choice automatic on every client.
- **An edited mode file stays the author's**: the quilt's copy is what the tool serves, kept with the shipped text written beside it as `.new` (invariants, `loom upgrade`).

### 9. The requests against the index

Fifteen of the author's requests, from both quilts, each with what the index would pick and what it should produce under §1.

| # | the request | the text | picks | produces |
|---|---|---|---|---|
| 1 | "Please provide annotations on the document text now. Suggest drop in text for every modification you suggest." | author's | review | graded annotations, each carrying its drop-in text; the report |
| 2 | "make a list three examples in increasing difficulty … implement each … Run each example through referee-> simplify modes … then … edit each for flow and clarity" | agent's | draft, referee, simplify, flow, in that order | edits; four reports; annotations only for what needs the author |
| 3 | "The 11 step list in section 7 should have more \refs so that one can follow the links from the viewer … what are D4, D5 etc?" | agent's | none | edits, and a message saying what changed |
| 4 | "make the change, pass it through referee and simplify and flow/clarity edit, then put it in our shared file" | agent's | referee, simplify, flow | as 2 |
| 5 | "The map $\Res_{M^T/M}$ is defined, why do you think it is not?" | author's | none | the answer; a finding withdrawn if it was wrong |
| 6 | "please revise example 8.2 and example 8.3 to include tikz illustrations of the tropical content" | agent's | none | edits |
| 7 | "please edit all of section 8 for clarity and flow while maintaining mathematical accuracy … the first examples someone who understands everything in draft5.tex sees" | agent's | flow, reader named | edits; a report with the fresh reader's result |
| 8 | "please fix the formatting weirdness in my question and then mark that annotation as resolved" | agent's | none | the fix, or the reason there is none |
| 9 | "Write a short (4-5 sentence) description of the issue to the chat record" | — | none | a message |
| 10 | "The procedure in section 7 … calls $W_\chi$ the fixed subscheme but doesn't say what it is a subscheme of." | agent's | quick | the answer and the edit, in one message |
| 11 | "How does the procedure change if instead a type is fixed first … (I forget whether one wants specializations or generizations)" | agent's | question | the report; the check script cited by path |
| 12 | "Restate Section 7 of the shared copy for M(X,τ), with Corollary rl-003K-ai as the τ = τ_0 case, marking what still needs proof." | agent's | draft | edits, `\incomplete` where unproved; the report |
| 13 | "What are the needed hypotheses on the target X?" | agent's | audit | `[hypothesis-ledger]` above all; annotations for the choices that are the author's |
| 14 | "My understanding of the procedure is that it is simpler … What am I missing, and as written is the procedure obtuse/unclear?" | agent's | question | the answer, with flow's diagnosis and no edits |
| 15 | "Plan the section 7 rewrite. List an explicit rubric … with explicit examples of good and bad … clarity to ME" | agent's | flow: structure, then sentences, with a rubric | edits; the report with the rubric graded before and after |

The index separates every case. The close pairs are quick against question, which differ in how much the answer needs, and audit against referee for 13, which asks what is used rather than whether it is right. Row 13 is where looser templates matter most: the agent ran six ledgers and four annotations for a question one ledger answers.

## Part six: what it touches

- `loom/src/loom/assets/ai/`: `rules.md` and `formatting.md` rewritten (§7); `orientation.md` mostly replaced by the server's instructions (plan 0.21.1); the mode files rewritten to the form of §3; `modes/flow.md` new; `modes/brainstorm.md` removed.
- The publisher's reports: `render/reports.py`, the notes-file pipeline in `render/threads.py`, the report rendering in `render/build.py`, `PipelineStep` and `Thread.pipeline` in `arras/src/lib/manifest/types.ts` and `docs/specs/manifest.md`, and their tests. No reader, so they go.
- arras: the transcript folds a long message after its first block.
- `AGENT_COMMANDS` and the MCP tool table: `mode NAME`.
- Pages: the research state and a work's overview, with the command that writes them and the work's Info view that shows the overview (§6).
- `docs/design/agents.md`: the homes, the boundary, full privilege on an agent document; "modes become tools" made concrete.
- [Plan 0.21](../plans/0.21-mcp.md): §§1–7 are 0.21.1, the contract cut, and 0.21.2, where agent work lands; the pages are 0.21.3; §8 is 0.21.5, the server, and 0.21.7, its prompts and resources.

## Part seven: open questions

1. **Mode 1 beyond one paper.** Ingest's understanding half restores mode 1 for a cited work (§6). What a Learner wants from a textbook chapter, or from several papers on one notion, is not settled by it, and waits for a quilt where someone is learning a field.
2. **Is a report a message like any other, or an entry of its own kind**, folded by default and indexed by the keys it names? This study recommends a message, with the viewer folding long ones; an entry of its own would let a key's view list the reports about it, which the notes-file pipeline was built to do and never did.
3. **Check scripts** stay files in the session's directory, cited by path, while computation is out of scope. When computation comes, a trial may become a record of its own.
