<script lang="ts">
	// A digest result's locator, `Construction 1.7, p.~13`, with the page made a link to the result on its paper, where every link to it goes (`keyUrl`). Where the result has no paper to open at a page — none filed, or the page another version's — the page is text, since a page in another version is not this place.
	import { store } from '$lib/manifest/client.svelte';
	import { keyUrl } from '$lib/nav';
	import { resultPlace } from '$lib/worklink';

	let { id, locator }: { id: string; locator: string | undefined } = $props();

	const text = $derived((locator ?? '').replace(/~/g, ' '));
	const link = $derived(resultPlace(store.manifest, id) ? keyUrl(store.manifest, id) : '');
	const split = $derived.by(() => {
		const m = text.match(/\b(?:pp?\.|pages?)\s*\d+(?:\s*[–-]\s*\d+)?/i);
		return m && m.index !== undefined ? { before: text.slice(0, m.index), page: m[0], after: text.slice(m.index + m[0].length) } : null;
	});
</script>

{#if link && split}{split.before}<a class="page" href={link} title="open the paper at this page" data-testid="page-link">{split.page}</a>{split.after}{:else}{text}{/if}

<style>
	.page {
		font: inherit;
		color: var(--link);
		background: none;
		text-decoration: none;
		border-bottom: 1px dotted var(--link);
	}
	.page:hover {
		border-bottom-style: solid;
	}
</style>
