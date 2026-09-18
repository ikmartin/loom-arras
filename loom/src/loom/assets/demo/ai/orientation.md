# Orientation: working in a quilt

You are working inside a **quilt**: a LaTeX-based research project managed by `loom`, usually mathematical, usually aimed at producing one or more papers but never limited to one. A quilt holds results, their dependencies, what the author has accepted, the papers being written from them, and digests of the literature they draw on. Loom exists to make that project workable with an assistant in it.

`loom ai orient` printed this and `ai/rules.md` together: this says where you are, and that says how to work and what your output looks like. Read both once. Then run `loom status` and propose what to do from what it reports.

## 1. What a quilt is

The project is a graph. A theorem-like environment or a section becomes a node when it carries a permanent id, written as a LaTeX label, e.g. `\label{rl-0004}`; an untagged one is not yet a node, and `loom id` is what tags it. Dependencies between nodes are read from the `\ref`, `\cite[postnote]` and `\uses` the author writes. The LaTeX compiles exactly as an ordinary paper, with or without loom. Loom reads the text, computes the graph, keeps a ledger of what the author has accepted, and checks whether accepted text has changed since.

A quilt may hold several documents at once — a paper, a talk, a survey — drawing on one body of results, and it may hold none at all if the work is still being developed. Do not assume there is one paper, or that there is a paper yet.

Nothing you produce enters the project or the ledger unless a person copies it or accepts it. Your job is to help the author: draft what they plan, review what they wrote, digest what they cite, answer what they ask.

## 2. Layout, and what you may write

**Read the paths from the quilt, not from this list.** `[quilt] drafting`, `canon` and `history` in `config.toml` are settable and default to the names below; `loom status --json` reports the masters as they actually are. A quilt that renamed them is still an ordinary quilt.

- `config.toml` — quilt configuration, including the id prefix and the directory names. Read only.
- `drafting/` — the working documents, every one live. `[quilt] main` names the default. Read only.
- `canon/` — landmarks: flat, self-contained copies of a document as it stood at some moment. Nothing in one has an identity, and the scanner never enters it. Read only.
- `nodes/` — one node per file, by convention rather than by rule; a node may equally live inline in a document. Read only.
- `digests/` — cited papers' results as external nodes, one file per citekey. Read only.
- `refs/` — what was fetched for each cited work: its source and PDF, under a directory named by the work's identifier. `loom refs path CITEKEY` prints it. Read only, and not in version control.
- `annotations/log.jsonl` — every review event, appended. Written only by `loom comment` and `loom refs note`; never edit it by hand, and never read it directly when `loom ai findings` or `loom status` will answer the question.
- `.loom/` — the acceptance ledger, the history of steps and the texts they froze, and loom's caches. Never touch.
- `build/` — derived; ignore.
- `ai/orientation.md` — this file. `ai/modes/` — the mode templates. Read only.
- `ai/runs/<run>/` — YOUR run directory, the only place you write files.

The rule: you write only under your run directory, and you write records only through loom commands. Everything else is the author's.

## 3. The source contract in one page

- A node is `\begin{ENV}[Title]\label{ID} ... \end{ENV}` where `ENV` is declared by `\newtheorem` in the master's preamble, or a `\section{Title}\label{ID}`. `ID` is `<prefix>-<local>`, e.g. `rl-0004`; the prefix is this quilt's, from `[quilt] prefix`, and is not `rl` unless this quilt says so. Other labels on the same node are aliases and resolve to it.
- `\begin{...}` and `\end{...}` of theorem-like environments are alone on their lines.
- A proof is `\begin{proof} ... \end{proof}` immediately after its statement, or anywhere as `\begin{proof}[Proof of Theorem~\ref{ID}]`. A statement may have several proofs. Proofs are keyed `ID/proof`, `ID/proof/2`, or by their own label if they have one.
- Dependencies: `\ref{ID}` (and `\eqref`, `\cref`, `\autoref`), `\cite[Theorem 4.1]{CITEKEY}` when a digest for `CITEKEY` exists, and `\uses{ID, ID}` for anything the text does not name.
- `\incomplete{text}` inside a statement or proof marks it as mathematically incomplete. Use it instead of bluffing.
- `\nest{file}` includes a file one section level down; `\input{file}` includes it as written.
- Equations keep the author's labels (`eq:main`); refer to them normally.
- Comments beginning `% !LOOM` are directives loom reads (`% !LOOM tags: ...`, `% !LOOM author: ...`, `% !LOOM see: ID, ID`); they never change the PDF. `see:` links two nodes in the viewer and is never a dependency.
- Digest nodes have ids `<citekey>-<label>`, e.g. `Man12-thm-4.1`; their statements are the cited paper's, verbatim, with locators in the title.

## 4. The ledger and states

The ledger holds acceptances only, written by the author with `loom accept`. A key's state is computed, never written: `draft` (never accepted), `accepted`, `accepted, stale` (the text or a dependency changed since acceptance; `loom status --explain KEY` shows which, and the diff), `incomplete` (contains `\incomplete`), and `conflicted` (two live documents define the same id, so the key has no text and no winner until one definition goes).

Reviews are not states: a key shows how many open annotations it has and who last looked. You never write the ledger and never run `loom accept`.

## 5. Commands you use

Nothing sets `$LOOM_RUN` for you. **Pass `--run` explicitly, naming your run**: a run's name, a prefix of one, or its path all work, and an ambiguous prefix will tell you what it matched rather than guess. Every command below that accepts `--run` logs the call to that run's `run.log`.

Working in the quilt:

- `loom status` (first, always): every key, its state, causes, open annotations; `--stale`, `--draft`, `--incomplete`, `--undigested`, `--explain KEY`; `--json` for tools. This is the to-do list.
- `loom search QUERY --json`: find ids by title, alias, tag or citekey; get a node's file.
- `loom source KEY [--closure]`: prints a key's own text, and with `--closure` exactly the statements it depends on first. Read this, not the directories. It writes no file, so nothing you read can go stale behind you.
- `loom deps KEY [--closure]`, `loom unravel ID`: the graph around a node.
- `loom linearize SPINE --to <file> --no-check`: a whole master flattened into one file, for when a plan or a paper is the context. Masters are not keys, so `loom source` does not apply to them.
- `loom lint`: what is structurally wrong. `loom check`: lint, then compile every master; with `--bundles all` it also compiles every key's closure, which the default does not.
- `loom compile KEY --with proposal.diff`, `loom compile --draft draft-ID.tex`: compiles your proposed text in place of the quilt's, so you can check it before the author applies anything. Nothing in the quilt changes.
- `loom new TAXON "Title" --print`: a skeleton for a node you will draft, printed rather than written. `loom id --next` prints the next free id alone.
- `loom refs path CITEKEY [--pdf]`: where a cited work's fetched artifacts are.

Recording what you found:

- `loom comment KEY "message" --quote "exact text" --kind objection|suggestion|question|ok|citation --run RUN`: a finding anchored to the sentence it concerns. This is how every review result is recorded.
- `--severity major|moderate|minor` grades the fault; `--payload` carries text you are proposing and `--placement replace|after|before` says where it would go; `--reply ID` answers the author; `--resolve ID` closes a finding that is met; `--edit ID` restates one that still stands; `--batch` reads JSON lines from stdin.

Your run:

- `loom ai runs [--all]`: the quilt's runs, as `YYYY-MM-DD: name`.
- `loom ai start "A name"`: open a new run and print its directory. Name it for what you were asked to do.
- `loom ai orient --run RUN`: this document, the quilt's live state, and that run's journal — how you resume a run, yours or another agent's.
- `loom ai findings --run RUN [--json]`: what that run has annotated, with ids, so a re-check can resolve and edit its own findings.
- `loom ai name "A better name" --run RUN`: rename a run once you know what it turned into.

## 6. Your run

A run is one conversation with you and nothing more. It has no mode, no state and no lifecycle: it is never concluded, and you rejoin one by passing `--run` again. Write in its directory:

- outputs named by mode and target: `referee-rl-0004.notes.md`, `draft-rl-0019.tex`, `proposal-rl-0004.diff`, `ingest-Man12.tex`. Where a mode's template says a second pass is numbered, as referee's and review's do, it is: `referee-rl-0004.2.notes.md`.
- `thread.md`: after each significant exchange, append a dated entry saying what was asked, what you did, what you decided and what remains. Keep it; a later session, yours or another agent's, resumes from it.

Loom writes `run.log` there for you, and `run.toml`, which holds the run's name and nothing you need to edit.

## 7. Modes

The author asks for a mode by name. Each has a template in `ai/modes/` with an input contract, a procedure, and an output contract with a checklist. `ai/rules.md` holds what is common to all of them, and applies when no mode is named at all. Follow the template exactly, and tick its checklist in your notes file.

- **audit**: hypothesis, citation, uses, and self-containedness ledgers.
- **referee**: hostile review — gaps, worked examples, counterexamples, verdict.
- **review**: a referee reading to improve rather than to reject; citations, hypotheses, errors and wording, each finding graded by severity. The author reaches for this most.
- **simplify**: shorter text, identical mathematics, as a diff.
- **question / quick**: answers, thorough or brief. If the author would want to re-read it next week it is quick; if it is a clarification of something you just said, it is chat and nothing is written.
- **draft**: a complete node from the author's plan.
- **ingest**: a digest of a cited paper.
- **brainstorm**: explore a topic before anything is proved — candidates, dead ends, what the digests already say.

Findings are annotations. Review mode grades every one with `--severity`; elsewhere you give a severity only when something is actually wrong, and a `--payload` only when you are proposing text. On a re-check you edit a finding that still stands rather than replying to yourself. `ai/rules.md` rules 5 to 7 are the full contract; where this summary and those rules disagree, the rules win.

A digest you produce waits in your run for the author to run `loom ai promote`. A drafted node is previewed by the author and pasted by them, with an id from `loom id --next`. Proposals are diffs the author applies.

## 8. Context economy

Read a key's closure, not directories: it is complete by construction. Do not read `nodes/` wholesale, do not read `build/`, do not read `.loom/`, and do not read the annotation log when `loom ai findings` answers the question. `ai/rules.md` §Inputs is the contract, including the one exception — a digest's overview, which no command prints.

## 9. What you never do

`ai/rules.md` §Never is the list, and it is the file to check: a mode reached through a slash command never passes through this document, so the prohibitions live where that reader will see them. In one line: you write only under your run directory, only through loom commands, and nothing that writes to the quilt on the author's behalf.

## 10. When you are done

Update `thread.md`, list your outputs, and tell the author which are drafted nodes to paste, which are diffs to apply, and which annotations need their decision.
