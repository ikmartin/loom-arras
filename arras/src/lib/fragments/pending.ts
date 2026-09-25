// The place a note is being written against, kept lit while the composer is open (phase 5 follow-up). Focusing the composer's field ends the reader's selection, so the words selected are painted as a highlight of their own — the CSS Custom Highlight API, which follows the text as it scrolls and changes no markup — and a block chosen by a box is marked by a class. One pending place at a time, cleared when the note is written or cancelled.

const NAME = 'note-pending';
let marked: HTMLElement | null = null;

/** Light the place a note is being written against: a text range, or an element a box was drawn round. */
export function showPending(range: Range | null, el: HTMLElement | null = null): void {
	clearPending();
	const registry = (globalThis as { CSS?: { highlights?: Map<string, unknown> } }).CSS?.highlights;
	const Ctor = (globalThis as { Highlight?: new (...r: Range[]) => unknown }).Highlight;
	if (range && registry && Ctor) registry.set(NAME, new Ctor(range));
	if (el) {
		el.classList.add(NAME);
		marked = el;
	}
}

/** Put the place out, whether or not anything was lit. */
export function clearPending(): void {
	(globalThis as { CSS?: { highlights?: Map<string, unknown> } }).CSS?.highlights?.delete(NAME);
	marked?.classList.remove(NAME);
	marked = null;
}
