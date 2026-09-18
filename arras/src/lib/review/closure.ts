// What a result rests on, as a stack (plan 0.11 Part D).
//
// The graph beside it answers "what would this disturb"; this answers "what does this rest on", which is the question you ask when reading an argument through rather than when judging a change. It is the shape the closure document had, as a page.

import type { Manifest } from '$lib/manifest/types';

/**
 * The keys a key rests on, to `depth` steps, in dependency order with the key itself last.
 *
 * Parameters
 * ----------
 * m : Manifest
 * key : string
 *     The key to read towards.
 * depth : number, default 1
 *     1 is what it uses directly; 2 adds what those use.
 *
 * Returns
 * -------
 * string[]
 *     Node ids, deepest first, with the result itself last. Ordering by distance is not a topological sort, but nothing appears before something it uses, which is the property a reader needs.
 */
export function stack(m: Manifest, key: string, depth = 1): string[] {
	const owner = m.keys[key]?.node ?? key;
	const node = m.nodes[owner];
	if (!m.keys[key] && !node) return [];
	// A result rests on whatever its PROOF rests on: in most quilts the statement's own `uses` is empty and every
	// dependency is declared inside the argument. Seeding with the statement alone answers a question nobody asked.
	const seeds = [key, ...(node?.proofs ?? [])].filter((k) => m.keys[k]);
	const distance = new Map<string, number>(seeds.map((k) => [k, 0]));
	let front = [...seeds];
	for (let d = 1; d <= depth && front.length; d++) {
		const next: string[] = [];
		for (const k of front)
			for (const used of m.keys[k]?.uses ?? [])
				if (!distance.has(used)) {
					distance.set(used, d);
					next.push(used);
				}
		front = next;
	}
	// Answered in nodes, not keys: a reader wants the results it stands on, and a statement and its proof are one result.
	const byNode = new Map<string, number>();
	for (const [k, d] of distance) {
		const id = m.keys[k]?.node ?? k;
		if (!m.nodes[id]) continue;
		byNode.set(id, Math.max(byNode.get(id) ?? 0, d));
	}
	byNode.delete(owner);
	const deps = [...byNode.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([id]) => id);
	return m.nodes[owner] ? [...deps, owner] : deps;
}
