// A key's own source text, fetched one key at a time (plan 0.11 Part E, specs/manifest.md §1).
//
// It is beside the manifest rather than in it: the manifest is loaded whole on every poll and already runs to hundreds of kilobytes, while source is wanted only when a reader asks to see it. A publisher need not write any, so `null` is an ordinary answer and means "this corpus does not publish source", not "something went wrong".

import { dataUrl } from '$lib/paths';

/** Cached per key for the life of the page: source does not change without the manifest's hash changing, and a reader toggling twice should not fetch twice. */
const cache = new Map<string, string | null>();

/** Where a key's source lives, if the publisher wrote any. The name is the key percent-encoded, as the fragment paths are. */
export function sourceUrl(key: string): string {
	return dataUrl('source/' + encodeURIComponent(key) + '.tex');
}

/** A key's source, or `null` when this corpus publishes none. Never throws: an absent file is an answer. */
export async function fetchSource(key: string): Promise<string | null> {
	if (cache.has(key)) return cache.get(key) ?? null;
	let text: string | null = null;
	try {
		const res = await fetch(sourceUrl(key));
		text = res.ok ? await res.text() : null;
	} catch {
		text = null;
	}
	cache.set(key, text);
	return text;
}

/** Forget what was fetched, for when the corpus underneath has changed. */
export function forgetSource(): void {
	cache.clear();
}

