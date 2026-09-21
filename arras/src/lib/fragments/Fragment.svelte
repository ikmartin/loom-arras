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
	import { stackMargins } from './mount';
	import { hidden } from '$lib/sessions/sessions.svelte';

	let {
		path,
		macroSet = '',
		master = '',
		headingLinks = false,
		margins = false,
		standalone = false,
		comments,
		onmounted
	}: {
		path: string;
		macroSet?: string;
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
	let el: HTMLElement | undefined = $state();

	async function load(p: string, hash: string) {
		try {
			html = await fetchFragment(p, hash);
			error = '';
		} catch (err) {
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
		inline = inPlace && store.manifest ? inlineComments(store.manifest, prefs.comments === 'floating') : null;
		const opened = inline;
		wire(root, store.manifest, (t, k) => void expand(t, k), (id) => (ui.activeAnnotation = id), {
			master,
			headingLinks,
			margins,
			keyless: standalone,
			comments,
			expand: opened ? (trigger, ids) => opened.toggle(trigger, ids) : undefined,
			floating: prefs.comments === 'floating'
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
		wireComments(root);
		wiredFor = prefs.comments;
		// counted as soon as the marks are wired, not after the mathematics is set: the header is about what is in the
		// document, and a reader should not wait on MathJax to be told how much of it is annotated
		counts();
		const first = root.firstElementChild as HTMLElement | null;
		const setName = macroSet || first?.dataset.macros || '';
		const sets = store.manifest?.macros.sets ?? {};
		const id = decodeURIComponent(location.hash.slice(1));
		const target = id ? document.getElementById(id) : null;
		// a long document typesets the part the reader lands on first, and everything above it, before revealing and scrolling there
		await typeset(root, store.manifest?.macros.default ?? [], setName ? (sets[setName] ?? []) : [], target && root.contains(target) ? target : null);
		onmounted?.(root);
		// the header counts what is in the fragment, which is only knowable once the fragment is wired
		counts();
		if (margins) stackMargins(root);
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
		void [store.manifest, macroSet, master, headingLinks, margins, standalone, comments];
		const root = el;
		if (html && root) untrack(() => void mount(root));
	});

	// A contents entry on the page already changes only the hash, so nothing re-mounts and the browser will not scroll to an element the fragment created after navigation.
	$effect(() => {
		const hash = page.url.hash;
		if (html && el && hash) scrollToHash();
	});

	onMount(() => {});

	/** How many phrases in this fragment carry an annotation, and how many the session selection is keeping out of it. */
	let marks = $state(0);
	let concealed = $state(0);
	let allOpen = $state(false);

	function counts(): void {
		if (!el) return;
		marks = el.querySelectorAll('mark.annotation[data-annotation]').length;
		const m = store.manifest;
		concealed = m ? hidden(m, Object.values(m.annotations ?? {}).filter((a) => !a.in_reply_to && !a.discarded)) : 0;
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
	{#if marks}
		<!-- The content pane's header. A key nobody has been told about does not exist, so the two states sit here as
		     buttons with their keys named, beside the count of what is marked and what the session filter is hiding. -->
		<div class="content-head" data-testid="content-head">
			<button
				type="button"
				class:on={allOpen}
				title="Expand every annotation at its own mark (e)"
				data-testid="expand-all"
				onclick={expandAll}>expand all</button
			>
			<button type="button" title="Close everything open, wherever it is (h)" data-testid="hide-all" onclick={hideAll}
				>hide all</button
			>
			<span class="count" data-testid="content-count">{marks} annotated</span>
			{#if concealed}
				<span class="concealed" data-testid="content-hidden">{concealed} hidden by the session filter</span>
			{/if}
		</div>
	{/if}
	<!-- A focusable region with two shortcut keys: the rule below models a static div, not a labelled region a reader
	     tabs into deliberately to reach the keys its own header names. -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="fragment"
		class:read={margins}
		class:inline-comments={prefs.comments === 'inline' || prefs.comments === 'floating'}
		bind:this={el}
		tabindex="-1"
		role="region"
		aria-label="the document"
		onkeydown={keys}
	>{@html html}</div>
{/if}
