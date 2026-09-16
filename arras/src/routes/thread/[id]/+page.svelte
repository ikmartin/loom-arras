<script lang="ts">
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import { nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const id = $derived(decodeURIComponent(page.params.id ?? ''));
	const t = $derived(m.threads[id]);
</script>

<main class="page">
	{#if !t}
		<h1>Unknown thread</h1>
	{:else}
		<h1>{t.title}</h1>
		<p class="muted">{t.kind} · {t.created} · participants {t.participants.map((p) => p.id).join(', ')}{t.discarded ? ' · discarded' : ''}</p>
		<p>targets: {#each t.targets as k, i (k)}{#if i}, {/if}<a href={nodeUrl(k)}>{k}</a>{/each}</p>
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
</main>

<style>
	.message {
		border-left: 3px solid var(--rule);
		padding-left: 0.75rem;
		margin: 1rem 0;
	}
</style>
