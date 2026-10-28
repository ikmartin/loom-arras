<script lang="ts">
	// A page loom keeps (plan 0.21.3): the quilt's research state, a reading an agent keeps and the person edits, rendered as a transcript message is. It says who last wrote it and when, and whether it was edited by hand since; a link that names nothing now, or a linked result that has changed since it was written, is said beside it rather than left to be found (P15: a reading is never a source).
	import { store } from '$lib/manifest/client.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import type { Item } from '../item';
	import PageMeta from './PageMeta.svelte';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const page = $derived(item.id === 'state' ? m.research_state : undefined);
</script>

<div class="page item research-state" data-testid="research-state">
	{#if page}
		<PageMeta {page} />
		<Prose html={page.body_html} />
	{:else}
		<p class="muted">This quilt has no research state yet; an agent writes one with <code>loom write state</code>.</p>
	{/if}
</div>
