<script lang="ts">
	// A thread, in one of two shapes (plan 0.11 Part C). A session that wrote a report is a document and that report read
	// against each other, which is what reviewing one actually is; a session that only commented has no report and no
	// draft to split against, so it keeps the list it always had. One route, because both are threads and a reader
	// arriving from the index should not have to know which kind they clicked.
	//
	// **The shape follows what the session has, not what kind it calls itself.** The condition was `kind !== 'comments'`
	// until sessions replaced runs and loom began writing `kind: "session"` for every one of them (DR-207), at which
	// point a session with nothing to split rendered as an empty two-pane review. A report is the thing that wants a
	// document beside it, so a report is what the split asks for.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import { keyUrl, nodeUrl } from '$lib/nav';
	import SplitView from '$lib/review/SplitView.svelte';
	import { sessionUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const id = $derived(decodeURIComponent(page.params.id ?? ''));
	const t = $derived(m.threads[id]);
	const split = $derived(!!t && (t.pipeline ?? []).length > 0);
</script>

<main class="page" class:wide={split}>
	{#if !t}
		<h1>Unknown thread</h1>
	{:else}
		<h1>{t.title}</h1>
		<p class="muted">{t.kind} · {t.created} · participants {t.participants.map((p) => p.id).join(', ')}{t.discarded ? ' · discarded' : ''}{#if m.sessions?.some((s) => s.id === id)} · <a href={sessionUrl(id)}>read it as a session</a>{/if}</p>
		{#if split}
			<SplitView thread={t} />
			{#if t.log.length}
				<details><summary>Run log ({t.log.length})</summary><pre>{t.log.map((l) => `${l.time}  ${l.command}`).join('\n')}</pre></details>
			{/if}
		{:else}
			<p>targets: {#each t.targets as k, i (k)}{#if i}, {/if}<a href={keyUrl(m, k)}>{k}</a>{/each}</p>
			<div class="messages">
				{#each t.messages as msg, i (i)}
					<article class="message">
						<p class="muted">{msg.author.id} · {msg.time}</p>
						<div>{@html msg.body_html}</div>
					</article>
				{/each}
			</div>
			{#if t.attachments.length}
				<h2>Attachments</h2>
				<ul>{#each t.attachments as a, i (i)}<li>{a.name} <span class="muted">{a.kind}{a.count != null ? ` · ${a.count}` : ''}</span></li>{/each}</ul>
			{/if}
			{#if t.log.length}
				<details><summary>Run log ({t.log.length})</summary><pre>{t.log.map((l) => `${l.time}  ${l.command}`).join('\n')}</pre></details>
			{/if}
		{/if}
	{/if}
</main>

<style>
	.message {
		border-left: 3px solid var(--rule);
		padding-left: 0.75rem;
		margin: 1rem 0;
	}
	/* The split view wants the window, not the measured column a document is read in. */
	.page.wide {
		max-width: none;
	}
</style>
