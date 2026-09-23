<script lang="ts">
	// A work's controls (plan 0.13.3 K2–K3), after its views: the tool pair, fit-width, zoom and page — typed into, as a desktop viewer's are — then `PDF`. They stay drawn on the digest and the entry, and on a work with no readable copy, greyed out rather than gone: a row that vanished and came back would move everything after it, and a greyed control still says what it would act on.
	import { store } from '$lib/manifest/client.svelte';
	import { artifactUrl } from '$lib/paths';
	import PdfTools from '$lib/pdf/PdfTools.svelte';
	import type { Item } from '../item';
	import { workState } from '../state.svelte';
	import { workViews } from '../views';

	let { item, name }: { item: Item; name: string } = $props();

	const m = $derived(store.manifest);
	const ref = $derived(m?.references[item.id]);
	const readable = $derived(!ref?.unreadable && !!ref?.artifacts?.pdf);
	// the same test the work itself uses: a view it lacks is the paper
	const onPaper = $derived(!m || !workViews(m, item.id).some((v) => v.id === item.view) || item.view === 'paper');
</script>

{#if ref}
	<PdfTools view={workState(item).pdf} of={name} disabled={!readable || !onPaper} />
	{#if readable}
		<a href={artifactUrl(ref.artifacts!.dir)} target="_blank" rel="noopener" aria-label="PDF of {name}">PDF</a>
	{:else}
		<span class="off" aria-disabled="true" title="No copy of this work is on file">PDF</span>
	{/if}
{/if}

<style>
	.off {
		color: var(--ink-faint);
		opacity: 0.6;
	}
</style>
