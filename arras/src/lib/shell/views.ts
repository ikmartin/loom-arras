// The views the shell offers. Every shell contains the same elements and no shell contains anything another lacks (book 15.2), so the list lives here and each arrangement renders it.

import type { Manifest } from '$lib/manifest/types';
import { canonUrl, masterUrl } from '$lib/nav';
import { route } from '$lib/paths';

export interface Index {
	label: string;
	href: string;
}

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
	const read = master ? masterUrl(master.path) : newest ? canonUrl(newest.path) : route('/');
	const has = m?.publishes;
	// `undefined` keeps a view: before the manifest loads there is nothing to go on, and a shell that draws six items
	// and then removes two is worse than one that never had them. A declared `false` is the only thing that removes.
	return [
		{ id: 'home', label: 'home', href: route('/'), icon: 'home', when: true },
		{ id: 'read', label: 'read', href: read, icon: 'read', when: has?.documents },
		{ id: 'graph', label: 'graph', href: route('/graph'), icon: 'graph', when: true },
		{ id: 'review', label: 'review', href: route('/review'), icon: 'review', when: has?.review },
		{ id: 'digest', label: 'digest', href: route('/digest'), icon: 'digest', when: has?.bibliography },
		{ id: 'problems', label: 'problems', href: route('/problems'), icon: 'problems', when: true },
		{ id: 'references', label: 'references', href: route('/references'), icon: 'references', when: has?.bibliography }
	]
		.filter((v) => v.when !== false)
		.map(({ when: _when, ...v }) => v);
}

/** Which view a path belongs to, for marking the current item. */
export function viewOf(path: string): string {
	if (path === '/') return 'home';
	if (path.startsWith('/master') || path.startsWith('/canon')) return 'read';
	if (path.startsWith('/digest')) return 'digest';
	if (path.startsWith('/node')) return 'read';
	if (path.startsWith('/graph')) return 'graph';
	if (path.startsWith('/review')) return 'review';
	if (path.startsWith('/problems')) return 'problems';
	if (path.startsWith('/references')) return 'references';
	return '';
}

/** The indexes, which every shell offers below its main list. A function rather than a constant: the list depends on the corpus, and `route()` should not run at import time. */
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
