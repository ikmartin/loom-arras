<script lang="ts">
	import NoDrafts from '$lib/components/NoDrafts.svelte';
	// The review panel (book 15.3.5): which keys are accepted, which have gone stale and why, and which mark a gap and what that gap blocks. A row expands in place to show the cause and its diff. The filters stand in the shell's left panel and live in the URL, so a home card opens this table already filtered.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import HelpDot from '$lib/components/HelpDot.svelte';
	import PagePanel from '$lib/shell/PagePanel.svelte';
	import { reviewFacts, shortDate, stateBadge } from '$lib/badges';
	import { downstream } from '$lib/graph/layout';
	import { keyUrl, threadUrl } from '$lib/nav';
	import { setQuery } from '$lib/query';
	import { reachedExternal } from '$lib/reached';

	const m = $derived(store.manifest!);
	const SHOWS = ['all', 'accepted', 'stale', 'draft', 'incomplete', 'loose', 'retired', 'external', 'classification'] as const;
	const q = (name: string) => page.url.searchParams.get(name) ?? '';
	const filter = $derived((SHOWS as readonly string[]).includes(q('show')) ? q('show') : 'all');
	const master = $derived(q('document'));
	const author = $derived(q('author'));
	const tag = $derived(q('tag'));
	let open = $state('');
	let blocksOpen = $state('');

	// An external node owes no proof and counts as settled as a dependency (7.6.3), so leaving the ones nothing
	// depends on out of the queue removes noise without hiding work. What is left is the handful whose acceptance
	// means something precise: this digest faithfully states what the source says.
	const reached = $derived(reachedExternal(m));
	const keys = $derived(
		Object.values(m.keys).filter((k) => {
			const n = m.nodes[k.node];
			return !n?.external || !!n.reached_by.length || reached.has(k.node) || filter === 'external';
		})
	);
	const isStale = (k: (typeof keys)[number]) => !!k.acceptance && k.acceptance.fresh === false;
	const counts = $derived({
		accepted: keys.filter((k) => k.state === 'accepted').length,
		stale: keys.filter(isStale).length,
		draft: keys.filter((k) => k.state === 'draft').length,
		incomplete: keys.filter((k) => k.state === 'incomplete').length,
		proved: Object.values(m.nodes).filter((n) => n.derived?.proved).length,
		settled: Object.values(m.nodes).filter((n) => n.derived?.settled).length
	});
	const needsClassification = $derived(keys.filter((k) => m.nodes[k.node]?.basis === 'unclassified' && m.nodes[k.node]?.reached_by.length).length);
	const undigested = $derived(Object.values(m.references).filter((r) => !r.digest && r.cited_by.length).map((r) => r.citekey));
	const rows = $derived(
		keys.filter((k) => {
			const n = m.nodes[k.node];
			if (filter === 'accepted' && k.state !== 'accepted') return false;
			if (filter === 'stale' && !isStale(k)) return false;
			if (filter === 'draft' && k.state !== 'draft') return false;
			if (filter === 'incomplete' && k.state !== 'incomplete') return false;
			if (filter === 'loose' && n?.reached_by.length) return false;
			if (filter === 'retired' && !k.previous_key_match) return false;
			if (filter === 'external' && !m.nodes[k.node]?.external) return false;
			if (filter === 'classification' && (n?.basis !== 'unclassified' || !n.reached_by.length)) return false;
			if (master && !n?.reached_by.includes(master)) return false;
			if (author && !(n?.author ?? []).includes(author) && k.acceptance?.author !== author) return false;
			if (tag && !n?.tags.includes(tag)) return false;
			return true;
		})
	);
	// What a gap blocks: everything that rests on the node carrying it. Computed only for rows that mark one, since the walk is per node.
	const blocks = $derived(new Map(rows.filter((k) => k.incomplete.length).map((k) => [k.key, [...downstream(m, k.node)].sort()])));
	// A column nothing in the current rows fills is not drawn, so a filtered table is not mostly empty headings.
	const hasFacts = $derived(rows.some((k) => reviewFacts(k)));
	const hasIncomplete = $derived(rows.some((k) => k.incomplete.length));
	const hasCauses = $derived(rows.some((k) => k.acceptance?.causes?.length || k.previous_key_match));
	const cols = $derived(5 + (hasCauses ? 1 : 0) + (hasFacts ? 1 : 0) + (hasIncomplete ? 2 : 0));

	const authors = $derived([...new Set([...Object.values(m.nodes).flatMap((n) => n.author ?? []), ...keys.map((k) => k.acceptance?.author).filter(Boolean)])].sort() as string[]);
	const records = $derived([...new Set(Object.values(m.annotations).map((a) => a.run ?? a.record))].sort());
	const threads = $derived(Object.values(m.threads));
	const causes = (k: string) => m.keys[k]?.acceptance?.causes ?? [];

	const LEADS: Record<string, string> = {
		all: 'Every statement and proof in this corpus, with the state recorded for it and, where an accepted text has since changed, the reason it is no longer current.',
		accepted: 'The texts someone has recorded as correct as they stand. One that has changed since is also listed under stale.',
		stale: 'Accepted texts that have changed since, or rest on something that has, with the reason for each.',
		draft: 'Texts nothing has been recorded about yet.',
		incomplete: 'Each text that marks a gap in itself, and what rests on it. A result whose proof is incomplete is not proved, and neither is anything that uses it.',
		loose: 'Texts no document reaches, so nothing depends on them yet.',
		retired: 'Acceptances recorded under an earlier key that now match this one; re-accept to confirm.',
		external: 'Results stated in digests of cited papers, including the ones nothing here uses.',
		classification: 'Blocks whose basis is unclear. Add % !LOOM basis: expository, local-proof, cited-result, assumption, or open-claim inside the drafting block, then rescan.'
	};
	const set = (name: string, fallback = '') => (e: Event) => void setQuery(page.url, name, (e.currentTarget as HTMLSelectElement).value, fallback);
	const show = (v: string) => void setQuery(page.url, 'show', filter === v ? 'all' : v, 'all');
</script>

<main class="page">
	<h1>Review <HelpDot label="what the review panel shows" topic="review" /></h1>
	{#if !m.masters.length}
		<NoDrafts what="keys to review" />
	{/if}
	<p class="lead">{LEADS[filter]} Nothing here writes: states are recorded from the command line, and this page reads them back.</p>
	<p class="counts" data-testid="review-counts">
		{#each [['accepted', counts.accepted], ['stale', counts.stale], ['draft', counts.draft], ['incomplete', counts.incomplete]] as [name, n], i (name)}
			{#if i}<span class="sep">·</span>{/if}<button class="count" class:on={filter === name} aria-pressed={filter === name} onclick={() => show(name as string)} data-testid="show-{name}">{n} {name}</button>
		{/each}
		<span class="sep">·</span>{counts.proved} proved <span class="sep">·</span>{counts.settled} settled
		{#if needsClassification}<span class="sep">·</span><button class="count" class:on={filter === 'classification'} aria-pressed={filter === 'classification'} onclick={() => show('classification')}>{needsClassification} need classification</button>{/if}
	</p>

	<table class="list">
		<thead>
			<tr>
				<th>key</th><th>state</th><th>basis</th><th>since</th>
				{#if hasCauses}<th>cause</th>{/if}
				{#if hasFacts}<th>review</th>{/if}
				{#if hasIncomplete}<th>incomplete</th><th>blocks</th>{/if}
				<th>reached by</th>
			</tr>
		</thead>
		<tbody>
			{#each rows as k (k.key)}
				<tr>
					<td><a href={keyUrl(m, k.key)}>{k.key}</a></td>
					<td><Badge parts={stateBadge(m, k)} /></td>
					<td>{#if m.nodes[k.node]?.kind === 'environment'}{m.nodes[k.node]?.basis === 'unclassified' ? 'needs classification' : m.nodes[k.node]?.basis}{m.nodes[k.node]?.inline_proof ? ' (inline)' : ''}{#if m.nodes[k.node]?.basis === 'unclassified'}<div class="faint">{m.nodes[k.node]?.basis_reason}</div>{/if}{/if}</td>
					<td class="faint nowrap">{k.acceptance ? shortDate(k.acceptance.date) : ''}</td>
					{#if hasCauses}
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
					{/if}
					{#if hasFacts}<td class="faint">{reviewFacts(k)}</td>{/if}
					{#if hasIncomplete}
						<td>{#each k.incomplete as t, i (i)}<div>{t}</div>{/each}</td>
						<td data-testid="blocks-{k.key}">
							{#if blocks.get(k.key)?.length}
								<button class="as-link" onclick={() => (blocksOpen = blocksOpen === k.key ? '' : k.key)} aria-expanded={blocksOpen === k.key}>{blocks.get(k.key)!.length} {blocks.get(k.key)!.length === 1 ? 'result' : 'results'}</button>
							{:else if k.incomplete.length}
								<span class="faint">nothing</span>
							{/if}
						</td>
					{/if}
					<td class="faint">{m.nodes[k.node]?.reached_by.join(', ') || 'loose'}</td>
				</tr>
				{#if open === k.key}
					<tr class="expansion" data-testid="expansion-{k.key}">
						<td colspan={cols}>
							{#each causes(k.key) as c, i (i)}
								{#if c.diff}
									<p class="cause">{c.kind}{c.id ? ' · ' + c.id : ''} — accepted text on the left, current text on the right</p>
									<DiffView path={c.diff} />
								{/if}
							{/each}
						</td>
					</tr>
				{/if}
				{#if blocksOpen === k.key}
					<tr class="expansion">
						<td colspan={cols}>
							<p class="cause">not proved while {k.key} is incomplete</p>
							<p class="blocked">{#each blocks.get(k.key) ?? [] as b, i (b)}{#if i}, {/if}<a href={keyUrl(m, b)}>{b}</a>{/each}</p>
						</td>
					</tr>
				{/if}
			{:else}
				<tr><td colspan={cols} class="faint">Nothing matches.</td></tr>
			{/each}
		</tbody>
	</table>

	{#if undigested.length && filter === 'all'}
		<h2>Undigested citations</h2>
		<p class="faint">{undigested.join(', ')}</p>
	{/if}

	{#if filter === 'all'}
		<h2>Runs and comment sessions</h2>
		{#if threads.length || records.length}
			<ul class="plain">
				{#each threads as t (t.id)}<li><a href={threadUrl(t.id)}>{t.title}</a> <span class="faint">{t.kind}{t.discarded ? ' · discarded' : ''}</span></li>{/each}
				{#each records as r (r)}<li><code>{r}</code></li>{/each}
			</ul>
		{:else}
			<p class="faint">None yet.</p>
		{/if}
	{/if}
</main>

<PagePanel label="Filters">
	<div class="filters">
		<label>show<select value={filter} onchange={set('show', 'all')} data-testid="filter-show"><option value="all">all</option><option value="accepted">accepted</option><option value="stale">stale</option><option value="draft">draft</option><option value="incomplete">incomplete</option><option value="loose">loose</option><option value="retired">previous-key matches</option><option value="external">cited results</option><option value="classification">needs classification</option></select></label>
		<label>document<select value={master} onchange={set('document')}><option value="">any</option>{#each m.masters as x (x.path)}<option value={x.path}>{x.path}</option>{/each}</select></label>
		<label>author<select value={author} onchange={set('author')}><option value="">any</option>{#each authors as a (a)}<option value={a}>{a}</option>{/each}</select></label>
		<label>tag<select value={tag} onchange={set('tag')}><option value="">any</option>{#each Object.keys(m.tags).sort() as t (t)}<option value={t}>{t}</option>{/each}</select></label>
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
	.counts .sep {
		margin: 0 4px;
		color: var(--ink-faint);
	}
	.count {
		font: inherit;
		color: inherit;
		background: none;
		border: none;
		padding: 0 3px;
		border-radius: var(--rad-pill);
		cursor: pointer;
	}
	.count:hover {
		color: var(--link);
	}
	.count.on {
		background: var(--link-wash);
		color: var(--link);
	}
	.nowrap {
		white-space: nowrap;
	}
	.cause {
		font-family: var(--sans);
		font-size: 10px;
		color: var(--ink-faint);
		margin: 0 0 var(--gap-hair);
	}
	.blocked {
		margin: 0;
		font-size: 12px;
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
