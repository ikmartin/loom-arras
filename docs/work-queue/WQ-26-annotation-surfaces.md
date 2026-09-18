# WQ-26 · Annotation surfaces in arras: input, payloads, reference notes, whole-document comments

**Repo:** arras, loom

## Trigger

The author decides to answer a review in arras rather than in the chat — a decision, not an observation, as WQ-23's trigger is. The annotation system itself lands with the workbench plan for agents to write into; this item is every surface a person needs to write and read through it in the viewer.

## Why deferred

The chat is the primary interface to agents (WQ-23, settled), so a person's replies go there today and arras reads. Building input into arras before the annotation log has settled would build it twice. And arras has no write API yet; this is the item that needs one.

## Rough design

Four surfaces, grouped because they share the write path and the annotation log:

- **Writing an annotation in arras**: select text, write, choose kind and severity; the annotation goes into `annotations/log.jsonl` with `author` the person and `kind: human`, through the write API of `docs/specs/write-api.md` — whose §4 still routes a model's reply through the runner declined as WQ-15 and must be rewritten first: loom cannot wake an agent, so the agent pulls open comments through `loom status` and answers with `loom comment --reply`.
- **Payloads inline**: a suggestion carrying text (a proof, a paragraph, a rewritten passage) rendered in red beneath its anchor, placed by its `placement` hint, with the verbatim toggle and copy beside it. Preview and copy only; nothing applies (see [WQ-27](WQ-27-applying-suggestions.md)).
- **Reference notes**: `reference-notes.jsonl` read and shown per node — the suggested works, who accepted them, from which run — and the accept action for a pending suggestion.
- **Whole-document annotations**: an annotation whose target is a document rather than a key. The log holds them today and arras shows them nowhere, since the read view attaches annotations only to elements carrying a key. Proposed: at the top of the document in the read view, and in the run's report.

## Blast radius

`docs/specs/write-api.md` (§4 rewritten, endpoints for annotations), `loom/src/loom/render/serve.py` (the write endpoints), arras's read view, node page, run pane and a reference-notes component, Chapters 10 and 15.

## Related

[WQ-23](WQ-23-agent-review.md) for the split view these surfaces sit in; [WQ-27](WQ-27-applying-suggestions.md); [WQ-28](WQ-28-annotated-export.md).
