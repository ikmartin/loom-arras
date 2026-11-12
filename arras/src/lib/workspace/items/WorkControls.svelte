<script lang="ts">
	// A work's toolbar: on the bar the PDF's (`PdfBar`): annotating as a document is annotated, the PDF's drawing tools, **PDF ▾**, and the page and the zoom, typed into as a desktop viewer's are; under *view*, `show settled annotations`, which the page's marks honour, then `open the PDF`. Off the Paper view, and on a work with no readable copy, they stay drawn and greyed rather than gone (DR-254-ikmartin): a bar that vanished and came back would move everything after it, and a greyed control still says what it would act on.
	import { store } from '$lib/manifest/client.svelte';
	import { artifactUrl } from '$lib/paths';
	import PdfBar from '$lib/pdf/PdfBar.svelte';
	import { hand, hintFor } from '$lib/review/annotating.svelte';
	import { ui } from '$lib/ui.svelte';
	import { can } from '$lib/write';
	import type { Item } from '../item';
	import ItemToolbar from '../ItemToolbar.svelte';
	import ToolbarItem from '../ToolbarItem.svelte';
	import { workState } from '../state.svelte';
	import { currentView, workViews } from '../views';

	let { item, name }: { item: Item; name: string } = $props();

	const m = $derived(store.manifest);
	const ref = $derived(m?.references[item.id]);
	const held = $derived(workState(item));
	const readable = $derived(!ref?.unreadable && !!ref?.artifacts?.pdf);
	// the same test the work itself uses
	const onPaper = $derived(!m || currentView(workViews(m, item.id), item.view) === 'paper');
	const pdfOff = $derived(!readable ? 'No copy of this work is on file' : !onPaper ? 'Open the Text view to open its PDF' : undefined);

	// the tools write, so a corpus served without a write API does not offer them
	let writes = $state(false);
	$effect(() => {
		void can('annotate').then((ok) => (writes = ok));
	});
</script>

{#snippet tools()}<PdfBar view={held.pdf} notes={held.notes} desk={held.desk} of={name} {writes} disabled={!readable || !onPaper} />{/snippet}

{#if ref}
	<ItemToolbar {name} bar={tools} on={ui.showSettled} hint={writes && readable && onPaper ? hintFor(m, held.notes, hand.value) : ''}>
		{#snippet view()}
			<ToolbarItem
				label={ui.showSettled ? 'hide settled annotations' : 'show settled annotations'}
				name="{ui.showSettled ? 'hide settled' : 'show settled'} annotations in {name}"
				checked={ui.showSettled}
				testid="toggle-settled"
				onclick={() => (ui.showSettled = !ui.showSettled)}
			/>
			<hr />
			<ToolbarItem label="open the PDF" name="open the PDF of {name}" href={readable ? artifactUrl(ref.artifacts!.dir) : undefined} off={pdfOff} testid="open-pdf" />
		{/snippet}
	</ItemToolbar>
{/if}
