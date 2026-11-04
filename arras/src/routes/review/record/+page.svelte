<script lang="ts">
	// Review › The Record › Versions (plan 0.25.5): one document's versions, oldest to newest and then Now, each kept at an act (the import, an edit kept, the text an undo set aside, changes taken in, one recorded by hand, the text a restore replaced), each opened, compared with now, or put back after asking; and a version recorded here by name. Versions no live document leads to are listed apart, since this is where they are reached from.
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { store } from '$lib/manifest/client.svelte';
	import { isAgentDocument } from '$lib/manifest/documents';
	import type { CanonDoc } from '$lib/manifest/types';
	import { canonUrl, masterUrl } from '$lib/nav';
	import { shortDate } from '$lib/badges';
	import { versionActor, versionLabel, versionsOf } from '$lib/review/timeline';
	import { can, write } from '$lib/write';
	import ActionBar from '$lib/review/ActionBar.svelte';
	import Empty from '$lib/review/Empty.svelte';
	import Said from '$lib/review/Said.svelte';

	const m = $derived(store.manifest!);
	const mine = $derived(m.masters.filter((x) => !x.closed && !x.context_only && !isAgentDocument(x)));
	const doc = $derived(mine.find((x) => x.path === page.url.searchParams.get('document')) ?? mine.find((x) => x.default) ?? mine[0]);
	const file = $derived(doc ? doc.path.split('/').pop()! : '');
	const versions = $derived(doc ? versionsOf(m, doc.path) : []);
	const selected = $derived(versions.find((v) => v.path === page.url.searchParams.get('version')) ?? versions.at(-1));
	const orphans = $derived((m.canon ?? []).filter((c) => c.step && !c.in));
	let records = $state(false);
	let restores = $state(false);
	let naming = $state(false);
	let name = $state('');
	let asking = $state('');
	let busy = $state('');
	let said = $state<{ at: string; text: string; refused: boolean } | null>(null);
	onMount(() => {
		void can('history-record').then((yes) => (records = yes));
		void can('history-restore').then((yes) => (restores = yes));
		naming = page.url.searchParams.has('record');
	});

	const capital = (t: string) => t.charAt(0).toUpperCase() + t.slice(1) + (t.endsWith('.') ? '' : '.');
	const day = (iso?: string) => (iso ? shortDate(iso) : '');
	const compareUrl = (v: CanonDoc) => `${canonUrl(v.path)}?beside=${encodeURIComponent(masterUrl(doc!.path))}&compare=1`;
	function select(v: CanonDoc): void {
		asking = '';
		void goto(`?document=${encodeURIComponent(doc!.path)}&version=${encodeURIComponent(v.path)}`, { noScroll: true, keepFocus: true });
	}

	/** One act, its answer said where it was asked (`at`): '*' the bar, a version's path. */
	async function act(at: string, endpoint: string, body: Record<string, unknown>, after?: () => void): Promise<void> {
		busy = at;
		said = null;
		const done = await write(endpoint, body);
		if (done.ok) {
			await store.refresh();
			after?.();
		}
		said = { at, text: done.ok ? capital(done.result ?? 'done') : (done.error?.message ?? 'The publisher refused it.'), refused: !done.ok };
		busy = '';
		asking = '';
	}
	const record = () =>
		act('*', 'history-record', { document: doc!.path, name: name.trim() }, () => {
			naming = false;
			name = '';
		});
	const restore = (v: CanonDoc) => act('*', 'history-restore', { document: doc!.path, version: v.path });
</script>

	{#if !mine.length && !orphans.length && !(m.history?.acts ?? []).length}
		<Empty text="Nothing has been recorded yet." testid="history-none" />
	{:else}
		{#if doc}
			<ActionBar said={said?.at === '*' ? said.text : ''} refused={said?.refused} testid="history-bar">
				{#snippet lead()}
					{#if mine.length > 1}<select aria-label="Document" data-testid="history-document" value={doc.path} onchange={(e) => goto(`?document=${encodeURIComponent(e.currentTarget.value)}`)}>{#each mine as d (d.path)}<option value={d.path}>{d.path.split('/').pop()}</option>{/each}</select>{:else}<strong>{file}</strong>{/if}
					<span class="muted" data-testid="history-summary">{versions.length} {versions.length === 1 ? 'version' : 'versions'}</span>
				{/snippet}
				{#snippet actions()}
					{#if records}
						{#if naming}
							<!-- svelte-ignore a11y_autofocus -->
							<input class="name" bind:value={name} placeholder="Name this version" aria-label="The version's name" autofocus data-testid="history-record-name" onkeydown={(e) => e.key === 'Enter' && name.trim() && void record()} />
							<button class="btn primary" disabled={!name.trim() || busy === '*'} data-testid="history-record-go" onclick={() => void record()}>{busy === '*' ? 'Recording…' : 'Record'}</button>
							<button class="btn quiet" onclick={() => ((naming = false), (name = ''))}>Cancel</button>
						{:else}
							<button class="btn" data-testid="history-record" onclick={() => ((naming = true), (said = null))}>Record this version</button>
						{/if}
					{/if}
				{/snippet}
			</ActionBar>
			{#if versions.length}
				<ol class="timeline" data-testid="history-timeline">
					{#each versions as v (v.path)}
						<li><button type="button" class="tick" class:at={v.path === selected?.path} aria-current={v.path === selected?.path ? 'true' : undefined} data-testid="history-tick" data-version={v.path} onclick={() => select(v)}><span class="label">{versionLabel(v)}</span><span class="when">{day(v.when)}</span></button></li>
					{/each}
					<li><span class="tick now" data-testid="history-now"><span class="label">Now</span></span></li>
				</ol>
				{#if selected}
					<section class="chosen" data-testid="history-selected">
						<h2>{versionLabel(selected)}</h2>
						<p class="muted">{selected.when ? selected.when.slice(0, 16).replace('T', ' ') : ''}{versionActor(m, selected) ? ` · ${versionActor(m, selected)}` : ''}</p>
						<div class="acts">
							<a class="btn" href={canonUrl(selected.path)} data-testid="history-open">Open</a>
							<a class="btn" href={compareUrl(selected)} data-testid="history-compare">Compare with now</a>
							{#if restores}
								{#if selected.cannot_restore}
									<p class="cannot" data-testid="history-cannot">{selected.cannot_restore}</p>
								{:else if asking === selected.path}
									<span class="ask" data-testid="history-ask">Put {file} back as it was{selected.when ? ` on ${day(selected.when)}` : ''}? Its text now is kept as a version.</span>
									<button class="btn primary" disabled={busy === '*'} data-testid="history-restore-go" onclick={() => void restore(selected)}>{busy === '*' ? 'Restoring…' : 'Restore'}</button>
									<button class="btn quiet" onclick={() => (asking = '')}>Cancel</button>
								{:else}
									<button class="btn" data-testid="history-restore" onclick={() => ((asking = selected.path), (said = null))}>Restore this version</button>
								{/if}
							{/if}
						</div>
					</section>
				{/if}
			{:else}
				<Empty text={`No version of ${file} is kept yet.`} testid="history-no-versions" />
			{/if}
		{/if}
		{#if orphans.length}
			<section class="orphans" data-testid="history-orphans">
				<h2>Versions no document leads to</h2>
				<ul>
					{#each orphans as c (c.path)}
						<li><a href={canonUrl(c.path)}>{c.name ?? c.stem}</a> <span class="orphan" title="no live draft leads to this version" data-testid="history-orphan-{Number(c.step)}">no draft leads here</span></li>
					{/each}
				</ul>
			</section>
		{/if}
	{/if}

<style>
	.timeline {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		list-style: none;
		margin: 0 0 var(--gap);
		padding: 0 0 10px;
		border-bottom: 1px solid var(--rule);
	}
	.tick {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 1px;
		font: inherit;
		text-align: left;
		padding: 6px 10px;
		border: 1px solid var(--rule);
		border-radius: 8px;
		background: var(--review-paper);
		color: var(--ink);
		cursor: pointer;
	}
	.tick .label {
		font-size: 13px;
	}
	.tick .when {
		font-size: 11.5px;
		color: var(--ink-soft);
	}
	.tick.at {
		border-color: var(--review-accent);
		box-shadow: inset 0 0 0 1px var(--review-accent);
	}
	.tick.now {
		cursor: default;
		color: var(--ink-soft);
	}
	.chosen h2 {
		font-size: 17px;
		font-weight: 500;
		margin: 0;
	}
	.chosen .acts {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		margin: 10px 0 var(--gap-wide);
	}
	.cannot,
	.ask {
		margin: 0;
		font-size: 12.5px;
		color: var(--ink-soft);
	}
	.muted {
		color: var(--ink-soft);
		font-size: 12.5px;
	}
	.name {
		font: inherit;
		padding: 3px 8px;
		min-width: 14em;
	}
	.orphans h2 {
		font-size: 14px;
		font-weight: 500;
	}
	.orphan {
		margin-left: 6px;
		font-size: 11px;
		color: var(--state-stale);
	}
</style>
