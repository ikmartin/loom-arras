<script lang="ts">
	// A PDF that is annotated as a document is: the renderer with every annotation on its pages drawn in its look, the one popup opening from a mark, the item's annotating (`Annotating`) told the annotations in reading order (page, then top, then left; the detached last), and the pages editor over it.
	//
	// **Annotate** on, selected words are marked at once in the look in hand and its style, and a drag over no words marks the region; a type that asks something opens the popup to say it first. **Comment** on, a press leaves a pin, written once it says something. The PDF's own tools draw ink, words on the page, a box, an oval or an arrow in the look in hand; words on the page are written once they say something. With no tool on, a selection goes to the caller, which offers Quote, and Alt-drag draws a region to comment on.
	import { tick, untrack, type ComponentProps } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import AnnotationPopup from '$lib/review/AnnotationPopup.svelte';
	import SideHost from '$lib/review/SideHost.svelte';
	import { hand, typeById, type Annotating, type Draft } from '$lib/review/annotating.svelte';
	import { say } from '$lib/review/toasts.svelte';
	import { popups, placeAt, type Popups } from '$lib/fragments/popup';
	import { ui } from '$lib/ui.svelte';
	import type { MarkDesk } from './desk.svelte';
	import { bound, mergeLines, type MarkKind } from './marks';
	import PagesEditor from './PagesEditor.svelte';
	import PdfDoc from './PdfDoc.svelte';
	import type { PdfView } from './view.svelte';

	type DocProps = ComponentProps<typeof PdfDoc>;
	type Box = { left: number; top: number; width: number; height: number };

	let {
		desk,
		view,
		notes,
		url,
		name,
		dir = '',
		page,
		share,
		seq,
		spans,
		focus = '',
		lands = true,
		onselect,
		onregion,
		onpage,
		onlink,
		onmoved
	}: {
		desk: MarkDesk;
		view: PdfView;
		/** The item's annotating: the tool in hand, the order, the popup's opening. */
		notes: Annotating;
		url: string;
		/** The PDF's file name, and how a new annotation's popup names its place. */
		name: string;
		/** The project directory a page edit saves into by default. */
		dir?: string;
		page?: DocProps['page'];
		share?: DocProps['share'];
		seq?: DocProps['seq'];
		spans?: DocProps['spans'];
		/** What a link names: a result to land on, or an annotation, opened on arrival. */
		focus?: string;
		lands?: DocProps['lands'];
		/** Words selected with no tool on, which the caller offers Quote for. */
		onselect?: DocProps['onselect'];
		/** A region drawn on a page, whatever is made of it, for the reader's place. */
		onregion?: DocProps['onbox'];
		onpage?: DocProps['onpage'];
		onlink?: DocProps['onlink'];
		onmoved?: DocProps['onmoved'];
	} = $props();

	let paper = $state<HTMLElement | null>(null);
	const annotating = $derived(notes.tool === 'annotate' && desk.writes);
	/** The pin is Comment's, which takes the pointer from the page as a drawing tool does. */
	const tool = $derived(notes.tool === 'comment' && desk.writes ? 'pin' : view.tool);

	// what the manifest now says lets go of what was on its way
	$effect(() => {
		void store.manifest;
		untrack(() => desk.settle());
	});

	// Annotate and Comment, and the PDF's drawing tools, are one hand: taking one puts the other down
	$effect(() => {
		if (notes.tool && view.tool !== 'select') untrack(() => (view.tool = 'select'));
	});
	$effect(() => {
		if (view.tool !== 'select' && notes.tool) untrack(() => (notes.tool = null));
	});

	// one popup over the paper, opened from a mark, the margin's lists, the stepper or a link
	let popup: Popups | null = null;
	$effect(() => {
		const host = paper;
		if (!host) return;
		const made = popups(() => store.manifest, {
			host,
			onopen: (id) => {
				notes.open = id;
				desk.selected = id ?? '';
			}
		});
		popup = made;
		notes.close = () => made.close();
		notes.show = (id) => show(id);
		return () => {
			made.destroy();
			if (popup === made) popup = null;
		};
	});

	/** Turn to annotation `id`'s page and open its popup at its mark once the page has drawn it; false when it has no place on a page. */
	function show(id: string): boolean {
		const m = desk.marks.find((x) => x.id === id);
		if (!m || !paper) return false;
		const host = paper;
		const at = () => host.querySelector<HTMLElement>(`[data-annotation="${CSS.escape(id)}"]`);
		if (!at()) view.goTo(m.page);
		let tries = 0;
		const look = () => {
			if (at() && popup) {
				popup.open(host, id, true);
				return;
			}
			if (++tries < 40) setTimeout(look, 100);
		};
		look();
		return true;
	}

	/** Open the popup on an annotation just written, once it is drawn. A work's sidecar places its words after the manifest that holds it arrives, so this keeps trying for a few seconds. */
	function showWhenDrawn(id: string, tries = 60): void {
		if (show(id) || tries <= 0) return;
		setTimeout(() => showWhenDrawn(id, tries - 1), 100);
	}

	// the annotations in reading order: by page, then down it, then across; those with no place last
	$effect(() => {
		const order = desk.placed
			.map(({ a, m }) => ({ id: a.id, at: m ? [m.page, bound(m.rects)[1], bound(m.rects)[0]] : [Infinity, 0, 0] }))
			.sort((x, y) => x.at[0] - y.at[0] || x.at[1] - y.at[1] || x.at[2] - y.at[2])
			.map((x) => x.id);
		untrack(() => {
			if (order.join(' ') !== notes.order.join(' ')) notes.order = order;
			notes.ready = order.length > 0;
		});
	});

	// a link to an annotation arrives with its popup open, once its mark is drawn
	let arrived = '';
	$effect(() => {
		const id = focus;
		void desk.marks.length;
		if (!id || !lands || arrived === `${id}#${seq}`) return;
		untrack(() => {
			if (show(id)) arrived = `${id}#${seq}`;
		});
	});

	/** A new annotation being written in the popup, and where it stands. */
	let drafting = $state<{ draft: Draft; at: Box } | null>(null);

	function openDraft(extra: Record<string, unknown>, at: Box, lit: { page: number; kind: MarkKind; rects: number[][] }): void {
		popup?.close();
		desk.lit = { id: 'lit', page: lit.page, kind: lit.kind, rects: lit.rects, body: '', plain: true };
		drafting = { draft: { target: desk.surface().on, name: `${name} p. ${lit.page}`, extra }, at };
	}

	function closeDraft(): void {
		drafting = null;
		desk.lit = null;
	}

	/** Whether the type in hand asks something, so words marked with it are said first. */
	const asks = () => !!typeById(store.manifest, hand.type)?.open;

	function selected(e: { page: number; text: string; rects: number[][]; client: Box }): void {
		if (!annotating) return onselect?.(e);
		window.getSelection()?.removeAllRanges();
		const rects = mergeLines(e.rects);
		if (asks()) openDraft({ page: e.page, rects, quote: e.text }, e.client, { page: e.page, kind: desk.style(), rects });
		else desk.markWords(e);
	}

	function boxed(e: { page: number; rects: number[][]; client: Box }): void {
		onregion?.(e);
		if (!desk.writes) return;
		if (annotating && !asks()) return desk.markRegion(e);
		// with no tool, a region drawn with Alt is commented on; one Annotate drew with a type that asks something says it first
		openDraft({ page: e.page, rects: e.rects }, e.client, { page: e.page, kind: annotating ? desk.style() : 'box', rects: e.rects });
	}

	function drawn(e: { kind: MarkKind; page: number; rects?: number[][]; strokes?: number[][]; client: Box }): void {
		if (e.kind === 'pin' || e.kind === 'text') {
			// a pin and words on the page say something, so they are written from the popup; Comment goes down once used
			if (e.kind === 'pin') notes.tool = null;
			openDraft({ page: e.page, rects: e.rects ?? [], mark: e.kind }, e.client, { page: e.page, kind: e.kind, rects: e.rects ?? [] });
			return;
		}
		desk.draw(e);
	}

	/** Put the draft's popup at its place once it is drawn, and again as it grows. */
	function placed(host: HTMLElement, at: Box) {
		let r = at;
		const go = () => placeAt(host, { left: r.left, top: r.top, bottom: r.top + r.height });
		const sized = new ResizeObserver(go);
		sized.observe(host);
		go();
		return {
			update(next: Box) {
				r = next;
				go();
			},
			destroy: () => sized.disconnect()
		};
	}

	$effect(() => {
		if (!drafting) return;
		const away = (e: PointerEvent) => {
			const t = e.target as Element | null;
			if (!t?.closest?.('.ann-popup-host, [data-testid="settings-window"]')) closeDraft();
		};
		document.addEventListener('pointerdown', away, true);
		return () => document.removeEventListener('pointerdown', away, true);
	});

	// Escape closes a draft, then puts down the tool in hand; a popup open takes it first
	$effect(() => {
		const key = (e: KeyboardEvent) => {
			if (e.key !== 'Escape' || e.defaultPrevented) return;
			if (drafting) {
				e.preventDefault();
				return closeDraft();
			}
			if (view.tool !== 'select') {
				desk.flush();
				view.tool = 'select';
			} else if (notes.tool) notes.tool = null;
		};
		document.addEventListener('keydown', key);
		return () => document.removeEventListener('keydown', key);
	});

	// the tool is put down: the lines of ink drawn with it are one mark
	$effect(() => {
		if (view.tool !== 'ink') untrack(() => desk.flush());
	});

	// the count of what the PDF itself holds, for the PDF menu's Take in
	$effect(() => {
		if (desk.writes) void untrack(() => desk.countHere());
	});
</script>

<div class="marked" class:show-settled={ui.showSettled} class:armed={annotating} class:with-side={!!notes.side} data-testid="marked-doc">
	<div class="paper" bind:this={paper}>
		<PdfDoc
			{url}
			{page}
			{share}
			{seq}
			{view}
			{spans}
			{focus}
			{lands}
			{tool}
			regions={annotating}
			marks={desk.marks}
			selected={desk.selected}
			hide={desk.hides}
			onselect={selected}
			onbox={boxed}
			{onpage}
			{onlink}
			{onmoved}
			ondraw={drawn}
			onpick={(e) => (e.id && paper ? popup?.open(paper, e.id, false) : popup?.close())}
			onmove={(e) => {
				desk.move(e);
				// the popup stands against the mark where it now is, clear of its handles
				void tick().then(() => popup?.place());
			}}
			onembedded={(e) => say({ title: `${e.subtype} in the PDF${e.by ? `, by ${e.by}` : ''}`, words: e.body, lines: [desk.writes ? 'Take it in from the PDF menu to answer or resolve it here.' : 'Held in the file.'] })}
		/>
	</div>
	{#if desk.pages}
		<PagesEditor {desk} {url} {name} {dir} onclose={() => (desk.pages = false)} />
	{/if}
</div>
<SideHost {notes} />
{#if drafting}
	<aside class="ann-popup-host" use:placed={drafting.at} data-testid="draft-host">
		<AnnotationPopup
			draft={drafting.draft}
			onclose={closeDraft}
			onwritten={(id) => {
				closeDraft();
				if (!id) return;
				void store.refresh().then(() => showWhenDrawn(id));
			}}
		/>
	</aside>
{/if}

<style>
	.marked {
		display: flex;
		flex-direction: column;
		flex: 1 1 auto;
		min-height: 0;
		height: 100%;
	}
	.marked.with-side {
		padding-right: 310px;
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
</style>
