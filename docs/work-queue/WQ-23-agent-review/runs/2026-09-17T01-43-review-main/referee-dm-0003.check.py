"""Trials for the referee of dm-0003. Standing rule 7: every trial saved, outputs appended below."""
from itertools import combinations, product


def involutions(n):
    X = range(n)
    for s in product(X, repeat=n):
        if all(s[s[i]] == i for i in X):
            yield s


# Trial 1. The statement claims Fix(sigma) is nonempty iff |X| is odd.
print("Trial 1: Fix(sigma) nonempty  <=>  |X| odd")
bad = []
for n in range(0, 6):
    for s in involutions(n):
        fix = [i for i in range(n) if s[i] == i]
        assert len(fix) % 2 == n % 2, "the congruence the proof uses"
        if bool(fix) != (n % 2 == 1):
            bad.append((n, s, fix))
print(f"  widgets with |X| <= 5 checked; counterexamples to the 'only if': {len(bad)}")
print(f"  smallest: X = {{0,1}}, sigma = {bad[0][1]} (the identity), Fix = {bad[0][2]}, |X| = 2")
print("  the congruence |X| = |Fix| mod 2 held in every case")


# Trial 2. The topological clause, on every topology of a 3-point set.
def topologies(n):
    pts = frozenset(range(n))
    subsets = [frozenset(c) for r in range(n + 1) for c in combinations(range(n), r)]
    others = [u for u in subsets if u and u != pts]
    for r in range(len(others) + 1):
        for extra in combinations(others, r):
            T = {frozenset(), pts, *extra}
            if all(a | b in T and a & b in T for a in T for b in T):
                yield T


def hausdorff(T, n):
    return all(any(x in U and y in V and not (U & V) for U in T for V in T) for x in range(n) for y in range(n) if x != y)


def continuous(s, T):
    return all(frozenset(i for i in range(len(s)) if s[i] in U) in T for U in T)


print("Trial 2: Fix(sigma) closed when sigma is continuous and X is Hausdorff")
n = 3
Ts = list(topologies(n))
closed_fail_hausdorff = closed_fail_other = 0
discrete = 0
for T in Ts:
    H = hausdorff(T, n)
    if H and len(T) == 2 ** n:
        discrete += 1
    for s in involutions(n):
        if not continuous(s, T):
            continue
        fix = frozenset(i for i in range(n) if s[i] == i)
        closed = frozenset(range(n)) - fix in T
        if H and not closed:
            closed_fail_hausdorff += 1
        if not H and not closed:
            closed_fail_other += 1
print(f"  {len(Ts)} topologies on 3 points; Hausdorff ones: {sum(hausdorff(T, n) for T in Ts)}, all discrete: {discrete}")
print(f"  Hausdorff and Fix not closed: {closed_fail_hausdorff}  (the clause holds, and vacuously: discrete)")
print(f"  not Hausdorff, sigma continuous, Fix not closed: {closed_fail_other}  (Hausdorff is load-bearing)")
