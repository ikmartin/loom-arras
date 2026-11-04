<script lang="ts">
	// Review › Record › Everything recorded: every act the history holds, in words, newest first, for one document or for all; an undo's set-aside text is put back from its row, after asking. An act's answer stays with it when a newer act arrives above it.
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { shortDate } from '$lib/badges';
	import { store } from '$lib/manifest/client.svelte';
	import { isAgentDocument } from '$lib/manifest/documents';
	import type { HistoryAct } from '$lib/manifest/types';
	import Empty from '$lib/review/Empty.svelte';
	import Said from '$lib/review/Said.svelte';
	import { actWords, actsOf, filesOf } from '$lib/review/timeline';
	import { can, write } from '$lib/write';

	const m = $derived(store.manifest!);
	const mine = $derived(m.masters.filter((x) => !x.closed && !x.context_only && !isAgentDocument(x)));
	const doc = $derived(mine.find((x) => x.path === page.url.searchParams.get('document')));
	const acts = $derived(actsOf(m, doc?.path ?? '', doc ? filesOf(m, doc.path) : new Set()));
	const file = (p: string) => p.split('/').pop() ?? p;

	let restores = $state(false);
	let asking = $state('');
	let busy = $state('');
	let said = $state<{ at: string; text: string; refused: boolean } | null>(null);
	onMount(() => {
		void can('history-restore').then((yes) => (restores = yes));
	});

	const capital = (t: string) => t.charAt(0).toUpperCase() + t.slice(1) + (t.endsWith('.') ? '' : '.');
	/** An act's own name, so its answer stays with it when a newer act arrives above it. */
	const actId = (a: HistoryAct) => `act-${a.when}-${a.action}-${a.path ?? a.in ?? ''}`;
	async function putBack(a: HistoryAct): Promise<void> {
		const at = actId(a);
		busy = at;
		said = null;
		const done = await write('history-restore', { path: a.path, text: a.from });
		if (done.ok) await store.refresh();
		said = { at, text: done.ok ? capital(done.result ?? 'done') : (done.error?.message ?? 'The publisher refused it.'), refused: !done.ok };
		busy = '';
		asking = '';
	}
</script>

{#if !(m.history?.acts ?? []).length}
	<Empty text="Nothing has been recorded yet." testid="history-none" />
{:else}
	<p class="bar">
		{#if mine.length}
			<select aria-label="Whose acts" data-testid="history-only-here" value={doc?.path ?? ''} onchange={(e) => goto(e.currentTarget.value ? `?document=${encodeURIComponent(e.currentTarget.value)}` : '?', { noScroll: true, keepFocus: true })}>
				<option value="">Every document</option>
				{#each mine as d (d.path)}<option value={d.path}>{file(d.path)}</option>{/each}
			</select>
		{/if}
		<span class="muted" data-testid="history-acts-count">{acts.length} {acts.length === 1 ? 'act' : 'acts'}</span>
	</p>
	<table class="list" data-testid="history-acts">
		<tbody>
			{#each acts as a, i (`${a.when}-${a.action}-${i}`)}
				<tr data-testid="history-act" data-action={a.action}>
					<td>{actWords(a)}{#if said?.at === actId(a)}<Said text={said.text} refused={said.refused} testid="history-act-said" />{/if}</td>
					<td class="when">{a.when ? shortDate(a.when) : ''}</td>
					<td class="muted">{a.actor ?? ''}</td>
					<td class="put">
						{#if restores && a.action === 'undo' && a.from && a.path}
							{#if asking === actId(a)}
								<button class="btn small primary" disabled={!!busy} data-testid="history-put-back-go" onclick={() => void putBack(a)}>Put it back</button>
								<button class="btn small quiet" onclick={() => (asking = '')}>Cancel</button>
							{:else}
								<button class="btn small" title="Write the text this undo set aside back into {a.path}; its text now is kept first" data-testid="history-put-back" onclick={() => ((asking = actId(a)), (said = null))}>Put back…</button>
							{/if}
						{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
{/if}

<style>
	.bar {
		display: flex;
		align-items: center;
		gap: 10px;
		margin: 0 0 var(--gap-tight);
	}
	table {
		margin: 0;
		width: 100%;
	}
	.muted {
		color: var(--ink-soft);
		font-size: 12.5px;
	}
	.when {
		white-space: nowrap;
		color: var(--ink-soft);
	}
	.put {
		text-align: right;
		white-space: nowrap;
	}
</style>
