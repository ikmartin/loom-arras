// A selection for Annotate, widened to whole words: a drag that stops partway through a word ("Hull's se") marks the whole word, as a reader means it. A selection inside one word is kept to the letter, since that is chosen on purpose, and a formula's text is never cut into.

/** A letter, digit or mark, or what joins two inside a word: an apostrophe, a hyphen, an underscore. */
const WORD = /[\p{L}\p{N}\p{M}'’_-]/u;

function wordAt(text: string, i: number): boolean {
	return i >= 0 && i < text.length && WORD.test(text[i]);
}

function inMath(n: Node): boolean {
	return !!n.parentElement?.closest('mjx-container, .math, [data-tex]');
}

/**
 * Widen `range` to the words its ends stand in, in place.
 *
 * Parameters
 * ----------
 * range : Range
 *     The selection's range; an end not in a text node, or in a formula, is left where it is.
 *
 * Returns
 * -------
 * bool
 *     Whether it was widened.
 */
export function snapToWords(range: Range): boolean {
	const s = range.startContainer;
	const e = range.endContainer;
	if (s === e && s.nodeType === Node.TEXT_NODE) {
		const inner = (s.textContent ?? '').slice(range.startOffset, range.endOffset);
		// within one word: the letters were chosen
		if (inner && [...inner].every((ch) => WORD.test(ch))) return false;
	}
	let moved = false;
	if (s.nodeType === Node.TEXT_NODE && !inMath(s)) {
		const text = s.textContent ?? '';
		let i = range.startOffset;
		if (wordAt(text, i) && wordAt(text, i - 1)) {
			while (wordAt(text, i - 1)) i--;
			range.setStart(s, i);
			moved = true;
		}
	}
	if (e.nodeType === Node.TEXT_NODE && !inMath(e)) {
		const text = e.textContent ?? '';
		let j = range.endOffset;
		if (wordAt(text, j) && wordAt(text, j - 1)) {
			while (wordAt(text, j)) j++;
			range.setEnd(e, j);
			moved = true;
		}
	}
	return moved;
}
