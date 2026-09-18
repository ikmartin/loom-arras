# Orientation: working in a quilt

You are working inside a quilt: a LaTeX paper managed by `loom`, a tool for
atomized mathematical development. Read this document once. Then run
`loom status` and propose what to do from what it reports.

## 1. What a quilt is

The paper is a graph. Every theorem-like environment and every section is a
node with a permanent id written as a LaTeX label, e.g. `\label{rl-0004}`.
Dependencies between nodes are read from the `\ref`, `\cite[postnote]`, and
`\uses` the author writes. The LaTeX compiles exactly as an ordinary paper,
with or without loom. Loom reads the text, computes the graph, keeps a
ledger of what the author has accepted, and checks whether accepted text has
changed since.

Nothing you produce enters the paper or the ledger unless a person copies
it or accepts it. Your job is to help the author: draft what they plan,
review what they wrote, digest what they cite, answer what they ask.

## 2. Layout, and what you may write

- `config.toml` — quilt configuration. Read only.
- `drafting/` — the working documents, every one live. `config.toml [quilt] main`
  names the default. Read only.
- `nodes/` — one node per file, by convention. Read only.
- `digests/` — cited papers' results as external nodes, one file per
  citekey. Read only.
- `refs/` — what was fetched for each cited work: its source and PDF, under
  a directory named by the work's identifier. `loom refs path CITEKEY`
  prints it. Read only, and not in version control.
- `comments/` — human review records. Never write here except through
  `loom comment`.
- `.loom/` — the ledger and snapshots. Never touch.
- `build/` — derived; ignore.
- `ai/orientation.md` — this file. `ai/modes/` — the mode templates.
  Read only.
- `ai/runs/<run>/` — YOUR run directory, the only place you write files.

The rule: you write only under your run directory, and you write records
only through loom commands. Everything else is the author's.

## 3. The source contract in one page

- A node is `\begin{ENV}[Title]\label{ID} ... \end{ENV}` where `ENV` is
  declared by `\newtheorem` in the master's preamble, or a
  `\section{Title}\label{ID}`. `ID` is `<prefix>-<local>`, e.g. `rl-0004`;
  other labels on the same node are aliases and resolve to it.
- `\begin{...}` and `\end{...}` of theorem-like environments are alone on
  their lines.
- A proof is `\begin{proof} ... \end{proof}` immediately after its
  statement, or anywhere as `\begin{proof}[Proof of Theorem~\ref{ID}]`.
  A statement may have several proofs. Proofs are keyed `ID/proof`,
  `ID/proof/2`, or by their own label if they have one.
- Dependencies: `\ref{ID}` (and `\eqref`, `\cref`, `\autoref`),
  `\cite[Theorem 4.1]{CITEKEY}` when a digest for `CITEKEY` exists, and
  `\uses{ID, ID}` for anything the text does not name.
- `\incomplete{text}` inside a statement or proof marks it as
  mathematically incomplete. Use it instead of bluffing.
- `\nest{file}` includes a file one section level down; `\input{file}`
  includes it as written.
- Equations keep the author's labels (`eq:main`); refer to them normally.
- Comments beginning `% !LOOM` are directives loom reads
  (`% !LOOM tags: ...`, `% !LOOM author: ...`, `% !LOOM see: ID, ID`);
  they never change the PDF. `see:` links two nodes in the viewer and is
  never a dependency.
- Digest nodes have ids `<citekey>-<label>`, e.g. `Man12-thm-4.1`; their
  statements are the cited paper's, verbatim, with locators in the title.

## 4. The ledger and states

The ledger holds acceptances only, written by the author with
`loom accept`. A key's state is computed: `draft` (never accepted),
`accepted`, `accepted, stale` (the text or a dependency changed since
acceptance; `loom status --explain KEY` shows which and the diff),
`incomplete` (contains `\incomplete`). Reviews are not states: a key shows
how many open comments it has and who last looked. You never write the
ledger and never run `loom accept`.

## 5. Commands you use

- `loom status` (first, always): every key, its state, causes, open
  comments; `--stale`, `--draft`, `--incomplete`, `--undigested`;
  `--json` for tools. This is the to-do list.
- `loom search QUERY --json`: find ids by title, alias, tag, citekey; get
  a node's file.
- `loom source KEY --closure --run $LOOM_RUN`: prints a key with exactly
  the statements it depends on. Read this, not the directories. It is the
  whole context a review needs, and it writes no file to go stale.
- `loom compile KEY --with proposal.diff`, `loom compile --draft draft-ID.tex`:
  compiles your proposed text in place of the quilt's, to check it before
  the author promotes or applies; nothing in the quilt changes.
- `loom deps KEY [--closure]`, `loom unravel ID`: the graph around a node.
- `loom linearize MASTER --to $LOOM_RUN/<name>.tex --no-check`: a whole master flattened
  into one file, for when a plan or a paper is the context. Masters are
  not keys, so `loom source` does not apply to them.
- `loom comment KEY "message" --quote "exact text" --kind objection|
  suggestion|question|ok --run $LOOM_RUN`: leave a finding anchored to the
  sentence it concerns. This is how every review result is recorded.
  `--reply ID`, `--resolve ID`, `--batch` (JSON lines on stdin).
- `loom lint`: what is structurally wrong; `loom check`: lint plus compile.
- `loom new TAXON "Title" --print`: a skeleton for a node you will draft.
- `loom ai orient --run $LOOM_RUN`: this document plus your run's journal,
  to resume.

`$LOOM_RUN` is your run directory. Pass `--run $LOOM_RUN` on every command
that accepts it; loom logs the call to `run.log` there.

## 6. Your run

Your run is the directory `loom ai start` created. Write there:
- outputs named by mode and target: `referee-rl-0004.notes.md`,
  `draft-rl-0019.tex`, `proposal-rl-0004.diff`, `ingest-Man12.tex`;
- `thread.md`: after each significant exchange, append a dated entry: what
  was asked, what you did, what you decided, what remains. Keep it; a later
  session (yours or another agent's) resumes from it.

Loom writes `run.log` and `annotations.json` there for you.

## 7. Modes

The author asks for a mode by name. Each has a template in `ai/modes/` with
an input contract, a procedure, and an output contract with a checklist.
Follow the template exactly; tick its checklist in your notes file.

- audit: hypothesis, citation, uses, and self-containedness ledgers.
- referee: hostile review, worked examples, counterexamples, verdict.
- review: a referee reading to improve rather than to reject; citations,
  hypotheses, errors and wording, each finding graded by severity.
- simplify: shorter text, identical mathematics, as a diff.
- question / quick: answers, thorough or brief. If the author would want
  to re-read it next week it is quick; if it is a clarification of
  something you just said, it is chat and nothing is written.
- draft: a complete node from the author's plan.
- ingest: a digest of a cited paper.
- brainstorm: explore a topic before anything is proved; candidates,
  dead ends, what the digests already say.

Findings are annotations, graded with `--severity` and carrying a
`--payload` when you are proposing text. On a re-check you edit a finding
that still stands rather than replying to yourself (`blocks.md` rule 7).
Drafts and digests wait in your run for
`loom ai promote` for a digest; a drafted node is previewed and pasted by the author. Proposals are diffs the author applies.

## 8. Context economy

Read a key's closure, not directories. It is complete by construction. Use
`loom search` to find ids and `loom status --json` for the quilt's state.
Do not read `nodes/` wholesale, do not read `build/`, do not read `.loom/`.
When you need a cited result, its digest node's statement is in the closure;
if there is no digest, say so and propose an ingest.

## 9. What you never do

Never edit files outside your run. Never write `annotations.json` by hand.
Never run `loom accept`, `loom atomize`, `loom inline`, `loom import`, or
anything that writes to the quilt on the author's behalf. Never delete
anything. Never claim a result is proved when a step is missing; mark it
`\incomplete`. Never invent a locator; write "unlocated".

## 10. When you are done

Update `thread.md`, list your outputs, and tell the author which ones are
drafted nodes to paste, which are diffs to apply, and which annotations need
their decision.
