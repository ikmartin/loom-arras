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
	.seg {
		display: inline-flex;
		border: 1px solid var(--rule);
		border-radius: 8px;
		overflow: hidden;
		background: var(--leaf);
	}
	button {
		font: inherit;
		font-family: var(--sans);
		font-size: 12.5px;
		white-space: nowrap;
		padding: 5px 12px;
		border: 0;
		border-left: 1px solid var(--rule);
		background: none;
		color: var(--ink-soft);
		cursor: pointer;
	}
	button:first-child {
		border-left: 0;
	}
	button:hover {
		color: var(--ink);
	}
	button.on {
		background: var(--sheet);
		color: var(--ink);
		font-weight: 500;
		box-shadow: inset 0 0 0 1px var(--rule-strong);
	}
</style>
