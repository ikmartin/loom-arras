<script lang="ts">
	// Review › Sessions: every session, open and closed, with what each holds, each opening its transcript; renaming, closing, reopening and deleting are here as in the picker, and are the same verbs (`sessions/actions.ts`).
	import { onMount } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { threadUrl } from '$lib/nav';
	import { can } from '$lib/write';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';
	import DeleteSession from '$lib/sessions/DeleteSession.svelte';
	import { closeSession, deleteSession, renameSession, reopenSession } from '$lib/sessions/actions';
	import { grouped, summary, titleOf } from '$lib/sessions/sessions.svelte';
	import type { SessionRow } from '$lib/manifest/types';

	const m = $derived(store.manifest!);
	const rows = $derived([...grouped(m).open, ...grouped(m).closed]);
	let writable = $state(false);
	onMount(() => void can('session-close').then((ok) => (writable = ok)));
	let busy = $state('');
	let renaming = $state('');
	let title = $state('');
	let doomed = $state<SessionRow | null>(null);

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
	const when = (iso: string) => iso.slice(0, 10);
</script>

<main class="page">
	<ReviewHeading title="Sessions" />
	{#if !rows.length}
		<p class="muted">No sessions yet. A session is opened from the session footer, and an agent opens its own.</p>
	{:else}
		<table class="list" data-testid="sessions-table">
			<thead><tr><th>Session</th><th>State</th><th>Open</th><th>Who</th><th>Last opened</th>{#if writable}<th></th>{/if}</tr></thead>
			<tbody>
				{#each rows as s (s.id)}
					{@const it = summary(m, s.id)}
					<tr data-testid="session-row-{s.id}">
						<td>
							{#if renaming === s.id}
								<!-- svelte-ignore a11y_autofocus -->
								<input bind:value={title} aria-label="Rename {titleOf(s)}" autofocus onkeydown={(e) => (e.key === 'Enter' ? rename(s) : e.key === 'Escape' ? (renaming = '') : undefined)} onblur={() => rename(s)} />
							{:else}
								<a href={threadUrl(s.id)}>{titleOf(s)}</a>{#if s.purpose}<div class="muted">{s.purpose}</div>{/if}
							{/if}
						</td>
						<td>{s.state}</td>
						<td>{it.open || '—'}</td>
						<td>{it.who.join(', ') || '—'}</td>
						<td>{when(s.opened || s.created)}</td>
						{#if writable}
							<td class="verbs">
								<button type="button" disabled={busy === s.id} onclick={() => ((renaming = s.id), (title = titleOf(s)))} data-testid="sessions-rename-{s.id}">rename</button>
								{#if s.state === 'open'}
									<button type="button" disabled={busy === s.id} onclick={() => act(s.id, () => closeSession(s.id))} data-testid="sessions-close-{s.id}">close</button>
								{:else}
									<button type="button" disabled={busy === s.id} onclick={() => act(s.id, () => reopenSession(s.id))} data-testid="sessions-reopen-{s.id}">reopen</button>
								{/if}
								<button type="button" disabled={busy === s.id} onclick={() => (doomed = s)} data-testid="sessions-delete-{s.id}">delete</button>
							</td>
						{/if}
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</main>

{#if doomed}
	<DeleteSession
		title={titleOf(doomed)}
		open={summary(m, doomed.id).open}
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
	}
	.verbs button {
		font: inherit;
		font-size: 11px;
		color: var(--link);
		background: none;
		border: 0;
		padding: 0 4px;
		cursor: pointer;
	}
	.verbs button:disabled {
		color: var(--ink-faint);
	}
</style>
