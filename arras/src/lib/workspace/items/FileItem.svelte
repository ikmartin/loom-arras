<script lang="ts">
	// A file of the project (plan 0.22.7), drawn by its kind: a Markdown file or a notebook as the publisher drew it, an HTML page in its own frame, a PDF by pdf.js, an image, text as text. Anything else is named, with "Open in its application" where the publisher can open it, and loom never opens a file that runs code.
	// Anything drawn here can be quoted (plan 0.22.8): words selected in a drawn body, in text or on a PDF page, and a box drawn on a PDF page or an image, each offered by the chip's one gesture, **quote**.
	import { store } from '$lib/manifest/client.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import { dataUrl, filesUrl } from '$lib/paths';
	import { MarkDesk } from '$lib/pdf/desk.svelte';
	import MarkedDoc from '$lib/pdf/MarkedDoc.svelte';
	import { mergeLines } from '$lib/pdf/marks';
	import { paperPlace } from '$lib/pdf/place.svelte';
	import PdfTools from '$lib/pdf/PdfTools.svelte';
	import AnnotateChip from '$lib/fragments/AnnotateChip.svelte';
	import { quote } from '$lib/notes';
	import { can, write } from '$lib/write';
	import { itemKey, type Item } from '../item';
	import { openOutside } from '../links';
	import { fileState, paneOf } from '../state.svelte';
	import { workspace } from '../store.svelte';
	import { onlyTicks, ticksIn } from '../tasks';
	import HtmlFrame from './HtmlFrame.svelte';

	let { item }: { item: Item } = $props();

	/** The suffixes the publisher opens in their application: documents only (`loom.files.OPENABLE`). */
	const OPENABLE = new Set(['pdf', 'ipynb', 'csv', 'xlsx', 'xls', 'ods', 'docx', 'odt', 'pptx', 'key', 'numbers', 'pages', 'apkg', 'colpkg', 'mp4', 'mov', 'mp3', 'm4a', 'wav', 'epub', 'djvu']);

	const m = $derived(store.manifest!);
	const file = $derived(m.files?.find((f) => f.path === item.id));
	const name = $derived(item.id.split('/').pop() ?? item.id);
	const suffix = $derived(name.includes('.') ? name.split('.').pop()!.toLowerCase() : '');
	const pdfPage = $derived(Number(/^page=(\d+)$/.exec(item.anchor ?? '')?.[1] ?? 1));
	const paper = $derived(fileState(item).pdf);
	/** Whether a link names a place on a PDF's pages: its page, or a mark on it. With none, it opens where the reader last was. */
	const named = $derived(/^page=\d+$/.test(item.anchor ?? '') || !!item.note);
	const place = paperPlace(
		() => paper,
		() => ({ seq: named ? (item.seq ?? 0) : 0, page: pdfPage }),
		() => workspace.update(itemKey(item), { anchor: undefined, note: undefined })
	);
	const desk = new MarkDesk(() => ({ on: item.id, owns: (n) => n.target.file === item.id, url: filesUrl(item.id), name }));
	const holder = paneOf();
	const hidesNotes = $derived(holder ? workspace.hidesNotes(holder.index) : false);
	let canOpen = $state(false);
	$effect(() => {
		void can('open').then((yes) => (canOpen = yes));
	});

	let body = $state<string | null>(null);
	let text = $state<string | null>(null);
	let failed = $state('');
	let el: HTMLElement | undefined = $state();
	let opens = $state(false);
	let refused = $state('');
	let tickable = $state(false);
	let tickRefused = $state('');
	/** The state each box was last asked for, which an older publication arriving late must not undo. */
	const asked = new Map<string, boolean>();

	// a drawn body is fetched by the manifest's hash, so an edit to the file shows on the next publication. What is drawn stays until the answer differs, so a publication that changed something else does not restart the page or a video playing in it, and one that only moved a tick leaves the mathematics and the scroll position alone
	let held: string | undefined;
	$effect(() => {
		const f = file;
		const hash = store.hash;
		if (f?.path !== held) {
			body = text = null;
			tickRefused = '';
			asked.clear();
		}
		held = f?.path;
		failed = '';
		if (!f) return;
		const at = f.body ? dataUrl(f.body) : f.kind === 'text' || f.kind === 'tex' || f.kind === 'document' ? filesUrl(f.path) : '';
		if (!at) return;
		void fetch(at + (at.includes('?') ? '&' : '?') + 'h=' + encodeURIComponent(hash), { cache: 'no-cache' })
			.then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${f.path}: ${r.status}`))))
			.then((t) => {
				if (held !== f.path) return;
				if (!f.body) text = t;
				else if (body !== null && onlyTicks(body, t)) settle(t);
				else body = t;
			})
			.catch((e: Error) => (failed = e.message));
	});

	$effect(() => {
		if (file?.kind === 'markdown') void can('file-tick').then((yes) => (tickable = yes));
	});

	/** The input of a drawn task item, given one if it has none yet: at the head of its words, which a loose list holds in a paragraph. */
	function boxOf(li: HTMLElement): HTMLInputElement {
		const found = li.querySelector<HTMLInputElement>(':scope > input.task-box, :scope > p > input.task-box');
		if (found) return found;
		const box = document.createElement('input');
		box.type = 'checkbox';
		box.className = 'task-box';
		box.setAttribute('aria-label', li.textContent?.trim().slice(0, 120) || 'A task');
		(li.querySelector<HTMLElement>(':scope > p') ?? li).prepend(box);
		return box;
	}

	// the publisher marks a task item and the viewer draws its box, which only a file loom can write to may change
	$effect(() => {
		void body;
		const live = tickable;
		for (const li of el?.querySelectorAll<HTMLElement>('.file-body li.task') ?? []) {
			const box = boxOf(li);
			const task = li.dataset.task;
			box.checked = (task ? asked.get(task) : undefined) ?? li.dataset.done === 'true';
			box.disabled = !(live && task);
		}
	});

	/** A new publication's boxes on the page as it stands. */
	function settle(html: string): void {
		const now = ticksIn(html);
		for (const li of el?.querySelectorAll<HTMLElement>('.file-body li.task') ?? []) {
			const task = li.dataset.task;
			const done = task ? now.get(task) : undefined;
			if (!task || done === undefined) continue;
			li.dataset.done = String(done);
			if (asked.get(task) === done) asked.delete(task);
			boxOf(li).checked = asked.get(task) ?? done;
		}
	}

	/** A box the person changed: it shows at once, and goes back with the reason if the publisher refuses. Once it is written the publication has it, so what a publication says wins again after a moment, whatever became of the file. */
	async function ticked(e: Event): Promise<void> {
		const box = e.target;
		if (!(box instanceof HTMLInputElement) || !box.classList.contains('task-box')) return;
		const li = box.closest<HTMLElement>('li.task');
		const task = li?.dataset.task;
		if (!li || !task) return;
		const done = box.checked;
		asked.set(task, done);
		tickRefused = '';
		const got = await write('file-tick', { path: item.id, task, done });
		if (!got.ok) {
			if (asked.get(task) === done) asked.delete(task);
			box.checked = !done;
			tickRefused = got.error?.message ?? 'That box could not be changed.';
			return;
		}
		setTimeout(() => {
			if (asked.get(task) !== done) return;
			asked.delete(task);
			box.checked = li.dataset.done === 'true';
		}, 3000);
	}

	// a frame in the body fills the column at the shape its width and height name, which a browser works out for an image and not for a frame
	$effect(() => {
		void body;
		for (const frame of el?.querySelectorAll<HTMLIFrameElement>('.file-body iframe') ?? []) {
			const [w, h] = [Number(frame.getAttribute('width')), Number(frame.getAttribute('height'))];
			if (w > 0 && h > 0) frame.style.aspectRatio = `${w} / ${h}`;
			else if (h > 0) {
				frame.style.aspectRatio = 'auto';
				frame.style.height = `${h}px`;
			}
		}
	});

	// a line a problem names (`L12`), whose text is then drawn a line at a time so the line can be shown
	const line = $derived(Number(/^L(\d+)$/.exec(item.anchor ?? '')?.[1] ?? 0));
	const lines = $derived(line && text !== null ? text.split('\n') : null);

	// the place a link named: a heading of a drawn body, or a line of a text, once it is on the page
	$effect(() => {
		const node = el;
		const anchor = item.anchor;
		void item.seq;
		if (!node || !anchor || (body === null && text === null)) return;
		requestAnimationFrame(() => node.querySelector(`[id="${CSS.escape(anchor)}"]`)?.scrollIntoView({ block: line ? 'center' : 'start' }));
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

	type Box = { left: number; top: number; width: number; height: number };
	/** What the chip offers to quote: words, or a region of a PDF page or the image, and where it stands. */
	let offered = $state<{ text?: string; page?: number; rects?: number[][]; lines?: number[][]; at: Box; range?: Range } | null>(null);

	/** Words selected in the drawn body or the text, offered once the mouse is up. */
	function selected(): void {
		const sel = window.getSelection();
		const words = sel?.toString().trim();
		if (!sel || !words || !sel.rangeCount || !el?.contains(sel.anchorNode)) return;
		const range = sel.getRangeAt(0);
		const r = range.getBoundingClientRect();
		offered = { text: words.slice(0, 4000), at: { left: r.left, top: r.top, width: r.width, height: r.height }, range: range.cloneRange() };
	}

	// words let go of take their offer with them, as a fragment's do
	$effect(() => {
		const gone = () => {
			if (offered?.range && !window.getSelection()?.toString().trim()) offered = null;
		};
		document.addEventListener('selectionchange', gone);
		return () => document.removeEventListener('selectionchange', gone);
	});

	// a box drawn on the image, in the image's own pixels from its top left
	let img = $state<HTMLImageElement | null>(null);
	let drag = $state<{ x: number; y: number; x2: number; y2: number } | null>(null);
	function press(e: PointerEvent): void {
		if (!img || e.button !== 0) return;
		e.preventDefault();
		const b = img.getBoundingClientRect();
		drag = { x: e.clientX - b.left, y: e.clientY - b.top, x2: e.clientX - b.left, y2: e.clientY - b.top };
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
	}
	function move(e: PointerEvent): void {
		if (!drag || !img) return;
		const b = img.getBoundingClientRect();
		drag = { ...drag, x2: Math.max(0, Math.min(b.width, e.clientX - b.left)), y2: Math.max(0, Math.min(b.height, e.clientY - b.top)) };
	}
	function release(): void {
		if (!drag || !img) return;
		const b = img.getBoundingClientRect();
		const [x, y, w, h] = [Math.min(drag.x, drag.x2), Math.min(drag.y, drag.y2), Math.abs(drag.x2 - drag.x), Math.abs(drag.y2 - drag.y)];
		if (w > 4 && h > 4) {
			const k = img.naturalWidth / (b.width || 1);
			offered = { rects: [[x * k, y * k, (x + w) * k, (y + h) * k].map((v) => Math.round(v * 10) / 10)], at: { left: b.left + x, top: b.top + y, width: w, height: h } };
		} else drag = null;
	}

	function quoting(): Promise<string> {
		const o = offered;
		if (!o || !file) return Promise.resolve('');
		return quote({ target: file.path, ...(o.page ? { page: o.page } : {}), ...(o.rects ? { rects: o.rects } : { quote: o.text, ...(o.lines ? { rects: o.lines } : {}) }) });
	}

	function highlight(): void {
		const o = offered;
		if (!o?.page || !o.lines || !o.text) return;
		desk.markWords('highlight', { page: o.page, text: o.text, rects: o.lines });
		offered = null;
		window.getSelection()?.removeAllRanges();
	}
</script>

{#if !file}
	<div class="page item" data-testid="file-item"><p class="muted">{item.id} is not a file this quilt shows.</p></div>
{:else if file.kind === 'html'}
	<HtmlFrame path={file.path} anchor={item.anchor ?? ''} seq={item.seq ?? 0} key={`file:${file.path}`} />
{:else if file.kind === 'pdf'}
	<div class="file-pdf" data-testid="file-item" data-kind="pdf">
		<PdfTools view={paper} markup />
		<MarkedDoc
			{desk}
			view={paper}
			url={filesUrl(file.path)}
			{name}
			dir={item.id.includes('/') ? item.id.slice(0, item.id.lastIndexOf('/')) : ''}
			hidden={hidesNotes}
			onoutside={canOpen ? () => void open().then(() => (desk.said = refused)) : undefined}
			page={place.opening.page}
			share={place.opening.share}
			seq={place.opening.seq}
			focus={item.note ?? ''}
			lands={!place.spent}
			onmoved={place.moved}
			onselect={(e) => {
				// the selection's range goes with the offer, so letting go of the words takes the chip with them
				const sel = window.getSelection();
				offered = { page: e.page, text: e.text, lines: mergeLines(e.rects), at: e.client, range: sel?.rangeCount ? sel.getRangeAt(0).cloneRange() : undefined };
			}}
			onbox={(e) => (offered = { page: e.page, rects: e.rects, at: e.client })}
		/>
	</div>
{:else}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="page item file" data-testid="file-item" data-kind={file.kind} data-file={file.path} bind:this={el} onmouseup={selected} onchange={ticked}>
		{#if tickRefused}<p class="tick-refused" role="alert" data-testid="file-tick-refused">{tickRefused}</p>{/if}
		{#if file.kind === 'image'}
			<!-- a box drawn on the image is a region it quotes -->
			<div class="image-frame" onpointerdown={press} onpointermove={move} onpointerup={release} data-testid="image-frame">
				<img class="file-image" bind:this={img} src={filesUrl(file.path)} alt={name} draggable="false" />
				{#if drag}<div class="drawn" style="left: {Math.min(drag.x, drag.x2)}px; top: {Math.min(drag.y, drag.y2)}px; width: {Math.abs(drag.x2 - drag.x)}px; height: {Math.abs(drag.y2 - drag.y)}px;"></div>{/if}
			</div>
		{:else if body !== null}
			<Prose html={body} class="body file-body" />
		{:else if lines}
			<pre class="file-text" data-testid="file-lines">{#each lines as l, i (i)}<span id="L{i + 1}" class:at={i + 1 === line}>{l}{'\n'}</span>{/each}</pre>
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
{#if offered}
	<AnnotateChip
		at={offered.at}
		range={offered.range}
		onquote={quoting}
		onhighlight={desk.writes && offered.lines ? highlight : undefined}
		ondone={() => {
			offered = null;
			drag = null;
			window.getSelection()?.removeAllRanges();
		}}
	/>
{/if}

<style>
	.image-frame {
		position: relative;
		display: inline-block;
		cursor: crosshair;
		user-select: none;
	}
	.drawn {
		position: absolute;
		border: 1.5px solid var(--ann-neutral);
		background: color-mix(in srgb, var(--ann-neutral) 12%, transparent);
		pointer-events: none;
	}
	.file-pdf {
		height: 100%;
		min-height: 0;
		display: flex;
		flex-direction: column;
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
	.file-text .at {
		background: var(--link-wash);
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
	/* a drawn body stands centred in a wide pane, as a document's column does; its one action stands with it */
	.file :global(.file-body),
	.file[data-kind='notebook'] .actions {
		max-width: var(--prose-measure);
		margin-inline: auto;
	}
	.file :global(.file-body :is(img, video, audio)) {
		max-width: 100%;
		height: auto;
	}
	/* a frame the file embeds takes the column's width, however wide it asked to be; the shape is a video's until the file names its own */
	.file :global(.file-body iframe) {
		display: block;
		width: 100%;
		height: auto;
		aspect-ratio: 16 / 9;
		border: 0;
		margin: var(--gap-tight) 0;
	}
	/* a task item's box stands where its bullet would */
	.file :global(.file-body li.task) {
		list-style: none;
	}
	.file :global(.file-body .task-box) {
		margin: 0 0.45em 0 -1.4em;
		vertical-align: -0.1em;
	}
	.tick-refused {
		position: sticky;
		top: 0;
		margin: 0 0 var(--gap-tight);
		padding: var(--gap-hair) var(--gap-tight);
		background: var(--paper);
		border-bottom: 1px solid var(--rule);
		color: var(--ink-soft);
		z-index: 1;
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
