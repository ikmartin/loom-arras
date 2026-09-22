<script lang="ts">
	// A session's permalink (plan 0.13 §5, §7): one piece of work read back whole, rather than through the panel's picker.
	//
	// The panel answers "which session am I in"; this answers "what happened in that one" — every annotation filed in
	// it, in the order it was filed, each a link to the thing it is about. It opens split, because the discussion is
	// what a session is; the content pane is the record and the pane beside it is where the next message goes.
	//
	// A deleted session is a tombstone the publisher does not send, so an unknown id is reported rather than invented.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import { keyUrl } from '$lib/nav';
	import { summary } from '$lib/sessions/sessions.svelte';
	import Beside from '$lib/split/Beside.svelte';
	import Prose from '$lib/math/Prose.svelte';

	const m = $derived(store.manifest!);
	const id = $derived(decodeURIComponent(page.params.id ?? ''));
	const s = $derived((m.sessions ?? []).find((x) => x.id === id));
	const facts = $derived(summary(m, id));
	// What was filed here, oldest first: a session is read forwards, the way it happened.
	const filed = $derived(
		Object.values(m.annotations ?? {})
			.filter((a) => a.run === id && !a.discarded)
			.sort((a, b) => a.created.localeCompare(b.created))
	);
	const when = (iso: string) => iso.slice(0, 16).replace('T', ' ');
</script>

<main class="page">
	{#if !s}
		<h1>Unknown session</h1>
		<p class="muted">This corpus has no session <code>{id}</code>. A deleted one leaves a tombstone the publisher does not send.</p>
	{:else}
		<h1>{s.title}</h1>
		<p class="muted" data-testid="session-facts">
			<code>{s.id}</code> · {s.state}{s.active ? ' · loom is writing here' : ''} · round {s.rounds} · opened {when(s.created)}
			{#if facts.who.length}· {facts.who.join(', ')}{/if}
			{#if s.attached?.length}<span data-testid="session-attached">· {s.attached.map((a) => `${a.who} ⟨${a.kind}⟩`).join(', ')} attached</span>{/if}
		</p>
		<Beside session={s.id} label="what was filed" open>
			<ol class="plain filed" data-testid="session-filed">
				{#each filed as a (a.id)}
					<li data-testid="filed-{a.id}">
						<p class="line">
							<span class="kind">{a.kind}</span>
							<span class="who">{a.author.label ?? a.author.id}</span>
							<span class="at">{when(a.created)}</span>
							{#if a.severity}<span class="sev">{a.severity}</span>{/if}
							{#if a.status === 'resolved'}<span class="done">resolved</span>{/if}
							<a href={keyUrl(m, a.target.key)}>{a.target.key}</a>
						</p>
						{#if a.quote}<p class="quote">“{a.quote}”</p>{/if}
						<Prose html={a.body_html} />
					</li>
				{:else}
					<li class="muted">Nothing has been filed in this session yet.</li>
				{/each}
			</ol>
		</Beside>
	{/if}
</main>

<style>
	.filed {
		margin: 0;
	}
	.filed li + li {
		margin-top: var(--gap);
		padding-top: var(--gap-tight);
		border-top: 1px solid var(--rule-faint);
	}
	.line {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--gap-tight);
		margin: 0;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
	}
	.kind {
		color: var(--ink);
	}
	.at,
	.who,
	.quote {
		color: var(--ink-faint);
	}
	.quote {
		margin: var(--gap-hair) 0 0;
		font-size: 12px;
	}
</style>
