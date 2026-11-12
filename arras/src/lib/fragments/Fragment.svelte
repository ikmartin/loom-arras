<script lang="ts">
	import type { Annotating } from '$lib/review/annotating.svelte';
	import { passes } from '$lib/review/annotating.svelte';
	import { acted, prune } from '$lib/review/acted.svelte';
	import { authorOf, changeById, changesIn, pending } from '$lib/review/changes';
	import type { Macro } from '$lib/manifest/types';
	import { onDestroy, onMount, tick, untrack } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import { resetComments, settled, wire, type CommentSlot } from '$lib/fragments/mount';
	import { on } from '$lib/annotations';
	import { flash } from '$lib/travel/travel';
	import { markPages } from '$lib/fragments/pages';
	import { typeset } from '$lib/math/mathjax';
	import { ui } from '$lib/ui.svelte';
	import { page } from '$app/state';
	import { prefs } from '$lib/prefs.svelte';
	import { paneOf } from '$lib/workspace/state.svelte';
	import { workspace } from '$lib/workspace/store.svelte';
	import { CHANGES, changeIds, MARKED, MARKS, popups, type Popups } from './popup';
	import { closeChooser, drawGutter, idsOf } from './gutter';
	import { hold, type Hold } from './hold';
	import { keep, take } from './kept';
	import { parse, patch } from './patch';

	let {
		path,
		macroSet = '',
		previewMacros,
		isolatedMacros = false,
		master = '',
		headingLinks = false,
		margins = false,
		annotations,
		standalone = false,
		comments,
		anchor,
		jump = 0,
		note,
		arrival,
		onmounted
	}: {
		path: string;
		macroSet?: string;
		previewMacros?: import('$lib/manifest/types').Macro[];
		/** Accepted review text uses its saved preamble without modifying the live MathJax instance. */
		isolatedMacros?: boolean;
		master?: string;
		headingLinks?: boolean;
		margins?: boolean;
		/** The item's annotating: this fragment sets its annotations' and changes' reading order and registers opening one; given, the margin's icons are drawn and the pending changes are drawn in their blocks, as its view says. */
		annotations?: Annotating;
		/** A document that carries no identity: its own references are already in-page anchors, and nothing in it is a key. */
		standalone?: boolean;
		comments?: (key: string) => CommentSlot[];
		/** The element to scroll to, by its published id. Given by a renderer in a pane, which then ignores the URL's hash: in two panes the hash is only one of them's. */
		anchor?: string;
		/** Changes each time the item is opened again, so the fragment goes to `anchor` even when it is unchanged. */
		jump?: number;
		/** An annotation to open at its mark on arrival: what a followed link to an annotation names. */
		note?: string;
		/** Where the request last answered is kept, when it must outlive this fragment: a pane's item keeps it, so coming back to the item does not go to its link's place again. */
		arrival?: { at: string | null };
		onmounted?: (root: HTMLElement) => void;
	} = $props();

	/** The element the reader is sent to: the pane's own anchor when one is given, else the URL's hash. */
	const target = (): string => (anchor !== undefined ? anchor : decodeURIComponent(location.hash.slice(1)));

	/** One request to go somewhere: in a pane, its anchor, the annotation it names and each reopening (`jump`); elsewhere the URL's hash. */
	const request = (): string => (anchor !== undefined ? `${anchor}\u0000${jump}\u0000${note ?? ''}` : page.url.hash);
	/**
	 * The request last arrived at. **A request is answered once**: the fragment mounts again on every new manifest, which a serving publisher writes whenever anything in the quilt changes -- an agent's annotation, a compile -- and a mount that went where the link had pointed each time sent a reader who had closed the box and scrolled on back to it, box open, every few seconds.
	 */
	const own = { at: null as string | null };
	const arrived = () => arrival ?? own;

	let html = $state('');
	/** The published markup drawn in `el` now, which new markup is patched against; null until something is drawn. */
	let placed: string | null = null;
	/** `placed` parsed, once a patch has needed it, so the next patch parses only the new markup. */
	let tree: DocumentFragment | null = null;
	let error = $state('');
	let mathReady = $state(false);
	let el: HTMLElement | undefined = $state();
	/** What holds the fragment: the popup stands in it, beside the fragment rather than inside its markup. */
	let frame: HTMLElement | undefined = $state();
	/** The margin's layer of icons. */
	let gutter: HTMLElement | undefined = $state();
	let mountVersion = 0;
	let loadVersion = 0;

	/** A `data-src`'s file and the range of it, `FILE:START:END`; null for one that names no range. */
	function rangeOf(src: string): { file: string; start: number; end: number } | null {
		const m = /^(.*):(\d+):(\d+)$/.exec(src);
		return m ? { file: m[1], start: Number(m[2]), end: Number(m[3]) } : null;
	}

	/** The elements of `t` with a `data-src` in `file`, each with its range. */
	function sourced(t: HTMLTemplateElement, file: string): { el: HTMLElement; start: number; end: number }[] {
		const out: { el: HTMLElement; start: number; end: number }[] = [];
		for (const el of t.content.querySelectorAll<HTMLElement>(`[data-src^="${CSS.escape(file + ':')}"]`)) {
			const r = rangeOf(el.dataset.src ?? '');
			if (r && r.file === file) out.push({ el, start: r.start, end: r.end });
		}
		return out;
	}

	/** Whether an element holds no other with a `data-src`: a leaf, one paragraph, display or item. */
	const leaf = (el: Element) => !el.querySelector('[data-src]');

	/**
	 * The element a merged block may be swapped for: the one whose `data-src` is the block's, where it is a leaf or a statement's or proof's own element; else, for a block whose range runs to its blank lines, the one leaf it overlaps. Null where it overlaps several, or names a container (a section, a list): such a change is drawn by its marker instead, so a merged block never stands over a whole section.
	 */
	function blockAt(t: HTMLTemplateElement, src: string): HTMLElement | null {
		const want = rangeOf(src);
		const exact = t.content.querySelector<HTMLElement>(`[data-src="${CSS.escape(src)}"]`);
		if (exact) return leaf(exact) || exact.matches('.env') ? exact : null;
		if (!want) return null;
		const hit = sourced(t, want.file).filter((x) => leaf(x.el) && Math.min(x.end, want.end) > Math.max(x.start, want.start));
		return hit.length === 1 ? hit[0].el : null;
	}

	/** The innermost element whose `data-src` holds the range `src`, where a change drawn by its marker stands; null where none does. */
	function holderOf(t: HTMLTemplateElement, src: string): HTMLElement | null {
		const want = rangeOf(src);
		if (!want) return null;
		const holding = sourced(t, want.file).filter((x) => x.start <= want.start && x.end >= want.end);
		holding.sort((a, b) => a.end - a.start - (b.end - b.start));
		return holding[0]?.el ?? null;
	}

	/** Whether merged text keeps every element of `at` that has a `data-src`: the document still needs each, for its place and its anchors. */
	function keepsAll(at: HTMLElement, merged: ParentNode): boolean {
		const has = new Set([...merged.querySelectorAll<HTMLElement>('[data-src]')].map((e) => e.dataset.src));
		return [...at.querySelectorAll<HTMLElement>('[data-src]')].every((e) => has.has(e.dataset.src));
	}

	/**
	 * The markup with each block holding pending changes swapped for the publisher's merged block, which carries every change's old and new words (`span.change`), and each change not merged into the text marked on the element holding its words (`data-change-at`). Only where the item annotates, which is where the changes are shown and acted on.
	 *
	 * The publisher gives a merged block the document's own offsets, ids and gone marks, and marks what only new words hold `data-new` in place of `data-src`. A merged block is swapped in only over one leaf, or over a statement's or proof's element whose every part it keeps, and never over another change's block: anything else is drawn by its marker, as a change to the text's structure (`place`) is. One element of the block's kind fills the block, which keeps its own element; anything else (TeX source, where TeX refused the merged text) takes a leaf's place, or stands inside a statement or proof after its label. One that cannot be fetched, or is not made yet, leaves its block as it was.
	 */
	async function withChanges(h: string, hash: string): Promise<string> {
		const all = pending(store.manifest);
		if (!annotations || !all.some((c) => c.block || c.place)) return h;
		const t = document.createElement('template');
		t.innerHTML = h;
		const blocks = new Map<string, { path: string; ids: string[] }>();
		for (const c of all) {
			if (!c.block?.src || !c.block.fragment) continue;
			const b = blocks.get(c.block.src) ?? { path: c.block.fragment, ids: [] };
			b.ids.push(c.id);
			blocks.set(c.block.src, b);
		}
		const found = [...blocks].map(([src, b]) => ({ src, ...b, at: blockAt(t, src) }));
		const marked: { id: string; src: string }[] = all.filter((c) => !c.block && c.place?.src).map((c) => ({ id: c.id, src: c.place!.src }));
		// a block in another's, or holding another's, is drawn by its marker: the one swap would undo the other
		const swaps = found.filter((f) => {
			const alone = !!f.at && !found.some((o) => o !== f && o.at && (f.at!.contains(o.at) || o.at.contains(f.at!)));
			if (!alone) marked.push(...f.ids.map((id) => ({ id, src: f.src })));
			return alone;
		});
		const merged = await Promise.all(swaps.map((b) => fetchFragment(b.path, hash).catch(() => null)));
		swaps.forEach((b, i) => {
			const text = merged[i];
			if (!text) return;
			const at = b.at!;
			const n = document.createElement('template');
			n.innerHTML = text;
			// shown as TeX where TeX refused it: the `{}` that joins a change's old words to its new ones is the publisher's, not the person's
			for (const old of n.content.querySelectorAll('pre.source span.change[data-side="old"]')) {
				const between = old.nextSibling;
				if (between?.nodeType === Node.TEXT_NODE && /^\s*\{\}\s*$/.test(between.textContent ?? '') && (between.nextSibling as Element | null)?.matches?.('span.change[data-side="new"]')) between.textContent = (between.textContent ?? '').replace('{}', ' ');
			}
			const roots = [...n.content.childNodes].filter((x) => x.nodeType !== Node.TEXT_NODE || x.textContent?.trim());
			const only = roots.length === 1 && roots[0] instanceof Element ? roots[0] : null;
			// a statement or proof keeps its block only where the merged text keeps every part of it the document needs
			if (!leaf(at) && !keepsAll(at, only?.tagName === at.tagName ? only : n.content)) return void marked.push(...b.ids.map((id) => ({ id, src: b.src })));
			// the block keeps its own element, and so its place, its anchors and its classes, where the merged text is one of its kind
			if (only && only.tagName === at.tagName) at.innerHTML = only.innerHTML;
			else if (leaf(at)) at.replaceWith(n.content);
			else {
				const label = at.querySelector(':scope > .env-label, :scope > summary');
				at.replaceChildren(...(label ? [label] : []), n.content);
			}
		});
		for (const m of marked) {
			const at = holderOf(t, m.src);
			if (!at) continue;
			const ids = (at.dataset.changeAt ?? '').split(/\s+/).filter(Boolean);
			if (!ids.includes(m.id)) at.dataset.changeAt = [...ids, m.id].join(' ');
		}
		return t.innerHTML;
	}

	async function load(p: string, hash: string) {
		const version = ++loadVersion;
		try {
			const fragment = await withChanges(await fetchFragment(p, hash), hash);
			if (version !== loadVersion) return;
			html = fragment;
			error = '';
		} catch (err) {
			if (version !== loadVersion) return;
			error = (err as Error).message;
		}
	}

	$effect(() => {
		if (path && store.hash) void load(path, store.hash);
	});

	async function expand(target: HTMLElement, key: string) {
		const node = store.manifest?.nodes[key];
		if (!node) return;
		const child = document.createElement('div');
		child.className = 'expanded';
		child.innerHTML = await fetchFragment(node.fragment, store.hash);
		target.replaceWith(child);
		await mount(child);
	}

	// An annotation's popup opens from its mark, its margin icon, a list or a link; one controller for the fragment's life, reading the manifest as it stands when a popup opens.
	let popup: Popups | null = null;
	$effect(() => {
		const host = frame;
		if (!host) return;
		const made = popups(() => store.manifest, {
			host,
			onopen: (id) => {
				if (annotations) annotations.open = id;
				margin();
			}
		});
		popup = made;
		if (annotations) {
			annotations.show = (id) => !!el && made.open(el, id);
			annotations.close = () => made.close();
		}
		return () => {
			made.destroy();
			if (popup === made) popup = null;
			closeChooser();
		};
	});

	// The compiled paper's page boundaries, drawn only where they can be known: `p2`, in a document, from the numbers
	// loom read out of the `.aux`. Re-run on a change of setting, and cleared when the setting is not `p2`.
	function pages(root: HTMLElement): void {
		const paged = prefs.format === 'p2';
		markPages(paged ? store.manifest : null, paged ? master : null, root);
	}
	$effect(() => {
		void prefs.format;
		void store.hash;
		if (el && placed !== null) untrack(() => pages(el!));
	});

	/** Wire the fragment as the annotations now stand; nothing here re-renders or re-typesets. */
	function wireComments(root: HTMLElement) {
		rewire(root);
		order(root);
	}

	// a fragment in a pane hides every annotation while its pane does; one outside every pane never does
	const pane = paneOf();
	const hide = $derived(pane ? workspace.hidesNotes(pane.index) : false);

	/** Wire the fragment again: what the manifest decides is read afresh, and nothing already bound is bound twice. */
	function rewire(root: HTMLElement): void {
		const m = store.manifest;
		const filter = annotations;
		wire(root, m, (t, k) => void expand(t, k), (id) => (ui.activeAnnotation = id), {
			master,
			headingLinks,
			margins,
			keyless: standalone,
			comments,
			expand: (trigger, ids) => popup?.toggle(trigger, ids),
			hide,
			shows: filter ? (a) => passes(m, a, filter) : undefined,
			changeState: (id) => {
				const how = acted.map[id];
				if (how) return how === 'kept' ? 'kept' : 'off';
				const c = changeById(m, id);
				return c && filter?.hidden.includes(authorOf(c).id) ? 'off' : 'live';
			}
		});
	}

	/** The annotations and pending changes read here in reading order, for the stepper and the lists: each mark's and each change's in the order they stand, then the annotations on the whole document and the changes drawn nowhere. */
	function order(root: HTMLElement): void {
		const m = store.manifest;
		if (!annotations || !m) return;
		const ids: string[] = [];
		const seen = new Set<string>();
		const add = (id: string) => {
			if (seen.has(id)) return;
			seen.add(id);
			ids.push(id);
		};
		for (const el of root.querySelectorAll<HTMLElement>(`${MARKS}, ${CHANGES}, ${MARKED}`)) {
			if (el.matches(`${CHANGES}, ${MARKED}`)) {
				for (const id of changeIds(el)) if (changeById(m, id)) add(id);
				continue;
			}
			for (const id of idsOf(m, el)) add(id);
		}
		if (master) {
			for (const a of on(m, master)) add(a.id);
			for (const c of changesIn(m, master)) add(c.id);
		}
		if (ids.join(' ') !== annotations.order.join(' ')) annotations.order = ids;
	}

	/** Draw the margin's icons again, a frame from now, once the layout they measure has settled. */
	let marginFrame = 0;
	function margin(): void {
		if (!annotations || marginFrame) return;
		marginFrame = requestAnimationFrame(() => {
			marginFrame = 0;
			if (!el || !gutter || !annotations) return;
			const at = el;
			drawGutter(gutter, at, store.manifest, { open: annotations.open, onpick: (id) => popup?.open(at, id, false) });
		});
	}
	$effect(() => {
		const root = el;
		if (!root || !annotations) return;
		const watch = new ResizeObserver(margin);
		watch.observe(root);
		return () => {
			watch.disconnect();
			cancelAnimationFrame(marginFrame);
			marginFrame = 0;
		};
	});

	/** What the label marks and the order show: every annotation's id, status and place. While it holds, a new manifest re-wires in place; when it moves, the label marks are made again. */
	let wiredKey = '';
	function annotationKey(): string {
		return Object.values(store.manifest?.annotations ?? {})
			.map((a) => `${a.id}:${a.status}:${a.detached ? 1 : 0}:${a.in ?? ''}:${a.version?.at ? 1 : 0}`)
			.join('|');
	}

	// The pane's hiding, the settled control and the filter govern the marks, and the view and the acts just pressed govern the changes: a change of any re-wires the fragment, which puts `hidden` on every mark they leave out, shows each change as it now stands, and remakes the label marks. The marks themselves are the fragment's and stay.
	$effect(() => {
		void hide;
		void ui.showSettled;
		void annotations?.hidden.length;
		void annotations?.todo;
		void annotations?.layer;
		void annotations?.view;
		void acted.map;
		if (!el || placed === null) return;
		const root = el;
		untrack(() => {
			resetComments(root);
			wireComments(root);
			counts();
		});
	});

	/** The corpus's macros and the fragment's own set, which every typeset of it is given. */
	function macros(root: HTMLElement): { defaults: Macro[]; set: Macro[] } {
		const first = root.firstElementChild as HTMLElement | null;
		const setName = macroSet || first?.dataset.macros || '';
		const sets = store.manifest?.macros.sets ?? {};
		return { defaults: store.manifest?.macros.default ?? [], set: setName ? (sets[setName] ?? []) : [] };
	}

	/** Each formula's TeX, kept before MathJax replaces it: a reader's selection across a formula is quoted as that TeX, which is what loom finds in the source (FragmentNotes). */
	function keepTex(root: HTMLElement): void {
		for (const m of root.querySelectorAll<HTMLElement>('.math')) if (m.dataset.tex === undefined) m.dataset.tex = m.textContent ?? '';
	}

	/**
	 * Put markup in the fragment: drawn whole the first time, taken back from a document kept when this one was last left, and patched in place after that.
	 *
	 * A new manifest whose fragment changed by one mark used to replace every element of a whole paper and typeset all its formulas again; a patch replaces the blocks that changed and typesets only those.
	 */
	async function place(root: HTMLElement, h: string): Promise<void> {
		if (h === placed) return;
		if (placed === null) {
			const back = cacheable() ? take(keepKey()) : undefined;
			if (!back) return draw(root, h);
			root.replaceChildren(back.nodes);
			placed = back.html;
			tree = null;
			await restored(root);
			if (h === placed) return;
		}
		if (!(await patched(root, placed, h))) draw(root, h);
	}

	/** The reader's place while markup already drawn is changed under them (`hold`): one at a time, the newest change's. */
	let holding: Hold | null = null;
	function holdPlace(root: HTMLElement): Hold {
		holding?.release();
		holding = hold(root);
		return holding;
	}
	/** How long a place is still held once a change is typeset: long enough for the browser to draw the blocks put in near the screen at their real size. */
	const SETTLE = 500;

	/** Draw the markup whole: parsed, wired and typeset from nothing. Drawn again over markup already there, the reader's place is held. */
	function draw(root: HTMLElement, h: string): void {
		// a drawing waits for its own typesetting; markup already in place keeps the typesetting it has, so a new manifest alone never leaves it waiting
		if (isolatedMacros) mathReady = false;
		const held = placed !== null ? holdPlace(root) : null;
		root.innerHTML = h;
		placed = h;
		tree = null;
		held?.again();
		void mount(root).finally(() => held?.release(SETTLE));
	}

	/** Bring the drawn markup up to `after` by replacing only the blocks that changed (`patch`), then typeset and wire what was put in, holding the reader's place; false when it must be drawn whole. */
	async function patched(root: HTMLElement, before: string, after: string): Promise<boolean> {
		if (isolatedMacros) return false;
		const held = holdPlace(root);
		const done = patch(root, (tree ??= parse(before)), after);
		if (!done) {
			held.release();
			return false;
		}
		const { put } = done;
		placed = after;
		tree = done.tree;
		held.again();
		const version = ++mountVersion;
		for (const b of put) keepTex(b);
		// what is placed in the blocks kept stays, as it does for a new manifest; the blocks put in are wired fresh
		wireComments(root);
		wiredKey = annotationKey();
		pages(root);
		counts();
		held.again();
		const { defaults, set } = macros(root);
		for (const b of put) {
			if (version !== mountVersion) return true;
			await typeset(b, defaults, set);
		}
		onmounted?.(root);
		counts();
		held.release(SETTLE);
		return true;
	}

	/** A kept document back in the fragment: wired again, and any formula a typesetting cut short when it was left set now. */
	async function restored(root: HTMLElement): Promise<void> {
		const version = ++mountVersion;
		wireComments(root);
		wiredKey = annotationKey();
		pages(root);
		counts();
		const { defaults, set } = macros(root);
		if (root.querySelector('.math:not(:has(mjx-container))')) await typeset(root, defaults, set);
		if (version !== mountVersion) return;
		onmounted?.(root);
		counts();
		// a frame later: a kept document is back before the pane has begun putting the reader where it was left, which would otherwise undo the arrival
		if (request() !== arrived().at) requestAnimationFrame(() => void arrive());
	}

	/** A new manifest with the markup unchanged: the wiring is read afresh, and the comments controller and the slots are made again only when the annotations moved. Nothing is typeset, and nothing already placed is taken out, so the box a reader acted in stays open on its mark. */
	function refresh(root: HTMLElement): void {
		const key = annotationKey();
		if (key !== wiredKey) {
			wiredKey = key;
			resetComments(root);
			wireComments(root);
			onmounted?.(root);
		} else {
			rewire(root);
			order(root);
		}
		counts();
	}

	/** Whether this fragment's document can be kept when it goes: not a comparison's or a preview's, which typeset with macros of their own. */
	const cacheable = (): boolean => !isolatedMacros && !previewMacros;
	/** What the kept markup was drawn and typeset for. */
	const keepKey = (): string => JSON.stringify([path, macroSet, master, margins, headingLinks, standalone]);

	// The document is kept when the fragment goes, typeset, so coming back to it -- a tab, a narrow layout's other pane, reading after the graph -- is a re-wire rather than a fresh draw.
	onDestroy(() => {
		holding?.release();
		const root = el;
		if (!root || placed === null || !cacheable()) return;
		popup?.close();
		resetComments(root);
		for (const b of root.querySelectorAll('.page-break')) b.remove();
		const nodes = document.createDocumentFragment();
		nodes.append(...root.childNodes);
		keep(keepKey(), { html: placed, nodes });
	});

	async function mount(root: HTMLElement) {
		const version = ++mountVersion;
		keepTex(root);
		wireComments(root);
		if (root === el) wiredKey = annotationKey();
		pages(root);
		// counted as soon as the marks are wired, not after the mathematics is set: the header is about what is in the
		// document, and a reader should not wait on MathJax to be told how much of it is annotated
		counts();
		const { defaults, set } = macros(root);
		const id = target();
		const landing = id ? root.querySelector<HTMLElement>(`[id="${CSS.escape(id)}"]`) : null;
		// a long document typesets the part the reader lands on first, and everything above it, before revealing and scrolling there
		if (isolatedMacros) {
			try {
				const { typesetScoped } = await import('$lib/math/scoped');
				if (version !== mountVersion || root !== el) return;
				await typesetScoped(root, previewMacros ?? set);
				if (version !== mountVersion || root !== el) return;
				mathReady = true;
			} catch (err) {
				if (version === mountVersion) error = `Could not render accepted mathematics: ${(err as Error).message}`;
				return;
			}
		} else {
			await typeset(root, defaults, set, landing);
		}
		onmounted?.(root);
		// the header counts what is in the fragment, which is only knowable once the fragment is wired
		counts();
		if (request() !== arrived().at) arrive();
	}

	/** The browser cannot honour `location.hash` for an element that did not exist at navigation time, and none of a fragment's elements do. Looked up inside this fragment: the same document open twice, or a node beside the document holding it, repeats every id. */
	function scrollToHash() {
		const id = target();
		if (!id || !el) return;
		const at = el.querySelector<HTMLElement>(`[id="${CSS.escape(id)}"]`);
		if (!at) return;
		at.scrollIntoView({ block: 'start' });
		// a place a pane was sent to is marked briefly, so the eye is told where it arrived (plan 0.14)
		if (anchor) flash(at);
	}

	/** Go where the item names: its place, and the annotation it names, its popup open at its mark. */
	async function arrive() {
		arrived().at = request();
		// the pane stops putting the reader back where the item was left: this request names where to go
		el?.dispatchEvent(new CustomEvent('arrive', { bubbles: true }));
		scrollToHash();
		const id = note;
		if (!id || !el) return;
		// a link that names a settled annotation is a request to see it: the settled control comes on for the sitting, as the view menu turns it, and the re-wire it causes is waited for, since a settled annotation with no mark of its own has no label mark until then
		if (settled(store.manifest?.annotations[id]) && !ui.showSettled) {
			ui.showSettled = true;
			await tick();
			if (!el || note !== id) return;
		}
		const at = el.querySelector<HTMLElement>(`:is(${MARKS})[data-annotation~="${CSS.escape(id)}"]`);
		if (!at || !popup) return;
		if (popup.current() !== id) popup.open(el, id);
		else at.scrollIntoView({ block: 'center' });
		flash(at);
	}

	// New markup is placed: drawn, taken back, or patched (`place`).
	$effect(() => {
		const h = html;
		const root = el;
		if (h && root) untrack(() => void place(root, h));
	});

	// What the wiring is built from: a new manifest, or a change of what the caller wires for, re-wires without typesetting.
	$effect(() => {
		void [store.manifest, master, headingLinks, margins, standalone, comments];
		const root = el;
		if (root) untrack(() => placed !== null && refresh(root));
	});

	// What the fragment is typeset with: a change draws it again.
	let typesetWith = '';
	$effect(() => {
		const key = JSON.stringify([macroSet, previewMacros ?? null, isolatedMacros]);
		const root = el;
		untrack(() => {
			if (typesetWith && key !== typesetWith && root && placed !== null) draw(root, html);
			typesetWith = key;
		});
	});

	// A contents entry on the page already changes only the hash, so nothing re-mounts and the browser will not scroll to an element the fragment created after navigation.
	$effect(() => {
		// a new request, and only a new one: new markup for the same request (the text edited, the manifest refreshed) is the mount's, which leaves the reader where they are
		const at = request();
		untrack(() => {
			if (html && el && at && at !== arrived().at) void arrive();
		});
	});

	onMount(() => {});

	/** Whether anything in this fragment carries an annotation, said as soon as the marks are wired; and the margin drawn again. */
	function counts(): void {
		if (!el) return;
		if (annotations) annotations.ready = el.querySelectorAll(`mark.annotation[data-annotation], .annotation-block[data-annotation], ${CHANGES}, [data-change-at]`).length > 0;
		margin();
	}
	$effect(() => {
		const a = annotations;
		return () => {
			if (a) a.ready = false;
		};
	});
	// the open annotation's icon is ringed
	$effect(() => {
		void annotations?.open;
		untrack(margin);
	});

	$effect(() => {
		const m = store.manifest;
		counts();
		// a change kept or discarded is shown so until the manifest no longer lists it
		untrack(() => prune(m));
	});
</script>

{#if error}
	<p class="problem">Fragment unavailable: {error}</p>
{:else}
	<div class="framed" bind:this={frame}>
		<div
			class="fragment"
			class:read={margins}
			class:math-pending={isolatedMacros && !mathReady}
			class:show-settled={ui.showSettled}
			class:changes-markup={!!annotations && annotations.layer !== 'annotations' && annotations.view === 'markup'}
			class:changes-final={!!annotations && annotations.layer !== 'annotations' && annotations.view === 'final'}
			class:changes-off={!!annotations && annotations.layer === 'annotations'}
			aria-busy={isolatedMacros && !mathReady}
			bind:this={el}
			tabindex="-1"
			role="region"
			aria-label="the document"
		></div>
		{#if annotations}<div class="ann-gutter" bind:this={gutter} data-testid="margin"></div>{/if}
	</div>
{/if}

<style>
	/* A comparison typesets with its own macro set, and half-typeset TeX is worse to look at than a held frame. */
	.fragment.math-pending {
		visibility: hidden;
	}
	.fragment.math-pending::before {
		content: 'Rendering comparison…';
		display: block;
		visibility: visible;
		font-family: var(--sans);
		color: var(--ink-soft);
	}
	.framed {
		position: relative;
	}
	/* Focusable so a click in it gives it the keys that scroll it. A browser rings it once a key is pressed, and around a document taller than the window the ring is two blue rules down the text's edges. */
	.fragment:focus {
		outline: none;
	}
</style>
