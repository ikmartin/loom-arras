# Audit: dm-0003 (Theorem, Main)

[summary]
Of the four hypotheses, one is load-bearing and two are redundant; the closedness argument does more work than its conclusion needs. Errors were the referee's and are not repeated here.

[hypothesis-ledger]
- $X$ finite (statement). Implied by another hypothesis: widgets are finite by definition, dm-0001. file-verified. (a-2026-09-17-0004)
- $\sigma$ continuous (statement). Implied by another hypothesis: finite Hausdorff spaces are discrete. proved-here. (a-2026-09-17-0005)
- $X$ Hausdorff (statement). Load-bearing here: without it $\Fix(\sigma)$ need not be closed; 9 counterexamples on three points (trial 2). (a-2026-09-17-0006)

[citation-ledger]
- Man12, Proposition 3.2. Located as digest node Man12-prop-3.2. file-verified against the digest; the digest is `method: manual` and so is not itself verified against the paper. Used as an analogy; see the referee's open question a-2026-09-17-0003.

[self-containedness]
No failures: every symbol is defined in dm-0001 or dm-0002.

[sharpenings]
- The closedness clause holds in every Hausdorff topology, with no condition on $\sigma$, and follows from discreteness without the diagonal. (a-2026-09-17-0007)

[patch-list]
1. Statement: delete "with $X$ a finite set".
2. Statement: delete "for which $\sigma$ is continuous".
3. Proof: replace the diagonal argument by discreteness.
