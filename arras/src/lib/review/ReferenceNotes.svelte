<script lang="ts">
	// Works an agent proposed citing, and what became of the suggestion (plan 0.11 Part H).
	//
	// Two lists in one place, because they are two halves of one errand: the citation suggestions still open on this key, each answerable here, and the works already accepted for it. An accepted note is a breadcrumb and never a second source of identity truth -- `verified` stays false until a person puts the identifier in the bibliography, and nothing here enters a closure.
	import { store } from '$lib/manifest/client.svelte';
	import { can, write } from '$lib/write';
	import type { Annotation } from '$lib/manifest/types';

	let { forKey }: { forKey: string } = $props();

	const m = $derived(store.manifest!);
	const notes = $derived((m.reference_notes ?? []).filter((n) => n.for?.includes(forKey)));
	const open = $derived(
		Object.values(m.annotations).filter(
			(a) => a.kind === 'citation' && a.status === 'open' && !a.discarded && !a.in_reply_to && a.target.key === forKey
		)
	);

	let allowed = $state(false);
	let busy = $state('');
	let said = $state('');

	$effect(() => {
		can('refs-note').then((ok) => (allowed = ok));
	});

	async function decide(a: Annotation, decision: 'accept' | 'reject') {
		busy = a.id;
		const res = await write('refs-note', { annotation: a.id, decision });
		busy = '';
		said = res.ok ? `${decision}ed` : (res.error?.message ?? 'refused');
	}
</script>

{#if notes.length || open.length}
	<section class="refnotes" data-testid="reference-notes">
		{#if open.length}
			<p class="head">Suggested citations</p>
			<ul class="plain">
				{#each open as a (a.id)}
					<li>
						<div class="body">{@html a.body_html}</div>
						{#if allowed}
							<p class="actions">
								<button disabled={busy === a.id} onclick={() => decide(a, 'accept')} data-testid="refnote-accept">accept</button>
								<button disabled={busy === a.id} onclick={() => decide(a, 'reject')} data-testid="refnote-reject">reject</button>
							</p>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
		{#if notes.length}
			<p class="head">Accepted, not yet in the bibliography</p>
			<ul class="plain">
				{#each notes as n, i (i)}
					<li>
						<span class="work">{n.work}</span>
						<span class="who">{n.accepted?.who ?? ''}</span>
						{#if !n.identifier?.verified}<span class="unverified">identifier unconfirmed</span>{/if}
					</li>
				{/each}
			</ul>
		{/if}
		{#if said}<p class="said" role="status">{said}</p>{/if}
	</section>
{/if}

<style>
	.refnotes {
		font-size: 0.85em;
	}
	.head {
		font-family: var(--sans);
		font-size: 0.8em;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-faint);
		margin: var(--gap) 0 var(--gap-tight);
	}
	li + li {
		margin-top: var(--gap-tight);
	}
	.actions {
		margin: 0.2em 0 0;
		display: flex;
		gap: 0.4em;
	}
	.actions button {
		background: none;
		border: 1px solid var(--rule);
		border-radius: 2px;
		padding: 0 0.5em;
		font-family: var(--sans);
		font-size: 0.9em;
		color: var(--ink-soft);
		cursor: pointer;
	}
	.who,
	.unverified {
		color: var(--ink-faint);
		font-size: 0.9em;
	}
	.unverified {
		color: var(--state-stale, var(--ink-faint));
	}
	.said {
		color: var(--ink-faint);
	}
</style>
