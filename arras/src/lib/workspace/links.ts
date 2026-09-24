// Where a followed link opens (plan 0.14): **one rule, for every link in the viewer.** A link names an item and a place in it. If the item is already open, in either pane, it is brought to the front of its pane at that place and the pane takes focus — a document's links to its own content are the same case. If it is not open, it opens as a new tab in the pane the reader is not in, so both ends of the connection stay on screen (P5); with one pane, the second is made. A click outside every pane — the side panel, the rail — is a choice of what to read, and opens in the focused pane.
//
// Two link forms name things (specs/dialect.md §2.13): `quilt:KEY[#PLACE]` for what the quilt owns — a node, a document, an annotation, a session — and `cited:SCHEME:VALUE` for a place in a cited work. The viewer's own paths are read too.
//
// One capture-phase listener for the whole viewer, so no renderer decides for itself and a link the router would otherwise follow is answered before it does.

import { goto } from '$app/navigation';
import type { Manifest } from '$lib/manifest/types';
import { pdf } from '$lib/pdf.svelte';
import { sessionView } from '$lib/sessions/sessions.svelte';
import { isWorkLink, locate, pageOf, parseWorkLink } from '$lib/worklink';
import { anchorId, keyUrl } from '$lib/nav';
import { isDocument } from '$lib/review/run';
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
	if (href.startsWith('quilt:')) return itemForQuilt(m, href.slice('quilt:'.length));
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
 * The item a `quilt:` link names, by the key after the scheme, or null when the manifest knows no such thing.
 *
 * An annotation opens what it is on, with its box open (`note`); a session its Chat; a document path its document, at the place after `#`; any other key its node, at the place in it.
 */
export function itemForQuilt(m: Manifest, body: string): Item | null {
	const cut = body.indexOf('#');
	const key = decodeURIComponent(cut < 0 ? body : body.slice(0, cut));
	const place = cut < 0 ? '' : decodeURIComponent(body.slice(cut + 1));
	if (!key) return null;
	const note = m.annotations[key];
	if (note) return noteItem(m, threadOf(m, note.id), note.target);
	if ((m.sessions ?? []).some((s) => s.id === key) || m.threads[key]) return { kind: 'session', id: key };
	if (isDocument(m, key)) return { kind: 'document', id: key, ...(place ? { anchor: anchorId(place) } : {}) };
	const paper = paperAt(m, key);
	if (paper) return paper;
	const at = itemFromPath(m, keyUrl(m, key));
	if (!at) return null;
	if (!place) return at;
	// a place in a node is a region of it (`KEY#label`) or another key it holds, such as its proof
	const region = m.regions?.[`${key}#${place}`];
	return { ...at, anchor: anchorId(region ? `${key}#${place}` : place) };
}

/**
 * A result read off a cited work, as the paper at the page it is printed on: what a citation of it opens, so a link to it opens the same place (study F9). Null for anything else, or where no copy is filed or no page is known.
 */
export function paperAt(m: Manifest, key: string): Item | null {
	const node = m.nodes[key];
	const work = node?.digest ? m.references[node.digest] : undefined;
	const page = pageOf(node?.locator);
	return work?.artifacts?.pdf && page ? { kind: 'work', id: work.citekey, place: { page, result: key } } : null;
}

/** The note a reply answers, and so on up: a box opens on a thread, by the note that began it. */
function threadOf(m: Manifest, id: string): string {
	const seen = new Set<string>();
	let at = id;
	while (!seen.has(at)) {
		seen.add(at);
		const up = m.annotations[at]?.in_reply_to;
		if (!up || !m.annotations[up]) break;
		at = up;
	}
	return at;
}

/** Where an annotation is read: its target, with the annotation to open there. A box round an equation is filed under the region's key (`KEY#label`), and is read in the node that holds it. */
function noteItem(m: Manifest, id: string, target: { key: string; page?: number | null }): Item | null {
	const work = Object.values(m.references).find((r) => r.work === target.key || r.works?.includes(target.key));
	if (work) return { kind: 'work', id: work.citekey, place: { page: target.page ?? 1, annot: id } };
	if (isDocument(m, target.key)) return { kind: 'document', id: target.key, note: id };
	const at = itemFromPath(m, keyUrl(m, m.regions?.[target.key]?.container ?? target.key));
	return at ? { ...at, note: id } : null;
}

/**
 * Open what a link names, from the pane it stands in: where it is open, it is revealed there; otherwise it opens in the other pane.
 *
 * A node counts as open where an open document holds it (DR-280-ikmartin): the document is revealed at the node rather than the node opened beside it.
 *
 * Parameters
 * ----------
 * item : Item
 *     What to open, at its place.
 * from : number
 *     The pane the link is in, or -1 for a link outside every pane, which opens in the focused pane.
 * m : Manifest, optional
 *     What says which documents hold a node; without it a node is open only as itself.
 */
export function follow(item: Item, from: number, m: Manifest | null = null): void {
	const at = workspace.paneOf(itemKey(item));
	if (at >= 0) return workspace.openIn(item, at);
	const holder = m ? holding(m, item, from) : null;
	if (holder) return workspace.openIn(holder.item, holder.pane);
	if (from < 0) workspace.here(item);
	else workspace.beside(item, from);
}

/**
 * The open document a node link is revealed in, at the node, or null when none holds it.
 *
 * The document the link stands in first; then one on screen; then, among tabs behind others, the one last looked at. The name the link was given is the default document's, so it may read differently where it lands.
 */
export function holding(m: Manifest, item: Item, from: number): { item: Item; pane: number } | null {
	if (item.kind !== 'node') return null;
	const within = new Set(m.nodes[item.id]?.reached_by ?? []);
	if (!within.size) return null;
	const open: { doc: Item; pane: number; front: boolean }[] = [];
	workspace.panes.forEach((p, pane) => {
		for (const it of p.items) if (it.kind === 'document' && within.has(it.id)) open.push({ doc: it, pane, front: p.active === itemKey(it) });
	});
	if (!open.length) return null;
	const rank = (o: (typeof open)[number]) => (o.front && o.pane === from ? 3 : o.front ? 2 : 1);
	open.sort((a, b) => rank(b) - rank(a) || workspace.shownAt(itemKey(b.doc)) - workspace.shownAt(itemKey(a.doc)));
	const { doc, pane } = open[0];
	return { item: { kind: 'document', id: doc.id, anchor: item.anchor ?? anchorId(item.id), ...(item.note ? { note: item.note } : {}) }, pane };
}

/**
 * Close every session but `id`, wherever it stands: the Chat on screen is the selected session's, so two conversations are never open at once (plan 0.14).
 */
export function soleSession(id: string): void {
	for (let p = workspace.panes.length - 1; p >= 0; p--) {
		for (const it of [...workspace.panes[p].items]) if (it.kind === 'session' && it.id !== id) workspace.close(p, itemKey(it));
	}
}

/**
 * Select a session and open its Chat beside what is being read, or reveal it where it is, without taking focus. `select` is false for a caller that has set the selection itself.
 *
 * Choosing whom to talk to is not a change of what is being read, so the rail keeps the tools of the item the reader was in.
 */
export function openChat(id: string, m: Manifest | null, select = true): void {
	if (select) sessionView.select(id, m);
	if (!workspace.onScreen) return;
	soleSession(id);
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
		// a jump within the text the link is in: the same item at a new place, revealed where it is like any other
		if (href.startsWith('#')) {
			const here = from >= 0 ? workspace.active(from) : null;
			if (!here) return;
			e.preventDefault();
			follow({ ...here, anchor: decodeURIComponent(href.slice(1)), note: undefined }, from);
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
			if (active()) follow(item, from, m);
			else void goto(pathFor(m, item));
			return;
		}
		const quilt = href.startsWith('quilt:');
		// outside reading mode the router follows its own paths; a `quilt:` link it cannot, so it goes to its item's page
		if (!active() && !quilt) return;
		// a `quilt:` link is never a browser navigation, even to nothing
		if (quilt) e.preventDefault();
		const item = itemForHref(m, href);
		if (!item) return;
		e.preventDefault();
		if (active()) follow(item, from, m);
		else void goto(pathFor(m, item));
	};
	document.addEventListener('click', click, true);
	return () => document.removeEventListener('click', click, true);
}
