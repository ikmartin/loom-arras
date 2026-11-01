## [overview]
Bellamy counts the lattice points of the median polytope $M(D)$ of a weighted digraph $D$. The main result, [](quilt:Bellamy19-thm-3.2), says the count $L(k)$ of points in $kM(D)$ is a polynomial in $k$ when $D$ is balanced; the hardest step is the integrality of the vertices of $M(D)$, [](quilt:Bellamy19-thm-2.3).

## [proof-basics]
- [](quilt:Bellamy19-thm-2.3): every vertex of $M(D)$ is integral, by total unimodularity of the incidence matrix (memory-grade: the paper's argument was read from its page 4).
- [](quilt:Bellamy19-thm-3.2): Ehrhart's theorem applied to an integral polytope gives the polynomial.

## [dependencies]
- [](quilt:Bellamy19-thm-3.2) rests on [](quilt:Bellamy19-thm-2.3); balance is used only there.

## [reconstruction-plan]
1. Prove integrality of the vertices from total unimodularity.
2. Apply Ehrhart's theorem.
