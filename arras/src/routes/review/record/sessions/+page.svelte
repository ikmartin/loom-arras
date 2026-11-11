<script lang="ts">
	// Review › The Record › Sessions: every session, open and closed, with when it was last active, each opening its transcript; annotations belong to no session, so none is counted here. A new session is started here as in the picker, and Write here chooses an open one as where the person's writes go, which reading a transcript never does; renaming, closing, reopening and deleting are the picker's verbs (`sessions/actions.ts`).
	import { onMount } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { threadUrl } from '$lib/nav';
	import { can } from '$lib/write';
	import ActionBar from '$lib/review/ActionBar.svelte';
	import Empty from '$lib/review/Empty.svelte';
	import DeleteSession from '$lib/sessions/DeleteSession.svelte';
	import { closeSession, deleteSession, renameSession, reopenSession } from '$lib/sessions/actions';
	import { openSession } from '$lib/sessions/new';
	import { grouped, sessionView, titleOf } from '$lib/sessions/sessions.svelte';
	import { when } from '$lib/sessions/when';
	import type { SessionRow } from '$lib/manifest/types';

	const m = $derived(store.manifest!);
	const rows = $derived([...grouped(m).open, ...grouped(m).closed]);
	let writable = $state(false);
	let starts = $state(false);
	onMount(() => {
		void can('session-close').then((ok) => (writable = ok));
		void can('session-new').then((ok) => (starts = ok));
	});
	let busy = $state('');
	let renaming = $state('');
	let title = $state('');
	let doomed = $state<SessionRow | null>(null);
	let naming = $state(false);
	let fresh = $state('');
	let said = $state<{ text: string; refused: boolean } | null>(null);

	async function act(id: string, verb: () => Promise<boolean>): Promise<void> {
		busy = id;
		await verb();
		busy = '';
	}
	async function rename(s: SessionRow): Promise<void> {
		const want = title.trim();
		renaming = '';
		if (want && want !== titleOf(s)) await act(s.id, () => renameSession(s, want));
	}
	async function start(): Promise<void> {
		const want = fresh.trim();
		if (!want || busy) return;
		busy = '*';
		said = null;
		const { id, error } = await openSession(want);
		busy = '';
		said = id ? { text: `Started “${want}”; your writes go there.`, refused: false } : { text: error, refused: true };
		if (id) (naming = false), (fresh = '');
	}
	function writeHere(s: SessionRow): void {
		sessionView.select(s.id);
		said = { text: `Your writes go to “${titleOf(s)}”.`, refused: false };
	}
</script>

	<ActionBar said={said?.text ?? ''} refused={said?.refused} testid="sessions-bar">
		{#snippet lead()}
			<span data-testid="sessions-writing">{sessionView.selected && rows.some((s) => s.id === sessionView.selected) ? `Writing in “${titleOf(rows.find((s) => s.id === sessionView.selected)!)}”` : 'Not writing in a session'}</span>
		{/snippet}
		{#snippet actions()}
			{#if starts}
				{#if naming}
					<!-- svelte-ignore a11y_autofocus -->
					<input class="name" bind:value={fresh} placeholder="What this sitting is for" aria-label="The new session's title" autofocus data-testid="sessions-new-title" onkeydown={(e) => (e.key === 'Enter' ? void start() : e.key === 'Escape' ? (naming = false) : undefined)} />
					<button type="button" class="btn primary" disabled={!fresh.trim() || busy === '*'} data-testid="sessions-new-go" onclick={() => void start()}>{busy === '*' ? 'Starting…' : 'Start'}</button>
					<button type="button" class="btn quiet" onclick={() => (naming = false)}>Cancel</button>
				{:else}
					<button type="button" class="btn" data-testid="sessions-new" onclick={() => ((naming = true), (said = null))}>New session</button>
				{/if}
			{/if}
		{/snippet}
	</ActionBar>
	{#if !rows.length}
		<Empty text="No sessions yet. An agent opens its own; you start one here or from the session footer." testid="sessions-none" />
	{:else}
		<table class="list" data-testid="sessions-table">
			<thead><tr><th>Session</th><th>State</th><th title="The newest command, note or message in it">Last active</th><th></th></tr></thead>
			<tbody>
				{#each rows as s (s.id)}
					{@const here = sessionView.selected === s.id}
					<tr data-testid="session-row-{s.id}" class:here>
						<td>
							{#if renaming === s.id}
								<!-- svelte-ignore a11y_autofocus -->
								<input bind:value={title} aria-label="Rename {titleOf(s)}" autofocus onkeydown={(e) => (e.key === 'Enter' ? rename(s) : e.key === 'Escape' ? (renaming = '') : undefined)} onblur={() => rename(s)} />
							{:else}
								<a href={threadUrl(s.id)}>{titleOf(s)}</a>{#if s.purpose}<div class="muted">{s.purpose}</div>{/if}
							{/if}
						</td>
						<td>{s.state}</td>
						<td data-testid="session-last-{s.id}" title={s.last || s.opened || s.created}>{when(s.last || s.opened || s.created)}</td>
						<td class="verbs">
							{#if here}
								<span class="writing" data-testid="sessions-writing-here">writing here</span>
							{:else if s.state === 'open'}
								<button type="button" class="btn small" data-testid="sessions-write-here-{s.id}" onclick={() => writeHere(s)}>Write here</button>
							{/if}
							{#if writable}
								<button type="button" class="btn small quiet" disabled={busy === s.id} onclick={() => ((renaming = s.id), (title = titleOf(s)))} data-testid="sessions-rename-{s.id}">rename</button>
								{#if s.state === 'open'}
									<button type="button" class="btn small quiet" disabled={busy === s.id} onclick={() => act(s.id, () => closeSession(s.id))} data-testid="sessions-close-{s.id}">close</button>
								{:else}
									<button type="button" class="btn small quiet" disabled={busy === s.id} onclick={() => act(s.id, () => reopenSession(s.id))} data-testid="sessions-reopen-{s.id}">reopen</button>
								{/if}
								<button type="button" class="btn small quiet" disabled={busy === s.id} onclick={() => (doomed = s)} data-testid="sessions-delete-{s.id}">delete</button>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}

{#if doomed}
	<DeleteSession
		title={titleOf(doomed)}
		onCancel={() => (doomed = null)}
		onDelete={() => {
			const id = doomed!.id;
			doomed = null;
			void act(id, () => deleteSession(id));
		}}
	/>
{/if}

<style>
	.verbs {
		white-space: nowrap;
		text-align: right;
	}
	.writing {
		font-size: 12px;
		color: var(--review-accent);
		margin-right: 6px;
	}
	tr.here td:first-child a {
		font-weight: 500;
	}
	.name {
		font: inherit;
		padding: 3px 8px;
		min-width: 14em;
	}
</style>
