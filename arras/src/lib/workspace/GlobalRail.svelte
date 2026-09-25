<script lang="ts">
	// The frame's one rail (plan 0.13.3 F1–F5, plan 0.14). It holds exactly two things: the annotation filter, which governs what documents draw; and the **control cluster** for the current item — its internal views, then its controls — drawn once, since two panes each carrying a row would be the same widgets twice for a document only one of which is being read. Nothing else is global: a session's Chat is opened by choosing the session.
	import { store } from '$lib/manifest/client.svelte';
	import SessionFilter from '$lib/sessions/SessionFilter.svelte';
	import Popover from '$lib/components/Popover.svelte';
	import { itemKey } from './item';
	import { kinds, nameOf } from './registry';
	import { workspace } from './store.svelte';

	const m = $derived(store.manifest);
	const current = $derived(workspace.current);
	const kind = $derived(current ? kinds[current.kind] : null);
	const name = $derived(current && m ? nameOf(current, m) : '');
	const views = $derived(current && m && kind?.views ? kind.views(current, m) : []);

	function view(id: string): void {
		if (!current) return;
		workspace.update(itemKey(current), { view: id === views[0]?.id ? undefined : id });
	}

	// **When the two parts do not fit, the cluster keeps its place.** It acts on what is being read, so it is what a narrow window keeps; the filter, asked for less often, goes behind `⋯`. Its width is taken while it is drawn and remembered, since a part that is not drawn cannot be measured. The cluster is centred in what the filter leaves.
	const GAPS = 3 * 12;
	let width = $state(0);
	let filterW = $state(0);
	let clusterW = $state(0);
	const compact = $derived(width > 0 && filterW + clusterW + GAPS > width);
</script>

<div class="global-rail" class:compact bind:clientWidth={width} data-testid="reading-rail">
	{#if !compact}
		<div class="filter" bind:offsetWidth={filterW}><SessionFilter /></div>
	{/if}
	<div class="cluster" role="group" aria-label={name ? `controls for ${name}` : 'controls'} data-testid="cluster">
		<div class="inner" bind:offsetWidth={clusterW}>
			{#if current && kind}
				{#if views.length > 1}
					<span class="views" role="group" aria-label="views of {name}">
						{#each views as v (v.id)}
							{@const on = (current.view ?? views[0].id) === v.id}
							<button type="button" class:on aria-pressed={on} aria-label="{v.label} of {name}" data-testid="tab-{v.id}" onclick={() => view(v.id)}>{v.label}</button>
						{/each}
					</span>
					{#if kind.controls}<span class="bar" aria-hidden="true"></span>{/if}
				{/if}
				{#if kind.controls}
					{@const Controls = kind.controls}
					{#key itemKey(current)}<Controls item={current} {name} />{/key}
				{/if}
			{/if}
		</div>
	</div>
	{#if compact}
		<Popover placement="below" align="end" testid="rail-more">
			{#snippet trigger({ open, toggle })}
				<button type="button" class="more" aria-label="Annotations shown" aria-expanded={open} data-testid="rail-more-toggle" onclick={toggle}>⋯</button>
			{/snippet}
			<div class="more-box">
				<SessionFilter />
			</div>
		</Popover>
	{/if}
</div>

<style>
	/* The mockup's rail: one line, 12.5px, the filter a quiet label and a pill at the left, the cluster centred with its parts divided by short rules. */
	.global-rail {
		display: grid;
		grid-template-columns: auto 1fr;
		align-items: center;
		gap: 12px;
		height: var(--reading-rail);
		padding: 0 12px;
		border-bottom: 1px solid var(--rule);
		font-family: var(--sans);
		font-size: 12.5px;
		color: var(--ink-soft);
		white-space: nowrap;
		overflow: hidden;
	}
	.global-rail.compact {
		grid-template-columns: 1fr auto;
	}
	.global-rail > * {
		min-width: 0;
	}
	.cluster {
		display: flex;
		justify-content: center;
		min-width: 0;
	}
	.inner {
		display: inline-flex;
		align-items: center;
		gap: 12px;
	}
	.views {
		display: inline-flex;
		gap: 12px;
	}
	.views button {
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 0;
		border-bottom: 2px solid transparent;
		padding: 3px 0 2px;
		cursor: pointer;
	}
	.views button:hover {
		color: var(--ink);
	}
	.views button.on {
		color: var(--ink);
		border-bottom-color: var(--accent);
	}
	.bar {
		width: 1px;
		height: 14px;
		background: var(--rule);
	}
	.more {
		font: inherit;
		font-size: 15px;
		letter-spacing: 1px;
		line-height: 1;
		color: var(--ink-soft);
		background: none;
		border: 0;
		border-radius: 4px;
		padding: 2px 6px;
		cursor: pointer;
	}
	.more:hover {
		background: var(--leaf);
		color: var(--ink);
	}
	.more-box {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 10px;
		padding: 10px 12px;
		font-family: var(--sans);
		font-size: 12.5px;
	}
</style>
