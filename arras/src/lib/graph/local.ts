// The neighbourhood of one node, for the local graph (book 15.5.1): what it depends on and what depends on it, out to a chosen number of steps in either direction, plus the `see` relations, which are drawn but never followed.

import type { Manifest } from '$lib/manifest/types';

export interface LocalLink {
	/** The node that depends. */
	from: string;
	/** The node depended on, or the other end of a relation. */
	to: string;
	kind: string;
}

export interface Neighbourhood {
	nodes: string[];
	links: LocalLink[];
	/** Steps from the centre, per node; the centre is 0. */
	distance: Map<string, number>;
}

/** The statement a key belongs to: a proof's edges are its statement's, since a graph of results draws results. */
const ownerOf = (m: Manifest, key: string) => m.keys[key]?.node ?? key;

/**
 * Nodes within `depth` dependency steps of `center`, ignoring direction, and every link among them.
 *
 * Parameters
 * ----------
 * m : Manifest
 * center : string
 *     A node id; a key that is not a node (a proof) is taken as its statement.
 * depth : number, default 1
 *     Steps out from the centre. 0 is the centre alone.
 *
 * Returns
 * -------
 * Neighbourhood
 *     Nodes in breadth-first order from the centre, so the first entries are the nearest.
 */
export function neighbourhood(m: Manifest, center: string, depth = 1): Neighbourhood {
	const start = ownerOf(m, center);
	const adj = new Map<string, Set<string>>();
	const edges = new Map<string, LocalLink>();
	const touch = (a: string, b: string) => {
		(adj.get(a) ?? adj.set(a, new Set()).get(a)!).add(b);
		(adj.get(b) ?? adj.set(b, new Set()).get(b)!).add(a);
	};
	for (const e of m.edges) {
		const from = ownerOf(m, e.from);
		const to = ownerOf(m, e.to);
		if (from === to || !m.nodes[from] || !m.nodes[to]) continue;
		touch(from, to);
		const k = `${from}>${to}`;
		if (!edges.has(k)) edges.set(k, { from, to, kind: e.kind });
	}
	const distance = new Map([[start, 0]]);
	let front = [start];
	for (let d = 1; d <= depth && front.length; d++) {
		const next: string[] = [];
		for (const id of front)
			for (const nb of adj.get(id) ?? [])
				if (!distance.has(nb)) {
					distance.set(nb, d);
					next.push(nb);
				}
		front = next;
	}
	const nodes = m.nodes[start] ? [...distance.keys()] : [];
	const inside = new Set(nodes);
	const links = [...edges.values()].filter((l) => inside.has(l.from) && inside.has(l.to));
	for (const r of m.relations ?? []) {
		if (inside.has(r.from) && inside.has(r.to) && r.from !== r.to) links.push({ from: r.from, to: r.to, kind: r.kind });
	}
	return { nodes, links, distance };
}

/** A short name for a node in a small drawing: its taxon and number when it has one, otherwise its title, otherwise its id. */
export function shortLabel(m: Manifest, id: string, master?: string): string {
	const n = m.nodes[id];
	if (!n) return id;
	const path = master ?? m.masters.find((x) => x.default)?.path ?? '';
	const number = n.numbers[path]?.number;
	if (number) return `${n.taxon} ${number}`;
	if (n.title) return n.title.length > 28 ? n.title.slice(0, 27) + '…' : n.title;
	return n.id;
}
