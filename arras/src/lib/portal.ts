// Floating layers that must cover the whole shell, whatever holds them in the component tree.

import type { Action } from 'svelte/action';

/**
 * Move an element to the end of `document.body` while it is mounted.
 *
 * A fixed overlay declared inside a rail or panel is otherwise stacked within that ancestor's stacking context, so a sibling panel with a lower z-index can still cover it.
 */
export const portal: Action<HTMLElement> = (node) => {
	document.body.appendChild(node);
	return {
		destroy() {
			node.remove();
		}
	};
};
