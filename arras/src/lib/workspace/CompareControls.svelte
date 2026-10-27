<script lang="ts">
	// **Compare**, while the two panes are compared, in the focused pane's toolbar: it counts the differences and steps through them, `[` and `]` as well as ‹ ›, and stops. Compare is started from a draft's history menu (HistoryMenu); what it does to the panes (annotations hidden in both, ended when a front tab changes, the publisher asked once per pair) is the workspace's, so it holds whichever pane is focused.
	import Icon from '$lib/components/Icon.svelte';
	import { comparison } from './compare.svelte';
	import { workspace } from './store.svelte';

	const n = $derived(comparison.plan?.differences.length ?? 0);
	const counted = $derived(comparison.at >= 0 && n ? `${comparison.at + 1} of ${n}` : n === 1 ? '1 difference' : `${n} differences`);
</script>

<span class="compare-controls">
	<span class="steps" data-testid="compare-steps">
		<button type="button" class="step" disabled={!n} aria-label="Previous difference" title="Previous difference ([)" data-testid="compare-prev" onclick={() => comparison.step(-1)}>‹</button>
		<span class="count" aria-live="polite" data-testid="compare-count">{n ? counted : 'no differences'}</span>
		<button type="button" class="step" disabled={!n} aria-label="Next difference" title="Next difference (])" data-testid="compare-next" onclick={() => comparison.step(1)}>›</button>
	</span>
	<button type="button" class="compare" title="Stop comparing, and put back each pane's annotations" data-testid="compare-stop" onclick={() => workspace.release()}
		><Icon name="compare" size={14} />stop</button
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
		color: var(--link);
		background: var(--link-wash);
		border: 0;
		border-radius: var(--rad-control);
		padding: 2px 8px;
		cursor: pointer;
	}
	.compare:hover {
		color: var(--ink);
	}
</style>
