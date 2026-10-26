# Contributing

For anyone, person or agent, changing loom or arras. What loom is and why lives in `docs/design/`; the loom–arras interface lives in `docs/specs/`, which wins on shapes; what is not done is in `docs/work-queue/README.md`.

## The repository

One repository: loom, and its viewer arras in a codebase of its own, each with its own build and tests; the viewer ships inside loom. A change that crosses them is one branch and one pull request.

| directory | what it holds |
|---|---|
| `loom/` | the CLI, Python, built with `uv` |
| `arras/` | the viewer, Svelte, built with `npm` |
| `docs/` | the design, the specs, the work queue, the plans, frozen history |
| `demos/` | the committed example quilts, rebuilt by `demos/build.py` |
| `scripts/` | `verify`, and the documentation checks it runs (`scripts/checks/`) |

To set up: `uv tool install -e ./loom` puts this checkout's `loom` on your PATH; `uv sync` in `loom/` makes `loom/.venv`, which the arras write and reading suites serve with; `npm ci` and `npx playwright install chromium` in `arras/`.

The workspace's documents and loom are GPL-3.0-or-later; arras AGPL-3.0-or-later; `loom.sty` and the demo quilt MIT (`loom/src/loom/assets/LICENSE`), so they can travel with a paper.

## Verifying

`scripts/verify` is the one verification command, and CI runs it and nothing else, one lane per workflow (`loom.yml`, `arras.yml`, `docs.yml`). It ends by printing the branch's latest CI runs; read them.

- `scripts/verify` (`fast`): while working. loom's ruff, format check, mypy and unit tier; arras's svelte-check and vitest; the docs lane.
- `scripts/verify full`: before a commit. Adds loom's TeX tier, an arras build, the four Playwright suites and the two figure scripts.
- `scripts/verify paper`: the paper tier, by hand, with `LOOM_PAPER_FIXTURES` naming a directory holding `0805.2065/` and `1709.09864/`. Never in CI.
- `scripts/verify client`: the real-client tier, by hand, after a change to what loom generates for an agent client. It runs Claude Code against the generated settings and spends on the account of whoever runs it, so it never runs in CI.
- `--only loom|arras|docs`: one lane, when a change touches one codebase or only documents.
- `--steps "pytest tex"`: named steps whatever their tier; CI runs the TeX tier this way.

The docs lane runs `docs/work-queue/check.py` and the checks in `scripts/checks/`, each runnable alone and printing the command that fixes what it finds. The arras perf suites (`playwright.perf.config.ts`, `playwright.perf-live.config.ts`) run by hand.

## How the tests work

- loom's tests run loom through `loom/tests/helpers.py`, in process with exceptions let through, so a crash surfaces as a traceback. A test asserts one exit code (`ok`, `exits`, `refused`), never a set of them.
- The fake TeX toolchain (`loom/tests/fake_latex/fake_tex.py`) exists only in the directory `loom/tests/conftest.py` makes per session, never on the real PATH. Look up every external tool on PATH so a test can substitute it.
- Every LaTeX compile in a test runs isolated: empty HOME, TEXMFHOME, TEXMFLOCAL, TEXMFVAR and TEXMFCONFIG, no TEXINPUTS, the quilt root as cwd. A test never passes because of a file elsewhere on the machine.
- Fixture quilts are written from `loom/tests/quilts/sources/` by loom's own commands under a fixed clock (`uv run python scripts/gen_quilts.py all` in `loom/`); `test_the_checked_in_quilt_is_what_the_generator_writes` compares them byte for byte. Never edit one by hand.
- `test_never_modifies_author_files` runs every command on every fixture quilt and fails if an author file's hash changes.
- Every diagnostic code is in `docs/specs/diagnostics.md` before loom emits it, and some test emits it. `test_all_emitted_codes_are_known` checks only that the fixtures' codes are in loom's table, not that every code is emitted.
- CI sees only committed files, so `loom/tests/unit/test_tracked.py` fails on a shipped file under `loom/src`, `loom/tests/quilts` or `arras/src` that is untracked or ignored.
- When loom's pytest runs beside the Playwright suites, `scripts/verify` gives it half the cores and splits the rest among the suites, because together they once starved the reading suite into timeouts.
- Dragging the divider is judged by the frames Chrome's trace records as presented (`presented()` in `arras/tests/perf-live/measure.ts`); scrolling a PDF is budgeted on `frameP95` from the `requestAnimationFrame` recorder in the same file.

## Construction

The construction principles C1–C5 (`docs/design/principles.md`) govern how the code is built:

- C1, the scanner before everything: nothing else can be tested without it.
- C2, vertical slices: work runs end to end, source to arras page, not one layer at a time.
- C3, the fixture is the contract's executable form: a change to loom's output regenerates it (`docs/specs/tools/refresh-fixture.sh`); a change to the interface changes it first.
- C4, author files are sacred: the test comes before the command that touches a file.
- C5, two codebases sharing nothing but `docs/specs/`.

## Rules for every change

- Never edit anything under `~/notes/`. Paper sources, the author's included, are copies under the workspace's gitignored `tests/fixtures/`, never committed, and neither are the quilts `demos/build.py` builds from them.
- Prose is never hard-wrapped: one line per paragraph, in Markdown, docstrings and comments. `scripts/checks/hardwrap.py` enforces it on added lines.
- Docstrings follow `CLAUDE.md`'s two styles and describe the current state only; review documentation with its ten passes.

## How the documents change

The design is still being discovered, and the previous system failed by treating it as a fixed specification. `docs/design/` records current thinking, not a contract. When implementation teaches you something, update the design document in the same change and explain why in the commit message. Open questions belong in the design document beside what they affect; the work queue holds deferred work, not design questions. Only an entry in `docs/design/invariants.md` changes deliberately, with a dated line there.

Every commit message explains the why of its change. `docs/design/decision-records-frozen.md` is frozen history: read it, never extend it.

The work queue, whose mechanical rules `docs/work-queue/check.py` enforces:

- An item is a row in the queue's README and a `WQ-NN-<slug>.md` beside it, with an observable trigger (a measurement crossing a threshold, a capability existing, a dependency landing); its "why deferred" is that trigger inverted.
- The cap is 45 active items; a forty-sixth means promoting, merging or dropping one.
- An item closes by deleting its file and row and adding one line to `closed.md`. Ids are never reused.

## Releases

`loom/docs/RELEASE.md` is loom's release checklist; follow it, not a summary. It stops before publishing: publishing to PyPI is the maintainer's step, never a script's or an agent's. arras is not published on its own; it ships as the bundle vendored into loom (`loom/scripts/vendor_arras.py`).
