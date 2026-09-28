# WQ-54 · Open annotations follow the text a person adopts

**Repo:** loom, arras

## Trigger

An adoption leaves an open annotation on the agent's copy whose node the person took, and the person files it again by hand on the adopted node.

## Why deferred

The umbrella decided that an open annotation on a node the person takes moves with it, re-anchored by an event in the log (plan 0.17, the adoption analysis), and plan 0.17.2 kept annotations on the contribution instead, reachable from it after incorporation: a transfer must keep the annotation's history and leave an anchor it cannot place visibly unresolved rather than guess, and that was more than the milestone needed. Nothing is lost meanwhile; the annotation is one link away from the adopted node.

## Rough design

A log event, `retargeted`, naming the annotation, the plain key and the document it now reads in, appended when an adoption takes the node the annotation is on; the anchor re-resolved against the adopted text, which is the copy's once the suffix is stripped, so its quote and recorded version hold (DR-284-ikmartin). Kept nodes' annotations and settled ones stay on the copy. The adoption preview lists which annotations would move.

## Blast radius

`records/log.py`, `adopt.py`'s incorporation, the adoption preview, chapter 7's annotation events.

## Related

[plan 0.17.2](../plans/0.17.2-luisa.md), whose scope section asked for this to be tracked.
