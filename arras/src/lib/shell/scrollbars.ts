// Scrollbars shown only while something scrolls (book 15.7): whatever is scrolling carries `is-scrolling`, and the stylesheet draws its bar only then.

/** How long a bar stays after the last movement: long enough to find it and take hold of it. */
const LINGER = 900;

/**
 * Mark each scrolling element while it scrolls, on the whole page.
 *
 * Returns
 * -------
 * () => void
 *     Removes the listener.
 */
export function revealWhileScrolling(): () => void {
	const timers = new WeakMap<Element, ReturnType<typeof setTimeout>>();
	const onScroll = (e: Event): void => {
		// arras scrolls its panels and panes, never the page; and a host's own elements are the host's to mark, not arras's
		const el = e.target instanceof Element ? e.target : null;
		if (!el?.closest('.arras')) return;
		el.classList.add('is-scrolling');
		clearTimeout(timers.get(el));
		timers.set(
			el,
			setTimeout(() => el.classList.remove('is-scrolling'), LINGER)
		);
	};
	// scroll does not bubble, so it is caught on the way down
	document.addEventListener('scroll', onScroll, { capture: true, passive: true });
	return () => document.removeEventListener('scroll', onScroll, { capture: true });
}
