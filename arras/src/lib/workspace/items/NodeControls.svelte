<script lang="ts">
	// A node's controls (plan 0.13.3 N3): the annotating tools, as a work's pages have them; `context`, which opens what the node is in and rests on beside it; `source`, naming the reading a click gives; `annotations`.
	import { store } from '$lib/manifest/client.svelte';
	import type { Item } from '../item';
	import { nodeState } from '../state.svelte';
	import { workspace } from '../store.svelte';
	import ToolPair from '$lib/pdf/ToolPair.svelte';
	import { can } from '$lib/write';

	let { item, name }: { item: Item; name: string } = $props();

	const node = $derived(store.manifest?.nodes[item.id]);
	const held = $derived(nodeState(item));

	function context(): void {
		const from = workspace.paneOf(`node:${item.id}`);
		workspace.beside({ kind: 'context', id: item.id }, from < 0 ? workspace.focus : from);
	}

	// the tools write, so a corpus served without a write API does not offer them
	let writes = $state(false);
	$effect(() => {
		void can('comment').then((ok) => (writes = ok));
	});
</script>

{#if node}
	{#if writes}<ToolPair holder={held} of={name} /><span class="bar" aria-hidden="true"></span>{/if}
	<button type="button" class="as-link" aria-label="context of {name}" data-testid="open-context" onclick={context}>context</button>
	{#if held.source}
		<button type="button" class="as-link" aria-pressed={held.verbatim} aria-label="{held.verbatim ? 'rendered latex' : 'verbatim code'} of {name}" data-testid="source-toggle" onclick={() => (held.verbatim = !held.verbatim)}
			>{held.verbatim ? 'rendered latex' : 'verbatim code'}</button
		>
	{/if}
	{#if held.notes.ready}
		<button
			type="button"
			class="as-link"
			aria-expanded={held.notes.allOpen}
			aria-label="{held.notes.allOpen ? 'hide all annotations' : 'show all annotations'} in {name}"
			data-testid="toggle-annotations"
			onclick={() => held.notes.toggle()}>{held.notes.allOpen ? 'hide all annotations' : 'show all annotations'}</button
		>
	{/if}
{/if}

<style>
	.bar {
		width: 1px;
		height: 14px;
		background: var(--rule);
	}
</style>
