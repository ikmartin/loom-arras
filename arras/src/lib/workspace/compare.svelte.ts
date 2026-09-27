// Compare's state (book 15.2.6), shared by the rail that turns it on and steps through it and by the layer each pane draws it with. What is compared is the workspace's (`compared`, in the URL); what it found and what the publisher answered live here.

import { store } from '$lib/manifest/client.svelte';
import type { Manifest } from '$lib/manifest/types';
import { can, write } from '$lib/write';
import { plan, type Answer, type Found, type Plan, type Side } from './compare';
import { isLandmark, type Item } from './item';
import { nameOf } from './registry';
import { workspace } from './store.svelte';

/** A request, from one pane to the other, to bring a pair to a height in the viewport. */
export interface Jump {
	pair: string;
	/** The pane the request came from; the other one moves. Both move on a step. */
	from: number | null;
	/** The viewport height to bring it to; null for the pane's upper third. */
	y: number | null;
	seq: number;
}

class Comparison {
	/** Each pane's nodes, in document order, as its layer last read them. */
	found = $state.raw<[Found[], Found[]]>([[], []]);
	/** The publisher's answer for the two items, when one is serving. */
	answer = $state.raw<Answer | null>(null);
	/** The difference stepped to, or -1 before any step. */
	at = $state(-1);
	/** The pair under the pointer, lit in both panes. */
	hover = $state<string | null>(null);
	jump = $state.raw<Jump | null>(null);
	#seq = 0;
	#asked = '';

	/** What is drawn: null while not comparing. */
	plan = $derived.by((): Plan | null => {
		const m = store.manifest;
		if (!workspace.comparing || !m) return null;
		const items = [workspace.active(0), workspace.active(1)];
		if (!items[0] || !items[1]) return null;
		const sides = [sideOf(items[0], m), sideOf(items[1], m)] as [Side, Side];
		return plan(this.found, sides, (key) => m.nodes[key]?.base?.math ?? null, this.answer);
	});

	/** Forget what one comparison found, when it ends or another begins. */
	reset(): void {
		this.found = [[], []];
		this.answer = null;
		this.at = -1;
		this.hover = null;
		this.jump = null;
		this.#asked = '';
	}

	/** Ask the publisher for the pairs' renderings, once per pair of items; nothing is asked where nobody serves. */
	async ask(left: Item, right: Item): Promise<void> {
		const key = `${left.id}\u0000${right.id}\u0000${store.hash}`;
		if (this.#asked === key) return;
		this.#asked = key;
		if (!(await can('compare'))) return;
		const res = (await write('compare', { left: left.id, right: right.id })) as unknown as Answer & { ok: boolean };
		if (this.#asked === key && res.ok) this.answer = { left: res.left, right: res.right, pairs: res.pairs };
	}

	/** Step to the next (`+1`) or previous (`-1`) difference, both panes brought to it. */
	step(by: 1 | -1): void {
		const n = this.plan?.differences.length ?? 0;
		if (!n) return;
		this.at = this.at < 0 ? (by > 0 ? 0 : n - 1) : (this.at + by + n) % n;
		this.go(this.plan!.differences[this.at].pair, null, null);
	}

	/** Bring a pair to a height: in the other pane when `from` is a pane, in both when it is null. */
	go(pair: string, from: number | null, y: number | null): void {
		this.jump = { pair, from, y, seq: ++this.#seq };
	}
}

export const comparison = new Comparison();

/** What compare knows of an item it can compare. */
export function sideOf(item: Item, m: Manifest): Side {
	const landmark = item.kind === 'document' && isLandmark(m, item.id);
	const master = item.kind === 'document' ? m.masters.find((x) => x.path === item.id) : undefined;
	const canon = landmark ? m.canon?.find((c) => c.path === item.id) : undefined;
	return {
		id: item.id,
		kind: item.kind === 'node' ? 'node' : landmark ? 'landmark' : 'document',
		name: nameOf(item, m),
		step: canon?.step ? Number(canon.step) : null,
		copyOf: master?.copy_of ?? null,
		copy: master?.directory === 'drafting-ai'
	};
}

const WHAT: Partial<Record<Item['kind'], string>> = { work: 'a paper', session: 'a session', context: "a node's context" };

/**
 * Why the two front tabs cannot be compared, or '' when they can.
 *
 * Parameters
 * ----------
 * narrow : boolean
 *     Whether the workspace draws one pane at a time.
 *
 * Returns
 * -------
 * str
 *     The button's title while it is disabled.
 */
export function uncomparable(narrow: boolean): string {
	if (narrow) return 'Compare needs the two panes side by side; the window is too narrow';
	const items = [workspace.active(0), workspace.active(1)];
	if (!items[0] || !items[1]) return 'Open a second document beside this one to compare them';
	for (const i of items) {
		const what = WHAT[i!.kind];
		if (what) return `Nothing in ${what} pairs with the other pane: compare reads documents, landmarks and nodes`;
	}
	if ((items[0]!.kind === 'node') !== (items[1]!.kind === 'node')) return 'A node compares with a node, a document with a document';
	return '';
}
