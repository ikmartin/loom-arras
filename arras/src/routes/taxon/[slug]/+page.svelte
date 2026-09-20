<script lang="ts">
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import { nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const slug = $derived(decodeURIComponent(page.params.slug ?? ''));
	const name = $derived(Object.entries(m.taxa).find(([, t]) => t.slug === slug)?.[0] ?? slug);
	const nodes = $derived(Object.values(m.nodes).filter((n) => n.taxon === name));
</script>

<main class="page">
	<h1>{name}</h1>
	<ul>{#each nodes as n (n.id)}<li><a href={nodeUrl(n.id)}>{n.id}</a> {n.title ?? ''} <span class="muted">{n.state}</span></li>{:else}<li class="muted">No nodes of this taxon.</li>{/each}</ul>
</main>
