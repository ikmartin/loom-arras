<script lang="ts">
	// The development shelf (plan 0.13 §7): the indexes — tags, taxa, threads, loose — which are scaffolding we keep while building and not part of the interface a reader is meant to learn. It stands at the foot of the icon strip rather than in the panel, so the panel holds only what a reader uses, and it keeps its odd symbol rather than a designed icon so that nobody mistakes it for a view and so it is conspicuous on the day it should be taken out.
	import Popover from '$lib/components/Popover.svelte';
	import type { Index } from './views';

	let { indexes }: { indexes: Index[] } = $props();
</script>

<Popover placement="right" testid="dev-sheet">
	{#snippet trigger({ open, toggle })}
		<button class="toggle" aria-label="Development" aria-expanded={open} title="development" data-testid="dev-shelf" onclick={toggle}>⚗</button>
	{/snippet}
	<div class="sheet">
		<p class="lbl">Development</p>
		<ul>
			{#each indexes as x (x.href)}
				<li><a href={x.href}>{x.label}</a></li>
			{/each}
		</ul>
	</div>
</Popover>

<style>
	/* Sized like the strip's own controls, so it sits in the column rather than beside it. */
	.toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 26px;
		font-size: 15px;
		line-height: 1;
		color: var(--ink-faint);
		background: none;
		border: none;
		border-radius: var(--rad-control);
		cursor: pointer;
	}
	.toggle:hover,
	.toggle[aria-expanded='true'] {
		color: var(--ink);
		background: var(--sheet);
	}
	.sheet {
		width: max-content;
		max-width: 260px;
		padding: var(--gap);
	}
	.lbl {
		font-size: 9px;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-faint);
		margin: 0 0 var(--gap-hair);
	}
	.sheet ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.sheet a {
		display: block;
		font-size: 11px;
		color: var(--ink-soft);
		padding: 2px 4px;
		border-radius: var(--rad-pill);
	}
	.sheet a:hover {
		color: var(--ink);
		text-decoration: none;
	}
</style>
