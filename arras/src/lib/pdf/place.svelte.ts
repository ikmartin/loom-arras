// Where a paper opens, and keeping where the reader goes from there: what a work's paper and a project's PDF share, each naming a place in its own way.

import { onDestroy } from 'svelte';
import { keepPlace, keptPlace, type PagePlace } from './position';
import type { PdfView } from './view.svelte';

export interface Opening extends PagePlace {
	/** The stamp of the link that sent the paper here; 0 where none did. */
	seq: number;
}

export interface PaperPlace {
	/** Where the paper is to open, for `PdfDoc`'s `page`, `share` and `seq`. */
	readonly opening: Opening;
	/** Whether the reader has moved on from the link in force, for `PdfDoc`'s `lands`, the negation. */
	readonly spent: boolean;
	/** The reader moved the paper by their own hand, from `PdfDoc`'s `onmoved`. */
	moved(e: { away: boolean }): void;
}

/**
 * Open a paper where a link in force names, else where the reader last was, and keep where they go. Call it while a component is being made.
 *
 * What it was last told holds until a new link says otherwise: the place coming off the item, or a plain link revealing what is already open, is no reason to move. The stored place is read only as the paper opens, so a second window on the same file never moves this one.
 *
 * Parameters
 * ----------
 * view : () => PdfView
 *     The item's view, which outlives its renderer, so a paper made again opens where it stood.
 * link : () => { seq: number; page: number }
 *     The stamp of a link naming a place, 0 where none does, and the page it sends the paper to.
 * left : () => void, optional
 *     The reader has moved off the page the link sent them to, so the place comes off the item.
 *
 * Returns
 * -------
 * PaperPlace
 *     Where to open, and what the renderer tells it.
 */
export function paperPlace(view: () => PdfView, link: () => { seq: number; page: number }, left?: () => void): PaperPlace {
	const seq = $derived(link().seq);
	const spent = $derived(!!seq && view().spent === seq);
	let told: Opening | null = null;
	const opening = $derived.by<Opening>(() => {
		if (seq && !spent) {
			const at = link().page;
			if (!told || told.page !== at || told.share || told.seq !== seq) told = { page: at, share: 0, seq };
			return told;
		}
		if (told) return told;
		const v = view();
		if (!v.file) return { page: 1, share: 0, seq: 0 };
		return (told = { ...(v.place ?? keptPlace(v.file) ?? { page: 1, share: 0 }), seq: 0 });
	});

	// Kept once the column has been still a moment, and when the page goes: not on every frame of a scroll.
	let saving: ReturnType<typeof setTimeout> | undefined;
	function save(): void {
		clearTimeout(saving);
		const v = view();
		if (v.place && v.file) keepPlace(v.file, v.place);
	}
	$effect(() => {
		void view().place;
		clearTimeout(saving);
		saving = setTimeout(save, 250);
	});
	$effect(() => {
		window.addEventListener('pagehide', save);
		return () => window.removeEventListener('pagehide', save);
	});
	onDestroy(save);

	return {
		get opening() {
			return opening;
		},
		get spent() {
			return spent;
		},
		moved(e) {
			if (!seq) return;
			view().spent = seq;
			if (e.away) left?.();
		}
	};
}
