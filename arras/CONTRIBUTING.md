# Contributing to arras

arras is loom's viewer: it is built here and vendored inside loom, and the two are one tool (`docs/design/principles.md`, P11). What it reads is what loom writes into `.loom/build/`, specified in `docs/specs/`; a change to what crosses changes loom, arras and those specs in one commit, and regenerates the fixture.

- Every page kind renders generically for unknown states, diagnostic codes, taxa, and labels; a new label in the manifest must not need a code change to appear.
- `npm run check`, `npm run test:unit -- --run`, `npm run build`, and `npm run test:e2e` must pass; the end-to-end tests run against the vendored fixture in `tests/fixture/`, refreshed from the workspace with `docs/specs/tools/refresh-fixture.sh`, and the write and reading suites against a served quilt with the pages TeX made of it (`tests/pages/`, from `loom/scripts/gen_pages.py`).
- After a change that reaches users, rebuild and re-vendor into loom (`scripts/vendor_arras.py` there) so a loom clone carries the matching bundle.
- Prose in comments and Markdown is never hard-wrapped.
