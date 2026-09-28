// Bare ids in published prose made into `quilt:` links (Prose.svelte), which the viewer then names as a reader refers to the result: `rl-0020-ai(a)` reads `Proposition 2.7(a)`.

/** A loom-local id, a derived one, and a proof's key: `rl-0020`, `rl-0020-ai`, `rl-0020/proof/2`; never inside a longer word or label. */
const ID = /(?<![\w:/-])[A-Za-z][A-Za-z0-9]*-[0-9A-Z]{4}(?:-ai)?(?:\/proof(?:\/\d+)?)?(?![\w-])/g;

/** Where an id is already something else: a link, code, a formula. */
const SKIP = 'a, code, pre, .math, mjx-container';

/**
 * Wrap every id `known` accepts, in the text of `root`, in an empty `quilt:` link.
 *
 * Parameters
 * ----------
 * root : Element
 *     Rendered prose.
 * known : (key: string) => boolean
 *     Whether the quilt has a node by this key; an id-shaped word it lacks is left as written.
 */
export function linkIds(root: Element, known: (key: string) => boolean): void {
	const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
	const texts: Text[] = [];
	for (let t = walker.nextNode(); t; t = walker.nextNode()) {
		if (!(t.parentElement?.closest(SKIP))) texts.push(t as Text);
	}
	for (const t of texts) {
		const parts = idParts(t.data, known);
		if (parts.length < 2) continue;
		const frag = document.createDocumentFragment();
		for (const part of parts) {
			if (typeof part === 'string') {
				frag.append(part);
				continue;
			}
			const a = document.createElement('a');
			a.href = 'quilt:' + part.id;
			a.title = part.id;
			frag.append(a);
		}
		t.replaceWith(frag);
	}
}

/** A text cut at the ids `known` accepts: the text between as strings, each id as `{ id }`. */
export function idParts(text: string, known: (key: string) => boolean): (string | { id: string })[] {
	const out: (string | { id: string })[] = [];
	let at = 0;
	for (const m of text.matchAll(ID)) {
		if (!known(m[0])) continue;
		if (m.index! > at) out.push(text.slice(at, m.index));
		out.push({ id: m[0] });
		at = m.index! + m[0].length;
	}
	if (at < text.length) out.push(text.slice(at));
	return out;
}
