<script lang="ts">
	// The side panel's session list (plan 0.13.1).
	//
	// **One selection, and it is where writes land.** Open and closed sessions share it: there is a selected session, or
	// none. The highlighted row says where work goes, which is why the `writing to` line this replaced is gone — it
	// stated in words what the highlight already shows.
	//
	// **The toggle filters annotations, never this list.** A reader navigates by the list, and hiding rows from it would
	// only make sessions hard to find. What `current` and `all` govern is which sessions' annotations the page draws.
	import { store } from '$lib/manifest/client.svelte';
	import { grouped, selected, sessionView, summary } from './sessions.svelte';
	import { touched } from './when';
	import DeleteSession from './DeleteSession.svelte';
	import { write } from '$lib/write';
	import type { SessionRow } from '$lib/manifest/types';

	const m = $derived(store.manifest);
	const groups = $derived(grouped(m));
	const here = $derived(selected(m));

	let busy = $state('');
	let renaming = $state('');
	let title = $state('');
	let closedOpen = $state(false);
	let doomed = $state<SessionRow | null>(null);

	async function act(id: string, endpoint: string, body: Record<string, unknown> = {}): Promise<void> {
		busy = id;
		await write(endpoint, { session: id, ...body });
		busy = '';
		store.refresh();
	}

	async function rename(id: string): Promise<void> {
		const want = title.trim();
		renaming = '';
		if (want) await act(id, 'session-rename', { title: want });
	}

	async function shut(id: string): Promise<void> {
		await act(id, 'session-close');
		sessionView.dropped(id);
	}

	async function remove(id: string): Promise<void> {
		doomed = null;
		await act(id, 'session-delete');
		sessionView.dropped(id);
	}

	function view(v: 'current' | 'all'): void {
		sessionView.view = v;
		sessionView.save();
	}

	function closedShown(yes: boolean): void {
		sessionView.showClosed = yes;
		sessionView.save();
	}
</script>

<div class="sessions" data-testid="session-picker">
	<p class="showing">
		<span>showing</span>
		<span class="choice" role="group" aria-label="which annotations the page shows">
			<button
				type="button"
				class:on={sessionView.view === 'current'}
				disabled={!here}
				title={here ? 'Show only the selected session’s annotations' : 'Nothing is selected yet'}
				data-testid="show-current"
				onclick={() => view('current')}>current</button
			><button type="button" class:on={sessionView.view === 'all'} data-testid="show-all" onclick={() => view('all')}>all</button>
		</span>
		<span>{sessionView.view === 'all' ? 'sessions' : 'session'}</span>
	</p>

	{#snippet row(s: SessionRow)}
		{@const it = summary(m, s.id)}
		{@const mine = sessionView.selected === s.id}
		{@const shutAlready = s.state !== 'open'}
		<li class:selected={mine} class:shut={shutAlready}>
			{#if renaming === s.id}
				<input
					class="rename"
					bind:value={title}
					aria-label="Rename {s.title}"
					data-testid="session-rename-{s.id}"
					onkeydown={(e) => (e.key === 'Enter' ? rename(s.id) : e.key === 'Escape' ? (renaming = '') : undefined)}
					onblur={() => rename(s.id)}
				/>
			{:else}
				<!-- The pencil edits the name, so it stands beside the name rather than among the verbs that act on the session. -->
				<span class="namebar">
					<button type="button" class="pick" aria-pressed={mine} data-testid="session-{s.id}" onclick={() => sessionView.pick(s.id, m)}>
						<span class="dot" aria-hidden="true">{mine ? '●' : '○'}</span>
						<span class="title">{s.title}</span>
					</button>
					<button
						type="button"
						class="edit"
						title="Rename"
						aria-label="Rename {s.title}"
						disabled={busy === s.id}
						data-testid="session-edit-{s.id}"
						onclick={() => {
							renaming = s.id;
							title = s.title;
						}}>✎</button
					>
				</span>
				<span class="verbs">
					<span class="count">{it.open} open</span>
					{#if shutAlready}
						<button
							type="button"
							title="reopen session"
							aria-label="Reopen {s.title}"
							disabled={busy === s.id}
							data-testid="session-reopen-{s.id}"
							onclick={() => act(s.id, 'session-reopen')}>⟳</button
						>
					{:else}
						<button
							type="button"
							title="Close this session"
							aria-label="Close {s.title}"
							disabled={busy === s.id}
							data-testid="session-close-{s.id}"
							onclick={() => shut(s.id)}>⏹</button
						>
					{/if}
					<button
						type="button"
						title="Remove from view"
						aria-label="Remove {s.title}"
						disabled={busy === s.id}
						data-testid="session-delete-{s.id}"
						onclick={() => (doomed = s)}>✕</button
					>
				</span>
				{#if s.purpose}<p class="purpose">{s.purpose}</p>{/if}
				{@const said = touched(s.opened, s.state)}
				{#if it.who.length || said || it.fresh || s.attached?.length}
					<p class="who">
						{[it.who.join(', '), said].filter(Boolean).join(' — ')}{#each s.attached ?? [] as a (a.who)}<span class="here" data-testid="attached-{a.who}"
								>{a.who} ⟨{a.kind}⟩ attached</span
							>{/each}{#if it.fresh}<span class="fresh">{it.fresh} new</span>{/if}
					</p>
				{/if}
			{/if}
		</li>
	{/snippet}

	<ul class="rows" data-testid="session-list">
		{#each groups.open as s (s.id)}{@render row(s)}{:else}
			<li class="none">no open sessions</li>
		{/each}
	</ul>

	{#if groups.closed.length}
		<p class="band">
			<button type="button" class="fold" aria-expanded={closedOpen} data-testid="show-closed" onclick={() => (closedOpen = !closedOpen)}>
				<span class="chev" class:down={closedOpen} aria-hidden="true"></span> Closed ({groups.closed.length})
			</button>
		</p>
		{#if closedOpen}
			<p class="setting">
				<span>display closed sessions</span>
				<span class="choice" role="group" aria-label="display closed sessions">
					<button type="button" class:on={!sessionView.showClosed} data-testid="closed-no" onclick={() => closedShown(false)}>no</button
					><button type="button" class:on={sessionView.showClosed} data-testid="closed-yes" onclick={() => closedShown(true)}>yes</button>
				</span>
			</p>
			<ul class="rows" data-testid="closed-list">
				{#each groups.closed as s (s.id)}{@render row(s)}{/each}
			</ul>
		{/if}
	{/if}

	<p class="foot">
		<span class="fresh">N new</span> counts events by anyone but you since you last opened the session. Writes land in the <strong>selected</strong> session whatever is shown.
	</p>
</div>

{#if doomed}
	<DeleteSession title={doomed.title} open={summary(m, doomed.id).open} onCancel={() => (doomed = null)} onDelete={() => remove(doomed!.id)} />
{/if}

<style>
	/* The panel's own size. The section was set in rem while the lists above it are 11px, so Sessions read a size
	   larger than Documents and Nodes and pulled the eye to the least important part of the panel. */
	.sessions {
		font-size: 11px;
	}
	.showing {
		display: flex;
		align-items: baseline;
		gap: 6px;
		flex-wrap: wrap;
		margin: 0 0 var(--gap-tight);
		color: var(--ink-faint);
		font-size: 0.92em;
	}
	.choice {
		display: inline-flex;
	}
	.choice button {
		font: inherit;
		font-size: 0.98em;
		color: var(--ink-soft);
		background: none;
		border: 1px solid var(--rule);
		padding: 0 6px;
		cursor: pointer;
	}
	.choice button:first-child {
		border-radius: var(--rad-pill) 0 0 var(--rad-pill);
	}
	.choice button:last-child {
		border-radius: 0 var(--rad-pill) var(--rad-pill) 0;
		border-left: 0;
	}
	.choice button.on {
		background: var(--annotation-tint, rgb(217 119 87 / 0.18));
		color: var(--ink);
		font-weight: 500;
	}
	.choice button:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}
	ul.rows {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: baseline;
		gap: 1px var(--gap-hair);
		padding: 2px 4px;
		border-radius: var(--rad-pill);
		border-left: 2px solid transparent;
	}
	li.selected {
		background: var(--annotation-tint, rgb(217 119 87 / 0.12));
		border-left-color: var(--annotation, #c05621);
	}
	li.shut .title {
		color: var(--ink-faint);
	}
	li.none {
		color: var(--ink-faint);
		display: block;
	}
	.namebar {
		display: flex;
		align-items: baseline;
		gap: 3px;
		min-width: 0;
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
	.dot {
		color: var(--ink-faint);
		font-size: 0.8em;
		flex: none;
	}
	li.selected .dot {
		color: var(--annotation, #c05621);
	}
	.title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	li.selected .title {
		font-weight: 600;
	}
	.edit {
		font: inherit;
		font-size: 0.85em;
		color: var(--ink-faint);
		background: none;
		border: 0;
		padding: 0 1px;
		cursor: pointer;
		flex: none;
	}
	.edit:hover {
		color: var(--ink);
	}
	.verbs {
		display: flex;
		align-items: baseline;
		gap: 1px;
	}
	.count {
		color: var(--ink-faint);
		font-size: 0.9em;
		white-space: nowrap;
		margin-right: 3px;
		font-variant-numeric: tabular-nums;
	}
	.verbs button {
		font: inherit;
		font-size: 0.9em;
		color: var(--ink-faint);
		background: none;
		border: 0;
		padding: 0 2px;
		cursor: pointer;
		text-decoration: none;
	}
	.verbs button:hover {
		color: var(--ink);
	}
	.purpose,
	.who {
		grid-column: 1 / -1;
		margin: 0 0 1px 16px;
		font-size: 0.86em;
	}
	.purpose {
		color: var(--ink-soft);
	}
	.who {
		color: var(--ink-faint);
	}
	.fresh {
		margin-left: 6px;
		background: var(--annotation-tint, rgb(217 119 87 / 0.18));
		color: var(--annotation, #c05621);
		border-radius: var(--rad-pill);
		padding: 0 5px;
		font-weight: 500;
	}
	.here {
		margin-left: 6px;
		color: var(--link);
	}
	.band {
		margin: var(--gap-tight) 0 2px;
	}
	.fold {
		display: flex;
		align-items: center;
		gap: var(--gap-hair);
		width: 100%;
		font: inherit;
		font-size: 0.72em;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-faint);
		background: none;
		border: 0;
		padding: 0;
		cursor: pointer;
	}
	.fold:hover {
		color: var(--ink-soft);
	}
	.chev {
		width: 5px;
		height: 5px;
		border-right: 1.5px solid currentColor;
		border-bottom: 1.5px solid currentColor;
		transform: rotate(-45deg);
		margin-bottom: 1px;
		flex: none;
	}
	.chev.down {
		transform: rotate(45deg);
		margin-bottom: 3px;
	}
	.setting {
		display: flex;
		align-items: baseline;
		gap: 6px;
		flex-wrap: wrap;
		margin: var(--gap-hair) 0 var(--gap-hair) 4px;
		color: var(--ink-faint);
		font-size: 0.86em;
	}
	.foot {
		margin: var(--gap-tight) 0 0;
		padding-top: var(--gap-hair);
		border-top: 1px solid var(--rule);
		color: var(--ink-faint);
		font-size: 0.82em;
		line-height: 1.45;
	}
	.foot .fresh {
		margin: 0 2px 0 0;
	}
	.foot strong {
		color: var(--ink-soft);
	}
	.rename {
		font: inherit;
		width: 100%;
		grid-column: 1 / -1;
	}
</style>
