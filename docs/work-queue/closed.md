# Closed

Append-only. One line per retired item: what it was, when it left, and where the substance went — a pointer to the plan or record that carries it, or one sentence on why it was dropped. Ids are never reused, so a reference from a chapter or a decision record stays resolvable after the item closes.

The full design of a built item lives in its plan; the full design of a dropped item lives in this repository's history. What is kept here is the epitaph, because a dropped item's *reason* is the part nothing else records.

## Retired items

| id | item | closed | outcome |
|---|---|---|---|
| WQ-20 | `loom bundle` of the main theorem in the man12 quilt, and the arras views over it | 2026-09-16 | dropped: a verification pass over one fixture, not a feature. Chapter 6 §6.10 already records what the man12 import produced; run it by hand if man12 is revisited. |
| WQ-01 | reference identity and the `reached` primitive | 2026-09-16 | graduated: the author committed to building it, so it is now [docs/plans/0.5-reference-identity-and-layout.md](../plans/0.5-reference-identity-and-layout.md). The first item to leave the queue by being built. |
| WQ-12 | an Emacs client | 2026-09-16 | dropped to stay under the cap: nobody on the project uses Emacs, and `eglot` needs only the server and a root function, so it costs no more to write the day someone wants it than it does today. |

## Milestones

The project was built to `docs/plans/implementation-plan.md` as milestones M0–M7, then extended by the 0.3 round. Every milestone is demonstrated. Each record holds the commands run, the output, the test counts and the deviations recorded; they were moved here from `docs/work-queue/closed/` when this queue replaced that directory's tracking role.

| milestone | demonstrated | record | notes |
|---|---|---|---|
| M0 skeleton | 2026-09-15 | [closed/M0.md](closed/M0.md) | CI green on loom (unit, tex) and arras (ci) |
| M1 read a quilt | 2026-09-15 | [closed/M1.md](closed/M1.md) | scanner reads all three real papers |
| M2 publish and view | 2026-09-15 | [closed/M2.md](closed/M2.md) | serve republishes in 0.88 s; fixture vendored |
| M3 review | 2026-09-15 | [closed/M3.md](closed/M3.md) | the timeline of §7.11 as one test |
| M4 bring a paper in | 2026-09-15 | [closed/M4.md](closed/M4.md) | both arXiv papers and relloc import with identity passing; ACGS needs no hand edits |
| M5 digests | 2026-09-16 | [closed/M5.md](closed/M5.md) | Manolache extracted into relloc; every postnote resolves; bundles compile |
| M6 the AI layer | 2026-09-16 | [closed/M6.md](closed/M6.md) | Claude Code session on the demo; the Codex half is [WQ-18](WQ-18-codex-session.md) |
| M7 acceptance | 2026-09-16 | [closed/M7.md](closed/M7.md) | criteria 1–8 on `demos/relloc`; 9 is [WQ-16](WQ-16-overleaf.md), 10 is [WQ-17](WQ-17-external-user.md) |
| book revision | 2026-09-16 | [closed/book-revision.md](closed/book-revision.md) | every chapter revised to the implementation; DR-81 to DR-83 |
| 0.3 arras redesign | 2026-09-16 | [closed/0.3-round.md](closed/0.3-round.md) | Chapter 15 built: three shells, tokens, contents from `inclusion`, anchors, force graph; DR-90 to DR-96 |
| 0.3 loom 0.2 | 2026-09-16 | [closed/0.3-round.md](closed/0.3-round.md) | `see:` relations, the brainstorm mode, candidate taxa; DR-89 |
| 0.3 editor clients | 2026-09-16 | [closed/0.3-round.md](closed/0.3-round.md) | `loom-lsp`, `loom-nvim` and `loom-vscode` built and tested against real editors; DR-97 |
