<script lang="ts">
	// A work, rendered small for a hover card (plan 0.13.3 H3–H5): **the paper, not the transcription of it**, at the place the link names. Where the place is a result the sidecar locates, the card is cropped to the statement and two lines either side, the page drawn at 115% of the card's width, and a translucent dot marks where the statement begins (H4) — a box would assert an extent the reader can already see. A span or a quote is located by the publisher; a box needs no mapping.
	import { store } from '$lib/manifest/client.svelte';
	import { artifactUrl, dataUrl } from '$lib/paths';
	import type { Sidecar } from '$lib/pdf/sidecar';
	import { can, write, type WriteResult } from '$lib/write';
	import PdfDoc from '$lib/pdf/PdfDoc.svelte';
	import type { Item } from '../item';

	let { item }: { item: Item; onresize: () => void } = $props();

	const ref = $derived(store.manifest?.references[item.id]);
	const place = $derived(item.place ?? {});
	const at = $derived(place.page ?? 1);
	const url = $derived(ref?.artifacts?.pdf ? artifactUrl(ref.artifacts.dir) : '');

	/** The place the link names, mapped by the publisher into rectangles; a box needs no mapping. */
	let lit = $state<{ page: number; rects: number[][] } | null>(null);
	/** The statement's own lines, from the work's sidecar: the card is sized to them and scrolls when they are longer. */
	let statement = $state<{ page: number; rects: number[][] } | null>(null);

	$effect(() => {
		const result = place.result;
		statement = null;
		if (!result || !ref?.spans) return;
		let dropped = false;
		fetch(dataUrl(ref.spans.path))
			.then((r) => (r.ok ? (r.json() as Promise<Sidecar>) : null))
			.then((j) => {
				const rects = j?.quads?.[result];
				if (!dropped && rects?.length) statement = { page: at, rects };
			})
			.catch(() => {});
		return () => {
			dropped = true;
		};
	});

	$effect(() => {
		lit = null;
		if (place.box) {
			lit = { page: at, rects: [[...place.box]] };
			return;
		}
		if (!place.span && !place.quote) return;
		let dropped = false;
		const citekey = item.id;
		void can('locate').then((ok) => {
			if (!ok || dropped) return;
			const body = place.span ? { citekey, page: at, span: place.span } : { citekey, page: at, text: place.quote };
			return write('locate', body).then((res: WriteResult & { anchor?: { quads?: number[][] } }) => {
				if (!dropped && res.ok && res.anchor?.quads?.length) lit = { page: at, rects: res.anchor.quads };
			});
		});
		return () => {
			dropped = true;
		};
	});

	/**
	 * How large the page is drawn inside the card, and how tall the card then is.
	 *
	 * The card is a window `CARD_WIDTH` wide, and the page is drawn at 115% of it: a paper's margins are not what the reader hovered, so letting them fall outside the window buys back the width the text is read at. `PAGE_WIDTH` is US Letter; a page of another size shifts the zoom a little either way.
	 */
	const CARD_WIDTH = 43.2 * 16;
	const PAGE_WIDTH = 612;
	const CARD_SCALE = (CARD_WIDTH * 1.15) / PAGE_WIDTH;
	const cropHeight = $derived.by(() => {
		const rs = statement?.rects ?? [];
		if (!rs.length) return 0;
		const top = Math.min(...rs.map((r) => r[1]));
		const bottom = Math.max(...rs.map((r) => r[3]));
		const line = Math.max(...rs.map((r) => r[3] - r[1]));
		return Math.round((bottom - top + line * 4) * CARD_SCALE);
	});
</script>

{#if url}
	<!-- Sized to the statement and a line either side where the sidecar knows where it is, and scrolled to it by the renderer's own `focus`; a statement longer than the card scrolls inside it rather than being shrunk until it cannot be read. A work with no located statement keeps the standing page-sized card. -->
	<div class="page-card" class:cropped={!!statement} style={statement ? `height: ${Math.min(cropHeight, 39.6 * 16)}px` : undefined} data-testid="preview-page">
		<PdfDoc
			{url}
			page={statement?.page ?? at}
			scale={statement ? CARD_SCALE : 0.99}
			window={0}
			spans={statement
				? [{ id: '_stmt', page: statement.page, rects: statement.rects, transient: true }]
				: lit
					? [{ id: '_locator', page: lit.page, rects: lit.rects, transient: true }]
					: []}
			focus={statement ? '_stmt' : lit ? '_locator' : ''}
		/>
	</div>
{/if}

<style>
	/* The page is drawn wider than the card on purpose and trimmed equally at both margins, so it centres plainly here; a pane uses `safe` centring so a page wider than it stays reachable. */
	.page-card :global(.column) {
		align-items: center;
	}
	.page-card {
		width: 43.2rem;
		height: 28.8rem;
		overflow: hidden;
		background: var(--sheet);
	}
	/* **The card marks where the result starts; it does not outline it.** A dot in the margin beside the first line says where it begins and leaves the text alone. */
	.page-card :global(.mark.transient) {
		outline: none;
		background: none;
	}
	.page-card :global(.marks > .mark.transient:first-child)::before {
		content: '';
		position: absolute;
		left: -0.7em;
		top: 50%;
		width: 0.5em;
		height: 0.5em;
		transform: translateY(-50%);
		border-radius: 50%;
		background: rgb(224 168 32 / 0.55);
	}
	/* the height comes from the statement; the floor keeps a one-line result from being a sliver */
	.page-card.cropped {
		min-height: 9rem;
		max-height: 39.6rem;
	}
</style>
