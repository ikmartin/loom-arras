<script lang="ts">
	// A PDF's toolbar bar, on a cited work's pages and a project PDF alike: a document's annotating bar (Annotate, Comment, the format menu, Undo and Redo, the stepper, Comments and Notes), then the PDF's own drawing tools, **PDF ▾** with its file acts, and the page and the zoom. Where nothing can be read here (no copy, or off the Paper view) every control stays drawn and greyed, so nothing after it moves.
	import AnnotateBar from '$lib/review/AnnotateBar.svelte';
	import type { Annotating } from '$lib/review/annotating.svelte';
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
		writes = false,
		disabled = false,
		onoutside
	}: {
		view: PdfView;
		notes: Annotating;
		desk: MarkDesk | null;
		of: string;
		/** Whether the publisher takes annotations. */
		writes?: boolean;
		/** Nothing to act on here. */
		disabled?: boolean;
		onoutside?: () => void;
	} = $props();
</script>

<!-- one box, since the toolbar lays its bar's children out from the right -->
<span class="pdf-bar">
	<AnnotateBar {notes} {of} writes={writes && !disabled} />
	{#if writes}
		<span class="sep" aria-hidden="true"></span>
		<DrawTools {view} {notes} {of} {disabled} />
	{/if}
	<PdfMenu {desk} {of} {disabled} {onoutside} />
	<span class="sep" aria-hidden="true"></span>
	<PdfTools {view} {of} {disabled} />
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
