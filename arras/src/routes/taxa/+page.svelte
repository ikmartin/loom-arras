<script lang="ts">
	import { store } from '$lib/manifest/client.svelte';
	import { taxonUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const taxa = $derived(Object.entries(m.taxa).sort());
</script>

<main class="page">
	<h1>Taxa</h1>
	<ul>{#each taxa as [name, t] (name)}<li><a href={taxonUrl(t.slug)}>{name}</a> <span class="muted">{t.style} · {t.count}</span></li>{/each}</ul>
</main>
