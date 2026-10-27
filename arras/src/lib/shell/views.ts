// The column's two primary views, the reading address Docs returns to, and the development shelf's indexes.

import type { Manifest } from '$lib/manifest/types';
import { canonUrl, masterUrl } from '$lib/nav';
import { route } from '$lib/paths';

export interface Index {
	label: string;
	href: string;
}

/** Docs is reading and writing; Review is the quilt's management. The column's two tabs choose one. */
export type Primary = 'docs' | 'review';

/** Which primary view a page is under, by its route id: Review holds `/review` and `/problems`, and every other page is read under Docs. */
export function primaryOf(routeId: string | null): Primary {
	return routeId === '/review' || routeId === '/problems' ? 'review' : 'docs';
}

/**
 * The address Docs returns to: what was open, as it was left (`reading`, the workspace's own address or the one remembered from an earlier visit); else the default document; else the newest landmark, since a corpus whose drafting directory is empty is still worth reading; `''` when there is nothing to read.
 */
export function readingAddress(m: Manifest | null, reading = ''): string {
	if (reading) return reading;
	const master = m?.masters.find((x) => x.default) ?? m?.masters.find((x) => x.directory !== 'drafting-ai' && !x.closed && !x.context_only);
	if (master) return masterUrl(master.path);
	const newest = m?.canon?.length ? m.canon[m.canon.length - 1] : undefined;
	return newest ? canonUrl(newest.path) : '';
}

/** The indexes, which the development shelf in Settings offers. A function rather than a constant: the list depends on the corpus, and `route()` should not run at import time. */
export function indexesOf(m: Manifest | null): Index[] {
	const has = m?.publishes;
	return [
		{ label: 'threads', href: route('/threads'), when: has?.discussions },
		{ label: 'tags', href: route('/tags'), when: true },
		{ label: 'taxa', href: route('/taxa'), when: true },
		{ label: 'not in a document', href: route('/loose'), when: has?.documents }
	]
		.filter((x) => x.when !== false)
		.map(({ when: _when, ...x }) => x);
}
