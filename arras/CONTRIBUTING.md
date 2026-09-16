# Contributing to arras

arras renders the loom–arras interface (`docs/specs/` in the loom-arras workspace) and nothing else. A change that needs more than the manifest and the fragment dialect is a change to the interface first: propose it in the specification, bump the interface version if it is not additive, regenerate the fixture, and only then teach arras.

- `src/` must not mention loom, LaTeX, quilts, or mathematics; `tests/unit/forbidden-words.spec.ts` fails when it does (the words the interface itself uses, such as `digest` and `proof`, are exempt).
- Every page kind renders generically for unknown states, diagnostic codes, taxa, and labels; a new label in the manifest must not need a code change to appear.
- `npm run check`, `npm run test:unit -- --run`, `npm run build`, and `npm run test:e2e` must pass; the end-to-end tests run against the vendored fixture in `tests/fixture/`, refreshed from the workspace with `docs/specs/tools/refresh-fixture.sh`.
- After a change that reaches users, rebuild and re-vendor into loom (`scripts/vendor_arras.py` there) so a loom clone carries the matching bundle.
- Prose in comments and Markdown is never hard-wrapped.
