<script lang="ts">
	// The version an annotation was written on, opened in its popup: the key's text as it was, typeset, with every annotation written on that version drawn in its own look and this one open. A mark in it opens that annotation's popup (`onmark`).
	import { store } from '$lib/manifest/client.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import { wire } from '$lib/fragments/mount';
	import { typeset } from '$lib/math/mathjax';

	let { path, focus, onmark }: { path: string; focus: string; onmark?: (trigger: HTMLElement, ids: string[]) => void } = $props();

	let el = $state<HTMLElement | null>(null);
	let error = $state('');

	$effect(() => {
		const root = el;
		const p = path;
		if (!root || !p) return;
		let gone = false;
		void (async () => {
			try {
				const html = await fetchFragment(p, store.hash);
				if (gone) return;
				root.innerHTML = html;
				const m = store.manifest;
				wire(root, m, () => {}, () => {}, { keyless: true, expand: onmark ? (trigger, ids) => onmark(trigger, ids) : undefined });
				for (const mark of root.querySelectorAll<HTMLElement>(`[data-annotation~="${CSS.escape(focus)}"]`)) mark.classList.add('open');
				const first = root.firstElementChild as HTMLElement | null;
				const set = first?.dataset.macros ? (m?.macros.sets?.[first.dataset.macros] ?? []) : [];
				await typeset(root, m?.macros.default ?? [], set);
			} catch (err) {
				if (!gone) error = (err as Error).message;
			}
		})();
		return () => {
			gone = true;
		};
	});
</script>

{#if error}
	<p class="said" data-testid="version-said">That version could not be read: {error}</p>
{:else}
	<div class="fragment version-view" bind:this={el} data-testid="version-view"></div>
{/if}

<style>
	.version-view {
		max-height: 240px;
		overflow: auto;
		padding: 6px 8px;
		font-family: var(--body-face);
		font-size: 13.5px;
		line-height: 1.5;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: 6px;
	}
	.said {
		margin: 0;
		font-size: 12px;
		color: var(--ink-soft);
	}
</style>
