<script lang="ts">
	import type { Annotation, Manifest } from '$lib/manifest/types';
	import AnnotationBox from './AnnotationBox.svelte';
	import { ui } from '$lib/ui.svelte';

	let { manifest, keys }: { manifest: Manifest; keys: string[] } = $props();

	const all = $derived(Object.values(manifest.annotations).filter((a) => keys.includes(a.target.key)));
	const roots = $derived(all.filter((a) => a.in_reply_to === null));
	const authors = $derived([...new Set(all.map((a) => a.author.label ?? a.author.id))].sort());
	// derived, not listed: a publisher may use kinds this viewer has never heard of, and one it cannot offer is one
	// nobody can filter by
	const kinds = $derived([...new Set(all.map((a) => a.kind))].sort());
	const visible = $derived(
		roots
			.filter((a) => (ui.showDiscarded || !a.discarded) && (!ui.kindFilter || a.kind === ui.kindFilter) && (!ui.authorFilter || (a.author.label ?? a.author.id) === ui.authorFilter))
			.sort((a, b) => (a.status === b.status ? b.created.localeCompare(a.created) : a.status === 'open' ? -1 : 1))
	);
	const replies = (id: string): Annotation[] => all.filter((a) => a.in_reply_to === id && (ui.showDiscarded || !a.discarded));
	const hiddenDiscarded = $derived(roots.filter((a) => a.discarded).length);
</script>

{#if roots.length}
	<h2>Annotations <span class="muted">{visible.length}{hiddenDiscarded && !ui.showDiscarded ? ` (+${hiddenDiscarded} discarded)` : ''}</span></h2>
	<p class="filters">
		<label>kind <select bind:value={ui.kindFilter}><option value="">all</option>{#each kinds as k (k)}<option value={k}>{k}</option>{/each}</select></label>
		<label>author <select bind:value={ui.authorFilter}><option value="">all</option>{#each authors as a (a)}<option value={a}>{a}</option>{/each}</select></label>
		<label><input type="checkbox" bind:checked={ui.showDiscarded} /> show discarded</label>
	</p>
	<div data-testid="annotation-list">
		{#each visible as a (a.id)}
			<AnnotationBox annotation={a} replies={replies(a.id)} />
		{/each}
	</div>
{/if}

<style>
	.filters label {
		margin-right: 1rem;
		font-size: 0.9rem;
	}
</style>
