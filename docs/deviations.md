# Deviations from the book

Every place the implementation departs from a `[decided]` statement, or settles an `[assumed]` or `[deferred]` one in a way worth recording. Each row also has a decision record in `docs/book/A-decision-records.md` (DR-39 onward). The final book revision walks this table and marks each row `book updated: y`.

| date | section | book says | implemented | why | DR | book updated |
|---|---|---|---|---|---|---|
| 2026-09-15 | 10.8 | arras source never contains the words quilt, digest, proof, or any loom command | guard test forbids quilt, atomize, unravel, and "loom <command>" phrases; digest and proof are exempt as manifest field names and the spec's route | `specs/manifest.md` §3, §4, §13 and route `/digest/<citekey>` use them; `crypto.subtle.digest()` too | DR-39 | n |
