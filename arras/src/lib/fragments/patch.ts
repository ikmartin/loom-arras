// Bringing a fragment's markup up to date in place: only the blocks whose markup changed are replaced, so every formula already typeset, and what the reader has open, stays where it is. An annotation's new mark changes one paragraph; replacing the whole document for it meant typesetting every formula again.

/** Attributes that carry source offsets: an edit earlier in a file moves them on every later block without changing what the block says. */
const OFFSETS = ['data-src', 'data-at', 'id'];
const OFFSET_TEXT = /\s(?:data-src|data-at|id)="[^"]*"/g;

const blocks = (root: ParentNode): HTMLElement[] => [...root.querySelectorAll<HTMLElement>('[data-src]')];
const plain = (html: string): string => html.replace(OFFSET_TEXT, '');

/** Published markup as a detached tree, for comparing against the next version. */
export function parse(html: string): DocumentFragment {
	const t = document.createElement('template');
	t.innerHTML = html;
	return t.content;
}

/** The markup of `nodes` with every block among them, at any depth, cut down to a placeholder: what is outside the blocks. */
function outside(nodes: NodeListOf<ChildNode>): string {
	let out = '';
	for (const n of nodes) {
		if (n.nodeType === Node.TEXT_NODE) out += n.textContent ?? '';
		else if (n instanceof Element) out += n.hasAttribute('data-src') ? '<b/>' : n.querySelector('[data-src]') ? shell(n) + outside(n.childNodes) : n.outerHTML;
	}
	return out;
}

/** An element's opening tag, with its attributes in order. */
function shell(el: Element): string {
	let out = '<' + el.tagName;
	for (const a of el.attributes) out += ` ${a.name}="${a.value}"`;
	return out + '>';
}

/** A block's own markup, its descendant blocks cut out, so a change inside a child is not a change to it. */
const own = (el: Element): string => shell(el) + outside(el.childNodes);

/** The elements carrying offsets in a block, the block first: all of them, or those of its own text only. What wiring and the reader's boxes put in a live block carries none, but a box's card may, so those are left out. */
function offsetBearers(block: HTMLElement, deep: boolean): HTMLElement[] {
	const inner = [...block.querySelectorAll<HTMLElement>('[data-src], [data-at]')].filter((e) => !e.closest('aside.comment-slot, .node-margin'));
	return [block, ...(deep ? inner : inner.filter((e) => !e.hasAttribute('data-src') && e.parentElement?.closest('[data-src]') === block))];
}

function sync(live: HTMLElement[], next: HTMLElement[]): void {
	for (let k = 0; k < live.length; k++)
		for (const a of OFFSETS) {
			const v = next[k].getAttribute(a);
			if (v === null) live[k].removeAttribute(a);
			else if (live[k].getAttribute(a) !== v) live[k].setAttribute(a, v);
		}
}

type Step = { at: number; does: 'replace' } | { at: number; does: 'sync'; deep: boolean };

/**
 * Patch `root`, which holds the markup `before` was parsed from as it was drawn (typeset and wired since), so that it holds `after`.
 *
 * Blocks are matched by position among the `[data-src]` elements, since `data-src` repeats (an inclusion and the section it wraps, a file included twice). A block whose markup is unchanged is left alone; one that differs only in its offsets has them copied in; one whose own markup is unchanged is looked into; any other is replaced by the new one, and the comment slot wiring put after it goes with it. Returns the blocks put in, for the caller to typeset and wire, and `after` parsed, to patch against next time; null when the two differ in structure, or the live markup has blocks of its own (an expanded inclusion, a comparison's swap), and the fragment should be drawn again whole.
 */
export function patch(root: HTMLElement, before: DocumentFragment, after: string): { put: HTMLElement[]; tree: DocumentFragment } | null {
	if (root.querySelector('.expanded, .compare-swap')) return null;
	const now = parse(after);
	const old = blocks(before);
	const next = blocks(now);
	const live = blocks(root);
	if (old.length !== next.length || live.length !== old.length) return null;
	if (old.some((b, i) => b.tagName !== next[i].tagName || b.tagName !== live[i].tagName)) return null;
	if (plain(outside(before.childNodes)) !== plain(outside(now.childNodes))) return null;

	const steps: Step[] = [];
	for (let i = 0; i < old.length; ) {
		const span = old[i].querySelectorAll('[data-src]').length;
		if (span !== next[i].querySelectorAll('[data-src]').length) return null;
		const a = old[i].outerHTML;
		const b = next[i].outerHTML;
		if (a === b) {
			i += span + 1;
		} else if (plain(a) === plain(b)) {
			steps.push({ at: i, does: 'sync', deep: true });
			i += span + 1;
		} else if (span && plain(own(old[i])) === plain(own(next[i]))) {
			steps.push({ at: i, does: 'sync', deep: false });
			i += 1;
		} else {
			steps.push({ at: i, does: 'replace' });
			i += span + 1;
		}
	}

	// everything checked before anything is changed
	const pairs: [HTMLElement[], HTMLElement[]][] = [];
	for (const s of steps) {
		if (s.does !== 'sync') continue;
		const l = offsetBearers(live[s.at], s.deep);
		const n = offsetBearers(next[s.at], s.deep);
		if (l.length !== n.length || l.some((e, k) => e.tagName !== n[k].tagName)) return null;
		pairs.push([l, n]);
	}
	for (const [l, n] of pairs) sync(l, n);
	const put: HTMLElement[] = [];
	for (const s of steps) {
		if (s.does !== 'replace') continue;
		const gone = live[s.at];
		const slot = gone.nextElementSibling;
		if (slot?.matches('aside.comment-slot[data-slot-for]')) slot.remove();
		const fresh = document.importNode(next[s.at], true);
		gone.replaceWith(fresh);
		put.push(fresh);
	}
	return { put, tree: now };
}
