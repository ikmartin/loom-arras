<script lang="ts">
	import type { Annotations } from './shown.svelte';
	import { onMount, untrack } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import { card, resetComments, wire, type CommentSlot } from '$lib/fragments/mount';
	import { flash } from '$lib/travel/travel';
	import { markPages } from '$lib/fragments/pages';
	import { typeset } from '$lib/math/mathjax';
	import { ui } from '$lib/ui.svelte';
	import { page } from '$app/state';
	import { prefs } from '$lib/prefs.svelte';
	import { sessionView } from '$lib/sessions/sessions.svelte';
	import { inlineComments, triggerFor, type InlineComments } from './expand';
	import { stackMargins } from './mount';

	let {
		path,
		macroSet = '',
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
		onmounted
	}: {
		path: string;
		macroSet?: string;
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
		onmounted?: (root: HTMLElement) => void;
	} = $props();

	/** The element the reader is sent to: the pane's own anchor when one is given, else the URL's hash. */
	const target = (): string => (anchor !== undefined ? anchor : decodeURIComponent(location.hash.slice(1)));

	let html = $state('');
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
	$effect(() => {
		const paged = prefs.format === 'p2';
		// Everything it reads: the setting, the manifest the boundaries come from, and the markup they are drawn into.
		// The fragment's HTML arrives after the element does, so an effect that does not read it runs once against an
		// empty div and never again.
		void store.hash;
		void html;
		if (!el) return;
		markPages(paged ? store.manifest : null, paged ? master : null, el);
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
		const floats = prefs.comments === 'floating' || !authoring;
		inline = inPlace && store.manifest ? inlineComments(store.manifest, floats) : null;
		const opened = inline;
		wire(root, store.manifest, (t, k) => void expand(t, k), (id) => (ui.activeAnnotation = id), {
			master,
			headingLinks,
			margins,
			keyless: standalone,
			comments,
			expand: opened ? (trigger, ids) => opened.toggle(trigger, ids) : undefined,
			floating: floats
		});
		const trigger = was && opened ? triggerFor(root, was) : null;
		if (trigger && opened) opened.toggle(trigger, (trigger.dataset.annotation ?? trigger.dataset.comments ?? '').split(/\s+/).filter(Boolean));
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

	// The session filter decides which comments are counted beside a result, so a change of it re-counts them, as a change of placement re-wires them; the marks themselves are the fragment's and stay.
	$effect(() => {
		void sessionView.view;
		void sessionView.selected;
		if (!el || wiredFor === null) return;
		const root = el;
		untrack(() => {
			resetComments(root);
			wireComments(root);
			counts();
		});
	});

	async function mount(root: HTMLElement) {
		const version = ++mountVersion;
		// Each formula's TeX, kept before MathJax replaces it: a reader's selection across a formula is quoted as that TeX, which is what loom finds in the source (FragmentNotes).
		for (const m of root.querySelectorAll<HTMLElement>('.math')) if (m.dataset.tex === undefined) m.dataset.tex = m.textContent ?? '';
		wireComments(root);
		wiredFor = prefs.comments;
		// counted as soon as the marks are wired, not after the mathematics is set: the header is about what is in the
		// document, and a reader should not wait on MathJax to be told how much of it is annotated
		counts();
		const first = root.firstElementChild as HTMLElement | null;
		const setName = macroSet || first?.dataset.macros || '';
		const sets = store.manifest?.macros.sets ?? {};
		const id = target();
		const landing = id ? root.querySelector<HTMLElement>(`[id="${CSS.escape(id)}"]`) : null;
		// a long document typesets the part the reader lands on first, and everything above it, before revealing and scrolling there
		if (isolatedMacros) {
			try {
				const { typesetScoped } = await import('$lib/math/scoped');
				if (version !== mountVersion || root !== el) return;
				await typesetScoped(root, setName ? (sets[setName] ?? []) : []);
				if (version !== mountVersion || root !== el) return;
				mathReady = true;
			} catch (err) {
				if (version === mountVersion) error = `Could not render accepted mathematics: ${(err as Error).message}`;
				return;
			}
		} else {
			await typeset(root, store.manifest?.macros.default ?? [], setName ? (sets[setName] ?? []) : [], landing);
		}
		onmounted?.(root);
		// the header counts what is in the fragment, which is only knowable once the fragment is wired
		counts();
		if (margins) stackMargins(root);
		arrive();
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
	function arrive() {
		scrollToHash();
		const id = note;
		if (!id || !el) return;
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

	// Mounting reads the comments setting, and an effect that tracked it re-mounted the whole fragment on every change of placement: a second wiring, a pass of MathJax over every formula, and a jump back to the URL's anchor. The effect above answers that setting; this one follows the markup and what the wiring is built from.
	$effect(() => {
		void [store.manifest, macroSet, isolatedMacros, master, headingLinks, margins, standalone, comments];
		const root = el;
		if (html && root) untrack(() => void mount(root));
	});

	// A contents entry on the page already changes only the hash, so nothing re-mounts and the browser will not scroll to an element the fragment created after navigation.
	$effect(() => {
		// in a pane, the item's own anchor, its annotation and each reopening; elsewhere the URL's hash
		const at = anchor !== undefined ? `${anchor}\u0000${jump}\u0000${note ?? ''}` : page.url.hash;
		if (html && el && at) untrack(arrive);
	});

	onMount(() => {});

	/** How many places in this fragment carry an annotation: marked phrases and blocks, and the counts beside results whose comments have no mark. */
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
		marks = el.querySelectorAll('mark.annotation[data-annotation], .annotation-block[data-annotation], button.comment-count').length;
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

	// `e` and `h` only while the content has focus, so they never fight the composer. Not on a modifier and not global:
	// a key that works everywhere is a key that fires while somebody is typing.
	function keys(e: KeyboardEvent): void {
		const typing = (e.target as HTMLElement | null)?.closest('input, textarea, [contenteditable]');
		if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
		if (e.key === 'e') expandAll();
		else if (e.key === 'h') hideAll();
		else return;
		e.preventDefault();
	}

	$effect(() => {
		void store.manifest;
		void prefs.comments;
		// a write lands in the log and comes back on the next poll; the boxes already open must show it
		inline?.refresh();
		counts();
		// the margin column is laid out against the nodes, so it is restacked whenever what is in it changes
		if (el && margins) requestAnimationFrame(() => el && stackMargins(el));
	});

	// and whenever the column's own width changes under it, which moves every box in it
	$effect(() => {
		if (!el || !margins) return;
		const watch = new ResizeObserver(() => el && stackMargins(el));
		watch.observe(el);
		return () => watch.disconnect();
	});

	$effect(() => {
		const id = ui.activeAnnotation;
		if (!el) return;
		for (const m of el.querySelectorAll<HTMLElement>('[data-annotation]')) {
			m.classList.toggle('active', !!id && (m.dataset.annotation ?? '').split(/\s+/).includes(id));
		}
	});
</script>

{#if error}
	<p class="problem">Fragment unavailable: {error}</p>
{:else}
	<!-- A focusable region with two shortcut keys: the rule below models a static div, not a labelled region a reader
	     tabs into deliberately to reach the keys its own header names. -->
	<div class="framed">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="fragment"
			class:read={margins}
			class:math-pending={isolatedMacros && !mathReady}
			class:inline-comments={prefs.comments === 'inline' || prefs.comments === 'floating'}
			aria-busy={isolatedMacros && !mathReady}
			bind:this={el}
			tabindex="-1"
			role="region"
			aria-label="the document"
			onkeydown={keys}
		>{@html html}</div>
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
</style>
