# WQ-19 · Publishing to PyPI and npm

**Repo:** loom, arras

## Trigger

The author decides to release.

## Why deferred

Publishing is the author's act and never an agent's — a standing rule in `AGENTS.md`. `docs/RELEASE.md` deliberately stops before `uv publish`.

## Rough design

Follow `loom/docs/RELEASE.md` to its last step, then the step it stops before. The checklist already requires the conformance fixture regenerated with both vendored snapshots equal, the arras bundle re-vendored from a named commit, `loom doctor` reporting that bundle and interface version 1, and the screenshots regenerated. [[WQ-16]] supplies the Overleaf result the release notes want.

The distribution is `loomtex` on PyPI; arras ships inside it as a vendored bundle, so end users need neither the arras repository nor Node.

## Blast radius

`loom/docs/RELEASE.md`, version numbers in both repositories, the release notes.

## Related

[[WQ-16]], [[WQ-17]]; `loom/docs/RELEASE.md`; `closed/M7.md`.
