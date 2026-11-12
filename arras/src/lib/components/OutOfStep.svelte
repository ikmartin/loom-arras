<script lang="ts">
	// The one line near the foot of the window, clear of the toolbars, that says this page and the loom serving it are out of step, and what to do: restart `loom serve` when loom was updated under it, reload when the page is older than what it serves. × puts it away for this page.
	import { outOfStep } from '$lib/outOfStep.svelte';

	const step = $derived(outOfStep.said && outOfStep.said !== outOfStep.dismissed ? outOfStep.said : null);
</script>

{#if step}
	<div class="step" role="status" data-testid="out-of-step" data-step={step}>
		{#if step === 'restart'}
			<span class="said">loom has been updated since <code>loom serve</code> started, so some of this page may not work. Stop it and run it again, then reload this page.</span>
		{:else}
			<span class="said">loom serve is running a newer viewer than this page.</span>
			<button type="button" class="btn small" onclick={() => location.reload()} data-testid="out-of-step-reload">Reload</button>
		{/if}
		<button type="button" class="close" title="Put this away" aria-label="Put this away" onclick={() => (outOfStep.dismissed = step)} data-testid="out-of-step-close">×</button>
	</div>
{/if}

<style>
	.step {
		position: fixed;
		z-index: 61;
		left: 50%;
		bottom: calc(var(--gap) * 3);
		transform: translateX(-50%);
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--gap-tight);
		max-width: min(640px, calc(100vw - 2 * var(--gap)));
		padding: 6px 10px;
		font-family: var(--sans);
		font-size: 13px;
		background: var(--sheet);
		color: var(--ink);
		border: 1px solid var(--rule);
		border-left: 3px solid var(--state-stale);
		border-radius: var(--rad-control);
		box-shadow: var(--float-shadow);
	}
	.said {
		flex: 1 1 auto;
	}
	.close {
		font: inherit;
		font-size: 16px;
		line-height: 1;
		background: none;
		border: none;
		color: var(--ink-faint);
		cursor: pointer;
		padding: 0 2px;
	}
</style>
