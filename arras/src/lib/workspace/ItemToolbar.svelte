<script lang="ts">
	// A pane's toolbar, in the pane's own flow beneath its tabs, drawn by every pane for every kind, dimmer in the one not focused. Its first row reads: at its left the item's views; at its right **Annotate**, which shows or puts away the annotation row where the kind has tools that write, then the kind's bar, a document's **history ▾**, compare's counter and stop while the two panes are compared, then **view ▾**, the menu holding every other control in full words, which always ends with turning every annotation in this pane off or on, a control with no key, since a stray letter must never hide what a reader is looking at. The annotation row beneath holds the tools that write, and at its right what the tool in hand does; while it is put away that line stands under the toolbar instead, over the page's head. Each control acts on its own pane only; compare, started from a draft's history, is the one that reaches across.
	import { untrack, type Snippet } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { annotationRow } from './annotationRow.svelte';
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
		tools,
		history,
		view,
		hint = '',
		on = false
	}: {
		/** The item's name, for every control's accessible name. */
		name: string;
		/** What stands on the bar before *view*; omitted when nothing does, and then no divider is drawn. */
		bar?: Snippet;
		/** The tools that write, for the annotation row; omitted where the kind has none, and then there is no row and no Annotate. */
		tools?: Snippet;
		/** A document's history menu (HistoryMenu), after the bar. */
		history?: Snippet;
		/** The kind's lines of the *view* menu (ToolbarItem), an `hr` between groups; the pane's own line follows them. */
		view?: Snippet;
		/** A mode inside *view* is on: the dot on *view* says so. */
		on?: boolean;
		/** What the tool in hand does, at the annotation row's right, or a line under the bar while the row is put away; '' for none. */
		hint?: string;
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

<div class="toolbars" role="group" aria-label="controls for {name}" data-testid="item-controls">
<div class="toolbar">
	<PaneViews index={pane.index} />
	<span class="end">
		{#if tools}
			<button type="button" class="row-toggle" class:on={annotationRow.open} aria-expanded={annotationRow.open} title={annotationRow.open ? 'Put the annotation tools away' : 'Show the annotation tools'} aria-label="annotation tools for {name}" data-testid="toggle-annotation-row" onclick={() => annotationRow.set(!annotationRow.open)}
				><Icon name="highlighter" size={14} /><span>Annotate</span><span class="caret" class:up={annotationRow.open}><Icon name="caret" size={11} /></span></button
			>
		{/if}
		{#if bar}<span class="bar">{@render bar()}</span>{/if}
		{#if history}{@render history()}{/if}
		{#if comparing}<CompareControls />{/if}
		<ToolbarMenu label="view" name="view menu for {name}" menuName="view of {name}" testid="toolbar-view" menuTestid="toolbar-menu" divided={!!bar || !!history || comparing} dot={on || hidden}>
			{#if view}{@render view()}<hr />{/if}
			<ToolbarItem
				label={hidden ? 'turn annotations on' : 'turn annotations off'}
				name="{hidden ? 'turn annotations on' : 'turn annotations off'} in the pane showing {name}"
				testid="toggle-hide-notes"
				onclick={() => workspace.hideNotes(pane.index, !hidden)}
			/>
		</ToolbarMenu>
	</span>
</div>
	{#if tools && annotationRow.open}
		<div class="tools-row" role="group" aria-label="annotation tools for {name}" data-testid="annotation-row">
			<span class="tools">{@render tools()}</span>
			{#if hint}<span class="row-hint" role="status" data-testid="annotate-hint">{hint}</span>{/if}
		</div>
	{:else if hint && !strip}<div class="hint" role="status" data-testid="annotate-hint">{hint}</div>{/if}
	{#if strip}
		<div class="strip" class:refused={strip.refused} role={strip.refused ? 'alert' : 'status'} data-testid={strip.testid}>
			<span class="said">{strip.text}</span>
			{#each strip.acts ?? [] as a (a.testid)}<button type="button" class="btn small" class:primary={a.primary} disabled={strip.busy} data-testid={a.testid} onclick={a.run}>{a.label}</button>{/each}
			{#if !strip.acts?.length}<button type="button" class="close" aria-label="close" data-testid="strip-close" onclick={() => setStrip(pane.index, undefined)}>×</button>{/if}
		</div>
	{/if}
</div>

<style>
	/* the toolbar's rows in the pane's flow under its tabs, never over the page */
	.toolbars {
		position: relative;
		flex: none;
	}
	/* the row that reads: the views at its left, the controls at its right */
	.toolbar {
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
	.row-toggle {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		height: 24px;
		margin-right: 6px;
		padding: 0 7px;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 1px solid transparent;
		border-radius: 6px;
		cursor: pointer;
	}
	.row-toggle:hover {
		color: var(--ink);
		background: var(--leaf);
	}
	.row-toggle.on {
		color: var(--ink);
		background: var(--accent-wash);
		border-color: color-mix(in srgb, var(--accent) 35%, transparent);
	}
	.caret {
		display: inline-flex;
		transition: transform 0.15s ease;
	}
	.caret.up {
		transform: rotate(180deg);
	}
	/* the row that writes: the tools at its left, what the tool in hand does at its right */
	.tools-row {
		display: flex;
		align-items: center;
		gap: 12px;
		box-sizing: border-box;
		height: var(--toolbar-h);
		padding: 0 12px 0 8px;
		font-family: var(--sans);
		font-size: 12.5px;
		color: var(--ink-soft);
		white-space: nowrap;
		background: var(--leaf);
		border-bottom: 1px solid var(--rule);
	}
	.tools {
		display: flex;
		align-items: center;
		gap: 2px;
		flex: none;
	}
	.row-hint {
		flex: 1 1 auto;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		text-align: right;
		font-size: 12px;
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
	/* the hint: one quiet line under the bar, across it, over the page's head */
	.hint {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		z-index: 5;
		box-sizing: border-box;
		padding: 4px 12px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 12px;
		color: var(--ink-soft);
		background: var(--leaf);
		border-bottom: 1px solid var(--rule);
		pointer-events: none;
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
