# 1. Design principles

This chapter holds every design principle of loom and arras, and nothing else does: what loom is, how the viewer and its annotations look and behave, how a command's output reads, and how the project is built. Later chapters, plans, decision records and code cite a principle by its name (P7, V3) rather than restating it, so there is one place to read a principle and one place to change it. Everything in later chapters is a consequence of this one; when a later chapter and this one disagree, this one is wrong or the later chapter is, and the disagreement is a decision-record event.

## 1.1 The one idea

**[decided]** Loom is a tool for atomized mathematical development. Atomicity married to as-close-to-pure-LaTeX-as-possible is the whole design. A paper is a graph of statements and proofs; each statement is addressable by a permanent identifier; dependencies are read from the text the author already writes; the LaTeX compiles with or without loom.

**[decided]** Loom is not about AI a priori. It is a tool for atomicity. In practice it is designed to work with an AI assistant, and every choice that makes it good for an assistant (bundles, an orientation document, one command to leave a comment) also makes it good for a human collaborator. The AI layer is an optional client of loom, never its reason.

## 1.2 The sets, and how a principle is added

**[decided]** The principles fall into sets, one per thing they govern, and each set has a letter and a section of its own (DR-323-ikmartin):

<!-- principles:sets -->
| set | governs | section | principles |
|---|---|---|---|
| P | What loom is | 1.7 | P1–P13 |
| V | The viewer | 1.8 | V1–V6 |
| A | Annotations | 1.9 | A1–A6 |
| T | Terminal output | 1.10 | T1–T8 |
| C | Construction | 1.11 | C1–C5 |
| K | The command line | 1.12 | K1–K7 |
<!-- /principles:sets -->

**[decided]** **A principle's name is its set's letter and its number**, `V3`, and the name is permanent. Numbers run from 1 in the order principles were added and are never reused or reordered, as decision records and work-queue items are not, so a citation written today still names the same principle after the set grows. A principle that stops holding is not deleted: its heading stays, marked *(retired, DR-NNN)*, so its old citations still resolve to the reason it went.

**[decided]** **Adding a principle** takes a decision record naming it and a heading `### X<n>. Title` at the end of its set's section, `n` the set's next number; the statement first, then why, then what follows from it. **Adding a set** takes an unused letter, a section `## 1.N X · What it governs` appended at the end of the chapter, after every other set, so that nothing before it is renumbered, and a sentence saying what the set covers and where its principles came from. In both cases `python3 scripts/checks/principles.py --write` rewrites the table above and the index in 1.3 from the headings; neither is edited by hand.

**[decided]** **A principle settles many decisions.** A rule that settles one, such as "no compact mode" or "below 900px the layout is undefined", is a decision and belongs in the chapter that decides it, citing the principle it follows from (15.1 cites the V set this way). A plan or a study may propose principles under names of its own; they come here, renamed into a set, when the author decides them, and the plan keeps its names, since a plan is a record of its time.

**[decided]** **Principles change only through decision records.** A record states the principle affected by name, the change, the reason and the date. Implementation may reveal that a principle is wrong; when it does, the record says so and the principle is amended here, not silently bypassed in code. The decision-record format is the one in Appendix A, deliberately small so that records get written.

**[decided]** `scripts/checks/principles.py`, run by `scripts/verify`, holds this chapter to these rules: every set has its row, every principle its line in 1.3, numbers rise without a gap, and every principle a chapter, a specification, an instruction file or a source comment cites exists.

Names elsewhere in the project that predate this chapter:

- Plans 0.13.3, 0.14, 0.15 and `review-panel-and-precise-dependencies.md` call the viewer principles P1–P6; they are V1–V6.
- The annotation study (`docs/reports/annotation-study.md`) calls the annotation principles A1–A6, the names they keep.
- Chapter 13 numbered the principles of construction 1–5 in its 13.1; they are C1–C5.
- The decision records' principle column names P1–P13, which kept their numbers.

## 1.3 Every principle at a glance

<!-- principles:index -->
| name | principle |
|---|---|
| [P1](#p1-source-is-latex-and-nothing-an-author-writes-lives-elsewhere) | Source is LaTeX, and nothing an author writes lives elsewhere. |
| [P2](#p2-author-data-in-the-source-decisions-in-the-ledger-derived-data-never-durable) | Author data in the source, decisions in the ledger, derived data never durable. |
| [P3](#p3-states-are-computed-never-stored) | States are computed, never stored. |
| [P4](#p4-one-mechanism-per-concept-one-write-path-per-kind-of-record) | One mechanism per concept, one write path per kind of record. |
| [P5](#p5-the-graph-is-defined-by-labels-and-environments-never-by-paths) | The graph is defined by labels and environments, never by paths. |
| [P6](#p6-config-only-for-what-the-preamble-cannot-say) | Config only for what the preamble cannot say. |
| [P7](#p7-loom-never-modifies-an-author-file) | Loom never modifies an author file. |
| [P8](#p8-no-editor-server-model-or-credential-is-required-by-any-command) | No editor, server, model, or credential is required by any command. |
| [P9](#p9-local-models-only) | Local models only. |
| [P10](#p10-comments-declare-they-never-command-they-never-change-typeset-output) | Comments declare; they never command; they never change typeset output. |
| [P11](#p11-the-build-interface-and-the-write-api-are-the-product-boundaries) | The build interface and the write API are the product boundaries. |
| [P12](#p12-the-paper-compiles-from-the-quilt-root-on-any-tex-on-overleaf) | The paper compiles from the quilt root, on any TeX, on Overleaf. |
| [P13](#p13-loom-verifies-what-it-can-reports-what-diverges-repairs-nothing-and-never-blocks-work) | Loom verifies what it can, reports what diverges, repairs nothing, and never blocks work. |
| [V1](#v1-open-on-the-thing-itself) | Open on the thing itself. |
| [V2](#v2-say-it-once-in-the-place-that-governs-it) | Say it once, in the place that governs it. |
| [V3](#v3-claim-only-what-is-known) | Claim only what is known. |
| [V4](#v4-name-the-question-one-element-one-question) | Name the question. One element, one question. |
| [V5](#v5-following-a-connection-must-not-cost-the-thing-you-followed-it-from) | Following a connection must not cost the thing you followed it from. |
| [V6](#v6-show-less-rather-than-more-by-default) | Show less rather than more by default. |
| [A1](#a1-the-text-comes-first) | The text comes first. |
| [A2](#a2-one-annotation-one-mark) | One annotation, one mark. |
| [A3](#a3-draw-only-what-loom-knows) | Draw only what loom knows. |
| [A4](#a4-one-channel-one-question) | One channel, one question. |
| [A5](#a5-opening-an-annotation-never-costs-the-text) | Opening an annotation never costs the text. |
| [A6](#a6-quiet-by-default) | Quiet by default. |
| [T1](#t1-lead-with-the-verdict) | Lead with the verdict. |
| [T2](#t2-group-count-then-list) | Group, count, then list. |
| [T3](#t3-every-problem-names-its-next-command) | Every problem names its next command. |
| [T4](#t4-use-the-readers-words-not-the-implementations) | Use the reader's words, not the implementation's. |
| [T5](#t5-make-the-numbers-add-up-and-fit-the-screen) | Make the numbers add up, and fit the screen. |
| [T6](#t6-a-command-that-takes-more-than-a-couple-of-seconds-shows-that-it-is-alive) | A command that takes more than a couple of seconds shows that it is alive. |
| [T7](#t7-say-only-what-happened) | Say only what happened. |
| [T8](#t8-machine-output-carries-what-the-text-carries) | Machine output carries what the text carries. |
| [C1](#c1-the-scanner-before-everything) | The scanner before everything. |
| [C2](#c2-vertical-slices) | Vertical slices. |
| [C3](#c3-the-fixture-is-the-contracts-executable-form) | The fixture is the contract's executable form. |
| [C4](#c4-author-files-are-sacred-from-the-first-commit) | Author files are sacred from the first commit. |
| [C5](#c5-two-tools-in-two-languages-sharing-nothing-but-specs) | Two tools, in two languages, sharing nothing but `specs/`. |
| [K1](#k1-one-action-one-command-one-name) | One action, one command, one name. |
| [K2](#k2-one-idea-one-flag-one-meaning) | One idea, one flag, one meaning. |
| [K3](#k3-refuse-what-is-not-understood) | Refuse what is not understood. |
| [K4](#k4-a-command-does-what-its-name-says-and-nothing-more) | A command does what its name says, and nothing more. |
| [K5](#k5-guard-by-consequence-uniformly) | Guard by consequence, uniformly. |
| [K6](#k6-the-help-is-a-map-of-the-work) | The help is a map of the work. |
| [K7](#k7-one-thing-one-name-everywhere) | One thing, one name, everywhere. |
<!-- /principles:index -->

## 1.4 Signs that a feature is bad

**[decided]** A proposed feature is antithetical to the design if it exhibits any of the following. The list is a filter, not a guideline; one hit is enough to reject or redesign.

1. It needs new syntax beyond `\uses`, `\incomplete`, and `\nest`.
2. It needs configuration where the preamble already says the answer.
3. It writes to an author's source file.
4. It introduces a second source of truth for anything.
5. It stores a state rather than computing it.
6. It requires a running process for something a command could do.
7. It only makes sense with a model in the loop.
8. It needs an API key.
9. It couples arras to a source language, to loom, or to a kind of event.
10. It names a directory for a property loom can compute.
11. It writes a record format that loom does not own (an annotation file written by hand, a ledger row written by an agent).
12. It makes a comment change what the PDF says.
13. It requires an editor, a server, or a particular agent.
14. It reinvents something LaTeX already has (`\input` for transclusion, multiple `\label`s for aliases, `\newtheorem` for taxa, TeX groups for scoped macros).

## 1.5 The test for a proposed feature

**[decided]** Before adding a feature, answer in writing:

1. Which principle motivates it? If none, stop.
2. Which sign in 1.4 does it come closest to? Explain why it does not cross the line.
3. What is the one mechanism it uses? If it introduces a second mechanism for an existing concept, redesign.
4. Where does its data live: source, ledger, or derived? If it needs a fourth place, redesign.
5. Does the paper still compile with plain `pdflatex` from the root, and on Overleaf, with the feature in use? If not, stop.
6. Does arras need to learn anything to display it? If arras needs to know what the feature means (rather than render a label, a link, a diff, or a diagnostic), redesign.
7. Can it be described in the README's contract page in two lines with an example? If not, it is too big or too clever.

Record the answers as a decision record (Appendix A) whether the feature is accepted or not.

## 1.6 Things the principles do not decide

The principles do not decide names, directory conventions, or command vocabulary; those are in later chapters and may change more freely. They do not decide what a "good" proof is, how review should be conducted, or how much an author should atomize; those are the author's. They do not decide the future corpus (Chapter 2); they only ensure that nothing built now forecloses it.

## 1.7 P · What loom is

The principles that decide what loom and arras are. Each is stated, followed by one sentence of reason and one concrete consequence. All are **[decided]**.

### P1. Source is LaTeX, and nothing an author writes lives elsewhere.

Mathematicians already know LaTeX; every construct the tool needs is expressed as a label, an environment, a citation, or one of three macros that print nothing. Consequence: there is no node file format, no frontmatter language, no markup beside LaTeX. The identity of a node is a `\label`; its kind is its environment; its dependencies are its `\ref`s.

### P2. Author data in the source, decisions in the ledger, derived data never durable.

Three kinds of information have three homes, and nothing fits in more than one. Consequence: `config.toml` has a handful of keys; the ledger records acceptances only; `build/` can be deleted at any moment and regenerated.

### P3. States are computed, never stored.

A stored state can disagree with the source; a computed one cannot. Consequence: "stale", "draft", "reviewed", "proved", and "settled" are all computed from records and the current text on every query. Nothing writes the word "stale" anywhere.

### P4. One mechanism per concept, one write path per kind of record.

Two ways to say the same thing drift apart. Consequence: `\input` is transclusion, `\ref` is dependency, `\newtheorem` is taxon, `loom accept` is the only writer of the ledger, `loom annotate` is the only writer of annotation records.

### P5. The graph is defined by labels and environments, never by paths.

Where a file lives carries no meaning. Consequence: one file per node and twelve lemmas in one section file are the same specification at two granularities. `nodes/` is a convention `loom new` follows, not a rule the scanner enforces. No directory exists to hold a property loom can compute (there is no `loose/` directory; loose is computed).

### P6. Config only for what the preamble cannot say.

The preamble is the author's declaration of their conventions; the tool reads it. Consequence: taxa come from `\newtheorem`, style classes from `\theoremstyle`, macros from the preamble closure, the engine from `% !TEX program`. `config.toml` names the default master, the masters directory, the id prefix, and a default engine, and almost nothing else.

### P7. Loom never modifies an author file.

An author's file is theirs; a tool that edits it in place is a tool that destroys work. Consequence: every operation that would change a file either writes to a destination the user names (`atomize SRC DEST`), writes a new file (`new`, `import` into copies), or prints a patch (`id`). `loom delete` exists only to say that loom will not delete. The in-place writers are the ledger and loom's own record files.

### P8. No editor, server, model, or credential is required by any command.

Every command runs from a terminal against files. Consequence: Emacs, VS Code, Overleaf, Claude Code, and Codex are all clients; none is assumed. Loom holds no API key and imports no model SDK. A language server and two editor plugins exist (Chapter 16); they are clients like the rest, and no loom command requires one.

### P9. Local models only.

Any model is reached through a local interface: a model running on the machine, or an agent CLI operated locally. Consequence: the runner contract names a local command; there is no hosted-API path.

### P10. Comments declare; they never command; they never change typeset output.

A `% !LOOM` directive is a fact the scanner reads, never an action loom performs, and never something that alters the PDF. Consequence: `% !LOOM ignore` and `% !LOOM tags:` exist; `% !LOOM accept` and `% !LOOM nest` do not. Anything that changes the typeset document is a macro (`\nest`), because LaTeX must see it.

### P11. The build interface and the write API are the product boundaries.

Loom and arras share no code; they share two documents. Consequence: loom publishes a build directory conforming to the specification; arras reads it and nothing else. Arras knows only that a directory changed, never what kind of change or why.

### P12. The paper compiles from the quilt root, on any TeX, on Overleaf.

Portability is a property of the source, not of the tool. Consequence: all paths are root-relative, local style files sit at the root, no `TEXINPUTS`, no shell escape, no absolute paths.

### P13. Loom verifies what it can, reports what diverges, repairs nothing, and never blocks work.

The head is always the files on disk, and the history is a log of what loom was told, never a claim about the filesystem; a divergence between the two is a fact to report, not a fault to mend. Consequence: an edited landmark, a hand-edited record, a retired id written under again, and two live definitions of one id are each reported with the exact commands that would resolve them, the rest of the quilt builds normally, and no command creates a step, moves a file, or rewrites a record of its own accord to make the report go away.

## 1.8 V · The viewer

How every surface of arras is judged: what it shows, where, and how much. They came out of the reading work of plans 0.13.3 and 0.14 rather than preceding it, each has cost something to follow, and every surface since is checked against them, one row per element (the principles check of plans 0.14 and 0.15). Chapter 15 decides the layout they leave open. All are **[decided]**.

### V1. Open on the thing itself.

The first screenful belongs to what the reader came for. What the application has to say *about* that thing goes to an edge or behind a control.

### V2. Say it once, in the place that governs it.

Where two surfaces state the same fact, one is deleted rather than restyled, and the survivor is whichever one controls the fact.

### V3. Claim only what is known.

Where the viewer does not know something it shows nothing rather than something plausible. A marker says the one thing that cannot be inferred and no more.

### V4. Name the question. One element, one question.

Every element exists because a reader asks something at that moment. If the question cannot be named in one short sentence, the element goes; if two can be named, it is two elements; if two elements answer one question, one goes. Two riders: **a place is not an element** — a rail or a panel groups elements, and the test for a place is whether its elements' questions are asked at the same moment — and **the question is the reader's, not the system's**, which is what condemns a section reporting that a node is "in no document".

### V5. Following a connection must not cost the thing you followed it from.

The viewer's subject is how texts relate; a relation has two terms; a viewer that holds one term can only show a relation by destroying the other.

### V6. Show less rather than more by default.

Unless something has a good reason to be shown, don't show it. Corollaries: simpler is better, and visual noise is bad.

## 1.9 A · Annotations

The viewer principles restated for how an annotation is drawn and how a reader reaches it: the `style()` and `interact()` of the annotation study (`docs/reports/annotation-study.md` §3), which plan 0.15 built and 15.3.1 implements. All are **[decided]**.

### A1. The text comes first.

At rest the page shows marks and nothing else: no open boxes, and at most one count per node. An annotation marks its place and waits to be opened.

### A2. One annotation, one mark.

On the page an annotation appears once: as a mark, or, with no anchor, as the single count on its node. The lists that show it (What it did, the tray, Context) link to it rather than restate it.

### A3. Draw only what loom knows.

A resolved annotation looks resolved. A detached one is never drawn at a guessed place; it is listed as detached. One written against text that has changed is not marked in the new text. No state is shown only as a word.

### A4. One channel, one question.

Each visual channel answers exactly one question, and no two channels answer the same one:

| channel | answers |
|---|---|
| hue | what kind of thing is said |
| weight | how severe (objection and suggestion; the other kinds take the middle step) |
| wash | which annotation's box is open, whatever its kind and severity, at one strength; at 3%, that it is settled |
| shape | what it is attached to: an underline for a phrase, a rule for a display, a tint for a PDF span, an outline for a box |

### A5. Opening an annotation never costs the text.

A box never covers the words it is about. Travel between a mark and its record is one gesture each way and leaves both on screen.

### A6. Quiet by default.

This is the principle against visual noise.

- At rest only open, top-level annotations are drawn.
- Settled annotations (resolved or discarded, marked by hand) are not drawn until the reader turns them on, and then at 3% wash with the underline at half weight and 50% opacity, the words untouched.
- The system uses four hues, one neutral and three weights, and nothing else.
- An annotation looks the same on every surface: text, PDF and hover card.

## 1.10 T · Terminal output

How what a command prints reads, for a person at a terminal and for an agent reading the same text. 12.1 has the mechanics these rest on: `--json` alone on stdout, diagnostics and progress on stderr. T1–T6 were drawn from what made `loom refs build`'s report unreadable on a real quilt (DR-323-ikmartin); the CLI study of 2026-10-02 (`docs/reports/cli-study.md`) sharpened them and added T7 and T8 (DR-324-ikmartin). The shape of the command line itself, as opposed to what one command prints, is the K set (1.12). All are **[decided]**.

### T1. Lead with the verdict.

The first lines answer "did it work, and do I need to do anything?"; detail comes after, for the reader who wants it. A report that ends without saying whether anything is wrong leaves the reader to work it out from the detail. A success that leaves work undone says so: "no changes to incorporate" while a change waits behind a flag, or "already up to date" over a conflict, is a verdict that is false.

### T2. Group, count, then list.

The same sentence is never printed N times: it is written once, as a heading with its count, and only what varies is listed under it, sorted and aligned. A reader should learn how many and of what before reading any one of them. Order serves the reader: the author's own results before the cited works' machine-made ones, which must never drown them; and a list cut short says what it left out (`… and 85 more`).

### T3. Every problem names its next command.

A line that implies action ends with the exact command that resolves it, as P13 asks of every divergence loom reports; what needs no action is summarised as a count rather than enumerated. A refusal names what blocks it and the flag or edit that clears it. The command named must work in the state that prompts it: advice that names a command which then does nothing (mapping a work that has no PDF, editing a file loom never re-reads) is worse than none, so a suggested command is tested in that state.

### T4. Use the reader's words, not the implementation's.

Output names what the reader recognises: their file names, citekeys, titles and the commands they type. Internal storage paths, hashes, truncated keys and the implementation's verbs ("adopts", "offered") stay out of it.

### T5. Make the numbers add up, and fit the screen.

Parts sum to the totals they claim, and each count says what it counts. Lines stay under about 100 columns, and one indentation pattern holds throughout: a heading, then its items indented beneath it. An identifier is never truncated to fit: a cut citekey or id is a different name, and two cut alike are indistinguishable, so a long name goes last on its line, or the line wraps.

### T6. A command that takes more than a couple of seconds shows that it is alive.

It names the stage it is in, the item it is on, that item's place in the count (`7/18`) and the time elapsed, refreshed at least every few seconds, so a reader never has to guess between waiting and stuck. An item that runs unusually long says so ("still compiling, 40 s") rather than going quiet. Progress goes to stderr, never into what a script or `--json` reads, and where stderr is not a terminal it is one plain line per item rather than a line that rewrites itself. Speed comes first: a command a person runs many times a day is made fast enough to need no progress line, and progress is for what is still slow after that.

### T7. Say only what happened.

Output describes what the command did and nothing it did not: no fetch reported for a fetch that did not happen, no "pass" over a result left broken, no "wrote" for a file that was skipped, and a dry run marked as one. This is V3, claim only what is known, for the terminal.

### T8. Machine output carries what the text carries.

Every command that reports offers `--json`, and its JSON holds everything the text says rather than a thinner subset, built from the same report so that the two cannot drift. Stdout holds only that document, on failure as on success.

## 1.11 C · Construction

How the project is built and changed, from the plan's first milestones (Chapter 13) onward. All are **[decided]**.

### C1. The scanner before everything.

Nothing else can be tested without it, and the source contract is the part most likely to be wrong on real papers. It was built against the demo quilt first, then the synthetic quilt, then Manolache, then ACGS.

### C2. Vertical slices.

Each milestone runs end to end (source to arras page) for a growing subset of the contract, rather than completing one layer at a time.

### C3. The fixture is the contract's executable form.

From milestone 2 onward, every change to loom's output regenerates the fixture and every change to the interface is a change to the fixture first.

### C4. Author files are sacred from the first commit.

The tests that enforce P7 (4.8) are written before any command that touches a file.

### C5. Two tools, in two languages, sharing nothing but `specs/`.

Loom and arras began as two repositories and now live in one, each with its own build, tests and release; they still meet only at the specifications, which is what keeps P11 a fact of the code and not only of the design.

## 1.12 K · The command line

The shape of the command line, as opposed to what one command prints (the T set, 1.10): which commands exist, what their flags mean, what they accept and do, and how a person finds them. Drawn from the CLI study of 2026-10-02 (`docs/reports/cli-study.md`), which found that most of what is structurally wrong with the command line is invisible to the T set (DR-324-ikmartin). All are **[decided]**.

### K1. One action, one command, one name.

No command has an alias and no two commands perform one act; a step of a pipeline is a flag of the pipeline, not a command of its own; a refusal is a line of help, not a command. A second name for one thing is a second thing to learn and a doubt about whether they differ.

### K2. One idea, one flag, one meaning.

A flag means the same thing on every command that takes it, and an idea has one flag wherever it appears: who is acting, a reason, the file to write, a session, consent to use the network. A flag whose meaning changes between commands is a mistake waiting for the second command.

### K3. Refuse what is not understood.

Every argument is checked before any work begins, and one that names nothing or holds a value the command does not understand — an unknown key, work, engine, date or level — is refused by name with exit 2, as 12.1 says. Accepting it silently, and acting on a guess or on nothing, reports a success that did not happen.

### K4. A command does what its name says, and nothing more.

A command that reads never writes, a command that prints a patch never records one, a refusal leaves no trace, and a dry run touches nothing. Housekeeping a command did not announce is a side effect the reader cannot see or undo.

### K5. Guard by consequence, uniformly.

Every act that is the author's alone, or that destroys, refuses an agent the same way and asks before destroying, whichever command performs it and whatever name the caller declares. The guard is on the act, not on the command that happens to reach it.

### K6. The help is a map of the work.

`loom --help` groups the commands by the task they serve, puts the person's commands first, marks the agent's and the upkeep commands as such, and gives each a full first sentence. A newcomer finds the command for what they want to do without reading every name.

### K7. One thing, one name, everywhere.

The command line, the viewer and the book call a thing by one name, and a state by one word: if the viewer says Library, so does the command line. Two names for one thing make a reader wonder whether they are two things.
