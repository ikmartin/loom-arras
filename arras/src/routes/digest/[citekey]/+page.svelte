<script lang="ts">
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import { nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const citekey = $derived(decodeURIComponent(page.params.citekey ?? ''));
	const ref = $derived(m.references[citekey]);
	const citers = $derived((id: string) => [...new Set(m.edges.filter((e) => e.to === id).map((e) => e.from))]); // one entry per citing key, however many edges
</script>

<main class="page">
	{#if !ref}
		<h1>Unknown reference</h1>
	{:else}
		<h1>{ref.bib.title ?? citekey}</h1>
		<p class="muted">
			<code>{citekey}</code>{ref.bib.author ? ` · ${ref.bib.author}` : ''}{ref.bib.year ? ` · ${ref.bib.year}` : ''}
			{#if ref.digest}· digest from {ref.digest.source} ({ref.digest.method}){/if}
			{#if ref.version_mismatch}<span class="problem"> · version mismatch between the digest's source and the bibliography</span>{/if}
		</p>
		{#if ref.digest}
			<Fragment path={ref.digest.fragment} macroSet={citekey} />
			<h2>Results and who cites them</h2>
			<ul>
				{#each ref.digest.nodes as id (id)}
					<li><a href={nodeUrl(id)}>{id}</a> {m.nodes[id]?.locator ? `(${m.nodes[id].locator})` : ''}: {#each citers(id) as c, i (c)}{#if i}, {/if}<a href={nodeUrl(c)}>{c}</a>{:else}<span class="muted">not cited</span>{/each}</li>
				{/each}
			</ul>
		{:else}
			<p>No digest yet. Cited by: {#each ref.cited_by as c, i (c)}{#if i}, {/if}<a href={nodeUrl(c)}>{c}</a>{:else}<span class="muted">nothing</span>{/each}</p>
		{/if}
	{/if}
</main>
