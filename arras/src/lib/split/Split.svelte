<script lang="ts">
	// The split: content on one side, discussion on the other, one divider between them (plan 0.13 §7).
	//
	// **One global ratio.** A reader sets the shape of their screen once, not once per route, so the ratio lives in the
	// preferences and every split in the app is the same width. The divider snaps at the middle and nowhere else — a
	// snap at a third is a guess about a screen this code cannot see — and a double-click puts it back there.
	//
	// **Below the breakpoint the split becomes a switch.** Two panes on a phone are two unusable panes; one at a time,
	// with a control to change which, is the same information in the room that has it.
	import type { Snippet } from 'svelte';
	import { prefs } from '$lib/prefs.svelte';

	let {
		content,
		discussion,
		contentLabel = 'content',
		discussionLabel = 'discussion',
		narrowAt = 700
	}: {
		content: Snippet;
		discussion: Snippet;
		contentLabel?: string;
		discussionLabel?: string;
		/** Below this width the split is a switch; two panes on a phone are two unusable panes. */
		narrowAt?: number;
	} = $props();

	const SNAP = 0.5;
	const NEAR = 0.03;
	const STEP = 0.02;

	let frame = $state<HTMLDivElement | null>(null);
	let width = $state(0);
	let dragging = $state(false);
	/** Which pane is collapsed, by the chevrons on the divider; independent of the ratio, which is remembered. */
	let folded = $state<'' | 'content' | 'discussion'>('');
	/** On a narrow screen, which pane is showing. */
	let showing = $state<'content' | 'discussion'>('content');

	const narrow = $derived(width > 0 && width < narrowAt);
	const ratio = $derived(folded === 'content' ? 0 : folded === 'discussion' ? 1 : prefs.divider);

	function set(next: number): void {
		const snapped = Math.abs(next - SNAP) < NEAR ? SNAP : next;
		prefs.divider = Math.min(0.8, Math.max(0.2, snapped));
		folded = '';
	}

	function drag(e: PointerEvent): void {
		if (!frame) return;
		const at = frame.getBoundingClientRect();
		const x = prefs.swap ? at.right - e.clientX : e.clientX - at.left;
		set(x / (at.width || 1));
	}

	function grab(e: PointerEvent): void {
		dragging = true;
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
		drag(e);
	}

	function move(e: PointerEvent): void {
		if (dragging) drag(e);
	}

	function drop(e: PointerEvent): void {
		if (!dragging) return;
		dragging = false;
		(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
	}

	function key(e: KeyboardEvent): void {
		const back = prefs.swap ? 'ArrowRight' : 'ArrowLeft';
		const forth = prefs.swap ? 'ArrowLeft' : 'ArrowRight';
		if (e.key === back) set(prefs.divider - STEP);
		else if (e.key === forth) set(prefs.divider + STEP);
		else if (e.key === 'Home') set(SNAP);
		else return;
		e.preventDefault();
	}
</script>

<svelte:window onresize={() => (width = frame?.clientWidth ?? width)} />

<div
	class="split"
	class:narrow
	class:swap={prefs.swap}
	class:dragging
	bind:this={frame}
	bind:clientWidth={width}
	data-testid="split"
	style="--ratio: {ratio}"
>
	{#if narrow}
		<div class="switch" role="tablist" aria-label="pane">
			<button
				type="button"
				role="tab"
				aria-selected={showing === 'content'}
				data-testid="switch-content"
				onclick={() => (showing = 'content')}>{contentLabel}</button
			>
			<button
				type="button"
				role="tab"
				aria-selected={showing === 'discussion'}
				data-testid="switch-discussion"
				onclick={() => (showing = 'discussion')}>{discussionLabel}</button
			>
		</div>
		<div class="pane one" data-testid="pane-{showing}">
			{#if showing === 'content'}{@render content()}{:else}{@render discussion()}{/if}
		</div>
	{:else}
		<div class="pane content" data-testid="pane-content" aria-hidden={folded === 'content'}>{@render content()}</div>
		<!-- A separator that takes focus is a widget in ARIA's own terms — a window splitter, with the arrow keys and
		     aria-valuenow this one has — so the two rules below are being told about a case they do not model. -->
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="divider"
			role="separator"
			tabindex="0"
			aria-label="Resize the panes"
			aria-orientation="vertical"
			aria-valuenow={Math.round(ratio * 100)}
			aria-valuemin={20}
			aria-valuemax={80}
			data-testid="divider"
			onpointerdown={grab}
			onpointermove={move}
			onpointerup={drop}
			onpointercancel={drop}
			ondblclick={() => set(SNAP)}
			onkeydown={key}
		>
			<button
				type="button"
				class="fold back"
				title="Collapse the {contentLabel}"
				aria-label="Collapse the {contentLabel}"
				data-testid="fold-content"
				onclick={() => (folded = folded === 'content' ? '' : 'content')}
				onpointerdown={(e) => e.stopPropagation()}
				ondblclick={(e) => e.stopPropagation()}>‹</button
			>
			<span class="grip" aria-hidden="true"></span>
			<button
				type="button"
				class="fold forth"
				title="Collapse the {discussionLabel}"
				aria-label="Collapse the {discussionLabel}"
				data-testid="fold-discussion"
				onclick={() => (folded = folded === 'discussion' ? '' : 'discussion')}
				onpointerdown={(e) => e.stopPropagation()}
				ondblclick={(e) => e.stopPropagation()}>›</button
			>
		</div>
		<div class="pane discussion" data-testid="pane-discussion" aria-hidden={folded === 'discussion'}>
			{@render discussion()}
		</div>
	{/if}
</div>

<style>
	.split {
		display: flex;
		align-items: stretch;
		min-height: 0;
		height: 100%;
		width: 100%;
	}
	.split.swap {
		flex-direction: row-reverse;
	}
	.split.narrow {
		flex-direction: column;
	}
	.pane {
		min-width: 0;
		min-height: 0;
		overflow: auto;
	}
	.pane.content {
		flex: 0 0 calc(var(--ratio) * 100%);
	}
	.pane.discussion {
		flex: 1 1 0;
	}
	.pane.one {
		flex: 1 1 auto;
	}
	.pane[aria-hidden='true'] {
		display: none;
	}
	.divider {
		flex: 0 0 auto;
		width: 9px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 4px;
		cursor: col-resize;
		background: var(--rule-faint, #efece5);
		border-left: 1px solid var(--rule, #ddd9cf);
		border-right: 1px solid var(--rule, #ddd9cf);
		touch-action: none;
	}
	.divider:focus-visible {
		outline: 2px solid var(--link, #35618f);
		outline-offset: -2px;
	}
	.split.dragging .divider,
	.divider:hover {
		background: var(--rule, #ddd9cf);
	}
	.grip {
		flex: 0 1 60px;
		width: 1px;
		background: var(--ink-faint, #8a857c);
		opacity: 0.5;
	}
	.fold {
		font: inherit;
		font-size: 10px;
		line-height: 1;
		color: var(--ink-faint, #6b6b6b);
		background: none;
		border: 0;
		padding: 2px 0;
		width: 100%;
		cursor: pointer;
	}
	.fold:hover {
		color: var(--ink, #1b1b1b);
	}
	.split.swap .fold.back,
	.split.swap .fold.forth {
		transform: scaleX(-1);
	}
	.switch {
		display: flex;
		gap: 4px;
		padding: 4px 6px;
		border-bottom: 1px solid var(--rule, #ddd9cf);
	}
	.switch button {
		font: inherit;
		font-size: 0.8rem;
		color: inherit;
		background: none;
		border: 1px solid var(--rule, #ddd9cf);
		border-radius: 3px;
		padding: 1px 8px;
		cursor: pointer;
	}
	.switch button[aria-selected='true'] {
		background: var(--annotation-tint, rgb(217 119 87 / 0.18));
	}
</style>
