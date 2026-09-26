<script lang="ts">
	// One pane (plan 0.13.3 W1, W10–W11): its tab strip, the active item's renderer in a body that scrolls, and while it is focused the item's toolbar (ItemToolbar, drawn by the kind's controls). Neither pane is primary; both hold every kind and behave alike.
	//
	// **A pinned toolbar has room** (DR-304-ikmartin): while the pin holds, a pane whose item draws a toolbar starts its body's content the bar's height lower, so the first line stands clear below the bar rather than under it. The unfocused pane keeps the same room, so moving focus never moves text; faded, the bar gets out of the way and no room is kept.
	//
	// **Focus is taken by any interaction** — a press on its text, a wheel over it, a tab into it — in the capture phase, so whatever acts on the focused pane reads the new value in the same frame. A pane scrolling itself (a paper sent to its page) is not an interaction, which is why the scroll event is not what is listened for. **The focused pane is marked** by its shadow while both are open, and the other is not dimmed: making a document harder to read to say it is not the current one is the wrong trade in a reading tool.
	import { tick } from 'svelte';
	import PaneHead from './PaneHead.svelte';
	import { itemKey } from './item';
	import { store } from '$lib/manifest/client.svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { hasToolbar, kinds, nameOf } from './registry';
	import { setPane } from './state.svelte';
	import { workspace } from './store.svelte';

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

	// Where each item was scrolled to, so a tab brought back to the front is where it was left.
	const scrolls = new Map<string, number>();
	let shown = '';
	$effect(() => {
		const k = key;
		if (k === shown) return;
		shown = k;
		void tick().then(() => {
			if (body && shown === k) body.scrollTop = scrolls.get(k) ?? 0;
		});
	});

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
	<div class="body" bind:this={body} onscroll={() => key && body && scrolls.set(key, body.scrollTop)}>
		{#if item}
			{#each [item] as it (key)}
				{@const Renderer = kinds[it.kind].renderer}
				<Renderer item={it} />
			{/each}
		{/if}
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
