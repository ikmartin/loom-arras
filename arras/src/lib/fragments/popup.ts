// The one popup (review/AnnotationPopup.svelte), opened at a mark. A click on a mark opens its annotation's popup, and on the mark of the one already open closes it; one popup at a time, so opening another closes the first. It stands over the text below its mark, above it where there is no room, follows the mark as the page scrolls, and closes on ×, Escape or a click away. Hovering opens nothing.
//
// The popup lives inside the fragment, `position: fixed`, so arras writes only in its own subtree; its host is placed in window coordinates and kept clear of every edge.

import { mount, unmount, type Component } from 'svelte';
import AnnotationPopup from '$lib/review/AnnotationPopup.svelte';
import type { Manifest } from '$lib/manifest/types';

/** The gap a popup keeps from its mark and from every edge of the window. */
const INSET = 8;

export interface Popups {
	/** Open the annotation a mark stands for at that mark, or close it when it is open already. */
	toggle(trigger: HTMLElement, ids: string[]): void;
	/** Open annotation `id` at its first mark in `root`, scrolled into view; false when it has no mark there. */
	open(root: HTMLElement, id: string, scroll?: boolean): boolean;
	close(): void;
	/** The annotation open, or null. */
	current(): string | null;
	/** Stand the popup against its mark again, after the mark moved. */
	place(): void;
	destroy(): void;
}

/** The marks that stand for annotations, in document order: on words, on a block, on a label, where words were, and on a PDF page. */
export const MARKS = 'mark.annotation[data-annotation], .annotation-block[data-annotation], button.mark[data-annotation]';

/** Every mark in `root` standing for `id`. */
export function marksOf(root: ParentNode, id: string): HTMLElement[] {
	return [...root.querySelectorAll<HTMLElement>(MARKS)].filter((el) => (el.dataset.annotation ?? '').split(/\s+/).includes(id));
}

/** Of the annotations a mark lists, the one it opens: the first top-level one, a reply being shown inside its parent. */
export function leadOf(manifest: Manifest | null, ids: string[]): string {
	for (const id of ids) {
		let a = manifest?.annotations[id];
		while (a?.in_reply_to && manifest?.annotations[a.in_reply_to]) a = manifest.annotations[a.in_reply_to];
		if (a) return a.id;
	}
	return ids[0] ?? '';
}

/**
 * Put a floating box against a rectangle: below it where it fits, above it where it does not, never within `INSET` of the window's edges, and never over the toolbar of the pane it stands in.
 *
 * Parameters
 * ----------
 * host : HTMLElement
 *     The box, `position: fixed`, already in the page so its size is known.
 * r : {left, top, bottom}
 *     What it stands against, in window coordinates.
 */
export function placeAt(host: HTMLElement, r: { left: number; top: number; bottom: number }): void {
	const w = host.offsetWidth;
	const h = host.offsetHeight;
	host.style.left = Math.round(Math.min(Math.max(INSET, r.left - 8), window.innerWidth - w - INSET)) + 'px';
	// the top of what scrolls in the pane: above it is the pane's toolbar, which a popup must leave free
	const floor = Math.max(INSET, (host.parentElement?.closest('[data-pane] > .body')?.getBoundingClientRect().top ?? 0) + 6);
	const below = r.bottom + INSET;
	const above = r.top - h - INSET;
	const fits = (t: number) => t >= floor && t + h <= window.innerHeight - INSET;
	let top = fits(below) ? below : fits(above) ? above : window.innerHeight - r.bottom > r.top - floor ? below : above;
	top = Math.min(Math.max(floor, top), Math.max(floor, window.innerHeight - h - INSET));
	host.style.top = Math.round(top) + 'px';
}

/** The box round every mark of one annotation in `root`; null when none is laid out. */
function rectOf(marks: HTMLElement[]): { left: number; top: number; bottom: number } | null {
	let out: { left: number; top: number; bottom: number } | null = null;
	for (const el of marks) {
		const b = el.getBoundingClientRect();
		if (!b.width && !b.height) continue;
		out = out ? { left: Math.min(out.left, b.left), top: Math.min(out.top, b.top), bottom: Math.max(out.bottom, b.bottom) } : { left: b.left, top: b.top, bottom: b.bottom };
	}
	return out;
}

type PopupProps = { id: string; onclose: () => void; onmark: (trigger: HTMLElement, ids: string[]) => void };

/**
 * The popup controller of one fragment or one paper.
 *
 * Parameters
 * ----------
 * source : () => Manifest | null
 *     Read when a mark is clicked, so a controller that outlives a poll reads the manifest as it is now.
 * opts.host : HTMLElement, optional
 *     Where the popup is put; default the fragment the mark is in.
 * opts.onopen : (id) => void, optional
 *     Told the annotation open, or null once none is.
 *
 * Returns
 * -------
 * Popups
 */
export function popups(source: () => Manifest | null, opts: { host?: HTMLElement; onopen?: (id: string | null) => void } = {}): Popups {
	let open: { id: string; root: HTMLElement; host: HTMLElement; made: Record<string, unknown>; sized: ResizeObserver; trigger: HTMLElement; at: { left: number; top: number; bottom: number } } | null = null;

	const lit = (on: boolean) => {
		if (!open) return;
		for (const el of marksOf(open.root, open.id)) {
			el.classList.toggle('open', on);
			el.setAttribute('aria-expanded', String(on));
		}
	};

	const place = () => {
		if (!open) return;
		const marks = marksOf(open.root, open.id);
		// with no mark in the text, as one opened from a version the popup showed, it stands where it was asked for
		const r = rectOf(marks.length ? marks : [open.trigger]) ?? open.at;
		placeAt(open.host, r);
	};

	const close = () => {
		if (!open) return;
		const was = open;
		lit(false);
		open = null;
		was.sized.disconnect();
		void unmount(was.made);
		was.host.remove();
		opts.onopen?.(null);
	};

	const show = (trigger: HTMLElement, id: string, within?: HTMLElement) => {
		const b = trigger.getBoundingClientRect();
		const at = { left: b.left, top: b.top, bottom: b.bottom };
		close();
		const root = within ?? (trigger.closest('.fragment') as HTMLElement | null) ?? opts.host ?? trigger.parentElement ?? trigger;
		const host = document.createElement('aside');
		host.className = 'ann-popup-host';
		host.dataset.testid = 'popup-host';
		(opts.host ?? root).append(host);
		// a mark in the version a popup opens opens its own annotation's popup, in this text, in place of this one
		const onmark = (t: HTMLElement, ids: string[]) => {
			const next = leadOf(source(), ids);
			if (next && next !== id) show(t, next, root);
		};
		const made = mount(AnnotationPopup as unknown as Component<PopupProps>, { target: host, props: { id, onclose: close, onmark } }) as Record<string, unknown>;
		// placed by the height it has once its content is drawn, and again as it grows: a comment's mathematics typesets after it opens
		const sized = new ResizeObserver(place);
		sized.observe(host);
		open = { id, root, host, made, sized, trigger, at };
		lit(true);
		place();
		opts.onopen?.(id);
	};

	const toggle = (trigger: HTMLElement, ids: string[]) => {
		const id = leadOf(source(), ids);
		if (!id) return;
		if (open?.id === id) return close();
		show(trigger, id);
	};

	const openId = (root: HTMLElement, id: string, scroll = true): boolean => {
		const at = marksOf(root, id).find((el) => !el.classList.contains('hidden')) ?? null;
		if (!at) return false;
		if (scroll) at.scrollIntoView({ block: 'center' });
		if (open?.id !== id) show(at, id);
		return true;
	};

	const down = (e: PointerEvent) => {
		if (!open) return;
		const t = e.target as Element | null;
		// a click on a mark is the mark's to answer, on the margin's icons, the stepper or the list theirs, in the popup or a menu it opened its own, and a press on a PDF mark's grip moves the mark the popup is open on
		if (t?.closest?.('.ann-popup-host, mark.annotation, .annotation-block, .mark[data-annotation], .ann-gutter, .ann-pick, .annotate-bar, .format-menu, .side-host, [data-testid="mark-grab"], [data-testid="settings-window"]')) return;
		close();
	};
	// Escape closes the popup and nothing else: the tool in hand stays up
	const key = (e: KeyboardEvent) => {
		if (e.key !== 'Escape' || !open || e.defaultPrevented) return;
		e.preventDefault();
		close();
	};
	const again = () => place();
	document.addEventListener('pointerdown', down, true);
	document.addEventListener('keydown', key);
	window.addEventListener('scroll', again, true);
	window.addEventListener('resize', again);

	return {
		toggle,
		open: openId,
		close,
		current: () => open?.id ?? null,
		place,
		destroy() {
			close();
			document.removeEventListener('pointerdown', down, true);
			document.removeEventListener('keydown', key);
			window.removeEventListener('scroll', again, true);
			window.removeEventListener('resize', again);
		}
	};
}
