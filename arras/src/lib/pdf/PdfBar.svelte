<script lang="ts">
	// A PDF's bar, on a cited work's pages and a project PDF alike, in two halves (`part`). The half that writes stands on the annotation row: a document's annotating tools (Annotate, Comment, the format menu, Undo and Redo) and then the PDF's own drawing tools. The half that reads stands on the toolbar's own row: the stepper, Comments and Notes, **PDF ▾** with its file acts, and the page and the zoom. Where nothing can be read here (no copy, or off the Paper view) every control stays drawn and greyed, so nothing after it moves. Putting the annotation row away puts a drawing tool down.
	import { untrack } from 'svelte';
	import AnnotateBar from '$lib/review/AnnotateBar.svelte';
	import type { Annotating } from '$lib/review/annotating.svelte';
	import { annotationRow } from '$lib/workspace/annotationRow.svelte';
	import type { MarkDesk } from './desk.svelte';
	import DrawTools from './DrawTools.svelte';
	import PdfMenu from './PdfMenu.svelte';
	import PdfTools from './PdfTools.svelte';
	import type { PdfView } from './view.svelte';

	let {
		view,
		notes,
		desk,
		of,
		part,
		writes = false,
		disabled = false,
		onoutside
	}: {
		view: PdfView;
		notes: Annotating;
		desk: MarkDesk | null;
		of: string;
		/** Which half: the tools that write, for the annotation row, or what reads, for the toolbar's own row. */
		part: 'read' | 'write';
		/** Whether the publisher takes annotations. */
		writes?: boolean;
		/** Nothing to act on here. */
		disabled?: boolean;
		onoutside?: () => void;
	} = $props();

	// a drawing tool goes down with the row that holds it
	$effect(() => {
		if (part !== 'read' || annotationRow.open) return;
		untrack(() => {
			if (view.tool !== 'select') view.tool = 'select';
		});
	});
</script>

<!-- one box, since the toolbar lays its bar's children out from the right -->
<span class="pdf-bar">
	{#if part === 'write'}
		<AnnotateBar {notes} {of} part="write" writes={writes && !disabled} />
		{#if writes}
			<span class="sep" aria-hidden="true"></span>
			<DrawTools {view} {notes} {of} {disabled} />
		{/if}
	{:else}
		<AnnotateBar {notes} {of} part="read" writes={writes && !disabled} />
		<PdfMenu {desk} {of} {disabled} {onoutside} />
		<span class="sep" aria-hidden="true"></span>
		<PdfTools {view} {of} {disabled} />
	{/if}
</span>

<style>
	.pdf-bar {
		display: inline-flex;
		align-items: center;
		gap: 2px;
	}
	.sep {
		width: 1px;
		height: 16px;
		margin: 0 5px;
		background: var(--rule);
	}
</style>
