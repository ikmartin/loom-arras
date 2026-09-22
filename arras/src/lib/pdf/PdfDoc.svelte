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
	import PdfTools from './PdfTools.svelte';
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
		toolbar = true,
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
		toolbar?: boolean;
		/** The reader's view of this document, when a page draws the controls itself. Left out, the renderer keeps its own and draws its toolbar. */
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

	// The reader's zoom for this kind of renderer, remembered across papers and across visits, unless a caller fixes it.
	const drawAt = $derived(scale ?? fitted ?? prefs.zoom.pdf ?? 1.4);
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
		target.scrollIntoView({ block: 'start', behavior: 'smooth' });
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
			target.scrollIntoView({ block: 'start' });
		}
	});

	$effect(() => {
		const id = focus;
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
			if (!mark && tries++ < 30) {
				frame = requestAnimationFrame(reach);
				return;
			}
			(mark ?? column?.querySelector(`[data-holder="${at.page}"]`))?.scrollIntoView({
				block: 'center',
				behavior: 'smooth'
			});
		};
		frame = requestAnimationFrame(reach);
		return () => cancelAnimationFrame(frame);
	});

	/** Sent to a page by a link inside the paper: scroll there and say so, as a scroll would. */
	function goTo(n: number): void {
		const target = column?.querySelector(`[data-holder="${n}"]`);
		if (!target) return;
		here = n;
		target.scrollIntoView({ block: 'start', behavior: 'smooth' });
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
	{#if toolbar}
		<div class="toolbar">
			<PdfTools view={v} />
			<span class="where" data-testid="pdf-where">{count ? `page ${at} of ${count}` : ''}</span>
		</div>
	{/if}
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
					render={shown.has(n)}
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
	/* The renderer's own toolbar, for a caller that does not draw one. A page with a rail of its own passes `toolbar: false` and puts `PdfTools` on that line instead. */
	.toolbar {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 3px 6px;
		border-bottom: 1px solid var(--rule, #ddd9cf);
	}
	.where {
		margin-left: auto;
		color: var(--muted, #6b6b6b);
		font-size: 0.78rem;
	}
	.column {
		flex: 1 1 auto;
		overflow: auto;
		display: flex;
		flex-direction: column;
		align-items: center;
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
