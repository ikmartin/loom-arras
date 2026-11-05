<script lang="ts">
	// Page edits (plan 0.27): turn, delete, reorder and insert pages, into a new file. Nothing here touches the PDF being read (P7): the result is saved beside it under a name the person gives, or handed to the browser, and marks go into it as a saved copy's do. Editing a page's own text is for its application.
	import type { PDFDocumentProxy } from 'pdfjs-dist';
	import { onMount, untrack } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Popover from '$lib/components/Popover.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { follow, paneOfElement } from '$lib/workspace/links';
	import { can, write } from '$lib/write';
	import { base64, download, type MarkDesk } from './desk.svelte';
	import { document_, pdfjs, sourceOf } from './document';
	import { editedPages, type NewPage } from './portable';
	import PageThumb from './PageThumb.svelte';

	let {
		desk,
		url,
		name,
		dir = '',
		onclose
	}: {
		desk: MarkDesk;
		url: string;
		/** The PDF's file name. */
		name: string;
		/** The project directory a new file goes in by default. */
		dir?: string;
		onclose: () => void;
	} = $props();

	type Row = NewPage & { key: number };
	const stem = $derived(name.replace(/\.pdf$/i, ''));
	let docs = $state<PDFDocumentProxy[]>([]);
	/** The bytes of each document inserted, from the second on. */
	let others: Uint8Array[] = [];
	let rows = $state<Row[]>([]);
	let chosen = $state<number[]>([]);
	/** Where the new file goes: beside the PDF until the person says otherwise. */
	let path = $state(untrack(() => `${dir ? dir + '/' : ''}${stem}-edited.pdf`));
	let carry = $state(true);
	let busy = $state(false);
	let said = $state('');
	let saves = $state(false);
	let picker = $state<HTMLInputElement | null>(null);
	let dragging = $state<number | null>(null);
	let host = $state<HTMLElement | null>(null);
	let fresh = 0;

	const pagesOf = (from: number, count: number): Row[] => Array.from({ length: count }, (_, index) => ({ key: fresh++, from, index, rotate: 0 }));
	const carried = $derived(desk.carried());

	onMount(() => {
		void can('pdf-save').then((yes) => (saves = yes));
		void document_(url).then((d) => {
			docs = [d];
			rows = pagesOf(0, d.numPages);
		});
	});

	function pick(key: number, e: MouseEvent): void {
		if (e.shiftKey && chosen.length) {
			const at = rows.map((r) => r.key);
			const [a, b] = [at.indexOf(chosen[chosen.length - 1]), at.indexOf(key)].sort((x, y) => x - y);
			chosen = at.slice(a, b + 1);
		} else if (e.metaKey || e.ctrlKey) chosen = chosen.includes(key) ? chosen.filter((k) => k !== key) : [...chosen, key];
		else chosen = chosen.length === 1 && chosen[0] === key ? [] : [key];
	}

	function turn(by: number): void {
		rows = rows.map((r) => (chosen.includes(r.key) ? { ...r, rotate: (r.rotate + by + 360) % 360 } : r));
	}

	function drop(): void {
		rows = rows.filter((r) => !chosen.includes(r.key));
		chosen = [];
	}

	/** Move what is chosen one place along, or the dragged page to where it was dropped. */
	function shift(by: number): void {
		const next = [...rows];
		const order = by > 0 ? [...next.keys()].reverse() : [...next.keys()];
		for (const i of order) {
			const j = i + by;
			if (chosen.includes(next[i].key) && j >= 0 && j < next.length && !chosen.includes(next[j].key)) [next[i], next[j]] = [next[j], next[i]];
		}
		rows = next;
	}

	function dropOn(key: number): void {
		if (dragging === null || dragging === key) return;
		const next = rows.filter((r) => r.key !== dragging);
		const moved = rows.find((r) => r.key === dragging)!;
		const at = next.findIndex((r) => r.key === key);
		next.splice(at + (rows.findIndex((r) => r.key === dragging) < rows.findIndex((r) => r.key === key) ? 1 : 0), 0, moved);
		rows = next;
		dragging = null;
	}

	async function insert(file: File): Promise<void> {
		busy = true;
		said = '';
		try {
			const data = new Uint8Array(await file.arrayBuffer());
			const lib = await pdfjs();
			const doc = await lib.getDocument(sourceOf(data.slice())).promise;
			others = [...others, data];
			docs = [...docs, doc];
			const incoming = pagesOf(docs.length - 1, doc.numPages);
			// after what is chosen, else at the end
			const last = rows.map((r) => r.key).findLastIndex((k) => chosen.includes(k));
			const at = last >= 0 ? last + 1 : rows.length;
			rows = [...rows.slice(0, at), ...incoming, ...rows.slice(at)];
		} catch (exc) {
			said = `Could not read ${file.name}: ${exc instanceof Error ? exc.message : String(exc)}`;
		} finally {
			busy = false;
		}
	}

	async function build(): Promise<Uint8Array> {
		const lib = await pdfjs();
		const { marks, replaced } = carry ? carried : { marks: [], replaced: [] };
		return editedPages(lib, sourceOf(url), rows.map(({ from, index, rotate }) => ({ from, index, rotate })), others, marks, replaced);
	}

	async function act(then: (bytes: Uint8Array) => Promise<void>): Promise<void> {
		if (!rows.length) {
			said = 'A PDF needs at least one page.';
			return;
		}
		busy = true;
		said = '';
		try {
			await then(await build());
		} catch (exc) {
			said = `Could not make the file: ${exc instanceof Error ? exc.message : String(exc)}`;
		} finally {
			busy = false;
		}
	}

	const saveHere = () =>
		act(async (bytes) => {
			const res = await write('pdf-save', { path: path.trim(), data: base64(bytes) });
			if (!res.ok) {
				said = res.error?.message ?? 'the publisher refused it';
				return;
			}
			const saved = (res as typeof res & { path?: string }).path ?? path.trim();
			await store.refresh();
			const from = paneOfElement(host);
			onclose();
			follow({ kind: 'file', id: saved }, from, store.manifest);
		});

	const saveDown = () => act(async (bytes) => download(bytes, `${stem}-edited.pdf`));
</script>

<Popover modal open label="Edit the pages of {name}" testid="pages-editor" {onclose}>
	<div class="editor" bind:this={host}>
		<header>
			<strong>Edit pages</strong>
			<span class="faint">into a new file; {name} stays as it is</span>
			<button type="button" class="tool close" aria-label="Close" onclick={onclose}><Icon name="close" size={14} /></button>
		</header>
		<div class="tools">
			<button type="button" class="tool" title="Turn left" aria-label="Turn left" data-testid="pages-left" disabled={!chosen.length} onclick={() => turn(-90)}><Icon name="turn-left" size={15} /></button>
			<button type="button" class="tool" title="Turn right" aria-label="Turn right" data-testid="pages-right" disabled={!chosen.length} onclick={() => turn(90)}><Icon name="turn-right" size={15} /></button>
			<button type="button" class="act" data-testid="pages-earlier" disabled={!chosen.length} onclick={() => shift(-1)}>Earlier</button>
			<button type="button" class="act" data-testid="pages-later" disabled={!chosen.length} onclick={() => shift(1)}>Later</button>
			<button type="button" class="act" data-testid="pages-delete" disabled={!chosen.length} onclick={drop}>Delete</button>
			<button type="button" class="act" data-testid="pages-keep-only" disabled={!chosen.length} onclick={() => (rows = rows.filter((r) => chosen.includes(r.key)))}>Keep only these</button>
			<button type="button" class="act" data-testid="pages-insert" disabled={busy} onclick={() => picker?.click()}>Insert a PDF…</button>
			<input
				bind:this={picker}
				type="file"
				accept="application/pdf,.pdf"
				hidden
				data-testid="pages-insert-file"
				onchange={(e) => {
					const f = e.currentTarget.files?.[0];
					e.currentTarget.value = '';
					if (f) void insert(f);
				}}
			/>
			<span class="faint" data-testid="pages-count">{rows.length} {rows.length === 1 ? 'page' : 'pages'}</span>
		</div>
		<div class="grid" role="listbox" aria-multiselectable="true" aria-label="the pages">
			{#each rows as r, i (r.key)}
				<button
					type="button"
					class="page"
					class:on={chosen.includes(r.key)}
					role="option"
					aria-selected={chosen.includes(r.key)}
					draggable="true"
					data-testid="pages-page-{i + 1}"
					data-from={r.from}
					data-index={r.index}
					data-rotate={r.rotate}
					onclick={(e) => pick(r.key, e)}
					ondragstart={() => (dragging = r.key)}
					ondragover={(e) => e.preventDefault()}
					ondrop={(e) => {
						e.preventDefault();
						dropOn(r.key);
					}}
				>
					{#if docs[r.from]}<PageThumb doc={docs[r.from]} index={r.index} turn={r.rotate} />{/if}
					<span class="n">{i + 1}{#if r.from} · inserted{/if}</span>
				</button>
			{/each}
		</div>
		<footer>
			{#if carried.marks.length}
				<label class="carry"><input type="checkbox" bind:checked={carry} data-testid="pages-carry" /> Write what is marked into it</label>
			{/if}
			{#if saves}
				<input class="path" type="text" bind:value={path} aria-label="Where the new file goes, in the project" data-testid="pages-path" />
				<button type="button" class="act main" data-testid="pages-save" disabled={busy} onclick={saveHere}>Save as a new file</button>
			{/if}
			<button type="button" class="act" data-testid="pages-download" disabled={busy} onclick={saveDown}>Download</button>
		</footer>
		{#if said}<p class="said" role="status" data-testid="pages-said">{said}</p>{/if}
	</div>
</Popover>

<style>
	.editor {
		display: flex;
		flex-direction: column;
		gap: 8px;
		width: min(92vw, 980px);
		height: min(86vh, 820px);
		padding: 12px 14px;
		font-family: var(--sans);
		font-size: 0.82rem;
		color: var(--ink);
	}
	header,
	.tools,
	footer {
		flex: none;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}
	.close {
		margin-left: auto;
	}
	.faint {
		color: var(--ink-soft);
	}
	button {
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: none;
		border-radius: 4px;
		cursor: pointer;
	}
	button:hover:not(:disabled) {
		color: var(--ink);
	}
	button:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.tool {
		display: flex;
		padding: 4px 5px;
	}
	.act {
		padding: 2px 8px;
		border: 1px solid var(--rule);
	}
	.act.main {
		color: var(--ink);
		font-weight: 600;
	}
	.grid {
		flex: 1 1 auto;
		min-height: 0;
		overflow: auto;
		display: flex;
		flex-wrap: wrap;
		align-content: flex-start;
		gap: 12px;
		padding: 6px;
		border: 1px solid var(--rule);
		border-radius: 6px;
	}
	.page {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: flex-end;
		gap: 4px;
		padding: 6px;
		border: 2px solid transparent;
		border-radius: 6px;
	}
	.page.on {
		border-color: var(--accent);
		background: var(--accent-wash);
	}
	.n {
		font-size: 0.74rem;
		color: var(--ink-soft);
	}
	.path {
		flex: 1 1 220px;
		font: inherit;
		color: inherit;
		background: transparent;
		border: 1px solid var(--rule);
		border-radius: 4px;
		padding: 2px 6px;
	}
	.carry {
		display: flex;
		align-items: center;
		gap: 4px;
		color: var(--ink-soft);
	}
	.said {
		flex: none;
		margin: 0;
		color: var(--ink-soft);
	}
</style>
