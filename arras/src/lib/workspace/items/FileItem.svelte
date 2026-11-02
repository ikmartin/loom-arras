<script lang="ts">
	// A file of the project (plan 0.22.7), drawn by its kind: a Markdown file or a notebook as the publisher drew it, an HTML page in its own frame, a PDF by pdf.js, an image, text as text. Anything else is named, with "Open in its application" where the publisher can open it, and loom never opens a file that runs code.
	import { store } from '$lib/manifest/client.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import { dataUrl, filesUrl } from '$lib/paths';
	import PdfDoc from '$lib/pdf/PdfDoc.svelte';
	import { PdfView } from '$lib/pdf/view.svelte';
	import { can } from '$lib/write';
	import type { Item } from '../item';
	import { openOutside } from '../links';
	import HtmlFrame from './HtmlFrame.svelte';

	let { item }: { item: Item } = $props();

	/** The suffixes the publisher opens in their application: documents only (`loom.files.OPENABLE`). */
	const OPENABLE = new Set(['ipynb', 'csv', 'xlsx', 'xls', 'ods', 'docx', 'odt', 'pptx', 'key', 'numbers', 'pages', 'apkg', 'colpkg', 'mp4', 'mov', 'mp3', 'm4a', 'wav', 'epub', 'djvu']);

	const m = $derived(store.manifest!);
	const file = $derived(m.files?.find((f) => f.path === item.id));
	const name = $derived(item.id.split('/').pop() ?? item.id);
	const suffix = $derived(name.includes('.') ? name.split('.').pop()!.toLowerCase() : '');
	const pdfPage = $derived(Number(/^page=(\d+)$/.exec(item.anchor ?? '')?.[1] ?? 1));
	const paper = new PdfView();

	let body = $state<string | null>(null);
	let text = $state<string | null>(null);
	let failed = $state('');
	let el: HTMLElement | undefined = $state();
	let opens = $state(false);
	let refused = $state('');

	// a drawn body is fetched by the manifest's hash, so an edit to the file shows on the next publication
	$effect(() => {
		const f = file;
		const hash = store.hash;
		body = text = null;
		failed = '';
		if (!f) return;
		const at = f.body ? dataUrl(f.body) : f.kind === 'text' || f.kind === 'tex' ? filesUrl(f.path) : '';
		if (!at) return;
		void fetch(at + (at.includes('?') ? '&' : '?') + 'h=' + encodeURIComponent(hash), { cache: 'no-cache' })
			.then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${f.path}: ${r.status}`))))
			.then((t) => {
				if (f.body) body = t;
				else text = t;
			})
			.catch((e: Error) => (failed = e.message));
	});

	// the place a link named: a heading of a drawn body, once it is on the page
	$effect(() => {
		const node = el;
		const anchor = item.anchor;
		void item.seq;
		if (!node || !anchor || body === null) return;
		requestAnimationFrame(() => node.querySelector(`[id="${CSS.escape(anchor)}"]`)?.scrollIntoView({ block: 'start' }));
	});

	$effect(() => {
		if (file?.kind === 'other' || file?.kind === 'notebook') void can('open').then((yes) => (opens = yes && OPENABLE.has(suffix)));
	});

	function size(bytes: number): string {
		return bytes < 1024 ? `${bytes} bytes` : bytes < 1 << 20 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1 << 20)).toFixed(1)} MB`;
	}

	async function open(): Promise<void> {
		refused = await openOutside({ file: item.id });
	}
</script>

{#if !file}
	<div class="page item" data-testid="file-item"><p class="muted">{item.id} is not a file this quilt shows.</p></div>
{:else if file.kind === 'html'}
	<HtmlFrame path={file.path} anchor={item.anchor ?? ''} seq={item.seq ?? 0} key={`file:${file.path}`} />
{:else if file.kind === 'pdf'}
	<div class="file-pdf" data-testid="file-item" data-kind="pdf">
		<PdfDoc url={filesUrl(file.path)} page={pdfPage} seq={item.seq ?? 0} view={paper} />
	</div>
{:else}
	<div class="page item file" data-testid="file-item" data-kind={file.kind} data-file={file.path} bind:this={el}>
		{#if file.kind === 'image'}
			<img class="file-image" src={filesUrl(file.path)} alt={name} />
		{:else if body !== null}
			<Prose html={body} class="body file-body" />
		{:else if text !== null}
			<pre class="file-text">{text}</pre>
		{:else if failed}
			<p class="muted">{failed}</p>
		{:else if file.kind === 'other'}
			<p class="file-other"><strong>{name}</strong> <span class="faint">· {size(file.bytes)}</span></p>
			<p class="muted">The viewer does not draw this kind of file.</p>
		{/if}
		{#if opens}
			<p class="actions">
				<button class="as-link" onclick={open} data-testid="file-open-outside">Open in its application</button>
				{#if refused}<span class="faint" data-testid="file-open-refused">{refused}</span>{/if}
			</p>
		{/if}
	</div>
{/if}

<style>
	.file-pdf {
		height: 100%;
		min-height: 0;
	}
	.file-image {
		max-width: 100%;
		height: auto;
	}
	.file-text {
		font-family: var(--mono);
		font-size: 12.5px;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		margin: 0;
	}
	.file :global(.nb-code) {
		margin: var(--gap-tight) 0;
		border-left: 2px solid var(--rule);
		padding-left: var(--gap-tight);
	}
	.file :global(.nb-count) {
		font-family: var(--mono);
		font-size: 11px;
		color: var(--ink-faint);
	}
	.file :global(.nb-code pre),
	.file :global(.nb-out) {
		font-family: var(--mono);
		font-size: 12.5px;
		white-space: pre-wrap;
		margin: var(--gap-hair) 0;
	}
	.file :global(.nb-out) {
		color: var(--ink-soft);
	}
	.file :global(.nb-image) {
		max-width: 100%;
	}
	.file :global(.nb-note) {
		color: var(--ink-faint);
		font-style: italic;
	}
	.file :global(.file-body img) {
		max-width: 100%;
	}
	/* a file's own headings, which annotations and messages rarely have, sized as a page's are */
	.file :global(.file-body :is(h1, h2, h3, h4)) {
		font-family: var(--sans);
		font-weight: 500;
		line-height: 1.25;
		margin: 1.1em 0 0.45em;
	}
	.file :global(.file-body h1) {
		font-size: 1.55em;
		margin-top: 0;
	}
	.file :global(.file-body h2) {
		font-size: 1.25em;
	}
	.file :global(.file-body h3) {
		font-size: 1.08em;
	}
</style>
