// A kind's internal views (plan 0.13.3, plan 0.16 decision 10): several readings of one thing, drawn at the head of its pane's tab strip, before the tabs, rather than in a band the renderer draws for itself.

import type { Manifest } from '$lib/manifest/types';

export interface View {
	id: string;
	label: string;
	/** Why the view cannot be read now, when it cannot: it is drawn greyed, with this as its title, rather than dropped, so the others keep their places. */
	off?: string;
}

/** A work's views, Paper · Info (K1): the paper greyed where no copy can be read, and what is known of the work, its digest's results among it, behind Info. */
export function workViews(m: Manifest, citekey: string): View[] {
	const ref = m.references[citekey];
	const off = ref?.unreadable ? `Declared unreadable: ${ref.unreadable.why}` : !ref?.artifacts?.pdf ? 'No copy of this work is on file' : undefined;
	return [{ id: 'paper', label: 'Paper', ...(off ? { off } : {}) }, { id: 'info', label: 'Info' }];
}

/** The item's default view: its first that can be read, so a paper with no copy opens on what is known of it. */
export function defaultView(views: View[]): string | undefined {
	return (views.find((v) => !v.off) ?? views[0])?.id;
}

/** The view shown: the one the item names when it is listed and can be read, else the default. */
export function currentView(views: View[], named: string | undefined): string | undefined {
	return views.some((v) => v.id === named && !v.off) ? named : defaultView(views);
}
