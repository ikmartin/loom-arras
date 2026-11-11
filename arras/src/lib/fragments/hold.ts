// Keeping the reader's place while a fragment changes above them. The browser's scroll anchoring does it for a block that changes size in place, but not for a block put in while the read view skips what is off screen (`content-visibility: auto`, theme.css): the new block starts at its placeholder size, the old one had its real size, and the browser leaves the scroll offset as it was, carrying the text the reader was on away. So the place is pinned by hand, as the pane's own restore does on a return.

/** Something that keeps the reader's place until it is let go. */
export interface Hold {
	/** Put the text that was at the scroller's top back where it was. */
	again(): void;
	/** Stop holding once `after` ms have passed, in which any change of size is still answered; 0 lets go now. */
	release(after?: number): void;
}

/**
 * The element that scrolls `el`.
 *
 * Parameters
 * ----------
 * el : Element
 *     Anything drawn in a scrolling view.
 *
 * Returns
 * -------
 * HTMLElement
 *     Its nearest ancestor that scrolls on the block axis, else the page's scrolling element.
 */
export function scrollerOf(el: Element): HTMLElement {
	for (let p = el.parentElement; p; p = p.parentElement) {
		const y = getComputedStyle(p).overflowY;
		if (y === 'auto' || y === 'scroll') return p;
	}
	return document.scrollingElement as HTMLElement;
}

/** Where `scroller`'s visible part begins, in viewport coordinates. */
const topOf = (scroller: HTMLElement): number => (scroller === document.scrollingElement ? 0 : scroller.getBoundingClientRect().top);

/** The blocks of `root` in document order, the reader's boxes and margin left out: a block's top is never above the one before it. */
const blocks = (root: HTMLElement): HTMLElement[] => [...root.querySelectorAll<HTMLElement>('[data-src]')].filter((e) => !e.closest('aside.comment-slot, .node-margin'));

/** The last block that begins at or above `line`: the deepest block the scroller's top falls in, or the one just above it. Bisected, since there are thousands. */
function blockAt(list: HTMLElement[], line: number): HTMLElement | null {
	let lo = 0;
	let hi = list.length - 1;
	let found = -1;
	while (lo <= hi) {
		const mid = (lo + hi) >> 1;
		if (list[mid].getBoundingClientRect().top <= line) {
			found = mid;
			lo = mid + 1;
		} else hi = mid - 1;
	}
	return found < 0 ? (list[0] ?? null) : list[found];
}

/** A block's file and where it begins, from its `data-src` (`FILE:START:END`). */
function placeOf(src: string): [string, number] {
	const m = /^(.*):(\d+):\d+$/.exec(src);
	return m ? [m[1], Number(m[2])] : ['', -1];
}

/** What a reader does to take the scroll over, which ends any holding of their place. */
export const INPUT = ['wheel', 'pointerdown', 'keydown', 'touchstart'] as const;

/**
 * Hold the reader's place in `root` while it changes: the block at the top of its scroller, and how far below the top it stands.
 *
 * The block is found again by its source place when it is itself replaced, or the whole fragment drawn again: the same place, else the nearest block of its file that begins before it. While held, every change of the fragment's size puts it back; the reader scrolling, or the fragment being sent somewhere (`arrive`), lets go at once.
 *
 * Parameters
 * ----------
 * root : HTMLElement
 *     The fragment, as drawn now.
 *
 * Returns
 * -------
 * Hold
 *     `again` to put the place back by hand after a change made in the same task; `release` to stop.
 */
export function hold(root: HTMLElement): Hold {
	const scroller = scrollerOf(root);
	const top = topOf(scroller);
	const list = blocks(root);
	const anchor = blockAt(list, top + 1);
	const src = anchor?.dataset.src ?? '';
	const rank = anchor ? list.filter((e) => e.dataset.src === src).indexOf(anchor) : -1;
	const below = anchor ? anchor.getBoundingClientRect().top - top : 0;
	let held = anchor;
	let timer: ReturnType<typeof setTimeout> | undefined;
	let done = false;

	/** The block held, found again once it is replaced: by its source place and rank, else as the last block of its file that begins at or before it, an edit having moved or taken it. */
	function find(): HTMLElement | null {
		const same = [...root.querySelectorAll<HTMLElement>(`[data-src="${CSS.escape(src)}"]`)];
		if (same.length) return same[Math.min(rank, same.length - 1)];
		const [file, start] = placeOf(src);
		let best: HTMLElement | null = null;
		let at = -1;
		for (const e of blocks(root)) {
			const [f, s] = placeOf(e.dataset.src ?? '');
			if (f === file && s <= start && s >= at) [best, at] = [e, s];
		}
		return best;
	}

	function again(): void {
		if (done || !anchor) return;
		if (!held?.isConnected) held = find();
		if (!held) return;
		const by = held.getBoundingClientRect().top - topOf(scroller) - below;
		if (Math.abs(by) >= 1) scroller.scrollTop += by;
	}

	const watch = new ResizeObserver(again);
	watch.observe(root);
	const stop = (): void => {
		if (done) return;
		done = true;
		clearTimeout(timer);
		watch.disconnect();
		for (const e of INPUT) scroller.removeEventListener(e, stop);
		scroller.removeEventListener('arrive', stop);
	};
	for (const e of INPUT) scroller.addEventListener(e, stop, { passive: true });
	scroller.addEventListener('arrive', stop);

	return {
		again,
		release(after = 0) {
			clearTimeout(timer);
			if (after > 0) timer = setTimeout(stop, after);
			else stop();
		}
	};
}
