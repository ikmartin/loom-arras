// What a reader selected in a fragment, as loom will look for it in the source: the words as they are, and each formula as its TeX between `$`s, which is the form loom's quote matching reads (records/selectors.py). The chrome a fragment carries — the gutter's id and state, a comment count, MathJax's hidden copy — is not text of the result and is left out.

const SKIP = '.node-margin, button, .comment-slot, mjx-assistive-mml, .env-label';

/** A formula's TeX as a quote carries it: `$…$` inline, `$$…$$` displayed. */
export function texOf(el: HTMLElement): string {
	let tex = (el.dataset.tex ?? el.textContent ?? '').trim();
	const display = el.classList.contains('display') || tex.startsWith('\\[');
	if (tex.startsWith('\\(') || tex.startsWith('\\[')) tex = tex.slice(2);
	if (tex.endsWith('\\)') || tex.endsWith('\\]')) tex = tex.slice(0, -2);
	tex = tex.trim();
	return display ? `$$${tex}$$` : `$${tex}$`;
}

/**
 * The quote a range stands for: its text, with every formula it touches whole, as TeX.
 *
 * Parameters
 * ----------
 * range : Range
 *     A selection's range, or a block's contents.
 *
 * Returns
 * -------
 * string
 *     Whitespace collapsed; '' when the range holds no text.
 */
export function quoteOf(range: Range): string {
	const root = range.commonAncestorContainer;
	const top = root.nodeType === Node.ELEMENT_NODE ? (root as Element) : root.parentElement;
	if (!top) return '';
	// a selection wholly inside one formula is that formula
	const inMath = top.closest<HTMLElement>('.math');
	if (inMath) return texOf(inMath);
	const out: string[] = [];
	const walk = (node: Node): void => {
		if (!range.intersectsNode(node)) return;
		if (node.nodeType === Node.TEXT_NODE) {
			const t = node.textContent ?? '';
			const a = node === range.startContainer ? range.startOffset : 0;
			const b = node === range.endContainer ? range.endOffset : t.length;
			out.push(t.slice(a, b));
			return;
		}
		if (node.nodeType !== Node.ELEMENT_NODE) return;
		const el = node as HTMLElement;
		if (el.matches(SKIP)) return;
		if (el.matches('.math')) {
			out.push(texOf(el));
			return;
		}
		for (const c of el.childNodes) walk(c);
	};
	walk(top);
	return out.join('').replace(/\s+/g, ' ').trim();
}

/** The key a place in a fragment belongs to: the closest result, proof or section around it, else `fallback`. */
export function keyOf(node: Node, fallback: string): string {
	const el = node.nodeType === Node.ELEMENT_NODE ? (node as Element) : node.parentElement;
	const at = el?.closest<HTMLElement>('div.env[data-key], details.env-proof[data-key], section[data-key], section[data-id]');
	return at?.dataset.key ?? at?.dataset.id ?? fallback;
}
