<script lang="ts">
	// One setting's values as one control, `serif | sans`, the chosen one pressed.
	let { options, current, pick, test, label }: { options: { v: string; label: string; title?: string }[]; current: string; pick: (v: string) => void; test: string; label: string } = $props();
</script>

<div class="seg" role="group" aria-label={label}>
	{#each options as o (o.v)}
		<button class:on={current === o.v} aria-pressed={current === o.v} title={o.title} onclick={() => pick(o.v)} data-testid="{test}-{o.v}">{o.label}</button>
	{/each}
</div>

<style>
	/* the chosen value is a raised chip inside the control, rounded on its own, so its outline follows its corners */
	.seg {
		display: inline-flex;
		gap: 2px;
		padding: 2px;
		border: 1px solid var(--rule);
		border-radius: 9px;
		background: var(--leaf);
	}
	button {
		font: inherit;
		font-family: var(--sans);
		font-size: 12.5px;
		white-space: nowrap;
		padding: 4px 11px;
		border: 0;
		border-radius: 6px;
		background: none;
		color: var(--ink-soft);
		cursor: pointer;
	}
	button:hover {
		color: var(--ink);
	}
	button.on {
		background: var(--sheet);
		color: var(--ink);
		font-weight: 500;
		box-shadow:
			0 0 0 1px var(--rule-strong),
			0 1px 2px rgb(0 0 0 / 8%);
	}
	button:focus-visible {
		outline: 2px solid var(--link);
		outline-offset: 1px;
	}
</style>
