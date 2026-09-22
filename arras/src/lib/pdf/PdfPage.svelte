<script lang="ts">
	type Box = { left: number; top: number; width: number; height: number };
	// One page of a PDF: the canvas, PDF.js's text layer over it, and loom's rectangles over that.
	//
	// **A dumb renderer** (plan 0.13 §6). It is given a document, a page and the rectangles to draw, and it reports what
	// the reader did. It fetches no annotations, knows nothing of sessions, and decides nothing about what a highlight
	// means — which is what lets the same component serve the pane, the modal, the proposal box and a preview.
	//
	// **`render` is the virtualisation seam.** A page outside the window keeps its size and loses its canvas, its text
	// layer and its overlay; the parent decides which pages are in, and this decides nothing about scrolling.
	//
	// It is deliberately NOT keyed on the manifest store: arras polls every second and swaps the manifest whenever its
	// hash changes, so a pane that re-derived from it would re-render a page a second — the failure `Fragment.svelte`
	// has been patched for twice.
	import { untrack } from 'svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { asPercent, document_, pdfjs } from './document';

	type Rect = readonly number[];

	let {
		url,
		page = 1,
		quads = [],
		scale = 1.4,
		render = true,
		tool = 'select',
		focus = '',
		onselect,
		onbox,
		onmark,
		onsized,
		onlink
	}: {
		url: string;
		page?: number;
		/** Rectangles to draw, in loom's space: points, origin top left, one per line. A note carries its kind, for colour, and is marked `note`; a result is not. */
		quads?: { id: string; rects: Rect[]; ids?: string[]; note?: boolean; kind?: string; transient?: boolean }[];
		scale?: number;
		/** Whether to draw at all. False keeps the page's size and releases everything that costs memory. */
		render?: boolean;
		/** `select` uses the text layer; `box` drags a region. A page with no text layer forces `box` whatever this says. */
		tool?: 'select' | 'box';
		/** The id of the mark to show as the one being looked at. */
		focus?: string;
		/** The reader selected text: the page, what they selected, and the rectangles it covers. */
		onselect?: (e: { page: number; text: string; rects: number[][]; client: Box }) => void;
		/** The reader drew a region where selection was not worth trusting. */
		onbox?: (e: { page: number; rects: number[][]; client: Box }) => void;
		/** The reader acted on an existing mark: one click selects, two travel. `el` is the mark, for a box to open at. */
		onmark?: (e: { id: string; ids: string[]; travel: boolean; note: boolean; el: HTMLElement }) => void;
		/** This page's size in points, once known, so a parent can size what it has not drawn. */
		onsized?: (e: { page: number; width: number; height: number }) => void;
		/** The reader followed a link inside the paper to another of its pages; a link out of it opens in a new tab and is not reported. */
		onlink?: (e: { page: number }) => void;
	} = $props();

	let host: HTMLDivElement;
	let canvas = $state<HTMLCanvasElement | null>(null);
	let textLayer = $state<HTMLDivElement | null>(null);
	let box = $state({ width: 612, height: 792 });
	let size = $state({ width: 612 * 1.4, height: 792 * 1.4 });
	let problem = $state('');
	let drawing = $state<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
	let empty = $state(false);
	let drawn = $state(false);
	/** The paper's own links on this page (plan 0.13 item 5, "link followed"): where each is, and where it goes. */
	let links = $state<{ left: string; top: string; width: string; height: string; url?: string; page?: number }[]>([]);

	/** Box mode: what the toolbar says, or forced on a page whose text layer has nothing to select. */
	const boxing = $derived(tool === 'box' || empty);

	// Stage timings go to the performance timeline rather than to a prop: they are wanted by the profiler, by whoever is
	// deciding whether a page is cheap enough to keep in a pane, and by nothing in the app. `measure` is free when
	// nobody is recording.
	function timed(name: string, from: number, to: number): void {
		performance.measure(`pdf:${name}`, { start: from, end: to });
	}

	async function draw(): Promise<void> {
		if (!canvas || !textLayer) return;
		try {
			const t0 = performance.now();
			const lib = await pdfjs();
			const doc = await document_(url);
			const p = await doc.getPage(page);
			const viewport = p.getViewport({ scale });
			box = { width: viewport.width / scale, height: viewport.height / scale };
			size = { width: viewport.width, height: viewport.height };
			onsized?.({ page, width: box.width, height: box.height });
			if (!canvas || !textLayer) return;
			const ratio = window.devicePixelRatio || 1;
			canvas.width = Math.floor(viewport.width * ratio);
			canvas.height = Math.floor(viewport.height * ratio);
			const ctx = canvas.getContext('2d');
			if (!ctx) return;
			ctx.scale(ratio, ratio);
			const t1 = performance.now();
			await p.render({ canvasContext: ctx, viewport, canvas }).promise;
			const t2 = performance.now();
			textLayer.replaceChildren();
			const layer = new lib.TextLayer({ textContentSource: await p.getTextContent(), container: textLayer, viewport });
			await layer.render();
			const t3 = performance.now();
			// The paper's links, drawn by us rather than by PDF.js's annotation layer, which wants a link service with a
			// contract of its own; a `Link` annotation is a rectangle and a destination, and that is all a reader needs.
			const found: typeof links = [];
			for (const a of await p.getAnnotations()) {
				if (a.subtype !== 'Link' || !Array.isArray(a.rect)) continue;
				const r = a.rect as number[];
				const [x0, y0] = viewport.convertToViewportPoint(r[0], r[1]);
				const [x1, y1] = viewport.convertToViewportPoint(r[2], r[3]);
				const at = {
					left: `${(Math.min(x0, x1) / viewport.width) * 100}%`,
					top: `${(Math.min(y0, y1) / viewport.height) * 100}%`,
					width: `${(Math.abs(x1 - x0) / viewport.width) * 100}%`,
					height: `${(Math.abs(y1 - y0) / viewport.height) * 100}%`
				};
				if (typeof a.url === 'string') found.push({ ...at, url: a.url });
				else if (a.dest) {
					try {
						const dest = typeof a.dest === 'string' ? await doc.getDestination(a.dest) : a.dest;
						const ref = Array.isArray(dest) ? dest[0] : null;
						if (ref) found.push({ ...at, page: (await doc.getPageIndex(ref)) + 1 });
					} catch {
						// a destination the document cannot resolve is a dead link in every viewer
					}
				}
			}
			links = found;
			timed('open', t0, t1);
			timed('render', t1, t2);
			timed('text', t2, t3);
			// a page with no text layer cannot be selected on, so the reader is given the box tool whatever the toolbar says
			empty = textLayer.textContent?.trim() === '';
			drawn = true;
		} catch (exc) {
			problem = exc instanceof Error ? exc.message : String(exc);
		}
	}

	$effect(() => {
		void url;
		void page;
		void scale;
		const on = render && !!canvas && !!textLayer;
		untrack(() => {
			if (on) void draw();
			else drawn = false;
		});
	});

	/** Where a client rectangle sits in loom's space: points from the top left of the page. */
	function toPoints(r: { left: number; top: number; width: number; height: number }): number[] {
		const at = host.getBoundingClientRect();
		const k = box.width / (size.width || 1);
		return [(r.left - at.left) * k, (r.top - at.top) * k, (r.left - at.left + r.width) * k, (r.top - at.top + r.height) * k];
	}

	function readSelection(): void {
		if (boxing) return;
		const sel = window.getSelection();
		const text = sel?.toString().trim() ?? '';
		if (!sel || !text || sel.rangeCount === 0) return;
		const client = [...sel.getRangeAt(0).getClientRects()];
		const rects = client.map((r) => toPoints(r));
		onselect?.({ page, text, rects, client: union(client) });
	}

	/** The box tool, or the modifier that reaches it without leaving the select tool. */
	function drags(e: PointerEvent): boolean {
		return boxing || e.altKey;
	}

	function startBox(e: PointerEvent): void {
		if (!drags(e)) return;
		const at = host.getBoundingClientRect();
		drawing = { x0: e.clientX - at.left, y0: e.clientY - at.top, x1: e.clientX - at.left, y1: e.clientY - at.top };
		// captured on the layer whose handlers these are: capturing on the page redirected every later pointer event
		// to the page, which listens for none of them, so a drag began and never ended
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
	}

	function moveBox(e: PointerEvent): void {
		if (!drawing) return;
		const at = host.getBoundingClientRect();
		drawing = { ...drawing, x1: e.clientX - at.left, y1: e.clientY - at.top };
	}

	function endBox(e: PointerEvent): void {
		if (!drawing) return;
		const at = host.getBoundingClientRect();
		const d = drawing;
		drawing = null;
		(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
		const left = Math.min(d.x0, d.x1) + at.left;
		const top = Math.min(d.y0, d.y1) + at.top;
		// a click without a drag leaves a point, which is the degenerate span
		const rect = { left, top, width: Math.abs(d.x1 - d.x0), height: Math.abs(d.y1 - d.y0) };
		onbox?.({ page, rects: [toPoints(rect)], client: rect });
	}

	/** One rectangle around several, in client space: where a form beside the selection stands. */
	function union(rs: { left: number; top: number; width: number; height: number }[]): { left: number; top: number; width: number; height: number } {
		if (!rs.length) return { left: 0, top: 0, width: 0, height: 0 };
		const l = Math.min(...rs.map((r) => r.left));
		const t = Math.min(...rs.map((r) => r.top));
		const r = Math.max(...rs.map((x) => x.left + x.width));
		const b = Math.max(...rs.map((x) => x.top + x.height));
		return { left: l, top: t, width: r - l, height: b - t };
	}
</script>

<div
	class="page"
	class:boxing
	bind:this={host}
	data-page={page}
	data-testid="pdf-page-{page}"
	style="width: {size.width}px; height: {size.height}px;"
>
	{#if render}
		<canvas bind:this={canvas} style="width: {size.width}px; height: {size.height}px;"></canvas>
		<div
			class="text"
			bind:this={textLayer}
			style="--scale-factor: {scale};"
			onmouseup={readSelection}
			onpointerdown={startBox}
			onpointermove={moveBox}
			onpointerup={endBox}
			role="presentation"
		></div>
		{#if links.length}
			<div class="links" aria-hidden="false">
				{#each links as l, i (i)}
					{#if l.url}
						<a class="link" href={l.url} target="_blank" rel="noopener noreferrer" title={l.url} aria-label="link out of the paper" style="left: {l.left}; top: {l.top}; width: {l.width}; height: {l.height};"></a>
					{:else if l.page}
						<button type="button" class="link" title="page {l.page}" aria-label="to page {l.page}" data-testid="pdf-link-{l.page}" style="left: {l.left}; top: {l.top}; width: {l.width}; height: {l.height};" onclick={() => onlink?.({ page: l.page! })}></button>
					{/if}
				{/each}
			</div>
		{/if}
		{#if quads.some((q) => q.note)}
			<!-- the tick column beside the page, on the discussion side (§8): one per note, the count where several share a place -->
			<div class="ticks" class:swap={prefs.swap} aria-label="annotated places">
				{#each quads.filter((q) => q.note) as q (q.id)}
					{@const at = asPercent(q.rects[0] ?? [0, 0, 0, 0], box)}
					<button
						type="button"
						class="tick"
						style="top: {at.top};"
						data-count={q.ids && q.ids.length > 1 ? q.ids.length : undefined}
						data-testid="tick-{q.id}"
						aria-label={q.ids && q.ids.length > 1 ? `${q.ids.length} notes here` : 'a note here'}
						onclick={(e) => onmark?.({ id: q.id, ids: q.ids ?? [q.id], travel: false, note: true, el: e.currentTarget })}
						ondblclick={(e) => onmark?.({ id: q.id, ids: q.ids ?? [q.id], travel: true, note: true, el: e.currentTarget })}
					></button>
				{/each}
			</div>
		{/if}
		<!-- Marks belong to a drawn page and to nothing else (plan 0.13 item 2): a held page has no box of its own to
		     position them against, and a book of hundreds of pages would otherwise carry every mark in the DOM at once. -->
		<div class="marks" aria-hidden={quads.length === 0}>
			{#each quads as q (q.id)}
				{#each q.rects as r, i (i)}
					{@const at = asPercent(r, box)}
					<button
						class="mark {q.kind ? 'k-' + q.kind : ''}"
						class:note={q.note}
						class:transient={q.transient}
						class:on={focus === q.id}
						data-mark={q.id}
						data-annotation={q.note ? (q.ids ?? [q.id]).join(' ') : undefined}
						data-count={q.ids && q.ids.length > 1 ? q.ids.length : undefined}
						data-testid="mark-{q.id}"
						aria-label="{q.transient ? 'the place this link points at' : q.note ? `${q.kind ?? 'note'} ${q.id}` : `result ${q.id}`}{q.ids && q.ids.length > 1 ? `, and ${q.ids.length - 1} more` : ''}"
						style="left: {at.left}; top: {at.top}; width: {at.width}; height: {at.height};"
						onclick={(e) => onmark?.({ id: q.id, ids: q.ids ?? [q.id], travel: false, note: !!q.note, el: e.currentTarget })}
						ondblclick={(e) => onmark?.({ id: q.id, ids: q.ids ?? [q.id], travel: true, note: !!q.note, el: e.currentTarget })}
					></button>
				{/each}
			{/each}
		</div>
	{:else}
		<div class="held" aria-hidden="true"></div>
	{/if}
	{#if drawing}
		<div
			class="drawn"
			style="left: {Math.min(drawing.x0, drawing.x1)}px; top: {Math.min(drawing.y0, drawing.y1)}px; width: {Math.abs(
				drawing.x1 - drawing.x0
			)}px; height: {Math.abs(drawing.y1 - drawing.y0)}px;"
		></div>
	{/if}
	{#if render && !drawn && !problem}<p class="waiting" aria-hidden="true">page {page}</p>{/if}
	{#if problem}<p class="problem" data-testid="pdf-problem">{problem}</p>{/if}
</div>

<style>
	.page {
		position: relative;
		background: var(--surface, #fff);
		box-shadow: 0 1px 3px rgb(0 0 0 / 0.14);
	}
	.page.boxing {
		cursor: crosshair;
	}
	canvas {
		display: block;
	}
	.held {
		position: absolute;
		inset: 0;
	}
	.text {
		position: absolute;
		inset: 0;
		overflow: hidden;
		line-height: 1;
		opacity: 0.2;
	}
	.text :global(span) {
		color: transparent;
		position: absolute;
		white-space: pre;
		transform-origin: 0 0;
	}
	.text :global(.endOfContent) {
		display: none;
	}
	.marks {
		position: absolute;
		inset: 0;
		pointer-events: none;
	}
	.ticks {
		position: absolute;
		top: 0;
		bottom: 0;
		right: -12px;
		width: 10px;
		pointer-events: none;
	}
	.ticks.swap {
		right: auto;
		left: -12px;
	}
	.tick {
		position: absolute;
		left: 0;
		width: 10px;
		height: 3px;
		border: 0;
		padding: 0;
		background: var(--annotation, #c05621);
		opacity: 0.6;
		cursor: pointer;
		pointer-events: auto;
	}
	.tick[data-count]::after {
		content: attr(data-count);
		position: absolute;
		left: 12px;
		top: -0.5em;
		font: 600 9px/1 var(--sans, sans-serif);
		color: var(--annotation, #c05621);
	}
	.links {
		position: absolute;
		inset: 0;
		pointer-events: none;
	}
	.link {
		position: absolute;
		display: block;
		border: 0;
		padding: 0;
		background: transparent;
		cursor: pointer;
		pointer-events: auto;
	}
	.link:hover {
		outline: 1px solid var(--link, #35618f);
		outline-offset: 1px;
	}
	.mark {
		position: absolute;
		border: 0;
		padding: 0;
		/* flat colour at low alpha: a blend mode or a shadow here is what makes a highlight layer expensive */
		background: var(--annotation-tint, rgb(217 119 87 / 0.22));
		cursor: pointer;
		pointer-events: auto;
	}
	/* with the box tool, what is under the pointer is the page and nothing on it: a reader drawing over a mark, a
	   link or a tick is drawing, not clicking, and a mark that took the press would end the box before it began */
	.page.boxing .mark,
	.page.boxing .link,
	.page.boxing .tick {
		pointer-events: none;
	}
	.mark:hover,
	.mark.on {
		background: var(--annotation-tint-strong, rgb(217 119 87 / 0.34));
	}
	/* a note is coloured by its kind, as a mark in a fragment is (theme.css); a tint only, since a shadow per mark is
	   what would make the overlay expensive, and a result keeps the neutral tint */
	.mark.note.k-objection {
		background: var(--state-incomplete-wash, rgb(196 88 60 / 0.22));
	}
	.mark.note.k-suggestion {
		background: var(--state-stale-wash, rgb(190 140 40 / 0.22));
	}
	.mark.note.k-question {
		background: var(--link-wash, rgb(53 97 143 / 0.18));
	}
	/* the place a link points at: lit while the URL carries it, never a record, so it is drawn as an outline */
	.mark.transient {
		background: none;
		outline: 2px solid var(--link, #35618f);
		outline-offset: 1px;
		pointer-events: none;
	}
	/* several notes on one place are one mark carrying the count, as a shared phrase is in a fragment */
	.mark[data-count]::after {
		content: attr(data-count);
		position: absolute;
		right: -2px;
		top: -0.9em;
		font: 600 9px/1 var(--sans, sans-serif);
		color: var(--annotation, #c05621);
	}
	.mark.note.k-citation,
	.mark.note.k-note,
	.mark.note.k-confirmation {
		background: var(--annotation-tint, rgb(217 119 87 / 0.22));
	}
	.drawn {
		position: absolute;
		border: 1px solid var(--annotation, #c05621);
		background: rgb(217 119 87 / 0.14);
		pointer-events: none;
	}
	.waiting,
	.problem {
		position: absolute;
		top: 8px;
		left: 12px;
		margin: 0;
		font-size: 0.8rem;
		color: var(--muted, #6b6b6b);
	}
	.problem {
		color: var(--problem, #a33);
	}
</style>
