// The one place reading mode puts things (plan 0.13.3 W1–W11): at most two panes of equal rank, each a list of open items with one active, and a focus. `current`, the focused pane's active item, is **the** definition of "the current document": the panel's contents, the rail's control cluster and the preview's `open here` all read it, and nothing computes it independently.
//
// Pure state: it renders nothing and touches no DOM, so its rules are unit-tested without a browser. The URL is derived from it (`canonical`) and read into it (`apply`); only the two active items and their places travel in the URL, and the rest of each pane's list is this session's alone.

import { itemFromPath, itemKey, pathFor, type Documents, type Item } from './item';

export interface Pane {
	items: Item[];
	/** The active item's key. */
	active: string;
}

export class Workspace {
	/** One or two panes; none before anything is read. */
	panes = $state<Pane[]>([]);
	/** The pane interaction last touched (W10). */
	focus = $state(0);
	/** Whether reading mode is on screen; set by the layout. Outside it the panes are kept but nothing is drawn, so nothing should open into them. */
	onScreen = $state(false);
	/** Per-item state a renderer keeps across being hidden behind another tab: a work's view of its pages, a document's open annotations, a scroll offset. */
	#state = new Map<string, object>();
	#seq = 0;

	/** The focused pane's active item: the current document, whatever kind it is. */
	get current(): Item | null {
		return this.active(this.focus);
	}

	/** A pane's active item, or null. */
	active(pane: number): Item | null {
		const p = this.panes[pane];
		return p?.items.find((i) => itemKey(i) === p.active) ?? null;
	}

	/** Which pane holds an item, or -1. */
	paneOf(key: string): number {
		return this.panes.findIndex((p) => p.items.some((i) => itemKey(i) === key));
	}

	/** The state kept for an item, made on first asking. Dropped when the item's last tab closes. */
	stateOf<T extends object>(key: string, make: () => T): T {
		let s = this.#state.get(key);
		if (!s) this.#state.set(key, (s = make()));
		return s as T;
	}

	/** Take focus (W10). */
	focusOn(pane: number): void {
		if (pane >= 0 && pane < this.panes.length && this.focus !== pane) this.focus = pane;
	}

	/**
	 * Open an item in the focused pane: a choice of what to read (S4), which never splits.
	 *
	 * An item already open in either pane is revealed where it is instead (W8).
	 */
	here(item: Item): void {
		this.openIn(item, this.panes.length ? this.focus : 0);
	}

	/**
	 * Open an item in the pane beside `from`: following a connection (W7), so both ends stay on screen. With one pane open, the second is made.
	 *
	 * Parameters
	 * ----------
	 * item : Item
	 *     What to open, at its place.
	 * from : number
	 *     The pane the link was in.
	 */
	beside(item: Item, from: number): void {
		if (this.paneOf(itemKey(item)) >= 0 || this.panes.length === 2) {
			this.openIn(item, this.panes.length === 2 ? 1 - from : from);
			return;
		}
		if (!this.panes.length) {
			this.openIn(item, 0);
			return;
		}
		const pane: Pane = { items: [this.#stamp(item)], active: itemKey(item) };
		this.panes = [this.panes[0], pane];
		this.focus = 1;
	}

	/** Open in a given pane, or reveal where it already is. */
	openIn(item: Item, pane: number): void {
		const key = itemKey(item);
		const at = this.paneOf(key);
		if (at >= 0) {
			this.#replace(at, key, item);
			this.panes[at].active = key;
			this.focus = at;
			return;
		}
		if (!this.panes.length) {
			this.panes = [{ items: [this.#stamp(item)], active: key }];
			this.focus = 0;
			return;
		}
		const p = this.panes[Math.min(pane, this.panes.length - 1)];
		p.items.push(this.#stamp(item));
		p.active = key;
		this.focus = this.panes.indexOf(p);
	}

	/** Make a tab the active one of its pane, and focus the pane. */
	activate(pane: number, key: string): void {
		const p = this.panes[pane];
		if (!p || !p.items.some((i) => itemKey(i) === key)) return;
		p.active = key;
		this.focus = pane;
	}

	/** Record where an open item now is — its anchor, place or view — without revealing it: the reader moved within it. */
	update(key: string, patch: Partial<Pick<Item, 'view' | 'anchor' | 'place' | 'params'>>): void {
		for (const p of this.panes) {
			const i = p.items.findIndex((x) => itemKey(x) === key);
			if (i >= 0) p.items[i] = { ...p.items[i], ...patch, seq: p.items[i].seq };
		}
	}

	/**
	 * Move a tab to the other pane, and focus it there (W6). With one pane, the other is made; a pane left empty closes.
	 */
	move(pane: number, key: string): void {
		const p = this.panes[pane];
		const item = p?.items.find((i) => itemKey(i) === key);
		if (!item) return;
		if (this.panes.length === 1 && p.items.length === 1) return; // it would empty one pane to refill the other with the same thing (W5)
		const dest = this.panes.length === 2 ? this.panes[1 - pane] : null;
		this.#drop(pane, key);
		if (!dest) {
			// the source pane kept its other tabs; the moved one makes the second pane
			this.panes = [this.panes[0], { items: [item], active: key }];
			this.focus = 1;
			return;
		}
		dest.items.push(item);
		dest.active = key;
		this.focus = this.panes.indexOf(dest);
	}

	/** Close a tab. Its neighbour becomes active; a pane left empty closes, and the other takes the width. */
	close(pane: number, key: string): void {
		if (!this.panes[pane]) return;
		this.#drop(pane, key);
		if (this.paneOf(key) < 0) this.#state.delete(key);
	}

	/**
	 * The URL that reproduces what is on screen: pane 0's active item as the path, pane 1's as `?beside`.
	 *
	 * Returns
	 * -------
	 * str
	 *     Path, query and hash, with the app's base; '' when nothing is open.
	 */
	canonical(m: Documents | null): string {
		const left = this.active(0);
		if (!left) return '';
		const url = new URL(pathFor(m, left), 'http://x');
		const right = this.active(1);
		if (right) url.searchParams.set('beside', pathFor(m, right));
		return url.pathname + url.search + url.hash;
	}

	/**
	 * Take in a URL the workspace did not write: a load, a link from outside reading mode, the palette.
	 *
	 * An empty workspace becomes exactly what the URL names. Otherwise the path's item opens in the focused pane (a choice of what to read) and `?beside`'s, if any, in the other.
	 */
	apply(m: Documents | null, href: string): void {
		const url = new URL(href, 'http://x');
		const besideRaw = url.searchParams.get('beside');
		url.searchParams.delete('beside');
		const main = itemFromPath(m, url.pathname + url.search + url.hash);
		const other = besideRaw ? itemFromPath(m, besideRaw) : null;
		if (!this.panes.length) {
			if (!main) return;
			this.panes = [{ items: [this.#stamp(main)], active: itemKey(main) }];
			this.focus = 0;
			if (other && itemKey(other) !== itemKey(main)) this.beside(other, 0);
			this.focus = 0;
			return;
		}
		if (main) this.here(main);
		if (other) {
			const at = this.focus;
			this.beside(other, at);
			this.focus = at;
		}
	}

	/** Forget everything: for tests, and nothing else. */
	reset(): void {
		this.panes = [];
		this.focus = 0;
		this.#state.clear();
	}

	#stamp(item: Item): Item {
		return { ...item, seq: ++this.#seq };
	}

	/** Put the new place of an open item in, with a fresh stamp so its renderer goes there even when the place is unchanged. */
	#replace(pane: number, key: string, item: Item): void {
		const p = this.panes[pane];
		const i = p.items.findIndex((x) => itemKey(x) === key);
		const was = p.items[i];
		// the new place replaces the old rather than merging with it: revealing without a place keeps the reader where they were
		p.items[i] = this.#stamp({ ...item, view: item.view ?? was.view });
	}

	#drop(pane: number, key: string): void {
		const p = this.panes[pane];
		const i = p.items.findIndex((x) => itemKey(x) === key);
		if (i < 0) return;
		p.items.splice(i, 1);
		if (!p.items.length) {
			this.panes = this.panes.filter((_, n) => n !== pane);
			this.focus = Math.min(this.focus > pane ? this.focus - 1 : this.focus, Math.max(0, this.panes.length - 1));
			return;
		}
		if (p.active === key) p.active = itemKey(p.items[Math.min(i, p.items.length - 1)]);
	}
}

export const workspace = new Workspace();
