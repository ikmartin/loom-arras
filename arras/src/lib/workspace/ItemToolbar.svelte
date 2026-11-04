<script lang="ts">
	// A pane's toolbar: one row in the pane's own flow beneath its tabs, drawn by every pane for every kind, dimmer in the one not focused. At its left the item's views; at its right the kind's bar, a document's **history ▾**, compare's counter and stop while the two panes are compared, then **view ▾**, the menu holding every other control in full words, which always ends with hiding every annotation in this pane (`a`). Each control acts on its own pane only; compare, started from a draft's history, is the one that reaches across.
	import { untrack, type Snippet } from 'svelte';
	import CompareControls from './CompareControls.svelte';
	import PaneViews from './PaneViews.svelte';
	import ToolbarItem from './ToolbarItem.svelte';
	import ToolbarMenu from './ToolbarMenu.svelte';
	import { getPane } from './state.svelte';
	import { setStrip, strips } from './strip.svelte';
	import { workspace } from './store.svelte';

	let {
		name,
		bar,
		history,
		view,
		on = false
	}: {
		/** The item's name, for every control's accessible name. */
		name: string;
		/** What stands on the bar before *view*; omitted when nothing does, and then no divider is drawn. */
		bar?: Snippet;
		/** A document's history menu (HistoryMenu), after the bar. */
		history?: Snippet;
		/** The kind's lines of the *view* menu (ToolbarItem), an `hr` between groups; the pane's own line follows them. */
		view?: Snippet;
		/** A mode inside *view* is on: the dot on *view* says so. */
		on?: boolean;
	} = $props();

	const pane = getPane();
	const hidden = $derived(workspace.hidesNotes(pane.index));
	// the counter and stop while comparing, in the focused pane
	const comparing = $derived(workspace.comparing && workspace.focus === pane.index);
	// the line under the bar stays with the item it was first drawn for, and goes when the pane turns to another
	const strip = $derived(strips[pane.index]);
	let drawnFor = '';
	$effect(() => {
		const [s, n] = [strip, name];
		untrack(() => {
			if (!s) drawnFor = '';
			else if (!drawnFor) drawnFor = n;
			else if (drawnFor !== n) {
				drawnFor = '';
				setStrip(pane.index, undefined);
			}
		});
	});
</script>

<div class="toolbar" role="group" aria-label="controls for {name}" data-testid="item-controls">
	<PaneViews index={pane.index} />
	<span class="end">
		{#if bar}<span class="bar">{@render bar()}</span>{/if}
		{#if history}{@render history()}{/if}
		{#if comparing}<CompareControls />{/if}
		<ToolbarMenu label="view" name="view menu for {name}" menuName="view of {name}" testid="toolbar-view" menuTestid="toolbar-menu" divided={!!bar || !!history || comparing} dot={on || hidden}>
			{#if view}{@render view()}<hr />{/if}
			<ToolbarItem
				label="annotations off in this pane"
				name="annotations off in the pane showing {name}"
				key="a"
				checked={hidden}
				testid="toggle-hide-notes"
				onclick={() => workspace.hideNotes(pane.index, !hidden)}
			/>
		</ToolbarMenu>
	</span>
	{#if strip}
		<div class="strip" class:refused={strip.refused} role={strip.refused ? 'alert' : 'status'} data-testid={strip.testid}>
			<span class="said">{strip.text}</span>
			{#each strip.acts ?? [] as a (a.testid)}<button type="button" class="btn small" class:primary={a.primary} disabled={strip.busy} data-testid={a.testid} onclick={a.run}>{a.label}</button>{/each}
			{#if !strip.acts?.length}<button type="button" class="close" aria-label="close" data-testid="strip-close" onclick={() => setStrip(pane.index, undefined)}>×</button>{/if}
		</div>
	{/if}
</div>

<style>
	/* a row in the pane's flow under its tabs, never over the page: the views at its left, the controls at its right */
	.toolbar {
		position: relative;
		flex: none;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		box-sizing: border-box;
		height: var(--toolbar-h);
		padding: 0 8px 0 0;
		font-family: var(--sans);
		font-size: 12.5px;
		color: var(--ink-soft);
		white-space: nowrap;
		background: var(--sheet);
		border-bottom: 1px solid var(--rule);
		transition: opacity 0.15s ease;
	}
	/* in a narrow pane the bar gives way first, clipped at its left, so view ▾ is always whole */
	.end {
		margin-left: auto;
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 2px;
		min-width: 0;
		overflow: hidden;
	}
	.bar {
		display: flex;
		align-items: center;
		gap: 2px;
		min-width: 0;
		overflow: hidden;
		flex: 0 1 auto;
		direction: rtl;
	}
	.bar > :global(*) {
		direction: ltr;
	}
	.end > :global(:not(.bar)) {
		flex: none;
	}
	/* under the bar, over the page's head, at the bar's right where the control that asked stands */
	.strip {
		position: absolute;
		top: calc(100% + 4px);
		right: 8px;
		z-index: 5;
		display: flex;
		align-items: center;
		gap: 8px;
		max-width: calc(100% - 16px);
		padding: 6px 8px 6px 12px;
		white-space: normal;
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule-strong);
		border-radius: 8px;
		box-shadow: 0 2px 8px rgb(0 0 0 / 0.08);
	}
	.strip.refused .said {
		color: var(--state-stale);
	}
	.close {
		font: inherit;
		font-size: 15px;
		line-height: 1;
		color: var(--ink-soft);
		background: none;
		border: 0;
		cursor: pointer;
	}
</style>
