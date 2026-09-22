// The reader's view of a document: which tool is in hand, how large the page is drawn, and where in it they are.
//
// It is a separate object because the controls and the renderer need not be in the same place. `PdfDoc` draws its own
// toolbar when nothing else claims one, and a page with a rail of its own creates a view, hands it to both, and puts
// the controls on one line with everything else it offers.

import { prefs } from '$lib/prefs.svelte';

export type Tool = 'select' | 'box';

export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 5;

export class PdfView {
	tool = $state<Tool>('select');
	/** Whether the page is matched to the column, which then survives a resize. */
	fitWidth = $state(false);
	/** The page the reader is on and how many there are; the renderer writes both. */
	page = $state(1);
	count = $state(0);
	/** The scale actually drawn, which is the fitted one while `fitWidth` holds; the renderer writes it. */
	scale = $state(1);

	/** A request to scroll somewhere, carrying a nonce so that asking for the page already shown still scrolls to it. */
	jump = $state<{ page: number; n: number } | null>(null);

	/** Send the reader to a page. Out-of-range asks are clamped rather than refused: a reader who types 99 of 12 means the end. */
	goTo(page: number): void {
		const n = (this.jump?.n ?? 0) + 1;
		this.jump = { page: Math.max(1, this.count ? Math.min(page, this.count) : page), n };
	}

	/** Set the zoom. An instruction about size leaves the fitted mode rather than fighting it. */
	zoomTo(v: number): void {
		this.fitWidth = false;
		prefs.zoom = { ...prefs.zoom, pdf: Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(v * 100) / 100)) };
	}
}
