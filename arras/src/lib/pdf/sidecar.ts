// The per-work sidecar, `build/spans/<scheme>/<id>.json`, as `_attach_spans` writes it (specs/manifest.md §13).
//
// Geometry only. Bodies stay in the manifest with every other annotation, so the session filter, the picker's counts,
// the discussion pane and the verbs all read one map; what a sidecar spares the manifest is the rectangles, which are
// wanted for the one paper being read and for nothing else.

export interface Sidecar {
	/** The artifact's hash, which every anchor in here names. */
	artifact: string;
	/** Each page anything is drawn on: its size in points and its rotation. Coordinates are points, origin top left. */
	pages: Record<string, { width: number; height: number; rotate: number }>;
	/** The work's results, by result id: one rectangle per line. */
	quads: Record<string, number[][]>;
	/** The notes on its pages, by annotation id: one rectangle per line, or the rectangle that was drawn. */
	marks?: Record<string, number[][]>;
}
