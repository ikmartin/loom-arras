<script lang="ts">
	import type { Annotations } from './shown.svelte';
	import type { Macro } from '$lib/manifest/types';
	import { onDestroy, onMount, tick, untrack } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import { card, resetComments, settled, wire, type CommentSlot } from '$lib/fragments/mount';
	import { flash } from '$lib/travel/travel';
	import { markPages } from '$lib/fragments/pages';
	import { typeset } from '$lib/math/mathjax';
	import { ui } from '$lib/ui.svelte';
	import { page } from '$app/state';
	import { prefs } from '$lib/prefs.svelte';
	import { sessionView } from '$lib/sessions/sessions.svelte';
	import { paneOf } from '$lib/workspace/state.svelte';
	import { workspace } from '$lib/workspace/store.svelte';
	import { inlineComments, triggerFor, type InlineComments } from './expand';
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
		authoring = true,
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
		/** Shared state for a rail that offers to open every annotation: this fragment registers the actions on it. */
		annotations?: Annotations;
		/** A document that carries no identity: its own references are already in-page anchors, and nothing in it is a key. */
		standalone?: boolean;
		comments?: (key: string) => CommentSlot[];
		/** Whether this is the corpus's own text. `inline` is the Authoring View's alone (plan 0.13 §7): a cited work's rendering is read, not written, and opens floating under that setting. */
		authoring?: boolean;
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
	let mountVersion = 0;
	let loadVersion = 0;

	async function load(p: string, hash: string) {
		const version = ++loadVersion;
		if (isolatedMacros) mathReady = false;
		try {
			const fragment = await fetchFragment(p, hash);
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

	// comments shown in place are opened by the marks and counts this fragment wires; the controller lives as long as the fragment does
	let inline: InlineComments | null = null;
	$effect(() => () => inline?.destroy());

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

	/** Wire the fragment for where comments currently stand; nothing here re-renders or re-typesets.
	 *
	 * The setting it was wired for is left on the element. A fragment mounts before the stored preferences are read, so it is wired once for the default and again when they arrive, and "which placement is live" is otherwise only knowable from a closure.
	 */
	function wireComments(root: HTMLElement) {
		root.dataset.commentsWired = prefs.comments;
		// a manifest refresh re-wires, and the one that follows a reply must not shut the box the reply was written in
		const was = inline?.current() ?? null;
		inline?.destroy();
		// `floating` and `inline` both open in the text; only where the box stands differs, which is the controller's
		// own business. `hover` was a third mode and is gone: a box the pointer brought up could not be read without
		// holding the pointer still, and could not be clicked into at all (plan 0.13 §7).
		const inPlace = prefs.comments === 'inline' || prefs.comments === 'floating';
		inline = inPlace && store.manifest ? inlineComments(() => store.manifest, floats()) : null;
		const opened = inline;
		rewire(root);
		const trigger = was && opened ? triggerFor(root, was) : null;
		if (trigger && opened) opened.toggle(trigger, (trigger.dataset.annotation ?? '').split(/\s+/).filter(Boolean));
	}

	const floats = (): boolean => prefs.comments === 'floating' || !authoring;
	// a fragment in a pane hides every annotation while its pane does; one outside every pane never does
	const pane = paneOf();
	const hide = $derived(pane ? workspace.hidesNotes(pane.index) : false);

	/** Wire the fragment again under the comments controller it has: what the manifest decides is read afresh, and nothing already bound is bound twice. */
	function rewire(root: HTMLElement): void {
		const opened = inline;
		wire(root, store.manifest, (t, k) => void expand(t, k), (id) => (ui.activeAnnotation = id), {
			master,
			headingLinks,
			margins,
			keyless: standalone,
			comments,
			expand: opened ? (trigger, ids) => opened.toggle(trigger, ids) : undefined,
			floating: floats(),
			hide
		});
	}

	/** What the comments controller and the slots show: every annotation's id, status and text. While it holds, a new manifest re-wires in place; when it moves, the controller and the slots are made again. */
	let wiredKey = '';
	function annotationKey(): string {
		return Object.values(store.manifest?.annotations ?? {})
			.map((a) => `${a.id}:${a.status}:${a.discarded ? 1 : 0}:${a.detached ? 1 : 0}:${a.in ?? ''}:${a.body_html}`)
			.join('|');
	}

	// Changing where comments stand used to re-key the fragment, which re-rendered the HTML and re-typeset every
	// formula in it: about 800ms of stall on a whole paper, for a setting that moves boxes around. The marks read the
	// live options, so the slots are taken out, put back the other way, and refilled.
	//
	// Only on a real change. The mount wires the fragment for the setting it has, and a re-wire tears down the
	// controller: firing once more when typesetting finishes closed a comment the reader had already opened.
	let wiredFor: string | null = null;
	$effect(() => {
		const mode = prefs.comments;
		// `wiredFor` is set as the fragment is wired, before its mathematics is typeset, so a change of placement is
		// answered at once rather than waiting on a document that takes seconds to set.
		if (!el || wiredFor === null || mode === wiredFor) return;
		wiredFor = mode;
		resetComments(el);
		wireComments(el);
		onmounted?.(el);
	});

	// The session filter, the pane's hiding and the settled control govern the marks: a change of any re-wires the fragment, which puts `hidden` on every mark whose annotation is not drawn and remakes the label marks from what is admitted. The marks themselves are the fragment's and stay.
	$effect(() => {
		void hide;
		void sessionView.view;
		void sessionView.selected;
		void sessionView.showClosed;
		void ui.showSettled;
		if (!el || wiredFor === null) return;
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

	/** Draw the markup whole: parsed, wired and typeset from nothing. */
	function draw(root: HTMLElement, h: string): void {
		root.innerHTML = h;
		placed = h;
		tree = null;
		void mount(root);
	}

	/** Bring the drawn markup up to `after` by replacing only the blocks that changed (`patch`), then typeset and wire what was put in; false when it must be drawn whole. */
	async function patched(root: HTMLElement, before: string, after: string): Promise<boolean> {
		if (isolatedMacros) return false;
		const done = patch(root, (tree ??= parse(before)), after);
		if (!done) return false;
		const { put } = done;
		placed = after;
		tree = done.tree;
		const version = ++mountVersion;
		for (const b of put) keepTex(b);
		// what is placed in the blocks kept stays, as it does for a new manifest; the blocks put in are wired fresh
		wireComments(root);
		wiredKey = annotationKey();
		pages(root);
		counts();
		const { defaults, set } = macros(root);
		for (const b of put) {
			if (version !== mountVersion) return true;
			await typeset(b, defaults, set);
		}
		onmounted?.(root);
		counts();
		return true;
	}

	/** A kept document back in the fragment: wired again, and any formula a typesetting cut short when it was left set now. */
	async function restored(root: HTMLElement): Promise<void> {
		const version = ++mountVersion;
		wireComments(root);
		wiredFor = prefs.comments;
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
			wireComments(root);
			onmounted?.(root);
		} else rewire(root);
		counts();
	}

	/** Whether this fragment's document can be kept when it goes: not a comparison's or a preview's, which typeset with macros of their own. */
	const cacheable = (): boolean => !isolatedMacros && !previewMacros;
	/** What the kept markup was drawn and typeset for. */
	const keepKey = (): string => JSON.stringify([path, macroSet, master, margins, headingLinks, standalone]);

	// The document is kept when the fragment goes, typeset, so coming back to it -- a tab, a narrow layout's other pane, reading after the graph -- is a re-wire rather than a fresh draw.
	onDestroy(() => {
		const root = el;
		if (!root || placed === null || !cacheable()) return;
		inline?.destroy();
		inline = null;
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
		wiredFor = prefs.comments;
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

	/** Go where the item names: its place, and the annotation it names, open at its mark — or, with comments in the gutter, its card. */
	async function arrive() {
		arrived().at = request();
		// the pane stops putting the reader back where the item was left: this request names where to go
		el?.dispatchEvent(new CustomEvent('arrive', { bubbles: true }));
		scrollToHash();
		const id = note;
		if (!id || !el) return;
		// a link that names a settled annotation is a request to see it: the settled control comes on for the sitting, as `s` would turn it, and the re-wire it causes is waited for, since a settled annotation with no mark of its own has no label mark until then
		if (settled(store.manifest?.annotations[id]) && !ui.showSettled) {
			ui.showSettled = true;
			await tick();
			if (!el || note !== id) return;
		}
		if (inline) {
			const at = triggerFor(el, [id]);
			if (!at) return;
			if (!inline.current()?.includes(id)) inline.toggle(at, [id]);
			at.scrollIntoView({ block: 'center' });
			flash(at);
			return;
		}
		const box = card(el, id);
		if (!box) return;
		ui.activeAnnotation = id;
		box.scrollIntoView({ block: 'center' });
		flash(box);
	}

	// New markup is placed: drawn, taken back, or patched (`place`).
	$effect(() => {
		const h = html;
		const root = el;
		if (h && root) untrack(() => void place(root, h));
	});

	// What the wiring is built from: a new manifest, or a change of what the caller wires for, re-wires without typesetting. The comments setting has an effect of its own, above.
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

	/** How many places in this fragment carry an annotation: marked phrases and blocks, and the labels of results whose annotations have no mark. */
	let marks = $state(0);
	let allOpen = $state(false);
	// What a rail outside this component needs in order to offer the same two actions: the actions themselves, whether there is anything to act on, and which way the control should read.
	$effect(() => {
		const a = annotations;
		if (!a) return;
		a.expand = expandAll;
		a.collapse = hideAll;
		a.ready = marks > 0;
		return () => {
			a.ready = false;
		};
	});
	$effect(() => {
		if (annotations) annotations.allOpen = allOpen;
	});
	function counts(): void {
		if (!el) return;
		marks = el.querySelectorAll('mark.annotation[data-annotation], .annotation-block[data-annotation]').length;
	}

	function expandAll(): void {
		if (!el || !inline) return;
		inline.expandAll(el);
		allOpen = true;
	}

	function hideAll(): void {
		inline?.hideAll();
		allOpen = false;
	}

	// `e`, `h` and `s` only while the content has focus, so they never fire while somebody is typing in a field. Not on a modifier and not global. `s` flips the settled control, which is the sitting's and not this fragment's (ui.svelte.ts); `a`, which hides every annotation, is the pane's (Pane.svelte).
	function keys(e: KeyboardEvent): void {
		const typing = (e.target as HTMLElement | null)?.closest('input, textarea, [contenteditable]');
		if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
		if (e.key === 'e') expandAll();
		else if (e.key === 'h') hideAll();
		else if (e.key === 's') ui.showSettled = !ui.showSettled;
		else return;
		e.preventDefault();
	}

	$effect(() => {
		void store.manifest;
		void prefs.comments;
		// a write lands in the log and comes back on the next poll; the boxes already open must show it
		inline?.refresh();
		counts();
	});
</script>

{#if error}
	<p class="problem">Fragment unavailable: {error}</p>
{:else}
	<!-- A focusable region with three shortcut keys: the rule below models a static div, not a labelled region a reader tabs into deliberately to reach the keys its own header names. -->
	<div class="framed">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="fragment"
			class:read={margins}
			class:math-pending={isolatedMacros && !mathReady}
			class:inline-comments={prefs.comments === 'inline' || prefs.comments === 'floating'}
			class:show-settled={ui.showSettled}
			aria-busy={isolatedMacros && !mathReady}
			bind:this={el}
			tabindex="-1"
			role="region"
			aria-label="the document"
			onkeydown={keys}
		></div>
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
	/* Focusable only so `e`, `h` and `s` reach it. A browser rings it once a key is pressed, and around a document taller than the window the ring is two blue rules down the text's edges. */
	.fragment:focus {
		outline: none;
	}
</style>
