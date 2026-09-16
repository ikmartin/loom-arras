# WQ-14 · `manifest.schema.json` derived from the specification

**Repo:** loom

## Trigger

A third implementation of the interface appears, or a manifest regression ships that a schema would have caught.

## Why deferred

There are two implementations, both in this workspace, and they are kept in agreement by a stronger mechanism than a schema: a generated conformance fixture vendored into both, byte-compared, with `docs/specs/tools/validate-dialect.py` over every fragment. A schema would be a second source of truth for the same shapes, and the weaker one.

## Rough design

Derive `docs/specs/manifest.schema.json` mechanically from `docs/specs/manifest.md` rather than writing it by hand, so the specification stays the source. Validate the fixture's manifest against it in `refresh-fixture.sh`. `docs/specs/fixture.md` already promises this file exists.

## Blast radius

`docs/specs/` (a new generated file and its generator), `refresh-fixture.sh`, `docs/specs/fixture.md`.

## Related

`docs/specs/fixture.md`; `docs/specs/tools/validate-dialect.py`, which is the existing and stronger check.
