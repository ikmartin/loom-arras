# Principles

Every design principle of loom and arras is here and nowhere else: what loom is, how the viewer and its annotations behave, how a command's output reads, how the command line is shaped, and how the code is built. Elsewhere a principle is cited by its name (`P7`, `V3`) rather than restated.

A principle's name is its set's letter and its number, and the name is permanent. Numbers run from 1 in the order principles were added and are never reused. A principle changes by editing it here, with the reason in the commit message; one that stops holding keeps its heading, marked *(retired)*, so its old citations still resolve. A new principle is a heading `### Xn. Title` at the end of its set, and a new set is a section `## X · What it governs` at the end of this file. `python3 scripts/checks/principles.py --write` regenerates the two tables below from the headings, and the check fails when a principle cited anywhere in the repository does not exist.

## The one idea

Loom is a tool for mathematical research built on atomicity married to as-close-to-pure LaTeX as possible. Mathematics is a graph of statements and proofs; each statement is addressable by a permanent identifier; dependencies are read from the text the author already writes; and the LaTeX compiles with or without loom.

Loom does not require an AI. It is a complete tool for reading, exploring, drafting and reviewing on its own, and every choice that makes it good for an assistant should also make it good for a person. It is also built to be excellent with an AI assistant, and much of its design exists for that.

<!-- principles:sets -->
| set | governs | principles |
|---|---|---|
| P | What loom is | P1–P15 |
| V | The viewer | V1–V6 |
| A | Annotations | A1–A6 |
| T | Terminal output | T1–T8 |
| C | Construction | C1–C5 |
| K | The command line | K1–K7 |
<!-- /principles:sets -->

<!-- principles:index -->
| name | principle |
|---|---|
| [P1](#p1-mathematics-is-latex-and-nothing-an-author-writes-as-mathematics-lives-elsewhere) | Mathematics is LaTeX, and nothing an author writes as mathematics lives elsewhere. |
| [P2](#p2-author-data-in-the-source-decisions-in-the-ledger-records-in-logs-loom-owns-derived-data-never-durable) | Author data in the source, decisions in the ledger, records in logs loom owns, derived data never durable. |
| [P3](#p3-states-are-computed-never-stored) | States are computed, never stored. |
| [P4](#p4-one-mechanism-per-concept-one-write-path-per-kind-of-record) | One mechanism per concept, one write path per kind of record. |
| [P5](#p5-the-graph-is-defined-by-labels-and-environments-never-by-paths) | The graph is defined by labels and environments, never by paths. |
| [P6](#p6-config-only-for-what-the-preamble-cannot-say) | Config only for what the preamble cannot say. |
| [P7](#p7-loom-changes-an-authors-file-only-when-the-author-incorporates-a-change-and-keeps-the-old-text-first) | Loom changes an author's file only when the author incorporates a change, and keeps the old text first. |
| [P8](#p8-no-editor-server-model-or-credential-is-required-by-any-command) | No editor, server, model, or credential is required by any command. |
| [P9](#p9-loom-calls-no-model-and-any-agent-may-attach) | Loom calls no model, and any agent may attach. |
| [P10](#p10-comments-declare-they-never-command-they-never-change-typeset-output) | Comments declare; they never command; they never change typeset output. |
| [P11](#p11-the-build-interface-and-the-write-api-are-the-product-boundaries) | The build interface and the write API are the product boundaries. |
| [P12](#p12-a-document-compiles-from-the-quilt-root-on-any-tex-on-overleaf) | A document compiles from the quilt root, on any TeX, on Overleaf. |
| [P13](#p13-loom-verifies-what-it-can-reports-what-diverges-repairs-nothing-and-never-blocks-work) | Loom verifies what it can, reports what diverges, repairs nothing, and never blocks work. |
| [P14](#p14-no-unnecessary-friction) | No unnecessary friction. |
| [P15](#p15-nothing-unchecked-looks-checked) | Nothing unchecked looks checked. |
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

## P · What loom is

The principles that decide what loom and arras are. Each is stated, followed by its reason and a concrete consequence.

### P1. Mathematics is LaTeX, and nothing an author writes as mathematics lives elsewhere.

Mathematicians already know LaTeX, and every construct the tool needs is a label, an environment, a citation, a directive comment, or one of three macros that print nothing. Consequence: there is no node file format and no markup beside LaTeX for mathematics. A node's identity is a `\label`, its kind is its environment, its dependencies are its `\ref`s. What is said *about* the mathematics (annotations, notes, transcripts) is not the author's source; it lives in records loom writes, one command for each kind (P2, P4).

### P2. Author data in the source, decisions in the ledger, records in logs loom owns, derived data never durable.

Four kinds of information have four homes, and nothing fits in more than one. Consequence: `config.toml` has a handful of keys; the ledger records acceptances only; annotations, the history and sessions are append-only logs that only loom writes; `build/` can be deleted at any moment and regenerated.

### P3. States are computed, never stored.

A stored state can disagree with the source; a computed one cannot. Consequence: `draft`, `accepted`, `stale`, `incomplete`, `conflicted`, `proved`, `settled`, and whether a note has faded are all computed from records and the current text on every query. Nothing writes the word "stale" anywhere.

### P4. One mechanism per concept, one write path per kind of record.

Two ways to say the same thing drift apart. Consequence: `\input` is transclusion, `\ref` is dependency, `\newtheorem` is taxon, `loom accept` is the only writer of the ledger, and `loom annotate` is the only writer of annotation records.

### P5. The graph is defined by labels and environments, never by paths.

Where a file lives carries no meaning. Consequence: one file per node and twelve lemmas in one section file are the same graph at two granularities. `nodes/` is a convention `loom new` follows, not a rule the scanner enforces, and no directory exists to hold a property loom can compute.

### P6. Config only for what the preamble cannot say.

The preamble is the author's declaration of their conventions, and the tool reads it. Consequence: taxa come from `\newtheorem`, style classes from `\theoremstyle`, macros from the preamble closure, the engine from `% !TEX program`. `config.toml` names the default document, the drafting directories, the id prefix and a default engine, and little else.

### P7. Loom changes an author's file only when the author incorporates a change, and keeps the old text first.

An author's file is theirs, and a tool that edits it behind their back destroys work. Consequence: every other operation writes a new file at a destination the user names (`atomize SRC --to DEST`, `history restore --to FILE`), writes into loom's own directories, or prints a patch (`id`, `revert`, `fork`). Incorporating a contribution, whether an agent document (`loom adopt`) or a collaborator's pull (`loom sync incorporate`), is the author's act: it is previewed, and it stamps each document it reaches before writing. Loom deletes nothing outside `build/`.

### P8. No editor, server, model, or credential is required by any command.

Every command runs from a terminal against files. Consequence: editors, Overleaf, Claude Code, Codex, Gemini and local agents are all clients, and none is assumed. The language server and the MCP server (not built yet, see [README](README.md#decided-not-yet-built)) are clients like the rest, and no command requires either.

### P9. Loom calls no model, and any agent may attach.

A tool that holds keys or calls a provider ties its users to that provider. Consequence: loom never runs a model, holds no API key and imports no model SDK. Agents from any vendor, hosted or local, reach loom through the same open interfaces (the command line, and MCP when it is built), and loom treats them alike.

### P10. Comments declare; they never command; they never change typeset output.

A `% !LOOM` directive is a fact the scanner reads, never an action loom performs, and never something that alters the PDF. Consequence: `% !LOOM ignore` and `% !LOOM tags:` exist; `% !LOOM accept` does not. Anything that changes the typeset document is a macro (`\nest`), because LaTeX must see it.

### P11. The build interface and the write API are the product boundaries.

Loom and arras share no code; they share specifications. Consequence: loom publishes a build directory conforming to `docs/specs/`, and arras reads it and nothing else. Arras knows only that a directory changed, never what kind of change or why.

### P12. A document compiles from the quilt root, on any TeX, on Overleaf.

Portability is a property of the source, not of the tool. Consequence: all paths are root-relative, local style files sit at the root, and there is no `TEXINPUTS`, no shell escape and no absolute path. A quilt with no document has nothing to compile; the rule binds documents, not quilts.

### P13. Loom verifies what it can, reports what diverges, repairs nothing, and never blocks work.

The head is always the files on disk, and the history is a log of what loom was told, never a claim about the filesystem. Consequence: an edited landmark, a hand-edited record, a retired id written under again, and two live definitions of one id are each reported with the exact commands that would resolve them, the rest of the quilt builds normally, and no command rewrites a record of its own accord to make the report go away.

### P14. No unnecessary friction.

Nobody uses a tool that charges them for nothing, and research friction lands hardest on exploration, where most ideas deserve to be forgotten. Every step a person must take buys them something at that moment: capturing costs one gesture, forgetting costs none, and only the move to permanence asks for care. Consequence: defaults rather than questions; a note needs no kind, target or title to be taken; a refusal names the one thing that clears it (T3); a rule that protects none of the three people (the Learner, the Explorer, the Author) is removed. The test is to list what a feature asks of each of them and what each step buys.

### P15. Nothing unchecked looks checked.

Mathematics is only as trustworthy as the checking behind it, and an assistant's output reads as confidently when it is wrong as when it is right. Whether a claim has been checked, and by whom, is always visible and never implied. Consequence: only the author accepts a result or verifies a transcription; an agent's work is marked as an agent's wherever it appears; extracted is not checked and checked is not verified; a passing check says "checked", never "verified"; and a design document marks what is not built yet.

## V · The viewer

How every surface of arras is judged: what it shows, where, and how much. Each has cost something to follow, and every surface is checked against them one element at a time.

### V1. Open on the thing itself.

The first screenful belongs to what the reader came for. What the application has to say *about* that thing goes to an edge or behind a control.

### V2. Say it once, in the place that governs it.

Where two surfaces state the same fact, one is deleted rather than restyled, and the survivor is whichever one controls the fact.

### V3. Claim only what is known.

Where the viewer does not know something it shows nothing rather than something plausible. A marker says the one thing that cannot be inferred and no more.

### V4. Name the question. One element, one question.

Every element exists because a reader asks something at that moment. If the question cannot be named in one short sentence, the element goes; if two can be named, it is two elements; if two elements answer one question, one goes. Two riders: **a place is not an element**, since a rail or a panel groups elements, and the test for a place is whether its elements' questions are asked at the same moment; and **the question is the reader's, not the system's**, which is what condemns a section reporting that a node is "in no document".

### V5. Following a connection must not cost the thing you followed it from.

The viewer's subject is how texts relate; a relation has two terms; a viewer that holds one term can only show a relation by destroying the other.

### V6. Show less rather than more by default.

Unless something has a good reason to be shown, don't show it. Corollaries: simpler is better, and visual noise is bad.

## A · Annotations

The viewer principles restated for how an annotation is drawn and how a reader reaches it.

### A1. The text comes first.

At rest the page shows marks and nothing else: no open boxes, and at most one count per node. An annotation marks its place and waits to be opened.

### A2. One annotation, one mark.

On the page an annotation appears once: as a mark, or, with no anchor, as the single count on its node. The lists that show it link to it rather than restate it.

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

- At rest only open, top-level annotations are drawn.
- Settled annotations (resolved or withdrawn, marked by hand) are not drawn until the reader turns them on, and then at 3% wash with the underline at half weight and 50% opacity, the words untouched.
- The system uses four hues, one neutral and three weights, and nothing else.
- An annotation looks the same on every surface: text, PDF and hover card.

## T · Terminal output

How what a command prints reads, for a person at a terminal and for an agent reading the same text. The mechanics they rest on: `--json` alone on stdout, diagnostics and progress on stderr.

### T1. Lead with the verdict.

The first lines answer "did it work, and do I need to do anything?"; detail comes after, for the reader who wants it. A report that ends without saying whether anything is wrong leaves the reader to work it out from the detail. A success that leaves work undone says so: "no changes to incorporate" while a change waits behind a flag, or "already up to date" over a conflict, is a verdict that is false.

### T2. Group, count, then list.

The same sentence is never printed N times: it is written once, as a heading with its count, and only what varies is listed under it, sorted and aligned. A reader should learn how many and of what before reading any one of them. Order serves the reader: the author's own results before the cited works' machine-made ones, which must never drown them; and a list cut short says what it left out (`… and 85 more`).

### T3. Every problem names its next command.

A line that implies action ends with the exact command that resolves it, as P13 asks of every divergence loom reports; what needs no action is summarised as a count rather than enumerated. A refusal names what blocks it and the flag or edit that clears it. The command named must work in the state that prompts it: advice that names a command which then does nothing is worse than none, so a suggested command is tested in that state.

### T4. Use the reader's words, not the implementation's.

Output names what the reader recognises: their file names, citekeys, titles and the commands they type. Internal storage paths, hashes, truncated keys and the implementation's verbs stay out of it.

### T5. Make the numbers add up, and fit the screen.

Parts sum to the totals they claim, and each count says what it counts. Lines stay under about 100 columns, and one indentation pattern holds throughout: a heading, then its items indented beneath it. An identifier is never truncated to fit: a cut citekey or id is a different name, so a long name goes last on its line, or the line wraps.

### T6. A command that takes more than a couple of seconds shows that it is alive.

It names the stage it is in, the item it is on, that item's place in the count (`7/18`) and the time elapsed, refreshed at least every few seconds, so a reader never has to guess between waiting and stuck. Progress goes to stderr, never into what a script or `--json` reads, and where stderr is not a terminal it is one plain line per item. Speed comes first: a command a person runs many times a day is made fast enough to need no progress line.

### T7. Say only what happened.

Output describes what the command did and nothing it did not: no fetch reported for a fetch that did not happen, no "pass" over a result left broken, no "wrote" for a file that was skipped, and a dry run marked as one. This is V3 for the terminal.

### T8. Machine output carries what the text carries.

Every command that reports offers `--json`, and its JSON holds everything the text says rather than a thinner subset, built from the same report so that the two cannot drift. Stdout holds only that document, on failure as on success.

## C · Construction

How the project is built and changed. `docs/contributing.md` says how to work within them.

### C1. The scanner before everything.

Nothing else can be tested without it, and the source contract is the part most likely to be wrong on real papers.

### C2. Vertical slices.

Each change runs end to end, source to arras page, for a growing part of the contract, rather than completing one layer at a time.

### C3. The fixture is the contract's executable form.

Every change to loom's output regenerates the fixture, and every change to the interface is a change to the fixture first.

### C4. Author files are sacred from the first commit.

The tests that enforce P7 are written before any command that touches a file.

### C5. Two tools, in two languages, sharing nothing but `specs/`.

Loom and arras live in one repository, each with its own build, tests and release, and they meet only at the specifications, which is what keeps P11 a fact of the code and not only of the design.

## K · The command line

The shape of the command line, as opposed to what one command prints (the T set): which commands exist, what their flags mean, what they accept and do, and how a person finds them.

### K1. One action, one command, one name.

No command has an alias and no two commands perform one act; a step of a pipeline is a flag of the pipeline, not a command of its own; a refusal is a line of help, not a command. A second name for one thing is a second thing to learn and a doubt about whether they differ.

### K2. One idea, one flag, one meaning.

A flag means the same thing on every command that takes it, and an idea has one flag wherever it appears: who is acting, a reason, the file to write, a session, consent to use the network.

### K3. Refuse what is not understood.

Every argument is checked before any work begins, and one that names nothing or holds a value the command does not understand is refused by name with exit 2. Accepting it silently, and acting on a guess or on nothing, reports a success that did not happen.

### K4. A command does what its name says, and nothing more.

A command that reads never writes, a command that prints a patch never records one, a refusal leaves no trace, and a dry run touches nothing. Housekeeping a command did not announce is a side effect the reader cannot see or undo.

### K5. Guard by consequence, uniformly.

Every act that is the author's alone, or that destroys, refuses an agent the same way and asks before destroying, whichever command performs it and whatever name the caller declares. The guard is on the act, not on the command that happens to reach it.

### K6. The help is a map of the work.

`loom --help` groups the commands by the task they serve, puts the person's commands first, marks the agent's and the upkeep commands as such, and gives each a full first sentence. A newcomer finds the command for what they want to do without reading every name.

### K7. One thing, one name, everywhere.

The command line, the viewer and the documentation call a thing by one name, and a state by one word: if the viewer says Library, so does the command line. Two names for one thing make a reader wonder whether they are two things.
