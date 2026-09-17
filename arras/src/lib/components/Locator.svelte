<script lang="ts">
	// A digest result's locator, `Construction 1.7, p.~13`, with the page made a link into the fetched paper when the paper on file is the version the digest was extracted from (book 15.3.7). Otherwise the page is text, since a page in another version is not this place.
	import type { Reference } from '$lib/manifest/types';
	import { digestPageLink } from '$lib/worklink';
	import { pdf } from '$lib/pdf.svelte';

	let { ref, locator }: { ref: Reference | undefined; locator: string | undefined } = $props();

	const text = $derived((locator ?? '').replace(/~/g, ' '));
	const link = $derived(digestPageLink(ref, locator));
	const split = $derived.by(() => {
		const m = text.match(/\b(?:pp?\.|pages?)\s*\d+(?:\s*[–-]\s*\d+)?/i);
		return m && m.index !== undefined ? { before: text.slice(0, m.index), page: m[0], after: text.slice(m.index + m[0].length) } : null;
	});
</script>

{#if link && split}{split.before}<button class="page" onclick={() => pdf.open(link)} title="open the paper at this page" data-testid="page-link">{split.page}</button>{split.after}{:else}{text}{/if}

<style>
	.page {
		font: inherit;
		color: var(--link);
		background: none;
		border: none;
		border-bottom: 1px dotted var(--link);
		padding: 0;
		cursor: pointer;
	}
	.page:hover {
		border-bottom-style: solid;
	}
</style>
