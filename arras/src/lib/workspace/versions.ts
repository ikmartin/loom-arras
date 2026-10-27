// A document turned to another version of itself in its own tab, and compared with one (plan 0.20.6): what a draft's history menu, and a landmark's way back to its live text, do to the workspace.

import { itemKey, type Item } from './item';
import { workspace } from './store.svelte';

const doc = (id: string): Item => ({ kind: 'document', id });

/** The published id of the result at the top of a pane, which a draft and its landmarks share; none at the very top, where the version opens at its start. */
function topResult(pane: number): string | undefined {
	const body = document.querySelector<HTMLElement>(`[data-pane="${pane}"] > .body`);
	if (!body || body.scrollTop < 40) return undefined;
	const line = body.getBoundingClientRect().top + 8;
	for (const el of body.querySelectorAll<HTMLElement>('[data-pair][id]')) if (el.getBoundingClientRect().bottom > line) return el.id;
	return undefined;
}

/**
 * Show another version of the document in its tab's place, at the result the reader was at.
 *
 * Parameters
 * ----------
 * pane : number
 *     The pane the document stands in.
 * from : Item
 *     The version shown now.
 * id : str
 *     The version to show: the live draft's path or a landmark's.
 */
export function turnTo(pane: number, from: Item, id: string): void {
	if (id === from.id) return;
	const anchor = topResult(pane);
	workspace.turn(pane, itemKey(from), { ...doc(id), ...(anchor ? { anchor } : {}) });
}

/** Whether the two panes are being compared, and the two are `item` and `id`. */
export function comparingWith(item: Item, id: string): boolean {
	const c = workspace.compared;
	return workspace.comparing && !!c && c.includes(itemKey(item)) && c.includes(itemKey(doc(id)));
}

/**
 * Compare the document with another version of it, or stop when the two are already compared.
 *
 * The other opens beside, moved there when it stands in this pane, and the pane the reader chose from keeps the focus.
 *
 * Parameters
 * ----------
 * pane : number
 *     The pane the document stands in.
 * item : Item
 *     The version shown now.
 * id : str
 *     What to compare it with: a landmark, the live draft, or an agent copy or its source.
 */
export function compareWith(pane: number, item: Item, id: string): void {
	if (comparingWith(item, id)) return workspace.release();
	const partner = doc(id);
	const key = itemKey(partner);
	if (workspace.paneOf(key) === pane) workspace.move(pane, key);
	else workspace.beside(partner, pane);
	const mine = workspace.paneOf(itemKey(item));
	if (mine >= 0) workspace.focusOn(mine);
	workspace.compare();
}
