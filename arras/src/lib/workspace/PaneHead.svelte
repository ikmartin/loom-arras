<script lang="ts">
	// A pane's head (plan 0.13.3 W2–W5, plan 0.16 decisions 10 and 11): the active item's views, then its row of tabs. It answers which item am I looking at, and which reading of it; the item's controls are the focused pane's, not the head's.
	//
	// **Tabs narrow, then scroll.** A tab is 148px at most, chosen against the corpus's real names (`main-atomic.tex`, `Arden24 · Prop 2.1`) with the controls showing; a crowded strip narrows every tab by the same amount, down to 1.5 times the strip's height, and past that the row of tabs scrolls — by the wheel as well as sideways, with no scrollbar drawn in a 30px strip — while the views keep their place at its left, and the active tab is brought into view whenever it changes. A name that does not fit ends in an ellipsis before the controls, never under them, since a cut that reads as a whole name is a plausible name and not the name (P3); the full name is the tab's title. **A tab's controls sit over it**, at its right behind a gradient in its own colour, on the active tab always and on the others under the pointer or keyboard focus, so a tab never grows on hover and moves what the pointer was travelling towards; below 90px a tab, the active one too, shows only its close under the pointer and both under keyboard focus, so a narrow tab keeps room for its name and a press on its middle still chooses it. **Controls appear only where they can act**: the lone tab of a lone pane has neither, since moving it would empty one pane to refill the other and closing it would leave nothing.
	import { tick } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { itemKey } from './item';
	import Icon from '$lib/components/Icon.svelte';
	import PaneViews from './PaneViews.svelte';
	import { kinds, tabOf } from './registry';
	import { workspace } from './store.svelte';

	let { index, views = true }: { index: number; views?: boolean } = $props();

	const pane = $derived(workspace.panes[index]);
	const lone = $derived(workspace.panes.length === 1 && (pane?.items.length ?? 0) === 1);

	let row = $state<HTMLElement | null>(null);
	let rowWidth = $state(0);
	/** Below 90px a tab's controls wait for the pointer or focus; every tab is the same width, so one measure of the row says it for all. */
	const narrow = $derived(!!pane?.items.length && rowWidth > 0 && rowWidth / pane.items.length < 90);

	/** Scroll the row the least that shows the active tab whole. */
	function reveal(): void {
		const on = row?.querySelector<HTMLElement>('.tab.on');
		if (!row || !on) return;
		if (on.offsetLeft < row.scrollLeft) row.scrollLeft = on.offsetLeft;
		else if (on.offsetLeft + on.offsetWidth > row.scrollLeft + row.clientWidth) row.scrollLeft = on.offsetLeft + on.offsetWidth - row.clientWidth;
	}

	$effect(() => {
		void pane?.active;
		void pane?.items.length;
		void tick().then(reveal);
	});

	// The row keeps the active tab in view as it narrows, and a vertical wheel over it scrolls it sideways; the listener is not passive, so the wheel does not also scroll what is behind.
	$effect(() => {
		const el = row;
		if (!el) return;
		const sized = new ResizeObserver(() => {
			rowWidth = el.clientWidth;
			reveal();
		});
		sized.observe(el);
		const wheel = (e: WheelEvent) => {
			if (el.scrollWidth <= el.clientWidth || Math.abs(e.deltaX) >= Math.abs(e.deltaY)) return;
			el.scrollLeft += e.deltaY;
			e.preventDefault();
		};
		el.addEventListener('wheel', wheel, { passive: false });
		return () => {
			sized.disconnect();
			el.removeEventListener('wheel', wheel);
		};
	});
</script>

{#if pane}
	<div class="head" data-testid="pane-head-{index}">
		{#if views}<PaneViews {index} />{/if}
		<div class="tabs" class:narrow role="tablist" aria-label="open in this pane" bind:this={row}>
			{#each pane.items as item (itemKey(item))}
				{@const key = itemKey(item)}
				{@const name = store.manifest ? tabOf(item, store.manifest) : item.id}
				{@const on = pane.active === key}
				{@const marker = kinds[item.kind].marker}
				{@const says = marker ? `${marker.says} ${name}` : name}
				<div class="tab" class:on role="presentation" data-testid="item-tab">
					<button type="button" class="label" role="tab" aria-selected={on} aria-label={says} title={says} onclick={() => workspace.activate(index, key)}
						>{#if marker}<span class="marker"><Icon name={marker.icon} size={12} /></span>{/if}{name}</button
					>
					{#if !lone}
						<span class="acts">
							<button
								type="button"
								class="move"
								title="Move to the other pane"
								aria-label="Move {name} to the other pane"
								data-testid="tab-move"
								onclick={() => workspace.move(index, key)}>⇄</button
							>
							<button type="button" title="Close" aria-label="Close {name}" data-testid="tab-close" onclick={() => workspace.close(index, key)}>×</button>
						</span>
					{/if}
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	.head {
		display: flex;
		flex: 0 0 var(--tab-h);
		height: var(--tab-h);
		min-width: 0;
		background: var(--leaf);
		border-bottom: 1px solid var(--rule);
		font-family: var(--sans);
		font-size: 12px;
	}
	/* the tabs are one flex item of the head, so past the floor they scroll and the views beside them do not */
	.tabs {
		position: relative;
		display: flex;
		flex: 0 1 auto;
		min-width: 0;
		overflow-x: auto;
		overflow-y: hidden;
		scrollbar-width: none;
	}
	.tabs::-webkit-scrollbar {
		display: none;
	}
	.tab {
		--tab: var(--leaf);
		position: relative;
		/* the width is what the tab contributes to the row's own size; the basis and the floor are what it narrows between */
		flex: 0 1 148px;
		width: 148px;
		min-width: calc(var(--tab-h) * 1.5);
		display: flex;
		align-items: center;
		background: var(--tab);
		border-right: 1px solid var(--rule);
	}
	.tab.on {
		--tab: var(--paper);
	}
	.label {
		flex: 1 1 auto;
		min-width: 0;
		height: 100%;
		padding: 0 10px;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 0;
		text-align: left;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		cursor: pointer;
	}
	.tab.on .label {
		color: var(--ink);
		font-weight: 500;
	}
	/* while the controls show, the label stops short of them, so its ellipsis is visible rather than covered */
	.tab:has(.acts).on .label,
	.tab:has(.acts):hover .label,
	.tab:has(.acts):focus-within .label {
		padding-right: 40px;
	}
	.marker {
		display: inline-flex;
		vertical-align: -2px;
		margin-right: 5px;
		color: var(--ink-faint);
	}
	.acts {
		position: absolute;
		right: 0;
		top: 0;
		bottom: 0;
		display: none;
		align-items: center;
		gap: 1px;
		padding: 0 4px 0 18px;
		background: linear-gradient(to right, transparent, var(--tab) 14px);
	}
	.tab.on .acts,
	.tab:hover .acts,
	.tab:focus-within .acts {
		display: flex;
	}
	.acts button {
		font: inherit;
		font-size: 11px;
		line-height: 1;
		color: var(--ink-faint);
		background: none;
		border: 0;
		padding: 2px 3px;
		cursor: pointer;
	}
	.acts button:hover {
		color: var(--ink);
	}
	/* Below 90px a tab keeps its name at rest, the active one too: the pointer shows only its close, standing short enough over the name that a press on the tab's middle still chooses it, and keyboard focus shows both its controls. */
	.narrow .label {
		padding: 0 6px;
	}
	.narrow .tab:has(.acts).on .label,
	.narrow .tab:has(.acts):focus-within .label {
		padding-right: 6px;
	}
	.narrow .tab:has(.acts):hover .label {
		padding-right: 20px;
	}
	.narrow .tab:has(.acts):has(:focus-visible) .label {
		padding-right: 36px;
	}
	.narrow .acts {
		padding-left: 2px;
		background: linear-gradient(to right, transparent, var(--tab) 2px);
	}
	.narrow .tab.on .acts,
	.narrow .tab:focus-within .acts {
		display: none;
	}
	.narrow .tab:hover .acts,
	.narrow .tab:has(:focus-visible) .acts {
		display: flex;
	}
	.narrow .tab:not(:has(:focus-visible)) .move {
		display: none;
	}
</style>
