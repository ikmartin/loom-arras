<script lang="ts">
	// A document's controls (plan 0.13.3 D3), drawn once in the rail for whichever document is current: the annotating tools, `annotations`, naming what the click gives, the settled control beside it, and `PDF`, the cheap escape from a manual latexmk. `e`, `h` and `s` do what the two annotation controls do from the keyboard, inside the document.
	import { store } from '$lib/manifest/client.svelte';
	import { dataUrl } from '$lib/paths';
	import { isLandmark, type Item } from '../item';
	import { documentState } from '../state.svelte';
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

{#if master}
	{#if writes}<ToolPair holder={documentState(item)} of={name} /><span class="bar" aria-hidden="true"></span>{/if}
	{#if notes.ready}
		<button
			type="button"
			class="as-link"
			aria-expanded={notes.allOpen}
			aria-label="{notes.allOpen ? 'hide all annotations' : 'show all annotations'} in {name}"
			data-testid="toggle-annotations"
			title={notes.allOpen ? 'Close everything open, wherever it is (h)' : 'Open every annotation at its own mark (e)'}
			onclick={() => notes.toggle()}
			>{notes.allOpen ? 'hide all annotations' : 'show all annotations'}<span class="chev" class:down={notes.allOpen} aria-hidden="true"></span></button
		>
	{/if}
	{#if notes.ready || anySettled}
		<!-- Settled annotations are hidden at rest; this shows them faintly, for the sitting, on every document and node (book 15.3.1). -->
		<button
			type="button"
			class="as-link"
			aria-pressed={ui.showSettled}
			aria-label="{ui.showSettled ? 'hide settled' : 'show settled'} annotations in {name}"
			data-testid="toggle-settled"
			title={ui.showSettled ? 'Hide resolved and discarded annotations again (s)' : 'Draw resolved and discarded annotations, faintly (s)'}
			onclick={() => (ui.showSettled = !ui.showSettled)}>{ui.showSettled ? 'hide settled' : 'show settled'}</button
		>
	{/if}
	{#if master.pdf}<a href={dataUrl(master.pdf)} aria-label="PDF of {name}">PDF</a>{/if}
{/if}

<style>
	.bar {
		width: 1px;
		height: 14px;
		background: var(--rule);
	}
	/* Drawn rather than set, as the panel's disclosure is: no chevron in the type stack is a true right angle with equal arms. Pointing right while everything is closed and down while it is open. */
	.chev {
		display: inline-block;
		width: 5px;
		height: 5px;
		margin-left: 6px;
		border-right: 1.5px solid currentColor;
		border-bottom: 1.5px solid currentColor;
		transform: rotate(-45deg);
		margin-bottom: 1px;
	}
	.chev.down {
		transform: rotate(45deg);
		margin-bottom: 3px;
	}
</style>
