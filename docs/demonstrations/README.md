# Demonstrations

One file per milestone records what was run, what came out, and whether the milestone's demonstration from `docs/book/13-plan.md` §13.2 was met. This table is the one-glance status; an agent resuming work reads it first and continues with the first row that is not `demonstrated`.

| milestone | status | date | notes |
|---|---|---|---|
| M0 skeleton | demonstrated | 2026-09-15 | CI green on loom (unit, tex) and arras (ci) |
| M1 read a quilt | demonstrated | 2026-09-15 | scanner reads all three real papers; see M1.md |
| M2 publish and view | demonstrated | 2026-09-15 | serve republishes in 0.88 s; 23 e2e; fixture vendored; see M2.md |
| M3 review | demonstrated | 2026-09-15 | timeline 7.11 as one test; see M3.md |
| M4 bring a paper in | demonstrated | 2026-09-15 | both arXiv papers and relloc import with identity passing; ACGS needs no hand edits; see M4.md |
| M5 digests | demonstrated | 2026-09-16 | Manolache extracted into relloc; every postnote resolves; bundles compile; see M5.md |
| M6 the AI layer | demonstrated | 2026-09-16 | Claude Code session on the demo; Codex half blocked (not installed); see M6.md |
| M7 acceptance | demonstrated | 2026-09-16 | criteria 1 to 8 on demos/relloc; 9 (Overleaf) and 10 (external user) blocked on the user; see M7.md |
| book revision | demonstrated | 2026-09-16 | every chapter revised to the implementation; DR-81 to DR-83; see book-revision.md |
| 0.3 arras redesign | demonstrated | 2026-09-16 | chapter 15 built: three shells, tokens, contents from `inclusion`, anchors, force graph; 43 end-to-end tests; DR-90 to DR-96; see `records/record-2026-09-16.md` |
| 0.3 loom 0.2 | demonstrated | 2026-09-16 | `see:` relations, the brainstorm mode, candidate taxa; the three use cases performed on `demos/relloc`; DR-89 |
| 0.3 editor clients | demonstrated | 2026-09-16 | `loom-lsp`, `loom-nvim` and `loom-vscode` built and tested against real editors; DR-97; Chapter 16 |

Status values: `pending`, `in progress`, `demonstrated`, `blocked (reason)`.