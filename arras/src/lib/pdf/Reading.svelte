<script lang="ts">
	// Reading one work (plan 0.13 item 5, item 6): the paper, its results and the notes on its pages drawn over it, and
	// the composer at the place a reader selects. Content only -- the split, the discussion and the composer beside it
	// are the Library View's, so there is one frame and not one inside another.
	//
	// **The session selection governs the page.** What the panel is showing is what the page marks; a note the
	// selection hides is counted in the header rather than drawn. **Two notes on one place are one mark** carrying
	// both, as a phrase shared in a fragment is (§8): stacked translucent highlights muddy immediately, and the box that
	// opens holds every lead comment in place.
	//
	// **A locator in the URL is drawn transiently** (§3, §6): `span=`, `box=` or `quote=` name a place a message or a
	// link pointed at, lit while the URL carries it and not recorded; `annot=` names a note by id and focuses its mark.
	import { artifactUrl, dataUrl } from '$lib/paths';
	import { store } from '$lib/manifest/client.svelte';
	import { hidden, visible } from '$lib/sessions/sessions.svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { ui } from '$lib/ui.svelte';
	import { inlineComments, type InlineComments } from '$lib/fragments/expand';
	import { repliesTo } from '$lib/annotations';
	import { travel as goTo } from '$lib/travel/travel';
	import AnnotationBox from '$lib/components/AnnotationBox.svelte';
	import type { Sidecar } from './sidecar';
	import type { Reference } from '$lib/manifest/types';
	import type { WorkLink } from '$lib/worklink';
	import { write, type WriteResult } from '$lib/write';
	import PdfDoc from './PdfDoc.svelte';
	import type { PdfView } from './view.svelte';
	import NoteAt from './NoteAt.svelte';
	import { clearPending, showPending } from '$lib/fragments/pending';
	import { onDestroy } from 'svelte';

	let {
		citekey,
		ref,
		page,
		locator = null,
		view,
	}: {
		citekey: string;
		ref: Reference;
		page: number;
		/** A place the URL points at: `span`, `box`, `quote` are lit transiently; `annot` focuses a note's mark. */
		locator?: WorkLink | null;
		/** The reader's view, when the page draws the controls in a rail of its own. */
		view?: PdfView;
	} = $props();

	const url = $derived(ref.artifacts?.pdf ? artifactUrl(ref.artifacts.dir) : '');

	$effect(() => {
		const drop = () => {
			if (offered && !(window.getSelection()?.toString().trim())) offered = null;
		};
		document.addEventListener('selectionchange', drop);
		return () => document.removeEventListener('selectionchange', drop);
	});
	let spans = $state<Sidecar | null>(null);
	let active = $state('');
	/** The place a note is being written against, while the composer is open. */
	let noting = $state<{ page: number; text?: string; rects?: number[][]; at: { left: number; top: number; width: number; height: number } } | null>(null);
	/**
	 * A selection waiting to be made into a note, if the reader wants one.
	 *
	 * **Selecting text is not a request to annotate it.** The composer used to open on every mouse-up, which meant the
	 * ordinary thing a reader does with a paper — highlight a phrase and copy it — was impossible without a form
	 * appearing over the page. Now the selection stays live and a single *annotate* chip offers the other thing; the
	 * box tool has no such ambiguity and still opens the composer directly.
	 */
	let offered = $state<{ page: number; text: string; at: { left: number; top: number; width: number; height: number }; range?: Range } | null>(null);
	onDestroy(clearPending);
	/** The composer closed, written or not: the place it was lit for goes out. */
	const done = () => {
		noting = null;
		clearPending();
	};

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

	// an open box over the page is re-read when the manifest is, so the surface that fired a write shows it
	$effect(() => {
		void store.manifest;
		boxes?.refresh();
	});

	/** The notes on this work's pages, top-level and standing. The session selection governs the page (plan 0.13 §7): what the panel is showing is what the page marks, and a note the selection hides is counted rather than drawn. */
	const notes = $derived(
		Object.values(store.manifest?.annotations ?? {}).filter(
			(a) => a.target.work === citekey && !a.discarded && a.in_reply_to === null && (a.target.page ?? 0) > 0
		)
	);
	const kept = $derived(hidden(store.manifest, notes));
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
		const body: Record<string, unknown> = l.span ? { citekey, page: at, span: l.span } : { citekey, page: at, text: l.quote };
		void write('locate', body).then((res: WriteResult & { anchor?: { quads?: number[][] } }) => {
			if (dropped) return;
			lit = res.ok && res.anchor?.quads?.length ? { page: at, rects: res.anchor.quads } : null;
		});
		return () => {
			dropped = true;
		};
	});

	type Drawn = { id: string; page: number; rects: number[][]; ids?: string[]; note?: boolean; kind?: string; transient?: boolean };
	/** Every anchor's geometry, by the page it is on: the work's results, the notes the selection shows -- stacked where they share a place -- and the lit locator. The document view draws what belongs to each page it renders. */
	const drawn = $derived.by<Drawn[]>(() => {
		const out: Drawn[] = Object.entries(spans?.quads ?? {})
			.map(([id, rects]) => ({ id, page: ref.results?.[id]?.page ?? 0, rects }))
			.filter((s) => s.page > 0);
		const stacked = new Map<string, Drawn>();
		for (const a of notes) {
			const rects = spans?.marks?.[a.id];
			if (!rects || !visible(store.manifest, a)) continue;
			const key = `${a.target.page}:` + rects.map((r) => r.map((v) => Math.round(v)).join(',')).join(';');
			const same = stacked.get(key);
			if (same) same.ids!.push(a.id);
			else stacked.set(key, { id: a.id, ids: [a.id], page: a.target.page ?? 0, rects, note: true, kind: a.kind });
		}
		out.push(...stacked.values());
		if (lit) out.push({ id: '_locator', page: lit.page, rects: lit.rects, transient: true });
		// a box drawn for a note stays drawn while the note is written
		if (noting?.rects) out.push({ id: '_noting', page: noting.page, rects: noting.rects, transient: true });
		return out;
	});
	// `result=` names a result of this work, whose rectangles the sidecar already carries under that same id, so it is
	// focused directly rather than resolved: a link to a cited result works with no publisher answering.
	const focusOn = $derived(locator?.annot ?? locator?.result ?? (lit ? '_locator' : active));
	let at = $state(0);
	const onPage = $derived(drawn.filter((s) => s.page === (at || page)));

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

	/** Where a box over the page lives: the content pane, since a mark sits in an overlay that takes no pointer events. */
	let pane = $state<HTMLElement | null>(null);
	let boxes: InlineComments | null = null;
	// One controller for the life of the pane, reading the manifest at the moment a box opens: recreating it on every
	// poll would shut whatever the reader had open, which is the failure `Fragment.svelte` has been patched for twice.
	$effect(() => {
		const host = pane;
		if (!host) {
			boxes?.destroy();
			boxes = null;
			return;
		}
		// `inline` is the Authoring View's alone: a PDF page cannot reflow, so it opens floating here
		boxes = inlineComments(() => store.manifest, true, { host });
		return () => {
			boxes?.destroy();
			boxes = null;
		};
	});


	function travel(e: { id: string; ids: string[]; travel: boolean; note: boolean; el: HTMLElement }): void {
		active = e.id;
		if (e.note) ui.activeAnnotation = e.id;
		if (e.travel) {
			// a note travels to its row in the discussion; a result to its entry beside the page
			const to = e.note
				? document.querySelector(`[data-testid="beside-${CSS.escape(e.id)}"]`)
				: document.querySelector(`[data-anchored="${CSS.escape(e.id)}"]`);
			goTo(to, e.el);
			return;
		}
		if (e.note && boxes) boxes.toggle(e.el, e.ids);
	}
</script>

<section class="reading" data-testid="reading">
	{#if url}
		{#if kept}<p class="kept" data-testid="reading-hidden">{kept} note{kept === 1 ? '' : 's'} hidden by the session being shown</p>{/if}
		<div class="paper" bind:this={pane}>
			<PdfDoc
				{url}
				{page}
				{view}
				spans={drawn}
				focus={focusOn}
				onselect={(e) => {
					const sel = window.getSelection();
					offered = { page: e.page, text: e.text, at: e.client, range: sel?.rangeCount ? sel.getRangeAt(0).cloneRange() : undefined };
				}}
				onbox={(e) => ((offered = null), (noting = { page: e.page, rects: e.rects, at: e.client }))}
				onmark={travel}
				onpage={(e) => (at = e.page)}
			/>
		</div>
	{:else}
		<p class="muted" data-testid="reading-absent">{absent}</p>
	{/if}
	{#if offered && !noting}
		<!-- Above the selection, out of the way of the words it is about, and gone the moment the selection is. -->
		<button
			type="button"
			class="offer"
			data-testid="annotate-offer"
			style="left: {Math.round(offered.at.left)}px; top: {Math.round(offered.at.top - 34)}px;"
			onclick={() => {
				showPending(offered!.range ?? null);
				noting = { page: offered!.page, text: offered!.text, at: offered!.at };
				offered = null;
			}}>annotate</button
		>
	{/if}
	{#if noting}
		<NoteAt
			{citekey}
			page={noting.page}
			text={noting.text ?? ''}
			rects={noting.rects}
			at={noting.at}
			onwritten={() => {
				done();
				store.refresh();
			}}
			onclose={done}
		/>
	{/if}
</section>

<style>
	/* Fixed, because the rect it is placed by is the selection's own client rect, and inset like a floating box so it
	   never hangs off the window. */
	.offer {
		position: fixed;
		z-index: 30;
		font-family: var(--sans);
		font-size: 11px;
		line-height: 1;
		padding: 5px 10px;
		border-radius: var(--rad-pill, 4px);
		border: 1px solid var(--annotation, #c05621);
		background: var(--sheet, #fff);
		color: var(--annotation, #c05621);
		box-shadow: 0 2px 8px rgb(0 0 0 / 14%);
		cursor: pointer;
	}
	.offer:hover {
		background: var(--annotation, #c05621);
		color: var(--sheet, #fff);
	}

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
	.paper > :global(.doc) {
		flex: 1 1 auto;
		min-width: 0;
	}
	.kept {
		margin: 0;
		padding: 2px 8px;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-faint);
	}
</style>
