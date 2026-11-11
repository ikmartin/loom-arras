<script lang="ts">
	// The undo of a delete: one line per annotation this page deleted, at the foot of the window, each with Undo and ×. The deleted annotation's mark and box are gone once loom rebuilds, so the undo stands here, held until the page closes or × lets it go.
	import { deletions, forget, undoDelete } from './deleted.svelte';

	let busy = $state('');
	let refused = $state<Record<string, string>>({});

	async function undo(id: string): Promise<void> {
		busy = id;
		const why = await undoDelete(id);
		refused = { ...refused, [id]: why };
		busy = '';
	}
</script>

{#if deletions.length}
	<ul class="deleted plain" data-testid="deleted-bar" aria-live="polite">
		{#each deletions as d (d.id)}
			<li data-testid="deleted" data-id={d.id}>
				<span class="said">Deleted {d.said}.</span>
				<button type="button" class="btn small" disabled={!!busy} onclick={() => void undo(d.id)} data-testid="deleted-undo">{busy === d.id ? 'Putting back…' : 'Undo'}</button>
				<button type="button" class="close" title="Forget this delete" aria-label="Forget this delete" onclick={() => forget(d.id)} data-testid="deleted-forget">×</button>
				{#if refused[d.id]}<span class="why" role="status" data-testid="deleted-said">{refused[d.id]}</span>{/if}
			</li>
		{/each}
	</ul>
{/if}

<style>
	.deleted {
		position: fixed;
		z-index: 60;
		left: 50%;
		bottom: var(--gap);
		transform: translateX(-50%);
		display: grid;
		gap: var(--gap-hair);
		max-width: calc(100vw - 2 * var(--gap));
		margin: 0;
		padding: 0;
		font-family: var(--sans);
		font-size: 13px;
	}
	li {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--gap-tight);
		padding: 6px 10px;
		background: var(--sheet);
		color: var(--ink);
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		box-shadow: var(--float-shadow);
	}
	.close {
		font: inherit;
		font-size: 16px;
		line-height: 1;
		background: none;
		border: 0;
		color: var(--ink-faint);
		cursor: pointer;
		padding: 0 2px;
	}
	.close:hover {
		color: var(--ink);
	}
	.why {
		flex-basis: 100%;
		color: var(--state-incomplete);
	}
</style>
