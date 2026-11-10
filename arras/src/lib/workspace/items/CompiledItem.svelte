<script lang="ts">
	// A document's compiled PDF (plan 0.29.1), to read and not to mark: marks go on the document's text, since every compile replaces these bytes. A new compile opens it again where the reader is; one that made no PDF leaves the last, and says why.
	import { store } from '$lib/manifest/client.svelte';
	import { compileError, compiles } from '$lib/manifest/compiles.svelte';
	import { dataUrl } from '$lib/paths';
	import { forget } from '$lib/pdf/document';
	import PdfDoc from '$lib/pdf/PdfDoc.svelte';
	import PdfTools from '$lib/pdf/PdfTools.svelte';
	import { paperPlace } from '$lib/pdf/place.svelte';
	import type { Item } from '../item';
	import { documentLabel } from '../names';
	import { fileState } from '../state.svelte';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const master = $derived(m.masters.find((x) => x.path === item.id));
	const name = $derived(master ? documentLabel(m.masters, master.path) : item.id);
	// the address carries the compile it is, so each compile is a new document to PDF.js and the browser
	const url = $derived(master?.pdf ? `${dataUrl(master.pdf)}?v=${encodeURIComponent(master.compiled ?? '')}` : '');
	const paper = $derived(fileState(item).pdf);
	const pdfPage = $derived(Number(/^page=(\d+)$/.exec(item.anchor ?? '')?.[1] ?? 1));
	const named = $derived(/^page=\d+$/.test(item.anchor ?? ''));
	const place = paperPlace(
		() => paper,
		() => ({ seq: named ? (item.seq ?? 0) : 0, page: pdfPage }),
		undefined,
		() => url
	);
	const c = $derived(compiles.all[item.id]);
	const said = $derived.by(() => {
		if (c?.state === 'compiling') return 'Compiling…';
		const err = compileError(c);
		if (c?.last?.result === 'failed') return `The last compile made no PDF, so this is the one before it: ${err}`;
		if (c?.last?.result === 'errors') return `LaTeX reported errors in this compile: ${err}`;
		return '';
	});

	// the bytes of a compile the reader has moved on from are let go
	let shown = '';
	$effect(() => {
		const u = url;
		if (shown && shown !== u) forget(shown);
		shown = u;
	});
</script>

<div class="file-pdf" data-testid="pdf-item" data-document={item.id}>
	{#if said}<p class="compile-said" role="status" data-testid="pdf-compile">{said}</p>{/if}
	{#if url}
		<PdfTools view={paper} of={name} />
		{#key url}
			<PdfDoc {url} view={paper} page={place.opening.page} share={place.opening.share} seq={place.opening.seq} lands={!place.spent} onmoved={place.moved} />
		{/key}
	{:else}
		<div class="page item"><p class="muted">{name} has no compiled PDF yet.</p></div>
	{/if}
</div>

<style>
	.file-pdf {
		height: 100%;
		min-height: 0;
		display: flex;
		flex-direction: column;
	}
	.compile-said {
		margin: 0;
		padding: var(--gap-hair) var(--gap-tight);
		border-bottom: 1px solid var(--rule);
		color: var(--ink-soft);
		font-size: 0.9em;
		overflow-wrap: anywhere;
	}
</style>
