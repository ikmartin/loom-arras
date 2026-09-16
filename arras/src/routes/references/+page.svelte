<script lang="ts">
	import { store } from '$lib/manifest/client.svelte';
	import { digestUrl, nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const refs = $derived(Object.values(m.references).sort((a, b) => a.citekey.localeCompare(b.citekey)));
</script>

<main class="page">
	<h1>References</h1>
	<table class="list">
		<thead><tr><th>citekey</th><th>title</th><th>digest</th><th>cited by</th></tr></thead>
		<tbody>
			{#each refs as r (r.citekey)}
				<tr>
					<td><a href={digestUrl(r.citekey)}>{r.citekey}</a></td>
					<td>{r.bib.title ?? ''}</td>
					<td>{#if r.digest}{r.digest.nodes.length} results ({r.digest.method}){#if r.version_mismatch} <span class="problem">version mismatch</span>{/if}{:else}<span class="muted">none</span>{/if}</td>
					<td>{#each r.cited_by as c, i (c)}{#if i}, {/if}<a href={nodeUrl(c)}>{c}</a>{/each}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</main>
