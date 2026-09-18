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

/** The undiscarded replies to one annotation. */
export function repliesTo(m: Manifest, id: string): Annotation[] {
	return (index(m).byParent.get(id) ?? []).filter((a) => !a.discarded);
}

/** The open, undiscarded, top-level annotations on a key: what a reader is being asked to answer. */
export function openOn(m: Manifest, key: string): Annotation[] {
	return on(m, key).filter((a) => !a.discarded);
}
