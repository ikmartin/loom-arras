<script lang="ts">
	// A whole document, virtualised: a column of pages, a window of them drawn, the rest holding their size (plan 0.13 §6).
	//
	// The reason to virtualise is memory rather than time — a page costs 12–16ms to draw, which is an order under the
	// budget, but a canvas for each of a 679-page book is gigabytes. A page outside the window keeps its height, so the
	// scrollbar never lies and nothing jumps when one is drawn.
	//
	// Page sizes are per page, not per document: a scan's pages differ by a point or two, and a fixed transform would
	// creep down a long paper. Page one's size is the placeholder until a page reports its own.
	import { onMount } from 'svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { PdfView } from './view.svelte';
	import { document_ } from './document';
	import PdfPage from './PdfPage.svelte';

	type Rect = readonly number[];
	type Box = { left: number; top: number; width: number; height: number };

	let {
		url,
		page = 1,
		spans = [],
		focus = '',
		scale,
		window: near = 2,
		view,
		onselect,
		onbox,
		onmark,
		onpage,
		onlink
	}: {
		url: string;
		/** The page to open at; changing it scrolls there. */
		page?: number;
		/** What to draw, by page: a work's results, and the notes on its pages, which carry their kind and are marked `note`. */
		spans?: { id: string; page: number; rects: Rect[]; ids?: string[]; note?: boolean; kind?: string; transient?: boolean }[];
		/** The span to scroll to and show as the one being looked at. */
		focus?: string;
		/** Overrides the reader's own zoom, for a pane whose size is not theirs to choose (the proposal box). */
		scale?: number;
		/** How many pages either side of the one in view are drawn. */
		window?: number;
		/** The reader's view of this document, which the caller's controls act on. Left out, the renderer keeps its own. */
		view?: PdfView;
		onselect?: (e: { page: number; text: string; rects: number[][]; client: Box }) => void;
		onbox?: (e: { page: number; rects: number[][]; client: Box }) => void;
		onmark?: (e: { id: string; ids: string[]; travel: boolean; note: boolean; el: HTMLElement }) => void;
		/** The page the reader is looking at changed, by scrolling or by being sent there. */
		onpage?: (e: { page: number }) => void;
		/** A link inside the paper was followed to another of its pages; the document scrolls there and says so. */
		onlink?: (e: { page: number }) => void;
	} = $props();

	// The renderer's own view, used when no caller supplied one; `v` is the one in force either way.
	const own = new PdfView();
	const v = $derived(view ?? own);
	let columnWidth = $state(0);
	const PAGE_GUTTER = 24;
	const fitted = $derived.by(() => {
		const w = sizes[at]?.width ?? sizes[1]?.width ?? 612;
		if (!v.fitWidth || !columnWidth) return null;
		return Math.min(3, Math.max(0.5, (columnWidth - PAGE_GUTTER) / w));
	});

	/** Where the text of the paper runs, in points, from every result and note the sidecar places: the margins either side are paper, not reading. */
	const textBlock = $derived.by(() => {
		let x0 = Infinity;
		let x1 = -Infinity;
		for (const s of spans)
			for (const r of s.rects) {
				x0 = Math.min(x0, r[0]);
				x1 = Math.max(x1, r[2]);
			}
		return x1 > x0 ? { x0, x1 } : null;
	});
	/** Room left of the text for the landing dot, which is drawn just outside a result's first line. */
	const LANDING = 18;
	// A page wider than its column at the reader's zoom is drawn so its text block fits, with room for the dot: in half a pane the reader's zoom would cut every line. With nothing placed on the paper, the page fits instead.
	const textFitted = $derived.by(() => {
		const reader = prefs.zoom.pdf ?? 1.4;
		const w = sizes[at]?.width ?? sizes[1]?.width ?? 612;
		if (!v.fitText || !columnWidth || w * reader <= columnWidth - PAGE_GUTTER) return null;
		const room = textBlock ? (columnWidth - LANDING - 12) / (textBlock.x1 - textBlock.x0) : (columnWidth - PAGE_GUTTER) / w;
		return Math.min(reader, Math.max(0.5, room));
	});

	/** Whether the zoom a page is drawn at is settled: while it may still fit the text to a column not yet measured, a page drawn now would be drawn again a frame later. */
	const ready = $derived(scale !== undefined || !v.fitText || columnWidth > 0);

	// The reader's zoom for this kind of renderer, remembered across papers and across visits, unless a caller fixes it.
	const drawAt = $derived(scale ?? fitted ?? textFitted ?? prefs.zoom.pdf ?? 1.4);

	/** With the page wider than the column, start the view at the text's left edge, less the dot's room, rather than at the paper's. */
	function toText(): void {
		if (!column || !textBlock || column.scrollWidth <= column.clientWidth) return;
		const holder = column.querySelector<HTMLElement>('[data-holder]');
		if (!holder) return;
		const left = holder.getBoundingClientRect().left - column.getBoundingClientRect().left + column.scrollLeft;
		column.scrollLeft = Math.max(0, left + textBlock.x0 * drawAt - LANDING);
	}
	/** Whether the text block fits the column at the zoom drawn, so the page is read from its left edge whatever it lands on. */
	function textFits(): boolean {
		return !!column && !!textBlock && (textBlock.x1 - textBlock.x0) * drawAt + LANDING <= column.clientWidth;
	}
	$effect(() => {
		void drawAt;
		void columnWidth;
		void count;
		if (!focus) requestAnimationFrame(toText);
	});
	// The controls read the scale actually drawn, which is the fitted one while fit-width holds.
	$effect(() => {
		v.scale = drawAt;
	});
	let column = $state<HTMLDivElement | null>(null);
	let count = $state(0);
	// `page` is the page the parent asked for; `here` is the one the reader is on, which scrolling also moves.
	let here = $state(0);
	let problem = $state('');
	/** Each page's own size in points, filled in as pages draw; page one's stands in for the undrawn. */
	let sizes = $state<Record<number, { width: number; height: number }>>({});

	const all = $derived(Array.from({ length: count }, (_, i) => i + 1));
	// A link may name a page the document does not have -- a preprint's numbering against a published copy's. The last
	// page is the honest answer; claiming page 40 of 12 is not.
	const at = $derived(count ? Math.min(Math.max(here || page, 1), count) : here || page);
	const shown = $derived(new Set(all.filter((n) => Math.abs(n - at) <= near)));
	const byPage = $derived.by(() => {
		const out: Record<number, { id: string; rects: Rect[]; ids?: string[]; note?: boolean; kind?: string; transient?: boolean }[]> = {};
		for (const s of spans) (out[s.page] ??= []).push({ id: s.id, rects: s.rects, ids: s.ids, note: s.note, kind: s.kind, transient: s.transient });
		return out;
	});

	function sizeOf(n: number): { width: number; height: number } {
		return sizes[n] ?? sizes[1] ?? { width: 612, height: 792 };
	}

	// what the controls show, wherever they are drawn
	$effect(() => {
		v.count = count;
	});
	$effect(() => {
		v.page = at;
	});
	// A control asking for a page, by nonce so that asking for the one already shown still scrolls to it.
	$effect(() => {
		const want = v.jump;
		if (!want || !column || !count) return;
		const n = Math.min(Math.max(want.page, 1), count);
		const target = column.querySelector(`[data-holder="${n}"]`);
		if (!target) return;
		here = n;
		toPage(target, 'smooth');
		onpage?.({ page: n });
	});

	onMount(() => {
		let dropped = false;
		document_(url)
			.then((doc) => {
				if (!dropped) count = doc.numPages;
			})
			.catch((exc) => {
				problem = exc instanceof Error ? exc.message : String(exc);
			});
		return () => {
			dropped = true;
		};
	});

	// Sent to a page: scroll it into view. Not an effect on `here`, which the scroll handler also writes — that would
	// fight the reader for the scrollbar.
	$effect(() => {
		const want = page;
		if (!column || !count) return;
		const target = column.querySelector(`[data-holder="${Math.min(Math.max(want, 1), count)}"]`);
		if (target) {
			here = Math.min(Math.max(want, 1), count);
			toPage(target);
		}
	});

	$effect(() => {
		const id = focus;
		// a redraw at another zoom or width moves the result: land again, which also re-reads whether the text now fits
		void drawAt;
		void columnWidth;
		if (!id || !column) return;
		const at = spans.find((s) => s.id === id);
		if (!at) return;
		here = at.page;
		// After the page is in the window and has drawn, the mark itself is what to scroll to — and it does not exist
		// until the page it is on is rendered, which is not the next frame. One frame was enough while the only caller
		// scrolled to a mark on a page already drawn; the preview card asks for one on a page it has just mounted, and
		// fell back to the top of the page every time. Wait for the mark, then give up on the page.
		let tries = 0;
		let frame = 0;
		const reach = () => {
			const mark = column?.querySelector(`[data-mark="${CSS.escape(id)}"]`);
			// and for the page to be drawn at the zoom about to be reasoned with: a page told its new zoom but not yet redrawn still places the mark at the old one, and a landing measured there scrolls to the wrong place
			const holder = column?.querySelector<HTMLElement>(`[data-holder="${at.page}"]`);
			const drawn = !holder || Math.abs(holder.getBoundingClientRect().width - sizeOf(at.page).width * drawAt) <= 2;
			if ((!mark || !drawn) && tries++ < 30) {
				frame = requestAnimationFrame(reach);
				return;
			}
			// A text block that fits the column is read from its left edge: `toText` sets the sideways place first, so the whole block is in view and the result needs no sideways move, which would otherwise go to where its first line starts, mid-line, cutting its every other line. Wider than the column, a result is read from its first word, with the dot in view.
			const fits = textFits();
			if (fits) toText();
			if (!mark) {
				// no mark after all: the page, which is wider than a half-pane column, so vertically only
				const holder = column?.querySelector(`[data-holder="${at.page}"]`);
				if (holder) toPage(holder, 'smooth');
				return;
			}
			mark.scrollIntoView({ block: 'center', inline: fits ? 'nearest' : 'start', behavior: 'smooth' });
		};
		frame = requestAnimationFrame(reach);
		return () => cancelAnimationFrame(frame);
	});

	/** Scroll a page's top to the top of the column, and nothing sideways: a page is wider than a half-pane column, and scrolling it into view let the browser align its right edge, over a landing that had just set where the text starts. */
	function toPage(target: Element, behavior: ScrollBehavior = 'auto'): void {
		if (!column) return;
		const top = column.scrollTop + target.getBoundingClientRect().top - column.getBoundingClientRect().top;
		column.scrollTo({ top, behavior });
	}

	/** Sent to a page by a link inside the paper: scroll there and say so, as a scroll would. */
	function goTo(n: number): void {
		const target = column?.querySelector(`[data-holder="${n}"]`);
		if (!target) return;
		here = n;
		toPage(target, 'smooth');
		onpage?.({ page: n });
	}

	function scrolled(): void {
		if (!column) return;
		const middle = column.scrollTop + column.clientHeight / 2;
		let best = here;
		for (const holder of column.querySelectorAll<HTMLElement>('[data-holder]')) {
			if (holder.offsetTop <= middle) best = Number(holder.dataset.holder);
		}
		if (best !== here) {
			here = best;
			onpage?.({ page: best });
		}
	}
</script>

<div class="doc" data-testid="pdf-doc">
	<div class="column" bind:this={column} bind:clientWidth={columnWidth} onscroll={scrolled}>
		{#if problem}
			<p class="problem" data-testid="pdf-problem">{problem}</p>
		{/if}
		{#each all as n (n)}
			{@const at = sizeOf(n)}
			<div class="holder" data-holder={n} style="min-height: {at.height * drawAt}px;">
				<PdfPage
					{url}
					page={n}
					scale={drawAt}
					tool={v.tool}
					{focus}
					render={shown.has(n) && ready}
					quads={byPage[n] ?? []}
					{onselect}
					{onbox}
					{onmark}
					onsized={(e) => (sizes = { ...sizes, [e.page]: { width: e.width, height: e.height } })}
					onlink={(e) => {
						goTo(e.page);
						onlink?.(e);
					}}
				/>
			</div>
		{/each}
	</div>
</div>

<style>
	.doc {
		display: flex;
		flex-direction: column;
		min-height: 0;
		height: 100%;
	}
	.column {
		flex: 1 1 auto;
		overflow: auto;
		display: flex;
		flex-direction: column;
		/* `safe`: a page wider than the column overflows to the right, where it can be scrolled to, rather than off the left edge */
		align-items: safe center;
		gap: 12px;
		padding: 12px 0;
		min-height: 0;
	}
	.problem {
		margin: 0;
		padding: 12px;
		font-size: 0.85rem;
		color: var(--problem, #a33);
	}
</style>
