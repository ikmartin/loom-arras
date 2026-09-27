<script lang="ts">
	// The frame's one rail (plan 0.16, decision 6). It holds only what concerns both panes: the annotation filter at its left, which governs what every document draws, and **compare** at its right, which acts on the two items on screen (book 15.2.6). Nothing about one item stands here: an item's views are at the end of its pane's tab strip, and its controls on the focused pane.
	//
	// **Compare turns annotations off** while it is pressed and puts back what was chosen when it is released: the comparison's washes and colours then mean one thing each (A4). It is released by a press, or by either pane's front tab changing. While comparing, the rail counts the differences and steps through them, `[` and `]` as well as ‹ ›: a step concerns both panes, so its keys are the rail's and not a fragment's.
	import { untrack } from 'svelte';
	import SessionFilter from '$lib/sessions/SessionFilter.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { sessionView } from '$lib/sessions/sessions.svelte';
	import { comparison, uncomparable } from './compare.svelte';
	import { workspace } from './store.svelte';

	const why = $derived(uncomparable(workspace.narrow));
	const on = $derived(workspace.comparing);
	const n = $derived(comparison.plan?.differences.length ?? 0);

	// the filter follows compare: off while it is pressed, and back to what it was once it is not
	$effect(() => {
		const pressed = on;
		const set = sessionView.displaced;
		untrack(() => {
			if (pressed && set === null) sessionView.suspend();
			else if (!pressed && set !== null) sessionView.resume();
		});
	});
	// a comparison that can no longer be drawn ends: the window narrowed, or a tab became something that does not pair
	$effect(() => {
		if (on && why) workspace.release();
	});
	// what one comparison found is forgotten when it ends, and the publisher is asked once per pair of items
	$effect(() => {
		const left = workspace.active(0);
		const right = workspace.active(1);
		if (!on || !left || !right) {
			comparison.reset();
			return;
		}
		void comparison.ask(left, right);
	});

	function toggle(): void {
		if (on) workspace.release();
		else if (!why) workspace.compare();
	}

	function keys(e: KeyboardEvent): void {
		if (!on || e.metaKey || e.ctrlKey || e.altKey) return;
		if ((e.target as HTMLElement | null)?.closest('input, textarea, select, [contenteditable]')) return;
		if (e.key === ']') comparison.step(1);
		else if (e.key === '[') comparison.step(-1);
		else return;
		e.preventDefault();
	}

	const counted = $derived(comparison.at >= 0 && n ? `${comparison.at + 1} of ${n}` : n === 1 ? '1 difference' : `${n} differences`);
</script>

<svelte:window onkeydown={keys} />

<div class="global-rail" data-testid="reading-rail">
	<SessionFilter />
	<span class="right">
		{#if on}
			<span class="steps" data-testid="compare-steps">
				<button type="button" class="step" disabled={!n} aria-label="Previous difference" title="Previous difference ([)" data-testid="compare-prev" onclick={() => comparison.step(-1)}>‹</button>
				<span class="count" aria-live="polite" data-testid="compare-count">{n ? counted : 'no differences'}</span>
				<button type="button" class="step" disabled={!n} aria-label="Next difference" title="Next difference (])" data-testid="compare-next" onclick={() => comparison.step(1)}>›</button>
			</span>
		{/if}
		<button
			type="button"
			class="compare"
			class:on
			disabled={!on && !!why}
			aria-pressed={on}
			title={on ? 'Stop comparing' : why || 'Compare the two panes: what differs between them, marked in both'}
			data-testid="rail-compare"
			onclick={toggle}><Icon name="compare" size={14} />compare</button
		>
	</span>
</div>

<style>
	/* One line, 12.5px: the filter a quiet label and a pill at the left, the counter and compare at the right. */
	.global-rail {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		height: var(--reading-rail);
		padding: 0 12px;
		border-bottom: 1px solid var(--rule);
		font-family: var(--sans);
		font-size: 12.5px;
		color: var(--ink-soft);
		white-space: nowrap;
		overflow: hidden;
	}
	.right {
		display: inline-flex;
		align-items: center;
		gap: 14px;
	}
	.steps {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-variant-numeric: tabular-nums;
	}
	.step {
		font: inherit;
		font-size: 15px;
		line-height: 1;
		color: var(--ink-soft);
		background: none;
		border: 0;
		padding: 0 4px;
		cursor: pointer;
	}
	.step:disabled {
		color: var(--ink-faint);
		cursor: default;
	}
	.compare {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 0;
		border-radius: var(--rad-control);
		padding: 2px 8px;
		cursor: pointer;
	}
	.compare:hover:not(:disabled) {
		color: var(--ink);
	}
	.compare.on {
		color: var(--link);
		background: var(--link-wash);
	}
	.compare:disabled {
		color: var(--ink-faint);
		cursor: default;
	}
</style>
