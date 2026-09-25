// What an open item keeps while another tab stands in front of it, and what its controls in the rail act on (plan 0.13.3 F4). The renderer and the controls are drawn in different places — the renderer in its pane, the controls once in the rail for whichever item is current — so the state they share lives here, keyed by the item, rather than in either.

import { getContext, setContext } from 'svelte';
import { Annotations } from '$lib/fragments/shown.svelte';
import { PdfView, type Tool } from '$lib/pdf/view.svelte';
import { itemKey, type Item } from './item';
import { workspace } from './store.svelte';

export class DocumentState {
	/** Whether every annotation is open at its mark; the fragment registers the doing. */
	notes = new Annotations();
	/** The annotating tool in hand on the document's text. */
	tool = $state<Tool>('select');
}

export class WorkState {
	/** The reader's view of the paper: the tool, the fit, the page. */
	pdf = new PdfView();
}

export class NodeState {
	notes = new Annotations();
	/** The annotating tool in hand on the node's text. */
	tool = $state<Tool>('select');
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
