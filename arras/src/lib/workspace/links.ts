// Where a followed link opens (plan 0.13.3 W7, H7). **Everything adds; the only question is which pane.** A link inside an item is a connection between two texts, so it opens in the other pane and both ends survive it; a click anywhere else — the side panel, the rail, a preview card — is a choice of what to read, and opens in the focused pane. A link's destination is a fact about the pane it lives in, not about what had focus a moment ago.
//
// **A context's links open in the context's own pane.** A context is about the node beside it, so the other pane is the node itself: opening there would hide the one term of the relation the reader followed it from (P5). In its own pane the context goes behind a tab, and the node stays.
//
// One capture-phase listener for the whole viewer, so no renderer decides for itself and a link the router would otherwise follow is answered before it does.

import { goto } from '$app/navigation';
import type { Manifest } from '$lib/manifest/types';
import { pdf } from '$lib/pdf.svelte';
import { isWorkLink, locate, parseWorkLink } from '$lib/worklink';
import { itemFromPath, itemKey, pathFor, type Item } from './item';
import { workspace } from './store.svelte';

/** The pane an element stands in, or -1 when it is in none. */
export function paneOfElement(el: Element | null): number {
	const at = el?.closest<HTMLElement>('[data-pane]');
	return at ? Number(at.dataset.pane) : -1;
}

/**
 * The item a link names, or null when it names nothing to read.
 *
 * A `cited:` link names a place in a work by the work's identifier; it is an item only when the copy on file is the very artifact the identifier names (book 10.4.1).
 */
export function itemForHref(m: Manifest, href: string): Item | null {
	if (isWorkLink(href)) {
		const link = parseWorkLink(href);
		const where = link ? locate(m, link) : null;
		if (!link || !where?.local || !where.ref) return null;
		const { id: _id, ...place } = link;
		return { kind: 'work', id: where.ref.citekey, place: { ...place, page: place.page ?? 1 } };
	}
	let url: URL;
	try {
		url = new URL(href, location.href);
	} catch {
		return null;
	}
	if (url.origin !== location.origin) return null;
	return itemFromPath(m, url.pathname + url.search + url.hash);
}

/**
 * Open what a link names, from the pane it stands in.
 *
 * Parameters
 * ----------
 * item : Item
 * from : number
 *     The pane the link is in, or -1 for a link outside every pane.
 * where : 'beside' | 'here'
 *     A click opens beside; the preview's `open here` opens in the link's own pane (H6).
 */
export function follow(item: Item, from: number, where: 'beside' | 'here' = 'beside'): void {
	if (from < 0) workspace.here(item);
	else if (where === 'here') workspace.openIn(item, from);
	else workspace.beside(item, from);
}

/** Where a click on a link in pane `from` opens it: beside, except inside a context, whose links open in its own pane. */
export function clickWhere(from: number): 'beside' | 'here' {
	return from >= 0 && workspace.active(from)?.kind === 'context' ? 'here' : 'beside';
}

/**
 * Open a session's discussion beside what is being read, or reveal it where it is, without taking focus.
 *
 * Choosing where to write is not a change of what is being read, so the rail keeps the tools of the item the reader was in.
 */
export function openDiscussion(id: string): void {
	if (!workspace.onScreen) return;
	const item: Item = { kind: 'session', id };
	const was = workspace.panes.length ? workspace.focus : -1;
	if (was < 0) {
		workspace.here(item);
		return;
	}
	const current = workspace.active(was);
	workspace.beside(item, was);
	// beside focuses what it opened; the reader's pane is the one they were in, wherever that item now stands
	const back = current ? workspace.paneOf(itemKey(current)) : was;
	workspace.focusOn(back >= 0 ? back : was);
}

/**
 * Install the listener. Returns its removal.
 *
 * Parameters
 * ----------
 * active : () => boolean
 *     Whether reading mode is on screen; elsewhere the router follows links as it always did, and arriving in reading mode opens what was followed.
 * manifest : () => Manifest | null
 */
export function interceptLinks(active: () => boolean, manifest: () => Manifest | null): () => void {
	const click = (e: MouseEvent) => {
		if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
		const a = (e.target as Element | null)?.closest?.('a');
		const href = a?.getAttribute('href');
		if (!a || !href || a.target === '_blank' || a.hasAttribute('download')) return;
		const m = manifest();
		if (!m) return;
		const from = paneOfElement(a);
		// a jump within the text the link is in: that pane scrolls, and the item remembers where it now is
		if (href.startsWith('#')) {
			if (from < 0) return;
			e.preventDefault();
			const id = decodeURIComponent(href.slice(1));
			const pane = a.closest('[data-pane]');
			pane?.querySelector<HTMLElement>(`[id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: 'start' });
			const here = workspace.active(from);
			if (here) workspace.update(itemKey(here), { anchor: id });
			return;
		}
		if (isWorkLink(href)) {
			e.preventDefault();
			const item = itemForHref(m, href);
			// no copy of that artifact here: the modal says so and offers the source (15.3.7)
			if (!item) {
				const link = parseWorkLink(href);
				if (link) pdf.open(link);
				return;
			}
			// from outside reading mode, into it: arriving opens the work in the focused pane
			if (active()) follow(item, from, clickWhere(from));
			else void goto(pathFor(m, item));
			return;
		}
		if (!active()) return;
		const item = itemForHref(m, href);
		if (!item) return;
		e.preventDefault();
		follow(item, from, clickWhere(from));
	};
	document.addEventListener('click', click, true);
	return () => document.removeEventListener('click', click, true);
}
