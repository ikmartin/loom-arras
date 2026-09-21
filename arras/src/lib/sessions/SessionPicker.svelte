<script lang="ts">
	// The side panel's Sessions section (plan 0.13 §5, §7): what loom is writing into, what the page is showing, and
	// the sessions there are to choose between.
	//
	// **Writing and showing are two different things**, and the panel says both in words rather than leaving the reader
	// to infer one from the other. Writing lands in the session loom says is active, whatever is being shown; the
	// selection is a view. A viewer that moved the write target when the view changed would file work where it was not
	// meant to go, and the reader would find out later.
	import { store } from '$lib/manifest/client.svelte';
	import { active, grouped, sessionView, summary } from './sessions.svelte';
	import { write } from '$lib/write';
	import { sessionUrl } from '$lib/nav';

	const m = $derived(store.manifest);
	const here = $derived(active(m));
	const groups = $derived(grouped(m));
	let busy = $state('');
	let renaming = $state('');
	let title = $state('');

	async function rename(id: string): Promise<void> {
		const want = title.trim();
		renaming = '';
		if (!want) return;
		busy = id;
		await write('session-rename', { session: id, title: want });
		busy = '';
		store.refresh();
	}

	async function remove(id: string, what: string): Promise<void> {
		if (!globalThis.confirm(`Remove “${what}” from view? Its annotations stay in the log.`)) return;
		busy = id;
		await write('session-delete', { session: id });
		busy = '';
		store.refresh();
	}

	function show(id: string): void {
		sessionView.showing = id;
		sessionView.save();
	}
</script>

<div class="sessions" data-testid="session-picker">
	<p class="line">
		<span class="what">writing to</span>
		{#if here}
			<strong data-testid="session-active">{here.title}</strong>
		{:else}
			<span class="none" data-testid="session-none">nothing yet — the first annotation opens one</span>
		{/if}
	</p>

	<p class="line">
		<span class="what">showing</span>
		<span class="choice" role="group" aria-label="which sessions the page shows">
			<button
				type="button"
				class:on={sessionView.showing !== 'all'}
				disabled={!here}
				data-testid="show-this"
				onclick={() => here && show(here.id)}>this session</button
			><button type="button" class:on={sessionView.showing === 'all'} data-testid="show-all" onclick={() => show('all')}
				>all</button
			>
		</span>
	</p>

	{#each [{ label: 'Active', rows: groups.active ? [groups.active] : [] }, { label: 'Recent', rows: groups.recent }] as band (band.label)}
		{#if band.rows.length}
			<p class="band">{band.label}</p>
			<ul>
				{#each band.rows as s (s.id)}
					{@const it = summary(m, s.id)}
					<li class:showing={sessionView.showing === s.id}>
						<button type="button" class="pick" data-testid="session-{s.id}" onclick={() => show(s.id)}>
							<span class="dot" aria-hidden="true">{s.active ? '●' : '○'}</span>
							<span class="title">{s.title}</span>
							<span class="count">{it.open} open</span>
						</button>
						{#if renaming === s.id}
							<input
								class="rename"
								bind:value={title}
								data-testid="session-rename-{s.id}"
								onkeydown={(e) => e.key === 'Enter' && rename(s.id)}
								onblur={() => rename(s.id)}
							/>
						{:else}
							<span class="verbs">
							<!-- The picker chooses what the page shows; the permalink is where the session is read back whole. -->
							<a href={sessionUrl(s.id)} title="Open this session" aria-label="Open {s.title}" data-testid="session-open-{s.id}">↗</a>
								<button
									type="button"
									title="Rename"
									aria-label="Rename {s.title}"
									disabled={busy === s.id}
									data-testid="session-edit-{s.id}"
									onclick={() => {
										renaming = s.id;
										title = s.title;
									}}>✎</button
								>
								<button
									type="button"
									title="Remove from view"
									aria-label="Remove {s.title}"
									disabled={busy === s.id}
									data-testid="session-delete-{s.id}"
									onclick={() => remove(s.id, s.title)}>✕</button
								>
							</span>
						{/if}
						{#if it.who.length || it.fresh || s.attached?.length}
							<p class="who">
								{it.who.join(', ')}{#each s.attached ?? [] as a (a.who)}<span class="here" data-testid="attached-{a.who}"
										>{a.who} ⟨{a.kind}⟩ attached</span
									>{/each}{#if it.fresh}<span class="fresh">{it.fresh} new</span>{/if}
							</p>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	{/each}

	{#if groups.closed.length}
		<p class="band closed">
			<button type="button" data-testid="show-closed" onclick={() => ((sessionView.closed = !sessionView.closed), sessionView.save())}>
				Closed ({groups.closed.length})
			</button>
			<span class="note">{sessionView.closed ? 'annotations shown' : 'annotations hidden'}</span>
		</p>
	{/if}
</div>

<style>
	.sessions {
		font-size: 0.82rem;
	}
	.line {
		display: flex;
		align-items: baseline;
		gap: 6px;
		margin: 0 0 4px;
	}
	.what {
		color: var(--ink-faint, #6b6b6b);
		font-size: 0.92em;
	}
	.none {
		color: var(--ink-faint, #6b6b6b);
	}
	.choice button {
		font: inherit;
		font-size: 0.92em;
		color: inherit;
		background: none;
		border: 1px solid var(--rule, #ddd9cf);
		padding: 0 6px;
		cursor: pointer;
	}
	.choice button:first-child {
		border-radius: 3px 0 0 3px;
	}
	.choice button:last-child {
		border-radius: 0 3px 3px 0;
		border-left: 0;
	}
	.choice button.on {
		background: var(--annotation-tint, rgb(217 119 87 / 0.18));
	}
	.band {
		margin: 8px 0 2px;
		font-size: 0.72em;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-faint, #6b6b6b);
	}
	.band button {
		font: inherit;
		color: inherit;
		background: none;
		border: 0;
		padding: 0;
		cursor: pointer;
		text-transform: inherit;
		letter-spacing: inherit;
	}
	.note {
		text-transform: none;
		letter-spacing: 0;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		display: grid;
		grid-template-columns: 1fr auto;
		align-items: baseline;
		padding: 1px 0;
	}
	li.showing {
		background: var(--annotation-tint, rgb(217 119 87 / 0.12));
	}
	.pick {
		display: flex;
		gap: 5px;
		align-items: baseline;
		font: inherit;
		color: inherit;
		background: none;
		border: 0;
		padding: 0;
		text-align: left;
		cursor: pointer;
		min-width: 0;
	}
	.title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.count {
		margin-left: auto;
		color: var(--ink-faint, #6b6b6b);
		font-size: 0.9em;
		white-space: nowrap;
	}
	.verbs a {
		color: var(--ink-faint, #6b6b6b);
		text-decoration: none;
		font-size: 0.9em;
		padding: 0 2px;
	}
	.verbs a:hover {
		color: var(--ink, #1b1b1b);
	}
	.verbs button {
		font: inherit;
		font-size: 0.9em;
		color: var(--ink-faint, #6b6b6b);
		background: none;
		border: 0;
		padding: 0 2px;
		cursor: pointer;
	}
	.verbs button:hover {
		color: var(--ink, #1b1b1b);
	}
	.who {
		grid-column: 1 / -1;
		margin: 0 0 2px 16px;
		color: var(--ink-faint, #6b6b6b);
		font-size: 0.86em;
	}
	.fresh {
		margin-left: 6px;
		color: var(--annotation, #c05621);
	}
	.here {
		margin-left: 6px;
		color: var(--link, #35618f);
	}
	.rename {
		font: inherit;
		width: 100%;
	}
</style>
