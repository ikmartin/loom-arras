<script lang="ts">
	import { store } from '$lib/manifest/client.svelte';
	import { nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const loose = $derived(Object.values(m.nodes).filter((n) => !n.reached_by.length && !n.external));
</script>

<main class="page">
	<h1>Not in any document</h1>
	<p class="muted">Nodes that no document includes.</p>
	<ul>{#each loose as n (n.id)}<li><a href={nodeUrl(n.id)}>{n.id}</a> {n.taxon} {n.title ?? ''} <span class="muted">{n.file}</span></li>{:else}<li class="muted">Every node is in a document.</li>{/each}</ul>
</main>
