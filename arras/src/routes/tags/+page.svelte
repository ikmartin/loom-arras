<script lang="ts">
	import { store } from '$lib/manifest/client.svelte';
	import { tagUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const tags = $derived(Object.entries(m.tags).sort());
</script>

<main class="page">
	<h1>Tags</h1>
	<ul>{#each tags as [t, keys] (t)}<li><a href={tagUrl(t)}>{t}</a> <span class="muted">{keys.length}</span></li>{:else}<li class="muted">No tags.</li>{/each}</ul>
</main>
