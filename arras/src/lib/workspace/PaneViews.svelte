<script lang="ts">
	// A pane's active item's views (plan 0.16, decision 10; DR-303-ikmartin), leading its tab strip before the first tab: plain words, the current one underlined in the accent, one that cannot be read now greyed. Drawn on both panes and never fading, since which reading to see is asked on arriving at an item, whichever pane it is in; the default view — the first that can be read — is kept out of its address.
	import { store } from '$lib/manifest/client.svelte';
	import { itemKey } from './item';
	import { kinds, nameOf } from './registry';
	import { workspace } from './store.svelte';
	import { currentView, defaultView } from './views';

	let { index }: { index: number } = $props();

	const m = $derived(store.manifest);
	const item = $derived(workspace.active(index));
	const views = $derived(item && m ? (kinds[item.kind].views?.(item, m) ?? []) : []);
	const name = $derived(item && m ? nameOf(item, m) : '');
	const current = $derived(currentView(views, item?.view));

	function show(id: string): void {
		if (!item) return;
		workspace.update(itemKey(item), { view: id === defaultView(views) ? undefined : id });
	}
</script>

{#if item && views.length > 1}
	<span class="views" role="group" aria-label="views of {name}" data-testid="pane-views-{index}">
		{#each views as v (v.id)}
			{@const on = current === v.id}
			<button
				type="button"
				class:on
				aria-pressed={on}
				aria-label="{v.label} of {name}"
				disabled={!!v.off}
				aria-disabled={v.off ? 'true' : undefined}
				title={v.off}
				data-testid="tab-{v.id}"
				onclick={() => show(v.id)}>{v.label}</button
			>
		{/each}
	</span>
{/if}

<style>
	/* a rule after the views parts them from the first tab, which starts where they end */
	.views {
		flex: none;
		display: flex;
		align-items: stretch;
		gap: 12px;
		padding: 0 14px 0 12px;
		border-right: 1px solid var(--rule);
		font-family: var(--sans);
		font-size: 12.5px;
		white-space: nowrap;
	}
	.views button {
		font: inherit;
		color: var(--link);
		background: none;
		border: 0;
		padding: 0;
		cursor: pointer;
	}
	.views button:hover:not(:disabled) {
		color: var(--ink);
	}
	.views button.on {
		color: var(--ink);
		box-shadow: inset 0 -2px 0 var(--accent);
		cursor: default;
	}
	.views button:disabled {
		color: var(--ink-faint);
		opacity: 0.5;
		cursor: default;
	}
	.views button:focus-visible {
		outline: 2px solid var(--link);
		outline-offset: -2px;
	}
</style>
