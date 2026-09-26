<script lang="ts">
	// A node's toolbar (plan 0.16, the table of the final design): the annotating tools on the bar, as a work's pages have them; under *view*, `show all annotations` and `show settled annotations` with their keys, then `open its context beside`, which opens what the node is in and rests on in the other pane, and `show verbatim code`, naming the reading a click gives.
	import { store } from '$lib/manifest/client.svelte';
	import type { Item } from '../item';
	import { nodeState } from '../state.svelte';
	import { workspace } from '../store.svelte';
	import ItemToolbar from '../ItemToolbar.svelte';
	import ToolbarItem from '../ToolbarItem.svelte';
	import ToolPair from '$lib/pdf/ToolPair.svelte';
	import { ui } from '$lib/ui.svelte';
	import { can } from '$lib/write';
	import { settledOn } from '$lib/annotations';

	let { item, name }: { item: Item; name: string } = $props();

	const node = $derived(store.manifest?.nodes[item.id]);
	const held = $derived(nodeState(item));
	// the settled control is offered wherever there is something for it to draw, so a node whose every annotation is settled — nothing drawn at rest — can still show them (15.2.5)
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

{#snippet tools()}<ToolPair holder={held} of={name} />{/snippet}

{#if node}
	<ItemToolbar {name} bar={writes ? tools : undefined} on={held.notes.allOpen || ui.showSettled || held.verbatim}>
		{#snippet view()}
			{#if held.notes.ready}
				<ToolbarItem
					label={held.notes.allOpen ? 'hide all annotations' : 'show all annotations'}
					name="{held.notes.allOpen ? 'hide all annotations' : 'show all annotations'} in {name}"
					key={held.notes.allOpen ? 'h' : 'e'}
					checked={held.notes.allOpen}
					testid="toggle-annotations"
					onclick={() => held.notes.toggle()}
				/>
			{/if}
			{#if held.notes.ready || anySettled}
				<ToolbarItem
					label={ui.showSettled ? 'hide settled annotations' : 'show settled annotations'}
					name="{ui.showSettled ? 'hide settled' : 'show settled'} annotations in {name}"
					key="s"
					checked={ui.showSettled}
					testid="toggle-settled"
					onclick={() => (ui.showSettled = !ui.showSettled)}
				/>
			{/if}
			{#if held.notes.ready || anySettled}<hr />{/if}
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
