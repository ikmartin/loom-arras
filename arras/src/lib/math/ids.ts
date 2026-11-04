// Bare ids in published prose made into `quilt:` links (Prose.svelte), which the viewer then names as a reader refers to the result: `rl-0020-ai(a)` reads `Proposition 2.7(a)`.

/** A loom-local id, a derived one, and a proof's key: `rl-0020`, `rl-0020-ai`, `rl-0020/proof/2`; never inside a longer word or label. */
const ID = /(?<![\w:/-])[A-Za-z][A-Za-z0-9]*-[0-9A-Z]{4}(?:-ai(?:-[0-9A-Z]{2,})?)?(?:\/proof(?:\/\d+)?)?(?![\w-])/g;

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

/**
 * A link's name once the words before it are read: the number alone when they already say its kind, as `Corollary~\ref{…}` prints in LaTeX, so "Corollary [](quilt:…)" reads "Corollary 7.8" and not "Corollary Corollary 7.8".
 *
 * Parameters
 * ----------
 * before : string
 *     The text right before the link.
 * name : string
 *     The name the viewer gives it ("Corollary 7.8"); one not ending in a number is kept whole.
 * chained : string | null
 *     The kind of the link just before, when it was shortened and only "and", "or", a comma or a dash stands between: "Theorems [](a) and [](b)" reads "Theorems 4.8 and 6.43".
 *
 * Returns
 * -------
 * { text: string; kind: string | null }
 *     The text to show, and the kind when it was shortened, to pass on as the next link's `chained`.
 */
export function elided(before: string, name: string, chained: string | null): { text: string; kind: string | null } {
	const m = /^(.*\S)\s+(\S*\d\S*)$/.exec(name);
	if (!m) return { text: name, kind: null };
	const [, kind, number] = m;
	const tail = before.replace(/[\s~ ]+$/, '');
	const said = new RegExp(`(^|[^\\w])${kind.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(s|es)?$`, 'i').test(tail);
	const listed = chained !== null && chained.toLowerCase() === kind.toLowerCase() && /(^|\s)(and|or)$|[,–-]$/i.test(tail);
	return said || listed ? { text: number, kind } : { text: name, kind: null };
}
