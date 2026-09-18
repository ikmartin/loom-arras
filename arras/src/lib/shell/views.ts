// The views the shell offers. Every shell contains the same elements and no shell contains anything another lacks (book 15.2), so the list lives here and each arrangement renders it.

import type { Manifest } from '$lib/manifest/types';
import { canonUrl, masterUrl } from '$lib/nav';

export interface View {
	id: string;
	label: string;
	href: string;
	/** The icon strip's drawing for this view, by name; see `$lib/components/Icon.svelte`. Every one also carries its label as an aria-label. */
	icon: string;
}

export function viewsOf(m: Manifest | null): View[] {
	const master = m?.masters.find((x) => x.default) ?? m?.masters[0];
	// a corpus whose drafting directory is empty is still worth reading: the newest landmark stands in for the document
	const newest = m?.canon?.length ? m.canon[m.canon.length - 1] : undefined;
	const read = master ? masterUrl(master.path) : newest ? canonUrl(newest.path) : '/';
	return [
		{ id: 'home', label: 'home', href: '/', icon: 'home' },
		{ id: 'read', label: 'read', href: read, icon: 'read' },
		{ id: 'graph', label: 'graph', href: '/graph', icon: 'graph' },
		{ id: 'review', label: 'review', href: '/review', icon: 'review' },
		{ id: 'problems', label: 'problems', href: '/problems', icon: 'problems' },
		{ id: 'references', label: 'references', href: '/references', icon: 'references' }
	];
}

/** Which view a path belongs to, for marking the current item. */
export function viewOf(path: string): string {
	if (path === '/') return 'home';
	if (path.startsWith('/master') || path.startsWith('/canon')) return 'read';
	if (path.startsWith('/node') || path.startsWith('/digest')) return 'read';
	if (path.startsWith('/graph')) return 'graph';
	if (path.startsWith('/review')) return 'review';
	if (path.startsWith('/problems')) return 'problems';
	if (path.startsWith('/references')) return 'references';
	return '';
}

/** The indexes, which every shell offers below its main list. */
export const INDEXES = [
	{ label: 'threads', href: '/threads' },
	{ label: 'tags', href: '/tags' },
	{ label: 'taxa', href: '/taxa' },
	{ label: 'loose', href: '/loose' }
];
