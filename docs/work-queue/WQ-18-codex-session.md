# WQ-18 · The Codex half of the AI layer

**Repo:** loom

## Trigger

Codex is installed on the machine.

## Why deferred

It is not installed, so the M6 demonstration ran the Claude Code half only. Writing a permission file for a tool that cannot be launched would be guessing at a format.

## Rough design

Run the M6 session against the demo quilt with Codex as the agent, and settle what M6 could not: **the form of a permission file for Codex**, which has no project-level equivalent of Claude Code's today. If it still has none, record that as the finding — "there is nothing to write" is a legitimate outcome and closes this item as well as a file would.

## Blast radius

`loom/src/loom/assets/ai/`, `loom ai init --skills`, Chapter 11 §11.5 and Appendix C, one demonstration record.

## Related

Chapter 11; `closed/M6.md`; [[WQ-15]].
