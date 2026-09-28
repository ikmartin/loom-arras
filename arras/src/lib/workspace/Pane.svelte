<script lang="ts">
	// One pane (plan 0.13.3 W1, W10–W11): its tab strip, the active item's renderer in a body that scrolls, and while it is focused the item's toolbar (ItemToolbar, drawn by the kind's controls). Neither pane is primary; both hold every kind and behave alike.
	//
	// **A pinned toolbar has room** (DR-304-ikmartin): while the pin holds, a pane whose item draws a toolbar starts its body's content the bar's height lower, so the first line stands clear below the bar rather than under it. The unfocused pane keeps the same room, so moving focus never moves text; faded, the bar gets out of the way and no room is kept.
	//
	// **Focus is taken by any interaction** — a press on its text, a wheel over it, a tab into it — in the capture phase, so whatever acts on the focused pane reads the new value in the same frame. A pane scrolling itself (a paper sent to its page) is not an interaction, which is why the scroll event is not what is listened for. **The focused pane is marked** by its shadow while both are open, and the other is not dimmed: making a document harder to read to say it is not the current one is the wrong trade in a reading tool.
	import { onDestroy, tick } from 'svelte';
	import CompareLayer from './CompareLayer.svelte';
	import PaneHead from './PaneHead.svelte';
	import { itemKey } from './item';
	import { store } from '$lib/manifest/client.svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { hasToolbar, kinds, nameOf } from './registry';
	import { setPane } from './state.svelte';
	import { workspace, type Place } from './store.svelte';

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
	// The item's toolbar, drawn by the focused pane only, so two panes never carry the same widgets twice; a kind with no controls draws none.
	const Controls = $derived(item && workspace.focus === index ? kinds[item.kind].controls : undefined);
	const name = $derived(item && store.manifest ? nameOf(item, store.manifest) : '');
	const room = $derived(prefs.controls === 'pinned' && !!item && !!store.manifest && hasToolbar(item, store.manifest));

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
		}
		function attempt(): void {
			if (shown !== k) return stop();
			const block = place!.src ? el.querySelector<HTMLElement>(`[data-src="${CSS.escape(place!.src)}"]`) : null;
			if (block) el.scrollTop += block.getBoundingClientRect().top - el.getBoundingClientRect().top - place!.below;
			else if (el.scrollHeight - el.clientHeight >= place!.top - 1) el.scrollTop = place!.top;
		}
		for (const e of events) el.addEventListener(e, stop, { passive: true });
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
	class:room
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
	<div class="body" bind:this={body} onscroll={remember}>
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
		/* where the toolbar stands: under the head, or at the top of a pane that has none; and its height, which is every toolbar's */
		--toolbar-top: calc(var(--tab-h) + 8px);
		--toolbar-h: 32px;
	}
	.pane.headless {
		--toolbar-top: 8px;
	}
	.body {
		flex: 1 1 auto;
		min-height: 0;
		overflow: auto;
		position: relative;
	}
	/* pinned, the content starts the bar's height lower: with the 8px the bar stands below the head and the page's own top margin, its first line begins about 20px below the bar */
	.pane.room > .body {
		padding-top: var(--toolbar-h);
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
