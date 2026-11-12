<script lang="ts">
	// Annotating on the corpus's own text, a node's or a document's: what the toolbar's tools do here.
	//
	// **Annotate** on, selected words are marked at once in the look in hand, and Add comment stands at their end for a moment; a type that stays open until resolved asks something, so its words open the popup to say it first, since loom takes such an annotation only with words. **Comment** on, a click leaves a comment at the place clicked, on the result it is in, and turns the tool off. With neither on, a selection offers **Quote**, which copies the words and where they came from and writes nothing. Alt-drag draws a box round what a selection cannot hold: a labelled equation is noted as itself, anything else as the words of the block under the box.
	//
	// A quote is what was selected with each formula it touches given as its TeX, the form loom finds in the source, so a selection across `$c$` anchors where the words on screen alone would not.
	import { untrack, type Snippet } from 'svelte';
	import { onDestroy } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { can } from '$lib/write';
	import { annotate as record } from '$lib/review/history.svelte';
	import { linkName } from '$lib/workspace/names';
	import AnnotationPopup from '$lib/review/AnnotationPopup.svelte';
	import AtSelection from '$lib/review/AtSelection.svelte';
	import QuoteChip from '$lib/review/QuoteChip.svelte';
	import { hand, handPayload, typeById, type Annotating, type Draft } from '$lib/review/annotating.svelte';
	import { say } from '$lib/review/toasts.svelte';
	import { placeAt } from './popup';
	import { quoteOf, keyOf, texOf } from './quote';
	import { clearPending, showPending } from './pending';

	let {
		notes,
		fallback,
		in: inDoc = '',
		children
	}: {
		/** The item's annotating: the tool in hand, and the popup's opening. */
		notes: Annotating;
		/** The key a place belongs to when no result encloses it: the node shown, or the document. */
		fallback: string;
		/** The document being read, when the fragment is one: every annotation written here is filed with it. A node's own page passes nothing. */
		in?: string;
		children: Snippet;
	} = $props();

	type Box = { left: number; top: number; width: number; height: number };
	const MIN_BOX = 6;

	let root = $state<HTMLElement | null>(null);
	let allowed = $state(false);
	$effect(() => {
		void can('annotate').then((ok) => (allowed = ok));
	});

	const m = $derived(store.manifest);

	/** A bare selection, offered Quote. */
	let offered = $state<{ words: string; target: string; at: Box; range: Range } | null>(null);
	/** A new annotation being written in the popup, and where the popup stands. */
	let drafting = $state<{ draft: Draft; at: Box } | null>(null);
	/** Words just marked by Annotate, with Add comment at their end for a few seconds. */
	let marked = $state<{ id: string; at: Box } | null>(null);
	let markedTimer: ReturnType<typeof setTimeout> | undefined;

	onDestroy(() => {
		clearPending();
		clearTimeout(markedTimer);
	});

	/** The tool goes off with Escape, as a highlighter is put down. */
	$effect(() => {
		const key = (e: KeyboardEvent) => {
			if (e.key !== 'Escape' || e.defaultPrevented) return;
			if (drafting) {
				e.preventDefault();
				return closeDraft();
			}
			if (notes.tool && !notes.open) notes.tool = null;
		};
		document.addEventListener('keydown', key);
		return () => document.removeEventListener('keydown', key);
	});

	$effect(() => {
		const drop = () => {
			if (offered && !window.getSelection()?.toString().trim()) offered = null;
		};
		document.addEventListener('selectionchange', drop);
		return () => document.removeEventListener('selectionchange', drop);
	});

	// choosing a tool ends whatever the last one offered
	$effect(() => {
		void notes.tool;
		untrack(() => {
			offered = null;
		});
	});

	/** What stands in the fragment without being its text: a popup, the margin, and what compare draws or swaps in. */
	const NOT_TEXT = 'aside, .ann-gutter, .ann-popup-host, .compare-swap, .compare-tag, .compare-gutter';

	function notText(n: Node): boolean {
		const el = n instanceof Element ? n : n.parentElement;
		return !!el?.closest(NOT_TEXT);
	}

	/** A place's name, as the popup's head and a quote's source say it: an equation by its number in its result; else the document and the result in it, or the result alone on its own page. */
	function nameFor(key: string): string {
		if (!m) return key;
		const region = m.regions?.[key];
		if (region) {
			const n = Object.values(region.numbers ?? {})[0]?.number;
			const of = linkName(m, `quilt:${region.container}`);
			return n ? `equation (${n}) in ${of}` : `an equation in ${of}`;
		}
		if (inDoc && key !== inDoc) return `${linkName(m, `quilt:${inDoc}`)}, ${linkName(m, `quilt:${key}`)}`;
		return linkName(m, `quilt:${key}`);
	}

	/** A link to a place: in a document, the document at the result; on a node's page, the result. */
	function hrefFor(key: string): string {
		if (inDoc && key !== inDoc) return `quilt:${inDoc}#${key}`;
		return `quilt:${key}`;
	}

	function rectOfRange(range: Range): Box {
		const r = range.getBoundingClientRect();
		return { left: r.left, top: r.top, width: r.width, height: r.height };
	}

	function endOf(range: Range): Box {
		const last = [...range.getClientRects()].filter((r) => r.width > 0 && r.height > 0).at(-1) ?? range.getBoundingClientRect();
		return { left: last.left, top: last.top, width: last.width, height: last.height };
	}

	function selected(): void {
		if (!root || drawing) return;
		const sel = window.getSelection();
		if (!sel || sel.isCollapsed || !sel.rangeCount) return;
		const range = sel.getRangeAt(0);
		if (!root.contains(range.commonAncestorContainer)) return;
		// only the text's own words: a popup, the margin or compare's drawing stands in the fragment without being its text
		if ([range.startContainer, range.endContainer, range.commonAncestorContainer].some(notText)) return;
		const words = quoteOf(range);
		if (!words) return;
		const target = keyOf(range.commonAncestorContainer, fallback);
		if (notes.tool === 'annotate' && allowed) return void annotate(target, words, range);
		if (notes.tool === 'comment') return;
		offered = { words, target, at: rectOfRange(range), range: range.cloneRange() };
	}

	/** Mark the selected words in the look in hand; a type that asks something opens the popup for its words first. */
	async function annotate(target: string, quote: string, range: Range): Promise<void> {
		const h = hand.value;
		if (typeById(m, h.type)?.open) {
			showPending(range);
			window.getSelection()?.removeAllRanges();
			openDraft({ target, quote, ...(inDoc ? { in: inDoc } : {}), name: nameFor(target) }, rectOfRange(range));
			return;
		}
		const at = endOf(range);
		window.getSelection()?.removeAllRanges();
		const res = await record({ target, quote, ...(inDoc ? { in: inDoc } : {}), ...handPayload(m, h) });
		if (!res.ok) {
			say({ title: 'Not annotated', lines: [res.error?.message ?? 'the publisher refused it'] });
			return;
		}
		const id = (res.result ?? '').split(/\s+/)[0] ?? '';
		clearTimeout(markedTimer);
		marked = id ? { id, at } : null;
		markedTimer = setTimeout(() => (marked = null), 4000);
	}

	/** Open the popup on an annotation just written, once the manifest that holds it has been drawn. */
	async function openWritten(id: string): Promise<void> {
		marked = null;
		await store.refresh();
		for (let i = 0; i < 20; i++) {
			if (notes.show(id)) return;
			await new Promise((r) => setTimeout(r, 100));
		}
	}

	function openDraft(draft: Draft, at: Box): void {
		notes.close();
		offered = null;
		drafting = { draft, at };
	}

	function closeDraft(): void {
		drafting = null;
		clearPending();
	}

	/** A click while Comment is on leaves a comment there: caught before a mark under it opens its popup. */
	function clicked(e: MouseEvent): void {
		if (notes.tool !== 'comment' || !allowed || !root || e.button !== 0) return;
		const on = e.target as Element;
		if (notText(on) || on.closest('a, button, input, textarea, select')) return;
		e.preventDefault();
		e.stopPropagation();
		const target = keyOf(on, fallback);
		notes.tool = null;
		const block = on.closest<HTMLElement>('p, li, .math.display, figure, table, h1, h2, h3, h4, h5, h6');
		if (block) showPending(null, block);
		openDraft({ target, ...(inDoc ? { in: inDoc } : {}), name: nameFor(target) }, { left: e.clientX, top: e.clientY, width: 0, height: 0 });
	}

	/** The box being drawn, in window coordinates. */
	let drawing = $state<{ x: number; y: number; x2: number; y2: number } | null>(null);
	/** A press on a mark while Alt is held: a click on the mark until the pointer moves, a box once it does. */
	let pressed: { x: number; y: number } | null = null;

	function down(e: PointerEvent): void {
		if (!allowed || e.button !== 0 || !e.altKey) return;
		const on = e.target as Element;
		// a press on a link or a control is a click on it, never the start of a box; one in a popup or the margin is not on the text
		if (on.closest('a, button, input, textarea, select') || notText(on)) return;
		if (on.closest('mark.annotation, .annotation-block')) {
			pressed = { x: e.clientX, y: e.clientY };
			return;
		}
		start(e, e.clientX, e.clientY);
	}

	function start(e: PointerEvent, x: number, y: number): void {
		e.preventDefault();
		window.getSelection()?.removeAllRanges();
		offered = null;
		drawing = { x, y, x2: e.clientX, y2: e.clientY };
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
	}

	function move(e: PointerEvent): void {
		if (pressed && Math.hypot(e.clientX - pressed.x, e.clientY - pressed.y) > 4) {
			const from = pressed;
			pressed = null;
			start(e, from.x, from.y);
			return;
		}
		if (drawing) drawing = { ...drawing, x2: e.clientX, y2: e.clientY };
	}

	function up(e: PointerEvent): void {
		pressed = null;
		if (!drawing || !root) return;
		(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
		const box = rectOf(drawing);
		drawing = null;
		if (box.width < MIN_BOX && box.height < MIN_BOX) return;
		const { el, target, text } = placeUnder(root, box);
		showPending(null, el);
		openDraft({ target, ...(text ? { quote: text } : {}), ...(inDoc ? { in: inDoc } : {}), name: nameFor(target) }, box);
	}

	function rectOf(d: { x: number; y: number; x2: number; y2: number }): Box {
		return { left: Math.min(d.x, d.x2), top: Math.min(d.y, d.y2), width: Math.abs(d.x2 - d.x), height: Math.abs(d.y2 - d.y) };
	}

	function overlap(a: DOMRect, b: Box): number {
		const w = Math.min(a.right, b.left + b.width) - Math.max(a.left, b.left);
		const h = Math.min(a.bottom, b.top + b.height) - Math.max(a.top, b.top);
		return w > 0 && h > 0 ? w * h : 0;
	}

	/** What a box was drawn round: a labelled equation as itself, else the words of the block it covers most, else the result it is in. */
	function placeUnder(at: HTMLElement, box: Box): { target: string; text: string; el: HTMLElement | null } {
		let best: { el: HTMLElement; score: number } | null = null;
		for (const el of at.querySelectorAll<HTMLElement>('.math.display[data-label], figure[data-label]')) {
			const score = overlap(el.getBoundingClientRect(), box);
			if (score > (best?.score ?? 0)) best = { el, score };
		}
		if (best) {
			const region = `${keyOf(best.el, fallback)}#${best.el.dataset.label}`;
			if (m?.regions?.[region]) return { target: region, text: '', el: best.el };
			return { target: keyOf(best.el, fallback), text: texOf(best.el), el: best.el };
		}
		let block: { el: HTMLElement; score: number } | null = null;
		for (const el of at.querySelectorAll<HTMLElement>('p[data-src], li[data-src], .math.display[data-src], figure[data-src], table[data-src]')) {
			const score = overlap(el.getBoundingClientRect(), box);
			if (score > (block?.score ?? 0)) block = { el, score };
		}
		if (block) {
			const range = document.createRange();
			range.selectNodeContents(block.el);
			return { target: keyOf(block.el, fallback), text: quoteOf(range), el: block.el };
		}
		return { target: fallback, text: '', el: null };
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

	/** A press outside the draft's popup puts it away, as a press outside any popup does. */
	$effect(() => {
		if (!drafting) return;
		const away = (e: PointerEvent) => {
			const t = e.target as Element | null;
			if (!t?.closest?.('.ann-popup-host, [data-testid="settings-window"]')) closeDraft();
		};
		document.addEventListener('pointerdown', away, true);
		return () => document.removeEventListener('pointerdown', away, true);
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
<div class="fragment-notes" class:armed={notes.tool === 'annotate' && allowed} class:placing={notes.tool === 'comment' && allowed} bind:this={root} onmouseup={selected} onclickcapture={clicked} onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={() => (drawing = null)} data-testid="fragment-notes">
	{@render children()}
</div>

{#if drawing}
	{@const b = rectOf(drawing)}
	<div class="drawn" style="left: {b.left}px; top: {b.top}px; width: {b.width}px; height: {b.height}px;" data-testid="drawn-box"></div>
{/if}
{#if offered && !drafting}
	<QuoteChip at={offered.at} range={offered.range} words={offered.words} name={nameFor(offered.target)} href={hrefFor(offered.target)} ondone={() => (offered = null)} />
{/if}
{#if marked}
	{@const id = marked.id}
	<AtSelection at={marked.at}>
		<button type="button" class="chip" data-testid="add-comment" onclick={() => void openWritten(id)}>Add comment</button>
	</AtSelection>
{/if}
{#if drafting}
	<aside class="ann-popup-host" use:placed={drafting.at} data-testid="draft-host">
		<AnnotationPopup
			draft={drafting.draft}
			onclose={closeDraft}
			onwritten={(id) => {
				closeDraft();
				if (id) void openWritten(id);
			}}
		/>
	</aside>
{/if}

<style>
	.fragment-notes.armed {
		cursor: text;
	}
	.fragment-notes.placing {
		cursor: copy;
	}
	.drawn {
		position: fixed;
		z-index: 30;
		pointer-events: none;
		border: 1.5px dashed var(--accent);
		background: var(--accent-wash);
		border-radius: 2px;
	}
</style>
