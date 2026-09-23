<script lang="ts">
	// The local graph with its controls (book 15.5.1): how far out to draw, dots or boxes as in the graph view, a larger drawing on demand, and — where it floats over the read view — a way to put it away.
	import Icon from '$lib/components/Icon.svelte';
	import Popover from '$lib/components/Popover.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import LocalGraph from './LocalGraph.svelte';
	import LocalBoxGraph from './LocalBoxGraph.svelte';
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
	let drawAs = $state<'dot' | 'box'>('dot');
	let expanded = $state(false);
	const m = $derived(store.manifest);
	const owner = $derived(m?.keys[center]?.node ?? center);
	const label = $derived(m ? shortLabel(m, owner, master) : center);
</script>

{#snippet controls()}
	<div class="group" role="group" aria-label="Steps out from the centre">
		{#each [1, 2] as d (d)}
			<button class:on={depth === d} aria-pressed={depth === d} onclick={() => (depth = d)} title="{d} {d === 1 ? 'step' : 'steps'} out">{d}</button>
		{/each}
	</div>
	<span class="sep" aria-hidden="true"></span>
	<div class="group" role="group" aria-label="Drawing">
		<button class:on={drawAs === 'dot'} aria-pressed={drawAs === 'dot'} onclick={() => (drawAs = 'dot')} title="dots, placed by force" data-testid="local-graph-dot">Dot</button>
		<button class:on={drawAs === 'box'} aria-pressed={drawAs === 'box'} onclick={() => (drawAs = 'box')} title="boxes, in layers" data-testid="local-graph-box-toggle">Box</button>
	</div>
	<span class="sep" aria-hidden="true"></span>
{/snippet}

<div class="panel" data-testid="local-graph-panel">
	<div class="bar">
		<span class="title">Local Graph</span>
		{@render controls()}
		<button class="icon" onclick={() => (expanded = true)} aria-label="Expand the local graph" title="expand" data-testid="local-graph-expand"><Icon name="expand" size={13} /></button>
		{#if onclose}<button class="icon" onclick={onclose} aria-label="Close the local graph" title="close" data-testid="local-graph-close"><Icon name="close" size={13} /></button>{/if}
	</div>
	{#if drawAs === 'box'}
		<LocalBoxGraph center={owner} {depth} {height} {master} {hrefFor} />
	{:else}
		<LocalGraph center={owner} {depth} {height} {master} {hrefFor} />
	{/if}
</div>

<Popover modal bind:open={expanded} label="the neighbourhood of {label}" testid="local-graph-dialog">
	<div class="dialog">
		<div class="bar">
			<span class="title">Local Graph</span>
			{@render controls()}
			<button class="icon" onclick={() => (expanded = false)} aria-label="Close" title="close"><Icon name="close" size={14} /></button>
		</div>
		{#if drawAs === 'box'}
			<LocalBoxGraph center={owner} {depth} height={Math.round(window.innerHeight * 0.72)} {master} {hrefFor} />
		{:else}
			<LocalGraph center={owner} {depth} height={Math.round(window.innerHeight * 0.72)} {master} {hrefFor} allLabels />
		{/if}
	</div>
</Popover>

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
	.title {
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--ink-soft);
	}
	.group {
		display: flex;
		gap: 2px;
	}
	.sep {
		align-self: stretch;
		width: 1px;
		margin: 2px 1px;
		background: var(--rule);
	}
	.group button,
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
	.group button.on {
		background: var(--link-wash);
		border-color: var(--link);
		color: var(--link);
	}
	.icon:hover,
	.group button:hover {
		color: var(--ink);
	}
	.dialog {
		width: min(80vw, 1100px);
		padding: var(--gap);
		display: flex;
		flex-direction: column;
		gap: var(--gap-tight);
	}
	.dialog .bar {
		font-size: 12px;
	}
</style>
