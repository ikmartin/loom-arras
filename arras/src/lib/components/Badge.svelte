<script lang="ts">
	import type { BadgePart } from '$lib/badges';

	let { parts, facts = '' }: { parts: BadgePart[]; facts?: string } = $props();
</script>

<span class="badge">
	{#each parts as p, i (i)}
		<span class="chip chip-{p.color}">{p.text}</span>
	{/each}
	{#if facts}<span class="facts">{facts}</span>{/if}
</span>

<style>
	.badge {
		display: inline-flex;
		flex-wrap: wrap;
		gap: 0.3rem;
		align-items: baseline;
	}
	.chip {
		font-size: 0.75rem;
		padding: 0.05rem 0.45rem;
		border-radius: 999px;
		border: 1px solid var(--chip-border);
		background: var(--chip-neutral);
		color: var(--fg);
	}
	.chip-positive {
		background: var(--chip-positive);
	}
	.chip-positive-strong {
		background: var(--chip-positive-strong);
		color: #fff;
	}
	.chip-warning {
		background: var(--chip-warning);
	}
	.chip-negative {
		background: var(--chip-negative);
		color: #fff;
	}
	.chip-info {
		background: var(--chip-info);
	}
	.facts {
		font-size: 0.8rem;
		color: var(--muted);
	}
</style>
