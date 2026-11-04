<script lang="ts">
	// **history ▾** on a document's toolbar (plan 0.20.6, 0.25.5): `record this version…`, its live text, and its versions newest first, each named by the act it was kept at and with a `compare` at its right, the newest twelve and the rest in Review › History; then its live agent copies to compare with. A landmark of the draft carries the same menu, and an agent copy one line, for its source. Choosing a version shows it in this tab's place, at the result the reader was at; choosing `compare` opens the other beside and compares the two, and choosing it again stops. Drawn only where there is a history to list (`historyOf`).
	import { shortDate } from '$lib/badges';
	import { store } from '$lib/manifest/client.svelte';
	import type { CanonDoc } from '$lib/manifest/types';
	import { uncomparable } from './compare.svelte';
	import { historyOf } from './history';
	import type { Item } from './item';
	import { getPane } from './state.svelte';
	import { workspace } from './store.svelte';
	import ToolbarItem from './ToolbarItem.svelte';
	import ToolbarMenu from './ToolbarMenu.svelte';
	import { compareWith, comparingWith, turnTo } from './versions';
	import { versionLabel } from '$lib/review/timeline';
	import { route } from '$lib/paths';
	import { can } from '$lib/write';
	import { goto } from '$app/navigation';

	/** How many versions the menu lists; the rest are in Review › History. */
	const SHOWN = 12;

	let { item, name, divided = false }: { item: Item; name: string; divided?: boolean } = $props();

	const m = $derived(store.manifest!);
	const pane = getPane();
	const history = $derived(historyOf(m, item.id));
	let records = $state(false);
	$effect(() => {
		void can('history-record').then((yes) => (records = yes));
	});
	const inReview = (doc: string) => route('/review/history') + '?document=' + encodeURIComponent(doc);
	// the menu lists only what pairs, so the one reason compare cannot start is the window's width
	const why = $derived(workspace.narrow ? uncomparable(true) : '');
	const file = (p: string) => p.split('/').pop() ?? p;
	const stem = (p: string) => file(p).replace(/\.tex$/, '');
	const when = (c: CanonDoc) => [c.step ? `step ${Number(c.step)}` : '', c.when ? shortDate(c.when) : ''].filter(Boolean).join(' · ');
</script>

{#snippet row(id: string, label: string, testid: string, aside = '', title = '')}
	<div class="row" role="none" title={title || undefined}>
		<button type="button" class="version" role="menuitemradio" tabindex="-1" aria-checked={id === item.id} aria-label="{label}, {name}" data-testid="history-version-{testid}" onclick={() => turnTo(pane.index, item, id)}
			><span class="mark" aria-hidden="true">{id === item.id ? '●' : ''}</span><span class="lab">{label}</span>{#if aside}<span class="aside">{aside}</span>{/if}</button
		>
		{#if id !== item.id}
			<button
				type="button"
				class="cmp"
				role="menuitemcheckbox"
				tabindex="-1"
				aria-checked={comparingWith(item, id)}
				aria-disabled={why ? 'true' : undefined}
				aria-label="compare {name} with {label}"
				title={why || undefined}
				data-testid="history-compare-{testid}"
				onclick={() => !why && compareWith(pane.index, item, id)}>compare</button
			>
		{/if}
	</div>
{/snippet}

{#if history}
	<ToolbarMenu label="history" name="history menu for {name}" menuName="history of {name}" testid="toolbar-history" menuTestid="history-menu" {divided} width={320}>
		{#if history.of === 'draft'}
			{#if records}<ToolbarItem label="record this version…" name="record a version of {name}" testid="history-record" onclick={() => goto(inReview(history.draft) + '&record=1')} /><hr />{/if}
			{@render row(history.draft, 'live text', 'live')}
			{#each history.landmarks.slice(0, SHOWN) as c (c.path)}{@render row(c.path, versionLabel(c), c.name ?? c.stem, when(c))}{/each}
			{#if history.landmarks.length > SHOWN}
				<ToolbarItem label="{history.landmarks.length - SHOWN} older, in Review › History" name="every version of {name}" testid="history-older" onclick={() => goto(inReview(history.draft))} />
			{/if}
			{#if history.copies.length}
				<hr />
				{#each history.copies as x (x.path)}
					<ToolbarItem
						label="compare with {file(x.path)}"
						name="compare {name} with {file(x.path)}"
						checked={comparingWith(item, x.path)}
						off={why || undefined}
						testid="history-compare-{stem(x.path)}"
						onclick={() => compareWith(pane.index, item, x.path)}
					/>
				{/each}
			{/if}
		{:else}
			<ToolbarItem
				label="compare with {file(history.source)}"
				name="compare {name} with {file(history.source)}"
				checked={comparingWith(item, history.source)}
				off={why || undefined}
				testid="history-compare-{stem(history.source)}"
				onclick={() => compareWith(pane.index, item, history.source)}
			/>
		{/if}
	</ToolbarMenu>
{/if}

<style>
	.row {
		display: flex;
		align-items: stretch;
	}
	.version,
	.cmp {
		font: inherit;
		color: var(--ink);
		text-align: left;
		background: none;
		border: 0;
		cursor: pointer;
	}
	.version {
		flex: 1 1 auto;
		min-width: 0;
		display: flex;
		align-items: baseline;
		gap: 6px;
		padding: 5px 8px 5px 10px;
	}
	.mark {
		flex: none;
		width: 0.8em;
		color: var(--link);
		font-size: 0.8em;
	}
	.lab {
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.aside {
		margin-left: auto;
		padding-left: 10px;
		font-size: 11px;
		color: var(--ink-faint);
		font-variant-numeric: tabular-nums;
	}
	.cmp {
		flex: none;
		padding: 5px 12px 5px 8px;
		font-size: 11.5px;
		color: var(--link);
	}
	.cmp[aria-checked='true'] {
		color: var(--ink);
		background: var(--link-wash);
	}
	.cmp[aria-disabled='true'] {
		color: var(--ink-faint);
		opacity: 0.6;
		cursor: default;
	}
	.version:hover,
	.version:focus-visible,
	.cmp:hover:not([aria-disabled='true']),
	.cmp:focus-visible {
		background: var(--leaf);
		outline: none;
	}
</style>
