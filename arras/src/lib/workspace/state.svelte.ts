// What an open item keeps while another tab stands in front of it, and what its controls act on (plan 0.13.3 F4). The renderer and the controls are drawn apart — the renderer in the pane's body, the controls by the pane, and only while it is focused — so the state they share lives here, keyed by the item, rather than in either.

import { getContext, setContext } from 'svelte';
import { Annotating } from '$lib/review/annotating.svelte';
import { PdfView } from '$lib/pdf/view.svelte';
import type { MarkDesk } from '$lib/pdf/desk.svelte';
import { itemKey, type Item } from './item';
import { workspace } from './store.svelte';

/** Which request to go somewhere an item's fragment last answered (Fragment's `arrival`): kept with the item, so a fragment made again -- the reader back from Review, a tab brought forward -- does not answer it twice. */
export interface Arrival {
	at: string | null;
}

export class DocumentState {
	/** Its annotating: the tool in hand, its annotations in reading order, the one open, the side list; the fragment registers the doing. */
	notes = new Annotating();
	arrival: Arrival = { at: null };
}

export class WorkState {
	/** The reader's view of the paper: the tool, the fit, the page. */
	pdf = new PdfView();
	/** Its annotating, as a document's: Annotate and Comment, its annotations in reading order, the one open, the side list. */
	notes = new Annotating();
	/** The paper's marks and file acts, which its renderer makes and the toolbar's `PDF ▾` acts through; null until the paper is drawn. */
	desk = $state.raw<MarkDesk | null>(null);
}

export class FileState {
	/** The reader's view of a PDF among the project's files: the tool, the fit, the page. */
	pdf = new PdfView();
	notes = new Annotating();
	desk = $state.raw<MarkDesk | null>(null);
}

export class NodeState {
	notes = new Annotating();
	arrival: Arrival = { at: null };
	/** Whether the node is read as its source rather than rendered. */
	verbatim = $state(false);
	/** The node's source, once fetched; null while unknown or when the corpus publishes none, and then there is no `source` control. */
	source = $state<string | null>(null);
}

/** The state of an open item, made on first asking. */
export function documentState(item: Item): DocumentState {
	return workspace.stateOf(itemKey(item), () => new DocumentState());
}
export function workState(item: Item): WorkState {
	return workspace.stateOf(itemKey(item), () => new WorkState());
}
export function fileState(item: Item): FileState {
	return workspace.stateOf(itemKey(item), () => new FileState());
}
export function nodeState(item: Item): NodeState {
	return workspace.stateOf(itemKey(item), () => new NodeState());
}

/** What a renderer knows of the pane it stands in: which one, and the element that scrolls. */
export interface PaneContext {
	index: number;
	/** The pane's scrolling body, for a renderer that follows the reader's position through it. */
	scroller: () => HTMLElement | null;
	/** The pane itself, which does not scroll: a floating panel is placed against it. */
	frame: () => HTMLElement | null;
}

const PANE = Symbol('pane');

export function setPane(ctx: PaneContext): void {
	setContext(PANE, ctx);
}

export function getPane(): PaneContext {
	return getContext<PaneContext>(PANE) ?? { index: 0, scroller: () => null, frame: () => null };
}

/** The pane a renderer stands in, or null outside every pane (a hover card, the Review page). */
export function paneOf(): PaneContext | null {
	return getContext<PaneContext>(PANE) ?? null;
}
