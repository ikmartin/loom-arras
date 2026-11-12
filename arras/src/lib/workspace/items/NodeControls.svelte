<script lang="ts">
	// A node's toolbar: the annotating bar, as a document has it; under *view*, `show settled annotations` and its key, then `open its context beside`, which opens what the node is in and rests on in the other pane, and `show verbatim code`, naming the reading a click gives.
	import { store } from '$lib/manifest/client.svelte';
	import type { Item } from '../item';
	import { nodeState } from '../state.svelte';
	import { workspace } from '../store.svelte';
	import ItemToolbar from '../ItemToolbar.svelte';
	import ToolbarItem from '../ToolbarItem.svelte';
	import AnnotateBar from '$lib/review/AnnotateBar.svelte';
	import { hand, hintFor } from '$lib/review/annotating.svelte';
	import { ui } from '$lib/ui.svelte';
	import { can } from '$lib/write';
	import { settledOn } from '$lib/annotations';

	let { item, name }: { item: Item; name: string } = $props();

	const node = $derived(store.manifest?.nodes[item.id]);
	const held = $derived(nodeState(item));
	// the settled control is offered wherever there is something for it to draw, so a node whose every annotation is settled — nothing drawn at rest — can still show them
	const anySettled = $derived(!!store.manifest && !!node && settledOn(store.manifest, [item.id, ...node.proofs]));

	function context(): void {
		const from = workspace.paneOf(`node:${item.id}`);
		workspace.beside({ kind: 'context', id: item.id }, from < 0 ? workspace.focus : from);
	}

	// the tools write, so a corpus served without a write API does not offer them
	let writes = $state(false);
	$effect(() => {
		void can('annotate').then((ok) => (writes = ok));
	});
</script>

{#snippet tools()}<AnnotateBar notes={held.notes} of={name} writes={writes && !node?.external} />{/snippet}

{#if node}
	<ItemToolbar {name} bar={tools} on={ui.showSettled || held.verbatim} hint={writes && !node.external ? hintFor(store.manifest, held.notes, hand.value) : ''}>
		{#snippet view()}
			{#if held.notes.ready || anySettled}
				<ToolbarItem
					label={ui.showSettled ? 'hide settled annotations' : 'show settled annotations'}
					name="{ui.showSettled ? 'hide settled' : 'show settled'} annotations in {name}"
					key="s"
					checked={ui.showSettled}
					testid="toggle-settled"
					onclick={() => (ui.showSettled = !ui.showSettled)}
				/>
				<hr />
			{/if}
			<ToolbarItem label="open its context beside" name="open the context of {name} beside" testid="open-context" onclick={context} />
			{#if held.source}
				<ToolbarItem
					label={held.verbatim ? 'show rendered latex' : 'show verbatim code'}
					name="{held.verbatim ? 'rendered latex' : 'verbatim code'} of {name}"
					checked={held.verbatim}
					testid="source-toggle"
					onclick={() => (held.verbatim = !held.verbatim)}
				/>
			{/if}
		{/snippet}
	</ItemToolbar>
{/if}
