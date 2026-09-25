<script lang="ts">
	// Writing on the corpus's own text (plan 0.13.3 phase 4): the two tools a cited work's pages have, on a node's or a document's fragment, so annotating is one act wherever a reader is.
	//
	// **Select** leaves the selection a selection and offers `annotate` at its end, as on a page: highlighting to copy is the ordinary thing to do with text. The note's place is the result the selection is in, and its quote is what was selected, with each formula it touches given as its TeX — loom finds the quote in the source, so a selection across `$c$` anchors where the words on screen alone would not. **Box**, or Alt-drag from select, draws round what a selection cannot hold: a labelled equation is noted as itself, anything else as the words of the block under the box.
	import type { Snippet } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import NoteAt from '$lib/pdf/NoteAt.svelte';
	import AnnotateChip from './AnnotateChip.svelte';
	import type { Tool } from '$lib/pdf/view.svelte';
	import { can } from '$lib/write';
	import { nameOf } from '$lib/workspace/registry';
	import { quoteOf, keyOf, texOf } from './quote';
	import { clearPending, showPending } from './pending';
	import { onDestroy } from 'svelte';

	let {
		holder,
		fallback,
		in: inDoc = '',
		children
	}: {
		/** Where the tool in hand is kept: the item's state, which the rail's tool pair sets. */
		holder: { tool: Tool };
		/** The key a place belongs to when no result encloses it: the node shown, or the document. */
		fallback: string;
		/** The document being read, when the fragment is one: every annotation written here is filed with it (book 7). A node's own page passes nothing. */
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
	/** A selection waiting to be made into a note, if the reader wants one. */
	let offered = $state<{ target: string; text: string; at: Box; range?: Range } | null>(null);
	/** The place a note is being written against, while the composer is open; it stays lit as long as the composer does. */
	let noting = $state<{ target: string; text: string; at: Box } | null>(null);
	onDestroy(clearPending);
	const done = () => {
		noting = null;
		clearPending();
	};
	/** The box being drawn, in window coordinates. */
	let drawing = $state<{ x: number; y: number; x2: number; y2: number } | null>(null);

	const m = $derived(store.manifest);
	const boxing = $derived(holder.tool === 'box');

	function nameFor(key: string): string {
		if (!m) return key;
		const region = m.regions?.[key];
		if (region) {
			const n = Object.values(region.numbers ?? {})[0]?.number;
			const of = m.nodes[region.container] ? nameOf({ kind: 'node', id: region.container }, m) : region.container;
			return n ? `equation (${n}) in ${of}` : `an equation in ${of}`;
		}
		if (m.nodes[key]) return nameOf({ kind: 'node', id: key }, m);
		if (m.masters.some((x) => x.path === key)) return key.split('/').pop() ?? key;
		return key;
	}

	$effect(() => {
		const drop = () => {
			if (offered && !window.getSelection()?.toString().trim()) offered = null;
		};
		document.addEventListener('selectionchange', drop);
		return () => document.removeEventListener('selectionchange', drop);
	});

	function selected(): void {
		if (!allowed || boxing || !root) return;
		const sel = window.getSelection();
		if (!sel || sel.isCollapsed || !sel.rangeCount) return;
		const range = sel.getRangeAt(0);
		if (!root.contains(range.commonAncestorContainer)) return;
		const text = quoteOf(range);
		if (!text) return;
		const r = range.getBoundingClientRect();
		offered = { target: keyOf(range.commonAncestorContainer, fallback), text, at: { left: r.left, top: r.top, width: r.width, height: r.height }, range: range.cloneRange() };
	}

	/** A press on a mark while the box tool is chosen: a click on the mark until the pointer moves, a box once it does. */
	let pressed: { x: number; y: number } | null = null;

	function down(e: PointerEvent): void {
		if (!allowed || e.button !== 0 || !(boxing || e.altKey)) return;
		const on = e.target as Element;
		// a press on a link or a control is a click on it, never the start of a box
		if (on.closest('a, button, input, textarea, select')) return;
		// On a mark, only the box tool draws, and only once the pointer moves: an annotated equation is still boxable for a second note, and a click without a drag still opens the mark (study F4).
		if (on.closest('mark.annotation, .annotation-block')) {
			if (boxing) pressed = { x: e.clientX, y: e.clientY };
			return;
		}
		start(e, e.clientX, e.clientY);
	}

	function start(e: PointerEvent, x: number, y: number): void {
		e.preventDefault();
		// a drag begun on a mark has already started selecting its words; a box is not a selection
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
		const { el, ...place } = placeUnder(root, box);
		showPending(null, el);
		noting = { ...place, at: box };
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
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="fragment-notes" class:boxing bind:this={root} onmouseup={selected} onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={() => (drawing = null)} data-testid="fragment-notes">
	{@render children()}
</div>

{#if drawing}
	{@const b = rectOf(drawing)}
	<div class="drawn" style="left: {b.left}px; top: {b.top}px; width: {b.width}px; height: {b.height}px;" data-testid="drawn-box"></div>
{/if}
{#if offered && !noting}
	<!-- At the selection's end, out of the way of the words it is about, and gone the moment the selection is or the composer opens. -->
	<AnnotateChip
		at={offered.at}
		range={offered.range}
		onaccept={() => {
			if (!offered) return;
			const { range, ...place } = offered;
			showPending(range ?? null);
			noting = place;
			offered = null;
		}}
	/>
{/if}
{#if noting}
	<NoteAt
		target={noting.target}
		name={nameFor(noting.target)}
		in={inDoc}
		text={noting.text}
		at={noting.at}
		onwritten={() => {
			done();
			store.refresh();
		}}
		onclose={done}
	/>
{/if}

<style>
	.fragment-notes.boxing {
		cursor: crosshair;
		user-select: none;
		-webkit-user-select: none;
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
