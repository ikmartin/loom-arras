<script lang="ts">
	import { onMount } from 'svelte';
	import { loadManifest, type LoadResult } from '$lib/manifest/loader';

	let result = $state<LoadResult | null>(null);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			const r = await loadManifest();
			result = r === 'unchanged' ? null : r;
		} catch (err) {
			error = (err as Error).message;
		}
	});
</script>

<main>
	{#if error}
		<p class="problem">Could not load the manifest: {error}</p>
	{:else if result === null}
		<p>Loading manifest…</p>
	{:else if result.manifest === null}
		<h1>Problems</h1>
		<ul class="diagnostics">
			<li><code>{result.diagnostic.code}</code> {result.diagnostic.message}</li>
		</ul>
	{:else}
		{@const m = result.manifest}
		<h1>{m.corpus.root_label}</h1>
		<p class="meta">
			corpus <code>{m.corpus.name}</code> · published by {m.publisher.name} {m.publisher.version} · interface version {m.interface_version} · manifest {result.hash.slice(0, 19)}
		</p>
		<dl class="counts">
			<dt>masters</dt>
			<dd>{m.masters.length}</dd>
			<dt>nodes</dt>
			<dd>{Object.keys(m.nodes).length}</dd>
			<dt>keys</dt>
			<dd>{Object.keys(m.keys).length}</dd>
			<dt>edges</dt>
			<dd>{m.edges.length}</dd>
			<dt>diagnostics</dt>
			<dd>{m.diagnostics.length}</dd>
		</dl>
		{#if m.masters.length}
			<h2>Masters</h2>
			<ul>
				{#each m.masters as master (master.path)}
					<li>{master.title} <code>{master.path}</code>{master.default ? ' (default)' : ''}</li>
				{/each}
			</ul>
		{/if}
		<h2>Nodes</h2>
		<ul>
			{#each Object.values(m.nodes) as node (node.id)}
				<li><span class="taxon">{node.taxon}</span> <code>{node.id}</code> {node.title ?? ''}</li>
			{/each}
		</ul>
	{/if}
</main>

<style>
	main {
		max-width: 48rem;
		margin: 2rem auto;
		padding: 0 1rem;
		font-family: system-ui, sans-serif;
		line-height: 1.5;
	}
	.meta {
		color: #555;
	}
	.counts {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.25rem 1rem;
	}
	.counts dt {
		font-weight: 600;
	}
	.counts dd {
		margin: 0;
	}
	.taxon {
		color: #2b4a6f;
		font-weight: 600;
	}
	.problem,
	.diagnostics {
		color: #8a1c1c;
	}
</style>
