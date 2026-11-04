<script lang="ts">
	// The bar at the head of a Review page: what the page is about and its acts, pinned while the page scrolls so an act is never out of reach, and the answer to the last act on the page said inside it, beside the controls that made it. `below` is a second row for the item on screen, its own controls held still while it scrolls beneath.
	import type { Snippet } from 'svelte';
	import Said from './Said.svelte';

	let { lead, actions, below, said = '', refused = false, testid = 'action-bar' }: { lead?: Snippet; actions?: Snippet; below?: Snippet; said?: string; refused?: boolean; testid?: string } = $props();
</script>

<div class="action-bar" data-testid={testid}>
	<div class="lead">{@render lead?.()}</div>
	{#if actions}<div class="acts">{@render actions()}</div>{/if}
	{#if said}<div class="answer"><Said text={said} {refused} testid="{testid}-said" /></div>{/if}
	{#if below}<div class="below">{@render below()}</div>{/if}
</div>

<style>
	.action-bar {
		position: sticky;
		top: 0;
		z-index: 5;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--gap-tight) var(--gap);
		margin: 0 0 var(--gap);
		padding: var(--gap-tight) 0;
		background: var(--paper);
		border-bottom: 1px solid var(--rule);
	}
	.lead {
		flex: 1;
		min-width: 0;
		font-size: 13px;
		color: var(--ink);
	}
	.acts {
		display: flex;
		align-items: center;
		gap: var(--gap-tight);
	}
	.answer,
	.below {
		flex-basis: 100%;
	}
	/* a second row for what is on screen beneath the bar, the controls for one item among many */
	.below {
		padding-top: var(--gap-tight);
		border-top: 1px solid var(--rule);
	}
</style>
