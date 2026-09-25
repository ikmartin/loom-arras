<script lang="ts">
	// A pane's head (plan 0.13.3 W2–W5): its tab strip, and nothing else. It answers one question — which item am I looking at — and everything about the item is in the rail.
	//
	// **Tabs are a fixed width**, 148px, chosen against the corpus's real names (`main-atomic.tex`, `Arden24 · Prop 2.1`) with the controls showing, so a target does not move as its neighbours open and close; a name that still does not fit ends in an ellipsis before the controls, never under them, since a cut that reads as a whole name is a plausible name and not the name (P3); the strip clips and scrolls sideways on hover, its scrollbar's room reserved so showing it shifts nothing. **A tab's controls sit over it**, at its right behind a gradient in its own colour, on the active tab always and on the others under the pointer or keyboard focus: a tab that grew on hover would move the thing the pointer was travelling towards. **Controls appear only where they can act**: the lone tab of a lone pane has neither, since moving it would empty one pane to refill the other and closing it would leave nothing.
	import { store } from '$lib/manifest/client.svelte';
	import { itemKey } from './item';
	import Icon from '$lib/components/Icon.svelte';
	import { kinds, tabOf } from './registry';
	import { workspace } from './store.svelte';

	let { index }: { index: number } = $props();

	const pane = $derived(workspace.panes[index]);
	const lone = $derived(workspace.panes.length === 1 && (pane?.items.length ?? 0) === 1);
</script>

{#if pane}
	<div class="head" role="tablist" aria-label="open in this pane" data-testid="pane-head-{index}">
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
{/if}

<style>
	.head {
		display: flex;
		flex: 0 0 30px;
		height: 30px;
		overflow-x: hidden;
		overflow-y: hidden;
		scrollbar-gutter: stable;
		scrollbar-width: thin;
		background: var(--leaf);
		border-bottom: 1px solid var(--rule);
		font-family: var(--sans);
		font-size: 12px;
	}
	.head:hover {
		overflow-x: auto;
	}
	.tab {
		--tab: var(--leaf);
		position: relative;
		flex: 0 0 148px;
		width: 148px;
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
</style>
