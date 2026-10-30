// Where the reader is (plan 0.21.8): the focused pane's item, the block at its top, the words selected or the region of a page, the block under review, and the session annotations land in, reported to the publisher's `here` so that `loom here` can tell an agent what "this" is.
//
// **The tab touched last wins.** Every tab reports when its place settles and again the moment it gains focus or comes back into view, and the publisher keeps only the last report. The publisher holds it in memory; nothing here or there writes it down.

import { itemKey, type Item } from '$lib/workspace/item';
import { workspace } from '$lib/workspace/store.svelte';
import { workState } from '$lib/workspace/state.svelte';
import { sessionView } from '$lib/sessions/sessions.svelte';
import { can, write } from '$lib/write';
import { keyOf, quoteOf } from '$lib/fragments/quote';

/** The block at the top of a pane: its `data-src` and the key it belongs to. */
export interface Block {
	src: string;
	key: string;
}

/** Words selected, or a region drawn: in a document by key, on a paper by page with rectangles in points from the page's top left. */
export interface Selection {
	item: string;
	key?: string;
	page?: number;
	text?: string;
	rects?: number[][];
}

/** What the renderers know of the reader's place, which nothing else keeps: written by the pane, the paper and Review, read by the report. */
class Here {
	/** By item key. */
	block = $state<Record<string, Block>>({});
	/** Words selected in the text; gone when the selection is. */
	selection = $state<Selection | null>(null);
	/** A region drawn with the box tool, kept until another replaces it. */
	region = $state<Selection | null>(null);
	/** The block under review and why, while Review shows one. */
	review = $state<{ key: string; cause: string | null } | null>(null);

	setBlock(item: string, block: Block | null): void {
		const was = this.block[item];
		if (block ? was?.src === block.src && was?.key === block.key : !was) return;
		const next = { ...this.block };
		if (block) next[item] = block;
		else delete next[item];
		this.block = next;
	}
}

export const here = new Here();

export type Route = 'reading' | 'review' | 'elsewhere';

export interface PlaceInput {
	route: Route;
	/** The viewer's path, for a page outside reading and Review. */
	path?: string;
	current: Item | null;
	beside: Item | null;
	block?: Block;
	selection: Selection | null;
	region: Selection | null;
	/** The paper's page in view, when the current item is a work. */
	page?: number;
	review: { key: string; cause: string | null } | null;
	session: string | null;
}

/** An item as the publisher is told it: what it is and which, and a paper's place; the view, anchor and note are the viewer's. */
function bare(item: Item | null): Record<string, unknown> | undefined {
	if (!item) return undefined;
	return { kind: item.kind, id: item.id, ...(item.place ? { place: item.place } : {}) };
}

/** The body of a `here` report: one place, the current pane's, with the selection only when it is in the current item. */
export function placeOf(i: PlaceInput): Record<string, unknown> {
	const out: Record<string, unknown> = { route: i.route };
	if (i.session) out.session = i.session;
	if (i.route === 'review') {
		if (i.review) out.review = i.review;
		return out;
	}
	if (i.route === 'elsewhere') {
		if (i.path) out.path = i.path;
		return out;
	}
	const key = i.current ? itemKey(i.current) : '';
	out.item = bare(i.current);
	if (i.block) out.block = i.block;
	const mark = i.selection?.item === key ? i.selection : i.region?.item === key ? i.region : null;
	if (mark) {
		const { item: _drop, ...rest } = mark;
		out.selection = rest;
	}
	if (i.page) out.page = i.page;
	const beside = bare(i.beside);
	if (beside) out.beside = beside;
	return out;
}

/** Words selected in a document's text, as the annotate chip quotes them; null when the selection is elsewhere or empty. */
function textSelection(item: string): Selection | null {
	const sel = window.getSelection();
	if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
	const range = sel.getRangeAt(0);
	const at = range.commonAncestorContainer;
	const el = at.nodeType === Node.ELEMENT_NODE ? (at as Element) : at.parentElement;
	if (!el?.closest('[data-src]')) return null;
	const text = quoteOf(range);
	const key = keyOf(at, '');
	return text && key ? { item, key, text } : null;
}

/**
 * Report the reader's place to the publisher while the page is open, if it serves `here`.
 *
 * Parameters
 * ----------
 * route : () => Route
 *     Which part of the viewer is on screen.
 * path : () => string
 *     The viewer's path, said for a page outside reading and Review.
 *
 * Returns
 * -------
 * () => void
 *     Stops reporting.
 */
export function startReporting(route: () => Route, path: () => string): () => void {
	let served = false;
	let last = '';
	let timer: ReturnType<typeof setTimeout> | undefined;
	const body = (): Record<string, unknown> => {
		const current = workspace.current;
		const key = current ? itemKey(current) : '';
		const other = workspace.panes.length === 2 ? workspace.active(1 - workspace.focus) : null;
		return placeOf({
			route: route(),
			path: path(),
			current,
			beside: other,
			block: key ? here.block[key] : undefined,
			selection: here.selection,
			region: here.region,
			page: current?.kind === 'work' ? workState(current).pdf.page : undefined,
			review: here.review,
			session: sessionView.selected
		});
	};
	const send = (force: boolean) => {
		if (!served) return;
		const said = JSON.stringify(body());
		if (!force && said === last) return;
		last = said;
		void write('here', JSON.parse(said));
	};
	const settle = () => {
		clearTimeout(timer);
		timer = setTimeout(() => send(false), 300);
	};
	const touched = () => {
		if (document.visibilityState === 'visible') send(true);
	};
	const selecting = () => {
		const current = workspace.current;
		if (!current) return;
		const key = itemKey(current);
		const words = textSelection(key);
		// a paper's selection is the paper's to report (`Reading`), with its page and rectangles
		if (words) here.selection = words;
		else if (here.selection && !window.getSelection()?.toString().trim()) here.selection = null;
	};
	const stop = $effect.root(() => {
		$effect(() => {
			body();
			settle();
		});
	});
	void can('here').then((yes) => {
		served = yes;
		send(true);
	});
	window.addEventListener('focus', touched);
	document.addEventListener('visibilitychange', touched);
	document.addEventListener('selectionchange', selecting);
	return () => {
		stop();
		clearTimeout(timer);
		window.removeEventListener('focus', touched);
		document.removeEventListener('visibilitychange', touched);
		document.removeEventListener('selectionchange', selecting);
	};
}
