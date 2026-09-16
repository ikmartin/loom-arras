<script lang="ts">
	import { store } from '$lib/manifest/client.svelte';
	import { downstream } from '$lib/graph/layout';
	import { nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const incomplete = $derived(Object.values(m.keys).filter((k) => k.incomplete.length));
	const byMaster = $derived.by(() => {
		const out = new Map<string, typeof incomplete>();
		for (const k of incomplete) {
			const reached = m.nodes[k.node]?.reached_by ?? [];
			for (const mp of reached.length ? reached : ['loose']) {
				if (!out.has(mp)) out.set(mp, []);
				out.get(mp)!.push(k);
			}
		}
		return out;
	});
	const blocked = $derived.by(() => {
		const set = new Set<string>();
		for (const k of incomplete) for (const d of downstream(m, k.node)) set.add(d);
		return [...set].sort();
	});
</script>

<main class="page">
	<h1>Blockers</h1>
	{#if !incomplete.length}
		<p class="muted">Nothing is marked incomplete.</p>
	{/if}
	{#each [...byMaster.entries()] as [mp, ks] (mp)}
		<h2>{mp}</h2>
		<ul>
			{#each ks as k (k.key)}
				<li><a href={nodeUrl(k.key)}>{k.key}</a>{#each k.incomplete as t, i (i)}<div class="muted">{t}</div>{/each}</li>
			{/each}
		</ul>
	{/each}
	{#if blocked.length}
		<h2>Results that depend on something incomplete</h2>
		<p>{#each blocked as b, i (b)}{#if i}, {/if}<a href={nodeUrl(b)}>{b}</a>{/each}</p>
	{/if}
</main>
