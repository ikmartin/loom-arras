<script lang="ts">
	// A pane's toolbar: one row in the pane's own flow beneath its tabs, drawn by every pane for every kind, dimmer in the one not focused. At its left the item's views; at its right the kind's bar, compare in the focused pane while two are open, then **view ▾**, the Popover holding every other control in full words, which always ends with hiding every annotation in this pane (`a`). Each control acts on its own pane only; compare is the one that reaches across, until the history menu replaces it.
	import { tick, type Snippet } from 'svelte';
	import Popover from '$lib/components/Popover.svelte';
	import CompareControls from './CompareControls.svelte';
	import PaneViews from './PaneViews.svelte';
	import ToolbarItem from './ToolbarItem.svelte';
	import { getPane } from './state.svelte';
	import { workspace } from './store.svelte';

	let {
		name,
		bar,
		view,
		on = false
	}: {
		/** The item's name, for every control's accessible name. */
		name: string;
		/** What stands on the bar before *view*; omitted when nothing does, and then no divider is drawn. */
		bar?: Snippet;
		/** The kind's lines of the *view* menu (ToolbarItem), an `hr` between groups; the pane's own line follows them. */
		view?: Snippet;
		/** A mode inside *view* is on: the dot on *view* says so. */
		on?: boolean;
	} = $props();

	const pane = getPane();
	let viewButton = $state<HTMLButtonElement | null>(null);
	let list = $state<HTMLElement | null>(null);
	let menu = $state(false);
	const hidden = $derived(workspace.hidesNotes(pane.index));
	const comparing = $derived(workspace.panes.length === 2 && workspace.focus === pane.index);

	function items(): HTMLElement[] {
		return [...(list?.querySelectorAll<HTMLElement>('[role^="menuitem"]') ?? [])];
	}

	/** Close the menu, handing focus back to *view* when it was inside, so a keyboard reader is not left on nothing. */
	function close(): void {
		const had = !!list?.contains(document.activeElement);
		menu = false;
		if (had) viewButton?.focus();
	}

	async function toggle(): Promise<void> {
		menu = !menu;
		if (!menu) return;
		await tick();
		items()[0]?.focus();
	}

	function keys(e: KeyboardEvent): void {
		const all = items();
		const at = all.indexOf(document.activeElement as HTMLElement);
		const to = e.key === 'ArrowDown' ? at + 1 : e.key === 'ArrowUp' ? at - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? all.length - 1 : null;
		if (to === null || !all.length) return;
		e.preventDefault();
		all[(to + all.length) % all.length].focus();
	}

	// a line chosen closes the menu, after its own handler has run; a greyed one does nothing
	function chosen(e: MouseEvent): void {
		const it = (e.target as Element).closest('[role^="menuitem"]');
		if (it && it.getAttribute('aria-disabled') !== 'true') close();
	}
</script>

<div class="toolbar" role="group" aria-label="controls for {name}" data-testid="item-controls">
	<PaneViews index={pane.index} />
	<span class="end">
		{#if bar}<span class="bar">{@render bar()}</span>{/if}
		{#if comparing}<CompareControls />{/if}
		<Popover bind:open={menu} placement="below" align="end" width={230} onclose={close}>
			{#snippet trigger()}
				<button
					type="button"
					class="view"
					class:divided={!!bar || comparing}
					aria-haspopup="menu"
					aria-expanded={menu}
					aria-label="view menu for {name}"
					data-testid="toolbar-view"
					bind:this={viewButton}
					onclick={toggle}
					>view{#if on || hidden}<span class="dot" aria-hidden="true" data-testid="toolbar-view-on"></span>{/if}<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true"
						><path d="M4.5 6.5 L8 10 L11.5 6.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" /></svg
					></button
				>
			{/snippet}
			<!-- svelte-ignore a11y_click_events_have_key_events (a menu item is a button or a link, whose Enter and Space arrive as clicks) -->
			<div class="menu" role="menu" tabindex="-1" aria-label="view of {name}" data-testid="toolbar-menu" bind:this={list} onkeydown={keys} onclick={chosen}>
				{#if view}{@render view()}<hr />{/if}
				<ToolbarItem
					label="annotations off in this pane"
					name="annotations off in the pane showing {name}"
					key="a"
					checked={hidden}
					testid="toggle-hide-notes"
					onclick={() => workspace.hideNotes(pane.index, !hidden)}
				/>
			</div>
		</Popover>
	</span>
</div>

<style>
	/* a row in the pane's flow under its tabs, never over the page: the views at its left, the controls at its right */
	.toolbar {
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
	.view {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		margin-left: 2px;
		padding: 2px 8px 2px 9px;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 0;
		cursor: pointer;
	}
	/* the divider before view, only when something stands to its left */
	.view.divided {
		border-left: 1px solid var(--rule);
	}
	.view:hover,
	.view[aria-expanded='true'] {
		color: var(--ink);
	}
	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--link);
	}
	.view:focus-visible {
		outline: 2px solid var(--link);
		outline-offset: 2px;
		border-radius: 4px;
	}
	.menu {
		padding: 6px 0;
		font-family: var(--sans);
		font-size: 12.5px;
		outline: none;
	}
	.menu :global(hr) {
		border: 0;
		border-top: 1px solid var(--rule);
		margin: 5px 0;
	}
</style>
