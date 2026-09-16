// The views the shell offers. Every shell contains the same elements and no shell contains anything another lacks (book 15.2), so the list lives here and each arrangement renders it.

import type { Manifest } from '$lib/manifest/types';
import { masterUrl } from '$lib/nav';

export interface View {
	id: string;
	label: string;
	href: string;
	/** A single glyph for the icon strip; every one also carries its label as an aria-label. */
	icon: string;
}

export function viewsOf(m: Manifest | null): View[] {
	const master = m?.masters.find((x) => x.default) ?? m?.masters[0];
	return [
		{ id: 'home', label: 'home', href: '/', icon: '◇' },
		{ id: 'read', label: 'read', href: master ? masterUrl(master.path) : '/', icon: '▤' },
		{ id: 'graph', label: 'graph', href: '/graph', icon: '◈' },
		{ id: 'review', label: 'review', href: '/review', icon: '✓' },
		{ id: 'problems', label: 'problems', href: '/problems', icon: '!' },
		{ id: 'references', label: 'references', href: '/references', icon: '¶' }
	];
}

/** Which view a path belongs to, for marking the current item. */
export function viewOf(path: string): string {
	if (path === '/') return 'home';
	if (path.startsWith('/master')) return 'read';
	if (path.startsWith('/node') || path.startsWith('/digest')) return 'read';
	if (path.startsWith('/graph')) return 'graph';
	if (path.startsWith('/review') || path.startsWith('/blockers')) return 'review';
	if (path.startsWith('/problems')) return 'problems';
	if (path.startsWith('/references')) return 'references';
	return '';
}

/** The indexes, which every shell offers below its main list. */
export const INDEXES = [
	{ label: 'threads', href: '/threads' },
	{ label: 'tags', href: '/tags' },
	{ label: 'taxa', href: '/taxa' },
	{ label: 'loose', href: '/loose' },
	{ label: 'blockers', href: '/blockers' }
];
