<script lang="ts">
	// The line over a page (plan 0.21.3): who last wrote it through loom and when, whether the person has edited it by hand since, and the links it holds that name nothing now or whose result has moved since the write.
	import type { Page } from '$lib/manifest/types';
	import { when } from '$lib/sessions/when';

	let { page }: { page: Page } = $props();

	const tail = $derived.by(() => {
		const moved = page.links.moved.length;
		const broken = page.links.broken.length;
		return [
			page.by && page.when ? when(page.when) : '',
			page.by && page.edited_since ? 'edited since' : '',
			moved ? `${moved} linked ${moved === 1 ? 'result has' : 'results have'} changed since` : '',
			broken ? `${broken} ${broken === 1 ? 'link names' : 'links name'} nothing now` : ''
		].filter(Boolean);
	});
</script>

<p class="page-meta" data-testid="page-meta">
	{#if page.by}written by <span class="who">{page.by.id}</span>{:else}written by hand{/if}{#each tail as part (part)}{' · '}{part}{/each}
</p>

<style>
	.page-meta {
		margin: 0 0 var(--gap-tight);
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-faint);
	}
	.who {
		color: var(--ink-soft);
	}
</style>
