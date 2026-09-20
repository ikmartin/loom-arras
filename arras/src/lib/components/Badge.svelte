<script lang="ts">
	// A state badge (book 15.3.2): a 14px pill, tinted background, state-coloured text. The colour comes from `state.ts`, never from this component.
	import type { BadgePart } from '$lib/badges';
	import { toneClass } from '$lib/state';

	let { parts, facts = '' }: { parts: BadgePart[]; facts?: string } = $props();
</script>

<span class="badge">
	{#each parts as p, i (i)}
		<span class="chip {toneClass(p.color)}">{p.text}</span>
	{/each}
	{#if facts}<span class="facts">{facts}</span>{/if}
</span>

<style>
	.badge {
		display: inline-flex;
		flex-wrap: wrap;
		gap: var(--gap-hair);
		align-items: baseline;
	}
	.chip {
		font-family: var(--sans);
		font-size: 9px;
		letter-spacing: 0.03em;
		text-transform: lowercase;
		line-height: 14px;
		padding: 0 6px;
		border-radius: var(--rad-pill);
		background: var(--tone-wash);
		color: var(--tone);
	}
	.facts {
		font-family: var(--sans);
		font-size: 10px;
		color: var(--ink-faint);
	}
</style>
