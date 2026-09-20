<script lang="ts">
	import { store } from '$lib/manifest/client.svelte';
	import { shortDate } from '$lib/badges';
	import { threadUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const threads = $derived(Object.values(m.threads).sort((a, b) => b.created.localeCompare(a.created)));
</script>

<main class="page">
	<h1>Threads</h1>
	{#if !threads.length}<p class="muted">No threads yet.</p>{/if}
	<ul>
		{#each threads as t (t.id)}
			<li><a href={threadUrl(t.id)}>{t.title}</a> <span class="muted">{t.kind} · {shortDate(t.created)} · {t.messages.length} messages{t.discarded ? ' · discarded' : ''}</span></li>
		{/each}
	</ul>
</main>
