// Where the divider between the two panes may stand (plan 0.13.3 W1): one snap, at the middle, and never so far that a pane is unusable.

/** The snap: the middle, since a snap at a third would be a guess about a screen this code cannot see. */
export const SNAP = 0.5;
const NEAR = 0.03;

/**
 * A dragged or nudged position, as the ratio it becomes.
 *
 * The snap is for a pointer, whose aim is approximate; a key names an exact step, so it passes `snap = false`. Clamped to 0.2–0.8 so a drag past the frame, or a pointer that left the window mid-drag, cannot leave a pane a reader cannot use.
 */
export function settle(next: number, snap = true): number {
	const snapped = snap && Math.abs(next - SNAP) < NEAR ? SNAP : next;
	return Math.min(0.8, Math.max(0.2, snapped));
}
