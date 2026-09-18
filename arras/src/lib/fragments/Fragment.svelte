<script lang="ts">
	import { onMount } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import { resetComments, wire, type CommentSlot } from '$lib/fragments/mount';
	import { typeset } from '$lib/math/mathjax';
	import { ui } from '$lib/ui.svelte';
	import { page } from '$app/state';
	import { prefs } from '$lib/prefs.svelte';
	import { inlineComments, type InlineComments } from './expand';

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

	/** Wire the fragment for where comments currently stand; nothing here re-renders or re-typesets. */
	function wireComments(root: HTMLElement) {
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
	}

	// Changing where comments stand used to re-key the fragment, which re-rendered the HTML and re-typeset every
	// formula in it: about 800ms of stall on a whole paper, for a setting that moves boxes around. The marks read the
	// live options, so the slots are taken out, put back the other way, and refilled.
	let wired = $state(false);
	$effect(() => {
		const mode = prefs.comments;
		if (!el || !wired) return;
		void mode;
		resetComments(el);
		wireComments(el);
		onmounted?.(el);
	});

	async function mount(root: HTMLElement) {
		wireComments(root);
		const first = root.firstElementChild as HTMLElement | null;
		const setName = macroSet || first?.dataset.macros || '';
		const sets = store.manifest?.macros.sets ?? {};
		const id = decodeURIComponent(location.hash.slice(1));
		const target = id ? document.getElementById(id) : null;
		// a long document typesets the part the reader lands on first, and everything above it, before revealing and scrolling there
		await typeset(root, store.manifest?.macros.default ?? [], setName ? (sets[setName] ?? []) : [], target && root.contains(target) ? target : null);
		onmounted?.(root);
		scrollToHash();
		wired = true;
	}

	/** The browser cannot honour `location.hash` for an element that did not exist at navigation time, and none of a fragment's elements do. */
	function scrollToHash() {
		const id = decodeURIComponent(location.hash.slice(1));
		if (!id) return;
		const target = document.getElementById(id);
		if (target) target.scrollIntoView({ block: 'start' });
	}

	$effect(() => {
		if (html && el) void mount(el);
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
	<div class="fragment" class:read={margins} class:inline-comments={prefs.comments === 'inline' || prefs.comments === 'hover'} bind:this={el}>{@html html}</div>
{/if}
