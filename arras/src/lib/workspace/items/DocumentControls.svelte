<script lang="ts">
	// A document's toolbar: the annotating bar (Annotate, Comment, the format menu and Undo and Redo where a publisher serves writes, with the hint beneath saying what the tool in hand does; the stepper, Comments and Notes), then **history ▾** where the document has one; under *view*, `show settled annotations` and its key, which `s` does from inside the document. Its compiled PDF opens from its row in the tree. A version (a landmark) has the history alone, and on its bar its own controls (`VersionControls`): older and newer, live text, compare with now, restore; a closed or context-only agent document has none of these.
	import { store } from '$lib/manifest/client.svelte';
	import { isLandmark, type Item } from '../item';
	import { historyOf } from '../history';
	import HistoryMenu from '../HistoryMenu.svelte';
	import VersionControls from '../VersionControls.svelte';
	import { documentState } from '../state.svelte';
	import ItemToolbar from '../ItemToolbar.svelte';
	import ToolbarItem from '../ToolbarItem.svelte';
	import AnnotateBar from '$lib/review/AnnotateBar.svelte';
	import { hand, hintFor } from '$lib/review/annotating.svelte';
	import { ui } from '$lib/ui.svelte';
	import { can } from '$lib/write';
	import { settledIn } from '$lib/annotations';

	let { item, name }: { item: Item; name: string } = $props();

	const m = $derived(store.manifest!);
	const master = $derived(isLandmark(m, item.id) ? undefined : m.masters.find((x) => x.path === item.id));
	const notes = $derived(documentState(item).notes);
	const history = $derived(historyOf(m, item.id));
	// a landmark of a live draft: the way back to its live text
	const draft = $derived(history?.of === 'draft' && history.at ? history.draft : '');
	// the settled control is offered wherever there is something for it to draw, so a document whose every annotation is settled can still show them
	const anySettled = $derived(!!master && settledIn(m, master.path));

	// the tools write, so a corpus served without a write API does not offer them
	let writes = $state(false);
	$effect(() => {
		void can('annotate').then((ok) => (writes = ok));
	});
</script>

{#snippet tools()}<AnnotateBar {notes} of={name} {writes} />{/snippet}
{#snippet versions()}<HistoryMenu {item} {name} divided={(!!master && !master.closed && !master.context_only) || !!draft} />{/snippet}
{#snippet live()}<VersionControls {item} {draft} />{/snippet}

{#if master && !master.closed && !master.context_only}
	<ItemToolbar {name} bar={tools} history={history ? versions : undefined} on={ui.showSettled} hint={writes ? hintFor(m, notes, hand.value) : ''}>
		{#snippet view()}
			{#if notes.ready || anySettled}
				<!-- Settled annotations are hidden at rest; this shows them faintly, for the sitting, on every document and node. -->
				<ToolbarItem
					label={ui.showSettled ? 'hide settled annotations' : 'show settled annotations'}
					name="{ui.showSettled ? 'hide settled' : 'show settled'} annotations in {name}"
					key="s"
					checked={ui.showSettled}
					testid="toggle-settled"
					onclick={() => (ui.showSettled = !ui.showSettled)}
				/>
			{/if}
		{/snippet}
	</ItemToolbar>
{:else}
	<ItemToolbar {name} bar={draft ? live : undefined} history={history ? versions : undefined} />
{/if}
