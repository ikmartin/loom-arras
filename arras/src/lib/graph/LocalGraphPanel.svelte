<script lang="ts">
	// The local graph with its controls (book 15.5.1): how far out to draw, a larger drawing on demand, and — where it floats over the read view — a way to put it away.
	import Icon from '$lib/components/Icon.svelte';
	import { dismiss } from '$lib/dismiss';
	import { store } from '$lib/manifest/client.svelte';
	import LocalGraph from './LocalGraph.svelte';
	import { shortLabel } from './local';

	let {
		center,
		master = undefined,
		hrefFor = undefined,
		height = 200,
		onclose = undefined
	}: {
		center: string;
		master?: string;
		hrefFor?: (id: string) => string;
		height?: number;
		/** Given, the panel offers to close itself; the read view's floating panel passes it, the node page's rail does not. */
		onclose?: () => void;
	} = $props();

	let depth = $state(1);
	let expanded = $state(false);
	const m = $derived(store.manifest);
	const owner = $derived(m?.keys[center]?.node ?? center);
	const label = $derived(m ? shortLabel(m, owner, master) : center);
</script>

{#snippet controls()}
	<div class="depth" role="group" aria-label="Steps out from the centre">
		{#each [1, 2] as d (d)}
			<button class:on={depth === d} aria-pressed={depth === d} onclick={() => (depth = d)} title="{d} {d === 1 ? 'step' : 'steps'} out">{d}</button>
		{/each}
	</div>
{/snippet}

<div class="panel" data-testid="local-graph-panel">
	<div class="bar">
		<span class="around" title={owner}>around {label}</span>
		{@render controls()}
		<button class="icon" onclick={() => (expanded = true)} aria-label="Expand the local graph" title="expand" data-testid="local-graph-expand"><Icon name="expand" size={13} /></button>
		{#if onclose}<button class="icon" onclick={onclose} aria-label="Close the local graph" title="close" data-testid="local-graph-close"><Icon name="close" size={13} /></button>{/if}
	</div>
	<LocalGraph center={owner} {depth} {height} {master} {hrefFor} />
</div>

{#if expanded}
	<div class="backdrop">
		<div class="dialog" role="dialog" aria-modal="true" aria-label="the neighbourhood of {label}" use:dismiss={() => (expanded = false)} data-testid="local-graph-dialog">
			<div class="bar">
				<span class="around">around {label}</span>
				{@render controls()}
				<button class="icon" onclick={() => (expanded = false)} aria-label="Close" title="close"><Icon name="close" size={14} /></button>
			</div>
			<LocalGraph center={owner} {depth} height={Math.round(window.innerHeight * 0.72)} {master} {hrefFor} allLabels />
		</div>
	</div>
{/if}

<style>
	.panel {
		display: flex;
		flex-direction: column;
		gap: var(--gap-hair);
	}
	.bar {
		display: flex;
		align-items: center;
		gap: var(--gap-hair);
		font-family: var(--sans);
		font-size: 10px;
		color: var(--ink-faint);
		min-width: 0;
	}
	.around {
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.depth {
		display: flex;
		gap: 2px;
	}
	.depth button,
	.icon {
		font: inherit;
		font-size: 10px;
		line-height: 1;
		min-width: 18px;
		height: 18px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--ink-soft);
		background: var(--leaf);
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		padding: 0 4px;
		cursor: pointer;
	}
	.depth button.on {
		background: var(--link-wash);
		border-color: var(--link);
		color: var(--link);
	}
	.icon:hover,
	.depth button:hover {
		color: var(--ink);
	}
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 50;
		background: rgb(0 0 0 / 22%);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.dialog {
		width: min(80vw, 1100px);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		box-shadow: 0 10px 40px rgb(0 0 0 / 20%);
		padding: var(--gap);
		display: flex;
		flex-direction: column;
		gap: var(--gap-tight);
	}
	.dialog .bar {
		font-size: 12px;
	}
</style>
