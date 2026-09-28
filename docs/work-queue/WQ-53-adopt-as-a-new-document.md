# WQ-53 · Adopting an agent's copy as a new document

**Repo:** loom, arras

## Trigger

A person wants an agent's copy to become a document of its own — a talk, an alternate version of the paper — rather than changes to the document it was copied from, and does it by hand or asks for it (the study's E3).

## Why deferred

Plan 0.17 designed it as `loom adopt DOC --as drafting/NEW.tex` (ai-drafting-study §8.1: changed and new nodes take fresh ids recorded as forks, unchanged node files shared by `\input`, unchanged inline nodes forked), and plan 0.17.2 removed it from its phases: which results stay shared and which get independent identities must be specified and previewed first, and a person should not have to infer it from whether a node sits inline or in a node file. `loom adopt` incorporates into the copy's own source document only.

## Rough design

Start from 0.17.2's condition: a preview that lists, per node, whether the new document shares it (one node file, one id) or forks it (a fresh id recorded as a fork of the original), before anything is written; then the study's rules as the default, the person able to change any row. The write is the fork machinery `loom fork` already has, over a document; nothing of the person's is touched.

## Blast radius

`adopt.py`, `reshape/fork.py`, the adoption preview in arras's Incoming, chapter 17.7.

## Related

[WQ-29](WQ-29-node-manager.md), whose fork this uses; [WQ-33](WQ-33-the-proposed-document.md).
