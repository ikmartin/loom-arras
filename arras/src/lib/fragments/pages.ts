// Where the compiled paper's pages ended (the `p2` setting).
//
// The point of a page view is that its numbers mean something, so the boundaries are not invented: loom publishes the
// page each numbered result fell on in the compiled PDF -- `nodes[key].numbers[master].page`, read from the `.aux` --
// and a divider goes before the first element whose page is higher than the one before it. A divider therefore falls
// exactly where a page ended in the paper the author compiled, and the number beside it is that paper's own.
//
// Two honest limits, both visible rather than papered over. The boundary can only be seen at a numbered element, so a
// run of prose between two results carries no divider however many pages it spans -- a page here is "the page this
// result is on", not a sheet of fixed height. And a master that has never been compiled publishes no numbers at all,
// so `p2` shows what `p1` shows; nothing is guessed.

import type { Manifest } from '$lib/manifest/types';

/** The page each keyed element in `root` belongs to, in document order; `null` where the publisher gives no number. */
export function pagesOf(m: Manifest | null, master: string | null, root: HTMLElement): (number | null)[] {
	const keyed = [...root.querySelectorAll<HTMLElement>('[data-key]')];
	return keyed.map((el) => {
		const key = el.dataset.key ?? '';
		const node = m?.nodes[m?.keys[key]?.node ?? key];
		const page = master ? node?.numbers?.[master]?.page : undefined;
		return typeof page === 'number' ? page : null;
	});
}

/**
 * Put a divider before each element that begins a new page of the compiled document.
 *
 * Idempotent: the dividers it made are removed before it looks again, so a re-render or a change of setting does not
 * stack them. Returns how many it drew, which is one fewer than the number of pages it could see.
 */
export function markPages(m: Manifest | null, master: string | null, root: HTMLElement): number {
	for (const old of root.querySelectorAll('.page-break')) old.remove();
	const keyed = [...root.querySelectorAll<HTMLElement>('[data-key]')];
	const pages = pagesOf(m, master, root);
	let last: number | null = null;
	let drawn = 0;
	for (let i = 0; i < keyed.length; i++) {
		const page = pages[i];
		if (page === null) continue;
		if (last !== null && page > last) {
			const rule = document.createElement('div');
			rule.className = 'page-break';
			rule.dataset.page = String(page);
			// the number a reader would cite: the page this element is on in the compiled paper
			rule.setAttribute('aria-label', `page ${page}`);
			keyed[i].before(rule);
			drawn += 1;
		}
		last = page;
	}
	return drawn;
}
