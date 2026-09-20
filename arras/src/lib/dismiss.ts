// One behaviour for every floating box: selecting anywhere outside it, or pressing Escape, closes it.

import type { Action } from 'svelte/action';

/**
 * Close a floating box when the pointer goes down outside it or Escape is pressed.
 *
 * Attach it to the element that holds both the box and the control that opens it, so the control's own click toggles rather than closing and reopening. `pointerdown` in the capture phase is used rather than `click`, so a press that starts a drag or a text selection elsewhere also closes the box, and nothing inside the page can swallow the event first.
 *
 * Parameters
 * ----------
 * node : HTMLElement
 *     The box, with its opener inside it.
 * close : () => void
 *     Called once per outside press or Escape; closing an already closed box must be harmless.
 */
export const dismiss: Action<HTMLElement, () => void> = (node, close) => {
	let fn = close;
	const onDown = (e: PointerEvent) => {
		if (!node.contains(e.target as Node)) fn?.();
	};
	const onKey = (e: KeyboardEvent) => {
		if (e.key === 'Escape') fn?.();
	};
	document.addEventListener('pointerdown', onDown, true);
	document.addEventListener('keydown', onKey);
	return {
		update(next) {
			fn = next;
		},
		destroy() {
			document.removeEventListener('pointerdown', onDown, true);
			document.removeEventListener('keydown', onKey);
		}
	};
};
