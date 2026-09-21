<script lang="ts">
	// One page of a PDF: the canvas, PDF.js's text layer over it, and loom's rectangles over that.
	//
	// **A dumb renderer** (plan 0.13 item 5). It is given a document, a page and the rectangles to draw, and it reports
	// what the reader did. It fetches no annotations, knows nothing of sessions, and decides nothing about what a
	// highlight means — which is what lets the same component serve the pane, the modal, the proposal box and a preview.
	//
	// It is deliberately NOT keyed on the manifest store: arras polls every second and swaps the manifest whenever its
	// hash changes, so a pane that re-derived from it would re-render a page a second — the failure `Fragment.svelte`
	// has been patched for twice.
	import { onMount, untrack } from 'svelte';
	import { asPercent, document_, pdfjs } from './document';

	type Rect = readonly number[];

	let {
		url,
		page = 1,
		quads = [],
		scale = 1.4,
		onselect,
		onbox,
		onmark
	}: {
		url: string;
		page?: number;
		/** Rectangles to draw, in loom's space: points, origin top left, one per line. */
		quads?: { id: string; rects: Rect[] }[];
		scale?: number;
		/** The reader selected text: the page, what they selected, and the rectangles it covers. */
		onselect?: (e: { page: number; text: string; rects: number[][] }) => void;
		/** The reader drew a region where selection was not worth trusting. */
		onbox?: (e: { page: number; rects: number[][] }) => void;
		/** The reader acted on an existing mark: one click selects, two travel. */
		onmark?: (e: { id: string; travel: boolean }) => void;
	} = $props();

	let host: HTMLDivElement;
	let canvas: HTMLCanvasElement;
	let textLayer: HTMLDivElement;
	let box = $state({ width: 612, height: 792 });
	let size = $state({ width: 0, height: 0 });
	let problem = $state('');
	let drawing = $state<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
	let boxMode = $state(false);

	// Stage timings go to the performance timeline rather than to a prop: they are wanted by the profiler, by whoever is
	// deciding whether a page is cheap enough to keep in a pane, and by nothing in the app. `measure` is free when
	// nobody is recording.
	function timed(name: string, from: number, to: number): void {
		performance.measure(`pdf:${name}`, { start: from, end: to });
	}

	async function draw(): Promise<void> {
		try {
			const t0 = performance.now();
			const lib = await pdfjs();
			const doc = await document_(url);
			const p = await doc.getPage(page);
			const viewport = p.getViewport({ scale });
			box = { width: viewport.width / scale, height: viewport.height / scale };
			size = { width: viewport.width, height: viewport.height };
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
			// a page with no text layer cannot be selected on, so the reader is given the box tool instead
			boxMode = textLayer.textContent?.trim() === '';
		} catch (exc) {
			problem = exc instanceof Error ? exc.message : String(exc);
		}
	}

	onMount(() => {
		void untrack(() => draw());
	});

	$effect(() => {
		void url;
		void page;
		void scale;
		untrack(() => void draw());
	});

	/** Where a client rectangle sits in loom's space: points from the top left of the page. */
	function toPoints(r: { left: number; top: number; width: number; height: number }): number[] {
		const at = host.getBoundingClientRect();
		const k = box.width / (size.width || 1);
		return [(r.left - at.left) * k, (r.top - at.top) * k, (r.left - at.left + r.width) * k, (r.top - at.top + r.height) * k];
	}

	function readSelection(): void {
		const sel = window.getSelection();
		const text = sel?.toString().trim() ?? '';
		if (!sel || !text || sel.rangeCount === 0) return;
		const rects = [...sel.getRangeAt(0).getClientRects()].map((r) => toPoints(r));
		onselect?.({ page, text, rects });
	}

	function startBox(e: PointerEvent): void {
		if (!boxMode) return;
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
		// a click without a drag leaves a point, which is item 2's degenerate span
		const rect = { left, top, width: Math.abs(d.x1 - d.x0), height: Math.abs(d.y1 - d.y0) };
		onbox?.({ page, rects: [toPoints(rect)] });
	}
</script>

<div class="page" bind:this={host} style="width: {size.width}px; height: {size.height}px;">
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
	<div class="marks" aria-hidden={quads.length === 0}>
		{#each quads as q (q.id)}
			{#each q.rects as r, i (i)}
				{@const at = asPercent(r, box)}
				<button
					class="mark"
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
	{#if problem}<p class="problem" data-testid="pdf-problem">{problem}</p>{/if}
</div>

<style>
	.page {
		position: relative;
		background: var(--surface, #fff);
		box-shadow: 0 1px 3px rgb(0 0 0 / 0.14);
	}
	canvas {
		display: block;
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
	.mark:hover {
		background: var(--annotation-tint-strong, rgb(217 119 87 / 0.34));
	}
	.drawn {
		position: absolute;
		border: 1px solid var(--annotation, #c05621);
		background: rgb(217 119 87 / 0.14);
		pointer-events: none;
	}
	.problem {
		margin: 0;
		padding: 12px;
		font-size: 0.85rem;
	}
</style>
