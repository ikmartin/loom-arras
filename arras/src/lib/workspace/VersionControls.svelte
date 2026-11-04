<script lang="ts">
	// On a version's toolbar (plan 0.25.5): ‹ older and newer › through its document's versions in this tab's place, `live text` and `compare with now`, and `restore…`, which asks first and then puts the document back as this version, its text now kept as a version, and turns back to the live text. A version that cannot be put back says why on the button.
	import { store } from '$lib/manifest/client.svelte';
	import { neighbours, versionLabel } from '$lib/review/timeline';
	import Said from '$lib/review/Said.svelte';
	import { can, write } from '$lib/write';
	import type { Item } from './item';
	import { getPane } from './state.svelte';
	import { compareWith, comparingWith, turnTo } from './versions';

	let { item, draft }: { item: Item; draft: string } = $props();

	const m = $derived(store.manifest!);
	const pane = getPane();
	const version = $derived(m.canon?.find((c) => c.path === item.id));
	const near = $derived(neighbours(m, item.id));
	const file = $derived(draft.split('/').pop() ?? draft);
	let restores = $state(false);
	let asking = $state(false);
	let busy = $state(false);
	let said = $state<{ text: string; refused: boolean } | null>(null);
	$effect(() => {
		void can('history-restore').then((yes) => (restores = yes));
	});
	const capital = (t: string) => t.charAt(0).toUpperCase() + t.slice(1) + (t.endsWith('.') ? '' : '.');

	async function restore(): Promise<void> {
		busy = true;
		said = null;
		const done = await write('history-restore', { document: draft, version: item.id });
		busy = false;
		asking = false;
		if (!done.ok) {
			said = { text: done.error?.message ?? 'The publisher refused it.', refused: true };
			return;
		}
		await store.refresh();
		said = { text: capital(done.result ?? 'restored'), refused: false };
		turnTo(pane.index, item, draft);
	}
</script>

<span class="version-controls" data-testid="version-controls">
	<button type="button" class="link" disabled={!near?.older} title={near?.older ? versionLabel(near.older) : 'No older version'} data-testid="version-older" onclick={() => near?.older && turnTo(pane.index, item, near.older.path)}>‹ older</button>
	<button type="button" class="link" title={near?.newer ? versionLabel(near.newer) : 'The live text'} data-testid="version-newer" onclick={() => turnTo(pane.index, item, near?.newer?.path ?? draft)}>newer ›</button>
	<button type="button" class="link" title="The draft's live text, at this result" data-testid="history-live" onclick={() => turnTo(pane.index, item, draft)}>live text</button>
	<button type="button" class="link" aria-pressed={comparingWith(item, draft)} data-testid="version-compare" onclick={() => compareWith(pane.index, item, draft)}>compare with now</button>
	{#if restores && version}
		{#if version.cannot_restore}
			<button type="button" class="link" disabled title={version.cannot_restore} data-testid="version-restore">restore…</button>
		{:else if asking}
			<span class="ask" data-testid="version-ask">Put {file} back as this version? Its text now is kept as a version.</span>
			<button type="button" class="btn small primary" disabled={busy} data-testid="version-restore-go" onclick={() => void restore()}>{busy ? 'Restoring…' : 'Restore'}</button>
			<button type="button" class="btn small quiet" disabled={busy} onclick={() => (asking = false)}>Cancel</button>
		{:else}
			<button type="button" class="link" data-testid="version-restore" onclick={() => ((asking = true), (said = null))}>restore…</button>
		{/if}
	{/if}
	{#if said}<Said text={said.text} refused={said.refused} testid="version-said" />{/if}
</span>

<style>
	.version-controls {
		display: inline-flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 2px 4px;
	}
	.link {
		font: inherit;
		color: var(--link);
		background: none;
		border: 0;
		border-radius: var(--rad-control);
		padding: 2px 8px;
		cursor: pointer;
	}
	.link:hover:not(:disabled),
	.link[aria-pressed='true'] {
		color: var(--ink);
		background: var(--leaf);
	}
	.link:disabled {
		color: var(--ink-faint);
		cursor: default;
	}
	.ask {
		font-size: 12.5px;
		color: var(--ink-soft);
		padding: 0 4px;
	}
</style>
