<script lang="ts">
	// On a version's toolbar: ‹ older and newer › through its document's versions in this tab's place, `live text`, `compare with now`, and `restore…`, one line that never wraps. While the two panes are compared it holds older and newer alone, the counter and stop standing beside it. Restore asks in the line under the toolbar, then puts the document back as this version, its text now kept as a version, and turns to the live text, the answer staying in that line. A version that cannot be put back says why on the button.
	import { onDestroy } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { neighbours, versionLabel } from '$lib/review/timeline';
	import { can, write } from '$lib/write';
	import type { Item } from './item';
	import { getPane } from './state.svelte';
	import { setStrip, strips, type Strip } from './strip.svelte';
	import { compareWith, comparingWith, turnTo } from './versions';

	let { item, draft }: { item: Item; draft: string } = $props();

	const m = $derived(store.manifest!);
	const pane = getPane();
	const version = $derived(m.canon?.find((c) => c.path === item.id));
	const near = $derived(neighbours(m, item.id));
	const file = $derived(draft.split('/').pop() ?? draft);
	const comparing = $derived(comparingWith(item, draft));
	let restores = $state(false);
	$effect(() => {
		void can('history-restore').then((yes) => (restores = yes));
	});
	const capital = (t: string) => t.charAt(0).toUpperCase() + t.slice(1) + (t.endsWith('.') ? '' : '.');

	let asking: Strip | undefined;
	function ask(): void {
		asking = {
			text: `Put ${file} back as this version? Its text now is kept as a version.`,
			testid: 'version-ask',
			acts: [
				{ label: 'Restore', testid: 'version-restore-go', primary: true, run: () => void restore() },
				{ label: 'Cancel', testid: 'version-restore-cancel', run: () => setStrip(pane.index, undefined) }
			]
		};
		setStrip(pane.index, asking);
	}
	// a question left open goes with the version it asked about; an answer stays
	onDestroy(() => {
		if (asking && strips[pane.index] === asking) setStrip(pane.index, undefined);
	});

	async function restore(): Promise<void> {
		const index = pane.index;
		setStrip(index, { ...asking!, busy: true });
		const done = await write('history-restore', { document: draft, version: item.id });
		asking = undefined;
		if (!done.ok) {
			setStrip(index, { text: done.error?.message ?? 'The publisher refused it.', testid: 'version-said', refused: true });
			return;
		}
		await store.refresh();
		setStrip(index, undefined);
		turnTo(index, item, draft);
		// hung once the pane shows the live text, whose toolbar keeps it
		queueMicrotask(() => setStrip(index, { text: capital(done.result ?? 'restored'), testid: 'version-said' }));
	}
</script>

<span class="version-controls" data-testid="version-controls">
	<button type="button" class="link" disabled={!near?.older} title={near?.older ? versionLabel(near.older) : 'No older version'} data-testid="version-older" onclick={() => near?.older && turnTo(pane.index, item, near.older.path)}>‹ older</button>
	<button type="button" class="link" title={near?.newer ? versionLabel(near.newer) : 'The live text'} data-testid="version-newer" onclick={() => turnTo(pane.index, item, near?.newer?.path ?? draft)}>newer ›</button>
	{#if !comparing}
		<button type="button" class="link" title="The draft's live text, at this result" data-testid="history-live" onclick={() => turnTo(pane.index, item, draft)}>live text</button>
		<button type="button" class="link" data-testid="version-compare" onclick={() => compareWith(pane.index, item, draft)}>compare with now</button>
		{#if restores && version}
			{#if version.cannot_restore}
				<button type="button" class="link" disabled title={version.cannot_restore} data-testid="version-restore">restore…</button>
			{:else}
				<button type="button" class="link" data-testid="version-restore" onclick={ask}>restore…</button>
			{/if}
		{/if}
	{/if}
</span>

<style>
	.version-controls {
		display: inline-flex;
		align-items: center;
		flex-wrap: nowrap;
		gap: 4px;
		white-space: nowrap;
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
	.link:hover:not(:disabled) {
		color: var(--ink);
		background: var(--leaf);
	}
	.link:disabled {
		color: var(--ink-faint);
		cursor: default;
	}
</style>
