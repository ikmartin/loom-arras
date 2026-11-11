// Annotations indexed by what they are about, built once per manifest.
//
// Every surface that draws a comment asks "which annotations are on this key", and each of them answered by scanning
// the whole table. One fragment mount asks it once per key, so a document of a hundred keys scanned a corpus of a
// thousand annotations a hundred times to answer a question one pass could have answered. The index is keyed on the
// manifest object itself, so a new poll gets a new index for free and a stale one cannot be returned.

import type { Annotation, Manifest } from '$lib/manifest/types';

interface Index {
	byTarget: Map<string, Annotation[]>;
	byParent: Map<string, Annotation[]>;
}

const cache = new WeakMap<Manifest, Index>();

function index(m: Manifest): Index {
	const found = cache.get(m);
	if (found) return found;
	const built: Index = { byTarget: new Map(), byParent: new Map() };
	for (const a of Object.values(m.annotations ?? {})) {
		const into = a.in_reply_to ? built.byParent : built.byTarget;
		const key = a.in_reply_to ?? a.target.key;
		const list = into.get(key);
		if (list) list.push(a);
		else into.set(key, [a]);
	}
	cache.set(m, built);
	return built;
}

/** Every annotation on this key, replies excluded; in manifest order. */
export function on(m: Manifest, key: string): Annotation[] {
	return index(m).byTarget.get(key) ?? [];
}

/** Every annotation on any of these keys, replies excluded: a node is its statement and its proofs. */
export function onAny(m: Manifest, keys: readonly string[]): Annotation[] {
	return keys.flatMap((k) => on(m, k));
}

/** The replies to one annotation. */
export function repliesTo(m: Manifest, id: string): Annotation[] {
	return index(m).byParent.get(id) ?? [];
}

/** Whether an annotation is settled, that is resolved. The same test as `fragments/mount`'s, here so the index's callers need not import the wiring. */
function isSettled(a: Annotation): boolean {
	return a.status !== 'open';
}

/** Whether any top-level annotation on these keys is settled: what lets a rail offer the settled control on a node where nothing is drawn at rest. */
export function settledOn(m: Manifest, keys: readonly string[]): boolean {
	return onAny(m, keys).some(isSettled);
}

/** Whether any top-level annotation read in the document at `path` is settled: one on the document itself, or on a key of a node the document reaches (a region's by its container, a proof's by its result) and not filed with another document. */
export function settledIn(m: Manifest, path: string): boolean {
	return Object.values(m.annotations ?? {}).some((a) => {
		if (a.in_reply_to || !isSettled(a)) return false;
		if (a.target.key === path) return true;
		if (a.in && a.in !== path) return false;
		const owner = m.regions?.[a.target.key]?.container ?? m.keys[a.target.key]?.node ?? a.target.key;
		return m.nodes[owner]?.reached_by.includes(path) ?? false;
	});
}
