// Document order (book 15.5): where each node falls in a master, from the inclusion tree the manifest publishes.

import type { Manifest } from '$lib/manifest/types';

/**
 * Each node's position in the reading order of one master.
 *
 * Parameters
 * ----------
 * m : Manifest
 * master : string
 *     A master's path; anything the tree does not reach is absent from the map.
 *
 * Returns
 * -------
 * Map<string, number>
 *     Node id to its place, counting from 0.
 */
export function documentOrder(m: Manifest, master: string): Map<string, number> {
	const out = new Map<string, number>();
	const walk = (t: { key?: string; children?: unknown[] } | undefined) => {
		if (!t) return;
		if (t.key && m.nodes[t.key] && !out.has(t.key)) out.set(t.key, out.size);
		for (const c of (t.children ?? []) as { key?: string; children?: unknown[] }[]) walk(c);
	};
	walk(m.inclusion?.[master] as { key?: string; children?: unknown[] } | undefined);
	return out;
}

/** A node's place in the reading order, with anything unplaced sorted to the end by id. */
export function placeOf(order: Map<string, number>, id: string): number {
	return order.get(id) ?? Number.MAX_SAFE_INTEGER;
}
