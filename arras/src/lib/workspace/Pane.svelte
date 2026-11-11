<script lang="ts">
	// One pane (plan 0.13.3 W1, W10–W11): its tab strip, its toolbar beneath (ItemToolbar, drawn by the kind's controls), and the active item's renderer in a body that scrolls. Neither pane is primary; both hold every kind and behave alike, and each draws its own toolbar, the unfocused one's dimmer, as its tabs are. `a` anywhere in the pane hides or shows every annotation in it.
	//
	// **Focus is taken by any interaction** — a press on its text, a wheel over it, a tab into it — in the capture phase, so whatever acts on the focused pane reads the new value in the same frame. A pane scrolling itself (a paper sent to its page) is not an interaction, which is why the scroll event is not what is listened for. **The focused pane is marked** by its shadow while both are open, and the other is not dimmed: making a document harder to read to say it is not the current one is the wrong trade in a reading tool.
	import { onDestroy, tick, untrack } from 'svelte';
	import CompareLayer from './CompareLayer.svelte';
	import PaneHead from './PaneHead.svelte';
	import { itemKey } from './item';
	import { store } from '$lib/manifest/client.svelte';
	import { kinds, nameOf } from './registry';
	import { setPane } from './state.svelte';
	import { workspace, type Place } from './store.svelte';
	import { here } from '$lib/here.svelte';
	import { keyOf } from '$lib/fragments/quote';

	let { index, style = '', head = true }: { index: number; style?: string; head?: boolean } = $props();

	let frame = $state<HTMLElement | null>(null);
	let body = $state<HTMLElement | null>(null);
	setPane({
		get index() {
			return index;
		},
		scroller: () => body,
		frame: () => frame
	});

	const item = $derived(workspace.active(index));
	const key = $derived(item ? itemKey(item) : '');
	const focused = $derived(workspace.panes.length === 2 && workspace.focus === index);
	const dim = $derived(workspace.panes.length === 2 && workspace.focus !== index);
	const Controls = $derived(item ? kinds[item.kind].controls : undefined);
	const name = $derived(item && store.manifest ? nameOf(item, store.manifest) : '');

	// `a` hides or shows every annotation in this pane, from anywhere in it but a field being typed in; listened for on the pane, so it reaches every kind's renderer alike
	$effect(() => {
		const el = frame;
		if (!el) return;
		const hide = (e: KeyboardEvent) => {
			if (e.key !== 'a' || e.metaKey || e.ctrlKey || e.altKey || e.defaultPrevented) return;
			if ((e.target as HTMLElement | null)?.closest('input, textarea, select, [contenteditable]')) return;
			workspace.hideNotes(index, !workspace.hidesNotes(index));
			e.preventDefault();
		};
		el.addEventListener('keydown', hide);
		return () => el.removeEventListener('keydown', hide);
	});

	/** The body's width when the divider was taken, kept while it moves, the pane clipping it or leaving room beside it, so the item is laid out once at the drop. Laid out at every width, a long paper's frame cost 50–60 ms of layout and pre-paint, and the divider trailed the pointer at about 20 frames a second. */
	let held = $state<number | null>(null);
	$effect(() => {
		const resizing = workspace.resizing;
		untrack(() => (held = resizing && body ? body.getBoundingClientRect().width : null));
	});

	// Where each item was scrolled to, so a tab brought back to the front, or the whole workspace brought back from another page, is where it was left. What is kept is the block at the top of the pane, since the content arrives after the pane does -- fetched, then typeset, formulas changing height as they are set -- and a pixel offset would land on other words. The place is taken again each time the page grows, until it settles or the reader scrolls themselves.
	let shown = '';
	let restoring = false;
	$effect(() => {
		const k = key;
		if (k === shown) return;
		shown = k;
		void tick().then(() => {
			if (body && shown === k) restore(body, k, workspace.scrolls.get(k));
		});
	});

	let pending = 0;
	function remember(): void {
		const el = body;
		const k = key;
		if (!el || !k || restoring) return;
		cancelAnimationFrame(pending);
		pending = requestAnimationFrame(() => {
			// a pane being taken down loses its content first, and the scroll that follows is not the reader's
			if (!el.isConnected || !workspace.onScreen || !el.querySelector('[data-src]')) return;
			const r = el.getBoundingClientRect();
			// a point in the text column just below the pane's top, clear of the toolbar at its right
			const hit = document.elementFromPoint(r.left + r.width * 0.3, r.top + 48)?.closest<HTMLElement>('[data-src]');
			const block = hit && el.contains(hit) ? hit : null;
			workspace.scrolls.set(k, { top: el.scrollTop, src: block?.dataset.src ?? null, below: block ? block.getBoundingClientRect().top - r.top : 0 });
			// and where the reader is, for `loom here`: the block by the key it belongs to
			const belongs = block ? keyOf(block, '') : '';
			here.setBlock(k, block?.dataset.src && belongs ? { src: block.dataset.src, key: belongs } : null);
		});
	}

	function restore(el: HTMLElement, k: string, place: Place | undefined): void {
		if (!place || (!place.top && !place.src)) {
			el.scrollTop = 0;
			return;
		}
		restoring = true;
		const watch = new ResizeObserver(attempt);
		const quit = setTimeout(stop, 6000);
		const events = ['wheel', 'pointerdown', 'keydown', 'touchstart'] as const;
		function stop(): void {
			restoring = false;
			watch.disconnect();
			clearTimeout(quit);
			for (const e of events) el.removeEventListener(e, stop);
			el.removeEventListener('arrive', stop);
		}
		function attempt(): void {
			if (shown !== k) return stop();
			const block = place!.src ? el.querySelector<HTMLElement>(`[data-src="${CSS.escape(place!.src)}"]`) : null;
			if (block) el.scrollTop += block.getBoundingClientRect().top - el.getBoundingClientRect().top - place!.below;
			else if (el.scrollHeight - el.clientHeight >= place!.top - 1) el.scrollTop = place!.top;
		}
		for (const e of events) el.addEventListener(e, stop, { passive: true });
		// a document sent somewhere goes there, and the place it was left at gives way
		el.addEventListener('arrive', stop);
		for (const child of el.children) watch.observe(child);
		attempt();
	}

	onDestroy(() => cancelAnimationFrame(pending));

	const take = () => workspace.focusOn(index);
</script>

<section
	class="pane"
	class:focused
	class:headless={!head}
	class:dim
	class:holding={held !== null}
	data-pane={index}
	data-testid="pane-{index}"
	aria-label="pane {index + 1}"
	bind:this={frame}
	{style}
	onpointerdowncapture={take}
	onwheelcapture={take}
	onfocusincapture={take}
>
	{#if head}<PaneHead {index} />{/if}
	{#if item && Controls}
		{#key key}<Controls {item} {name} />{/key}
	{/if}
	<div class="body" bind:this={body} style:width={held === null ? null : `${held}px`} onscroll={remember}>
		{#if item}
			{#each [item] as it (key)}
				{@const Renderer = kinds[it.kind].renderer}
				<Renderer item={it} />
			{/each}
		{/if}
		{#if workspace.comparing && head}<CompareLayer {index} body={() => body} />{/if}
	</div>
</section>

<style>
	/* above the divider, so a box opened over the text is drawn over it; the focused pane above the other, for its lift */
	.pane {
		position: relative;
		z-index: 1;
		display: flex;
		flex-direction: column;
		min-width: 0;
		min-height: 0;
		container: pane / inline-size;
		/* every toolbar's height */
		--toolbar-h: 32px;
	}
	/* the unfocused pane's toolbar is quieter, as its tabs are */
	.pane.dim :global(.toolbar) {
		opacity: 0.72;
	}
	.pane.holding {
		overflow: clip;
	}
	.body {
		flex: 1 1 auto;
		min-height: 0;
		overflow: auto;
		position: relative;
	}
	/* The focused pane, while two are open (W11): a lift and a white head, and nothing drawn on it. A line on the head reads as a property of the tabs, and a coloured one asks what it means. */
	.pane.focused {
		box-shadow:
			0 0 0 1px var(--rule),
			0 6px 26px rgb(0 0 0 / 11%);
		z-index: 2;
	}
	.pane.focused :global(.head) {
		background: var(--sheet);
	}
</style>
