<script lang="ts">
	// One pane (plan 0.13.3 W1, W10–W11): its tab strip, and the active item's renderer in a body that scrolls. Neither pane is primary; both hold every kind and behave alike.
	//
	// **Focus is taken by any interaction** — a press on its text, a wheel over it, a tab into it — in the capture phase, so whatever acts on the focused pane reads the new value in the same frame. A pane scrolling itself (a paper sent to its page) is not an interaction, which is why the scroll event is not what is listened for. **The focused pane is marked** by its shadow while both are open, and the other is not dimmed: making a document harder to read to say it is not the current one is the wrong trade in a reading tool.
	import { tick } from 'svelte';
	import PaneHead from './PaneHead.svelte';
	import { itemKey } from './item';
	import { kinds } from './registry';
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
