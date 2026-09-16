<script lang="ts">
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import { nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const tag = $derived(decodeURIComponent(page.params.tag ?? ''));
	const keys = $derived(m.tags[tag] ?? []);
</script>

<main class="page">
	<h1>#{tag}</h1>
	<ul>{#each keys as k (k)}<li><a href={nodeUrl(k)}>{k}</a> {m.nodes[k]?.taxon ?? ''} {m.nodes[k]?.title ?? ''}</li>{:else}<li class="muted">No nodes carry this tag.</li>{/each}</ul>
</main>
