# Loom

Loom is a local command-line tool for mathematical research, and arras is the viewer it publishes to. This directory is their design: what they are for, the principles they follow, the model they share, how agents take part, and the invariants that must not be lost. It replaces the design book, whose decision records are frozen in [`decision-records-frozen.md`](decision-records-frozen.md); the book itself is deleted, and git history keeps it.

## What loom is for

Loom is a tool for every stage of mathematical research, from learning a field to submitting a paper. It treats mathematics as a graph of addressable statements: your drafts, the papers and books you read, and the questions you are working on. Anything a person or an AI says about that mathematics attaches to the statement it concerns and can be found from there.

Most of research is provisional, and loom lets it stay that way. As in a Zettelkasten, conversations and half-formed ideas are fleeting notes, kept while they are useful and allowed to fade. What proves worth keeping is distilled into durable notes, about the literature or in your own words, that are atomic, linked, and found from the mathematics they concern. Nothing fades while a durable note relies on it.

Loom is useful with no AI present and built to be excellent with one, from any provider, including local models. It assumes as little as possible about who you are, what stage you are at, or whether you have a draft or a problem at all. And it never lets a claim that nobody has checked look checked.

## Three people

Every design decision is tested against three people. A feature that serves none of them does not belong; one that serves one and costs another needs a reason.

**The Learner** is a graduate student reading literature openly, with no draft and no research question. They need to read papers and books through loom, see how results in different works relate, ask an AI to clarify a concept or build an example of a definition, and keep what they learn attached to the statement it is about. Today loom gives them the library (works, page text, digests of results, search, relations between results) and annotations on a page of a work. The rest is not built yet: a quilt that is a library rather than a paper, notes attached to any result, and a viewer that opens on what they are reading.

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
- it needs a running process for something a command could do;
- it only makes sense with a model in the loop, or needs an API key;
- it teaches arras what a kind of event means rather than how to render it (P11);
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

- **An MCP server for agents.** MCP is the intended way agents attach to loom, with the full set of agent commands as tools, vendor-neutral and optional. See `agents.md`.
- **Notes.** Fleeting and durable notes attached to any key, a work's page or a session, with fading computed from age and links. See `model.md`.
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
