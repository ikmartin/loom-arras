// What reading mode shows (plan 0.13.3): an **item** is a thing with an address, a renderer, controls and optionally internal views. This module is the address half — what an item is, and the codec between an item and the route URL that names it. Nothing here renders.
//
// An item's identity is its kind and id. Its view and its place in it are state, not identity: a second tab of one document would be one document in two states (W8).

import { base } from '$app/paths';
import { canonUrl, keyFromParam, masterStem, masterUrl, nodeUrl, workUrl } from '$lib/nav';
import { route } from '$lib/paths';
import { placeParams, readKeys, type WorkLink } from '$lib/worklink';

export type ItemKind = 'document' | 'work' | 'node' | 'context' | 'session';

/** A place on a work's page: the work-link keys without the work's identifier, which the item already names. */
export type Place = Omit<WorkLink, 'id'>;

export interface Item {
	kind: ItemKind;
	/** A document's path, a work's citekey, a node's key, a session's id. */
	id: string;
	/** An internal view: a work's `digest` or `info`; absent means the first. */
	view?: string;
	/** An element to scroll to, by its published id: a document's section or result, a node's proof. */
	anchor?: string;
	/** Where on a work's pages. */
	place?: Place;
	/** An annotation to open at its mark on arrival: what a link to an annotation names. */
	note?: string;
	/** A document's review and incoming comparisons, which the review page opens by URL (`review`, `cause`, `incoming`). */
	params?: Record<string, string>;
	/** Stamped by the workspace each time the item is opened or revealed, so its renderer goes to the place again even when the place is unchanged. */
	seq?: number;
}

/** What the manifest must say for a document path to be told from a landmark and a stem to be resolved. */
export interface Documents {
	masters: { path: string }[];
	canon?: { path: string }[];
}

const DOC_PARAMS = ['review', 'cause', 'incoming'] as const;

/** The identity of an item, for finding it among the open ones. */
export function itemKey(i: Pick<Item, 'kind' | 'id'>): string {
	return `${i.kind}:${i.id}`;
}

/** Whether a document path is a landmark rather than a draft. */
export function isLandmark(m: Documents | null, path: string): boolean {
	return !!m?.canon?.some((c) => c.path === path);
}

/**
 * The item a route URL names, or null when it names none.
 *
 * Parameters
 * ----------
 * m : Documents | null
 *     The manifest, to resolve a document's stem to its path; with none, the stem stands in.
 * href : string
 *     A path with its query and hash, with or without the app's base; an absolute same-origin URL is accepted too.
 *
 * Returns
 * -------
 * Item | null
 *     The item, carrying the view, anchor and place the URL names.
 */
export function itemFromPath(m: Documents | null, href: string): Item | null {
	let url: URL;
	try {
		url = new URL(href, 'http://x');
	} catch {
		return null;
	}
	let path = url.pathname;
	if (base && path.startsWith(base)) path = path.slice(base.length) || '/';
	const [, head, ...rest] = path.split('/');
	const tail = rest.join('/');
	if (!tail) return null;
	const anchor = url.hash ? safe(url.hash.slice(1)) : undefined;
	const query = url.searchParams;
	const note = query.get('note') || undefined;
	switch (head) {
		case 'master':
		case 'canon': {
			const stem = safe(tail);
			const pool = head === 'canon' ? (m?.canon ?? []) : (m?.masters ?? []);
			const id = pool.find((d) => masterStem(d.path) === stem)?.path ?? stem;
			const params: Record<string, string> = {};
			for (const k of DOC_PARAMS) {
				const v = query.get(k);
				if (v) params[k] = v;
			}
			return { kind: 'document', id, ...(anchor ? { anchor } : {}), ...(note ? { note } : {}), ...(Object.keys(params).length ? { params } : {}) };
		}
		case 'library': {
			const place = readKeys({ id: '' }, url.search.slice(1)) as WorkLink;
			const { id: _drop, ...keys } = place;
			const view = query.get('view') || undefined;
			return { kind: 'work', id: safe(tail), ...(view ? { view } : {}), ...(Object.keys(keys).length ? { place: keys } : {}) };
		}
		case 'node':
			return { kind: 'node', id: keyFromParam(tail), ...(anchor ? { anchor } : {}), ...(note ? { note } : {}) };
		case 'context':
			return { kind: 'context', id: keyFromParam(tail) };
		case 'session':
		// a run's record was a page of its own; its address now names the session it belongs to, so old links still land
		case 'thread':
			return { kind: 'session', id: safe(tail), ...(query.get('view') ? { view: query.get('view')! } : {}) };
		default:
			return null;
	}
}

/**
 * The route URL that names an item, with the app's base: the inverse of `itemFromPath`.
 *
 * Parameters
 * ----------
 * m : Documents | null
 *     The manifest, to tell a landmark from a draft.
 * item : Item
 *     The item, with whatever view, anchor and place it is at.
 *
 * Returns
 * -------
 * str
 *     Path, query and hash.
 */
export function pathFor(m: Documents | null, item: Item): string {
	const hash = item.anchor ? '#' + item.anchor : '';
	switch (item.kind) {
		case 'document': {
			const at = isLandmark(m, item.id) ? canonUrl(item.id) : masterUrl(item.id);
			const q = new URLSearchParams();
			for (const k of DOC_PARAMS) if (item.params?.[k]) q.set(k, item.params[k]);
			if (item.note) q.set('note', item.note);
			return at + (q.size ? '?' + q : '') + hash;
		}
		case 'work': {
			const q = placeParams(item.place ?? {});
			if (item.view) q.set('view', item.view);
			return workUrl(item.id) + (q.size ? '?' + q : '');
		}
		case 'node':
			return nodeUrl(item.id) + (item.note ? '?note=' + encodeURIComponent(item.note) : '') + hash;
		case 'context':
			return route('/context/' + item.id.split('/').map(encodeURIComponent).join('/'));
		case 'session':
			return route('/session/' + encodeURIComponent(item.id)) + (item.view ? '?view=' + encodeURIComponent(item.view) : '');
	}
}

function safe(s: string): string {
	try {
		return decodeURIComponent(s);
	} catch {
		return s;
	}
}
