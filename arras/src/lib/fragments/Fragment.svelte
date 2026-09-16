<script lang="ts">
	import { onMount } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import { wire } from '$lib/fragments/mount';
	import { typeset } from '$lib/math/mathjax';
	import { ui } from '$lib/ui.svelte';

	let { path, macroSet = '' }: { path: string; macroSet?: string } = $props();

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

	async function mount(root: HTMLElement) {
		wire(root, store.manifest, (t, k) => void expand(t, k), (id) => (ui.activeAnnotation = id));
		const first = root.firstElementChild as HTMLElement | null;
		const setName = macroSet || first?.dataset.macros || '';
		const sets = store.manifest?.macros.sets ?? {};
		await typeset(root, store.manifest?.macros.default ?? [], setName ? (sets[setName] ?? []) : []);
	}

	$effect(() => {
		if (html && el) void mount(el);
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
	<div class="fragment" bind:this={el}>{@html html}</div>
{/if}
