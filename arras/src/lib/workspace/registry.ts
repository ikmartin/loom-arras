// One entry per kind of item (plan 0.13.3): how its tab is named, what renders it, what it acts with in the rail, and which internal views it has. Nothing else in the viewer knows what kinds exist.

import type { Component } from 'svelte';
import type { Manifest } from '$lib/manifest/types';
import { masterStem } from '$lib/nav';
import { titleOf } from '$lib/sessions/sessions.svelte';
import { isLandmark, type Item, type ItemKind } from './item';
import { shortLocator } from './names';
import { workViews, type View } from './views';
import DocumentItem from './items/DocumentItem.svelte';
import DocumentControls from './items/DocumentControls.svelte';
import WorkItem from './items/WorkItem.svelte';
import WorkControls from './items/WorkControls.svelte';
import NodeItem from './items/NodeItem.svelte';
import NodeControls from './items/NodeControls.svelte';
import ContextItem from './items/ContextItem.svelte';
import SessionItem from './items/SessionItem.svelte';
import NodePreview from './items/NodePreview.svelte';
import WorkPreview from './items/WorkPreview.svelte';
import { fetchFragment } from '$lib/fragments/fetch';
import { store } from '$lib/manifest/client.svelte';

export interface Kind {
	/** What the tab says: the thing's identity, short enough for a fixed 148px tab. */
	tab(item: Item, m: Manifest): string;
	/** A glyph drawn before the tab's name, for a kind that is *about* the item its name names; `says` precedes the name wherever it is read as text. */
	marker?: { icon: string; says: string };
	renderer: Component<{ item: Item }>;
	/** Drawn in the rail's cluster for the current item; `name` is the tab's, for the controls' accessible names. */
	controls?: Component<{ item: Item; name: string }>;
	/** Several readings of one thing, switched in the cluster. */
	views?(item: Item, m: Manifest): View[];
	/** The item rendered small, for a hover card (H1–H7); a kind without one previews nothing rather than something made up (P3). `onresize` asks the card to place itself again once the content has its size. */
	preview?: Component<{ item: Item; onresize: () => void }>;
	/** The small render is its own frame and runs to the card's edge, as a page does (H3). */
	bleeds?: boolean;
	/** Start fetching what the small render needs while the pointer waits out the card's delay. */
	prefetch?(item: Item, m: Manifest): void;
}

/** A document's name as its author types it: the file, and a landmark's step, which is its identity rather than a note about it (D1). */
function documentTab(item: Item, m: Manifest): string {
	const file = item.id.split('/').pop() ?? item.id;
	if (!isLandmark(m, item.id)) return file;
	const c = m.canon?.find((x) => x.path === item.id);
	return c?.step ? `${masterStem(file)} @${Number(c.step)}` : file;
}

/** A node by how a reader refers to it: its taxon and number where the default document numbers it; a result read off a cited work as that work's citekey and the result's short name; else its id. */
function nodeTab(id: string, m: Manifest): string {
	const n = m.nodes[id];
	if (!n) return id;
	if (n.digest && n.locator) return `${n.digest} · ${shortLocator(n.locator)}`;
	const main = m.masters.find((x) => x.default)?.path;
	const number = main ? n.numbers[main]?.number : undefined;
	return number ? `${n.taxon[0].toUpperCase()}${n.taxon.slice(1)} ${number}` : id;
}

export const kinds: Record<ItemKind, Kind> = {
	document: { tab: documentTab, renderer: DocumentItem, controls: DocumentControls },
	work: {
		// the citekey, and the result it is at when there is one: `Arden24 · Prop 2.1` says which paper and where
		tab: (item, m) => {
			const r = item.place?.result;
			const at = r ? m.nodes[r] : undefined;
			return at?.locator ? `${item.id} · ${shortLocator(at.locator)}` : item.id;
		},
		renderer: WorkItem,
		controls: WorkControls,
		preview: WorkPreview,
		bleeds: true,
		views: (item, m) => workViews(m, item.id)
	},
	node: {
		tab: (item, m) => nodeTab(item.id, m),
		renderer: NodeItem,
		controls: NodeControls,
		preview: NodePreview,
		prefetch: (item, m) => {
			const n = m.nodes[item.id];
			if (n && n.kind !== 'section') void fetchFragment(n.fragment, store.hash).catch(() => '');
		}
	},
	context: { tab: (item, m) => nodeTab(item.id, m), marker: { icon: 'graph', says: 'context of' }, renderer: ContextItem },
	session: {
		tab: (item, m) => {
			const s = (m.sessions ?? []).find((x) => x.id === item.id);
			return s ? titleOf(s) : (m.threads[item.id]?.title ?? item.id);
		},
		renderer: SessionItem,
		views: () => [
			{ id: 'chat', label: 'Chat' },
			{ id: 'did', label: 'What it did' }
		]
	}
};

/** The tab label of an item. */
export function tabOf(item: Item, m: Manifest): string {
	return kinds[item.kind].tab(item, m);
}

/** An item's name as text, where no glyph can be drawn: the tab's label, after what its marker says (`context of Theorem 3.1`). */
export function nameOf(item: Item, m: Manifest): string {
	const k = kinds[item.kind];
	return k.marker ? `${k.marker.says} ${k.tab(item, m)}` : k.tab(item, m);
}
