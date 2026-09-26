<script lang="ts">
	// A work's toolbar (plan 0.16, the table of the final design): the tool pair, fit-width, zoom and page on the bar — typed into, as a desktop viewer's are; under *view*, `show settled annotations`, which the page's marks honour, then `open the PDF`. Off the Paper view, and on a work with no readable copy, they stay drawn and greyed rather than gone (DR-254-ikmartin): a bar that vanished and came back would move everything after it, and a greyed control still says what it would act on. The page has no keys, so no line names one.
	import { store } from '$lib/manifest/client.svelte';
	import { artifactUrl } from '$lib/paths';
	import PdfTools from '$lib/pdf/PdfTools.svelte';
	import { ui } from '$lib/ui.svelte';
	import type { Item } from '../item';
	import ItemToolbar from '../ItemToolbar.svelte';
	import ToolbarItem from '../ToolbarItem.svelte';
	import { workState } from '../state.svelte';
	import { currentView, workViews } from '../views';

	let { item, name }: { item: Item; name: string } = $props();

	const m = $derived(store.manifest);
	const ref = $derived(m?.references[item.id]);
	const readable = $derived(!ref?.unreadable && !!ref?.artifacts?.pdf);
	// the same test the work itself uses
	const onPaper = $derived(!m || currentView(workViews(m, item.id), item.view) === 'paper');
	const pdfOff = $derived(!readable ? 'No copy of this work is on file' : !onPaper ? 'Open the Paper view to open its PDF' : undefined);
</script>

{#snippet tools()}<PdfTools view={workState(item).pdf} of={name} disabled={!readable || !onPaper} />{/snippet}

{#if ref}
	<ItemToolbar {name} bar={tools} on={ui.showSettled}>
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
