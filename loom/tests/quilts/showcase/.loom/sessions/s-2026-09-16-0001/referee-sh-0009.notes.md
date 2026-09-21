## [summary]
The rank theorem is correct and its proof is complete. The counting theorem is not: it takes integrality of the polytope's vertices from a saturation statement that does not give it, and the lemma meant to close that gap is marked incomplete. Everything else here is exposition.

## [notation]
- $\Zcyc(\quiv)$ is the cycle lattice, written $\mathcal{Z}(Q)$ in Arden24.
- $\Pi$ is the flow polytope of sh-000C; Bellamy's $M(D)$ is a different polytope over the same arc set.
- $c$ is the number of connected components of the underlying graph.

## [referee-review] Major and minor issues

### Major Issues
- Integrality of the vertices of $\Pi$ is asserted from saturation of $\Zcyc(\quiv)$, and saturation is a statement about the lattice rather than about the polytope. Bellamy's theorem assumes the second. (a-2026-09-16-0003)
- The rank formula does not say how a loop is counted, and the answer changes the rank. (a-2026-09-16-0001)

### Minor Issues
- The kernel--image step of the rank proof is one clause doing three things; a replacement is attached. (a-2026-09-16-0002)

### Clarity/Exposition
- Connectedness is never assumed and never excluded, and the rank formula is the one statement where it would matter. (a-2026-09-16-0006)

## [decision]
Minor Revision for the rank theorem; the counting theorem needs the integrality lemma before it can be accepted.
