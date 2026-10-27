# A quilt butler

*An idea, 2026-10-26. Nothing here is decided, and it depends on the MCP server of plan 0.21, which is not built.*

Collaborators are interested in fine-tuning small local models, around 8B parameters (a Qwen model, say). This document asks what such a model, tuned specifically for loom, could do: whether it could carry out routine loom work, whether it could sort requests into those that need deep reasoning and those that do not, and whether it could act as a *quilt butler*, a resident assistant that keeps a quilt in order without ever deciding anything on the author's behalf. It does not limit itself to loom's present design; the places where it would press on that design are collected at the end.

## In short

A small model is a poor mathematician and a good clerk, and loom already has what makes a clerk safe: the acts that make a claim are refused to every agent, much of what an agent writes is checked mechanically, and context comes in closures rather than whole papers. A butler is feasible, and most useful where the work is frequent, tedious and cheap to check: filing notes, locating the results of PDF-only works on their pages, proposing missing dependencies, catching notation drift, and keeping the record of a session.

The split between "thinking" and "non-thinking" work is real, but the line to draw is the **cost of checking the output**, not the difficulty of producing it. A small model is fine wherever loom or a glance checks its work, however tedious the work is; it should hand off anything only a mathematician can check, however short.

## Why loom suits a small model

Most tools would make a weak model dangerous. Four properties of loom contain one.

- **The trust boundary is enforced, not requested.** `loom accept`, `loom library verify`, `loom adopt` and the other author's acts refuse any agent, by declared name and by the agent's shell markers (`docs/design/agents.md`), and the MCP server will not offer them as tools at all. A butler cannot sign the ledger however confused it gets, which is roughly what being a butler means.
- **Loom checks much of what it is given.** An id resolves or it does not, a document compiles or it does not, and `loom library propose` refuses a quotation that is not on the page or in the source file it names. Where loom is the checker, a small model's mistakes are caught before they are stored, not by the author afterwards.
- **Context comes in closures.** `loom source KEY --closure` prints exactly what a statement rests on. Small models degrade as context grows, and loom already does the narrowing they need.
- **Notes fade** (not built yet; `docs/design/model.md`). A note fades unless it is kept or something durable links to it, so a small model's guesses can be fleeting by default and clear themselves away.

## Routing by the cost of checking

| lane | examples | who checks the output | who does the work |
|---|---|---|---|
| 0 | "what is stale?", "where is the boundary lemma used?", a `\cite` locator no digest answers | loom | no model: the butler runs the command |
| 1 | file a capture, resolve a description to an id, locate a result's printed label on its page, summarise a session | loom mechanically, or a glance | the small model, without thinking |
| 2 | propose a missing `\uses` edge, find notation that drifts, find a hypothesis dropped where a lemma is applied, write a page's statement as LaTeX | the author, quickly | the small model, thinking |
| 3 | is this proof right, build an example, is this result known, draft new mathematics | a mathematician, at real cost | a frontier agent, then the author |
| author | accept, verify, adopt | nobody else can | the author alone |

Lane 0 matters more than it looks. Many questions need no model, and a butler's first skill is noticing that and running the command; some, like a `\cite` postnote that no digest answers, are already loom diagnostics.

Misrouting is lopsided. Sending lane 3 work to lane 1 produces a confident wrong answer; sending lane 1 work to lane 3 wastes some money. The router should lean towards escalating, and rules should decide what they can before a model sees anything: anything about whether a proof is correct goes to lane 3, whatever it looks like. A lane 3 question the butler answered itself must say so where the answer is recorded (P15).

Several current open-weight families, Qwen's among them, switch thinking on and off per request in the same weights, so one fine-tune can be both the router and the worker for lanes 1 and 2.

## What the butler does

Best fits first. Each job writes through loom under a declared agent name (`--as "Butler AI"`), so every record says what wrote it and the author learns how far to trust it, kind by kind.

1. **Filing captures** (Explorer, Learner). `docs/design/model.md` leaves a gap shaped exactly like this: "Loom infers nothing, since it has no model." The butler guesses a note's kind (attempt, dead end, claim, question), resolves "the lemma about the boundary map" to its id through `loom search`, and refiles captures that were saved to the session alone. Capture should cost one gesture (P14), which wants a model that is local, fast and free to call on every capture. A misfiled note is cheap, visible and attributed.
2. **Reading PDF-only works** (Learner, Author). For old books and papers with no LaTeX source, the work splits into two steps of very different cost, and the butler does them at different times. First it looks for a LaTeX source under another version of the work, since extraction from source is free and mechanical.
   - *Locating* is cheap and checked by loom. The butler finds each result's printed label ("Theorem 4.1") on its page and records the locator, page and region; `loom library locate` already gives the region. That is enough for a citation to open the PDF at the place, for its number to be checked, and for relations and notes to have something to attach to. It is the default, for every result of a work being read.
   - *Transcribing* is hard and checked by the author: writing the statement as LaTeX from a text layer that turns mathematics into control bytes. It waits until a result needs its text, which is when the author cites it, because only then does the statement belong in a closure. The author has just looked the result up to cite it, so its page is already open and verifying the transcription costs almost nothing.

   This serves the person least likely to pay for a hosted model, and it moves most of the job from lane 2 to lane 1. A result that is located but not transcribed does not exist in loom today; see the last Open paragraph.
3. **Keeping the graph honest** (Author). "By the previous lemma" and "as in Section 3" are dependencies with no `\ref`, and the butler proposes them as `\uses` edges in suggestions. This matters for trust: an acceptance holds hashes of its closure, so a lemma used without an edge can change without the acceptance going stale. A butler that finds missing edges makes P15 hold more often.
4. **Review below the mathematics** (Author). Notation that drifts between sections, a symbol used before it is defined, a hypothesis that disappears where a lemma is applied. These need language rather than a judgment of whether the mathematics is right, and they are what lint cannot see.
5. **Writing in the author's house style** (Author). The strongest case for fine-tuning over prompting: a model tuned on one author's macros, environments and conventions follows them better than a prompted frontier model. It works in an agent document in `drafting-ai/`, and the author adopts what they want (P7).
6. **Briefs and transcripts** (everyone). It turns what the person did since an agent last looked (`loom since`, a name proposed in plan 0.21.5) into a short account, and writes `loom session say` entries from a session's `run.log` and the records it produced, so a session has a record even when no frontier agent took part.
7. **Handing off lane 3** (everyone). It turns a question into a task for a frontier agent: the question, the ids it concerns, the closure to read. The expensive model then spends its reasoning on the mathematics rather than on finding its way around the quilt.

For the Explorer's "is this known?", a **fine-tuned embedding model** over digest results and library statements is likely a better tool than an 8B generator, and a better first project: retrieval is where a small model is strongest, and the library already holds the statements to train on.

## What it should not do

- **Judge proofs.** An 8B model produces confident false objections, and every one costs the author a reading (P14).
- **Construct examples for a Learner.** A wrong example that looks right teaches something false, and nothing checks it until loom can run code.
- **Sort stale acceptances into "cosmetic" and "substantive".** The most tempting job and the most dangerous: it is one summary away from "the butler said it was fine", the same reasoning `docs/design/agents.md` gives against request objects. Ordering the Review queue would be acceptable; hiding anything from it would not.
- **Run long autonomous loops.** Small models degrade over many steps, even on a narrow tool set, so each job should be a few tool calls.

## Training: loom is a reward function

- **Verifiable rewards.** Loom's exit codes, quotation checks, id resolution and compiles give reinforcement learning a reward signal for nothing, with the MCP tools as the action space and the fixture quilts as the environment.
- **Ground truth by ablation.** Remove the `\uses` edges and `\ref`s from a fixture document, and the removed edges are the answers for job 3. The same trick serves job 1: describe a node in words and ask for its id.
- **Extraction data at scale.** For any arXiv paper with both LaTeX source and a PDF, loom's mechanical digest extractor labels the PDF's page text with each result's statement and locator. That trains both halves of job 2, the label's page and region for locating and the statement for transcribing, with no hand labelling.
- **Preference labels from real use.** Annotations are resolved or withdrawn, agent documents are adopted node by node, proposals are verified or discarded. Every record names its writer, so a butler's hit rate can be measured per kind of record, and the measurement is a training signal. This data is small for any one quilt, and because annotations are shared with coauthors, they must agree before their words are trained on.
- **Teacher trajectories.** A frontier agent working the fixtures produces examples of good tool use. Check that provider's terms on training other models; an open-weight teacher avoids the question.

At four bits an 8B model is roughly 5 GB and runs on an ordinary Apple Silicon Mac; a 4-bit LoRA fine-tune (QLoRA) fits on one 24 GB GPU.

## A first experiment

1. When plan 0.21.2 lands, attach a stock ~8B model to a fixture quilt through an MCP-capable local client.
2. Give it three jobs whose success loom can measure: resolve a description to an id (job 1), locate and transcribe the results on a PDF page and compare both with the digest extracted from the work's source (job 2), and recover ablated edges (job 3).
3. Record where it fails, fine-tune on those failures, and measure again on fixtures it was not trained on.

Fine-tuning before the MCP server exists would teach shell conventions that are about to be replaced, so 0.21.2 is the real prerequisite.

## Where it presses on the design

- **As an MCP client, nothing changes.** The butler is an agent like any other; loom still calls no model (P9) and requires none (P8).
- **The client matters.** A local model needs an app that starts a stdio MCP server, as LM Studio does. A front end that speaks only HTTP, such as Open WebUI, needs the HTTP transport plan 0.21 leaves out of scope.
- **Volume.** A tireless writer can flood the annotation log. Defaulting the butler's output to fleeting notes handles most of it, which is a reason to build notes before a butler.
- **Privacy is the strongest argument for going local.** Unpublished drafts, institutional rules against sending them to hosted models, and students without the budget for them all point the same way, and a model that never leaves the machine serves all three.

**Open.** Whether a model ever belongs inside loom. The author's long-term aim, an application in which the command line is optional for a person, meets a local model most naturally in a natural-language control in the viewer: type what you want, see the `loom` command it means, press to run it. That would be the first idea to genuinely challenge P8 and P9. A gentler version keeps the model outside, reading where the person is looking through `loom here` (a name proposed in plan 0.21.5) and acting as a client.

**Open.** Where the butler's task lists live. A task list is a queue, and the design distrusts queues that nag. The honest version computes its lists from records that already exist (open questions, `\incomplete` steps, stale keys, unfiled captures), and the butler labels them rather than owning them. Whether a label such as "lane 3: needs a frontier agent" is an annotation, a note or a new kind of record is undecided.

**Open.** Whether a small model's notes should fade faster than a person's. Fading is computed (P3), so it could depend on the writer; that may be right, or it may be the start of a ranking of writers by trust that nobody asked for.

**Open.** What a located result is (job 2). Every result in a digest today has a statement: a proposal carries its LaTeX, and `docs/specs/digests.md` has no state for a result whose label was found on a page but whose words were never written down. Such a result needs a state of its own, one that claims only that the label is on the page (P15), and an answer to whether citing it makes an edge. It might: the dependency could hash the located span's page text, which cannot change, since the filed document an anchor was checked against never changes. But it would put no statement in a closure, so an agent reviewing the citing proof would see a page and a region rather than the hypotheses it needs to check, unless it can read the region as an image.
