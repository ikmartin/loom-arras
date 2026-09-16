<script lang="ts">
	import { store } from '$lib/manifest/client.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import { reviewFacts, shortDate, stateBadge } from '$lib/badges';
	import { nodeUrl, threadUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	let filter = $state('all');
	let master = $state('');
	let author = $state('');
	let tag = $state('');

	const keys = $derived(Object.values(m.keys));
	const counts = $derived({
		accepted: keys.filter((k) => k.state === 'accepted').length,
		stale: keys.filter((k) => k.acceptance && k.acceptance.fresh === false).length,
		draft: keys.filter((k) => k.state === 'draft').length,
		incomplete: keys.filter((k) => k.state === 'incomplete').length,
		proved: Object.values(m.nodes).filter((n) => n.derived?.proved).length,
		settled: Object.values(m.nodes).filter((n) => n.derived?.settled).length
	});
	const undigested = $derived(Object.values(m.references).filter((r) => !r.digest && r.cited_by.length).map((r) => r.citekey));
	const rows = $derived(
		keys.filter((k) => {
			const n = m.nodes[k.node];
			if (filter === 'stale' && !(k.acceptance && k.acceptance.fresh === false)) return false;
			if (filter === 'draft' && k.state !== 'draft') return false;
			if (filter === 'incomplete' && k.state !== 'incomplete') return false;
			if (filter === 'loose' && n?.reached_by.length) return false;
			if (filter === 'retired' && !k.previous_key_match) return false;
			if (master && !n?.reached_by.includes(master)) return false;
			if (author && !(n?.author ?? []).includes(author) && k.acceptance?.author !== author) return false;
			if (tag && !n?.tags.includes(tag)) return false;
			return true;
		})
	);
	const authors = $derived([...new Set([...Object.values(m.nodes).flatMap((n) => n.author ?? []), ...keys.map((k) => k.acceptance?.author).filter(Boolean)])].sort() as string[]);
	const records = $derived([...new Set(Object.values(m.annotations).map((a) => a.record))].sort());
	const threads = $derived(Object.values(m.threads));
</script>

<main class="page">
	<h1>Review</h1>
	<p data-testid="review-counts">{counts.accepted} accepted · {counts.stale} stale · {counts.draft} draft · {counts.incomplete} incomplete · {counts.proved} proved · {counts.settled} settled</p>
	<p class="controls">
		<label>show <select bind:value={filter}><option value="all">all</option><option value="stale">stale</option><option value="draft">draft</option><option value="incomplete">incomplete</option><option value="loose">loose</option><option value="retired">previous-key matches</option></select></label>
		<label>master <select bind:value={master}><option value="">any</option>{#each m.masters as x (x.path)}<option value={x.path}>{x.path}</option>{/each}</select></label>
		<label>author <select bind:value={author}><option value="">any</option>{#each authors as a (a)}<option value={a}>{a}</option>{/each}</select></label>
		<label>tag <select bind:value={tag}><option value="">any</option>{#each Object.keys(m.tags).sort() as t (t)}<option value={t}>{t}</option>{/each}</select></label>
	</p>
	<table class="list">
		<thead><tr><th>key</th><th>state</th><th>since</th><th>cause</th><th>review</th><th>incomplete</th><th>reached by</th></tr></thead>
		<tbody>
			{#each rows as k (k.key)}
				<tr>
					<td><a href={nodeUrl(k.key)}>{k.key}</a></td>
					<td><Badge parts={stateBadge(m, k)} /></td>
					<td class="muted">{k.acceptance ? shortDate(k.acceptance.date) : ''}</td>
					<td>
						{#each k.acceptance?.causes ?? [] as c, i (i)}
							<div>{c.kind}{c.id ? ' ' + c.id : ''}{c.when ? ` (${shortDate(c.when)})` : ''}{#if c.diff} · <a href={'/build/' + c.diff}>diff</a>{/if}</div>
						{/each}
						{#if k.previous_key_match}<div class="muted">acceptance recorded under {k.previous_key_match}; re-accept to confirm</div>{/if}
					</td>
					<td class="muted">{reviewFacts(k)}</td>
					<td>{#each k.incomplete as t, i (i)}<div>{t}</div>{/each}</td>
					<td class="muted">{m.nodes[k.node]?.reached_by.join(', ') || 'loose'}</td>
				</tr>
			{/each}
		</tbody>
	</table>
	{#if undigested.length}
		<h2>Undigested citations</h2>
		<p>{undigested.join(', ')}</p>
	{/if}
	<h2>Runs and comment sessions</h2>
	{#if threads.length || records.length}
		<ul>
			{#each threads as t (t.id)}<li><a href={threadUrl(t.id)}>{t.title}</a> <span class="muted">{t.kind}{t.discarded ? ' · discarded' : ''}</span></li>{/each}
			{#each records as r (r)}<li><code>{r}</code></li>{/each}
		</ul>
	{:else}
		<p class="muted">None yet.</p>
	{/if}
</main>

<style>
	.controls label {
		margin-right: 1rem;
	}
</style>
