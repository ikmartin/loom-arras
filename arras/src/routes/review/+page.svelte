<script lang="ts">
	// The review panel (book 15.3.5): which keys are accepted, which have gone stale, and why. A row expands in place to show the cause and its diff. The filters stand in the shell's left panel.
	import { store } from '$lib/manifest/client.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import HelpDot from '$lib/components/HelpDot.svelte';
	import PagePanel from '$lib/shell/PagePanel.svelte';
	import { reviewFacts, shortDate, stateBadge } from '$lib/badges';
	import { keyUrl, threadUrl } from '$lib/nav';
	import { reachedExternal } from '$lib/reached';

	const m = $derived(store.manifest!);
	let filter = $state('all');
	let master = $state('');
	let author = $state('');
	let tag = $state('');
	let open = $state('');

	// An external node owes no proof and counts as settled as a dependency (7.6.3), so leaving the ones nothing
	// depends on out of the queue removes noise without hiding work. What is left is the handful whose acceptance
	// means something precise: this digest faithfully states what the source says.
	const reached = $derived(reachedExternal(m));
	const keys = $derived(
		Object.values(m.keys).filter((k) => {
			const n = m.nodes[k.node];
			return !n?.external || reached.has(k.node) || filter === 'external';
		})
	);
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
			if (filter === 'external' && !m.nodes[k.node]?.external) return false;
			if (master && !n?.reached_by.includes(master)) return false;
			if (author && !(n?.author ?? []).includes(author) && k.acceptance?.author !== author) return false;
			if (tag && !n?.tags.includes(tag)) return false;
			return true;
		})
	);
	const authors = $derived([...new Set([...Object.values(m.nodes).flatMap((n) => n.author ?? []), ...keys.map((k) => k.acceptance?.author).filter(Boolean)])].sort() as string[]);
	const records = $derived([...new Set(Object.values(m.annotations).map((a) => a.record))].sort());
	const threads = $derived(Object.values(m.threads));
	const causes = (k: string) => m.keys[k]?.acceptance?.causes ?? [];
</script>

<main class="page">
	<h1>Review <HelpDot label="what the review panel shows" topic="review" /></h1>
	<p class="lead">
		Every statement and proof in this corpus, with the state recorded for it and, where an accepted text has since changed, the reason it is no longer current. Nothing here writes: states are recorded from the command line, and this page reads them back.
	</p>
	<p class="counts" data-testid="review-counts">
		{counts.accepted} accepted · {counts.stale} stale · {counts.draft} draft · {counts.incomplete} incomplete · {counts.proved} proved · {counts.settled} settled
	</p>

	<table class="list">
		<thead><tr><th>key</th><th>state</th><th>since</th><th>cause</th><th>review</th><th>incomplete</th><th>reached by</th></tr></thead>
		<tbody>
			{#each rows as k (k.key)}
				<tr>
					<td><a href={keyUrl(m, k.key)}>{k.key}</a></td>
					<td><Badge parts={stateBadge(m, k)} /></td>
					<td class="faint">{k.acceptance ? shortDate(k.acceptance.date) : ''}</td>
					<td>
						{#each causes(k.key) as c, i (i)}
							<div>
								{c.kind}{c.id ? ' ' + c.id : ''}{c.when ? ` (${shortDate(c.when)})` : ''}
								{#if c.diff}
									· <button class="as-link" onclick={() => (open = open === k.key ? '' : k.key)} data-testid="expand-{k.key}">{open === k.key ? 'hide' : 'what changed'}</button>
								{/if}
							</div>
						{/each}
						{#if k.previous_key_match}<div class="faint">acceptance recorded under {k.previous_key_match}; re-accept to confirm</div>{/if}
					</td>
					<td class="faint">{reviewFacts(k)}</td>
					<td>{#each k.incomplete as t, i (i)}<div>{t}</div>{/each}</td>
					<td class="faint">{m.nodes[k.node]?.reached_by.join(', ') || 'loose'}</td>
				</tr>
				{#if open === k.key}
					<tr class="expansion" data-testid="expansion-{k.key}">
						<td colspan="7">
							{#each causes(k.key) as c, i (i)}
								{#if c.diff}
									<p class="cause">{c.kind}{c.id ? ' · ' + c.id : ''} — accepted text on the left, current text on the right</p>
									<DiffView path={c.diff} />
								{/if}
							{/each}
						</td>
					</tr>
				{/if}
			{/each}
		</tbody>
	</table>

	{#if undigested.length}
		<h2>Undigested citations</h2>
		<p class="faint">{undigested.join(', ')}</p>
	{/if}

	<h2>Runs and comment sessions</h2>
	{#if threads.length || records.length}
		<ul class="plain">
			{#each threads as t (t.id)}<li><a href={threadUrl(t.id)}>{t.title}</a> <span class="faint">{t.kind}{t.discarded ? ' · discarded' : ''}</span></li>{/each}
			{#each records as r (r)}<li><code>{r}</code></li>{/each}
		</ul>
	{:else}
		<p class="faint">None yet.</p>
	{/if}
</main>

<PagePanel label="Filters">
	<div class="filters">
		<label>show<select bind:value={filter}><option value="all">all</option><option value="stale">stale</option><option value="draft">draft</option><option value="incomplete">incomplete</option><option value="loose">loose</option><option value="retired">previous-key matches</option><option value="external">cited results</option></select></label>
		<label>document<select bind:value={master}><option value="">any</option>{#each m.masters as x (x.path)}<option value={x.path}>{x.path}</option>{/each}</select></label>
		<label>author<select bind:value={author}><option value="">any</option>{#each authors as a (a)}<option value={a}>{a}</option>{/each}</select></label>
		<label>tag<select bind:value={tag}><option value="">any</option>{#each Object.keys(m.tags).sort() as t (t)}<option value={t}>{t}</option>{/each}</select></label>
		<p class="faint">{rows.length} of {keys.length} keys</p>
	</div>
</PagePanel>

<style>
	.lead {
		max-width: var(--measure);
		color: var(--ink-soft);
		font-size: 12px;
		line-height: 1.6;
	}
	.counts {
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
	}
	.cause {
		font-family: var(--sans);
		font-size: 10px;
		color: var(--ink-faint);
		margin: 0 0 var(--gap-hair);
	}
	tr.expansion td {
		background: var(--leaf);
		padding: var(--gap-tight);
	}
	.filters {
		display: grid;
		gap: var(--gap-tight);
	}
	.filters label {
		display: grid;
		gap: 2px;
		font-family: var(--sans);
		font-size: 9px;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-faint);
	}
</style>
