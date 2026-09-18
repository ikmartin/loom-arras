# WQ-36 · Annotation bodies beside the manifest rather than inside it

**Repo:** loom, arras

## Trigger

A corpus's manifest crosses a few megabytes and the reason is annotation prose rather than nodes — a long review, a pasted proof in a payload, a thread nobody trimmed.

## Why deferred

Raised by the hostile demo (`records/hostile-demo.md`, direction 5) and deliberately not acted on, because the condition it guards against has not happened.

The manifest is **loaded whole on every poll**. `build/source/<key>.tex` exists precisely so that a key's own LaTeX is fetched one key at a time and only when a reader asks; annotation bodies, payloads and thread messages have no such arrangement and are carried inline. A single 400 KB annotation body put into a hostile quilt took its manifest to 3.2 MB on its own.

That is a real shape, and it is not yet a real problem. No corpus anyone has has a large annotation: the largest real manifest measured is relloc's at 772 KB, and none of that is annotation prose. Building the split — a `build/annotations/` directory, a fetch path, a viewer that renders a body it may not have yet — costs an interface change, a publisher change and a loading state in every surface that draws a comment, to solve a size nobody has reached.

**The trigger above is observable**, which is the test for whether this belongs in the queue at all: it is a number in a file, and `loom build` already knows it.

## Rough design

Two steps, and the first may be all that is ever wanted:

- **Make the condition visible.** `loom build` reports a manifest over some threshold, saying what the largest contributors are. A diagnostic costs nothing and turns "the viewer feels slow on this corpus" into a sentence naming the cause. It also means the trigger fires by itself rather than waiting to be noticed.
- **Move the prose** if it does. `build/annotations/<id>.html` beside `build/source/<key>.tex`, with the manifest keeping every field a reader filters or sorts by — author, kind, severity, status, target, anchor — and carrying the body only as a length. Everything that lists, counts or filters annotations keeps working from the manifest alone; only the surfaces that *render* prose fetch.

The second step is additive and needs no interface version: a viewer that finds a body inline uses it, and one that finds a path fetches.

## Blast radius

`loom/src/loom/records/store.py`'s annotation emission, `render/build.py` for the new directory, `specs/manifest.md` §9, and every arras surface that renders `body_html` — `AnnotationBox`, the report pane, the thread messages.

## Related

`records/hostile-demo.md`, which measured it; [plan 0.11](../plans/0.11-run-review-view.md), which introduced `build/source/` for the same reason about node text.
