<script lang="ts">
	// The question asked where the quilt has the network off and an act could use it: allow it for this one act, go on without it where that still does something (a run still extracts and maps), or not act at all.
	let {
		onallow,
		onoffline,
		oncancel,
		question = 'This looks works up and fetches them, which needs the network, off in this quilt. Allow it for this run?',
		allow = 'Allow and run',
		offline = 'Run offline'
	}: { onallow: () => void; onoffline?: () => void; oncancel: () => void; question?: string; allow?: string; offline?: string } = $props();
</script>

<div class="ask" role="group" aria-label="Allow the network" data-testid="network-ask">
	<span>{question}</span>
	<span class="buttons">
		<button class="btn" onclick={onallow} data-testid="network-allow">{allow}</button>
		{#if onoffline}<button class="btn" onclick={onoffline} data-testid="network-offline">{offline}</button>{/if}
		<button class="btn quiet" onclick={oncancel}>Cancel</button>
	</span>
</div>

<style>
	.ask {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px 10px;
		margin: 0 0 16px;
		padding: 8px 12px;
		border-radius: 8px;
		background: var(--state-stale-wash);
		color: var(--ink);
		font-family: var(--sans);
		font-size: 12.5px;
	}
	.buttons {
		display: flex;
		gap: 6px;
	}
	.btn {
		font: inherit;
		font-size: 12px;
		padding: 3px 10px;
		border-radius: 6px;
		border: 1px solid var(--rule);
		background: var(--sheet);
		color: var(--ink);
		cursor: pointer;
	}
	.btn:hover {
		background: var(--link-wash);
	}
	.btn.quiet {
		border-color: transparent;
		background: none;
		color: var(--ink-soft);
	}
</style>
