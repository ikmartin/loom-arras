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
- `notes/` — the author's reference material, if the quilt has one: files, excerpts and research notes that are not cited works and not in any digest. Read it when it bears on the task; it is context, not a source to cite, digest or propose from. Never scanned, in version control. Read only.
- `annotations/log.jsonl` — every review event, appended. Written only by `loom comment` and `loom refs note`; never edit it by hand, and never read it directly when `loom ai findings` or `loom status` will answer the question.
- `.loom/` — the acceptance ledger, the history of steps and the texts they froze, and loom's caches. Never touch, except your own session's directory below.
- `build/` — derived; ignore.
- `ai/orientation.md` — this file. `ai/modes/` — the mode templates. Read only.
- `.loom/sessions/<id>/` — YOUR session's directory, the only place you write files.

The rule: you write only under your session's directory, and you write records only through loom commands. Everything else is the author's.

## 3. The source contract in one page

- A node is `\begin{ENV}[Title]\label{ID} ... \end{ENV}` where `ENV` is declared by `\newtheorem` in the master's preamble, or a `\section{Title}\label{ID}`. `ID` is `<prefix>-<local>`, e.g. `rl-0004`; the prefix is this quilt's, from `[quilt] prefix`, and is not `rl` unless this quilt says so. Other labels on the same node are aliases and resolve to it.
- `\begin{...}` and `\end{...}` of theorem-like environments are alone on their lines.
- A proof is `\begin{proof} ... \end{proof}` immediately after its statement, or anywhere as `\begin{proof}[Proof of Theorem~\ref{ID}]`. A statement may have several proofs. Proofs are keyed `ID/proof`, `ID/proof/2`, or by their own label if they have one.
- Dependencies: `\ref{ID}` (and `\eqref`, `\cref`, `\autoref`), `\cite[Theorem 4.1]{CITEKEY}` when a digest for `CITEKEY` exists, and `\uses{ID, ID}` for anything the text does not name.
- `\incomplete{text}` inside a statement or proof marks it as mathematically incomplete. Use it instead of bluffing.
- `\nest{file}` includes a file one section level down; `\input{file}` includes it as written.
- Equations keep the author's labels (`eq:main`); refer to them normally.
- Comments beginning `% !LOOM` are directives loom reads (`% !LOOM tags: ...`, `% !LOOM author: ...`, `% !LOOM see: ID, ID`); they never change the PDF. `see:` links two nodes in the viewer and is never a dependency.
- Digest nodes carry a cited paper's statements verbatim, with locators in the title. Their ids are derived from the citekey, but not by copying it: punctuation is stripped, so the citekey in `refs.bib` is not the id. Ask instead of guessing — `loom search CITEKEY --json` gives the ids of everything digested from that work.

## 4. The ledger and states

The ledger holds acceptances only, written by the author with `loom accept`. A key's state is computed, never written: `draft` (never accepted), `accepted`, `accepted, stale` (the text or a dependency changed since acceptance; `loom status --explain KEY` shows which, and the diff), `incomplete` (contains `\incomplete`), and `conflicted` (two live documents define the same id, so the key has no text and no winner until one definition goes).

Reviews are not states: a key shows how many open annotations it has and who last looked. You never write the ledger and never run `loom accept`.

## 5. Commands you use

Writing lands in the **active session** — `loom ai orient` names it — so you need not pass anything. **Pass `--session` when you mean another one**: its id, its title, or part of either, and an ambiguous value will tell you what it matched rather than guess. `$LOOM_SESSION` is read where it is set. Every command below that accepts `--session` logs the call to that session's `run.log`.

A session is shared: the author may be working in the one you are in, and their annotations and yours sit together. The record says who wrote each — you are named as the agent you are, never as the author whose git identity this shell happens to carry.

Working in the quilt:

- `loom status` (first, always): every key, its state, causes, open annotations; `--stale`, `--draft`, `--incomplete`, `--undigested`, `--explain KEY`; `--json` for tools. This is the to-do list.
- `loom search QUERY --json`: find ids by title, alias, tag or citekey; get a node's file.
- `loom source TARGET [--closure]`: prints a key's own text, and with `--closure` exactly the statements it depends on first. Give it a document's path instead and it prints that document flattened, every inclusion expanded in place, for when a plan or a paper is the context. Read this, not the directories. It writes no file, so nothing you read can go stale behind you.
- `loom deps KEY [--closure]`, `loom unravel ID`: the graph around a node.
- `loom lint`: what is structurally wrong. `loom check`: lint, then compile every master; with `--bundles all` it also compiles every key's closure, which the default does not.
- `loom compile KEY --with proposal.diff`, `loom compile --draft draft-ID.tex`: compiles your proposed text in place of the quilt's, so you can check it before the author applies anything. Nothing in the quilt changes.
- `loom new TAXON "Title" --print`: a skeleton for a node you will draft, printed rather than written. `loom id --next` prints the next free id alone.
- `loom refs path CITEKEY [--pdf]`: where a cited work's fetched artifacts are.

Reading the literature the quilt cites. **Ask the digest before you read a paper, and read a paper through loom rather than directly** — what you quote must be checkable against the page it came from.

- `loom refs coverage [FRAGMENT]`: what is known about each cited work — whether it has a source, a PDF, page text and a digest. Read this first; a search over a partly digested corpus is a search over silence. An author or title fragment (`loom refs coverage brion`) narrows it to the works it matches and is how you find a citekey.
- `loom refs find TEXT`: search the statements already digested. Every answer says how much of the corpus it could search, and a miss names the fallback.
- `loom refs grep TEXT`: search the raw page text of every cited PDF for a phrase — a literal phrase, not a pattern. The cold-start path. A hit is a page to read, never a quotation: page text is mathematics after a text layer.
- `loom refs page CITEKEY N[-M]`: a page's text and the section it falls in. **The sanctioned read.** Quote only from this.
- `loom refs propose CITEKEY --local thm-4.1 --page N --source-text "…" --statement "…" [--level 1]`: record a result you read. `--source-text` must be the page's own words — **the whole statement, not the first clause**, because it is what the author reads your rendering against; if the statement runs onto the next page, give `--page 353-354` — and it is checked against the page; `--statement` is your LaTeX rendering and is never checked for faithfulness — loom names any of its words the quotation does not contain, and those are usually yours: **the body only** (loom writes the environment, the locator and the label, and refuses a statement that carries its own), and **the paper's words only** — no gloss, no "Equivalently…", no definition of a symbol the statement does not define, no note about which page something is on. Those go in your session's own notes; in the second study run five of six corrections an author had to make were an agent's additions. A proposal is not verified by passing the page check: only the author verifies it, and until then call it a proposal, waiting for the author. Refused with the page attached if the quotation is not there. A work needs its main results (`--level 1`) before anything deeper. `--local` is the paper's own number — `thm-4.1`, `cor-2.3.1` for the first corollary under 2.3, `eq-1` for a numbered display the paper calls a result, `thm-star-1` for an unnumbered one — and a name that is not one is refused.
- **A work with a LaTeX source** (`coverage` says `src yes`) has a mechanical digest; read that first. A result the extractor missed is quoted from the source, not the PDF: `--source-file main.tex` in place of `--page`, with `--source-text` the LaTeX itself, because the PDF's text layer has lost the mathematics — a formula there is often control bytes.
- `loom refs link --from ID --to ID --kind same-notion|generalises|specialises|depends-on|contradicts --why "…" --session SESSION`: **record a relation between two results, with a reason.** When you work out how two papers' results relate, record it here rather than in a notes file: a link is drawn in the author's digest view and found from either end, and prose in your session is found by nobody. A link is an assertion, never checked, never citable.
- `loom refs why ID`, `loom refs links ID`: where a result came from, and what it has been related to.
- `loom refs overview CITEKEY`: a digest's overview, which is written to be read whole.

`loom refs --help` lists the rest; the author runs `loom refs build`, `verify`, `discard`, `unreadable` and `forget`; those five refuse you.

Recording what you found:

- `loom comment KEY "message" --quote "exact text" --kind objection|suggestion|question|confirmation|citation|note --session SESSION`: a finding anchored to the sentence it concerns. This is how every review result is recorded.
- `--severity major|moderate|minor` grades the fault; `--payload` carries text you are proposing and `--placement replace|after|before` says where it would go; `--reply ID` answers the author; `--resolve ID` closes a finding that is met; `--edit ID` restates one that still stands; `--batch` reads JSON lines from stdin.

Your run:

- `loom ai runs [--all]`, or `loom session list`: the quilt's sessions, as `YYYY-MM-DD: title`.
- `loom ai start "A name"`: open a new run and print its directory. Name it for what you were asked to do.
- `loom ai orient --session SESSION`: this document, the quilt's live state, and that session's journal — how you rejoin a session, yours, the author's, or another agent's.
- `loom ai findings --session SESSION [--json]`: what that session has annotated, with ids, so a re-check can resolve and edit its own findings — and what the author decided about each proposal it made: verified, edited (with the edit shown) or discarded (with the reason). Run it first when you rejoin a session.
- `loom ai name "A better title" --session SESSION`: retitle a session once you know what it turned into.

## 6. Messages, and how to wait for one

**The author may be talking to you.** A session carries an inbox, and the composer in the viewer posts into it. Nothing launches you and nothing assigns you work — loom appends a line, and you find it because you asked.

- `loom session next --wait 120 --json --as "Referee Agent"`: **park until something lands**, print it, and exit. One call is one turn. It returns the moment a message arrives rather than on a poll interval; with nothing waiting it comes back empty and you park again. Keep `--wait` under whatever timeout your harness puts on a tool call.
- `loom session send "…" --as "Referee Agent"`: say something back.
- Your cursor moves as you read, so a message survives being read and you resume where you were after a crash. The inbox is a **broadcast**: another agent attached to the same session sees everything you see, and neither of you is handed a task.

**Name yourself.** `--as` is how the record says what wrote a thing. Choose a name that fits the role you were invoked in — `Referee Agent`, `Simplify Agent`, `Tutor Agent` — and **include `Agent` or `AI` in it**. Identity is declared, not sniffed: a command run under an agent's shell with no `--as` is refused rather than guessed at, because an author may ask you to run something and an environment variable is not a claim about who is speaking.

**These commands are the author's and will refuse you**, whatever shell you are in, because each makes a claim only a person can make — *I have checked this*, *I accept this mathematics*:

- `loom accept` · `loom refs verify` · `loom refs discard` · `loom refs unreadable` · `loom refs forget`

**Ask through an annotation, not a request.** Wanting a proposal verified, write a `suggestion` on the result with your reasoning as the body; it surfaces in the proposal box where the author verifies anyway. There is no request object to fill in, deliberately: one would become a queue that nags, and an agent that "requested verification" is one summary away from reporting that it verified.

## 7. Your session

A session is a stretch of work on this quilt, and it may be shared with the author. It has no mode: it is opened, worked in, and closed when the work is done, and you rejoin one with `loom session use` or by naming it with `--session`. Write in its directory:

- outputs named by mode and target: `referee-rl-0004.notes.md`, `draft-rl-0019.tex`, `proposal-rl-0004.diff`, `ingest-Man12.tex`. Where a mode's template says a second pass is numbered, as referee's and review's do, it is: `referee-rl-0004.2.notes.md`.
- `thread.md`: after each significant exchange, append a dated entry saying what was asked, what you did, what you decided and what remains. Keep it; a later session, yours or another agent's, resumes from it.

Loom writes `run.log` there for you. The session's title and state live in `.loom/sessions/index.jsonl`, which is loom's to append to and never yours to edit.

## 8. Modes

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

You never write a digest. `loom refs build` extracts one mechanically from every cited paper whose source can be fetched, and that is most of them. For a work with only a PDF you may **propose** a result with `loom refs propose`: it is verified against the page, held in a file nothing inputs, and enters the digest only when the author compares both texts and verifies it. A proposal that was discarded is refused if you make it again, and the refusal says why — read it, and pass `--supersedes` only if you are answering it. A drafted node is previewed by the author and pasted by them, with an id from `loom id --next`. Proposals are diffs the author applies.

## 9. Context economy

Read a key's closure, not directories: it is complete by construction. Do not read `nodes/` wholesale, do not read `build/`, do not read `.loom/`, and do not read the annotation log when `loom ai findings` answers the question. `ai/rules.md` §Inputs is the contract; a digest's overview is `loom refs overview CITEKEY`.

## 10. What you never do

`ai/rules.md` §Never is the list, and it is the file to check: a mode reached through a slash command never passes through this document, so the prohibitions live where that reader will see them. In one line: you write only under your session's directory, only through loom commands, and nothing that writes to the quilt on the author's behalf.

## 11. When you are done

Update `thread.md`, list your outputs, and tell the author which are drafted nodes to paste, which are diffs to apply, and which annotations need their decision.
