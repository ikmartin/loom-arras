<script lang="ts">
	// Compare, drawn over one pane (book 15.2.6). It reads the nodes the pane shows (`data-pair`, `data-hash`) into the comparison, and draws what the plan says on them: with a base, an 18px gutter at the pane's left edge carrying `−`, `+`, `~` or `↕` on each line that differs and a wedge where the other pane has a node this one lacks; without one, a dashed or dotted rule at a node's left; in both, a quiet tag after the node's label. The marks stand outside the text or wash it, never in the format's own furniture, so every format carries them.
	//
	// **A node's changed words need the publisher.** Until it answers, and for good on a static host, a node that differs is marked on every line; its answer is a rendering of each side with the changed words marked, which replaces the node's body in place, typeset with its own side's macros, so the marks narrow to the lines and words that changed. A node that holds other nodes keeps its whole-node marks: its own text has markers where they stand, and a rendering of it alone would drop them.
	//
	// **The panes never scroll together.** A step brings both to the difference, at the upper third; a double-click on a node brings its partner to the same height in the other pane, as a SyncTeX jump does, or its wedge where it has none.
	import { onDestroy, untrack } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import { flash } from '$lib/travel/travel';
	import type { Found, Mark, Plan } from './compare';
	import { comparison } from './compare.svelte';

	let { index, body }: { index: number; body: () => HTMLElement | null } = $props();

	const GLYPH: Record<string, string> = { del: '−', add: '+', both: '~', moved: '↕' };

	/** The element each pair is drawn on in this pane: its swapped rendering while there is one, else the node. */
	let nodes = new Map<string, HTMLElement>();
	const swaps = new Map<string, { el: HTMLElement; path: string }>();
	let overlay: HTMLElement | null = null;
	let wedgeAt = new Map<string, HTMLElement>();
	let frame = 0;

	/** Read the pane's nodes in document order; the comparison is only told when they changed. */
	function collect(): void {
		const root = body();
		if (!root) return;
		const found: Found[] = [];
		const seen = new Map<string, HTMLElement>();
		const headings = [...root.querySelectorAll<HTMLElement>(':is(h1, h2, h3, h4) .number')].filter((h) => !h.closest('.compare-swap, .review-comparison'));
		for (const el of root.querySelectorAll<HTMLElement>('[data-pair][data-hash]')) {
			if (el.closest('.compare-swap, .review-comparison, .compare-gutter')) continue;
			const pair = el.dataset.pair!;
			if (seen.has(pair)) continue;
			seen.set(pair, el);
			found.push({ pair, hash: el.dataset.hash ?? '', key: el.dataset.key ?? null, section: sectionOf(el, headings) });
		}
		nodes = seen;
		const was = comparison.found[index];
		if (was.length === found.length && was.every((f, i) => f.pair === found[i].pair && f.hash === found[i].hash && f.section === found[i].section)) return;
		const next = [...comparison.found] as [Found[], Found[]];
		next[index] = found;
		comparison.found = next;
	}

	/** The number of the last numbered heading before a node, for "moved from §2". */
	function sectionOf(el: HTMLElement, headings: HTMLElement[]): string | null {
		let last: HTMLElement | null = null;
		for (const h of headings) {
			if (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) last = h;
			else break;
		}
		return last?.textContent?.trim() || null;
	}

	/** The element a pair is drawn on here. */
	const drawn = (pair: string): HTMLElement | null => swaps.get(pair)?.el ?? nodes.get(pair) ?? null;

	/** Take off everything this layer put on the pane. */
	function strip(): void {
		const root = body();
		for (const { el } of swaps.values()) el.remove();
		swaps.clear();
		if (root) {
			for (const el of root.querySelectorAll<HTMLElement>('[data-compare-hidden]')) {
				el.hidden = false;
				delete el.dataset.compareHidden;
			}
			for (const t of root.querySelectorAll('.compare-tag')) t.remove();
			for (const el of root.querySelectorAll<HTMLElement>('.compare-mark')) el.classList.remove(...[...el.classList].filter((c) => c.startsWith('compare-')));
		}
		overlay?.remove();
		overlay = null;
	}

	/** Put the plan's marks on the nodes: classes, tags, and the publisher's renderings where it gave one. */
	function decorate(p: Plan): void {
		strip();
		const marks = p.marks[index];
		const side = index === 0 ? 'left' : 'right';
		const answered = new Map((comparison.answer?.pairs ?? []).map((a) => [a.pair, a[side]]));
		const macroName = comparison.answer?.[side].macros ?? null;
		for (const [pair, el] of nodes) {
			const mark = marks.get(pair);
			if (!mark) continue;
			const path = answered.get(pair)?.fragment;
			if (!mark.whole && path && !el.querySelector('[data-pair]')) void swap(pair, el, path, mark, macroName);
			label(el, mark);
		}
		schedule();
	}

	function label(el: HTMLElement, mark: Mark): void {
		el.classList.add('compare-mark', `compare-${mark.kind}`);
		if (mark.also) el.classList.add(`compare-also-${mark.also}`);
		if (!mark.tag) return;
		// a swapped rendering holds the node one level down
		const at = el.querySelector(':scope > .env-label, :scope > summary, :scope > .env > .env-label, :scope > details > summary') ?? el;
		const tag = document.createElement('span');
		tag.className = 'compare-tag';
		tag.textContent = mark.tag;
		at.appendChild(tag);
	}

	/** Replace a node's body with the publisher's rendering of it, its changed words marked, typeset with its own side's macros. */
	async function swap(pair: string, el: HTMLElement, path: string, mark: Mark, macroName: string | null): Promise<void> {
		let html: string;
		try {
			html = await fetchFragment(path, store.hash);
		} catch {
			return; // the whole-node marks stand
		}
		if (nodes.get(pair) !== el || swaps.has(pair)) return;
		const holder = document.createElement('div');
		holder.className = 'compare-swap';
		holder.dataset.swapFor = pair;
		holder.innerHTML = html;
		const inner = holder.firstElementChild as HTMLElement | null;
		if (inner?.tagName === 'DETAILS') inner.setAttribute('open', '');
		el.after(holder);
		el.hidden = true;
		el.dataset.compareHidden = '';
		swaps.set(pair, { el: holder, path });
		label(holder, mark);
		const sets = store.manifest?.macros.sets ?? {};
		const macros = macroName ? (sets[macroName] ?? []) : (store.manifest?.macros.default ?? []);
		try {
			const { typesetScoped } = await import('$lib/math/scoped');
			await typesetScoped(holder, macros);
		} catch {
			// the rendering reads as TeX where it cannot be typeset; its marks still stand
		}
		schedule();
	}

	function schedule(): void {
		cancelAnimationFrame(frame);
		frame = requestAnimationFrame(draw);
	}

	/** The lines of an element's text, as their middles in viewport coordinates: from its words and its formulas, never from a block's box, which spans several lines. */
	function lines(el: HTMLElement): number[] {
		const boxes: DOMRect[] = [];
		const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
			acceptNode: (n) => {
				if (n instanceof HTMLElement && (n.hidden || n.matches('.compare-tag'))) return NodeFilter.FILTER_REJECT;
				// a typeset formula is measured whole; MathJax draws its glyphs with no text of their own
				if (n instanceof Element && n.matches('mjx-container, img, svg')) {
					boxes.push(...n.getClientRects());
					return NodeFilter.FILTER_REJECT;
				}
				return n.nodeType === Node.TEXT_NODE && n.textContent?.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
			}
		});
		const range = document.createRange();
		for (let t = walk.nextNode(); t; t = walk.nextNode()) {
			range.selectNodeContents(t);
			boxes.push(...range.getClientRects());
		}
		// boxes on one line overlap by most of the shorter one's height; a tall formula and the words beside it are one line
		const sorted = boxes.filter((r) => r.height && r.width).sort((a, b) => a.top - b.top);
		const out: { top: number; bottom: number }[] = [];
		for (const r of sorted) {
			const last = out[out.length - 1];
			if (last && Math.min(last.bottom, r.bottom) - Math.max(last.top, r.top) > 0.4 * Math.min(r.height, last.bottom - last.top)) {
				last.top = Math.min(last.top, r.top);
				last.bottom = Math.max(last.bottom, r.bottom);
			} else out.push({ top: r.top, bottom: r.bottom });
		}
		return out.map((b) => (b.top + b.bottom) / 2);
	}

	/** The gutter and its wedges, drawn again whenever what is under them may have moved. */
	function draw(): void {
		const root = body();
		const p = comparison.plan;
		if (!root || !p) return;
		root.classList.toggle('compare-room', p.based);
		if (!p.based) {
			overlay?.remove();
			overlay = null;
			return;
		}
		if (!overlay) {
			overlay = document.createElement('div');
			overlay.className = 'compare-gutter';
			overlay.setAttribute('aria-hidden', 'true');
			root.prepend(overlay);
		}
		const top0 = root.getBoundingClientRect().top - root.scrollTop;
		overlay.style.height = `${root.scrollHeight}px`;
		let out = '';
		for (const [pair, mark] of p.marks[index]) {
			const glyph = GLYPH[mark.kind];
			const el = drawn(pair);
			if (!glyph || !el || el.hidden) continue;
			const lh = parseFloat(getComputedStyle(el).lineHeight) || 22;
			let ys = lines(el);
			if (!mark.whole) {
				const changed = [...el.querySelectorAll('.review-changed, .review-change-point')].flatMap((m) => [...m.getClientRects()]);
				const hit = ys.filter((y) => changed.some((r) => Math.abs(r.top + r.height / 2 - y) < lh / 2));
				if (hit.length) ys = hit;
			}
			for (const y of ys) out += `<div class="gl ${mark.kind}" data-glyph="${esc(pair)}" style="top:${y - top0 - lh / 2}px;height:${lh}px">${glyph}</div>`;
		}
		const fragmentTop = (root.querySelector('.fragment')?.getBoundingClientRect().top ?? top0) - top0;
		const placed = p.wedges[index]
			.map((w) => {
				const after = w.after ? drawn(w.after) : null;
				return { w, y: (after ? after.getBoundingClientRect().bottom - top0 : fragmentTop) - 5 };
			})
			.sort((a, b) => a.y - b.y);
		let last = -Infinity;
		for (const { w, y: at } of placed) {
			// two wedges at one place stack rather than cover each other
			const y = at - last < 11 ? last + 11 : at;
			last = y;
			out += `<div class="gw ${w.kind}" data-wedge="${esc(w.pair)}" style="top:${y}px"></div>`;
		}
		overlay.innerHTML = out;
		wedgeAt = new Map([...overlay.querySelectorAll<HTMLElement>('[data-wedge]')].map((w) => [w.dataset.wedge!, w]));
	}

	const esc = (s: string) => s.replace(/[&"<>]/g, (c) => `&#${c.charCodeAt(0)};`);

	/** Bring a pair here to a height in the viewport, or its wedge where this pane lacks it; nothing moves where there is neither. */
	function bring(pair: string, y: number | null): void {
		const root = body();
		if (!root) return;
		const el = drawn(pair) ?? wedgeAt.get(pair) ?? null;
		if (!el) return;
		const at = root.getBoundingClientRect();
		const want = y ?? at.top + root.clientHeight / 3;
		root.scrollTop += el.getBoundingClientRect().top - want;
		flash(el);
	}

	// the pane's nodes arrive with its fragment, after typesetting, and again on every re-render
	$effect(() => {
		const root = body();
		if (!root) return;
		collect();
		const seen = new MutationObserver((records) => {
			// what this layer draws is not a change to the document
			if (records.every((r) => (r.target as HTMLElement).closest?.('.compare-gutter, .compare-swap, .compare-tag') || [...r.addedNodes, ...r.removedNodes].every((n) => n instanceof HTMLElement && n.matches('.compare-gutter, .compare-swap, .compare-tag')))) return;
			collect();
			const p = untrack(() => comparison.plan);
			if (p) schedule();
		});
		seen.observe(root, { childList: true, subtree: true });
		// the page grows as its formulas are typeset and its fragments arrive: every child but the gutter is watched
		const size = new ResizeObserver(schedule);
		size.observe(root);
		for (const child of root.children) if (!child.classList.contains('compare-gutter')) size.observe(child);
		return () => {
			seen.disconnect();
			size.disconnect();
		};
	});

	// the marks follow the plan: what the two panes hold, and what the publisher answered
	$effect(() => {
		const p = comparison.plan;
		if (p) untrack(() => decorate(p));
	});

	$effect(() => {
		const j = comparison.jump;
		if (j && j.from !== index) untrack(() => bring(j.pair, j.y));
	});

	// hover lights the partner, in whichever pane it stands
	$effect(() => {
		const pair = comparison.hover;
		const el = pair ? drawn(pair) : null;
		el?.classList.add('compare-lit');
		return () => el?.classList.remove('compare-lit');
	});

	function nodeAt(t: EventTarget | null): string | null {
		const el = (t as HTMLElement | null)?.closest?.<HTMLElement>('[data-pair], [data-swap-for]');
		return el?.dataset.pair ?? el?.dataset.swapFor ?? null;
	}

	function over(e: MouseEvent): void {
		const pair = nodeAt(e.target);
		if (pair !== comparison.hover) comparison.hover = pair;
	}

	function twice(e: MouseEvent): void {
		// a double-click on an annotation's mark keeps its own meaning
		if ((e.target as HTMLElement | null)?.closest('mark.annotation, .annotation-block, a')) return;
		const pair = nodeAt(e.target);
		if (!pair) return;
		window.getSelection()?.removeAllRanges();
		const el = drawn(pair);
		comparison.go(pair, index, el ? el.getBoundingClientRect().top : e.clientY);
	}

	$effect(() => {
		const root = body();
		if (!root) return;
		root.addEventListener('mouseover', over);
		root.addEventListener('dblclick', twice);
		return () => {
			root.removeEventListener('mouseover', over);
			root.removeEventListener('dblclick', twice);
		};
	});

	onDestroy(() => {
		cancelAnimationFrame(frame);
		strip();
		body()?.classList.remove('compare-room');
		const next = [...comparison.found] as [Found[], Found[]];
		next[index] = [];
		comparison.found = next;
	});
</script>

<style>
	/* room for the gutter, so it never covers the first letters of a line */
	:global(.body.compare-room) {
		padding-left: 24px;
	}
	/* the gutter: 18px down the pane's left edge, over the text's margin, one cell per line that differs */
	:global(.compare-gutter) {
		position: absolute;
		left: 0;
		top: 0;
		width: 18px;
		border-right: 1px solid var(--rule);
		pointer-events: none;
		z-index: 1;
	}
	:global(.compare-gutter .gl) {
		position: absolute;
		left: 0;
		width: 18px;
		display: grid;
		place-items: center;
		font: 600 12px/1 var(--mono);
	}
	:global(.compare-gutter .gl.del) {
		background: var(--diff-del-wash);
		color: var(--diff-del);
	}
	:global(.compare-gutter .gl.add) {
		background: var(--diff-add-wash);
		color: var(--diff-add);
	}
	:global(.compare-gutter .gl.both) {
		background: var(--state-stale-wash);
		color: var(--state-stale);
	}
	:global(.compare-gutter .gl.moved) {
		background: var(--leaf);
		color: var(--ink-soft);
	}
	:global(.compare-gutter .gw) {
		position: absolute;
		left: 0;
		width: 0;
		height: 0;
		border-block: 5px solid transparent;
		border-left: 8px solid var(--diff-del);
	}
	:global(.compare-gutter .gw.add) {
		border-left-color: var(--diff-add);
	}
	:global(.compare-gutter .gw.moved) {
		border-left-color: var(--ink-faint);
	}
	:global(.compare-gutter .gw.travelled) {
		filter: drop-shadow(0 0 3px var(--link));
	}
	/* the changed words, washed to match their side */
	:global(.compare-swap.compare-del mark.review-changed),
	:global(.compare-swap.compare-del .math.review-changed) {
		background: var(--diff-del-wash);
		color: inherit;
	}
	:global(.compare-swap.compare-add mark.review-changed),
	:global(.compare-swap.compare-add .math.review-changed) {
		background: var(--diff-add-wash);
		color: inherit;
	}
	:global(.compare-swap.compare-both mark.review-changed),
	:global(.compare-swap.compare-both .math.review-changed) {
		background: var(--state-stale-wash);
		color: inherit;
	}
	/* where one side has words the other lacks: a thin bar in its side's colour, never the text's, which reads as a caret */
	:global(.compare-swap .review-change-point) {
		border-left: 2px solid var(--diff-del);
	}
	:global(.compare-swap.compare-add .review-change-point) {
		border-left-color: var(--diff-add);
	}
	:global(.compare-swap.compare-both .review-change-point) {
		border-left-color: var(--state-stale);
	}
	/* presence dashed, order dotted, just left of the node: drawn beside it rather than as its border, which every format already uses for its own furniture */
	:global(.compare-mark.compare-only),
	:global(.compare-mark.compare-order) {
		position: relative;
	}
	:global(.compare-mark.compare-only)::after,
	:global(.compare-mark.compare-order)::after {
		content: '';
		position: absolute;
		left: -10px;
		top: 2px;
		bottom: 2px;
		border-left: 2px dashed var(--ink-faint);
		pointer-events: none;
	}
	:global(.compare-mark.compare-order)::after {
		border-left-style: dotted;
	}
	/* inline-block, so a justified line does not stretch the words apart */
	:global(.compare-tag) {
		display: inline-block;
		font-family: var(--sans);
		font-size: 11px;
		font-weight: 400;
		font-style: normal;
		color: var(--ink-faint);
		margin-left: 6px;
		white-space: nowrap;
		text-indent: 0;
	}
	:global(.compare-lit) {
		border-radius: 4px;
		box-shadow: 0 0 0 4px var(--link-wash);
		background: var(--link-wash);
	}
</style>
