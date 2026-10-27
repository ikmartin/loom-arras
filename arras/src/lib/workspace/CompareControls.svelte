<script lang="ts">
	// **Compare**, in the focused pane's toolbar while two panes are open: the one control that acts on both panes, until a draft's history menu takes its place. While comparing it counts the differences and steps through them, `[` and `]` as well as ‹ ›. What compare does to the panes (annotations hidden in both, ended when a front tab changes, the publisher asked once per pair) is the workspace's, so it holds whichever pane is focused.
	import Icon from '$lib/components/Icon.svelte';
	import { comparison, uncomparable } from './compare.svelte';
	import { workspace } from './store.svelte';

	const why = $derived(uncomparable(workspace.narrow));
	const on = $derived(workspace.comparing);
	const n = $derived(comparison.plan?.differences.length ?? 0);
	const counted = $derived(comparison.at >= 0 && n ? `${comparison.at + 1} of ${n}` : n === 1 ? '1 difference' : `${n} differences`);

	function toggle(): void {
		if (on) workspace.release();
		else if (!why) workspace.compare();
	}
</script>

<span class="compare-controls">
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
		data-testid="pane-compare"
		onclick={toggle}><Icon name="compare" size={14} />compare</button
	>
</span>

<style>
	.compare-controls {
		display: inline-flex;
		align-items: center;
		gap: 10px;
		margin-left: 6px;
		padding-left: 8px;
		border-left: 1px solid var(--rule);
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
