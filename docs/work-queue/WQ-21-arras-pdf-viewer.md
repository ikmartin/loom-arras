# WQ-21 · arras displays PDFs and resolves reference links into them

**Repo:** arras

## Trigger

Plan 0.5 has landed, publishing the two things this needs: the manifest's per-reference artifacts block, and the `refs/` route on `loom serve`.

This is a decision rather than an observation — it is intended work waiting on a prerequisite, not a contingency waiting on evidence. Most triggers in this queue are things you wait to notice; this one fires the moment 0.5 is done.

## Why deferred

Only by prerequisite. Until 0.5 there is no route to fetch a PDF through and no manifest field saying one exists, so there is nothing for a viewer to open.

## Rough design

The motivating feature is not citation convenience: **a comment should be able to link to a specific place in a reference PDF**, so that a reader — or an agent that read the reference for ground truth — can point at the evidence rather than paraphrase it.

**Where the link lives.** An annotation is `target_key` + `target_hash` + `selector` + `kind` + `body`. The selector is a text-quote anchor *into the node's own text*, which is how a gutter comment attaches to a phrase, so it is the wrong slot — the PDF is not what the comment is attached to, it is what the comment cites. The link goes in the body, which is free text, and needs no record-format change.

**The link names the global id**, never the citekey:

```
[Prop 3.2](loom:arxiv:0805.2065v2#page=9)
```

A comment outlives a citekey rename, is read by collaborators whose bibliography calls the work something else, and — decisively — a page number means nothing without naming which artifact it is a page of, once a preprint and a published version are both in play.

**Admit both anchor forms from the start**, so no link needs rewriting later: `#page=N` resolves today with the browser's own viewer, and `#quote=…` resolves later against a text layer. The quote form reuses the `{exact, prefix, suffix}` vocabulary `Selector` already defines, and is the durable one, because pages shift between versions exactly where this project is fragile.

**Renderer: browser-native first.** `<iframe src="/refs/arxiv/0805.2065v2/paper.pdf#page=9">` costs nothing. `#page=` is an Adobe convention Chrome and Firefox honour and Safari has historically been unreliable about, so check that before committing. PDF.js gives a text layer, region highlights and reliable navigation, but arras ships **vendored inside the loom wheel** at 3.9 MB beside d3-force, elkjs, mathjax and ninja-keys, and PDF.js plus its worker is a meaningful fraction of that again in every `pipx install loomtex`. Defer it to its own item, triggered by page-level linking proving insufficient.

**Degradation matters more than usual.** `refs/` is gitignored, so a collaborator who clones the quilt has the comment and not the bytes. A link to an absent PDF must resolve to "not fetched — `loom digest fetch Man12 --pdf`", ideally as an action, never a 404. A durable reference to a deliberately non-durable artifact is unusual enough to design for in the first version.

## Blast radius

`arras/src/lib/components/` (a viewer and a link renderer), comment body rendering, `arras/src/routes/digest/`, Chapter 15, `docs/specs/dialect.md` if the link becomes a recognised form rather than plain text.

## Related

Plan 0.5 (its prerequisites); [[WQ-22]]; the deferred PDF.js item this spawns if page-level proves insufficient.
