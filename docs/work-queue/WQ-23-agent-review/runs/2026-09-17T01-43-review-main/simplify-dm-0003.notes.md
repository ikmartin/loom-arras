# Simplify: dm-0003 (Theorem, Main)

[summary]
Starts from the audit's patch-list and the referee's correction. The statement is shorter, correct, and states the stronger closedness claim; the proof loses the diagonal argument.

[simplifications]
- unnecessary-hypothesis. Statement, "with $X$ a finite set". Licensed by dm-0001: no step uses finiteness except through the definition. Old: "a widget with $X$ a finite set". New: "a widget".
- unnecessary-hypothesis. Statement, "for which $\sigma$ is continuous". Licensed by audit a-2026-09-17-0005: implied by Hausdorff and finiteness. Removing a hypothesis strengthens the statement.
- condensation. Proof, closedness. Old: the diagonal argument. New: "A finite Hausdorff space is discrete, so every subset of $X$ is closed." Licensed by audit a-2026-09-17-0007.

[rejected]
- Removing the appeal to Man12, Proposition 3.2. Considered as scaffolding for an argument no longer used; left in place because the referee's question a-2026-09-17-0003 on its role is still open.

[revised]
`proposal-dm-0003.diff`, revised in place over the referee's version. Built with `loom bundle dm-0003 --with`.

[meaning-drift-check]
- The parity claim changes meaning, deliberately: the original equivalence was false, and the revision states the true congruence the proof establishes. This is the referee's correction carried forward, not drift introduced here.
- The closedness claim is strengthened, not weakened: it now holds for every Hausdorff topology rather than only those making $\sigma$ continuous. Every topology the original covered is still covered.
