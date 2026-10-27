# Notes, and a running notes view

*An idea, 2026-10-27, from the exploration discussion of 2026-10-26. Nothing here is decided. It is written to be argued with: every design choice below is a possibility, most with alternatives beside it, and the questions at the end matter more than any answer suggested along the way.*

## The starting point

Most research happens before anything is a node: an idea tried, an example worked, a counterexample found, a definition finally understood. Loom gives that work no home today, so it lands in chat that scrolls away, in session files nobody opens again, and in the author's head. The idea is some form of **note**: a small piece of writing about the mathematics, easy to take, easy to find again from what it concerns, and easy to let go of. Alongside it, a **running notes view**: every note in one stream, newest first, like a lab notebook.

How far that goes, what a note is, and how it relates to the rest of loom are all open.

## Why

Evidence from relloc's two-week session (`s-2026-10-12-0001`):

- **What failed was lost where it was found.** Two counterexamples to a lemma's first statement, a step that was false for genus above zero, and a grouping error each lived in a notes file or a chat message, and none can be found from the result it concerns.
- **Open problems were prose,** spread across remarks, annotations and a to-do comment, with nowhere for attempts on them to collect.
- **Effort went where it was cheap to record.** The examples got four polishing passes while every proof beneath them stayed a placeholder.
- **Sessions organise by time, not subject,** so "what has been tried on this problem?" meant reading sessions in order.

From the author's experience of Zettelkasten practice: note systems tend to add friction to exploration far more than to drafting, and to give fleeting notes more permanence than they deserve. Whatever loom does here has to be judged first by that (P14).

## What a note might be

One possible shape, deliberately small:

- **Text,** perhaps Markdown with mathematics as annotation bodies are, perhaps LaTeX, perhaps either.
- **Something it is about,** perhaps optional: a result, a proof, a section, a cited result, a page of a paper, an `\incomplete` step, an open problem, or nothing yet, to be filed later or never.
- **A kind,** perhaps: explanation, example, question, attempt, claim, dead end, connection. Or no kinds at all, and tags instead, or nothing.
- **Who wrote it and when.**

Other shapes worth weighing:

- **Notes as annotations.** Annotations already have targets, authors, sessions, replies and a viewer. A note could be an annotation that asks nothing of the text; there is already a `note` kind meaning roughly that. The question is whether a note's life (kept, forgotten, promoted, refuted) is different enough from an annotation's (open, resolved) to be a thing of its own.
- **Notes as LaTeX.** A notes document in the drafting directory, each note an environment with an id, gets ids, the graph and compilation for free, and costs every note a label and a compile.
- **Notes as pages, not slips.** A running page per problem or per paper, edited freely, rather than many small records.
- **Notes outside loom.** Obsidian, Zotero or a plain folder of Markdown already hold many people's notes; loom could link to them by path and anchor rather than store its own.

## Two ways to see notes

**Where they belong.** Beside the result, page or problem a note concerns, in the place that thing is read (V7), quiet until opened, as annotations are. This answers "what do I know about this?".

**The running notes view.** Every note in one stream, newest first. This answers "what have I been thinking?", and it may be what makes taking a note feel safe, because it is always somewhere. Possibilities:

- grouped by day, each entry linking to what it concerns, opened where that thing lives;
- notes about nothing yet living here until filed;
- a capture box at the top, taking whatever is in view as the default subject;
- filters (who wrote it, what it concerns, kept or not) and search;
- the same stream on the command line (`loom notes`), so an agent can read what the person has been thinking about before it starts.

Open: where the view sits in plan 0.20's frame (a Notes entry in the Docs column? a pane of its own?); whether session transcripts appear in it, one line each; whether it should be per person, per quilt, or across quilts; whether "newest first" is the right order, or by day, or by problem.

## How long a note lives

This is where the Zettelkasten worry bites, and there are several plausible answers:

- **Fading.** A note fades from default views after a while unless it is kept or linked to; nothing is ever deleted, and faded notes stay searchable.
- **Never fading.** Everything stays; the running view's ordering does the forgetting, as a notebook's does.
- **Explicit archive.** The person clears what they no longer want, in batches.
- **Two tiers.** A scratch tier that clears itself and a kept tier that never does.

And separately: does anything ever turn a note into durable mathematics (*promotion* into a node in one of the author's documents), or do notes stay notes and the author writes the mathematics afresh after reading them?

## Claims, evidence, and problems

- A note that claims something might carry a status (conjectured, tested on examples, sketched, proved here, refuted) with the evidence for each step and who supplied it, so an agent's "proved here" never reads as checked (P15). Or that might be too much structure for a note, and belong only to something promoted.
- An open problem might be a node (a `question` or `conjecture` in a research document) with its attempts and dead ends attached as notes, so a fresh session reads what failed before trying again. Or a problem might be a note itself, a page, or a tag.
- A dead end might record why it failed (a counterexample, a computation, a known obstruction) so it is found from the problem and from the result it bumped into.

## Agents

- "Log that" could be one call, from any agent app, under the agent's own name (`loom note`, and the same act over MCP, plan 0.21).
- An agent could read the stream, or a problem's notes, before it starts, which may be most of what a session's working memory needs.
- Filing notes may suit a small local model (`docs/ideas/quilt-butler.md`): frequent work, cheap to check, and mistakes that matter little.
- Open: whether agents' notes and the person's are kept apart, shown together, or filtered by default.

## The three people

Sketches of what notes might do for each, not requirements:

- **The Learner** reads a definition in a paper, asks an agent for examples and non-examples, and keeps the two that clarified it, attached to the definition. A month later the running view shows what they were reading that week.
- **The Explorer** opens a problem, reads three earlier attempts and the counterexample that killed one, tries a fourth, and records why it fails. When an attempt works it becomes a lemma, perhaps carrying what led to it.
- **The Author,** proofreading, notices that a constant could be sharpened. That is not an objection anyone must answer, so it is a note, found again when a referee asks.

## Principles that bear on it

P14, no unnecessary friction, above all; P15, nothing unchecked looks checked; V7, show a thing where it lives, which the running view tests, since a stream is a view apart from where things live; and P1 and P2, which ask where notes would be stored and in what form. Any of these might be argued with in light of what notes turn out to need.

## Questions

**What notes are**
- Are notes a new kind of record, a kind of annotation, LaTeX, or something loom links to rather than stores?
- Is the unit a small slip, a running page, or both?
- Markdown, LaTeX, or either?
- Is there a kind at all, or tags, or nothing?

**Life and memory**
- Do notes fade, stay, get archived, or come in two tiers?
- Does anything turn a note into mathematics, or does the author always write afresh?
- How does a note differ from a transcript entry, and should the running view hold both?

**Names**
- "Note" is already an annotation kind, and `notes/` is already the author's folder of reference material that loom never scans. Which gives way, if either?

**Sharing**
- Are notes shared with coauthors, private to their writer, or a choice per note?
- Should a Learner's notes on a paper follow the paper into their next project (WQ-03)?

**Agents**
- How much should an agent note on its own initiative, and how much only when asked?
- Do agents' notes need marking beyond the author's name?

**Fit**
- Where does the running view live in the new frame?
- Is the Zettelkasten the right model at all, or is a lab notebook, or something else?
- What is the smallest version worth trying?

## Related ideas, not yet planned

From the same discussion, each worth a file of its own if taken further:

- **A research state:** a short page of goals, open problems, conventions and decisions, kept by an agent and edited by the author, so any session picks up quickly. Decisions such as "ξ is the type of a fixed map" were buried in relloc's chat.
- **Acceptance cheap enough to use:** in relloc nothing was accepted. A review queue ordered by dependency, with one-click acceptance and what each acceptance unlocks.
- **Conditional results:** an unproved hypothesis as a node, and everything resting on it shown as conditional, rather than the condition living in a remark.
- **Agent work in `loom status`,** which today counts only the author's documents, so placeholders in an agent document go unseen.
- **Library-first quilts:** a quilt that is a reading list, with works that are read but not cited treated as first-class.
- **Reusable computation** (deferred): shared scripts and computations as rerunnable records, instead of each session writing its own.

## Ways to learn more before deciding

- Keep notes by hand in a plain Markdown file for a week of real work, in a few candidate formats, and see which gets used.
- Write the pages of two real relloc problems (`rl-001Q`, and the tree case of `rl-003L-ai`) in a candidate format, and give them to a fresh agent, more than once, to see whether it repeats a recorded dead end or finds what was tried.
- Ask a Learner what they actually do with a paper they are reading, before designing for them.
