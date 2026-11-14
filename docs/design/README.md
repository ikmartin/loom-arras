# Loom

Loom is a local application for mathematical research: a person reads, annotates and decides in its viewer, arras, and their own AI agent works beside them through loom's commands. This directory is their design: what they are for, the principles they follow, the model they share, how agents take part, and the invariants that must not be lost. It replaces the design book, whose decision records are frozen in [`decision-records-frozen.md`](decision-records-frozen.md); the book itself is deleted, and git history keeps it.

## What loom is for

Mathematicians do not finally care whether a theorem is true so much as understand why it is. Loom is a tool for building that understanding at every stage of research, from learning a field to submitting a paper, and it uses AI to deepen it. It treats mathematics as a graph of addressable statements: your drafts, the papers and books you read, and the questions you are working on. Anything a person or an AI says about that mathematics attaches to the statement it concerns and can be found from there, so that the connections in your head have a counterpart you can follow.

Most of research is provisional, and loom lets it stay that way. As in a Zettelkasten, conversations and half-formed ideas are fleeting notes: one gesture to leave, asking nothing of anyone afterwards, so forgetting one costs nothing. What proves worth keeping is distilled into durable notes, about the literature or in your own words, that are atomic, linked, and found from the mathematics they concern.

AI-written mathematics and documents are welcome in loom and will be a large part of research. Loom's part is a clear boundary around what an AI may change, so that the person keeps control of their own text and of how they work. Loom calls no model and stays useful with none present; it is built to be excellent with one, from any provider, including local models (P9). It assumes as little as possible about who you are, what stage you are at, or whether you have a draft or a problem at all. And it never lets a claim that nobody has checked look checked.

A person uses loom as an application: they launch it, open a quilt or start one, drag in papers and drafts, and read, annotate and decide in the viewer. They need no command line, and loom is not a text editor: they write in their own editor, or on Overleaf. An agent uses loom through its commands, in a shell or over MCP. The viewer's controls, the commands and the MCP tools are surfaces over one set of operations. Much of this is [not built yet](#decided-not-yet-built): today a person still starts loom, makes a quilt and sets up an agent from a terminal.

## Three people

Every design decision is tested against three people. A feature that serves none of them does not belong; one that serves one and costs another needs a reason.

**The Learner** is a graduate student reading literature openly, with no draft and no research question. They need to read papers and books through loom, see how results in different works relate, ask an AI to clarify a concept or build an example of a definition, and keep what they learn attached to the statement it is about. Today loom gives them the library (works, page text, digests of results, search, relations between results), annotations on a page of a work, and their own files (Markdown, HTML, notebooks, PDFs) in the project's tree, opened on a front door they name. The rest is not built yet: a quilt that is a library rather than a paper, and notes attached to any result.

**The Explorer** is a researcher with a concrete question, working examples and trying proofs. They need to record attempts, claims and dead ends against the question, find out quickly whether something is known, see which steps are still open, and turn an attempt that works into a statement. Today loom gives them nodes, `\incomplete` steps, the graph, library search and agent documents to draft in. A problem page that remembers what was tried is not built yet.

**The Author** has a draft and is proofreading, expanding and checking it before submission. They need review that lands on the text, their own annotations as a working list, an audit of every dependency and citation, acceptance that goes stale when anything underneath changes, and a record of what was submitted. Loom serves the Author well today; this is where it began.

## Judging a change

Before building something, answer three questions:

1. **What friction does it add, for which of the three people, and what does it buy them at that moment?** A step that buys nothing is removed, defaulted or never introduced (P14).
2. **Could it let something unchecked look checked?** Whether a claim has been checked, and by whom, must stay visible (P15).
3. **Does it work with no AI present, and with any AI?** Loom calls no model, and no vendor is assumed (P8, P9).

These are warning signs. Each is a reason to think again, not an automatic veto:

- it needs syntax beyond `\uses`, `\incomplete` and `\nest`;
- it asks for configuration where the preamble already says the answer;
- it writes to an author's file outside an incorporation the author chose (P7);
- it creates a second source of truth, or stores a state that could be computed (P3);
- it makes a person type a command for something a control could do, or makes an agent need the viewer for something a command could do;
- it only makes sense with a model in the loop, or needs an API key;
- it names a directory for a property loom can compute;
- it reinvents something LaTeX already has.

## How this design changes

The design is still being discovered, and this directory records current thinking, not a contract. When building something teaches you that the design is wrong, change the design in the same change and say why in the commit message. Three things differ in how they change:

- **Invariants** (`invariants.md`) change deliberately. Each records a failure that happened; changing one adds a dated line to its entry saying what changed and why.
- **Principles** (`principles.md`) change by editing them, with the reason in the commit message. A principle's name is permanent: a retired principle keeps its heading, marked retired, so that citations still resolve.
- **Everything else** is current thinking. Edit it as you learn.

Two markers keep the text honest:

- A paragraph that begins **Open.** states a question that is not decided, beside the design it affects. The work queue (`docs/work-queue/`) holds deferred work, each item with a trigger; it does not hold design questions.
- **(not built yet)** marks something decided and not yet implemented, and links to the list below. Nothing unbuilt may read as built.

## Decided, not yet built

- **Loom as an application.** Installing with one line; a home page that opens, creates and lists quilts; dropping a paper in; connecting an agent from the viewer and seeing that it is connected; and no step that makes a person type a command. See `docs/plans/0.32-v0.1.md`, which also holds what is recommended and not yet decided.
- **Annotating PDFs and reviewing changes as plan 0.30 settled them.** Annotating documents is built: the toolbar and its one popup, the Comments and Notes lists, Quote, Settings › Annotations, and an annotation opening the version it was written on. Not built: the same toolbar on a PDF page, a mark found again on a changed PDF and a crop of it for an agent (0.30.2), and changes reviewed in the document (0.30.3). See `model.md` and `docs/plans/0.30-annotations.md`.
- **Notes beyond annotations.** Claims carrying their evidence, and promotion to durable notes. See `model.md`.
- **Open problems as nodes,** with the attempts, claims and dead ends about them attached as notes.
- **A reader-first library.** Works that are read but not cited are first-class; the bibliography, fetching and the graph stop assuming a draft. See `docs/specs/digests.md`.
- **The viewer's Library.** A Library view of the works; the frame it stands in, and Review as the quilt's management, are built. See `model.md` and plan 0.20.
- **Later:** running code to test claims (not in the next weeks).

## Where things live

| what | where |
|---|---|
| this design | `docs/design/`: this file, `principles.md`, `model.md`, `agents.md`, `invariants.md` |
| formats: the loom–arras interface, the source contract, digests, diagnostics | `docs/specs/` |
| commands and their options | `loom <command> --help`, generated into `loom/docs/cli-reference.md` |
| what an agent is given | `loom/src/loom/assets/ai/` (orientation, rules, modes) |
| building, testing, verifying, releasing | `docs/contributing.md` |
| deferred work | `docs/work-queue/` |
| history: the old book's decision records, plans, reports | `docs/design/decision-records-frozen.md`, `docs/plans/`, `docs/reports/` |

Where the design and a spec disagree about a shape, the spec wins; about what a thing means, the design wins. Where either disagrees with the code, one of them is wrong, and the fix is to correct whichever it is.
