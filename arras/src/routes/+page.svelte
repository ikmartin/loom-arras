<script lang="ts">
	import { store } from '$lib/manifest/client.svelte';
	import { masterUrl, nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const keys = $derived(Object.values(m.keys));
	const count = (state: string) => keys.filter((k) => k.state === state).length;
	const stale = $derived(keys.filter((k) => k.acceptance && k.acceptance.fresh === false).length);
	const nodes = $derived(Object.values(m.nodes).filter((n) => n.kind !== 'section'));
</script>

<main class="page">
	<h1>{m.corpus.root_label}</h1>
	<p class="muted">
		corpus <code>{m.corpus.name}</code> · published by {m.publisher.name} {m.publisher.version} · interface {m.interface_version} · manifest <code>{store.hash.slice(7, 19)}</code>
	</p>

	<h2>Masters</h2>
	<ul>
		{#each m.masters as master (master.path)}
			<li><a href={masterUrl(master.path)}>{master.title}</a> <code>{master.path}</code>{master.default ? ' (default)' : ''}{master.numbering_known ? '' : ' · not yet compiled'}</li>
		{/each}
	</ul>

	<h2>Review</h2>
	<p>
		<a href="/review">{keys.length} keys</a>: {count('accepted')} accepted{stale ? ` (${stale} stale)` : ''}, {count('draft')} draft, {count('incomplete')} incomplete ·
		<a href="/problems">{m.diagnostics.length} diagnostics</a> ·
		<a href="/graph">{m.edges.length} edges</a>
	</p>

	<h2>Nodes</h2>
	<table class="list">
		<tbody>
			{#each nodes as n (n.id)}
				<tr>
					<td><a href={nodeUrl(n.id)}>{n.id}</a></td>
					<td>{n.taxon}</td>
					<td>{n.title ?? ''}</td>
					<td class="muted">{n.state}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</main>
