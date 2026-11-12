<script lang="ts">
	// Reading one work (plan 0.13 item 5, item 6): the paper, its results drawn over it where a link lands, and its annotations, annotated and read as a document's are (`MarkedDoc`). Content only -- the split and the discussion are the Library View's, so there is one frame and not one inside another.
	//
	// **Every annotation on the page is drawn** by the desk (`desk.svelte.ts`) in its look, unless the pane hides them all; a settled one only while the settled control is on. One drawn with a tool records its place; one anchored by its words or a box is placed by the work's sidecar.
	//
	// **A locator in the URL is drawn transiently** (§3, §6): `span=`, `box=` or `quote=` name a place a message or a link pointed at, lit while the URL carries it and not recorded; `annot=` names an annotation by id and focuses its mark.
	//
	// **It opens where the reader last was, unless a link sends it elsewhere.** A link's place wins for as long as it is in force, and where it lands is then where the reader is. Once they move by their own hand nothing sends them back to it, and once its page has left the view the link is done with: its place comes off the item and so off the URL, so a reload returns to where they went.
	import { artifactUrl, dataUrl } from '$lib/paths';
	import { paperPlace } from './place.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { paneOf } from '$lib/workspace/state.svelte';
	import { workspace } from '$lib/workspace/store.svelte';
	import { workState } from '$lib/workspace/state.svelte';
	import type { Sidecar } from './sidecar';
	import type { Reference } from '$lib/manifest/types';
	import type { WorkLink } from '$lib/worklink';
	import { write, type WriteResult } from '$lib/write';
	import { MarkDesk } from './desk.svelte';
	import MarkedDoc from './MarkedDoc.svelte';
	import { mergeLines } from './marks';
	import type { PdfView } from './view.svelte';
	import QuoteChip from '$lib/review/QuoteChip.svelte';
	import { here } from '$lib/here.svelte';

	let {
		citekey,
		ref,
		page,
		seq = 0,
		locator = null,
		view,
		onleft,
	}: {
		citekey: string;
		ref: Reference;
		page: number;
		/** Changed each time a link sends the reader to a place, so being sent again lands again; 0 where no link names one. */
		seq?: number;
		/** A place the URL points at: `span`, `box`, `quote` are lit transiently; `annot` focuses an annotation's mark. */
		locator?: WorkLink | null;
		/** The reader's view, which the controls drawn beside the paper act on and which outlives this component. */
		view: PdfView;
		/** The reader has moved off the page the link sent them to. */
		onleft?: () => void;
	} = $props();

	const url = $derived(ref.artifacts?.pdf ? artifactUrl(ref.artifacts.dir) : '');
	// the item's annotating, which the toolbar shares; a work's pages are an item's only inside a pane
	const held = $derived(workState({ kind: 'work', id: citekey }));
	// a work's pages in a pane hide every annotation while the pane does
	const holder = paneOf();
	const hide = $derived(holder ? workspace.hidesNotes(holder.index) : false);
	const desk = new MarkDesk(() => ({ on: citekey, owns: (a) => a.target.work === citekey, rectsOf: (a) => spans?.marks?.[a.id], url, name: `${citekey}.pdf`, notes: held.notes, hidden: hide }));
	// the toolbar's PDF menu acts through it
	$effect(() => {
		const state = held;
		state.desk = desk;
		return () => {
			if (state.desk === desk) state.desk = null;
		};
	});

	$effect(() => {
		const drop = () => {
			if (offered && !window.getSelection()?.toString().trim()) offered = null;
		};
		document.addEventListener('selectionchange', drop);
		return () => document.removeEventListener('selectionchange', drop);
	});
	let spans = $state<Sidecar | null>(null);
	let active = $state('');
	/** A bare selection, offered Quote: selecting words is not a request to annotate them, which Annotate is for. */
	let offered = $state<{ page: number; text: string; lines: number[][]; at: { left: number; top: number; width: number; height: number }; range?: Range } | null>(null);
	/** Where a quote from page `n` came from, as a link an agent can follow: the work by its identifier, else its citekey. */
	const quoteHref = (n: number): string => (ref.work ? `cited:${ref.work}?page=${n}` : `quilt:${citekey}`);

	// Fetched by the sidecar's own hash rather than derived from the manifest: the manifest is replaced on every poll,
	// and re-fetching geometry once a second is exactly the re-render this pane must not do. Naming the hash is also
	// what lets a stale copy be noticed while the publisher rebuilds underneath.
	$effect(() => {
		const at = ref.spans;
		if (!at) return;
		let dropped = false;
		fetch(dataUrl(at.path))
			.then((r) => (r.ok ? (r.json() as Promise<Sidecar>) : null))
			.then((j) => {
				if (!dropped) spans = j;
			})
			.catch(() => {});
		return () => {
			dropped = true;
		};
	});

	/** The place the URL points at, mapped by loom into rectangles, while the URL carries it. */
	let lit = $state<{ page: number; rects: number[][] } | null>(null);
	$effect(() => {
		const l = locator;
		if (!l || (!l.span && !l.box && !l.quote)) {
			lit = null;
			return;
		}
		const at = l.page ?? page;
		if (l.box) {
			lit = { page: at, rects: [[...l.box]] };
			return;
		}
		let dropped = false;
		// a quote with no page is looked for across the work, and lit on the page loom finds it on
		const body: Record<string, unknown> = l.span ? { citekey, page: at, span: l.span } : { citekey, ...(l.page ? { page: l.page } : {}), text: l.quote };
		void write('locate', body).then((res: WriteResult & { page?: number; anchor?: { quads?: number[][] } }) => {
			if (dropped) return;
			lit = res.ok && res.anchor?.quads?.length ? { page: res.page ?? at, rects: res.anchor.quads } : null;
		});
		return () => {
			dropped = true;
		};
	});
	// A link in force sends the paper to the page loom lit, which a quote with no page learns only from the answer, else the one asked for: opened at page 1 while lighting page 2, the place the renderer keeps across a redraw is page 1's, and putting it back cancels the landing's scroll.
	const place = paperPlace(
		() => view,
		() => ({ seq, page: lit?.page ?? page }),
		() => onleft?.()
	);

	type Drawn = { id: string; page: number; rects: number[][]; transient?: boolean };
	/** The geometry drawn besides the annotations, by the page it is on: the work's results, where a link lands on one, and the lit locator. */
	const drawn = $derived.by<Drawn[]>(() => {
		const out: Drawn[] = Object.entries(spans?.quads ?? {})
			.map(([id, rects]) => ({ id, page: ref.results?.[id]?.page ?? 0, rects }))
			.filter((s) => s.page > 0);
		if (lit) out.push({ id: '_locator', page: lit.page, rects: lit.rects, transient: true });
		return out;
	});
	// `result=` names a result of this work, whose rectangles the sidecar already carries under that same id, so it is focused directly rather than resolved: a link to a cited result works with no publisher answering.
	const focusOn = $derived(locator?.annot ?? locator?.result ?? (lit ? '_locator' : active));

	// Three states, not two. A work whose LaTeX is in the store but whose PDF is not has a digest worth trusting and no
	// page to show it against, which is neither "nothing here" nor "we could not get it" — and page-numbered locators
	// into it are unverified, because the pagination a reader will open is the publisher's and not ours.
	const absent = $derived(
		ref.unreadable
			? `Declared unreadable: ${ref.unreadable.why}`
			: ref.artifacts?.source
				? 'The LaTeX of this paper is here but its PDF is not, so there is no page to show. Locators into it are unverified against the document a reader would open.'
				: 'No copy of this paper on this machine.'
	);

</script>

<section class="reading" data-testid="reading">
	{#if url}
		<div class="paper">
			<MarkedDoc
				{desk}
				{view}
				notes={held.notes}
				{url}
				name="{citekey}.pdf"
				page={place.opening.page}
				share={place.opening.share}
				seq={place.opening.seq}
				spans={drawn}
				focus={focusOn}
				lands={!place.spent}
				onselect={(e) => {
					const sel = window.getSelection();
					offered = { page: e.page, text: e.text, lines: mergeLines(e.rects), at: e.client, range: sel?.rangeCount ? sel.getRangeAt(0).cloneRange() : undefined };
					here.selection = { item: `work:${citekey}`, page: e.page, text: e.text, rects: e.rects };
				}}
				onregion={(e) => {
					offered = null;
					here.region = { item: `work:${citekey}`, page: e.page, rects: e.rects };
				}}
				onmoved={(e) => {
					// what was being looked at is left behind with the place, so nothing lands back on it
					active = '';
					place.moved(e);
				}}
			/>
		</div>
	{:else}
		<p class="muted" data-testid="reading-absent">{absent}</p>
	{/if}
	{#if offered}
		<QuoteChip at={offered.at} range={offered.range} words={offered.text} name="{citekey} p. {offered.page}" href={quoteHref(offered.page)} ondone={() => (offered = null)} />
	{/if}
</section>

<style>
	.reading {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}
	.paper {
		position: relative;
		flex: 1 1 auto;
		min-height: 0;
		display: flex;
	}
	.paper > :global(.marked) {
		flex: 1 1 auto;
		min-width: 0;
	}
</style>
