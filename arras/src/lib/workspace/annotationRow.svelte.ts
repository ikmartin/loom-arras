// Whether the annotation row stands beneath every pane's toolbar: the tools that write (Annotate, Comment, the format menu, Undo and Redo, a PDF's drawing tools) on a row of their own, so the toolbar's own row holds what reads and fits a narrow pane. Shown at first, as a word processor's toolbar is, and kept in this browser once it is put away or shown again.
//
// Showing the row arms nothing; putting it away puts down any tool in hand, so no tool is ever armed while its button is out of sight.

const KEY = 'arras.annotation-row';

class AnnotationRow {
	open = $state(true);

	constructor() {
		try {
			if (globalThis.localStorage?.getItem(KEY) === 'hidden') this.open = false;
		} catch {
			// a browser that stores nothing shows the row
		}
	}

	/** Show or put away the row, everywhere, and remember which. */
	set(open: boolean): void {
		this.open = open;
		try {
			globalThis.localStorage?.setItem(KEY, open ? 'shown' : 'hidden');
		} catch {
			// kept for this visit only
		}
	}
}

export const annotationRow = new AnnotationRow();
