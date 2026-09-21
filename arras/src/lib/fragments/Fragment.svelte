<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import { resetComments, wire, type CommentSlot } from '$lib/fragments/mount';
	import { markPages } from '$lib/fragments/pages';
	import { typeset } from '$lib/math/mathjax';
	import { ui } from '$lib/ui.svelte';
	import { page } from '$app/state';
	import { prefs } from '$lib/prefs.svelte';
	import { inlineComments, triggerFor, type InlineComments } from './expand';

	let {
		path,
		macroSet = '',
		isolatedMacros = false,
		master = '',
		headingLinks = false,
		margins = false,
		standalone = false,
		comments,
		onmounted
	}: {
		path: string;
		macroSet?: string;
		/** Accepted review text uses its saved preamble without modifying the live MathJax instance. */
		isolatedMacros?: boolean;
		master?: string;
		headingLinks?: boolean;
		margins?: boolean;
		/** A document that carries no identity: its own references are already in-page anchors, and nothing in it is a key. */
		standalone?: boolean;
		comments?: (key: string) => CommentSlot[];
		onmounted?: (root: HTMLElement) => void;
	} = $props();

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
		const inPlace = prefs.comments === 'inline' || prefs.comments === 'hover';
		inline = inPlace && store.manifest ? inlineComments(store.manifest, prefs.comments === 'hover') : null;
		const opened = inline;
		wire(root, store.manifest, (t, k) => void expand(t, k), (id) => (ui.activeAnnotation = id), {
			master,
			headingLinks,
			margins,
			keyless: standalone,
			comments,
			expand: opened ? (trigger, ids) => opened.toggle(trigger, ids) : undefined,
			hover: prefs.comments === 'hover'
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

	async function mount(root: HTMLElement) {
		const version = ++mountVersion;
		wireComments(root);
		wiredFor = prefs.comments;
		const first = root.firstElementChild as HTMLElement | null;
		const setName = macroSet || first?.dataset.macros || '';
		const sets = store.manifest?.macros.sets ?? {};
		const id = decodeURIComponent(location.hash.slice(1));
		const target = id ? document.getElementById(id) : null;
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
			await typeset(root, store.manifest?.macros.default ?? [], setName ? (sets[setName] ?? []) : [], target && root.contains(target) ? target : null);
		}
		onmounted?.(root);
		scrollToHash();
	}

	/** The browser cannot honour `location.hash` for an element that did not exist at navigation time, and none of a fragment's elements do. */
	function scrollToHash() {
		const id = decodeURIComponent(location.hash.slice(1));
		if (!id) return;
		const target = document.getElementById(id);
		if (target) target.scrollIntoView({ block: 'start' });
	}

	// Mounting reads the comments setting, and an effect that tracked it re-mounted the whole fragment on every change of placement: a second wiring, a pass of MathJax over every formula, and a jump back to the URL's anchor. The effect above answers that setting; this one follows the markup and what the wiring is built from.
	$effect(() => {
		void [store.manifest, macroSet, isolatedMacros, master, headingLinks, margins, standalone, comments];
		const root = el;
		if (html && root) untrack(() => void mount(root));
	});

	// A contents entry on the page already changes only the hash, so nothing re-mounts and the browser will not scroll to an element the fragment created after navigation.
	$effect(() => {
		const hash = page.url.hash;
		if (html && el && hash) scrollToHash();
	});

	onMount(() => {});

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
	<div class="fragment" class:read={margins} class:math-pending={isolatedMacros && !mathReady} class:inline-comments={prefs.comments === 'inline' || prefs.comments === 'hover'} aria-busy={isolatedMacros && !mathReady} bind:this={el}>{@html html}</div>
{/if}

<style>
	.fragment.math-pending { visibility: hidden; }
	.fragment.math-pending::before { content: 'Rendering comparison…'; display: block; visibility: visible; font-family: var(--sans); color: var(--ink-soft); }
</style>
