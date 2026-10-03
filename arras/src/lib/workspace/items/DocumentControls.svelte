<script lang="ts">
	// A document's toolbar (plan 0.16, the table of the final design): the annotating tools on the bar where a publisher serves writes; under *view*, `show all annotations` and `show settled annotations` with their keys, then `open the PDF`, the cheap escape from a manual latexmk. `e`, `h` and `s` do what the two annotation lines do from the keyboard, inside the document. A landmark has none.
	import { store } from '$lib/manifest/client.svelte';
	import { dataUrl } from '$lib/paths';
	import { isLandmark, type Item } from '../item';
	import { documentState } from '../state.svelte';
	import ItemToolbar from '../ItemToolbar.svelte';
	import ToolbarItem from '../ToolbarItem.svelte';
	import ToolPair from '$lib/pdf/ToolPair.svelte';
	import { ui } from '$lib/ui.svelte';
	import { can } from '$lib/write';
	import { settledIn } from '$lib/annotations';

	let { item, name }: { item: Item; name: string } = $props();

	const m = $derived(store.manifest!);
	const master = $derived(isLandmark(m, item.id) ? undefined : m.masters.find((x) => x.path === item.id));
	const notes = $derived(documentState(item).notes);
	// the settled control is offered wherever there is something for it to draw, so a document whose every annotation is settled can still show them (15.2.5)
	const anySettled = $derived(!!master && settledIn(m, master.path));

	// the tools write, so a corpus served without a write API does not offer them
	let writes = $state(false);
	$effect(() => {
		void can('annotate').then((ok) => (writes = ok));
	});
</script>

{#snippet tools()}<ToolPair holder={documentState(item)} of={name} />{/snippet}

{#if master && !master.closed && !master.context_only}
	<ItemToolbar {name} bar={writes ? tools : undefined} on={notes.allOpen || ui.showSettled}>
		{#snippet view()}
			{#if notes.ready}
				<ToolbarItem
					label={notes.allOpen ? 'hide all annotations' : 'show all annotations'}
					name="{notes.allOpen ? 'hide all annotations' : 'show all annotations'} in {name}"
					key={notes.allOpen ? 'h' : 'e'}
					checked={notes.allOpen}
					testid="toggle-annotations"
					onclick={() => notes.toggle()}
				/>
			{/if}
			{#if notes.ready || anySettled}
				<!-- Settled annotations are hidden at rest; this shows them faintly, for the sitting, on every document and node (book 15.3.1). -->
				<ToolbarItem
					label={ui.showSettled ? 'hide settled annotations' : 'show settled annotations'}
					name="{ui.showSettled ? 'hide settled' : 'show settled'} annotations in {name}"
					key="s"
					checked={ui.showSettled}
					testid="toggle-settled"
					onclick={() => (ui.showSettled = !ui.showSettled)}
				/>
			{/if}
			{#if notes.ready || anySettled}<hr />{/if}
			<ToolbarItem label="open the PDF" name="open the PDF of {name}" href={master.pdf ? dataUrl(master.pdf) : undefined} off={master.pdf ? undefined : 'This document has no compiled PDF'} testid="open-pdf" />
		{/snippet}
	</ItemToolbar>
{/if}
