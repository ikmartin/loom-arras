// Travel between the panes (plan 0.13 §7): from a mark in the content to the annotation it belongs to, and back.
//
// **A brief scroll, then a flash.** Not a jump, which loses the reader's place, and not a long animation, which costs
// time they did not ask to spend. The flash is on the destination, so the eye is told where it arrived rather than
// being left to search the pane it was sent to.
//
// **Where there is nothing to travel to, nothing moves.** An annotation anchored to another document, or one whose
// anchor has detached, has no destination; a notice says so for about a second and a half, anchored to whatever was
// double-clicked. No approximate destination is invented — sending a reader to roughly the right place is worse than
// telling them there is no place, because they will believe it.

import { INPUT, scrollerOf } from '$lib/fragments/hold';

/** How long the destination is marked after arriving. Long enough to find, short enough not to be decoration. */
const FLASH = 700;
/** How long the notice stands when there is nowhere to go. */
const NOTICE = 1500;

/** Mark an element as the place just arrived at, and clear it again. */
export function flash(el: Element): void {
	el.classList.add('travelled');
	setTimeout(() => el.classList.remove('travelled'), FLASH);
}

/**
 * Say, beside `from`, that there is nowhere to go.
 *
 * Placed in viewport coordinates and appended to `from`'s own pane rather than the page root: arras is a guest in the
 * document it renders and writes only inside its own subtree.
 */
export function nowhere(from: Element, said = 'nothing to travel to'): void {
	const host = document.createElement('div');
	host.className = 'travel-notice';
	host.setAttribute('role', 'status');
	host.dataset.testid = 'travel-nowhere';
	host.textContent = said;
	(from.closest('.fragment, .pane, main') ?? document.body).append(host);
	const r = from.getBoundingClientRect();
	host.style.left = Math.max(4, Math.min(r.left, window.innerWidth - host.offsetWidth - 4)) + 'px';
	host.style.top = Math.max(4, r.top - host.offsetHeight - 6) + 'px';
	setTimeout(() => host.remove(), NOTICE);
}

/**
 * Travel from one place to another.
 *
 * Parameters
 * ----------
 * to : Element or null
 *     Where to go; null is the honest answer for an annotation with no place in this document, and produces the notice.
 * from : Element
 *     What was double-clicked, which is what the notice is anchored to.
 *
 * Returns
 * -------
 * boolean
 *     Whether it went anywhere.
 */
export function travel(to: Element | null | undefined, from: Element): boolean {
	if (!to) {
		nowhere(from);
		return false;
	}
	arriveAt(to);
	to.scrollIntoView({ block: 'center', behavior: 'smooth' });
	flash(to);
	return true;
}

/** Put `to` back at the centre once a smooth scroll to it ends: the blocks a read view skips are laid out at their real size as the scroll passes them, so the place it set out for can be thousands of pixels from where `to` stands when it gets there. Nothing waits when `to` is centred already; the reader taking over, or a scroll that never ends, cancels it. */
function arriveAt(to: Element): void {
	if (!('onscrollend' in window)) return;
	const scroller = scrollerOf(to);
	const view = scroller === document.scrollingElement ? { top: 0, height: window.innerHeight } : scroller.getBoundingClientRect();
	const r = to.getBoundingClientRect();
	if (Math.abs(r.top + r.height / 2 - (view.top + view.height / 2)) < 2) return;
	const ends: EventTarget = scroller === document.scrollingElement ? document : scroller;
	const quit = setTimeout(done, 5000);
	function done(): void {
		clearTimeout(quit);
		ends.removeEventListener('scrollend', end);
		for (const e of INPUT) window.removeEventListener(e, done, true);
	}
	function end(): void {
		done();
		if (to.isConnected) to.scrollIntoView({ block: 'center' });
	}
	ends.addEventListener('scrollend', end);
	for (const e of INPUT) window.addEventListener(e, done, { capture: true, passive: true });
}
