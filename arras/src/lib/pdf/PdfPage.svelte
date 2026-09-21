<script lang="ts">
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
		onsized
	}: {
		url: string;
		page?: number;
		/** Rectangles to draw, in loom's space: points, origin top left, one per line. */
		quads?: { id: string; rects: Rect[] }[];
		scale?: number;
		/** Whether to draw at all. False keeps the page's size and releases everything that costs memory. */
		render?: boolean;
		/** `select` uses the text layer; `box` drags a region. A page with no text layer forces `box` whatever this says. */
		tool?: 'select' | 'box';
		/** The id of the mark to show as the one being looked at. */
		focus?: string;
		/** The reader selected text: the page, what they selected, and the rectangles it covers. */
		onselect?: (e: { page: number; text: string; rects: number[][] }) => void;
		/** The reader drew a region where selection was not worth trusting. */
		onbox?: (e: { page: number; rects: number[][] }) => void;
		/** The reader acted on an existing mark: one click selects, two travel. */
		onmark?: (e: { id: string; travel: boolean }) => void;
		/** This page's size in points, once known, so a parent can size what it has not drawn. */
		onsized?: (e: { page: number; width: number; height: number }) => void;
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
		const rects = [...sel.getRangeAt(0).getClientRects()].map((r) => toPoints(r));
		onselect?.({ page, text, rects });
	}

	/** The box tool, or the modifier that reaches it without leaving the select tool. */
	function drags(e: PointerEvent): boolean {
		return boxing || e.altKey;
	}

	function startBox(e: PointerEvent): void {
		if (!drags(e)) return;
		const at = host.getBoundingClientRect();
		drawing = { x0: e.clientX - at.left, y0: e.clientY - at.top, x1: e.clientX - at.left, y1: e.clientY - at.top };
		host.setPointerCapture(e.pointerId);
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
		host.releasePointerCapture(e.pointerId);
		const left = Math.min(d.x0, d.x1) + at.left;
		const top = Math.min(d.y0, d.y1) + at.top;
		// a click without a drag leaves a point, which is the degenerate span
		const rect = { left, top, width: Math.abs(d.x1 - d.x0), height: Math.abs(d.y1 - d.y0) };
		onbox?.({ page, rects: [toPoints(rect)] });
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
	{:else}
		<div class="held" aria-hidden="true"></div>
	{/if}
	<div class="marks" aria-hidden={quads.length === 0}>
		{#each quads as q (q.id)}
			{#each q.rects as r, i (i)}
				{@const at = asPercent(r, box)}
				<button
					class="mark"
					class:on={focus === q.id}
					data-mark={q.id}
					data-testid="mark-{q.id}"
					aria-label="annotation {q.id}"
					style="left: {at.left}; top: {at.top}; width: {at.width}; height: {at.height};"
					onclick={() => onmark?.({ id: q.id, travel: false })}
					ondblclick={() => onmark?.({ id: q.id, travel: true })}
				></button>
			{/each}
		{/each}
	</div>
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
	.mark {
		position: absolute;
		border: 0;
		padding: 0;
		/* flat colour at low alpha: a blend mode or a shadow here is what makes a highlight layer expensive */
		background: var(--annotation-tint, rgb(217 119 87 / 0.22));
		cursor: pointer;
		pointer-events: auto;
	}
	.mark:hover,
	.mark.on {
		background: var(--annotation-tint-strong, rgb(217 119 87 / 0.34));
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
