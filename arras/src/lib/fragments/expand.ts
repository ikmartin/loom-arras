// Annotations shown where they are (book 15.3.1; plan 0.13 §7): a mark on the text, or on the label of a node whose annotation has no mark of its own, opens its box at the mark. The mark whose box is open carries the class `open`, which is what the wash means (theme.css).
//
// Two placements share this controller because they differ only in where the box goes. `inline` puts it in the flow beneath the block the mark sits in, so nothing is covered and the text reflows. `floating` puts it over the page at the mark, free to overlap the text and the gutter. In both, the box is the same `AnnotationBox`.
//
// **A click opens; hovering never does.** The placement we shipped as `hover` meant a box hovering *over* the text, not a box the pointer summons — and a summoned box cannot be read without holding the pointer still, nor clicked into at all, because moving toward it leaves the mark.
//
// **Many boxes.** An open box stays open until its own ×, Escape on the front-most, a click away or *hide all* closes it; clicking a box brings it in front of the others.

import { mount, unmount, type Component } from 'svelte';
import AnnotationBox from '$lib/components/AnnotationBox.svelte';
import { repliesTo } from '$lib/annotations';
import { inert } from './mount';
import { travel } from '$lib/travel/travel';
import type { Annotation, Manifest } from '$lib/manifest/types';

/** The gap a box keeps from every edge of the window, applied after placement so one near an edge slides rather than clipping. */
const INSET = 4;

export interface InlineComments {
	/** Open the comments `ids` at `trigger`, or close them when they are already open there. */
	toggle(trigger: HTMLElement, ids: string[]): void;
	/** Re-read every open box from the current manifest, in place. A write lands in the log and comes back on the next poll; the box that fired it must not be the one surface still showing the old state. */
	refresh(): void;
	/** Open every annotation in `root` at its own mark. A state, not an action: what materialises later opens too. */
	expandAll(root: HTMLElement): void;
	/** Close everything open, wherever it is. The escape hatch that clicking outside no longer provides. */
	hideAll(): void;
	close(): void;
	/** Whether expand-all is on, so a fragment re-wired or a page rendered later can honour it. */
	expanded(): boolean;
	/** The annotations the front-most box shows, or null; a re-wire reads it to open the same ones again. */
	current(): string[] | null;
	destroy(): void;
}

type Box = Component<{ annotation: Annotation; replies: Annotation[]; onclose?: () => void }>;

/** The top-level annotations among `ids`, settled ones included; a reply is shown inside its parent, so a mark listing both opens the parent once. A discarded one is a settled one (15.3.1): its mark is inert until the settled control draws it, and then its box opens like a resolved one's. */
export function leadComments(manifest: Manifest, ids: string[]): Annotation[] {
	const out: Annotation[] = [];
	const seen = new Set<string>();
	for (const id of ids) {
		let a = manifest.annotations[id];
		while (a?.in_reply_to && manifest.annotations[a.in_reply_to]) a = manifest.annotations[a.in_reply_to];
		if (a && !seen.has(a.id)) {
			seen.add(a.id);
			out.push(a);
		}
	}
	return out;
}

/** Every mark in `root` that stands for an annotation, in document order; with `drawn`, only those a reader can see, since a settled mark with the settled control off, or one the session filter hides, is nothing to open at once. */
function triggers(root: HTMLElement, drawn = false): HTMLElement[] {
	const all = [...root.querySelectorAll<HTMLElement>('mark.annotation[data-annotation], .annotation-block[data-annotation], button.mark[data-annotation]')];
	return drawn ? all.filter((el) => !inert(el)) : all;
}

/** The ids a trigger stands for. */
function idsOf(el: HTMLElement): string[] {
	return (el.dataset.annotation ?? '').split(/\s+/).filter(Boolean);
}

/** The mark in `root` that stands for any of `ids`, drawn or not, so annotations open before a re-wire can be opened again after it: a box whose annotation was just discarded from it stays open to offer the undo. */
export function triggerFor(root: HTMLElement, ids: string[]): HTMLElement | null {
	for (const el of triggers(root)) {
		const has = idsOf(el);
		if (ids.some((i) => has.includes(i))) return el;
	}
	return null;
}

interface Opened {
	trigger: HTMLElement;
	host: HTMLElement;
	made: Record<string, unknown>[];
	ids: string[];
	/** Whether this box stands over the text; a box opened by `expandAll` stands in the flow whatever the placement. */
	floats: boolean;
}

export function inlineComments(
	source: Manifest | (() => Manifest | null),
	floating = false,
	opts: { host?: HTMLElement } = {}
): InlineComments {
	let boxes: Opened[] = [];
	let all = false;
	// A getter, so a controller that outlives one manifest poll reads the current one at the moment a box opens; a
	// fragment hands the object it was wired with, and re-wires when that changes.
	const manifestNow = (): Manifest | null => (typeof source === 'function' ? source() : source);

	/**
	 * Put a floating box at the mark: below it when there is room, above it when there is not, and never within `INSET`
	 * of any edge.
	 *
	 * Viewport coordinates and `position: fixed`, so the box does not depend on which ancestor happens to be positioned,
	 * and it lives inside the fragment rather than in the page's root -- arras is a guest and writes only in its own
	 * subtree.
	 */
	const place = (host: HTMLElement, trigger: HTMLElement) => {
		const r = trigger.getBoundingClientRect();
		const width = Math.min(420, window.innerWidth - 2 * INSET);
		host.style.width = width + 'px';
		host.style.left = Math.min(Math.max(INSET, r.left), window.innerWidth - width - INSET) + 'px';
		host.style.top = r.bottom + 6 + 'px';
		// measured once it is in the page, because its height depends on the comment
		const h = host.offsetHeight;
		if (r.bottom + h + INSET > window.innerHeight && r.top - h - 6 > INSET) host.style.top = r.top - h - 6 + 'px';
		const top = parseFloat(host.style.top);
		host.style.top = Math.min(Math.max(INSET, top), Math.max(INSET, window.innerHeight - h - INSET)) + 'px';
	};

	const front = (box: Opened) => {
		for (const b of boxes) b.host.classList.toggle('behind', b !== box);
		boxes = [...boxes.filter((b) => b !== box), box];
	};

	const shut = (box: Opened) => {
		for (const made of box.made) void unmount(made);
		box.host.remove();
		box.trigger.classList.remove('open');
		box.trigger.setAttribute('aria-expanded', 'false');
		boxes = boxes.filter((b) => b !== box);
	};

	const hideAll = () => {
		all = false;
		for (const b of [...boxes]) shut(b);
	};

	const openAt = (trigger: HTMLElement, ids: string[], floats = floating): Opened | null => {
		const manifest = manifestNow();
		if (!manifest) return null;
		const lead = leadComments(manifest, ids);
		if (!lead.length) return null;
		const host = document.createElement('aside');
		host.className = floats ? 'comment-slot expanded floating' : 'comment-slot expanded';
		host.dataset.testid = 'comment-expanded';
		if (floats) {
			// into the host a page gave, else the fragment: a mark on a PDF page sits in an overlay that takes no
			// pointer events, which is no place for a box that must be clicked into
			(opts.host ?? trigger.closest('.fragment') ?? trigger.parentElement ?? trigger).append(host);
		} else {
			// beneath the paragraph, item or display the mark sits in, so the text keeps its line; a mark on a label opens under the label
			const block = trigger.classList.contains('annotation-label')
				? trigger.closest<HTMLElement>('p.env-label, summary.env-label, h1, h2, h3, h4, h5, h6')
				: trigger.closest<HTMLElement>('p, li, .math.display, .annotation-block, summary');
			(block ?? trigger).after(host);
		}
		const box: Opened = { trigger, host, made: [], ids: lead.map((a) => a.id), floats };
		box.made = fill(host, box.ids, () => shut(box));
		trigger.classList.add('open');
		trigger.setAttribute('aria-expanded', 'true');
		boxes = [...boxes, box];
		host.addEventListener('pointerdown', () => front(box));
		if (floats) place(host, trigger);
		front(box);
		return box;
	};

	/** Mount one card per id into `host`, from the manifest as it stands. Returns what was mounted, to unmount later.
	 *
	 * The host's one × is the first card's, on its title line; `close` shuts the whole host. */
	function fill(host: HTMLElement, ids: string[], close: () => void): Record<string, unknown>[] {
		const manifest = manifestNow();
		if (!manifest) return [];
		return leadComments(manifest, ids).map(
			(a, i) =>
				mount(AnnotationBox as unknown as Box, {
					target: host,
					props: { annotation: a, replies: repliesTo(manifest, a.id), onclose: i === 0 ? close : undefined }
				}) as Record<string, unknown>
		);
	}

	/**
	 * Re-read every open box from the manifest as it now stands, keeping the box where it is.
	 *
	 * A card is mounted with the annotation it had when it opened, and nothing updated it: resolving from a box left
	 * the box saying `open` with the same verbs, so a reader clicked again and the log took two `resolved` events for
	 * one annotation. Found by the reading study, 2026-09-21. The host and its placement are kept, because the box is
	 * where the reader put it and a write is not a reason to move it.
	 */
	const refresh = () => {
		for (const box of boxes) {
			for (const made of box.made) void unmount(made);
			box.made = fill(box.host, box.ids, () => shut(box));
		}
	};

	const toggle = (trigger: HTMLElement, ids: string[]) => {
		// **One box per annotation, not per mark.** A note over four lines of a paper draws four marks, and each was a trigger of its own, so clicking a second line of the same highlight opened a second box a few pixels off the first -- which read as one box with a doubled border. A box already showing any of these ids is the box.
		const already = boxes.find((b) => b.trigger === trigger || b.ids.some((id) => ids.includes(id)));
		if (already) {
			// a backgrounded box is brought forward rather than shut: the reader is reaching for it, not dismissing it
			if (already.host.classList.contains('behind')) front(already);
			else shut(already);
			return;
		}
		// a box the page itself mounted in the flow (comparison mode's cards, `DocumentItem`) is the annotation's one box: the mark goes to it rather than opening a second
		const standing = ids.map((id) => trigger.closest('.fragment')?.querySelector<HTMLElement>(`aside.comment-slot.inline [id="ann-${CSS.escape(id)}"]`)).find(Boolean);
		if (standing) {
			travel(standing, trigger);
			return;
		}
		openAt(trigger, ids);
	};

	// **Every box at once stands in the flow.** Opened together over the text, floating boxes stood on one another and on the words until neither could be read; in the flow each stands under its own paragraph or label, and the text makes room. A box already floating is closed and opened again in the flow. A single mark's click keeps the reader's placement.
	const expandAll = (root: HTMLElement) => {
		all = true;
		for (const t of triggers(root, true)) {
			const open = boxes.find((b) => b.trigger === t);
			if (open && !open.floats) continue;
			if (open) shut(open);
			openAt(t, idsOf(t), false);
		}
		// nothing is in front when everything is open: the reader's eye, not the z-order, is what picks one out
		for (const b of boxes) b.host.classList.remove('behind');
	};

	const down = (e: PointerEvent) => {
		if (!boxes.length) return;
		const t = e.target as Element | null;
		if (t?.closest?.('.comment-slot.expanded, mark.annotation, .annotation-block, .mark[data-annotation]')) return;
		// **A click away closes.** DR-202 backgrounded instead, so that nothing a reader opened would disappear because they looked elsewhere. What that leaves on the page is a clipped, faded stub of a box -- which reads as a ghost when it is alone and as a doubled border when another box is in front of it. Closing is what clicking away means everywhere else, and the mark is still there to open it again.
		hideAll();
	};
	const key = (e: KeyboardEvent) => {
		if (e.key !== 'Escape' || !boxes.length) return;
		// a reply, restatement or reason being written in the front box is what Escape closes first; its own row does that
		const front = boxes[boxes.length - 1];
		if (front.host.querySelector('.compose')) return;
		shut(front);
	};
	// A floating box is placed against the window, so it follows its mark rather than being abandoned by it. It used to
	// close on scroll, which was right only while the pointer was what opened it.
	const again = () => {
		for (const b of boxes) if (b.floats) place(b.host, b.trigger);
	};
	document.addEventListener('pointerdown', down, true);
	document.addEventListener('keydown', key);
	window.addEventListener('scroll', again, true);
	window.addEventListener('resize', again);

	return {
		toggle,
		refresh,
		expandAll,
		hideAll,
		close: hideAll,
		expanded: () => all,
		current: () => boxes[boxes.length - 1]?.ids ?? null,
		destroy() {
			hideAll();
			document.removeEventListener('pointerdown', down, true);
			document.removeEventListener('keydown', key);
			window.removeEventListener('scroll', again, true);
			window.removeEventListener('resize', again);
		}
	};
}
